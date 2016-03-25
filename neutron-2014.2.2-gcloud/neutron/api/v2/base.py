# -*- coding:utf-8 -*-
# Copyright (c) 2012 OpenStack Foundation.
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

import copy
import netaddr
import webob.exc

from oslo.config import cfg

from neutron.api import api_common
from neutron.api.rpc.agentnotifiers import dhcp_rpc_agent_api
from neutron.api.v2 import attributes
from neutron.api.v2 import resource as wsgi_resource
from neutron.common import constants as const
from neutron.common import exceptions
from neutron.common import rpc as n_rpc
from neutron.openstack.common import excutils
from neutron.openstack.common import log as logging
from neutron import policy
from neutron import quota
#from dbgp.client import brk

LOG = logging.getLogger(__name__)

FAULT_MAP = {exceptions.NotFound: webob.exc.HTTPNotFound,
             exceptions.Conflict: webob.exc.HTTPConflict,
             exceptions.InUse: webob.exc.HTTPConflict,
             exceptions.BadRequest: webob.exc.HTTPBadRequest,
             exceptions.ServiceUnavailable: webob.exc.HTTPServiceUnavailable,
             exceptions.NotAuthorized: webob.exc.HTTPForbidden,
             netaddr.AddrFormatError: webob.exc.HTTPBadRequest,
             }


