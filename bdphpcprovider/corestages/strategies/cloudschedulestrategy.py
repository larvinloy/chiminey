# Copyright (C) 2014, RMIT University

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import logging
import os

from django.core.exceptions import ImproperlyConfigured
from bdphpcprovider.smartconnectorscheduler import models, hrmcstages
from bdphpcprovider.platform import get_job_dir
from bdphpcprovider.cloudconnection import is_vm_running
from bdphpcprovider.runsettings import SettingNotFoundException, getval, update
from bdphpcprovider.storage import get_url_with_pkey, get_make_path, put_file, list_dirs
from bdphpcprovider.sshconnection import open_connection
from bdphpcprovider.compute import run_command_with_status


logger = logging.getLogger(__name__)
RMIT_SCHEMA = "http://rmit.edu.au/schemas"


def set_schedule_settings(self, run_settings, local_settings):
    #fixme: the last three should move to hrmc package
    update(local_settings, run_settings,
            #'%s/input/system/cloud/number_vm_instances' % RMIT_SCHEMA,
            '%s/input/reliability/maximum_retry' % RMIT_SCHEMA,
            '%s/stages/setup/payload_destination' % RMIT_SCHEMA,
            '%s/stages/setup/filename_for_PIDs' % RMIT_SCHEMA,
            '%s/stages/setup/payload_name' % RMIT_SCHEMA,
            #'%s/system/platform' % RMIT_SCHEMA,
            '%s/stages/bootstrap/bootstrapped_nodes' % RMIT_SCHEMA,
            #'%s/stages/create/custom_prompt' % RMIT_SCHEMA,
            '%s/system/max_seed_int' % RMIT_SCHEMA,
            '%s/input/hrmc/optimisation_scheme' % RMIT_SCHEMA,
            '%s/input/hrmc/fanout_per_kept_result' % RMIT_SCHEMA)
    local_settings['bdp_username'] = getval(run_settings, '%s/bdp_userprofile/username' % RMIT_SCHEMA)


def schedule_task(schedule_class, run_settings, local_settings):
    if schedule_class.procs_2b_rescheduled:
        start_reschedule(schedule_class, run_settings, local_settings)
    else:
        start_schedule(schedule_class, run_settings, local_settings)


def complete_schedule(schedule_class, local_settings):
    logger.debug("started")
    for node in schedule_class.nodes:
        node_ip = node.ip_address
        logger.debug("node_ip=%s" % node_ip)
        if not node_ip:
            node_ip = node.private_ip_address
        if (node_ip in [x[1]
                                for x in schedule_class.scheduled_nodes
                                if x[1] == node_ip]) \
            and (not schedule_class.procs_2b_rescheduled):
            logger.debug("skip1")
            continue
        if (node_ip in [x[1]
                                for x in schedule_class.rescheduled_nodes
                                if x[1] == node_ip]) \
            and schedule_class.procs_2b_rescheduled:
            logger.debug("skip2")

            continue
        if not is_vm_running(node):
            # An unlikely situation where the node crashed after is was
            # detected as registered.
            #FIXME: should error nodes be counted as finished?
            #FIXME: remove this instance from created_nodes
            logger.error('Instance %s not running' % node.id)
            #self.error_nodes.append((node.id, node_ip,
            #                        unicode(node.region)))
            logger.debug("skip3")
            continue

        logger.debug('mynode=%s' % node_ip)
        try:
            relative_path = "%s@%s" % (local_settings['type'],
                local_settings['payload_destination'])
            destination = get_url_with_pkey(
                local_settings,
                relative_path,
                is_relative_path=True,
                ip_address=node_ip)
        except Exception, e:
            logger.debug(e)
        logger.debug("Relative path %s" % relative_path)
        logger.debug("Destination %s" % destination)
        fin = _is_schedule_complete(node_ip, local_settings, destination)
        logger.debug("fin=%s" % fin)
        if fin:
            logger.debug("done.")
            node_list = schedule_class.scheduled_nodes
            if schedule_class.procs_2b_rescheduled:
                node_list = schedule_class.rescheduled_nodes
            if not (node_ip in [x[1]
                                            for x in node_list
                                            if x[1] == node_ip]):
                    node_list.append([node.id, node_ip,
                                                unicode(node.region), 'running'])
                    if schedule_class.procs_2b_rescheduled:
                        scheduled_procs = [x
                                           for x in schedule_class.current_processes
                                           if x['ip_address'] == node_ip
                            and x['status'] == 'reschedule_ready']
                        schedule_class.total_rescheduled_procs += len(scheduled_procs)
                        for process in scheduled_procs:
                            process['status'] = 'ready'
                        schedule_class.all_processes = update_lookup_table(
                            schedule_class.all_processes,
                            reschedule_to_ready='reschedule_to_ready')
                    else:
                        scheduled_procs = [x['ip_address']
                                           for x in schedule_class.current_processes
                                           if x['ip_address'] == node_ip]
                        schedule_class.total_scheduled_procs += len(scheduled_procs)
                        #if self.total_scheduled_procs == len(self.current_processes):
                        #    break
            else:
                    logger.info("We have already "
                        + "scheduled process on node %s" % node_ip)
        else:
            print "job still running on %s" % node_ip


