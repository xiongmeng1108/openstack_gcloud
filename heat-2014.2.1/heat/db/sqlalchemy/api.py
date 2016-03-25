# -*- coding:utf-8 -*-
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

'''Implementation of SQLAlchemy backend.'''
from datetime import datetime
from datetime import timedelta
import sys
#from dbgp.client import brk
from oslo.config import cfg
from oslo.db.sqlalchemy import session as db_session
from oslo.db.sqlalchemy import utils
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy.orm.session import Session

from heat.common import crypt
from heat.common import exception
from heat.common.i18n import _
from heat.db.sqlalchemy import filters as db_filters
from heat.db.sqlalchemy import migration
from heat.db.sqlalchemy import models
from heat.rpc import api as rpc_api
import six
from sqlalchemy import func, or_, not_, and_
from heat.openstack.common import log as logging
LOG = logging.getLogger(__name__)

CONF = cfg.CONF
CONF.import_opt('max_events_per_stack', 'heat.common.config')

_facade = None


def get_facade():
    global _facade

    if not _facade:
        _facade = db_session.EngineFacade.from_config(CONF)
    return _facade

get_engine = lambda: get_facade().get_engine()
get_session = lambda: get_facade().get_session()


def get_backend():
    """The backend is this module itself."""
    return sys.modules[__name__]


def model_query(context, *args):
    session = _session(context)
    query = session.query(*args)
    return query


def soft_delete_aware_query(context, *args, **kwargs):
    """Stack query helper that accounts for context's `show_deleted` field.

    :param show_deleted: if True, overrides context's show_deleted field.
    """

    query = model_query(context, *args)
    show_deleted = kwargs.get('show_deleted') or context.show_deleted
    #LOG.warn(_("ssss context.show_deleted=%s, show_deleted=%s"),context.show_deleted,show_deleted)
    if not show_deleted:
        query = query.filter_by(deleted_at=None)
    return query


def _session(context):
    return (context and context.session) or get_session()


def raw_template_get(context, template_id):
    result = model_query(context, models.RawTemplate).get(template_id)

    if not result:
        raise exception.NotFound(_('raw template with id %s not found') %
                                 template_id)
    return result


def raw_template_create(context, values):
    raw_template_ref = models.RawTemplate()
    raw_template_ref.update(values)
    raw_template_ref.save(_session(context))
    return raw_template_ref


def raw_template_update(context, template_id, values):
    raw_template_ref = raw_template_get(context, template_id)
    # get only the changed values
    values = dict((k, v) for k, v in values.items()
                  if getattr(raw_template_ref, k) != v)

    if values:
        raw_template_ref.update_and_save(values)

    return raw_template_ref


def resource_get(context, resource_id):
    result = model_query(context, models.Resource).get(resource_id)

    if not result:
        raise exception.NotFound(_("resource with id %s not found") %
                                 resource_id)
    return result


def resource_get_by_name_and_stack(context, resource_name, stack_id):
    result = model_query(context, models.Resource).\
        filter_by(name=resource_name).\
        filter_by(stack_id=stack_id).\
        options(orm.joinedload("data")).first()
    return result


def resource_get_by_physical_resource_id(context, physical_resource_id):
    results = (model_query(context, models.Resource)
               .filter_by(nova_instance=physical_resource_id)
               .all())

    for result in results:
        if context is None or context.tenant_id in (
                result.stack.tenant, result.stack.stack_user_project_id):
            return result
    return None


def resource_get_all(context):
    results = model_query(context, models.Resource).all()

    if not results:
        raise exception.NotFound(_('no resources were found'))
    return results


def resource_data_get_all(resource, data=None):
    """
    Looks up resource_data by resource.id.  If data is encrypted,
    this method will decrypt the results.
    """
    if data is None:
        data = (model_query(resource.context, models.ResourceData)
                .filter_by(resource_id=resource.id))

    if not data:
        raise exception.NotFound(_('no resource data found'))

    ret = {}

    for res in data:
        if res.redact:
            ret[res.key] = _decrypt(res.value, res.decrypt_method)
        else:
            ret[res.key] = res.value
    return ret


def resource_data_get(resource, key):
    """Lookup value of resource's data by key. Decrypts resource data if
    necessary.
    """
    result = resource_data_get_by_key(resource.context,
                                      resource.id,
                                      key)
    if result.redact:
        return _decrypt(result.value, result.decrypt_method)
    return result.value


def _encrypt(value):
    if value is not None:
        return crypt.encrypt(value.encode('utf-8'))
    else:
        return None, None


def _decrypt(enc_value, method):
    if method is None:
        return None
    decryptor = getattr(crypt, method)
    value = decryptor(enc_value)
    if value is not None:
        return unicode(value, 'utf-8')


