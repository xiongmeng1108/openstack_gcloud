# -*- coding:utf-8 -*-
# Copyright (c) 2014 OpenStack Foundation.
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

import weakref

from sqlalchemy import sql
from sqlalchemy import  or_
from neutron.common import exceptions as n_exc
from neutron.db import sqlalchemyutils
from neutron.openstack.common import log
LOG = log.getLogger(__name__)

class CommonDbMixin(object):
    """Common methods used in core and service plugins."""
    # Plugins, mixin classes implementing extension will register
    # hooks into the dict below for "augmenting" the "core way" of
    # building a query for retrieving objects from a model class.
    # To this aim, the register_model_query_hook and unregister_query_hook
    # from this class should be invoked
    _model_query_hooks = {}

    # This dictionary will store methods for extending attributes of
    # api resources. Mixins can use this dict for adding their own methods
    # TODO(salvatore-orlando): Avoid using class-level variables
    _dict_extend_functions = {}

    @classmethod
    def register_model_query_hook(cls, model, name, query_hook, filter_hook,
                                  result_filters=None):
        """Register a hook to be invoked when a query is executed.

        Add the hooks to the _model_query_hooks dict. Models are the keys
        of this dict, whereas the value is another dict mapping hook names to
        callables performing the hook.
        Each hook has a "query" component, used to build the query expression
        and a "filter" component, which is used to build the filter expression.

        Query hooks take as input the query being built and return a
        transformed query expression.

        Filter hooks take as input the filter expression being built and return
        a transformed filter expression
        """
        model_hooks = cls._model_query_hooks.get(model)
        if not model_hooks:
            # add key to dict
            model_hooks = {}
            cls._model_query_hooks[model] = model_hooks
        model_hooks[name] = {'query': query_hook, 'filter': filter_hook,
                             'result_filters': result_filters}

    @property
    def safe_reference(self):
        """Return a weakref to the instance.

        Minimize the potential for the instance persisting
        unnecessarily in memory by returning a weakref proxy that
        won't prevent deallocation.
        """
        return weakref.proxy(self)

    def _model_query(self, context, model):
        query = context.session.query(model)
        # define basic filter condition for model query
        # NOTE(jkoelker) non-admin queries are scoped to their tenant_id
        # NOTE(salvatore-orlando): unless the model allows for shared objects

        # ###-------- alter by xm and zyk at 2015.9.23--------------
        # query_filter = None
        # if not context.is_admin and hasattr(model, 'tenant_id'):
        #     if hasattr(model, 'shared'):
        #         query_filter = ((model.tenant_id == context.tenant_id) |
        #                         (model.shared == sql.true()))
        #     else:
        #         query_filter = (model.tenant_id == context.tenant_id)
        ###--change to as follow (because of gcloud7 access controller:gc_resource_type=0/1 0isOwnerAndShared 1isAll)--:

        query_filter = None
        if context.gc_resource_type == '0' and hasattr(model, 'user_id'):
            if hasattr(model, 'shared'):
                query_filter = ((model.user_id == context.user_id) |
                                (model.shared == sql.true()) |
                                (model.user_id == None))
            else:
                query_filter = ((model.user_id == context.user_id) | (model.user_id == None))
        #model.user_id ==None(can not change as model.user_id is None) added
        # because of such as network:dhcp Ports(which user_id is None)
        ###------------- end by xm and zyk--------------------------------

        # Execute query hooks registered from mixins and plugins
        for _name, hooks in self._model_query_hooks.get(model,
                                                        {}).iteritems():
            query_hook = hooks.get('query')
            if isinstance(query_hook, basestring):
                query_hook = getattr(self, query_hook, None)
            if query_hook:
                query = query_hook(context, model, query)

            filter_hook = hooks.get('filter')
            if isinstance(filter_hook, basestring):
                filter_hook = getattr(self, filter_hook, None)
            if filter_hook:
                query_filter = filter_hook(context, model, query_filter)

        # NOTE(salvatore-orlando): 'if query_filter' will try to evaluate the
        # condition, raising an exception
        if query_filter is not None:
            query = query.filter(query_filter)
        return query

    def _fields(self, resource, fields):
        if fields:
            return dict(((key, item) for key, item in resource.items()
                         if key in fields))
        return resource

    def _get_tenant_id_for_create(self, context, resource):
        if context.is_admin and 'tenant_id' in resource:
            tenant_id = resource['tenant_id']
        elif ('tenant_id' in resource and
              resource['tenant_id'] != context.tenant_id):
            reason = _('Cannot create resource for another tenant')
            raise n_exc.AdminRequired(reason=reason)
        else:
            tenant_id = context.tenant_id
        return tenant_id

    def _get_by_id(self, context, model, id):
        query = self._model_query(context, model)
        return query.filter(model.id == id).one()

    def get_or_query(self,query,model,key_names,key_values):
        """
        get or query contions
        return query
        """
        if key_names and key_values:
                criteria_list = []
                for key in key_names:
                       column = getattr(model, key, None)
                       key_like=key_values[0]
                       if column:
                           try:
                                #key_like=myqldb.escape_string(key_like)
                                key_like=key_like.replace("_","\_")
                                key_like=key_like.replace("%","\%")
                           finally:
                             key_like="%"+key_like+"%"
                             likestr=column.like(key_like ,escape="\\")
                             criteria_list.append(likestr)
                if len(criteria_list)>0:
                    return query.filter(or_(*criteria_list))
        return query

    ### add by xm and luoyb at 2015.9.22
    def get_or_no_like_query(self,query,model,column_names,column_values):
        """
        get or query contions
        return query
        """
        if column_names and column_values:
            criteria_list = []
            index=0
            for key in column_names:

                column = getattr(model, key, None)


                if column and column_values[index]:
                    criteria_list.append(column.in_(column_values[index]))
                index+=1
            if len(criteria_list)>0:
                return query.filter(or_(*criteria_list))
        return query
    ###end

    def _apply_filters_to_query(self, query, model, filters):
        if filters:
            filters=filters.copy()
            #support create time filters
            created_time_first=filters.pop("create_time_first",None)
            created_time_end=filters.pop("create_time_end",None)
            if created_time_first or created_time_end :
                #define time range key ,default column name is create_time
                time_range_key=filters.pop("time_range_key",["create_time"])
                column = getattr(model, time_range_key[0], None)
                if column :
                    if created_time_first:
                        query = query.filter(column>=created_time_first)
                    if created_time_end:
                        query = query.filter(column<=created_time_end)

            key_names=filters.pop("key_name",None)
            key_values=filters.pop("key_value",None)
            query=self.get_or_query(query,model,key_names,key_values)

            # ### add by xm and luoyb at 2015.9.22
            # column_names=filters.pop("column_names",None)
            # column_values=filters.pop("column_values",None)
            # query=self.get_or_no_like_query(query,model,column_names,column_values)
            # ### end

            for key, value in filters.iteritems():
                column = getattr(model, key, None)
                #add by xm-2015.6.12-通用字段为空刷选(数据库中为空包括'空白字符串'和Null)：
                # （1）当为‘空白字符串’时（设计表有不能为空属性时），如：?"device_id=''"
                # （2）当为Null时，如：?"device_id=None"
                if column:
                    if value == [u"''"]:
                        query = query.filter(column == '')
                    elif value == [u"None"]:
                        query = query.filter(column == None)
                    else:
                        query = query.filter(column.in_(value))
            for _name, hooks in self._model_query_hooks.get(model,
                                                            {}).iteritems():
                result_filter = hooks.get('result_filters', None)
                if isinstance(result_filter, basestring):
                    result_filter = getattr(self, result_filter, None)

                if result_filter:
                    query = result_filter(query, filters)
        return query

    def _apply_dict_extend_functions(self, resource_type,
                                     response, db_object):
        for func in self._dict_extend_functions.get(
            resource_type, []):
            args = (response, db_object)
            if isinstance(func, basestring):
                func = getattr(self, func, None)
            else:
                # must call unbound method - use self as 1st argument
                args = (self,) + args
            if func:
                func(*args)

    def _get_collection_query(self, context, model, filters=None,
                              sorts=None, limit=None, marker_obj=None,
                              page_reverse=False,offset=None):
        collection = self._model_query(context, model)
        collection = self._apply_filters_to_query(collection, model, filters)
        if limit and page_reverse and sorts:
            sorts = [(s[0], not s[1]) for s in sorts]
        collection = sqlalchemyutils.paginate_query(collection, model, limit,
                                                    sorts,
                                                    marker_obj=marker_obj, offset=offset)
        return collection

    def _get_collection(self, context, model, dict_func, filters=None,
                        fields=None, sorts=None, limit=None, marker_obj=None,
                        page_reverse=False,offset=None):
        query = self._get_collection_query(context, model, filters=filters,
                                           sorts=sorts,
                                           limit=limit,
                                           marker_obj=marker_obj,
                                           page_reverse=page_reverse,offset=offset)
        items = [dict_func(c, fields) for c in query]
        if limit and page_reverse:
            items.reverse()
        return items

    def _get_collection_count(self, context, model, filters=None):
        return self._get_collection_query(context, model, filters).count()

    def _get_marker_obj(self, context, resource, limit, marker):
        if limit and marker:
            return getattr(self, '_get_%s' % resource)(context, marker)
        return None

    def _filter_non_model_columns(self, data, model):
        """Remove all the attributes from data which are not columns of
        the model passed as second parameter.
        """
        columns = [c.name for c in model.__table__.columns]
        return dict((k, v) for (k, v) in
                    data.iteritems() if k in columns)