def start_schedule(schedule_class, run_settings, local_settings):
    #FIXme replace with hrmcstage.get_parent_stage()
    schedule_package = "bdphpcprovider.corestages.schedule.Schedule"
    parent_obj = models.Stage.objects.get(package=schedule_package)
    parent_stage = parent_obj.parent
    logger.debug("local_settings=%s" % local_settings)
    logger.debug("run_settings=%s" % run_settings)
    try:
        logger.debug('parent_package=%s' % (parent_stage.package))
        stage = hrmcstages.safe_import(parent_stage.package, [],
                                       {'user_settings': local_settings})
        logger.debug("stage=%s" % stage)
    except ImproperlyConfigured, e:
        logger.debug(e)
        return (False, "Except in import of stage: %s: %s"
            % (parent_stage.name, e))
    except Exception, e:
        logger.error(e)
        raise

    map = stage.get_run_map(local_settings, run_settings=run_settings)
    try:
        isinstance(map, tuple)
        run_map = map[0]
    except TypeError:
        run_map = map
    logger.debug('map=%s' % run_map)
    output_storage_settings = schedule_class.get_platform_settings(
            run_settings, 'http://rmit.edu.au/schemas/platform/storage/output')
    offset = getval(run_settings, '%s/platform/storage/output/offset' % RMIT_SCHEMA)
    job_dir = get_job_dir(output_storage_settings, offset)
    schedule_class.total_processes = get_total_templates(
        [run_map], run_settings=run_settings,
        output_storage_settings=output_storage_settings, job_dir=job_dir)
    logger.debug('total_processes=%d' % schedule_class.total_processes)
    schedule_class.current_processes = []
    schedule_class.schedule_index, schedule_class.current_processes = \
            start_round_robin_schedule(
                schedule_class.nodes, schedule_class.total_processes,
                                       schedule_class.schedule_index,
                                       local_settings)
    schedule_class.all_processes = update_lookup_table(
             schedule_class.all_processes,
             new_processes=schedule_class.current_processes)
    logger.debug('all_processes=%s' % schedule_class.all_processes)


def start_reschedule(schedule_class, run_settings, local_settings):
    output_storage_settings = schedule_class.get_platform_settings(
            run_settings, 'http://rmit.edu.au/schemas/platform/storage/output')
    _, schedule_class.current_processes = \
    start_round_robin_reschedule(schedule_class.nodes, schedule_class.procs_2b_rescheduled,
                                 schedule_class.current_processes, local_settings, output_storage_settings)
    schedule_class.all_processes = update_lookup_table(
             schedule_class.all_processes,
             new_processes=schedule_class.current_processes, reschedule=True)