class Controller(object):
    LIST = 'list'
    SHOW = 'show'
    CREATE = 'create'
    UPDATE = 'update'
    DELETE = 'delete'

    def __init__(self, plugin, collection, resource, attr_info,
                 allow_bulk=False, member_actions=None, parent=None,
                 allow_pagination=False, allow_sorting=False):
        """  控制器初始化 add by ;luoyibing
       :param  allowbulk 是否允许批量？
       :param  collection  "subnet"
       :param  resource  "subnet"
       :param  attr_info
       :param plugin   插件信息
                {
                 agent_notifters:{"DHCP agent":"DHCCPAgent***","L3 agent":"***","Loadbalancer agent"：“**”}
                 ,extension_manager:
                 ，mechaism manager 含义指 ？
                 ,network schedule......
        :param member_actions
        resource
        """
        if member_actions is None:
            member_actions = []
        self._plugin = plugin
        self._collection = collection.replace('-', '_')
        self._resource = resource.replace('-', '_')
        self._attr_info = attr_info
        self._allow_bulk = allow_bulk
        self._allow_pagination = allow_pagination
        self._allow_sorting = allow_sorting
        self._native_bulk = self._is_native_bulk_supported()
        self._native_pagination = self._is_native_pagination_supported()
        self._native_sorting = self._is_native_sorting_supported()
        self._policy_attrs = [name for (name, info) in self._attr_info.items()
                              if info.get('required_by_policy')]
        self._notifier = n_rpc.get_notifier('network')#建立根据network.controller 名称通知的发布者:具体过程调用notifier.py中prepare方法实现
        # use plugin's dhcp notifier, if this is already instantiated
        agent_notifiers = getattr(plugin, 'agent_notifiers', {})#从插件中获取agent_notitfiers
        self._dhcp_agent_notifier = (     #agent_notifiers中获取dhcp agent或者 DhcpAgentNotifyAPI
            agent_notifiers.get(const.AGENT_TYPE_DHCP) or
            dhcp_rpc_agent_api.DhcpAgentNotifyAPI()
        )
        if cfg.CONF.notify_nova_on_port_data_changes:#neutron.conf配置文件中配置项
            from neutron.notifiers import nova
            self._nova_notifier = nova.Notifier() #引入通知计算节点的Notifier
        self._member_actions = member_actions
        self._primary_key = self._get_primary_key()
        if self._allow_pagination and self._native_pagination:
            # Native pagination need native sorting support
            if not self._native_sorting:
                raise exceptions.Invalid(
                    _("Native pagination depend on native sorting")
                )
            if not self._allow_sorting:
                LOG.info(_("Allow sorting is enabled because native "
                           "pagination requires native sorting"))
                self._allow_sorting = True

        if parent:
            self._parent_id_name = '%s_id' % parent['member_name']
            parent_part = '_%s' % parent['member_name']
        else:
            self._parent_id_name = None
            parent_part = ''
        self._plugin_handlers = {
            self.LIST: 'get%s_%s' % (parent_part, self._collection),
            self.SHOW: 'get%s_%s' % (parent_part, self._resource)
        }
        for action in [self.CREATE, self.UPDATE, self.DELETE]:
            self._plugin_handlers[action] = '%s%s_%s' % (action, parent_part,
                                                         self._resource)#??创建对应的资源handers

    def _get_primary_key(self, default_primary_key='id'):
        for key, value in self._attr_info.iteritems():
            if value.get('primary_key', False):
                return key
        return default_primary_key

    def _is_native_bulk_supported(self):
        native_bulk_attr_name = ("_%s__native_bulk_support"
                                 % self._plugin.__class__.__name__)
        return getattr(self._plugin, native_bulk_attr_name, False)

    def _is_native_pagination_supported(self):
        native_pagination_attr_name = ("_%s__native_pagination_support"
                                       % self._plugin.__class__.__name__)
        return getattr(self._plugin, native_pagination_attr_name, False)

    def _is_native_sorting_supported(self):
        native_sorting_attr_name = ("_%s__native_sorting_support"
                                    % self._plugin.__class__.__name__)
        return getattr(self._plugin, native_sorting_attr_name, False)

    def _exclude_attributes_by_policy(self, context, data):
        """Identifies attributes to exclude according to authZ policies.

        Return a list of attribute names which should be stripped from the
        response returned to the user because the user is not authorized
        to see them.
        """
        attributes_to_exclude = []
        for attr_name in data.keys():
            attr_data = self._attr_info.get(attr_name)
            if attr_data and attr_data['is_visible']:
                if policy.check(
                    context,
                    '%s:%s' % (self._plugin_handlers[self.SHOW], attr_name),
                    data,
                    might_not_exist=True):
                    # this attribute is visible, check next one
                    continue
            # if the code reaches this point then either the policy check
            # failed or the attribute was not visible in the first place
            attributes_to_exclude.append(attr_name)
        return attributes_to_exclude

    def _view(self, context, data, fields_to_strip=None):
        """Build a view of an API resource.

        :param context: the neutron context
        :param data: the object for which a view is being created
        :param fields_to_strip: attributes to remove from the view

        :returns: a view of the object which includes only attributes
        visible according to API resource declaration and authZ policies.
        """
        fields_to_strip = ((fields_to_strip or []) +
                           self._exclude_attributes_by_policy(context, data))
        return self._filter_attributes(context, data, fields_to_strip)

    def _filter_attributes(self, context, data, fields_to_strip=None):
        if not fields_to_strip:
            return data
        return dict(item for item in data.iteritems()
                    if (item[0] not in fields_to_strip))

    def _do_field_list(self, original_fields):
        fields_to_add = None
        # don't do anything if fields were not specified in the request
        if original_fields:
            fields_to_add = [attr for attr in self._policy_attrs
                             if attr not in original_fields]
            original_fields.extend(self._policy_attrs)
        return original_fields, fields_to_add

    def __getattr__(self, name):
        if name in self._member_actions:
            def _handle_action(request, id, **kwargs):
                arg_list = [request.context, id]
                # Ensure policy engine is initialized
                policy.init()
                # Fetch the resource and verify if the user can access it
                try:
                    resource = self._item(request, id, True)
                except exceptions.PolicyNotAuthorized:
                    msg = _('The resource could not be found.')
                    raise webob.exc.HTTPNotFound(msg)
                body = kwargs.pop('body', None)
                # Explicit comparison with None to distinguish from {}
                if body is not None:
                    arg_list.append(body)
                # It is ok to raise a 403 because accessibility to the
                # object was checked earlier in this method
                policy.enforce(request.context, name, resource)
                return getattr(self._plugin, name)(*arg_list, **kwargs)
            return _handle_action
        else:
            raise AttributeError()

    def _get_pagination_helper(self, request):
        if self._allow_pagination and self._native_pagination:
            return api_common.PaginationNativeHelper(request,
                                                     self._primary_key)
        elif self._allow_pagination:
            return api_common.PaginationEmulatedHelper(request,
                                                       self._primary_key)
        return api_common.NoPaginationHelper(request, self._primary_key)

    def _get_sorting_helper(self, request):
        if self._allow_sorting and self._native_sorting:
            return api_common.SortingNativeHelper(request, self._attr_info)
        elif self._allow_sorting:
            return api_common.SortingEmulatedHelper(request, self._attr_info)
        return api_common.NoSortingHelper(request, self._attr_info)

    def _get_is_query_detail_items_infos(self,filters):
        """
        according to  filters params:only_statics ,get is_query_items
        return:True or False
        """
        only_statics=filters.pop("only_statics",None)
        is_query_details=True
        if only_statics:
              is_only_count=("true"==only_statics[0])
              if is_only_count:
                    is_query_details=False
        return is_query_details
    def _items(self, request, do_authz=False, parent_id=None):
        """Retrieves and formats a list of elements of the requested entity."""
        # NOTE(salvatore-orlando): The following ensures that fields which
        # are needed for authZ policy validation are not stripped away by the
        # plugin before returning.
        #brk(host="10.10.12.21", port=49175)
        original_fields, fields_to_add = self._do_field_list(
            api_common.list_args(request, 'fields')) #获取查询条件字段??
        filters = api_common.get_filters(request, self._attr_info,
                                         ['fields', 'sort_key', 'sort_dir',
                                          'limit', 'marker', 'page_reverse','offset'])

        # ### add by xm at 2015.9.22 权限控制
        # #LOG.debug(_("111111 222 %s"), filters)
        # #LOG.debug(_("111111 222 context: %s"), request.context.__dict__)
        # if request.context.gc_resource_type == '0':
        #     #LOG.debug(_("111111 222 context.user_id:%s  gc_resource_type:%s"),  request.context.user_id, request.context.gc_resource_type)
        #     user_id = [request.context.user_id]
        #     user_id = list(set(user_id) | set(filters.get("user_id", [])))
        #     filters.update({"user_id": user_id})
        #     #LOG.debug(_("111111 222 ddd %s"), filters)
        # #LOG.debug(_("111111 222 %s"), filters)
        # ###end by xm

        #validate create_time_first and create_time_end
        api_common.validate_update_time_range(filters)


        kwargs = {'filters': filters,
                  'fields': original_fields}

        #according to  filters params:only_statics ,get is_query_items
        is_query_items=self._get_is_query_detail_items_infos(filters)

        filters_copy=filters.copy()
        # first get resources count number by resources filters
        counter=self._get_items_count_by_filter(request=request,filters=filters_copy)

        collection={}
        if is_query_items :#this function is not only statics
        #get resources items
            obj_list=None
            pagination_helper=None
            #change from counter >=0 to counter !=0  for no method of 'get_xxx_count'
            if (counter is not None and counter != 0) or (counter is None):
                    obj_list,pagination_helper = self._get_items_by_filter_and_order_and_page(request=request
                                                                  ,kwargs=kwargs,
                                                                  original_fields=original_fields
                                                                  ,fields_to_add=fields_to_add,
                                                                  do_authz=do_authz,
                                                                  parent_id=parent_id)
            # Use the first element in the list for discriminating which attributes
            # should be filtered out because of authZ policies
            # fields_to_add contains a list of attributes added for request policy
            # checks but that were not required by the user. They should be
            # therefore stripped
            fields_to_strip = fields_to_add or []
            if obj_list:
                fields_to_strip += self._exclude_attributes_by_policy(
                    request.context, obj_list[0])

            if obj_list:
                collection = {self._collection:
                          [self._filter_attributes(
                              request.context, obj,
                              fields_to_strip=fields_to_strip)
                           for obj in obj_list]}
            else:
                 collection = {self._collection:[]}
                 counter=0
        if counter is not None and counter>=0 :
            collection["list"]={"count":counter}
        #delete by luoyibing
        #pagination_links = pagination_helper.get_links(obj_list)

        #if pagination_links:
           # collection[self._collection + "_links"] = pagination_links
        return collection

    def _item(self, request, id, do_authz=False, field_list=None,
              parent_id=None):
        """Retrieves and formats a single element of the requested entity."""
        kwargs = {'fields': field_list}
        action = self._plugin_handlers[self.SHOW]
        if parent_id:
            kwargs[self._parent_id_name] = parent_id
        obj_getter = getattr(self._plugin, action)
        obj = obj_getter(request.context, id, **kwargs)
        # Check authz
        # FIXME(salvatore-orlando): obj_getter might return references to
        # other resources. Must check authZ on them too.
        if do_authz:
            policy.enforce(request.context, action, obj)
        return obj

    def _get_items_by_filter_and_order_and_page(self, request,kwargs,original_fields=None,fields_to_add=None,do_authz=False, parent_id=None):
        """
        get resource items by filters,order,and page

        """
        sorting_helper = self._get_sorting_helper(request)#convert sort
        pagination_helper = self._get_pagination_helper(request) #convert paging
        sorting_helper.update_args(kwargs) #add sort to kwargs
        sorting_helper.update_fields(original_fields, fields_to_add)
        pagination_helper.update_args(kwargs) #add page to kwargs
        pagination_helper.update_fields(original_fields, fields_to_add)
        if parent_id:
            kwargs[self._parent_id_name] = parent_id
        obj_getter = getattr(self._plugin, self._plugin_handlers[self.LIST])

        obj_list = obj_getter(request.context, **kwargs)
        obj_list = sorting_helper.sort(obj_list)
        obj_list = pagination_helper.paginate(obj_list)
        # Check authz
        if do_authz and obj_list:
            # FIXME(salvatore-orlando): obj_getter might return references to
            # other resources. Must check authZ on them too.
            # Omit items from list that should not be visible
            obj_list = [obj for obj in obj_list
                        if policy.check(request.context,
                                        self._plugin_handlers[self.SHOW],
                                        obj,
                                        plugin=self._plugin)]
        return obj_list,pagination_helper

    def _get_items_count_by_filter(self,request,filters):
        """
        get request resource items count by filters
        return count,or None()
        """
        obj_counter = getattr(self._plugin, self._plugin_handlers[self.LIST]+"_count",None)
        if obj_counter:
                return obj_counter(request.context, filters)
        return -1

    def _send_dhcp_notification(self, context, data, methodname):
        if cfg.CONF.dhcp_agent_notification:
            if self._collection in data:
                for body in data[self._collection]:
                    item = {self._resource: body}
                    self._dhcp_agent_notifier.notify(context, item, methodname)
            else:
                self._dhcp_agent_notifier.notify(context, data, methodname)  #调用eutron.api.rpc.agentnotifiers.dhcp_rpc_agent_api.DhcpAgentNotifyAPI发送创建结束消息
                                                                             #{'args': {'payload': {'port': {'status': 'DOWN', 'binding:host_id': '', 'allowed_address_pairs': [], 'device_owner': '', 'binding:profile': {}, 'fixed_ips': [{'subnet_id': u'49c43896-6a7c-4321-9445-113250a2e987', 'ip_address': u'11.11.0.15'}], 'id': '9665340c-bf4e-4c71-9bce-63f880b7411b', 'security_groups': [u'06f739d6-cc9e-444a-bfee-c830ecec7cf2'], 'device_id': '', 'name': u'testnew111122222-port', 'admin_state_up': True, 'network_id': u'2bd09dd6-75e3-4e55-817e-c0d091854e36', 'tenant_id': u'8bcbc26515234902a12a0185b2a64bdd', 'binding:vif_details': {}, 'binding:vnic_type': 'normal', 'binding:vif_type': 'unbound', 'mac_address': 'fa:16:3e:23:6d:12'}}}, 'namespace': None, 'method': 'port_create_end'}) {'topic': u'dhcp_agent.controller'}

    def _send_nova_notification(self, action, orig, returned):
        if hasattr(self, '_nova_notifier'):
            self._nova_notifier.send_network_change(action, orig, returned)

    def index(self, request, **kwargs):
        """Returns a list of the requested entity."""
        parent_id = kwargs.get(self._parent_id_name)
        # Ensure policy engine is initialized
        policy.init()
        return self._items(request, True, parent_id)

    def show(self, request, id, **kwargs):
        """Returns detailed information about the requested entity."""
        try:
            # NOTE(salvatore-orlando): The following ensures that fields
            # which are needed for authZ policy validation are not stripped
            # away by the plugin before returning.
            field_list, added_fields = self._do_field_list(
                api_common.list_args(request, "fields"))
            parent_id = kwargs.get(self._parent_id_name)
            # Ensure policy engine is initialized
            policy.init()
            return {self._resource:
                    self._view(request.context,
                               self._item(request,
                                          id,
                                          do_authz=True,
                                          field_list=field_list,
                                          parent_id=parent_id),
                               fields_to_strip=added_fields)}
        except exceptions.PolicyNotAuthorized:
            # To avoid giving away information, pretend that it
            # doesn't exist
            msg = _('The resource could not be found.')
            raise webob.exc.HTTPNotFound(msg)

    def _emulate_bulk_create(self, obj_creator, request, body, parent_id=None):
        objs = []
        try:
            for item in body[self._collection]:
                kwargs = {self._resource: item}
                if parent_id:
                    kwargs[self._parent_id_name] = parent_id
                fields_to_strip = self._exclude_attributes_by_policy(
                    request.context, item)
                objs.append(self._filter_attributes(
                    request.context,
                    obj_creator(request.context, **kwargs),
                    fields_to_strip=fields_to_strip))
            return objs
        # Note(salvatore-orlando): broad catch as in theory a plugin
        # could raise any kind of exception
        except Exception as ex:
            for obj in objs:
                obj_deleter = getattr(self._plugin,
                                      self._plugin_handlers[self.DELETE])
                try:
                    kwargs = ({self._parent_id_name: parent_id} if parent_id
                              else {})
                    obj_deleter(request.context, obj['id'], **kwargs)
                except Exception:
                    # broad catch as our only purpose is to log the exception
                    LOG.exception(_("Unable to undo add for "
                                    "%(resource)s %(id)s"),
                                  {'resource': self._resource,
                                   'id': obj['id']})
            # TODO(salvatore-orlando): The object being processed when the
            # plugin raised might have been created or not in the db.
            # We need a way for ensuring that if it has been created,
            # it is then deleted
            raise ex

    def create(self, request, body=None, **kwargs):
        """Creates a new instance of the requested entity.
        add by luoyibing 2015-4-8
        :param request  wsgi.eg: 参数中包括很多属性  environ 类型dict,其中包括REQUEST_METHOD方法POST,RAW_PATH_INFO:"/v2.0/ports.json",'“”
        :param  body  type:dict  eg:port{ "network_id":"2bd09dd6-75e3-4e55-817e-c0d091854e36","name":"testnew-port","admin_state_up":true}
        :param  kwargs
        """

        parent_id = kwargs.get(self._parent_id_name)
        self._notifier.info(request.context,
                            self._resource + '.create.start',
                            body) #根据初始化通知时间，通知 port.create.start事件
        body = Controller.prepare_request_body(request.context, body, True,
                                               self._resource, self._attr_info,
                                               allow_bulk=self._allow_bulk) #获取Controller对象中neutron.context内容：里面  包含auth_token  3b4590cbbfc34d24a52fb54100f2865a,roler角色admin等信息
        action = self._plugin_handlers[self.CREATE] #获取具体的cation操作 如create_port
        # Check authz
        if self._collection in body:
            # Have to account for bulk create
            items = body[self._collection]
            deltas = {}
            bulk = True
        else:
            items = [body]
            bulk = False
        # Ensure policy engine is initialized
        policy.init()
        for item in items:
            self._validate_network_tenant_ownership(request,
                                                    item[self._resource])
            policy.enforce(request.context,
                           action,
                           item[self._resource])
            try:
                tenant_id = item[self._resource]['tenant_id']
                count = quota.QUOTAS.count(request.context, self._resource,
                                           self._plugin, self._collection,
                                           tenant_id)
                if bulk:
                    delta = deltas.get(tenant_id, 0) + 1
                    deltas[tenant_id] = delta
                else:
                    delta = 1
                kwargs = {self._resource: count + delta}
            except exceptions.QuotaResourceUnknown as e:
                # We don't want to quota this resource
                LOG.debug(e)
            else:
                quota.QUOTAS.limit_check(request.context,
                                         item[self._resource]['tenant_id'],
                                         **kwargs)

        def notify(create_result):
            notifier_method = self._resource + '.create.end' #eg:port.create.end
            self._notifier.info(request.context,
                                notifier_method,
                                create_result)#发送notifier消息，创建成功
            self._send_dhcp_notification(request.context,
                                         create_result,
                                         notifier_method)
            return create_result

        kwargs = {self._parent_id_name: parent_id} if parent_id else {}
        if self._collection in body and self._native_bulk:
            # plugin does atomic bulk create operations
            obj_creator = getattr(self._plugin, "%s_bulk" % action)
            objs = obj_creator(request.context, body, **kwargs)
            # Use first element of list to discriminate attributes which
            # should be removed because of authZ policies
            fields_to_strip = self._exclude_attributes_by_policy(
                request.context, objs[0])
            return notify({self._collection: [self._filter_attributes(
                request.context, obj, fields_to_strip=fields_to_strip)
                for obj in objs]})
        else: #非批量操作??
            obj_creator = getattr(self._plugin, action)#type :instancemethod <bound method Ml2Plugin.create_port of <neutron.plugins.ml2.plugin.Ml2Plugin object at 0x2565e10>>
            if self._collection in body:
                # Emulate atomic bulk behavior
                objs = self._emulate_bulk_create(obj_creator, request,
                                                 body, parent_id)
                return notify({self._collection: objs})
            else:
                kwargs.update({self._resource: body})
                obj = obj_creator(request.context, **kwargs)#具体执行操作，例如：M2Plugin 类中 create_port方法,反馈创建后的资源对象
                self._send_nova_notification(action, {},
                                             {self._resource: obj})#通知计算节点：对应资源，对应操作,eg： create_port,{port属性}
                return notify({self._resource: self._view(request.context,
                                                          obj)})

    def delete(self, request, id, **kwargs):
        """Deletes the specified entity."""
        self._notifier.info(request.context,
                            self._resource + '.delete.start',
                            {self._resource + '_id': id}) #通知
        action = self._plugin_handlers[self.DELETE]  #获取具体资源操作行为 eg delete_port

        # Check authz
        policy.init()
        parent_id = kwargs.get(self._parent_id_name)
        obj = self._item(request, id, parent_id=parent_id)
        try:
            policy.enforce(request.context,
                           action,
                           obj)                                    #检查操作权限
        except exceptions.PolicyNotAuthorized:
            # To avoid giving away information, pretend that it
            # doesn't exist
            msg = _('The resource could not be found.')
            raise webob.exc.HTTPNotFound(msg)

        obj_deleter = getattr(self._plugin, action) #获取具体操作方法 eg:M2lplugin类中delete_port
        obj_deleter(request.context, id, **kwargs)  #根据参数，执行具体操作方法
        notifier_method = self._resource + '.delete.end'
        self._notifier.info(request.context,
                            notifier_method,
                            {self._resource + '_id': id}) #消息格式??
        result = {self._resource: self._view(request.context, obj)}
        self._send_nova_notification(action, {}, result)  #通知nova消息,消息内容什么样的?
        self._send_dhcp_notification(request.context,          #通知dhcp消息，消息内容什么样的?
                                     result,
                                     notifier_method)

    def update(self, request, id, body=None, **kwargs):
        """Updates the specified entity's attributes."""
        parent_id = kwargs.get(self._parent_id_name)
        try:
            payload = body.copy()
        except AttributeError:
            msg = _("Invalid format: %s") % request.body
            raise exceptions.BadRequest(resource='body', msg=msg)
        payload['id'] = id
        self._notifier.info(request.context,
                            self._resource + '.update.start',
                            payload)
        body = Controller.prepare_request_body(request.context, body, False,
                                               self._resource, self._attr_info,
                                               allow_bulk=self._allow_bulk)
        action = self._plugin_handlers[self.UPDATE]
        # Load object to check authz
        # but pass only attributes in the original body and required
        # by the policy engine to the policy 'brain'
        field_list = [name for (name, value) in self._attr_info.iteritems()
                      if (value.get('required_by_policy') or
                          value.get('primary_key') or
                          'default' not in value)]
        # Ensure policy engine is initialized
        policy.init()
        orig_obj = self._item(request, id, field_list=field_list,
                              parent_id=parent_id)
        orig_object_copy = copy.copy(orig_obj)
        orig_obj.update(body[self._resource])
        # Make a list of attributes to be updated to inform the policy engine
        # which attributes are set explicitly so that it can distinguish them
        # from the ones that are set to their default values.
        orig_obj[const.ATTRIBUTES_TO_UPDATE] = body[self._resource].keys()
        try:
            policy.enforce(request.context,
                           action,
                           orig_obj)
        except exceptions.PolicyNotAuthorized:
            with excutils.save_and_reraise_exception() as ctxt:
                # If a tenant is modifying it's own object, it's safe to return
                # a 403. Otherwise, pretend that it doesn't exist to avoid
                # giving away information.
                if request.context.tenant_id != orig_obj['tenant_id']:
                    ctxt.reraise = False
            msg = _('The resource could not be found.')
            raise webob.exc.HTTPNotFound(msg)

        obj_updater = getattr(self._plugin, action)
        kwargs = {self._resource: body}
        if parent_id:
            kwargs[self._parent_id_name] = parent_id
        obj = obj_updater(request.context, id, **kwargs)
        result = {self._resource: self._view(request.context, obj)}
        notifier_method = self._resource + '.update.end'
        self._notifier.info(request.context, notifier_method, result)
        self._send_dhcp_notification(request.context,
                                     result,
                                     notifier_method)
        self._send_nova_notification(action, orig_object_copy, result)
        return result

    @staticmethod
    def _populate_tenant_id(context, res_dict, is_create):

        if (('tenant_id' in res_dict and
             res_dict['tenant_id'] != context.tenant_id and
             not context.is_admin)):
            msg = _("Specifying 'tenant_id' other than authenticated "
                    "tenant in request requires admin privileges")
            raise webob.exc.HTTPBadRequest(msg)

        if is_create and 'tenant_id' not in res_dict:
            if context.tenant_id:
                res_dict['tenant_id'] = context.tenant_id
            else:
                msg = _("Running without keystone AuthN requires "
                        " that tenant_id is specified")
                raise webob.exc.HTTPBadRequest(msg)

    @staticmethod
    def prepare_request_body(context, body, is_create, resource, attr_info,
                             allow_bulk=False):
        """Verifies required attributes are in request body.

        Also checking that an attribute is only specified if it is allowed
        for the given operation (create/update).

        Attribute with default values are considered to be optional.

        body argument must be the deserialized body.
        """
        #test at 2015.6.16-创建、更新子网时在测试平台无法指定"gateway_ip":null,只能指定为"gateway_ip":""
        # if body.get('subnet', None) is not None:
        #     if body.get('subnet').get('gateway_ip', None) == '':
        #         body['subnet'].update({'gateway_ip': None})

        collection = resource + "s"
        if not body:
            raise webob.exc.HTTPBadRequest(_("Resource body required"))

        LOG.debug(_("Request body: %(body)s"), {'body': body})
        if collection in body:
            if not allow_bulk:
                raise webob.exc.HTTPBadRequest(_("Bulk operation "
                                                 "not supported"))
            if not body[collection]:
                raise webob.exc.HTTPBadRequest(_("Resources required"))
            bulk_body = [
                Controller.prepare_request_body(
                    context, item if resource in item else {resource: item},
                    is_create, resource, attr_info, allow_bulk
                ) for item in body[collection]
            ]
            return {collection: bulk_body}

        res_dict = body.get(resource)
        if res_dict is None:
            msg = _("Unable to find '%s' in request body") % resource
            raise webob.exc.HTTPBadRequest(msg)

        Controller._populate_tenant_id(context, res_dict, is_create)
        Controller._verify_attributes(res_dict, attr_info)

        if is_create:  # POST
            for attr, attr_vals in attr_info.iteritems():
                if attr_vals['allow_post']:
                    if ('default' not in attr_vals and
                        attr not in res_dict):
                        msg = _("Failed to parse request. Required "
                                "attribute '%s' not specified") % attr
                        raise webob.exc.HTTPBadRequest(msg)
                    res_dict[attr] = res_dict.get(attr,
                                                  attr_vals.get('default'))
                else:
                    if attr in res_dict:
                        msg = _("Attribute '%s' not allowed in POST") % attr
                        raise webob.exc.HTTPBadRequest(msg)
        else:  # PUT
            for attr, attr_vals in attr_info.iteritems():
                if attr in res_dict and not attr_vals['allow_put']:
                    msg = _("Cannot update read-only attribute %s") % attr
                    raise webob.exc.HTTPBadRequest(msg)

        for attr, attr_vals in attr_info.iteritems():
            if (attr not in res_dict or
                res_dict[attr] is attributes.ATTR_NOT_SPECIFIED):
                continue
            # Convert values if necessary
            if 'convert_to' in attr_vals:
                res_dict[attr] = attr_vals['convert_to'](res_dict[attr])
            # Check that configured values are correct
            if 'validate' not in attr_vals:
                continue
            for rule in attr_vals['validate']:
                res = attributes.validators[rule](res_dict[attr],
                                                  attr_vals['validate'][rule])
                if res:
                    msg_dict = dict(attr=attr, reason=res)
                    msg = _("Invalid input for %(attr)s. "
                            "Reason: %(reason)s.") % msg_dict
                    raise webob.exc.HTTPBadRequest(msg)
        return body

    @staticmethod
    def _verify_attributes(res_dict, attr_info):
        extra_keys = set(res_dict.keys()) - set(attr_info.keys())
        if extra_keys:
            msg = _("Unrecognized attribute(s) '%s'") % ', '.join(extra_keys)
            raise webob.exc.HTTPBadRequest(msg)

    def _validate_network_tenant_ownership(self, request, resource_item):
        # TODO(salvatore-orlando): consider whether this check can be folded
        # in the policy engine
        if (request.context.is_admin or
                self._resource not in ('port', 'subnet')):
            return
        network = self._plugin.get_network(
            request.context,
            resource_item['network_id'])
        # do not perform the check on shared networks
        if network.get('shared'):
            return

        network_owner = network['tenant_id']

        if network_owner != resource_item['tenant_id']:
            msg = _("Tenant %(tenant_id)s not allowed to "
                    "create %(resource)s on this network")
            raise webob.exc.HTTPForbidden(msg % {
                "tenant_id": resource_item['tenant_id'],
                "resource": self._resource,
            })


def create_resource(collection, resource, plugin, params, allow_bulk=False,
                    member_actions=None, parent=None, allow_pagination=False,
                    allow_sorting=False):
    controller = Controller(plugin, collection, resource, params, allow_bulk,
                            member_actions=member_actions, parent=parent,
                            allow_pagination=allow_pagination,
                            allow_sorting=allow_sorting)

    return wsgi_resource.Resource(controller, FAULT_MAP)