def resource_data_get_by_key(context, resource_id, key):
    """Looks up resource_data by resource_id and key. Does not unencrypt
    resource_data.
    """
    result = (model_query(context, models.ResourceData)
              .filter_by(resource_id=resource_id)
              .filter_by(key=key).first())

    if not result:
        raise exception.NotFound(_('No resource data found'))
    return result


def resource_data_set(resource, key, value, redact=False):
    """Save resource's key/value pair to database."""
    if redact:
        method, value = _encrypt(value)
    else:
        method = ''
    try:
        current = resource_data_get_by_key(resource.context, resource.id, key)
    except exception.NotFound:
        current = models.ResourceData()
        current.key = key
        current.resource_id = resource.id
    current.redact = redact
    current.value = value
    current.decrypt_method = method
    current.save(session=resource.context.session)
    return current


def resource_exchange_stacks(context, resource_id1, resource_id2):
    query = model_query(context, models.Resource)
    session = query.session
    session.begin()

    res1 = query.get(resource_id1)
    res2 = query.get(resource_id2)

    res1.stack, res2.stack = res2.stack, res1.stack

    session.commit()


def resource_data_delete(resource, key):
    result = resource_data_get_by_key(resource.context, resource.id, key)
    result.delete()


def resource_create(context, values):
    resource_ref = models.Resource()
    resource_ref.update(values)
    resource_ref.save(_session(context))
    return resource_ref


def resource_get_all_by_stack(context, stack_id):
    results = model_query(context, models.Resource).\
        filter_by(stack_id=stack_id).\
        options(orm.joinedload("data")).all()

    if not results:
        raise exception.NotFound(_("no resources for stack_id %s were found")
                                 % stack_id)
    return dict((res.name, res) for res in results)


def stack_get_by_name_and_owner_id(context, stack_name, owner_id):
    query = soft_delete_aware_query(context, models.Stack).\
        filter(sqlalchemy.or_(
            models.Stack.tenant == context.tenant_id,
            models.Stack.stack_user_project_id == context.tenant_id
        )).\
        filter_by(name=stack_name).\
        filter_by(owner_id=owner_id)
    return query.first()


def stack_get_by_name(context, stack_name):
    query = soft_delete_aware_query(context, models.Stack).\
        filter(sqlalchemy.or_(
            models.Stack.tenant == context.tenant_id,
            models.Stack.stack_user_project_id == context.tenant_id
        )).\
        filter_by(name=stack_name)
    return query.first()

#add by xm-20150603
def stack_get_by_app_name(context, app_name):
    query = soft_delete_aware_query(context, models.Stack).\
        filter(sqlalchemy.or_(
            models.Stack.tenant == context.tenant_id,
            models.Stack.stack_user_project_id == context.tenant_id
        )).\
        filter_by(app_name=app_name)
    return query.first()

def stack_get(context, stack_id, show_deleted=False, tenant_safe=True,
              eager_load=False):
    query = model_query(context, models.Stack)
    if eager_load:
        query = query.options(orm.joinedload("raw_template"))
    result = query.get(stack_id)

    deleted_ok = show_deleted or context.show_deleted
    if result is None or result.deleted_at is not None and not deleted_ok:
        return None

    # One exception to normal project scoping is users created by the
    # stacks in the stack_user_project_id (in the heat stack user domain)
    if (tenant_safe and result is not None and context is not None and
        context.tenant_id not in (result.tenant,
                                  result.stack_user_project_id)):
        return None
    return result


def stack_get_all_by_owner_id(context, owner_id):
    results = soft_delete_aware_query(context, models.Stack).\
        filter_by(owner_id=owner_id).all()
    return results


def _get_sort_keys(sort_keys, mapping):
    '''Returns an array containing only whitelisted keys

    :param sort_keys: an array of strings
    :param mapping: a mapping from keys to DB column names
    :returns: filtered list of sort keys
    '''
    if isinstance(sort_keys, basestring):
        sort_keys = [sort_keys]
    return [mapping[key] for key in sort_keys or [] if key in mapping]


def _paginate_query(context, query, model, limit=None, sort_keys=None,
                    marker=None, sort_dir=None, offset=None):
    default_sort_keys = ['created_at']
    if not sort_keys:
        sort_keys = default_sort_keys
        if not sort_dir:
            sort_dir = 'desc'

    # This assures the order of the stacks will always be the same
    # even for sort_key values that are not unique in the database
    sort_keys = sort_keys + ['id']

    model_marker = None
    if marker:
        model_marker = model_query(context, model).get(marker)

    try:
        query = utils.paginate_query(query, model, None, sort_keys,
                                     model_marker, sort_dir)
        if offset is not None:
            query=query.offset(offset)


    except utils.InvalidSortKey as exc:
        raise exception.Invalid(reason=exc.message)

    if limit is not None:
        return query.limit(limit)

    else:
        return query


