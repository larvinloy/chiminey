# Copyright (C) 2013, RMIT University

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
#
#
#
import logging
import logging.config
logger = logging.getLogger(__name__)


from tastypie import fields
from tastypie.resources import ModelResource
from tastypie.utils import dict_strip_unicode_keys
from tastypie import http


# TODO: replace digest authentication with oauth
from tastypie.authentication import DigestAuthentication
from tastypie.authorization import DjangoAuthorization
from bdphpcprovider.smartconnectorscheduler import models
from django.contrib.auth.models import User
import django

from bdphpcprovider.smartconnectorscheduler.errors import InvalidInputError


from bdphpcprovider.smartconnectorscheduler import hrmcstages


class UserResource(ModelResource):
    class Meta:
        queryset = User.objects.all()
        resource_name = 'user'
        allowed_methods = ['get']
        excludes = ['email', 'password', 'is_active', 'is_staff', 'is_superuser']


class UserProfileResource(ModelResource):
    userid = fields.ForeignKey(UserResource, 'user')

    class Meta:
        queryset = models.UserProfile.objects.all()
        resource_name = 'userprofile'
        allowed_methods = ['get']
        authentication = DigestAuthentication()
        authorization = DjangoAuthorization()

    def apply_authorization_limits(self, request, object_list):
        return object_list.filter(user=request.user)

    # def obj_create(self, bundle, **kwargs):
    #     return super(UserProfileResource, self).obj_create(bundle,
    #         user=bundle.request.user)

    def get_object_list(self, request):
        # FIXME: we never seem to be authenticated here
        if request.user.is_authenticated():
            return models.UserProfile.objects.filter(user=request.user)
        else:
            return models.UserProfile.objects.none()


class SchemaResource(ModelResource):
    class Meta:
        queryset = models.Schema.objects.all()
        resource_name = 'schemas'
        allowed_methods = ['get']


class ParameterNameResource(ModelResource):
    class Meta:
        queryset = models.ParameterName.objects.all()
        resource_name = 'parametername'
        allowed_methods = ['get']


class UserProfileParameterSetResource(ModelResource):
    user_profile = fields.ForeignKey(UserProfileResource,
        attribute='user_profile')
    schema = fields.ForeignKey(SchemaResource,
        attribute='schema')

    class Meta:
        queryset = models.UserProfileParameterSet.objects.all()
        resource_name = 'userprofileparameterset'
        authentication = DigestAuthentication()
        authorization = DjangoAuthorization()
        allowed_methods = ['get']

    def get_object_list(self, request):
        return models.UserProfileParameterSet.objects.filter(user_profile__user=request.user)


class UserProfileParameterResource(ModelResource):
    name = fields.ForeignKey(ParameterNameResource,
        attribute='name')
    paramset = fields.ForeignKey(UserProfileParameterSetResource,
        attribute='paramset')

    def apply_authorization_limits(self, request, object_list):
        return object_list.filter(paramset__user_profile__user=request.user)

    def obj_create(self, bundle, **kwargs):
        return super(UserProfileParameterResource, self).obj_create(bundle,
            user=bundle.request.user)

    def get_object_list(self, request):
        return models.UserProfileParameter.objects.filter(paramset__user_profile__user=request.user)

    class Meta:
        queryset = models.UserProfileParameter.objects.all()
        resource_name = 'userprofileparameter'
        authentication = DigestAuthentication()
        authorization = DjangoAuthorization()
        # curl --digest --user user2 --dump-header - -H "Content-Type: application/json" -X PUT --data ' {"value": 44}' http://115.146.86.247/api/v1/userprofileparameter/48/?format=json
        allowed_methods = ['get', 'put']


class ContextResource(ModelResource):

    owner = fields.ForeignKey(UserProfileResource,
        attribute='owner')

    class Meta:
        queryset = models.Context.objects.all()
        resource_name = 'context'
        authentication = DigestAuthentication()
        authorization = DjangoAuthorization()
        allowed_methods = ['get', 'post']

    def apply_authorization_limits(self, request, object_list):
        return object_list.filter(user=request.user)

    def get_object_list(self, request):
        return models.Context.objects.filter(owner__user=request.user)

    def post_list(self, request, **kwargs):
        #curl --digest --user user2 --dump-header - -H "Content-Type: application/json" -X POST --data ' {"number_vm_instances": 8, "iseed": 42, "input_location": "file://127.0.0.1/myfiles/input", "number_of_dimensions": 2, "threshold": "[2]", "error_threshold": "0.03", "max_iteration": 10}' http://115.146.86.247/api/v1/context/?format=json

        if django.VERSION >= (1, 4):
            body = request.body
        else:
            body = request.raw_post_data
        deserialized = self.deserialize(request, body, format=request.META.get('CONTENT_TYPE', 'application/json'))
        deserialized = self.alter_deserialized_detail_data(request, deserialized)
        bundle = self.build_bundle(data=dict_strip_unicode_keys(deserialized), request=request)

        platform = 'nectar'
        directive_name = "smartconnector_hrmc"
        logger.debug("%s" % directive_name)
        directive_args = []

        directive_args.append(
         ['',
             ['http://rmit.edu.au/schemas/hrmc',
                 ('number_vm_instances',
                     bundle.data['number_vm_instances']),
                 (u'iseed', bundle.data['iseed']),
                ('input_location',  bundle.data['input_location']),
                 ('number_dimensions', bundle.data['number_of_dimensions']),
                 ('threshold', str(bundle.data['threshold'])),
                 ('error_threshold', str(bundle.data['error_threshold'])),
                 ('max_iteration', bundle.data['max_iteration'])
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
                 directive_args, system_settings, request.user.username)

        except InvalidInputError:
            bundle.obj = None

        bundle.obj.pk = run_context.id
        # We do not call obj_create because make_runcontext_for_directive()
        # has already created the object.
        location = self.get_resource_uri(bundle)

        return http.HttpCreated(location=location)
