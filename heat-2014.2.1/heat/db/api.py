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

'''
Interface for database access.

Usage:

    >>> from heat import db
    >>> db.event_get(context, event_id)
    # Event object received

The underlying driver is loaded . SQLAlchemy is currently the only
supported backend.
'''

from oslo.config import cfg
from oslo.db import api

CONF = cfg.CONF


_BACKEND_MAPPING = {'sqlalchemy': 'heat.db.sqlalchemy.api'}

IMPL = api.DBAPI.from_config(CONF, backend_mapping=_BACKEND_MAPPING)


def get_engine():
    return IMPL.get_engine()


def get_session():
    return IMPL.get_session()


def raw_template_get(context, template_id):
    return IMPL.raw_template_get(context, template_id)


def raw_template_create(context, values):
    return IMPL.raw_template_create(context, values)


def raw_template_update(context, template_id, values):
    return IMPL.raw_template_update(context, template_id, values)


def resource_data_get_all(resource, data=None):
    return IMPL.resource_data_get_all(resource, data)


def resource_data_get(resource, key):
    return IMPL.resource_data_get(resource, key)


def resource_data_set(resource, key, value, redact=False):
    return IMPL.resource_data_set(resource, key, value, redact=redact)


def resource_data_get_by_key(context, resource_id, key):
    return IMPL.resource_data_get_by_key(context, resource_id, key)


def resource_data_delete(resource, key):
    """Remove a resource_data element associated to a resource."""
    return IMPL.resource_data_delete(resource, key)


def resource_get(context, resource_id):
    return IMPL.resource_get(context, resource_id)


def resource_get_all(context):
    return IMPL.resource_get_all(context)


def resource_create(context, values):
    return IMPL.resource_create(context, values)


def resource_exchange_stacks(context, resource_id1, resource_id2):
    return IMPL.resource_exchange_stacks(context, resource_id1, resource_id2)


def resource_get_all_by_stack(context, stack_id):
    return IMPL.resource_get_all_by_stack(context, stack_id)


def resource_get_by_name_and_stack(context, resource_name, stack_id):
    return IMPL.resource_get_by_name_and_stack(context,
                                               resource_name, stack_id)


def resource_get_by_physical_resource_id(context, physical_resource_id):
    return IMPL.resource_get_by_physical_resource_id(context,
                                                     physical_resource_id)


def stack_get(context, stack_id, show_deleted=False, tenant_safe=True,
              eager_load=False):
    return IMPL.stack_get(context, stack_id, show_deleted=show_deleted,
                          tenant_safe=tenant_safe,
                          eager_load=eager_load)


def stack_get_by_name_and_owner_id(context, stack_name, owner_id):
    return IMPL.stack_get_by_name_and_owner_id(context, stack_name,
                                               owner_id=owner_id)


def stack_get_by_name(context, stack_name):
    return IMPL.stack_get_by_name(context, stack_name)

#add by xm-20150603
def stack_get_by_app_name(context, app_name):
    return IMPL.stack_get_by_app_name(context, app_name)

def stack_get_all(context, limit=None, sort_keys=None, marker=None,
                  sort_dir=None, filters=None, tenant_safe=True,
                  show_deleted=False, show_nested=False):
    return IMPL.stack_get_all(context, limit, sort_keys,
                              marker, sort_dir, filters, tenant_safe,
                              show_deleted, show_nested)


def stack_get_all_by_owner_id(context, owner_id):
    return IMPL.stack_get_all_by_owner_id(context, owner_id)


def stack_count_all(context, filters=None, tenant_safe=True,
                    show_deleted=False, show_nested=False):
    return IMPL.stack_count_all(context, filters=filters,
                                tenant_safe=tenant_safe,
                                show_deleted=show_deleted,
                                show_nested=show_nested)


def stack_create(context, values):
    return IMPL.stack_create(context, values)    #heat/db/sqlalchemy/api.py  line 396 def stack_create


def stack_update(context, stack_id, values):
    return IMPL.stack_update(context, stack_id, values)


def stack_delete(context, stack_id):
    return IMPL.stack_delete(context, stack_id)


def stack_lock_create(stack_id, engine_id):
    return IMPL.stack_lock_create(stack_id, engine_id)


def stack_lock_steal(stack_id, old_engine_id, new_engine_id):
    return IMPL.stack_lock_steal(stack_id, old_engine_id, new_engine_id)


def stack_lock_release(stack_id, engine_id):
    return IMPL.stack_lock_release(stack_id, engine_id)


def user_creds_create(context):
    return IMPL.user_creds_create(context)   #heat/db/sqlalchemy/api.py  line474 def user_creds_create


def user_creds_delete(context, user_creds_id):
    return IMPL.user_creds_delete(context, user_creds_id)


def user_creds_get(context_id):
    return IMPL.user_creds_get(context_id)


def event_get(context, event_id):
    return IMPL.event_get(context, event_id)