def _query_stack_get_all(context, tenant_safe=True, show_deleted=False,
                         show_nested=False):
    if show_nested:
        query = soft_delete_aware_query(context, models.Stack,
                                        show_deleted=show_deleted).\
            filter_by(backup=False)
    else:
        query = soft_delete_aware_query(context, models.Stack,
                                        show_deleted=show_deleted).\
            filter_by(owner_id=None)

    if tenant_safe:
        query = query.filter_by(tenant=context.tenant_id)
    return query

def _query_stack_get_all_gcloud(context, tenant_safe=True, show_deleted=False,
                         show_nested=False, isscaler=False):
    if show_nested:
        query = soft_delete_aware_query(context, models.Stack,
                                        show_deleted=show_deleted).\
            filter_by(backup=False)
    else:
        query = soft_delete_aware_query(context, models.Stack,
                                        show_deleted=show_deleted).\
            filter_by(owner_id=None)

    if tenant_safe:
        query = query.filter_by(tenant=context.tenant_id)

    if isscaler:
        query = query.filter_by(isscaler=True)
    if "admin" not in context.roles:
        query = query.filter_by(username=context.username)
    return query

def stack_get_all(context, limit=None, sort_keys=None, marker=None,
                  sort_dir=None, filters=None, tenant_safe=True,
                  show_deleted=False, show_nested=False):
    query = _query_stack_get_all(context, tenant_safe,
                                 show_deleted=show_deleted,
                                 show_nested=show_nested)
    return _filter_and_page_query(context, query, limit, sort_keys,
                                  marker, sort_dir, filters).all()


def _filter_and_page_query(context, query, limit=None, sort_keys=None,
                           marker=None, sort_dir=None, filters=None):
    if filters is None:
        filters = {}

    sort_key_map = {rpc_api.STACK_NAME: models.Stack.name.key,
                    rpc_api.STACK_STATUS: models.Stack.status.key,
                    rpc_api.STACK_CREATION_TIME: models.Stack.created_at.key,
                    rpc_api.STACK_UPDATED_TIME: models.Stack.updated_at.key}
    whitelisted_sort_keys = _get_sort_keys(sort_keys, sort_key_map)

    query = db_filters.exact_filter(query, models.Stack, filters)
    return _paginate_query(context, query, models.Stack, limit,
                           whitelisted_sort_keys, marker, sort_dir)


def stack_count_all(context, filters=None, tenant_safe=True,
                    show_deleted=False, show_nested=False):
    query = _query_stack_get_all(context, tenant_safe=tenant_safe,
                                 show_deleted=show_deleted,
                                 show_nested=show_nested)
    query = db_filters.exact_filter(query, models.Stack, filters)
    return query.count()

def stack_count_all_gcloud(context, filters=None, tenant_safe=True,
                    show_deleted=False, show_nested=False, isscaler=False):
    query = _query_stack_get_all_gcloud(context, tenant_safe=tenant_safe,
                                 show_deleted=show_deleted,
                                 show_nested=show_nested,
                                 isscaler=isscaler)
    query = db_filters.exact_filter(query, models.Stack, filters)
    return query.count()

def stack_create(context, values):
    stack_ref = models.Stack()
    stack_ref.update(values)
    stack_ref.save(_session(context))
    return stack_ref


def stack_update(context, stack_id, values):
    stack = stack_get(context, stack_id)

    if not stack:
        raise exception.NotFound(_('Attempt to update a stack with id: '
                                 '%(id)s %(msg)s') % {
                                     'id': stack_id,
                                     'msg': 'that does not exist'})

    stack.update(values)
    stack.save(_session(context))


def stack_delete(context, stack_id):
    s = stack_get(context, stack_id)
    if not s:
        raise exception.NotFound(_('Attempt to delete a stack with id: '
                                 '%(id)s %(msg)s') % {
                                     'id': stack_id,
                                     'msg': 'that does not exist'})
    session = Session.object_session(s)

    for r in s.resources:
        session.delete(r)

    s.soft_delete(session=session)
    session.flush()


def stack_lock_create(stack_id, engine_id):
    session = get_session()
    with session.begin():
        lock = session.query(models.StackLock).get(stack_id)
        if lock is not None:
            return lock.engine_id
        session.add(models.StackLock(stack_id=stack_id, engine_id=engine_id))


