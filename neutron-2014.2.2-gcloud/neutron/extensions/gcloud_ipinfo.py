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

RESOURCE_ATTRIBUTE_MAP = {
    "ipinfos": {
        'subnet_id': {
            'allow_post': False,
            'allow_put': False,
            'validate': {'type:uuid': None},
            'is_visible': True,
        },
        'ip_total_num': {
            "allow_post": False,
            "allow_put": False,
            'validate': {'type:range_or_none': positive_int},
            "is_visible": True,
        },
        'ip_used_num': {
            "allow_post": False,
            "allow_put": False,
            'validate': {'type:range_or_none': positive_int},
            "is_visible": True,
        },
        'ip_free_num': {
            "allow_post": False,
            "allow_put": False,
            'validate': {'type:range_or_none': positive_int},
            "is_visible": True,
        },
    },
}

class IpInfoNotFound(qexception.NotFound):
    message = _("ipinfo %(id)s is could not be found.")

class Gcloud_ipinfo(extensions.ExtensionDescriptor):
    """
     defines the description for extensions.
    """

    def get_resources(self):
        special_mappings = {'ipinfos': 'ipinfo'}
        plural_mappings = resource_helper.build_plural_mappings(
            special_mappings, RESOURCE_ATTRIBUTE_MAP)
        attr.PLURALS.update(plural_mappings)
        action_map = {}
        return resource_helper.build_resource_info(plural_mappings,
                                                   RESOURCE_ATTRIBUTE_MAP,
                                         "ipinfo",
                                                   action_map=action_map)

    @classmethod
    def get_name(cls):
        return "Provider subnet ipinfo"

    @classmethod
    def get_alias(cls):
        return "ipinfo"

    @classmethod
    def get_description(cls):
        return ("provide ipinfo of subnet")

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
class GcloudIpInfoPluginBase(service_base.ServicePluginBase):
    def get_plugin_description(self):
        return "ipinfo"
    def get_plugin_name(self):
        return "ipinfo"
    def get_plugin_type(self):
        return "ipinfo"
    @abc.abstractmethod
    def get_ipinfo(self, context, id, fields=None):
        pass
    @abc.abstractmethod
    def get_ipinfos(self, context, filters=None, fields=None,
                    sorts=None, limit=None, marker=None,
                    page_reverse=False, offset=None):
        pass