def event_get_all(context):
    return IMPL.event_get_all(context)


def event_get_all_by_tenant(context, limit=None, marker=None,
                            sort_keys=None, sort_dir=None, filters=None):
    return IMPL.event_get_all_by_tenant(context,
                                        limit=limit,
                                        marker=marker,
                                        sort_keys=sort_keys,
                                        sort_dir=sort_dir,
                                        filters=filters)


def event_get_all_by_stack(context, stack_id, limit=None, marker=None,
                           sort_keys=None, sort_dir=None, filters=None):
    return IMPL.event_get_all_by_stack(context, stack_id,
                                       limit=limit,
                                       marker=marker,
                                       sort_keys=sort_keys,
                                       sort_dir=sort_dir,
                                       filters=filters)


def event_count_all_by_stack(context, stack_id):
    return IMPL.event_count_all_by_stack(context, stack_id)


def event_create(context, values):
    return IMPL.event_create(context, values)


def watch_rule_get(context, watch_rule_id):
    return IMPL.watch_rule_get(context, watch_rule_id)


def watch_rule_get_by_name(context, watch_rule_name):
    return IMPL.watch_rule_get_by_name(context, watch_rule_name)


def watch_rule_get_all(context):
    return IMPL.watch_rule_get_all(context)


def watch_rule_get_all_by_stack(context, stack_id):
    return IMPL.watch_rule_get_all_by_stack(context, stack_id)


def watch_rule_create(context, values):
    return IMPL.watch_rule_create(context, values)


def watch_rule_update(context, watch_id, values):
    return IMPL.watch_rule_update(context, watch_id, values)


def watch_rule_delete(context, watch_id):
    return IMPL.watch_rule_delete(context, watch_id)


def watch_data_create(context, values):
    return IMPL.watch_data_create(context, values)


def watch_data_get_all(context):
    return IMPL.watch_data_get_all(context)


def software_config_create(context, values):
    return IMPL.software_config_create(context, values)


def software_config_get(context, config_id):
    return IMPL.software_config_get(context, config_id)


def software_config_delete(context, config_id):
    return IMPL.software_config_delete(context, config_id)


def software_deployment_create(context, values):
    return IMPL.software_deployment_create(context, values)


def software_deployment_get(context, deployment_id):
    return IMPL.software_deployment_get(context, deployment_id)


def software_deployment_get_all(context, server_id=None):
    return IMPL.software_deployment_get_all(context, server_id)


def software_deployment_update(context, deployment_id, values):
    return IMPL.software_deployment_update(context, deployment_id, values)


def software_deployment_delete(context, deployment_id):
    return IMPL.software_deployment_delete(context, deployment_id)


def snapshot_create(context, values):
    return IMPL.snapshot_create(context, values)


def snapshot_get(context, snapshot_id):
    return IMPL.snapshot_get(context, snapshot_id)


def snapshot_update(context, snapshot_id, values):
    return IMPL.snapshot_update(context, snapshot_id, values)


def snapshot_delete(context, snapshot_id):
    return IMPL.snapshot_delete(context, snapshot_id)


def snapshot_get_all(context, stack_id):
    return IMPL.snapshot_get_all(context, stack_id)


def db_sync(engine, version=None):
    """Migrate the database to `version` or the most recent version."""
    return IMPL.db_sync(engine, version=version)


def db_version(engine):
    """Display the current database version."""
    return IMPL.db_version(engine)


def template_create(context, values):

    return IMPL.template_create(context, values)

def template_get_all(context, limit=None, sort_keys=None, offset=None,
                  sort_dir=None, filters=None):
    return IMPL.template_get_all(context, limit, sort_keys, offset, sort_dir, filters)


def template_delete(context, template_id=None):

    return IMPL.template_delete(context, template_id)


def template_get(context, template_id=None):

    return IMPL.template_get(context, template_id)

def template_get_count(context):
    return IMPL.template_get_count(context)


def event_get_all_for_g_cloud(context, limit=None, sort_keys=None, offset=None,
                  sort_dir=None, filters=None):
    return IMPL.event_get_all_for_g_cloud(context, limit, sort_keys, offset, sort_dir, filters)

## heat/db/sqlalchemy/api.py
def stack_get_all_for_g_cloud(context, limit=None, sort_keys=None, offset=None,
                  sort_dir=None, filters=None):
    return IMPL.stack_get_all_for_g_cloud(context, limit, sort_keys, offset, sort_dir, filters)

def data_get_all_for_g_cloud(context, limit=None, sort_keys=None, offset=None,
                  sort_dir=None, filters=None):
    return IMPL.data_get_all_for_g_cloud(context, limit, sort_keys, offset, sort_dir, filters)

def get_stack_name_by_stack_id_for_g_cloud(context,stack_id):
    return IMPL.get_stack_name_by_stack_id_for_g_cloud(context,stack_id)