def start_round_robin_schedule(nodes, processes, schedule_index, settings):
    total_nodes = len(nodes)
    all_nodes = list(nodes)
    if total_nodes > processes:
        total_nodes = processes
        all_nodes = nodes[:total_nodes]
    if total_nodes == 0:
        return
    proc_per_node = processes / total_nodes
    remaining_procs = processes % total_nodes
    index = schedule_index
    new_processes = []

    for cur_node in all_nodes:
        ip_address = cur_node.ip_address
        if not ip_address:
            ip_address = cur_node.private_ip_address
        logger.debug('ip_address=%s' % ip_address)
        relative_path = settings['type'] + '@' + settings['payload_destination']
        procs_on_cur_node = proc_per_node
        if remaining_procs:
            procs_on_cur_node = proc_per_node + 1
            remaining_procs -= 1
        logger.debug('procs_cur_node=%d' % procs_on_cur_node)
        ids = get_procs_ids(procs_on_cur_node, index=index)
        index += len(ids)
        logger.debug('index=%d' % index)
        put_proc_ids(relative_path, ids, ip_address, settings)
        new_processes = construct_lookup_table(
            ids, ip_address, new_processes,
            maximum_retry=int(settings['maximum_retry']))

        destination = get_url_with_pkey(
            settings,
            relative_path,
            is_relative_path=True,
            ip_address=ip_address)
        logger.debug('schedule destination=%s' % destination)
        makefile_path = get_make_path(destination)
        logger.debug('makefile_path=%s' % makefile_path)
        command = "cd %s; make %s" % (makefile_path,
            'schedulestart PAYLOAD_NAME=%s IDS=%s' % (
            settings['payload_name'], settings['filename_for_PIDs']))
        command_out = ''
        errs = ''
        logger.debug("starting command for %s" % ip_address)
        try:
            ssh = open_connection(ip_address=ip_address, settings=settings)
            command_out, errs = run_command_with_status(ssh, command)
        except Exception, e:
            logger.error(e)
        finally:
            if ssh:
                ssh.close()
        logger.debug("command_out2=(%s, %s)" % (command_out, errs))
    logger.debug('index=%d' % index)
    logger.debug('current_processes=%s' % new_processes)
    return index, new_processes


def start_round_robin_reschedule(nodes, procs_2b_rescheduled,
                                 current_procs, settings, output_storage_settings):
    total_nodes = len(nodes)
    all_nodes = list(nodes)
    processes = len(procs_2b_rescheduled)
    if total_nodes > processes:
        total_nodes = processes
        all_nodes = nodes[:total_nodes]
    if total_nodes == 0:
        return
    proc_per_node = processes / total_nodes
    remaining_procs = processes % total_nodes
    index = 0
    new_processes = current_procs
    rescheduled_procs = list(procs_2b_rescheduled)
    for cur_node in all_nodes:
        logger.debug('Schedule here %s' % cur_node)
        ip_address = cur_node.ip_address
        if not ip_address:
            ip_address = cur_node.private_ip_address
        logger.debug('ip_address=%s' % ip_address)
        relative_path = output_storage_settings['type'] + '@' + settings['payload_destination']
        procs_on_cur_node = proc_per_node
        if remaining_procs:
            procs_on_cur_node = proc_per_node + 1
            remaining_procs -= 1
        logger.debug('procs_cur_node=%d' % procs_on_cur_node)
        ids = get_procs_ids(procs_on_cur_node,
                            rescheduled_procs=rescheduled_procs)
        #index += len(ids)
        #logger.debug('index=%d' % index)
        put_proc_ids(relative_path, ids, ip_address, settings)
        new_processes = construct_lookup_table(
            ids, ip_address, new_processes,
            status='reschedule_ready',
            maximum_retry=int(settings['maximum_retry']))
        destination = get_url_with_pkey(settings,
            relative_path,
            is_relative_path=True,
            ip_address=ip_address)
        logger.debug('schedule destination=%s' % destination)
        makefile_path = get_make_path(destination)
        logger.debug('makefile_path=%s' % makefile_path)
        command = "cd %s; make %s" % (makefile_path,
            'schedulestart PAYLOAD_NAME=%s IDS=%s' % (
            settings['payload_name'], settings['filename_for_PIDs']))
        command_out = ''
        errs = ''
        logger.debug("starting command for %s" % ip_address)
        try:
            ssh = open_connection(ip_address=ip_address, settings=settings)
            command_out, errs = run_command_with_status(ssh, command)
        except Exception, e:
            logger.error(e)
        finally:
            if ssh:
                ssh.close()
        logger.debug("command_out2=(%s, %s)" % (command_out, errs))
    logger.debug('index=%d' % index)
    logger.debug('current_processes=%s' % new_processes)
    return index, new_processes


