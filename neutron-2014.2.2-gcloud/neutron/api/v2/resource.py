# -*- coding:utf-8 -*-
# Copyright 2012 OpenStack Foundation.
# All Rights Reserved.
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

"""
Utility methods for working with WSGI servers redux
"""

import sys

import netaddr
import six
import webob.dec
import webob.exc

from neutron.api.v2 import attributes
from neutron.common import exceptions
from neutron.openstack.common import gettextutils
from neutron.openstack.common import log as logging
from neutron import wsgi
#from dbgp.client import brk
#import pdb


LOG = logging.getLogger(__name__)


class Request(wsgi.Request):
    pass


def Resource(controller, faults=None, deserializers=None, serializers=None):
    """Represents an API entity resource and the associated serialization and
    deserialization logic
    """
    xml_deserializer = wsgi.XMLDeserializer(attributes.get_attr_metadata())
    default_deserializers = {'application/xml': xml_deserializer,
                             'application/json': wsgi.JSONDeserializer()}
    xml_serializer = wsgi.XMLDictSerializer(attributes.get_attr_metadata())
    default_serializers = {'application/xml': xml_serializer,
                           'application/json': wsgi.JSONDictSerializer()}
    format_types = {'xml': 'application/xml',
                    'json': 'application/json'}
    action_status = dict(create=201, delete=204)

    default_deserializers.update(deserializers or {})
    default_serializers.update(serializers or {})

    deserializers = default_deserializers
    serializers = default_serializers
    faults = faults or {}
    #neutron/api/v2/base.py 789 wsgi_resource.Resource(controller, FAULT_MAP)
    #FAULT_MAP :neutron/api/v2/base.py 38

    @webob.dec.wsgify(RequestClass=Request)
    def resource(request):
        # #brk(host="10.10.12.21", port=49175)
        # #add by xm-2015.7.8：G-cloud7.0区域权限控制，
        # #根据api请求中是否附件resource_type及是否resource_type=0/1来区分用户角色
        # #resource_type = request.params.get('resource_type', None)
        # resource_type = request.environ.get('HTTP_G_AUTH_RESOURCETYPE', None)
        # #resource_type = request.headers.environ.get('HTTP_G_AUTH_RESOURCETYPE', None)
        # LOG.debug(_('resource_type_xm: %(resource_type)s'), {'resource_type': resource_type})
        # if resource_type == '0':
        #     request.context.roles = list(set(request.context.roles) - set(['admin']))
        #     request.context.is_admin = False
        # elif resource_type == '1':
        #     request.context.roles = list(set(request.context.roles) | set(['admin']))
        #     request.context.is_admin = True
        # #end-2015.7.8

        route_args = request.environ.get('wsgiorg.routing_args')
        if route_args:
            args = route_args[1].copy()
        else:
            args = {}

        # NOTE(jkoelker) by now the controller is already found, remove
        #                it from the args if it is in the matchdict
        args.pop('controller', None)
        fmt = args.pop('format', None)
        action = args.pop('action', None)
        content_type = format_types.get(fmt,
                                        request.best_match_content_type())
        language = request.best_match_language()
        deserializer = deserializers.get(content_type)
        serializer = serializers.get(content_type)

        try:
            if request.body:
                args['body'] = deserializer.deserialize(request.body)['body']
                #首先进入/usr/lib/python2.7/site-packages/webob/request.py(671)_body__get() 然后return 到/usr/lib/python2.7/site-packages/neutron/wsgi.py(599)deserialize()

            method = getattr(controller, action)
            #pdb.set_trace()
            result = method(request=request, **args)
        except (exceptions.NeutronException,
                netaddr.AddrFormatError) as e:
            #faults = {<class 'neutron.common.exceptions.NotAuthorized'>: <class 'webob.exc.HTTPForbidden'>,
            # <class 'neutron.common.exceptions.Conflict'>: <class 'webob.exc.HTTPConflict'>,
            # <class 'neutron.common.exceptions.NotFound'>: <class 'webob.exc.HTTPNotFound'>,
            # <class 'neutron.common.exceptions.ServiceUnavailable'>: <class 'webob.exc.HTTPServiceUnavailable'>,
            # <class 'netaddr.core.AddrFormatError'>: <class 'webob.exc.HTTPBadRequest'>,
            # <class 'neutron.common.exceptions.BadRequest'>: <class 'webob.exc.HTTPBadRequest'>,
            # <class 'neutron.common.exceptions.InUse'>: <class 'webob.exc.HTTPConflict'>}
            for fault in faults:
                if isinstance(e, fault):
                    mapped_exc = faults[fault]
                    break
            else:
                if e.code and e.code != 500:
                    mapped_exc = webob.exc.HTTPClientError
                else:
                    mapped_exc = webob.exc.HTTPInternalServerError
            if 400 <= mapped_exc.code < 500:
                LOG.info(_('%(action)s failed (client error): %(exc)s'),
                         {'action': action, 'exc': e})
            else:
                LOG.exception(_('%s failed'), action)
            e = translate(e, language)
            body = serializer.serialize(
                {'NeutronError': get_exception_data(e)})
            kwargs = {'body': body, 'content_type': content_type}
            raise mapped_exc(**kwargs)
        except webob.exc.HTTPException as e:
            type_, value, tb = sys.exc_info()
            LOG.exception(_('%s failed'), action)
            translate(e, language)
            value.body = serializer.serialize(
                {'NeutronError': get_exception_data(e)})
            value.content_type = content_type
            six.reraise(type_, value, tb)
        except NotImplementedError as e:
            e = translate(e, language)
            # NOTE(armando-migliaccio): from a client standpoint
            # it makes sense to receive these errors, because
            # extensions may or may not be implemented by
            # the underlying plugin. So if something goes south,
            # because a plugin does not implement a feature,
            # returning 500 is definitely confusing.
            body = serializer.serialize(
                {'NotImplementedError': get_exception_data(e)})
            kwargs = {'body': body, 'content_type': content_type}
            raise webob.exc.HTTPNotImplemented(**kwargs)
        except Exception:
            # NOTE(jkoelker) Everything else is 500
            LOG.exception(_('%s failed'), action)
            # Do not expose details of 500 error to clients.
            msg = _('Request Failed: internal server error while '
                    'processing your request.')
            msg = translate(msg, language)
            body = serializer.serialize(
                {'NeutronError': get_exception_data(
                    webob.exc.HTTPInternalServerError(msg))})
            kwargs = {'body': body, 'content_type': content_type}
            raise webob.exc.HTTPInternalServerError(**kwargs)

        status = action_status.get(action, 200)
        body = serializer.serialize(result)
        # NOTE(jkoelker) Comply with RFC2616 section 9.7
        if status == 204:
            content_type = ''
            body = None

        return webob.Response(request=request, status=status,
                              content_type=content_type,
                              body=body)
    return resource


