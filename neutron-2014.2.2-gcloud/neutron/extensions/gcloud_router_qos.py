__author__ = 'luoyb'
import abc
from oslo.config import cfg
import six
from neutron.api import extensions
from neutron.api.v2 import attributes as attr
from neutron.api.v2 import resource_helper
from neutron.api.v2 import attributes as attr
from neutron.services import service_base
from neutron.common import exceptions as qexception
from neutron.common import constants as com_const

positive_int = (1, attr.UNLIMITED)

RESOURCE_ATTRIBUTE_MAP = {
    'router_qoss': {
        "id":{
                    "allow_post":False,
                    "allow_put":True,
                    'validate': {'type:uuid': None},
                    "is_visible":True,
                    "primary_key":True
                    },
        "max_rate":
                    {
                     "allow_post":True,
                     "allow_put":True,
                     'validate': {'type:range_or_none': positive_int},
                     "is_visible":True,
                    },
        "name":
                    {
                     "allow_post":True,
                     'validate': {'type:string_or_none': 36},
                     "allow_put":True,
                     "is_visible":True,
                     'default': None
                    },
        'type':
                  {'allow_post':True,
                    'allow_put':False,
                   'is_visible':True,
                    'default': None,
                    'validate': {'type:values': com_const.EXT_NET_TYPE},
                     "is_visible":True,
                    },
        'tenant_id': {'allow_post': True, 'allow_put': False,
                      'required_by_policy': True,
                      'validate': {'type:string': None},
                      'is_visible': True},
        'ip_num': {'allow_post': False, 'allow_put': False,
                      'required_by_policy': True,
                      'is_visible': True}

    },
    'router_qosrules':
     {
        "id":{
                    "allow_put":False,
                    "allow_post":False,
                    'validate': {'type:uuid': None},
                    "is_visible":True,
                    "primary_key":True
                    },
        "max_rate":
                    {
                     "allow_post":False,
                     "allow_put":False,
                     'validate': {'type:range_or_none': positive_int},
                     "is_visible":True,
                    },
        "name":
                  {
                     "allow_post":True,
                     'validate': {'type:string_or_none': 36},
                     "allow_put":True,
                     "is_visible":True,
                      'default': None
                    },
        "qos_id":
                 {
                     "allow_post":False,
                     "allow_put":False,
                     "is_visible":True,
                      'default': None
                 }

     },
   'router_qosrule_binds':
       {
         "id":{
                    "allow_put":False,
                    "allow_post":False,
                    'validate': {'type:uuid': None},
                    "is_visible":True,
                    "primary_key":True
                    },
        "qos_id":
                  {

                     "allow_post":False,
                     'validate':{'type:uuid': None},
                     "allow_put":False,
                     "is_visible":True,
                    },
        "rule_id":
                  {
                     "allow_post":True,
                     'validate':{'type:uuid': None},
                     "allow_put":False,
                     "is_visible":True,
                    },
         "src_ip":
                  {
                     "allow_post":False,
                     "allow_put":False,
                     "is_visible":True,
                    },
           "port_id":
                 {
                     "allow_post":True,
                     'validate':{'type:uuid': None},
                     "allow_put":False,
                     "is_visible":True,
                    },
           "ip_type":
                 {
                     "allow_post":True,
                     'validate':{'type:values': com_const.IP_TYPE},
                     "allow_put":False,
                     "is_visible":True,
                    },
          'tenant_id':
              {
                 'allow_post': True,
                 'allow_put': False,
                 'required_by_policy': True,
                 'validate': {'type:string': None},
                 'is_visible': True
             }
       }

}

#EXTENDED_ATTRIBUTES_2_0 = {
#    'floatingips': {"qos": {'allow_post': False,
#                         'allow_put': False,
#                       'is_visible': True,
#                         'default': attr.ATTR_NOT_SPECIFIED}}}


class RouterQosNotFound(qexception.NotFound):
    message = _("Router qos %(id)s could not be found.")
    code = "neutron_server_gcloud_router_qos_000001"
class RouterQosRuleNotFound(qexception.NotFound):
    message = _("Router qos rule id %(id)s could not be found.")
    code = "neutron_server_gcloud_router_qos_000002"
