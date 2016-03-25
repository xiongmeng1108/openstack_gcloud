#
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Heat exception subclasses"""

import functools
import sys

import six
from six.moves.urllib import parse as urlparse

from heat.openstack.common.gettextutils import _
from heat.openstack.common import log as logging


_FATAL_EXCEPTION_FORMAT_ERRORS = False


LOG = logging.getLogger(__name__)


class RedirectException(Exception):
    def __init__(self, url):
        self.url = urlparse.urlparse(url)


class KeystoneError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message

    def __str__(self):
        return "Code: %s, message: %s" % (self.code, self.message)


def wrap_exception(notifier=None, publisher_id=None, event_type=None,
                   level=None):
    """This decorator wraps a method to catch any exceptions that may
    get thrown. It logs the exception as well as optionally sending
    it to the notification system.
    """
    # TODO(sandy): Find a way to import nova.notifier.api so we don't have
    # to pass it in as a parameter. Otherwise we get a cyclic import of
    # nova.notifier.api -> nova.utils -> nova.exception :(
    # TODO(johannes): Also, it would be nice to use
    # utils.save_and_reraise_exception() without an import loop
    def inner(f):
        def wrapped(*args, **kw):
            try:
                return f(*args, **kw)
            except Exception as e:
                # Save exception since it can be clobbered during processing
                # below before we can re-raise
                exc_info = sys.exc_info()

                if notifier:
                    payload = dict(args=args, exception=e)
                    payload.update(kw)

                    # Use a temp vars so we don't shadow
                    # our outer definitions.
                    temp_level = level
                    if not temp_level:
                        temp_level = notifier.ERROR

                    temp_type = event_type
                    if not temp_type:
                        # If f has multiple decorators, they must use
                        # functools.wraps to ensure the name is
                        # propagated.
                        temp_type = f.__name__

                    notifier.notify(publisher_id, temp_type, temp_level,
                                    payload)

                # re-raise original exception since it may have been clobbered
                raise exc_info[0], exc_info[1], exc_info[2]

        return functools.wraps(f)(wrapped)
    return inner


class HeatException(Exception):
    """Base Heat Exception

    To correctly use this class, inherit from it and define
    a 'msg_fmt' property. That msg_fmt will get printf'd
    with the keyword arguments provided to the constructor.

    """
    message = _("An unknown exception occurred.")

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        try:
            self.message = self.msg_fmt % kwargs
            self.params = []
            self._define_params_for_error_code(kwargs, self.params)
        except KeyError:
            exc_info = sys.exc_info()
            #kwargs doesn't match a variable in the message
            #log the issue and the kwargs
            LOG.exception(_('Exception in string format operation'))
            for name, value in six.iteritems(kwargs):
                LOG.error("%s: %s" % (name, value))  # noqa

            if _FATAL_EXCEPTION_FORMAT_ERRORS:
                raise exc_info[0], exc_info[1], exc_info[2]

    def _define_params_for_error_code(self, kwargs, params):
        if kwargs:
            for name, value in six.iteritems(kwargs):
                params.append(value)

    def __str__(self):
        return unicode(self.message).encode('UTF-8')

    def __unicode__(self):
        return unicode(self.message)

    def __deepcopy__(self, memo):
        return self.__class__(**self.kwargs)


class MissingCredentialError(HeatException):
    msg_fmt = _("Missing required credential: %(required)s")
    code = 'heat_server_common_000001'


class BadAuthStrategy(HeatException):
    msg_fmt = _("Incorrect auth strategy, expected \"%(expected)s\" but "
                "received \"%(received)s\"")
    code = 'heat_server_common_000002'


class AuthBadRequest(HeatException):
    msg_fmt = _("Connect error/bad request to Auth service at URL %(url)s.")
    code = 'heat_server_common_000003'


class AuthUrlNotFound(HeatException):
    msg_fmt = _("Auth service at URL %(url)s not found.")
    code = 'heat_server_common_000004'

class AuthorizationFailure(HeatException):
    msg_fmt = _("Authorization failed.")
    code = 'heat_server_common_000005'


class NotAuthenticated(HeatException):
    msg_fmt = _("You are not authenticated.")
    code = 'heat_server_common_000006'



class Forbidden(HeatException):
    msg_fmt = _("You are not authorized to complete this action.")
    code = 'heat_server_common_000007'

#NOTE(bcwaldon): here for backwards-compatibility, need to deprecate.
class NotAuthorized(Forbidden):
    msg_fmt = _("You are not authorized to complete this action.")
    code = 'heat_server_common_000008'

class Invalid(HeatException):
    msg_fmt = _("Data supplied was not valid: %(reason)s")
    code = 'heat_server_common_000009'

class AuthorizationRedirect(HeatException):
    msg_fmt = _("Redirecting to %(uri)s for authorization.")
    code = 'heat_server_common_000010'

class RequestUriTooLong(HeatException):
    msg_fmt = _("The URI was too long.")
    code = 'heat_server_common_000011'


class MaxRedirectsExceeded(HeatException):
    msg_fmt = _("Maximum redirects (%(redirects)s) was exceeded.")
    code = 'heat_server_common_000012'


class InvalidRedirect(HeatException):
    msg_fmt = _("Received invalid HTTP redirect.")
    code = 'heat_server_common_000013'

class RegionAmbiguity(HeatException):
    msg_fmt = _("Multiple 'image' service matches for region %(region)s. This "
                "generally means that a region is required and you have not "
                "supplied one.")
    code = 'heat_server_common_000014'


class UserParameterMissing(HeatException):
    msg_fmt = _("The Parameter (%(key)s) was not provided.")
    code = 'heat_server_common_000015'

class UnknownUserParameter(HeatException):
    msg_fmt = _("The Parameter (%(key)s) was not defined in template.")
    code = 'heat_server_template_000001'

class InvalidTemplateVersion(HeatException):
    msg_fmt = _("The template version is invalid: %(explanation)s")
    code = 'heat_server_template_000002'

class InvalidTemplateSection(HeatException):
    msg_fmt = _("The template section is invalid: %(section)s")
    code = 'heat_server_template_000003'


class InvalidTemplateParameter(HeatException):
    msg_fmt = _("The Parameter (%(key)s) has no attributes.")
    code = 'heat_server_template_000004'


class InvalidTemplateAttribute(HeatException):
    msg_fmt = _("The Referenced Attribute (%(resource)s %(key)s)"
                " is incorrect.")
    code = 'heat_server_template_000005'


class InvalidTemplateReference(HeatException):
    msg_fmt = _("The specified reference \"%(resource)s\" (in %(key)s)"
                " is incorrect.")
    code = 'heat_server_template_000006'


class UserKeyPairMissing(HeatException):
    msg_fmt = _("The Key (%(key_name)s) could not be found.")
    code = 'heat_server_common_000016'

class FlavorMissing(HeatException):
    msg_fmt = _("The Flavor ID (%(flavor_id)s) could not be found.")
    code = 'heat_server_common_000017'

class ImageNotFound(HeatException):
    msg_fmt = _("The Image (%(image_name)s) could not be found.")
    code = 'heat_server_common_000018'

class PhysicalResourceNameAmbiguity(HeatException):
    msg_fmt = _(
        "Multiple physical resources were found with name (%(name)s).")
    code = 'heat_server_common_000019'


class InvalidTenant(HeatException):
    msg_fmt = _("Searching Tenant %(target)s "
                "from Tenant %(actual)s forbidden.")
    code = 'heat_server_common_000020'

class StackNotFound(HeatException):
    msg_fmt = _("The Stack (%(stack_name)s) could not be found.")
    code = 'heat_server_stack_000001'


class StackExists(HeatException):
    msg_fmt = _("The Stack (%(stack_name)s) already exists.")
    code = 'heat_server_stack_000002'

#add by xm-20150603
class StackExistsAppName(HeatException):
    msg_fmt = _("The Stack which app_name is (%(app_name)s) already exists.")
    code = 'heat_server_stack_000003'

#add by xm-20150603
class StackAppNameIsNone(HeatException):
    msg_fmt = _("The app_name can not be None, must be assign")
    code = 'heat_server_stack_000004'

class StackValidationFailed(HeatException):
    msg_fmt = _("%(message)s")
    code = 'heat_server_stack_000005'

class InvalidSchemaError(HeatException):
    msg_fmt = _("%(message)s")
    code = 'heat_server_common_000021'


class ResourceNotFound(HeatException):
    msg_fmt = _("The Resource (%(resource_name)s) could not be found "
                "in Stack %(stack_name)s.")
    code = 'heat_server_resource_000001'


class ResourceTypeNotFound(HeatException):
    msg_fmt = _("The Resource Type (%(type_name)s) could not be found.")
    code = 'heat_server_resource_000002'


class ResourceNotAvailable(HeatException):
    msg_fmt = _("The Resource (%(resource_name)s) is not available.")
    code = 'heat_server_resource_000003'


class PhysicalResourceNotFound(HeatException):
    msg_fmt = _("The Resource (%(resource_id)s) could not be found.")
    code = 'heat_server_resource_000004'

class WatchRuleNotFound(HeatException):
    msg_fmt = _("The Watch Rule (%(watch_name)s) could not be found.")
    code = 'heat_server_common_000022'


class ResourceFailure(HeatException):
    msg_fmt = _("%(exc_type)s: %(message)s")

    def __init__(self, exception, resource, action=None):
        if isinstance(exception, ResourceFailure):
            exception = getattr(exception, 'exc', exception)
        self.exc = exception
        self.resource = resource
        self.action = action
        exc_type = type(exception).__name__
        super(ResourceFailure, self).__init__(exc_type=exc_type,
                                              message=six.text_type(exception))


class NotSupported(HeatException):
    msg_fmt = _("%(feature)s is not supported.")
    code = 'heat_server_common_000023'


class ResourceActionNotSupported(HeatException):
    msg_fmt = _("%(action)s is not supported for resource.")
    code = 'heat_server_resource_000005'


class ResourcePropertyConflict(HeatException):
    msg_fmt = _('Cannot define the following properties at the same time: %s.')

    def __init__(self, *args):
        self.msg_fmt = self.msg_fmt % ", ".join(args)
        super(ResourcePropertyConflict, self).__init__()


class HTTPExceptionDisguise(Exception):
    """Disguises HTTP exceptions so they can be handled by the webob fault
    application in the wsgi pipeline.
    """

    def __init__(self, exception):
        self.exc = exception
        self.tb = sys.exc_info()[2]


class EgressRuleNotAllowed(HeatException):
    msg_fmt = _("Egress rules are only allowed when "
                "Neutron is used and the 'VpcId' property is set.")
    code = 'heat_server_common_000024'


class Error(HeatException):
    msg_fmt = "%(message)s"

    def __init__(self, msg):
        super(Error, self).__init__(message=msg)


class NotFound(HeatException):
    def __init__(self, msg_fmt=_('Not found')):
        self.msg_fmt = msg_fmt
        super(NotFound, self).__init__()


class InvalidContentType(HeatException):
    msg_fmt = _("Invalid content type %(content_type)s")
    code = 'heat_server_common_000025'

class RequestLimitExceeded(HeatException):
    msg_fmt = _('Request limit exceeded: %(message)s')
    code = 'heat_server_common_000026'

class StackResourceLimitExceeded(HeatException):
    msg_fmt = _('Maximum resources per stack exceeded.')
    code = 'heat_server_stack_000006'


class ActionInProgress(HeatException):
    msg_fmt = _("Stack %(stack_name)s already has an action (%(action)s) "
                "in progress.")
    code = 'heat_server_stack_000007'


class StopActionFailed(HeatException):
    msg_fmt = _("Failed to stop stack (%(stack_name)s) on other engine "
                "(%(engine_id)s)")
    code = 'heat_server_stack_000008'


class EventSendFailed(HeatException):
    msg_fmt = _("Failed to send message to stack (%(stack_name)s) "
                "on other engine (%(engine_id)s)")
    code = 'heat_server_stack_000009'

class TemplateNotFound(HeatException):
    msg_fmt = _("Failed to found template (%(template_id)s) ")
    code = 'heat_server_template_000007'


class ServiceUrlNotFound(HeatException):
    msg_fmt = _("Failed to found service url because  (%(text)s) ")
    code = 'heat_server_stack_000010'

class ClientRequestException(HeatException):
    msg_fmt = _("request (%(text)s)  error ")
    code = 'heat_server_stack_client_000001'

class GcloudTemplateRequestInvalid(HeatException):
    msg_fmt = _("request (%(input)s) is invalid")
    code = 'gcloud_template_000001'