def stack_lock_steal(stack_id, old_engine_id, new_engine_id):
    session = get_session()
    with session.begin():
        lock = session.query(models.StackLock).get(stack_id)
        rows_affected = session.query(models.StackLock).\
            filter_by(stack_id=stack_id, engine_id=old_engine_id).\
            update({"engine_id": new_engine_id})
    if not rows_affected:
        return lock.engine_id if lock is not None else True


def stack_lock_release(stack_id, engine_id):
    session = get_session()
    with session.begin():
        rows_affected = session.query(models.StackLock).\
            filter_by(stack_id=stack_id, engine_id=engine_id).\
            delete()
    if not rows_affected:
        return True


def user_creds_create(context):
    values = context.to_dict()
    user_creds_ref = models.UserCreds()
    if values.get('trust_id'):
        method, trust_id = _encrypt(values.get('trust_id'))
        user_creds_ref.trust_id = trust_id
        user_creds_ref.decrypt_method = method
        user_creds_ref.trustor_user_id = values.get('trustor_user_id')
        user_creds_ref.username = None
        user_creds_ref.password = None
        user_creds_ref.tenant = values.get('tenant')
        user_creds_ref.tenant_id = values.get('tenant_id')
    else:
        user_creds_ref.update(values)
        method, password = _encrypt(values['password'])
        user_creds_ref.password = password
        user_creds_ref.decrypt_method = method
    user_creds_ref.save(_session(context))
    return user_creds_ref


def user_creds_get(user_creds_id):
    db_result = model_query(None, models.UserCreds).get(user_creds_id)
    if db_result is None:
        return None
    # Return a dict copy of db results, do not decrypt details into db_result
    # or it can be committed back to the DB in decrypted form
    result = dict(db_result)
    del result['decrypt_method']
    result['password'] = _decrypt(result['password'], db_result.decrypt_method)
    result['trust_id'] = _decrypt(result['trust_id'], db_result.decrypt_method)
    return result


def user_creds_delete(context, user_creds_id):
    creds = model_query(context, models.UserCreds).get(user_creds_id)
    if not creds:
        raise exception.NotFound(
            _('Attempt to delete user creds with id '
              '%(id)s that does not exist') % {'id': user_creds_id})
    session = Session.object_session(creds)
    session.delete(creds)
    session.flush()


def event_get(context, event_id):
    result = model_query(context, models.Event).get(event_id)
    return result


def event_get_all(context):
    stacks = soft_delete_aware_query(context, models.Stack)
    stack_ids = [stack.id for stack in stacks]
    results = model_query(context, models.Event).\
        filter(models.Event.stack_id.in_(stack_ids)).all()
    return results


def event_get_all_by_tenant(context, limit=None, marker=None,
                            sort_keys=None, sort_dir=None, filters=None):
    query = model_query(context, models.Event)
    query = db_filters.exact_filter(query, models.Event, filters)
    query = query.join(models.Event.stack).\
        filter_by(tenant=context.tenant_id).filter_by(deleted_at=None)
    filters = None
    return _events_filter_and_page_query(context, query, limit, marker,
                                         sort_keys, sort_dir, filters).all()


def _query_all_by_stack(context, stack_id):
    query = model_query(context, models.Event).\
        filter_by(stack_id=stack_id)
    return query


def event_get_all_by_stack(context, stack_id, limit=None, marker=None,
                           sort_keys=None, sort_dir=None, filters=None):
    query = _query_all_by_stack(context, stack_id)
    return _events_filter_and_page_query(context, query, limit, marker,
                                         sort_keys, sort_dir, filters).all()


def _events_paginate_query(context, query, model, limit=None, sort_keys=None,
                           marker=None, sort_dir=None):
    default_sort_keys = ['created_at']
    if not sort_keys:
        sort_keys = default_sort_keys
        if not sort_dir:
            sort_dir = 'desc'

    # This assures the order of the stacks will always be the same
    # even for sort_key values that are not unique in the database
    sort_keys = sort_keys + ['id']

    model_marker = None
    if marker:
        # not to use model_query(context, model).get(marker), because
        # user can only see the ID(column 'uuid') and the ID as the marker
        model_marker = model_query(context, model).filter_by(uuid=marker).\
            first()
    try:
        query = utils.paginate_query(query, model, limit, sort_keys,
                                     model_marker, sort_dir)
    except utils.InvalidSortKey as exc:
        raise exception.Invalid(reason=exc.message)

    return query


