# Copyright (C) 2013 eNovance SAS <licensing@enovance.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock

from neutron.api.v2 import attributes as attr
from neutron.common import constants as n_constants
from neutron.common import topics
from neutron import context
from neutron.db import agents_db
from neutron.db import l3_agentschedulers_db
from neutron.db.metering import metering_rpc
from neutron.extensions import l3 as ext_l3
from neutron.extensions import metering as ext_metering
from neutron import manager
from neutron.openstack.common import timeutils
from neutron.openstack.common import uuidutils
from neutron.plugins.common import constants
from neutron.tests.unit.db.metering import test_db_metering
from neutron.tests.unit import test_db_plugin
from neutron.tests.unit import test_l3_plugin


_uuid = uuidutils.generate_uuid

METERING_SERVICE_PLUGIN_KLASS = (
    "neutron.services.metering."
    "metering_plugin.MeteringPlugin"
)


class MeteringTestExtensionManager(object):

    def get_resources(self):
        attr.RESOURCE_ATTRIBUTE_MAP.update(ext_metering.RESOURCE_ATTRIBUTE_MAP)
        attr.RESOURCE_ATTRIBUTE_MAP.update(ext_l3.RESOURCE_ATTRIBUTE_MAP)

        l3_res = ext_l3.L3.get_resources()
        metering_res = ext_metering.Metering.get_resources()

        return l3_res + metering_res

    def get_actions(self):
        return []

    def get_request_extensions(self):
        return []