class RouterQosRuleBindNotFound(qexception.NotFound):
    message = _("Router qos rule bind id %(id)s could not be found.")
    code = "neutron_server_gcloud_router_qos_000003"
class RouterQosPortIdInUse(qexception.Conflict):
    message = _("Router qos port  id %(port_id)s is in used.")
    code = "neutron_server_gcloud_router_qos_000004"
class RouterQosTypeNotSame(qexception.Conflict):
    message = _("Router port_id %(port_id)s type is not  the same qos_id  %(qos_id)s ")
    code = "neutron_server_gcloud_router_qos_000005"
#class RouterQosRuleNotInFound(qexception.NotFound):
#    message = _("Router qos rule  id %(rule_id)s is not found.")
#    code = "neutron_server_gcloud_router_qos_000006"
class RouterIpInfoNotInFound(qexception.NotFound):
    message = _("Router qos  port_id %(port_id)s is not found.")
    code = "neutron_server_gcloud_router_qos_000007"
class RouterQosRouterPluginNotInFound(qexception.NotFound):
     message = _("Router qos  router l3 plugin  is not found.")
     code = "neutron_server_gcloud_router_qos_000008"
class Gcloud_router_qos(extensions.ExtensionDescriptor):
    """
     defines the description for extensions.
    """

    def get_resources(self):
        special_mappings = {'router_qoss': 'router_qos',"router_qosrules":"router_qosrule","router_qosrule_binds":"router_qosrule_bind"}
        plural_mappings = resource_helper.build_plural_mappings(
            special_mappings, RESOURCE_ATTRIBUTE_MAP)
        attr.PLURALS.update(plural_mappings)
        action_map = {}
        return resource_helper.build_resource_info(plural_mappings,
                                                   RESOURCE_ATTRIBUTE_MAP,
                                         "gcloud_router_qos",
                                                   action_map=action_map)

    @classmethod
    def get_name(cls):
        return "Provider Network Qos"

    @classmethod
    def get_alias(cls):
        return "gcloud_router_qos"

    @classmethod
    def get_description(cls):
        return "gcloud router qos"


    @classmethod
    def get_namespace(cls):
         return "neutron.service_plugins"

    @classmethod
    def get_updated(cls):
        return "2016-03-1T10:00:00-00:00"
    @classmethod
    def get_plugin_interface(cls):
        return GcloudRouterQosPluginBase

    def get_extended_resources(self, version):
        #if version == "2.0":
         #   return RESOURCE_ATTRIBUTE_MAP
        #else:
            return {}


@six.add_metaclass(abc.ABCMeta)
class GcloudRouterQosPluginBase(service_base.ServicePluginBase):
    def get_plugin_description(self):
        return "gcloud_router_qos"
    def get_plugin_name(self):
        return "gcloud_router_qos"
    def get_plugin_type(self):
        return "gcloud_router_qos"

    @abc.abstractmethod
    def get_router_qos(self, context, id, fields=None):
        pass
    @abc.abstractmethod
    def create_router_qos(self, context, router_qos):
        pass

    @abc.abstractmethod
    def update_router_qos(self, context,id,router_qos):
        pass

    @abc.abstractmethod
    def delete_router_qos(self, context,id):
        pass

    @abc.abstractmethod
    def get_router_qoss(self, context,filters=None, fields=None,
                        sorts=None, limit=None, marker=None,
                        page_reverse=False,offset=None):
        pass

    @abc.abstractmethod
    def get_router_qoss_count(self, context,filters=None):
        pass

    @abc.abstractmethod
    def get_router_qosrules(self, context,filters=None, fields=None,
                        sorts=None, limit=None, marker=None,
                        page_reverse=False,offset=None):
        pass
    @abc.abstractmethod
    def get_router_qosrules_count(self, context,filters=None):
        pass

    @abc.abstractmethod
    def create_router_qosrule_bind(self, context, router_qosrule_bind):
        pass

    @abc.abstractmethod
    def delete_router_qosrule_bind(self, context, id):
        pass

    @abc.abstractmethod
    def get_router_qosrule_binds(self, context,filters=None, fields=None,
                        sorts=None, limit=None, marker=None,
                        page_reverse=False, offset=None):
        pass

    @abc.abstractmethod
    def get_router_qosrule_binds_count(self, context,filters=None):
        pass







