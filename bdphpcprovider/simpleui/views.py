# Create your views here.

import logging
import logging.config
logger = logging.getLogger(__name__)

from django.views.generic import ListView, UpdateView, CreateView, DeleteView
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from pprint import pformat

from django.contrib.auth import logout
from django.http import HttpResponseRedirect

from bdphpcprovider.simpleui.hrmc.hrmcsubmit import HRMCSubmitForm
from bdphpcprovider.simpleui.hrmc.copy import CopyForm
from bdphpcprovider.smartconnectorscheduler import models
from bdphpcprovider.smartconnectorscheduler import hrmcstages
from bdphpcprovider.smartconnectorscheduler.errors import ContextKeyMissing, \
    InvalidInputError

from django.views.generic.edit import FormView


class UserProfileParameterListView(ListView):
    model = models.UserProfileParameter
    template_name = "list_userprofileparameter.html"

    def get_queryset(self):
            return models.UserProfileParameter.objects.filter(paramset__user_profile__user=self.request.user)


class CreateUserProfileParameterView(CreateView):
    model = models.UserProfileParameter
    template_name = "edit_userprofileparameter.html"

    def get_success_url(self):
        return reverse('userprofileparameter-list')

    def get_context_data(self, **kwargs):
        context = super(CreateUserProfileParameterView, self).get_context_data(**kwargs)
        context['action'] = reverse('userprofileparameter-new')
        return context


class UpdateUserProfileParameterView(UpdateView):
    model = models.UserProfileParameter
    template_name = "edit_userprofileparameter.html"

    def get_success_url(self):
        return reverse('userprofileparameter-list')

    def get_context_data(self, **kwargs):
        context = super(UpdateUserProfileParameterView, self).get_context_data(**kwargs)
        context['action'] = reverse('userprofileparameter-edit', kwargs={'pk': self.get_object().id})
        return context


class DeleteUserProfileParameterView(DeleteView):
    model = models.UserProfileParameter
    template_name = 'delete_userprofileparameter.html'

    def get_success_url(self):
        return reverse('userprofileparameter-list')


def logout_page(request):
    """
    Log users out and re-direct them to the main page.
    """
    logout(request)
    return HttpResponseRedirect('/accounts/login')


class ContextList(ListView):
    model = models.Context
    template_name = "list_jobs.html"

    def get_queryset(self):
        return models.Context.objects.filter(owner__user=self.request.user)


from django.views.generic import DetailView


class ContextView(DetailView):
    model = models.Context
    template_name = 'view_context.html'

    def get_context_data(self, **kwargs):
        context = super(ContextView, self).get_context_data(**kwargs)
        cpset = models.ContextParameterSet.objects.filter(context=self.object)
        res = []
        context['stage'] = self.object.current_stage.name
        for cps in cpset:
            res.append("<h3>%s</h3> " % cps.schema.namespace)
            for cp in models.ContextParameter.objects.filter(paramset=cps):
                res.append("%s=%s" % (cp.name.name, cp.value))
        context['settings'] = '<br>'.join(res)
        return context


class HRMCSubmitFormView(FormView):
    template_name = 'hrmc.html'
    form_class = HRMCSubmitForm
    success_url = '/jobs'

    initial = {'number_vm_instances': 2,
        'iseed': 42,
        'input_location': 'file://127.0.0.1/myfiles/input',
        'number_of_dimensions': 1,
        'threshold': "[1]",
        'error_threshold': "0.03",
        'max_iteration': 20
        }

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        platform = 'nectar'
        directive_name = "smartconnector_hrmc"
        logger.debug("%s" % directive_name)
        directive_args = []

        directive_args.append(
            ['',
                ['http://rmit.edu.au/schemas/hrmc',
                    ('number_vm_instances',
                        form.cleaned_data['number_vm_instances']),
                    (u'iseed', form.cleaned_data['iseed']),
                    ('input_location',  form.cleaned_data['input_location']),
                    ('number_dimensions', form.cleaned_data['number_of_dimensions']),
                    ('threshold', str(form.cleaned_data['threshold'])),
                    ('error_threshold', str(form.cleaned_data['error_threshold'])),
                    ('max_iteration', form.cleaned_data['max_iteration'])
                ]
            ])

        # make the system settings, available to initial stage and merged with run_settings
        system_dict = {u'system': u'settings'}
        system_settings = {u'http://rmit.edu.au/schemas/system/misc': system_dict}

        logger.debug("directive_name=%s" % directive_name)
        logger.debug("directive_args=%s" % directive_args)

        try:
            (run_settings, command_args, run_context) \
                = hrmcstages.make_runcontext_for_directive(
                platform,
                directive_name,
                directive_args, system_settings, self.request.user.username)

        except InvalidInputError, e:
            return HttpResponse(str(e))


        return super(HRMCSubmitFormView, self).form_valid(form)


class CopyFormView(FormView):
    template_name = 'copy.html'
    form_class = CopyForm
    success_url = '/jobs'

    initial = {'source_bdp_url': 'file://127.0.0.1/myotherfiles/input',
        'destination_bdp_url': 'file://127.0.0.1/myfiles/input_0',
        }

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        platform = 'nectar'
        directive_name = "smartconnector_hrmc"
        logger.debug("%s" % directive_name)
        directive_args = []

        directive_args.append(
            ['',
                ['http://rmit.edu.au/schemas/hrmc',
                    ('number_vm_instances',
                        form.cleaned_data['number_vm_instances']),
                    (u'iseed', form.cleaned_data['iseed']),
                    ('input_location',  form.cleaned_data['input_location']),
                    ('number_dimensions', form.cleaned_data['number_of_dimensions']),
                    ('threshold', str(form.cleaned_data['threshold'])),
                    ('error_threshold', str(form.cleaned_data['error_threshold'])),
                    ('max_iteration', form.cleaned_data['max_iteration'])
                ]
            ])

        # make the system settings, available to initial stage and merged with run_settings
        system_dict = {u'system': u'settings'}
        system_settings = {u'http://rmit.edu.au/schemas/system/misc': system_dict}

        logger.debug("directive_name=%s" % directive_name)
        logger.debug("directive_args=%s" % directive_args)

        try:
            (run_settings, command_args, run_context) \
                = hrmcstages.make_runcontext_for_directive(
                platform,
                directive_name,
                directive_args, system_settings, self.request.user.username)

        except InvalidInputError, e:
            return HttpResponse(str(e))


        return super(HRMCSubmitFormView, self).form_valid(form)