class TestMeteringPlugin(test_db_plugin.NeutronDbPluginV2TestCase,
                         test_l3_plugin.L3NatTestCaseMixin,
                         test_db_metering.MeteringPluginDbTestCaseMixin):

    resource_prefix_map = dict(
        (k.replace('_', '-'), constants.COMMON_PREFIXES[constants.METERING])
        for k in ext_metering.RESOURCE_ATTRIBUTE_MAP.keys()
    )

    def setUp(self):
        plugin = 'neutron.tests.unit.test_l3_plugin.TestL3NatIntPlugin'
        service_plugins = {'metering_plugin_name':
                           METERING_SERVICE_PLUGIN_KLASS}
        ext_mgr = MeteringTestExtensionManager()
        super(TestMeteringPlugin, self).setUp(plugin=plugin, ext_mgr=ext_mgr,
                                              service_plugins=service_plugins)

        self.uuid = '654f6b9d-0f36-4ae5-bd1b-01616794ca60'

        uuid = 'neutron.openstack.common.uuidutils.generate_uuid'
        self.uuid_patch = mock.patch(uuid, return_value=self.uuid)
        self.mock_uuid = self.uuid_patch.start()

        fanout = ('neutron.common.rpc.RpcProxy.fanout_cast')
        self.fanout_patch = mock.patch(fanout)
        self.mock_fanout = self.fanout_patch.start()

        self.tenant_id = 'a7e61382-47b8-4d40-bae3-f95981b5637b'
        self.ctx = context.Context('', self.tenant_id, is_admin=True)
        self.context_patch = mock.patch('neutron.context.Context',
                                        return_value=self.ctx)
        self.mock_context = self.context_patch.start()

        self.topic = 'metering_agent'

    def test_add_metering_label_rpc_call(self):
        second_uuid = 'e27fe2df-376e-4ac7-ae13-92f050a21f84'
        expected = {'args': {'routers': [{'status': 'ACTIVE',
                                          'name': 'router1',
                                          'gw_port_id': None,
                                          'admin_state_up': True,
                                          'tenant_id': self.tenant_id,
                                          '_metering_labels': [
                                              {'rules': [],
                                               'id': self.uuid}],
                                          'id': self.uuid}]},
                    'namespace': None,
                    'method': 'add_metering_label'}

        tenant_id_2 = '8a268a58-1610-4890-87e0-07abb8231206'
        self.mock_uuid.return_value = second_uuid
        with self.router(name='router2', tenant_id=tenant_id_2,
                         set_context=True):
            self.mock_uuid.return_value = self.uuid
            with self.router(name='router1', tenant_id=self.tenant_id,
                             set_context=True):
                with self.metering_label(tenant_id=self.tenant_id,
                                         set_context=True):
                    self.mock_fanout.assert_called_with(self.ctx, expected)

    def test_add_metering_label_shared_rpc_call(self):
        second_uuid = 'e27fe2df-376e-4ac7-ae13-92f050a21f84'
        expected = {'args': {'routers': [{'status': 'ACTIVE',
                                          'name': 'router1',
                                          'gw_port_id': None,
                                          'admin_state_up': True,
                                          'tenant_id': self.tenant_id,
                                          '_metering_labels': [
                                              {'rules': [],
                                               'id': self.uuid},
                                              {'rules': [],
                                               'id': second_uuid}],
                                          'id': self.uuid}]},
                    'namespace': None,
                    'method': 'add_metering_label'}

        tenant_id_2 = '8a268a58-1610-4890-87e0-07abb8231206'
        with self.router(name='router1', tenant_id=self.tenant_id,
                         set_context=True):
            with self.metering_label(tenant_id=self.tenant_id,
                                     set_context=True):
                self.mock_uuid.return_value = second_uuid
                with self.metering_label(tenant_id=tenant_id_2, shared=True,
                                         set_context=True):
                    self.mock_fanout.assert_called_with(self.ctx, expected)

    def test_remove_metering_label_rpc_call(self):
        expected = {'args':
                    {'routers': [{'status': 'ACTIVE',
                                  'name': 'router1',
                                  'gw_port_id': None,
                                  'admin_state_up': True,
                                  'tenant_id': self.tenant_id,
                                  '_metering_labels': [
                                      {'rules': [],
                                       'id': self.uuid}],
                                  'id': self.uuid}]},
                    'namespace': None,
                    'method': 'add_metering_label'}

        with self.router(tenant_id=self.tenant_id, set_context=True):
            with self.metering_label(tenant_id=self.tenant_id,
                                     set_context=True):
                self.mock_fanout.assert_called_with(self.ctx, expected)
            expected['method'] = 'remove_metering_label'
            self.mock_fanout.assert_called_with(self.ctx, expected)

    def test_remove_one_metering_label_rpc_call(self):
        second_uuid = 'e27fe2df-376e-4ac7-ae13-92f050a21f84'
        expected_add = {'args':
                        {'routers': [{'status': 'ACTIVE',
                                      'name': 'router1',
                                      'gw_port_id': None,
                                      'admin_state_up': True,
                                      'tenant_id': self.tenant_id,
                                      '_metering_labels': [
                                          {'rules': [],
                                           'id': self.uuid},
                                          {'rules': [],
                                           'id': second_uuid}],
                                      'id': self.uuid}]},
                        'namespace': None,
                        'method': 'add_metering_label'}
        expected_remove = {'args':
                           {'routers': [{'status': 'ACTIVE',
                                         'name': 'router1',
                                         'gw_port_id': None,
                                         'admin_state_up': True,
                                         'tenant_id': self.tenant_id,
                                         '_metering_labels': [
                                             {'rules': [],
                                              'id': second_uuid}],
                                         'id': self.uuid}]},
                           'namespace': None,
                           'method': 'remove_metering_label'}

        with self.router(tenant_id=self.tenant_id, set_context=True):
            with self.metering_label(tenant_id=self.tenant_id,
                                     set_context=True):
                self.mock_uuid.return_value = second_uuid
                with self.metering_label(tenant_id=self.tenant_id,
                                         set_context=True):
                    self.mock_fanout.assert_called_with(self.ctx, expected_add)
                self.mock_fanout.assert_called_with(self.ctx, expected_remove)

    def test_update_metering_label_rules_rpc_call(self):
        second_uuid = 'e27fe2df-376e-4ac7-ae13-92f050a21f84'
        expected_add = {'args':
                        {'routers': [
                            {'status': 'ACTIVE',
                             'name': 'router1',
                             'gw_port_id': None,
                             'admin_state_up': True,
                             'tenant_id': self.tenant_id,
                             '_metering_labels': [
                                 {'rules': [
                                     {'remote_ip_prefix': '10.0.0.0/24',
                                      'direction': 'ingress',
                                      'metering_label_id': self.uuid,
                                      'excluded': False,
                                      'id': self.uuid},
                                     {'remote_ip_prefix': '10.0.0.0/24',
                                      'direction': 'egress',
                                      'metering_label_id': self.uuid,
                                      'excluded': False,
                                      'id': second_uuid}],
                                  'id': self.uuid}],
                             'id': self.uuid}]},
                        'namespace': None,
                        'method': 'update_metering_label_rules'}

        expected_del = {'args':
                        {'routers': [
                            {'status': 'ACTIVE',
                             'name': 'router1',
                             'gw_port_id': None,
                             'admin_state_up': True,
                             'tenant_id': self.tenant_id,
                             '_metering_labels': [
                                 {'rules': [
                                     {'remote_ip_prefix': '10.0.0.0/24',
                                      'direction': 'ingress',
                                      'metering_label_id': self.uuid,
                                      'excluded': False,
                                      'id': self.uuid}],
                                  'id': self.uuid}],
                             'id': self.uuid}]},
                        'namespace': None,
                        'method': 'update_metering_label_rules'}

        with self.router(tenant_id=self.tenant_id, set_context=True):
            with self.metering_label(tenant_id=self.tenant_id,
                                     set_context=True) as label:
                l = label['metering_label']
                with self.metering_label_rule(l['id']):
                    self.mock_uuid.return_value = second_uuid
                    with self.metering_label_rule(l['id'], direction='egress'):
                        self.mock_fanout.assert_called_with(self.ctx,
                                                            expected_add)
                    self.mock_fanout.assert_called_with(self.ctx,
                                                        expected_del)

    def test_delete_metering_label_does_not_clear_router_tenant_id(self):
        tenant_id = '654f6b9d-0f36-4ae5-bd1b-01616794ca60'
        with self.metering_label(tenant_id=tenant_id,
                                 do_delete=False) as metering_label:
            with self.router(tenant_id=tenant_id, set_context=True) as r:
                router = self._show('routers', r['router']['id'])
                self.assertEqual(tenant_id, router['router']['tenant_id'])
                metering_label_id = metering_label['metering_label']['id']
                self._delete('metering-labels', metering_label_id, 204)
                router = self._show('routers', r['router']['id'])
                self.assertEqual(tenant_id, router['router']['tenant_id'])


