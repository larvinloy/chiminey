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

import os
import logging
import json
from itertools import product
from pprint import pformat
from collections import deque


from chiminey.corestages.stage import Stage
from chiminey.smartconnectorscheduler import models
from chiminey.smartconnectorscheduler.jobs \
    import generate_rands, make_runcontext_for_directive

from chiminey import messages
from chiminey.platform import manage
from chiminey import mytardis

from chiminey.runsettings import getval, getvals, \
    setval, update, get_schema_namespaces, SettingNotFoundException
from chiminey.storage import get_url_with_credentials, copy_directories, get_file, put_file

from contextlib import contextmanager

logger = logging.getLogger(__name__)


from django.conf import settings as django_settings

FIRST_ITERATION_DIR = "input_0"
SUBDIRECTIVE_DIR = "run%(run_counter)s"

VALUES_MAP_TEMPLATE_FILE = '%(template_name)s_values'
VALUES_MAP_FILE = django_settings.VALUES_FNAME #"values"


@contextmanager
def ignored(*exceptions):
    try:
        yield
    except exceptions:
        pass

class Sweep(Stage):

    def __init__(self, user_settings=None):
        self.numbfile = 0
        logger.debug("Sweep stage initialized")


    def input_valid(self, settings_to_test):
        #fixme: move to hrmc
        with ignored(SettingNotFoundException, ValueError):
            iseed = int(getval(settings_to_test, '%s/input/hrmc/iseed' % django_settings.SCHEMA_PREFIX))
            NUMBER_SEEDS = 10000 #fixme: should be length of no lines on random_number file
            if not iseed in range(0, NUMBER_SEEDS):
                return (False, 'Random Number Seed should be in range (0, %d)' % (NUMBER_SEEDS -1))
        return (True, 'valid input')


    def is_triggered(self, run_settings):
        logger.debug('run_settings=%s' % run_settings)

        try:
            configure_done = int(getval(run_settings,
                '%s/stages/sweep/sweep_done' % django_settings.SCHEMA_PREFIX))
        except (ValueError, SettingNotFoundException):
            return True

        return not configure_done

    def _get_sweep_name(self, run_settings):
        try:
            return getval(run_settings, '%s/directive_profile/sweep_name' % django_settings.SCHEMA_PREFIX)
        except SettingNotFoundException:
            return 'unknown_sweep'

    def process(self, run_settings):
        logger.debug('run_settings=%s' % run_settings)
        messages.info(run_settings, "0: sweep started")
        # Need to make copy because we pass on run_settings to sub connector
        # so any changes we make here to run_settings WILL be inherited
        def make_local_settings(run_settings):
            from copy import deepcopy
            local_settings = deepcopy(getvals(run_settings, models.UserProfile.PROFILE_SCHEMA_NS))

            update(local_settings, run_settings,
                    django_settings.SCHEMA_PREFIX + '/system/platform',
                    # django_settings.SCHEMA_PREFIX + '/input/mytardis/experiment_id',
                    # django_settings.SCHEMA_PREFIX + '/system/random_numbers',
                   )
            local_settings['bdp_username'] = getval(
                run_settings, '%s/bdp_userprofile/username' % django_settings.SCHEMA_PREFIX)
            return local_settings

        local_settings = make_local_settings(run_settings)
        logger.debug('local_settings=%s' % local_settings)

        compplatform = [k for k, v in run_settings.iteritems()
                        if k.startswith('%s/input/system/compplatform' % django_settings.SCHEMA_PREFIX)]

        setval(run_settings,
               '%s/platform/computation/platform_url' % django_settings.SCHEMA_PREFIX,
               getval(run_settings,
                      '%s/computation_platform'
                          % compplatform[0]))

        def _parse_output_location(run_settings, location):

            loc_list = location.split('/')
            name = loc_list[0]
            offset = ''
            if len(loc_list) > 1:
                offset = os.path.join(*loc_list[1:])
            logger.debug('offset=%s' % offset)
            return name, offset

        contextid = int(getval(run_settings, '%s/system/contextid' % django_settings.SCHEMA_PREFIX))
        logger.debug("contextid=%s" % contextid)

        sweep_name = self._get_sweep_name(run_settings)
        logger.debug("sweep_name=%s" % sweep_name)

        output_loc = self.output_exists(run_settings)
        location = ""
        if output_loc:
            location = getval(run_settings, output_loc)
            output_storage_name, output_storage_offset = \
                _parse_output_location(run_settings, location)
            setval(run_settings,
                   '%s/platform/storage/output/platform_url' % django_settings.SCHEMA_PREFIX,
                   output_storage_name)
            setval(run_settings, '%s/platform/storage/output/offset' % django_settings.SCHEMA_PREFIX,
                   os.path.join(output_storage_offset, '%s%s' % (sweep_name, contextid)))

        def _parse_input_location(run_settings, location):
            loc_list = location.split('/')
            name = loc_list[0]
            offset = ''
            if len(loc_list) > 1:
                offset = os.path.join(*loc_list[1:])
            logger.debug('offset=%s' % offset)
            return (name, offset)

        input_loc = self.input_exists(run_settings)
        logger.debug('special_input_loc=%s' % input_loc)
        if input_loc:
            location = getval(run_settings, input_loc)
            input_storage_name, input_storage_offset = \
                _parse_input_location(run_settings, location)
            setval(run_settings, '%s/platform/storage/input/platform_url' % django_settings.SCHEMA_PREFIX,
                   input_storage_name)
            # store offsets
            setval(run_settings,
                   '%s/platform/storage/input/offset' % django_settings.SCHEMA_PREFIX,
                   input_storage_offset)

        # TODO: replace with scratch space computation platform space
        self.scratch_platform = '%s%s%s' % (
            manage.get_scratch_platform(), sweep_name,
            contextid)

        # mytardis

        if output_loc:
            try:
                self.experiment_id = int(getval(run_settings, '%s/input/mytardis/experiment_id' % django_settings.SCHEMA_PREFIX))
            except KeyError, ValueError:
                self.experiment_id = 0
            try:
                curate_data = getval(run_settings, '%s/input/mytardis/curate_data' % django_settings.SCHEMA_PREFIX)
            except SettingNotFoundException:
                curate_data = False
            curate_data = False #TODO remove
            if curate_data:
                logger.debug('location=%s' %location)
                location = "%s%s" %(sweep_name, contextid)
                self.experiment_id = self.curate_data(run_settings, location, self.experiment_id)
            setval(run_settings,
                   '%s/input/mytardis/experiment_id' % django_settings.SCHEMA_PREFIX,
                   str(self.experiment_id))

        # generate all variations
        map_text = getval(run_settings, '%s/input/sweep/sweep_map' % django_settings.SCHEMA_PREFIX)
        if not map_text:
            map_text = {}
        # map_text = run_settings[django_settings.SCHEMA_PREFIX + '/input/sweep']['sweep_map']
        sweep_map = json.loads(map_text)
        logger.debug("sweep_map=%s" % pformat(sweep_map))
        runs = _expand_variations(maps=[sweep_map], values={})
        logger.debug("runs=%s" % runs)

        # Create random numbers if needed
        # TODO: move iseed out of hrmc into separate generic schema
        # to use on any sweepable connector and make this function
        # completely hrmc independent.

        rands = []

        try:
            self.rand_index = getval(run_settings, '%s/input/hrmc/iseed' % django_settings.SCHEMA_PREFIX)
            logger.debug("rand_index=%s" % self.rand_index)
        except SettingNotFoundException:
            pass
        else:
            # prep random seeds for each run based off original iseed
            # FIXME: inefficient for large random file
            # TODO, FIXME: this is potentially problematic if different
            # runs end up overlapping in the random numbers they utilise.
            # solution is to have separate random files per run or partition
            # big file up.

            try:
                num_url = getval(run_settings, "%s/system/random_numbers" % django_settings.SCHEMA_PREFIX)
                logger.debug('num_url=%s' % num_url)
            except SettingNotFoundException:
                pass
            else:
                try:
                    local_settings['random_numbers'] = num_url
                    rands = generate_rands(settings=local_settings,
                        start_range=0,
                        end_range=-1,
                        num_required=len(runs),
                        start_index=self.rand_index)
                    logger.debug("rands=%s" % rands)
                except Exception, e:
                    logger.debug('error')
                    logger.error(e)
                    raise

        # load initial values map in the input directory which
        # contains variable to use for all subdirectives
        starting_map = {}
        if input_loc:

            input_storage_settings = self.get_platform_settings(
                run_settings, '%s/platform/storage/input' % django_settings.SCHEMA_PREFIX)
            try:
                input_prefix = '%s://%s@' % (input_storage_settings['scheme'],
                                        input_storage_settings['type'])

                values_url = get_url_with_credentials(
                    input_storage_settings,
                    input_prefix + os.path.join(input_storage_settings['ip_address'],
                        input_storage_offset, "initial", VALUES_MAP_FILE),
                    is_relative_path=False)
                logger.debug("values_url=%s" % values_url)

                values_e_url = get_url_with_credentials(
                    local_settings,
                    values_url,
                    is_relative_path=False)
                logger.debug("values_url=%s" % values_e_url)
                values_content = get_file(values_e_url)
                logger.debug("values_content=%s" % values_content)
                starting_map = dict(json.loads(values_content))
            except IOError:
                logger.warn("no starting values file found")
            except ValueError:
                logger.error("problem parsing contents of %s" % VALUES_MAP_FILE)
                pass
            logger.debug("starting_map after initial values=%s"
                % pformat(starting_map))

        # Copy form input values info starting map
        # FIXME: could have name collisions between form inputs and
        # starting values.
        for ns in run_settings:
            if ns.startswith(django_settings.SCHEMA_PREFIX + "/input"):
                #starting_map.update(dict([(k,v) for k,v in getvals(run_settings, ns).iteritems()]))
                # for k, v in run_settings[ns].items():
                for k, v in getvals(run_settings, ns).iteritems():
                    starting_map[k] = v
        logger.debug("starting_map after form=%s" % pformat(starting_map))

        # FIXME: we assume we will always have input directory

        # Get input_url directory
        input_url = ""
        if input_loc:
            input_prefix = '%s://%s@' % (input_storage_settings['scheme'],
                                    input_storage_settings['type'])
            input_url = get_url_with_credentials(input_storage_settings,
                input_prefix + os.path.join(input_storage_settings['ip_address'],
                    input_storage_offset),
            is_relative_path=False)
            logger.debug("input_url=%s" % input_url)

        current_context = models.Context.objects.get(id=contextid)
        user = current_context.owner.user.username

        # For each of the generated runs, copy across initial input
        # to individual input directories with variation values,
        # and then schedule subrun of sub directive
        logger.debug("run_settings=%s" % run_settings)
        for i, context in enumerate(runs):

            run_counter = int(context['run_counter'])
            logger.debug("run_counter=%s" % run_counter)
            run_inputdir = os.path.join(self.scratch_platform,
                SUBDIRECTIVE_DIR % {'run_counter': str(run_counter)},
                FIRST_ITERATION_DIR,)
            logger.debug("run_inputdir=%s" % run_inputdir)
            run_iter_url = get_url_with_credentials(local_settings,
                run_inputdir, is_relative_path=False)
            logger.debug("run_iter_url=%s" % run_iter_url)

            # Duplicate any input_directory into runX duplicates
            if input_loc:
                logger.debug("context=%s" % context)
                copy_directories(input_url, run_iter_url)

            # Need to load up existing values, because original input_dir could
            # have contained values for the whole run
            # This code is deprecated in favour of single values file.
            self.error_detected = False

            # try:
            #     template_name = getval(run_settings,
            #                            '%s/stages/sweep/template_name'
            #                                 % django_settings.SCHEMA_PREFIX)
            # except SettingNotFoundException:
            #     pass
            # else:
            #     logger.debug("template_name=%s" % template_name)
            #     v_map = {}
            #     try:
            #         values_url = get_url_with_credentials(
            #             local_settings,
            #             os.path.join(run_inputdir, "initial",
            #                  VALUES_MAP_TEMPLATE_FILE % {'template_name': template_name}),
            #             is_relative_path=False)
            #         logger.debug("values_url=%s" % values_url)
            #         values_content = get_file(values_url)
            #         logger.debug("values_content=%s" % values_content)
            #         v_map = dict(json.loads(values_content), indent=4)
            #     except IOError:
            #         logger.warn("no values file found")
            #     except ValueError:
            #         logger.error("problem parsing contents of %s" % VALUES_MAP_FILE)
            #         pass
            #     v_map.update(starting_map)
            #     v_map.update(context)
            #     v_map['run_counter'] = 1
            #     logger.debug("new v_map=%s" % v_map)
            #     put_file(values_url, json.dumps(v_map, indent=4))

            v_map = {}
            try:
                values_url = get_url_with_credentials(
                    local_settings,
                    os.path.join(run_inputdir, "initial",
                        VALUES_MAP_FILE),
                    is_relative_path=False)
                logger.debug("values_url=%s" % values_url)
                values_content = get_file(values_url)
                logger.debug("values_content=%s" % values_content)
                v_map = dict(json.loads(values_content), )
            except IOError:
                logger.warn("no values file found")
            except ValueError:
                logger.error("problem parsing contents of %s" % VALUES_MAP_FILE)
                pass
            v_map.update(starting_map)
            v_map.update(context)
            v_map['run_counter'] = 1

            logger.debug("new v_map=%s" % v_map)
            put_file(values_url, json.dumps(v_map, indent=4))

            # Set random numbers for subdirective
            logger.debug("run_settings=%s" % pformat(run_settings))
            if rands:
                setval(run_settings, '%s/input/hrmc/iseed' % django_settings.SCHEMA_PREFIX, rands[i])


            if input_loc:
                # Set revised input_location for subdirective
                setval(run_settings, input_loc,
                    "%s/%s/%s" % (self.scratch_platform,
                                    SUBDIRECTIVE_DIR
                                        % {'run_counter': str(run_counter)},
                                    FIRST_ITERATION_DIR))

            # Redirect input
            run_input_storage_name, run_input_storage_offset = \
                _parse_input_location(run_settings,
                    "local/%s%s/run%s/input_0" % (sweep_name, contextid, run_counter))

            #run_input_storage_offset = os.path.join('%s%s' % (sweep_name, contextid), run_input_storage_offset)

            logger.debug('run_input_storage_name=%s' % run_input_storage_name)
            logger.debug('run_input_storage_offset=%s' % run_input_storage_offset)

            setval(run_settings,
                    '%s/platform/storage/input/platform_url' % django_settings.SCHEMA_PREFIX,
                    run_input_storage_name)
            setval(run_settings,
                    '%s/platform/storage/input/offset' % django_settings.SCHEMA_PREFIX,
                    run_input_storage_offset)

            logger.debug("updated_run_settings=%s" % pformat(run_settings))
            try:
                _submit_subdirective("nectar", run_settings, user, current_context)
            except Exception, e:
                logger.error(e)
                raise e

    def output(self, run_settings):
        logger.debug("sweep output")

        setval(run_settings, '%s/stages/sweep/sweep_done' % django_settings.SCHEMA_PREFIX, 1)
        logger.debug('interesting run_settings=%s' % run_settings)

        with ignored(SettingNotFoundException):
            if getvals(run_settings, '%s/input/mytardis' % django_settings.SCHEMA_PREFIX):
                setval(run_settings,
                       '%s/input/mytardis/experiment_id' % django_settings.SCHEMA_PREFIX,
                       str(self.experiment_id))

        if not self.error_detected:
            messages.success(run_settings, "0: sweep completed")
        return run_settings

    def curate_data(self, run_settings, location, experiment_id):
        # TODO: this is a domain-specific so this function should be overridden
        # in domain specfic mytardis class
        #TODO: By default, this class should NOT CREATE an experiment

        # try:
        #     experiment_id = int(getval(run_settings, '%s/input/mytardis/experiment_id' % django_settings.SCHEMA_PREFIX))
        # except SettingNotFoundException:
        #     experiment_id = 0
        # except ValueError:
        #     experiment_id = 0

        # experiment_id = post_mytardis_exp(
        #     run_settings=run_settings,
        #     experiment_id=experiment_id,
        #     output_location=self.scratch_platform)

        # return experiment_id

        return experiment_id


