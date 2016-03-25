# -*- coding:utf-8 -*-
__author__ = 'zhangyk'
from heat.common import wsgi
from heat.common import serializers
from heat.openstack.common import log as logging
from heat.db.sqlalchemy import models
from heat.db import api as db_api
from heat.api.openstack.v1 import util
from heat.common.i18n import _
import copy
import json
import datetime
import six
from webob import exc
from heat.db import api as db_api
import pytz
from pytz import timezone
LOG = logging.getLogger(__name__)


def format_events_response(events):
    response = {"events": []}
    for e in events:
        e_dict = {
            "app_name": e.stack.app_name,
            "resource_name": e.resource_name,
            "resource_status": e.resource_status,
            "event_time": e.created_at.replace(tzinfo=pytz.utc).astimezone
            (timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S"),
            "resource_status_reason": e.resource_status_reason


        }
        response["events"].append(e_dict)

    return response

def change_status(stack_status, stack_action=None, flag="req"):
    if flag == 'req':
        if stack_status == 'running':
            status = 'COMPLETE'
        elif stack_status == 'failed':
            status = 'FAILED'
        elif stack_status == 'progress':
            status = 'IN_PROGRESS'
        elif stack_status == 'suspend':
            status = 'COMPLETE'
        else:
            status = stack_status
    elif flag == 'resp':
        if stack_status == 'COMPLETE'and (stack_action == 'CREATE' or stack_action == 'UPDATE' or stack_action == 'RESUME'):
            status = 'running'
        elif stack_status == 'FAILED':
            status = 'failed'
        elif stack_status == 'IN_PROGRESS':
            status = 'progress'
        elif stack_status == 'COMPLETE'and stack_action == 'SUSPEND':
            status = 'suspend'
        else:
            status = stack_status
    return status


def format_stacks_response(stacks):
    response = {"stacks": []}
     ### uncommit at 2015.9.2---begin---
    total_stacks = 0
    total_scalar_stack = 0
    ### uncommit at 2015.9.2---end---
    for e in stacks:
        e_dict = {
            "id": e.id,
            "stack_name": e.name,
            "app_name": e.app_name,
            "stack_apps_style": e.stack_apps_style,
            "isscaler": e.isscaler,
            "description": e.description,
            "created_at": e.created_at.replace(tzinfo=pytz.utc).astimezone
            (timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S"),
            "stack_status": change_status(e.status, stack_action=e.action, flag='resp'),
            "stack_owner": e.username,
            "enduser": e.enduser,
            "template_id": e.template_id,
        }
        ### uncommit at 2015.9.2---begin---
        total_stacks += 1
        if e.isscaler:
            total_scalar_stack += 1
        ### uncommit at 2015.9.2---end---
        response["stacks"].append(e_dict)
    ### uncommit at 2015.9.2---begin---
    response.update({"total_stacks": total_stacks, "total_scalar_stack": total_scalar_stack})
    ### uncommit at 2015.9.2---end---
    return response

def string_to_datetime(string):
    try:
        time = datetime.datetime.strptime(string, "%Y-%m-%dT%H:%M:%S")
    except Exception,msg:
        raise exc.HTTPBadRequest(_(msg))
    return time


def validate_and_translate(filter_params):
    created_time_first=filter_params.get("create_time_first",None)
    created_time_end=filter_params.get("create_time_end", None)
    if created_time_first:
        created_time_first = string_to_datetime(created_time_first)
    if created_time_end:
        created_time_end = string_to_datetime(created_time_end)

    if created_time_first and created_time_end:
        if created_time_first > created_time_end:
            LOG.error(_("created_time_first is greater than  created_time_end"))
            raise exc.HTTPBadRequest(_("created_time_first is greater than  created_time_end"))

    # do translate
    new_filters = {}
    for key, value in six.iteritems(filter_params):
        if key == 'create_time_first':
            new_filters['create_time_first'] = created_time_first
        if key == "create_time_end":
            new_filters['create_time_end'] = created_time_end
        if key == "stack_status":
            stack_status = filter_params.get("stack_status")
            #当stack_status为suspend时，需要2个刷选条件:status=COMPLETE,action in ['SUSPEND']
            if stack_status == 'suspend':
                new_filters.update({'action': ['SUSPEND']})
            #当stack_status为running时，需要2个刷选条件:status=COMPLETE,action in ['CREATE', 'UPDATE', 'RESUME']
            if stack_status == 'running':
                new_filters.update({'action': ['CREATE', 'UPDATE', 'RESUME']})
            new_filters.update({"stack_status": change_status(stack_status, flag='req')})
        else:
            new_filters[key] = value

    return new_filters



def event_list_from_db(req):
    filter_whitelist = {
         'create_time_first': 'single',
         'create_time_end': 'single',
         'app_name': 'single',
         'stack_id': 'single',
         'stack_apps_style': 'single',
         'resource_status': 'single'
        }
    whitelist = {
         'limit': 'single',
         'offset': 'single',
         'sort_dir': 'single',
         'sort_keys': 'multi',
    }
    params = util.get_allowed_params(req.params, whitelist)
    filter_params = util.get_allowed_params(req.params, filter_whitelist)
    return db_api.event_get_all_for_g_cloud(req.context, filters=validate_and_translate(filter_params), **params)

def stack_list_from_db(req):
    filter_whitelist = {
         'id': 'single',
         'create_time_first': 'single',
         'create_time_end': 'single',
         'app_name': 'single',
         'stack_apps_style': 'single',
         'stack_status': 'single'
        }
    whitelist = {
         'limit': 'single',
         'offset': 'single',
         'sort_dir': 'single',
         'sort_keys': 'multi',
    }
    params = util.get_allowed_params(req.params, whitelist)
    filter_params = util.get_allowed_params(req.params, filter_whitelist)
    return db_api.stack_get_all_for_g_cloud(req.context, filters=validate_and_translate(filter_params), **params)

def data_list_from_db(req):
    filter_whitelist = {
         'create_time_first': 'single',
         'create_time_end': 'single',
         'app_name': 'single',
         'stack_apps_style': 'single',
         'stack_status': 'single'
        }
    whitelist = {
         'limit': 'single',
         'offset': 'single',
         'sort_dir': 'single',
         'sort_keys': 'multi',
    }
    params = util.get_allowed_params(req.params, whitelist)
    filter_params = util.get_allowed_params(req.params, filter_whitelist)
    return db_api.data_get_all_for_g_cloud(req.context, filters=validate_and_translate(filter_params), **params)

def get_stack_name_by_stack_id(req, stack_id):
    return db_api.get_stack_name_by_stack_id_for_g_cloud(req.context,stack_id)