class TestMeteringPluginL3AgentScheduler(
        l3_agentschedulers_db.L3AgentSchedulerDbMixin,
        test_db_plugin.NeutronDbPluginV2TestCase,
        test_l3_plugin.L3NatTestCaseMixin,
        test_db_metering.MeteringPluginDbTestCaseMixin):

    resource_prefix_map = dict(
        (k.replace('_', '-'), constants.COMMON_PREFIXES[constants.METERING])
        for k in ext_metering.RESOURCE_ATTRIBUTE_MAP.keys()
    )

    def setUp(self, plugin_str=None, service_plugins=None, scheduler=None):
        if not plugin_str:
            plugin_str = ('neutron.tests.unit.test_l3_plugin.'
                          'TestL3NatIntAgentSchedulingPlugin')

        if not service_plugins:
            service_plugins = {'metering_plugin_name':
                               METERING_SERVICE_PLUGIN_KLASS}

        if not scheduler:
            scheduler = plugin_str

        ext_mgr = MeteringTestExtensionManager()
        super(TestMeteringPluginL3AgentScheduler,
              self).setUp(plugin=plugin_str, ext_mgr=ext_mgr,
                          service_plugins=service_plugins)

        self.uuid = '654f6b9d-0f36-4ae5-bd1b-01616794ca60'

        uuid = 'neutron.openstack.common.uuidutils.generate_uuid'
        self.uuid_patch = mock.patch(uuid, return_value=self.uuid)
        self.mock_uuid = self.uuid_patch.start()

        cast = 'neutron.common.rpc.RpcProxy.cast'
        self.cast_patch = mock.patch(cast)
        self.mock_cast = self.cast_patch.start()

        self.tenant_id = 'a7e61382-47b8-4d40-bae3-f95981b5637b'
        self.ctx = context.Context('', self.tenant_id, is_admin=True)
        self.context_patch = mock.patch('neutron.context.Context',
                                        return_value=self.ctx)
        self.mock_context = self.context_patch.start()

        self.l3routers_patch = mock.patch(scheduler +
                                          '.get_l3_agents_hosting_routers')
        self.l3routers_mock = self.l3routers_patch.start()

        self.topic = 'metering_agent'

    def test_add_metering_label_rpc_call(self):
        second_uuid = 'e27fe2df-376e-4ac7-ae13-92f050a21f84'
        expected1 = {'args': {'routers': [{'status': 'ACTIVE',
                                           'name': 'router1',
                                           'gw_port_id': None,
                                           'admin_state_up': True,
                                           'tenant_id': self.tenant_id,
                                           '_metering_labels': [
                                               {'rules': [],
                                                'id': second_uuid}],
                                           'id': self.uuid}]},
                     'namespace': None,
                     'method': 'add_metering_label'}
        expected2 = {'args': {'routers': [{'status': 'ACTIVE',
                                           'name': 'router2',
                                           'gw_port_id': None,
                                           'admin_state_up': True,
                                           'tenant_id': self.tenant_id,
                                           '_metering_labels': [
                                               {'rules': [],
                                                'id': second_uuid}],
                                           'id': second_uuid}]},
                     'namespace': None,
                     'method': 'add_metering_label'}

        # bind each router to a specific agent
        agent1 = agents_db.Agent(host='agent1')
        agent2 = agents_db.Agent(host='agent2')

        agents = {self.uuid: agent1,
                  second_uuid: agent2}

        def side_effect(context, routers, admin_state_up, active):
            return [agents[routers[0]]]

        self.l3routers_mock.side_effect = side_effect

        with self.router(name='router1', tenant_id=self.tenant_id,
                         set_context=True):
            self.mock_uuid.return_value = second_uuid
            with self.router(name='router2', tenant_id=self.tenant_id,
                             set_context=True):
                with self.metering_label(tenant_id=self.tenant_id,
                                         set_context=True):

                    topic1 = "%s.%s" % (self.topic, 'agent1')
                    topic2 = "%s.%s" % (self.topic, 'agent2')

                    # check if there is a call per agent
                    expected = [mock.call(self.ctx, expected1, topic=topic1),
                                mock.call(self.ctx, expected2, topic=topic2)]

                    self.mock_cast.assert_has_calls(expected, any_order=True)


