__author__ = 'xm'
import abc
from oslo.config import cfg
import six
from neutron.api import extensions
from neutron.api.v2 import attributes as attr
from neutron.api.v2 import resource_helper
from neutron.api.v2 import attributes as attr
from neutron.services import service_base
from neutron.common import exceptions as qexception

positive_int = (1, attr.UNLIMITED)
positive_int_range = (1, 65535)

class NatNotFound(qexception.NotFound):
    message = _("Gcloud_Nat %(nat_id)s could not be found")
    code = "neutron_server_gcloud_nat_000001"

class GatewayNotSet(qexception.NotFound):
    message = _("Gcloud_Nat: the router %(router_id)s must set extnet_gateway first!")
    code = "neutron_server_gcloud_nat_000002"

class InvalidateGcloudNatRule1(qexception.Conflict):
    message = _("InvalidateGcloudNatRule! the ext_port=%(ext_port)s of the router=%(router_id)s exist!")
    code = "neutron_server_gcloud_nat_000003"

class InvalidateGcloudNatRule2(qexception.Conflict):
    message = _("InvalidateGcloudNatRule! the int_port=%(int_port)s of the port=%(port_id)s exist!")
    code = "neutron_server_gcloud_nat_000004"

class SubnetNotHAveRouterInterface(qexception.NeutronException):
    message = _("nat ip can not reach  the port=%(port_id)s ")
    code = "neutron_server_gcloud_nat_000005"
RESOURCE_ATTRIBUTE_MAP = {
    "gcloud_nats": {
        'tenant_id': {
            'allow_post': True,
            'allow_put': False,
            'required_by_policy': True,
            'validate': {'type:string': None},
            'is_visible': True
        },
        'id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True,
            'primary_key': True
        },
        'router_id': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True
        },
        'port_id': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True,
        },
        'gw_port_id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True,
        },
        'ext_ip': {
            'allow_post': False,
            'allow_put': False,
            'default': None,
            'validate': {'type:ip_address_or_none': None},
            'is_visible': True
        },
        'ext_port': {
            "allow_post": True,
            "allow_put": True,
            'default': None,
            'validate': {'type:range_or_none': positive_int_range},
            "is_visible": True
        },
        'int_ip': {
            "allow_post": False,
            "allow_put": False,
            'default': None,
            'validate': {'type:ip_address_or_none': None},
            "is_visible": True
        },
        'int_port': {
            "allow_post": True,
            "allow_put": True,
            'default': None,
            'validate': {'type:range_or_none': positive_int_range},
            "is_visible": True
        },
        'create_time': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True
        },
        'user_id': {
            'allow_post': False,
            'allow_put': False,
            'is_visible': True
        },
    },

}

class Gcloud_nat(extensions.ExtensionDescriptor):
    """
     defines the description for extensions.
    """

    def get_resources(self):
        special_mappings = {'gcloud_nats': 'gcloud_nat'}
        plural_mappings = resource_helper.build_plural_mappings(
            special_mappings, RESOURCE_ATTRIBUTE_MAP)
        attr.PLURALS.update(plural_mappings)
        action_map = {}
        return resource_helper.build_resource_info(plural_mappings,
                                                   RESOURCE_ATTRIBUTE_MAP,
                                                   "gcloud_nat",
                                                   action_map=action_map)

    @classmethod
    def get_name(cls):
        return "Provider gcloud router_gateway nat"

    @classmethod
    def get_alias(cls):
        return "gcloud_nat"

    @classmethod
    def get_description(cls):
        return ("provide nat of router_gateway")

    @classmethod
    def get_namespace(cls):
         return "neutron.service_plugins"

    @classmethod
    def get_updated(cls):
        return "2013-06-27T10:00:00-00:00"

    def get_extended_resources(self, version):
        if version == "2.0":
            return RESOURCE_ATTRIBUTE_MAP
        else:
            return {}

@six.add_metaclass(abc.ABCMeta)
class GcloudNatPluginBase(service_base.ServicePluginBase):

    def get_plugin_description(self):
        return "gcloud_nat"

    def get_plugin_name(self):
        return "gcloud_nat"

    def get_plugin_type(self):
        return "gcloud_nat"

    @abc.abstractmethod
    def get_gcloud_nat(self, context, id, fields=None):
        pass

    @abc.abstractmethod
    def get_gcloud_nats(self, context, filters=None, fields=None,
                    sorts=None, limit=None, marker=None,
                    page_reverse=False, offset=None):
        pass

    @abc.abstractmethod
    def create_gcloud_nat(self, context, gcloud_nat):
        pass

    @abc.abstractmethod
    def update_gcloud_nat(self, context, id, gcloud_nat):
        pass

    @abc.abstractmethod
    def delete_gcloud_nat(self, context, id):
        pass

    def delete_gcloud_nats(self,context,router_id):
        pass