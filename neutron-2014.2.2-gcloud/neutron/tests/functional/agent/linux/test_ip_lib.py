# Copyright (c) 2014 Red Hat, Inc.
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

import collections

from oslo.config import cfg

from neutron.agent.common import config
from neutron.agent.linux import interface
from neutron.agent.linux import ip_lib
from neutron.common import utils
from neutron.openstack.common import importutils
from neutron.openstack.common import log as logging
from neutron.tests.functional.agent.linux import base

LOG = logging.getLogger(__name__)
Device = collections.namedtuple('Device', 'name ip_cidr mac_address namespace')


class IpLibTestFramework(base.BaseLinuxTestCase):
    def setUp(self):
        super(IpLibTestFramework, self).setUp()
        self.check_sudo_enabled()
        self._configure()

    def _configure(self):
        config.setup_logging()
        config.register_root_helper(cfg.CONF)
        cfg.CONF.set_override('root_helper', self.root_helper, group='AGENT')
        config.register_interface_driver_opts_helper(cfg.CONF)
        cfg.CONF.set_override(
            'interface_driver',
            'neutron.agent.linux.interface.OVSInterfaceDriver')
        cfg.CONF.register_opts(interface.OPTS)
        self.driver = importutils.import_object(cfg.CONF.interface_driver,
                                                cfg.CONF)

    def generate_device_details(self, name=None, ip_cidr=None,
                                mac_address=None, namespace=None):
        return Device(name or self.get_rand_name(),
                      ip_cidr or '240.0.0.1/24',
                      mac_address or
                      utils.get_random_mac('fa:16:3e:00:00:00'.split(':')),
                      namespace or self.get_rand_name())

    def _safe_delete_device(self, device):
        try:
            device.link.delete()
        except RuntimeError:
            LOG.debug('Could not delete %s, was it already deleted?', device)

    def manage_device(self, attr):
        """Create a tuntap with the specified attributes.

        The device is cleaned up at the end of the test.

        :param attr: A Device namedtuple
        :return: A tuntap ip_lib.IPDevice
        """
        ip = ip_lib.IPWrapper(self.root_helper, namespace=attr.namespace)
        ip.netns.add(attr.namespace)
        self.addCleanup(ip.netns.delete, attr.namespace)
        tap_device = ip.add_tuntap(attr.name)
        self.addCleanup(self._safe_delete_device, tap_device)
        tap_device.link.set_address(attr.mac_address)
        self.driver.init_l3(attr.name, [attr.ip_cidr],
                            namespace=attr.namespace)
        tap_device.link.set_up()
        return tap_device


class IpLibTestCase(IpLibTestFramework):
    def test_device_exists(self):
        attr = self.generate_device_details()

        self.assertFalse(
            ip_lib.device_exists(attr.name, self.root_helper,
                                 attr.namespace))

        device = self.manage_device(attr)

        self.assertTrue(
            ip_lib.device_exists(device.name, self.root_helper,
                                 attr.namespace))

        device.link.delete()

        self.assertFalse(
            ip_lib.device_exists(attr.name, self.root_helper,
                                 attr.namespace))

    def test_device_exists_with_ip_mac(self):
        attr = self.generate_device_details()
        device = self.manage_device(attr)
        self.assertTrue(
            ip_lib.device_exists_with_ip_mac(
                *attr, root_helper=self.root_helper))

        wrong_ip_cidr = '10.0.0.1/8'
        wrong_mac_address = 'aa:aa:aa:aa:aa:aa'

        attr = self.generate_device_details(name='wrong_name')
        self.assertFalse(
            ip_lib.device_exists_with_ip_mac(
                *attr, root_helper=self.root_helper))

        attr = self.generate_device_details(ip_cidr=wrong_ip_cidr)
        self.assertFalse(
            ip_lib.device_exists_with_ip_mac(
                *attr, root_helper=self.root_helper))

        attr = self.generate_device_details(mac_address=wrong_mac_address)
        self.assertFalse(
            ip_lib.device_exists_with_ip_mac(
                *attr, root_helper=self.root_helper))

        attr = self.generate_device_details(namespace='wrong_namespace')
        self.assertFalse(
            ip_lib.device_exists_with_ip_mac(
                *attr, root_helper=self.root_helper))

        device.link.delete()