def _events_filter_and_page_query(context, query,
                                  limit=None, marker=None,
                                  sort_keys=None, sort_dir=None,
                                  filters=None):
    if filters is None:
        filters = {}

    sort_key_map = {rpc_api.EVENT_TIMESTAMP: models.Event.created_at.key,
                    rpc_api.EVENT_RES_TYPE: models.Event.resource_type.key}
    whitelisted_sort_keys = _get_sort_keys(sort_keys, sort_key_map)

    query = db_filters.exact_filter(query, models.Event, filters)

    return _events_paginate_query(context, query, models.Event, limit,
                                  whitelisted_sort_keys, marker, sort_dir)


def event_count_all_by_stack(context, stack_id):
    return _query_all_by_stack(context, stack_id).count()


def _delete_event_rows(context, stack_id, limit):
    # MySQL does not support LIMIT in subqueries,
    # sqlite does not support JOIN in DELETE.
    # So we must manually supply the IN() values.
    # pgsql SHOULD work with the pure DELETE/JOIN below but that must be
    # confirmed via integration tests.
    query = _query_all_by_stack(context, stack_id)
    session = _session(context)
    ids = [r.id for r in query.order_by(
        models.Event.id).limit(limit).all()]
    q = session.query(models.Event).filter(
        models.Event.id.in_(ids))
    return q.delete(synchronize_session='fetch')


def event_create(context, values):
    if 'stack_id' in values and cfg.CONF.max_events_per_stack:
        if ((event_count_all_by_stack(context, values['stack_id']) >=
             cfg.CONF.max_events_per_stack)):
            # prune
            _delete_event_rows(
                context, values['stack_id'], cfg.CONF.event_purge_batch_size)
    event_ref = models.Event()
    event_ref.update(values)
    event_ref.save(_session(context))
    return event_ref


def watch_rule_get(context, watch_rule_id):
    result = model_query(context, models.WatchRule).get(watch_rule_id)
    return result


def watch_rule_get_by_name(context, watch_rule_name):
    result = model_query(context, models.WatchRule).\
        filter_by(name=watch_rule_name).first()
    return result


def watch_rule_get_all(context):
    results = model_query(context, models.WatchRule).all()
    return results


def watch_rule_get_all_by_stack(context, stack_id):
    results = model_query(context, models.WatchRule).\
        filter_by(stack_id=stack_id).all()
    return results


def watch_rule_create(context, values):
    obj_ref = models.WatchRule()
    obj_ref.update(values)
    obj_ref.save(_session(context))
    return obj_ref


def watch_rule_update(context, watch_id, values):
    wr = watch_rule_get(context, watch_id)

    if not wr:
        raise exception.NotFound(_('Attempt to update a watch with id: '
                                 '%(id)s %(msg)s') % {
                                     'id': watch_id,
                                     'msg': 'that does not exist'})
    wr.update(values)
    wr.save(_session(context))


def watch_rule_delete(context, watch_id):
    wr = watch_rule_get(context, watch_id)
    if not wr:
        raise exception.NotFound(_('Attempt to delete watch_rule: '
                                 '%(id)s %(msg)s') % {
                                     'id': watch_id,
                                     'msg': 'that does not exist'})
    session = Session.object_session(wr)

    for d in wr.watch_data:
        session.delete(d)

    session.delete(wr)
    session.flush()


def watch_data_create(context, values):
    obj_ref = models.WatchData()
    obj_ref.update(values)
    obj_ref.save(_session(context))
    return obj_ref


def watch_data_get_all(context):
    results = model_query(context, models.WatchData).all()
    return results


def software_config_create(context, values):
    obj_ref = models.SoftwareConfig()
    obj_ref.update(values)
    obj_ref.save(_session(context))
    return obj_ref


def software_config_get(context, config_id):
    result = model_query(context, models.SoftwareConfig).get(config_id)
    if (result is not None and context is not None and
            result.tenant != context.tenant_id):
        result = None

    if not result:
        raise exception.NotFound(_('Software config with id %s not found') %
                                 config_id)
    return result


def software_config_delete(context, config_id):
    config = software_config_get(context, config_id)
    session = Session.object_session(config)
    session.delete(config)
    session.flush()


def software_deployment_create(context, values):
    obj_ref = models.SoftwareDeployment()
    obj_ref.update(values)
    obj_ref.save(_session(context))
    return obj_ref


def software_deployment_get(context, deployment_id):
    result = model_query(context, models.SoftwareDeployment).get(deployment_id)
    if (result is not None and context is not None and
        context.tenant_id not in (result.tenant,
                                  result.stack_user_project_id)):
        result = None

    if not result:
        raise exception.NotFound(_('Deployment with id %s not found') %
                                 deployment_id)
    return result


def software_deployment_get_all(context, server_id=None):
    sd = models.SoftwareDeployment
    query = model_query(context, sd).\
        filter(sqlalchemy.or_(
            sd.tenant == context.tenant_id,
            sd.stack_user_project_id == context.tenant_id
        )).\
        order_by(sd.created_at)
    if server_id:
        query = query.filter_by(server_id=server_id)
    return query.all()