def _submit_subdirective(platform, run_settings, user, parentcontext):
    try:
        subdirective_name = getval(run_settings, '%s/stages/sweep/directive' % django_settings.SCHEMA_PREFIX)
    except SettingNotFoundException:
        logger.warn("cannot find subdirective_name name")
        raise

    directive_args = deque()
    for schema in get_schema_namespaces(run_settings):
        keys = getvals(run_settings, schema)
        #d = []
        d = deque([(k,v) for k,v in keys.iteritems()])
        logger.debug("keys=%s" % keys.iteritems())
        # for k, v in keys.iteritems():
        #     d.append((k, v))
        d.appendleft(schema)
        #d.insert(0, schema)
        directive_args.append(list(d))
    directive_args.appendleft('')
    #directive_args.insert(0, '')
    directive_args = [list(directive_args)]
    logger.debug("directive_args=%s" % pformat(directive_args))
    logger.debug('subdirective_name=%s' % subdirective_name)

    (task_run_settings, command_args, run_context) \
        = make_runcontext_for_directive(
            platform_name=platform,
            directive_name=subdirective_name,
            directive_args=directive_args,
            initial_settings={},
            username=user, parent=parentcontext)

    logger.debug("sweep process done")


def _expand_variations(maps, values):
    """
    Based on maps, generate all range variations from the template
    """
    # FIXME: doesn't handle multiple template files together
    res = []
    numbfile = 0
    for iter, template_map in enumerate(maps):
        logger.debug("template_map=%s" % template_map)
        logger.debug("iter #%d" % iter)
        # ensure ordering of the template_map entries
        map_keys = template_map.keys()
        logger.debug("map_keys %s" % map_keys)
        map_ranges = [list(template_map[x]) for x in map_keys]
        logger.debug("map_ranges=%s" % map_ranges)
        for z in product(*map_ranges):
            logger.debug("len(z)=%s" % len(z))
            context = dict(values)
            for i, k in enumerate(map_keys):
                logger.debug("i=%s k=%s" % (i, k))
                logger.debug("z[i]=%s" % z[i])
                context[k] = str(z[i])  # str() so that 0 doesn't default value
            context['run_counter'] = numbfile
            numbfile += 1
            res.append(context)
    return res