def get_exception_data(e):
    """Extract the information about an exception.

    Neutron client for the v2 API expects exceptions to have 'type', 'message'
    and 'detail' attributes.This information is extracted and converted into a
    dictionary.

    :param e: the exception to be reraised
    :returns: a structured dict with the exception data
    """
    err_data=None
    if getattr(e,"code",None) is not None:
        err_data = {'type': e.__class__.__name__,
                'message': e, 'detail': '','code':e.code}
    else:
        err_data = {'type': e.__class__.__name__,
                'message': e, 'detail': ''}
    return err_data


def translate(translatable, locale):
    """Translates the object to the given locale.

    If the object is an exception its translatable elements are translated
    in place, if the object is a translatable string it is translated and
    returned. Otherwise, the object is returned as-is.

    :param translatable: the object to be translated
    :param locale: the locale to translate to
    :returns: the translated object, or the object as-is if it
              was not translated
    """
    localize = gettextutils.translate
    if isinstance(translatable, exceptions.NeutronException):
        translatable.msg = localize(translatable.msg, locale)
    elif isinstance(translatable, webob.exc.HTTPError):
        translatable.detail = localize(translatable.detail, locale)
    elif isinstance(translatable, Exception):
        translatable.message = localize(translatable.message, locale)
    else:
        return localize(translatable, locale)
    return translatable