def software_deployment_update(context, deployment_id, values):
    deployment = software_deployment_get(context, deployment_id)
    deployment.update(values)
    deployment.save(_session(context))
    return deployment


def software_deployment_delete(context, deployment_id):
    deployment = software_deployment_get(context, deployment_id)
    session = Session.object_session(deployment)
    session.delete(deployment)
    session.flush()


def snapshot_create(context, values):
    obj_ref = models.Snapshot()
    obj_ref.update(values)
    obj_ref.save(_session(context))
    return obj_ref


def snapshot_get(context, snapshot_id):
    result = model_query(context, models.Snapshot).get(snapshot_id)
    if (result is not None and context is not None and
            context.tenant_id != result.tenant):
        result = None

    if not result:
        raise exception.NotFound(_('Snapshot with id %s not found') %
                                 snapshot_id)
    return result


def snapshot_update(context, snapshot_id, values):
    snapshot = snapshot_get(context, snapshot_id)
    snapshot.update(values)
    snapshot.save(_session(context))
    return snapshot


def snapshot_delete(context, snapshot_id):
    snapshot = snapshot_get(context, snapshot_id)
    session = Session.object_session(snapshot)
    session.delete(snapshot)
    session.flush()


def snapshot_get_all(context, stack_id):
    return model_query(context, models.Snapshot).filter_by(
        stack_id=stack_id, tenant=context.tenant_id)


def purge_deleted(age, granularity='days'):
    try:
        age = int(age)
    except ValueError:
        raise exception.Error(_("age should be an integer"))
    if age < 0:
        raise exception.Error(_("age should be a positive integer"))

    if granularity not in ('days', 'hours', 'minutes', 'seconds'):
        raise exception.Error(
            _("granularity should be days, hours, minutes, or seconds"))

    if granularity == 'days':
        age = age * 86400
    elif granularity == 'hours':
        age = age * 3600
    elif granularity == 'minutes':
        age = age * 60

    time_line = datetime.now() - timedelta(seconds=age)
    engine = get_engine()
    meta = sqlalchemy.MetaData()
    meta.bind = engine

    stack = sqlalchemy.Table('stack', meta, autoload=True)
    event = sqlalchemy.Table('event', meta, autoload=True)
    raw_template = sqlalchemy.Table('raw_template', meta, autoload=True)
    user_creds = sqlalchemy.Table('user_creds', meta, autoload=True)

    stmt = sqlalchemy.select([stack.c.id,
                              stack.c.raw_template_id,
                              stack.c.user_creds_id]).\
        where(stack.c.deleted_at < time_line)
    deleted_stacks = engine.execute(stmt)

    for s in deleted_stacks:
        event_del = event.delete().where(event.c.stack_id == s[0])
        engine.execute(event_del)
        stack_del = stack.delete().where(stack.c.id == s[0])
        engine.execute(stack_del)
        raw_template_del = raw_template.delete().\
            where(raw_template.c.id == s[1])
        engine.execute(raw_template_del)
        user_creds_del = user_creds.delete().where(user_creds.c.id == s[2])
        engine.execute(user_creds_del)


def db_sync(engine, version=None):
    """Migrate the database to `version` or the most recent version."""
    return migration.db_sync(engine, version=version)


def db_version(engine):
    """Display the current database version."""
    return migration.db_version(engine)


def template_create(context, values):
    """ save gcloud_template"""
    gcloud_template = models.Gcloud_template()
    gcloud_template.update(values)
    gcloud_template.save(_session(context))
    return gcloud_template

def template_get_all(context, limit=None, sort_keys=None, offset=None,
                  sort_dir=None, filters=None):

    if "admin" not in context.roles:
         filters.update({"creater": context.username})

    session = _session(context)
    list = []
    for key, value in six.iteritems(filters):
        if key == "name":
            list.append(getattr(models.Gcloud_template, key).like("%s%s%s" % ("%", value, "%")))

        else:
            list.append(getattr(models.Gcloud_template, key) == value)
    query = session.query(models.Gcloud_template).filter(and_(*list))
    return _paginate_query(context, query, models.Gcloud_template, limit, sort_keys, None, sort_dir, offset)


def template_delete(context, template_id):
    session = _session(context)
    session.begin()
    if "admin"  in context.roles:
        templates = session.query(models.Gcloud_template).filter_by(id=template_id)
    else:
        templates = session.query(models.Gcloud_template).filter(and_(
            models.Gcloud_template.creater == context.username,models.Gcloud_template.id == template_id))

    for t in templates:
        session.delete(t)
    session.commit()