class HRMCSweep(Sweep):
    pass
    # def curate_data(self, run_settings):

    #     # mytardis
    #     try:
    #         subdirective = getval(run_settings, '%s/stages/sweep/directive' % django_settings.SCHEMA_PREFIX)
    #     except SettingNotFoundException:
    #         logger.warn("cannot find subdirective name")
    #         subdirective = ''
    #     try:
    #         experiment_id = int(getvala(run_settings, '%s/input/mytardis/experiment_id' % django_settings.SCHEMA_PREFIX))
    #     except SettingNotFoundException:
    #         experiment_id = 0
    #     except ValueError:
    #         experiment_id = 0

    #     if subdirective == "hrmc":
    #         experiment_id = post_mytardis_exp(
    #             run_settings=run_settings,
    #             experiment_id=experiment_id,
    #             output_location=self.scratch_platform)
    #     else:
    #         logger.warn("cannot find subdirective name")

    #     return experiment_id


def post_mytardis_exp(run_settings,
        experiment_id,
        output_location,
        experiment_paramset=[]):
    # TODO: move into mytardis package?
    bdp_username = getval(run_settings, '%s/bdp_userprofile/username' % django_settings.SCHEMA_PREFIX)

    try:
        mytardis_url = getval(run_settings, '%s/input/mytardis/mytardis_platform' % django_settings.SCHEMA_PREFIX)
    except SettingNotFoundException:
        logger.error("mytardis_platform not set")
        return 0

    mytardis_settings = manage.get_platform_settings(
        mytardis_url,
        bdp_username)
    logger.debug(mytardis_settings)
    curate_data = getval(run_settings, '%s/input/mytardis/curate_data' % django_settings.SCHEMA_PREFIX)
    if curate_data:
        if mytardis_settings['mytardis_host']:
            def _get_exp_name_for_input(path):
                return str(os.sep.join(path.split(os.sep)[-1:]))
            ename = _get_exp_name_for_input(output_location)
            logger.debug("ename=%s" % ename)
            experiment_id = mytardis.create_experiment(
                settings=mytardis_settings,
                exp_id=experiment_id,
                experiment_paramset=experiment_paramset,
                expname=ename)
        else:
            logger.warn("no mytardis host specified")
    else:
        logger.warn('Data curation is off')
    return experiment_id
