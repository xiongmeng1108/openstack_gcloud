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

positive_int = (1, attr.UNLIMITED)

RESOURCE_ATTRIBUTE_MAP = {
    'qoss': {
        "port_id":{
                    "allow_post":True,
                    "allow_put":True,
                    'validate': {'type:uuid': None},
                    "is_visible":True,
                    "primary_key":True
                    },
        "ingress":
                    {
                    "allow_post":True,
                    'validate': {'type:range_or_none': positive_int},
                    "allow_put":True,
                    "is_visible":True,
                    },
        "outgress":
                    {
                     "allow_post":True,
                     'validate': {'type:range_or_none': positive_int},
                     "allow_put":True,
                     "is_visible":True,
                    },
        'tenant_id': {'allow_post': True, 'allow_put': False,
                      'required_by_policy': True,
                      'is_visible': True},
    }
}

EXTENDED_ATTRIBUTES_2_0 = {
    'ports': {"qos": {'allow_post': False,
                         'allow_put': False,
                        'is_visible': True,
                         'default': attr.ATTR_NOT_SPECIFIED}}}

class QosPortNotFound(qexception.NotFound):
    message = _("Port %(id)s is could not be found.")

class Gcloud_qos(extensions.ExtensionDescriptor):
    """
     defines the description for extensions.
    """

    def get_resources(self):
        special_mappings = {'qoss': 'qos'}
        plural_mappings = resource_helper.build_plural_mappings(
            special_mappings, RESOURCE_ATTRIBUTE_MAP)
        attr.PLURALS.update(plural_mappings)
        action_map = {}
        return resource_helper.build_resource_info(plural_mappings,
                                                   RESOURCE_ATTRIBUTE_MAP,
                                         "qos",
                                                   action_map=action_map)

    @classmethod
    def get_name(cls):
        return "Provider Network Qos"

    @classmethod
    def get_alias(cls):
        return "qos"

    @classmethod
    def get_description(cls):
        return ("Expose mapping of virtual networks to multiple physical "
                "networks")

    @classmethod
    def get_namespace(cls):
         return "neutron.service_plugins"

    @classmethod
    def get_updated(cls):
        return "2013-06-27T10:00:00-00:00"

    def get_extended_resources(self, version):
        if version == "2.0":
            return EXTENDED_ATTRIBUTES_2_0
        else:
            return {}

@six.add_metaclass(abc.ABCMeta)
class GcloudQosPluginBase(service_base.ServicePluginBase):
    def get_plugin_description(self):
        return "qos"
    def get_plugin_name(self):
        return "qos"
    def get_plugin_type(self):
        return "qos"
    @abc.abstractmethod
    def get_qos(self, context, id, fields=None):
        pass
    @abc.abstractmethod
    def create_qos(self, context, qos):
        pass
    @abc.abstractmethod
    def update_qos(self, context,id,qos):
        pass