def template_get(context, template_id):

    session = _session(context)
    if "admin"  in context.roles:
        templates = session.query(models.Gcloud_template).filter_by(id=template_id)
    else:
        templates = session.query(models.Gcloud_template).filter(and_(
            models.Gcloud_template.creater == context.username, models.Gcloud_template.id == template_id))

    if templates is not None:
        return templates

    else:
        raise exception.TemplateNotFound(template_id=template_id)

def template_get_count(context):
    session = _session(context)
    filters=dict()
    if "admin" not in context.roles:
        filters.update({"creater": context.username})

    query = session.query(models.Gcloud_template).filter_by(**filters)
    return query.count()

def event_get_all_for_g_cloud(context, limit=None, sort_keys=None, offset=None,
                  sort_dir=None, filters=None):

    if "admin" not in context.roles:
        filters.update({"username": context.username})
    session = _session(context)
    query = session.query(models.Event).join(models.Event.stack)
    #去掉被删除的栈2015.8.6
    query = query.filter(getattr(models.Stack, "deleted_at") == None)
    #去掉backup等中间过程生成的子栈
    query = query.filter(getattr(models.Stack, "owner_id") == None)
    #只获取本身tenant_id的记录
    query = query.filter(getattr(models.Stack, "tenant") == context.tenant_id)
    if filters:
           #filter by create time
            created_time_first=filters.pop("create_time_first",None)
            created_time_end=filters.pop("create_time_end",None)
            if created_time_first or created_time_end :
                #define time range key ,default column name is create_time
                time_range_key=filters.pop("time_range_key",["created_at"])
                column = getattr(models.Event, time_range_key[0], None)
                if column :
                    if created_time_first:
                        query = query.filter(column>=created_time_first)
                    if created_time_end:
                        query = query.filter(column<=created_time_end)

            stack_id = filters.pop("stack_id", None)
            stack_apps_style = filters.pop("stack_apps_style", None)
            app_name = filters.pop("app_name", None)
            username = filters.pop("username", None)
            resource_status = filters.pop("resource_status", None)

            if resource_status:
                query = query.filter(getattr(models.Event, "resource_status") == resource_status)
            if username:
                query = query.filter(getattr(models.Stack,"username") == username)

            if stack_id:
                query = query.filter(getattr(models.Stack,"id") == stack_id)

            if stack_apps_style:
                query = query.filter(getattr(models.Stack,"stack_apps_style") == stack_apps_style)

            if app_name:
                query = query.filter(getattr(models.Stack, "app_name").like("%s%s%s" %("%", app_name, "%")))

            #query = query.filter(getattr(models.Stack, "owner_id")== None)


    return _paginate_query(context, query, models.Event, limit, sort_keys, None, sort_dir, offset)


def stack_get_all_for_g_cloud(context, limit=None, sort_keys=None, offset=None,
                  sort_dir=None, filters=None):

    if "admin" not in context.roles:
        filters.update({"username": context.username})
    session = _session(context)
    query = session.query(models.Stack)
    #去掉被删除的栈2015.8.6：for bug 5568
    query = query.filter_by(deleted_at=None)
    #去掉backup=1等子栈
    query = query.filter(getattr(models.Stack, "owner_id") == None)
    #只获取本身tenant_id的记录
    query = query.filter(getattr(models.Stack, "tenant") == context.tenant_id)
    if filters:
           #filter by create time
            created_time_first=filters.pop("create_time_first",None)
            created_time_end=filters.pop("create_time_end",None)
            if created_time_first or created_time_end :
                #define time range key ,default column name is create_time
                time_range_key=filters.pop("time_range_key", ["created_at"])
                column = getattr(models.Stack, time_range_key[0], None)
                if column:
                    if created_time_first:
                        query = query.filter(column>=created_time_first)
                    if created_time_end:
                        query = query.filter(column<=created_time_end)

            stack_apps_style = filters.pop("stack_apps_style", None)
            app_name = filters.pop("app_name", None)
            username = filters.pop("username", None)
            status = filters.pop("stack_status", None)
            action = filters.pop('action', None)
            id = filters.pop('id', None)
            #如果action存在，则表示刷选条件中未stack_status=suspend||running,
            # 此时需要2个条件:status=COMPLETE,action in ['SUSPEND'] || ['CREATE', 'UPDATE', 'RESUME']
            if action:
                column = getattr(models.Stack, 'action', None)
                if column:
                    query = query.filter(column.in_(action))
            if status:
                query = query.filter(getattr(models.Stack, "status") == status)
            if username:
                query = query.filter(getattr(models.Stack, "username") == username)
            if stack_apps_style:
                query = query.filter(getattr(models.Stack, "stack_apps_style") == stack_apps_style)
            if app_name:
                query = query.filter(getattr(models.Stack, "app_name").like("%s%s%s" % ("%", app_name, "%")))
            if id:
                query = query.filter(getattr(models.Stack, "id") == id)

    return _paginate_query(context, query, models.Stack, limit, sort_keys, None, sort_dir, offset)