def get_procs_ids(process, **kwargs):
    ids = []
    try:
        index = kwargs['index']
        for i in range(process):
            ids.append(index + 1)
            index += 1
    except KeyError, e:
        logger.debug(e)
    try:
        rescheduled_procs = kwargs['rescheduled_procs']
        for i in range(process):
            reschedule_process = rescheduled_procs[0]
            ids.append(reschedule_process['id'])
            rescheduled_procs.pop(0)
    except KeyError, e:
        logger.debug(e)
    logger.debug('process ids = %s' % ids)
    return ids


def put_proc_ids(relative_path, ids, ip, settings):
    relative_path = os.path.join(relative_path,
                                 settings['filename_for_PIDs'])
    logger.debug('put_proc_ids=%s' % relative_path)
    destination = get_url_with_pkey(settings,
        relative_path,
        is_relative_path=True,
        ip_address=ip)
    logger.debug('destination=%s' % destination)
    ids_str = []
    [ids_str.append(str(i)) for i in ids]
    proc_ids = ("\n".join(ids_str)) + "\n"
    logger.debug('ids_str=%s' % ids_str)
    logger.debug('proc_ids=%s' % proc_ids)
    logger.debug('encoded=%s' % proc_ids.encode('utf-8'))
    put_file(destination, proc_ids.encode('utf-8'))


def construct_lookup_table(ids, ip_address, new_processes, maximum_retry=1, status='ready'):
    for id in ids:
        new_processes.append(
            {'status': '%s' % status, 'id': '%s' % id,
             'ip_address': '%s' % ip_address,
             'retry_left': '%d' % maximum_retry})
    return new_processes


def update_lookup_table(all_processes, reschedule=False, **kwargs):
    try:
        new_processes = kwargs['new_processes']
        if not reschedule:
            for process in new_processes:
                all_processes.append(process)
        else:
            for process in new_processes:
                if process['status'] == 'reschedule_ready':
                    all_processes.append(process)
    except KeyError, e:
        logger.debug(e)
    try:
        reschedule_to_ready = kwargs['reschedule_to_ready']
        for process in all_processes:
            if process['status'] == 'reschedule_ready':
                process['status'] = 'ready'
    except KeyError, e:
        logger.debug(e)
    return all_processes

#todo: check get_total_templates() in composite.py
def get_total_templates(maps, **kwargs):
        run_settings = kwargs['run_settings']
        output_storage_settings = kwargs['output_storage_settings']
        job_dir = kwargs['job_dir']
        try:
            id = int(getval(run_settings,
                                 '%s/system/id' % RMIT_SCHEMA))
        except (SettingNotFoundException, ValueError) as e:
            logger.debug(e)
            id = 0
        iter_inputdir = os.path.join(job_dir, "input_%s" % id)
        url_with_pkey = get_url_with_pkey(
            output_storage_settings,
            '%s://%s@%s' % (output_storage_settings['scheme'],
                           output_storage_settings['type'],
                            iter_inputdir),
            is_relative_path=False)
        logger.debug(url_with_pkey)
        input_dirs = list_dirs(url_with_pkey)
        for iter, template_map in enumerate(maps):
            logger.debug("template_map=%s" % template_map)
            map_keys = template_map.keys()
            logger.debug("map_keys %s" % map_keys)
            map_ranges = [list(template_map[x]) for x in map_keys]
            product = 1
            for i in map_ranges:
                product = product * len(i)
            total_templates = product * len(input_dirs)
            logger.debug("total_templates=%d" % (total_templates))
        return total_templates


def _is_schedule_complete(ip, settings, destination):
        """
            Return True if package job on instance_id has is_job_finished
        """
        ssh = open_connection(ip_address=ip, settings=settings)
        makefile_path = get_make_path(destination)
        command = "cd %s; make %s" % (makefile_path,
                                      'scheduledone IDS=%s' % (
                                          settings['filename_for_PIDs']))
        command_out, _ = run_command_with_status(ssh, command)
        if command_out:
            logger.debug("command_out = %s" % command_out)
            for line in command_out:
                if 'All processes are scheduled' in line:
                    return True
        return False