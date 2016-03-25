__author__ = 'luoyb'

import abc
from oslo.config import cfg
import six
from neutron.api import extensions
from neutron.api.v2 import attributes as attr
from neutron.api.v2 import resource_helper
from neutron.common import exceptions as qexception
from neutron.openstack.common import log as logging
from neutron.plugins.common import constants
from neutron.services import service_base
from neutron import manager
from neutron import quota
from neutron.api.v2 import base

EXTENDED_ATTRIBUTES_2_0 = {
    'phynetworks': {
        "phydev": {
            'allow_post': False,
            'allow_put': False,
            'default': "eth0",
            'enforce_policy': True,
            'is_visible': True
        }
    },
    'networktypes': {
        "nettype": {
            'allow_post': False,
            'allow_put': False,
            'default': "vlan",
            'enforce_policy': True,
            'is_visible': True
        }
    }
}

class Phynetwork(extensions.ExtensionDescriptor):
    """
     defines the description for extensions.
    """
    @classmethod
    def get_resources(self):
       # plural_mappings = resource_helper.build_plural_mappings(
       #     {}, EXTENDED_ATTRIBUTES_2_0)
       # attr.PLURALS.update(plural_mappings)
       # action_map = {'phynetworks': {'get_phynetworks': 'GET'},"phynetwork":{'get_phynetwork':'GET'}}
        # PCM: Metering sets pagination and sorting to True. Do we have cfg
        # entries for these so can be read? Else, must pass in.
      #  return resource_helper.build_resource_info(plural_mappings,
       #                                            EXTENDED_ATTRIBUTES_2_0,
      #                                            "phynetwork",
       #                                         action_map)

        # special_mappings = {'phynetworks': 'phynetwork', 'networktypes': 'networktype'}
        # plural_mappings = resource_helper.build_plural_mappings(
        #     special_mappings, EXTENDED_ATTRIBUTES_2_0)
        # attr.PLURALS.update(plural_mappings)
        # action_map = {}
        # return resource_helper.build_resource_info(plural_mappings,
        #                                            EXTENDED_ATTRIBUTES_2_0,
        #                                            "phynetwork",
        #                                            action_map=action_map)

        my_plurals = [(key, key[:-1]) for key in EXTENDED_ATTRIBUTES_2_0.keys()]
        attr.PLURALS.update(dict(my_plurals))
        exts = []
        #plugin = manager.NeutronManager.get_plugin()
        plugin = manager.NeutronManager.get_service_plugins()['phynetwork']
        for resource_name in ['phynetwork', 'networktype']:
            collection_name = resource_name.replace('_', '-') + "s"
            params = EXTENDED_ATTRIBUTES_2_0.get(resource_name + "s", dict())
            quota.QUOTAS.register_resource_by_name(resource_name)
            controller = base.create_resource(collection_name,
                                              resource_name,
                                              plugin, params, allow_bulk=True,
                                              allow_pagination=True,
                                              allow_sorting=True)

            ex = extensions.ResourceExtension(collection_name,
                                              controller,
                                              attr_map=params)
            exts.append(ex)

        return exts


    @classmethod
    def get_name(cls):
        return "Multi Provider Network"

    @classmethod
    def get_alias(cls):
        return "phynetwork"

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
class PhyNetworkPluginBase(service_base.ServicePluginBase):
    def get_plugin_description(self):
        return "phynetwork"
    def get_plugin_name(self):
        return "phynetwork"
    def get_plugin_type(self):
        return "phynetwork"
    @abc.abstractmethod
    def get_phynetworks(self, context, filters=None, fields=None):
        pass
    @abc.abstractmethod
    def get_phynetwork(self, context, id, fields=None):
        pass
    @abc.abstractmethod
    def get_networktypes(self, context, filters=None, fields=None):
        pass