def data_get_all_for_g_cloud(context, limit=None, sort_keys=None, offset=None,
                  sort_dir=None, filters=None):

    if "admin" not in context.roles:
        filters.update({"username": context.username})
    session = _session(context)
    query = session.query(models.Stack)
    query = query.filter_by(deleted_at=None)
    #去掉backup=1等子栈
    query = query.filter(getattr(models.Stack, "owner_id") == None)
    #只获取本身tenant_id的记录
    query = query.filter(getattr(models.Stack, "tenant") == context.tenant_id)
    if filters:
           #filter by create time
            created_time_first=filters.pop("create_time_first", None)
            created_time_end=filters.pop("create_time_end", None)
            if created_time_first or created_time_end :
                #define time range key ,default column name is create_time
                time_range_key=filters.pop("time_range_key", ["created_at"])
                column = getattr(models.Stack, time_range_key[0], None)
                if column:
                    if created_time_first:
                        query = query.filter(column >= created_time_first)
                    if created_time_end:
                        query = query.filter(column <= created_time_end)

            stack_apps_style = filters.pop("stack_apps_style", None)
            app_name = filters.pop("app_name", None)
            username = filters.pop("username", None)
            status = filters.pop("stack_status", None)
            action = filters.pop('action', None)
            #如果action存在，则表示刷选条件中stack_status=suspend||running,
            # 此时需要2个条件:status=COMPLETE,action in ['SUSPEND'] || ['CREATE', 'UPDATE', 'RESUME']
            if action:
                column = getattr(models.Stack, 'action', None)
                if column:
                    query = query.filter(column.in_(action))
            if status:
                query = query.filter(getattr(models.Stack, "status") == status)
            if username:
                query = query.filter(getattr(models.Stack, "username") == username)
            if stack_apps_style:
                query = query.filter(getattr(models.Stack, "stack_apps_style") == stack_apps_style)
            if app_name:
                query = query.filter(getattr(models.Stack, "app_name").like("%s%s%s" % ("%", app_name, "%")))

    data = _paginate_query(context, query, models.Stack, limit, sort_keys, None, sort_dir, offset)
    return process_data(data)

def get_stack_name_by_stack_id_for_g_cloud(context, stack_id, filters=None):
    #brk(host="10.10.12.21", port=49163)
    if "admin" not in context.roles:
        filters.update({"username": context.username})
    session = _session(context)
    query = session.query(models.Stack)
    #只获取本身tenant_id的记录
    query = query.filter(getattr(models.Stack, "tenant") == context.tenant_id)
    if filters:
            username = filters.pop("username", None)
            if username:
                query = query.filter(getattr(models.Stack, "username") == username)
    query = query.filter(getattr(models.Stack, "id") == stack_id)
    stack = query.first()
    if stack:
        data = {"app_name": stack["app_name"]}
    else:
        data = {"app_name": ""}
    return data

def process_data(data):
    """
     process data for data_get_all_for_g_cloud
    """
    public_num = 0
    socity_num = 0
    market_num = 0
    economy_num = 0
    government_num = 0
    common_num = 0
    industry_num = 0
    for d in data:
        #if d['stack_apps_style'] in ['PUBLIC', 'SOCITY', 'MARKET', 'ECONOMY', 'GOVERNMENT', 'COMMON', 'INDUSTRY']:
        if d['stack_apps_style'] == 'PUBLIC':
            public_num += 1
        elif d['stack_apps_style'] == 'SOCITY':
            socity_num += 1
        elif d['stack_apps_style'] == 'MARKET':
            market_num += 1
        elif d['stack_apps_style'] == 'ECONOMY':
            economy_num += 1
        elif d['stack_apps_style'] == 'GOVERNMENT':
            government_num += 1
        elif d['stack_apps_style'] == 'COMMON':
            common_num += 1
        elif d['stack_apps_style'] == 'INDUSTRY':
            industry_num += 1
    res = [{'appType': "PUBLIC", "num": public_num},
           {'appType': "SOCITY", "num": socity_num},
           {'appType': "MARKET", "num": market_num},
           {'appType': "ECONOMY", "num": economy_num},
           {'appType': "GOVERNMENT", "num": government_num},
           {'appType': "COMMON", "num": common_num},
           {'appType': "INDUSTRY", "num": industry_num}]
    return res