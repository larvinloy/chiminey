
import logging

from bdphpcprovider.smartconnectorscheduler.sshconnector import get_package_pids, open_connection

from bdphpcprovider.smartconnectorscheduler.smartconnector import Stage, UI, SmartConnector

from bdphpcprovider.smartconnectorscheduler import botocloudconnector

from bdphpcprovider.smartconnectorscheduler.hrmcstages import get_settings, \
    get_run_info, get_filesys, get_all_settings, update_key

from bdphpcprovider.smartconnectorscheduler import sshconnector
from bdphpcprovider.smartconnectorscheduler import hrmcimpl

logger = logging.getLogger(__name__)


def _status_of_nodeset(fs, nodes, output_dir, settings):
    """
    Return lists that describe which of the set of nodes are finished or
    have disappeared
    """
    error_nodes = []
    finished_nodes = []

    for node in nodes:
        instance_id = node.id
        logger.debug("instance_id = %s" % instance_id)

        if not botocloudconnector.is_instance_running(instance_id, settings):
            # An unlikely situation where the node crashed after is was
            # detected as registered.
            logging.error('Instance %s not running' % instance_id)
            error_nodes.append(node)
            continue

        finished = Finished()
        if finished.job_finished(instance_id, settings):
            print "done. output is available"
            hrmcimpl.get_output(fs, instance_id,
#                       "%s/%s" % (output_dir, instance_id),
                output_dir,
                settings)

            hrmcimpl.run_post_task(instance_id, settings)
            post_output_dir = instance_id + "_post"
            hrmcimpl.get_post_output(instance_id,
                "%s/%s" % (output_dir, post_output_dir),
                settings)

            finished_nodes.append(node)
        else:
            print "job still running on %s: %s\
            " % (instance_id, botocloudconnector.get_instance_ip(instance_id, settings))

    return (error_nodes, finished_nodes)



def packages_complete(fs, group_id, output_dir, settings):
    """
    Indicates if all the package nodes have finished and generate
    any output as needed
    """
    nodes = botocloudconnector.get_rego_nodes(group_id, settings)
    error_nodes, finished_nodes = _status_of_nodeset(fs, nodes,
                                                     output_dir,
                                                     settings)
    if finished_nodes + error_nodes == nodes:
        logger.info("Package Finished")
        return True

    if error_nodes:
        logger.warn("error nodes: %s" % error_nodes)
        return True

    return False


class Finished(Stage):
    """
        Return whether the run has finished or not
    """

    def __init__(self):
        self.runs_left = 0
        self.error_nodes = 0
        self.run_time_key = "run_time"

    def triggered(self, context):
        """
            Checks whether there is a non-zero number of runs still going.
        """
        self.settings = get_all_settings(context)
        logger.debug("settings = %s" % self.settings)

        try:
            self.group_id = self.settings['group_id']
        except KeyError:
            logger.warn("group_id is not set in settings")
            return False
        logger.debug("group_id = %s" % self.group_id)

        if 'id' in self.settings:
            self.id = self.settings['id']
            self.output_dir = "output_%s" % self.id
        else:
            self.output_dir = "output"

        # if we have no runs_left then we must have finished all the runs
        if 'runs_left' in self.settings:
            return self.settings['runs_left']
        logger.debug("Finished NOT Triggered")
        return False


    def job_finished(self, instance_id, settings):
        """
            Return True if package job on instance_id has job_finished
        """
        ip = botocloudconnector.get_instance_ip(instance_id, settings)
        ssh = open_connection(ip_address=ip, settings=settings)
        makefile_path = settings['PAYLOAD_DESTINATION']

        command = "cd %s; make %s" % (makefile_path, 'running')
        command_out, _ = sshconnector.run_sudo_command(ssh, command, settings, instance_id)
        if command_out:
            logger.debug("command_out = %s" % command_out)
            still_going = 'stillrunning' in command_out
            logger.debug("still_going = %s" % still_going)
            return not still_going
        return False  # FIXME: this may be undesirable

    def process(self, context):
        """
            Check all registered nodes to find whether
            they are running, stopped or in error_nodes
        """
        fsys = get_filesys(context)
        logger.debug("fsys= %s" % fsys)

        logger.debug("Finished stage process began")
        self.nodes = botocloudconnector.get_rego_nodes(self.group_id, self.settings)

        self.error_nodes = []
        self.finished_nodes = []
        import time
        for node in self.nodes:
            instance_id = node.id
            ip = botocloudconnector.get_instance_ip(instance_id, self.settings)
            ssh = open_connection(ip_address=ip, settings=self.settings)
            if not botocloudconnector.is_instance_running(instance_id, self.settings):
                # An unlikely situation where the node crashed after is was
                # detected as registered.
                #FIXME: should error nodes be counted as finished?
                logging.error('Instance %s not running' % instance_id)
                self.error_nodes.append(node)
                continue
            fin = self.job_finished(instance_id, self.settings)
            logger.debug("fin=%s" % fin)
            if fin:
                print "done. output is available"
                end_time = time.time()

                self.run_time_key = "run_time"
                run_exec_dict = self.settings[self.run_time_key]
                #run_exec_key = node.ip_address
                run_exec_key = botocloudconnector.get_instance_ip(instance_id, self.settings)
                run_exec_vec = run_exec_dict[run_exec_key]
                run_exec_vec.append(end_time)
                run_exec_vec.append(end_time-run_exec_vec[(len(run_exec_vec)-2)])
                run_exec_dict[run_exec_key] = run_exec_vec
                update_key(self.run_time_key, run_exec_dict, self.settings)
                logger.debug("Execution time completed on IP[%s] at "
                             "%f" % (run_exec_key, end_time))


                logger.debug("node=%s" % node)
                logger.debug("finished_nodes=%s" % self.finished_nodes)
                #FIXME: for multiple nodes, if one finishes before the other then
                #its output will be retrieved, but it may again when the other node fails, because
                #we cannot tell whether we have prevous retrieved this output before and finished_nodes
                # is not maintained between triggerings...

                if not (node.id in [x.id for x in self.finished_nodes]):
                    start_time = time.time()
                    hrmcimpl.get_output(fsys, instance_id, self.output_dir, self.settings)
                    #fsys.download_output(ssh, instance_id, self.output_dir, self.settings)
                    import os
                    audit_file = os.path.join(self.output_dir, instance_id, "audit.txt")
                    logger.debug("Audit file path %s" % audit_file)
                    if fsys.exists(self.output_dir, instance_id, "audit.txt"):
                        fsys.delete(audit_file)
                    end_time = time.time()

                    run_exec_vec = run_exec_dict[run_exec_key]
                    run_exec_vec.append(end_time-start_time)
                    run_exec_dict[run_exec_key] = run_exec_vec
                    update_key(self.run_time_key, run_exec_dict, self.settings)
                    logger.debug("Output at IP[%s] reduced" % (run_exec_key))


                else:
                    logger.info("We have already "
                        + "processed output from node %s" % node.id)


                self.finished_nodes.append(node)
            else:
                print "job still running on %s: %s\
                " % (instance_id,
                     botocloudconnector.get_instance_ip(instance_id, self.settings))

    def output(self, context):
        """
        Output new runs_left value (including zero value)
        """
        nodes_working = len(self.nodes) - len(self.finished_nodes)
        update_key('runs_left', nodes_working, context)
        # FIXME: possible race condition?
        update_key('error_nodes', len(self.error_nodes), context)
        update_key('runs_left', nodes_working, context)
        # NOTE: runs_left cannot be deleted or run() will trigger
        return context