class TestMeteringPluginL3AgentSchedulerServicePlugin(
        TestMeteringPluginL3AgentScheduler):

    """Unit tests for the case where separate service plugin
    implements L3 routing.
    """

    def setUp(self):
        l3_plugin = ('neutron.tests.unit.test_l3_plugin.'
                     'TestL3NatAgentSchedulingServicePlugin')
        service_plugins = {'metering_plugin_name':
                           METERING_SERVICE_PLUGIN_KLASS,
                           'l3_plugin_name': l3_plugin}

        plugin_str = ('neutron.tests.unit.test_l3_plugin.'
                      'TestNoL3NatPlugin')

        super(TestMeteringPluginL3AgentSchedulerServicePlugin, self).setUp(
            plugin_str=plugin_str, service_plugins=service_plugins,
            scheduler=l3_plugin)


class TestMeteringPluginRpcFromL3Agent(
        test_db_plugin.NeutronDbPluginV2TestCase,
        test_l3_plugin.L3NatTestCaseMixin,
        test_db_metering.MeteringPluginDbTestCaseMixin):

    resource_prefix_map = dict(
        (k.replace('_', '-'), constants.COMMON_PREFIXES[constants.METERING])
        for k in ext_metering.RESOURCE_ATTRIBUTE_MAP
    )

    def setUp(self):
        service_plugins = {'metering_plugin_name':
                           METERING_SERVICE_PLUGIN_KLASS}

        plugin = ('neutron.tests.unit.test_l3_plugin.'
                  'TestL3NatIntAgentSchedulingPlugin')

        ext_mgr = MeteringTestExtensionManager()
        super(TestMeteringPluginRpcFromL3Agent,
              self).setUp(plugin=plugin, service_plugins=service_plugins,
                          ext_mgr=ext_mgr)

        self.meter_plugin = manager.NeutronManager.get_service_plugins().get(
            constants.METERING)

        self.tenant_id = 'admin_tenant_id'
        self.tenant_id_1 = 'tenant_id_1'
        self.tenant_id_2 = 'tenant_id_2'

        self.adminContext = context.get_admin_context()
        self._register_l3_agent('agent1')

    def _register_l3_agent(self, host):
        agent = {
            'binary': 'neutron-l3-agent',
            'host': host,
            'topic': topics.L3_AGENT,
            'configurations': {},
            'agent_type': n_constants.AGENT_TYPE_L3,
            'start_flag': True
        }
        callback = agents_db.AgentExtRpcCallback()
        callback.report_state(self.adminContext,
                              agent_state={'agent_state': agent},
                              time=timeutils.strtime())

    def test_get_sync_data_metering(self):
        with self.subnet() as subnet:
            s = subnet['subnet']
            self._set_net_external(s['network_id'])
            with self.router(name='router1', subnet=subnet) as router:
                r = router['router']
                self._add_external_gateway_to_router(r['id'], s['network_id'])
                with self.metering_label(tenant_id=r['tenant_id']):
                    callbacks = metering_rpc.MeteringRpcCallbacks(
                        self.meter_plugin)
                    data = callbacks.get_sync_data_metering(self.adminContext,
                                                            host='agent1')
                    self.assertEqual('router1', data[0]['name'])

                    self._register_l3_agent('agent2')
                    data = callbacks.get_sync_data_metering(self.adminContext,
                                                            host='agent2')
                    self.assertFalse(data)

                self._remove_external_gateway_from_router(
                    r['id'], s['network_id'])

    def test_get_sync_data_metering_shared(self):
        with self.router(name='router1', tenant_id=self.tenant_id_1):
            with self.router(name='router2', tenant_id=self.tenant_id_2):
                with self.metering_label(tenant_id=self.tenant_id,
                                         shared=True):
                    callbacks = metering_rpc.MeteringRpcCallbacks(
                        self.meter_plugin)
                    data = callbacks.get_sync_data_metering(self.adminContext)

                    routers = [router['name'] for router in data]

                    self.assertIn('router1', routers)
                    self.assertIn('router2', routers)

    def test_get_sync_data_metering_not_shared(self):
        with self.router(name='router1', tenant_id=self.tenant_id_1):
            with self.router(name='router2', tenant_id=self.tenant_id_2):
                with self.metering_label(tenant_id=self.tenant_id):
                    callbacks = metering_rpc.MeteringRpcCallbacks(
                        self.meter_plugin)
                    data = callbacks.get_sync_data_metering(self.adminContext)

                    routers = [router['name'] for router in data]

                    self.assertEqual([], routers)
