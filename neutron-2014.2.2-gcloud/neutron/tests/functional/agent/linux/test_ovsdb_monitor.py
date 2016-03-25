# Copyright 2013 Red Hat, Inc.
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

"""
Tests in this module will be skipped unless:

 - ovsdb-client is installed

 - ovsdb-client can be invoked password-less via the configured root helper

 - sudo testing is enabled (see neutron.tests.functional.base for details)
"""

import eventlet

from neutron.agent.linux import ovsdb_monitor
from neutron.tests.functional.agent.linux import base as linux_base
from neutron.tests.functional import base as functional_base


class BaseMonitorTest(linux_base.BaseOVSLinuxTestCase):

    def setUp(self):
        super(BaseMonitorTest, self).setUp()

        rootwrap_not_configured = (self.root_helper ==
                                   functional_base.SUDO_CMD)
        if rootwrap_not_configured:
            # The monitor tests require a nested invocation that has
            # to be emulated by double sudo if rootwrap is not
            # configured.
            self.root_helper = '%s %s' % (self.root_helper, self.root_helper)

        self._check_test_requirements()
        self.bridge = self.create_ovs_bridge()

    def _check_test_requirements(self):
        self.check_sudo_enabled()
        self.check_command(['ovsdb-client', 'list-dbs'],
                           'Exit code: 1',
                           'password-less sudo not granted for ovsdb-client',
                           root_helper=self.root_helper)


class TestOvsdbMonitor(BaseMonitorTest):

    def setUp(self):
        super(TestOvsdbMonitor, self).setUp()

        self.monitor = ovsdb_monitor.OvsdbMonitor('Bridge',
                                                  root_helper=self.root_helper)
        self.addCleanup(self.monitor.stop)
        self.monitor.start()

    def collect_initial_output(self):
        while True:
            output = list(self.monitor.iter_stdout())
            if output:
                # Output[0] is header row with spaces for column separation.
                # The column widths can vary depending on the data in the
                # columns, so compress multiple spaces to one for testing.
                return ' '.join(output[0].split())
            eventlet.sleep(0.01)

    def test_killed_monitor_respawns(self):
        with self.assert_max_execution_time():
            self.monitor.respawn_interval = 0
            old_pid = self.monitor._process.pid
            output1 = self.collect_initial_output()
            pid = self.monitor._get_pid_to_kill()
            self.monitor._kill_process(pid)
            self.monitor._reset_queues()
            while (self.monitor._process.pid == old_pid):
                eventlet.sleep(0.01)
            output2 = self.collect_initial_output()
            # Initial output should appear twice
            self.assertEqual(output1, output2)


class TestSimpleInterfaceMonitor(BaseMonitorTest):

    def setUp(self):
        super(TestSimpleInterfaceMonitor, self).setUp()

        self.monitor = ovsdb_monitor.SimpleInterfaceMonitor(
            root_helper=self.root_helper)
        self.addCleanup(self.monitor.stop)
        self.monitor.start(block=True, timeout=60)

    def test_has_updates(self):
        self.assertTrue(self.monitor.has_updates,
                        'Initial call should always be true')
        self.assertFalse(self.monitor.has_updates,
                         'has_updates without port addition should be False')
        self.create_resource('test-port-', self.bridge.add_port)
        with self.assert_max_execution_time():
            # has_updates after port addition should become True
            while not self.monitor.has_updates:
                eventlet.sleep(0.01)
