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

import json
import mock

from heat.common import template_format
from heat.engine import scheduler
from heat.tests.common import HeatTestCase
from heat.tests import utils
from heat.tests.v1_1 import fakes

sg_template = {
    "heat_template_version": "2013-05-23",
    "resources": {
        "ServerGroup": {
            "type": "OS::Nova::ServerGroup",
            "properties": {
                "name": "test",
                "policies": ["anti-affinity"]
            }
        }
    }
}


class FakeGroup(object):
    def __init__(self, name):
        self.id = name
        self.name = name


class NovaServerGroupTest(HeatTestCase):
    def setUp(self):
        super(NovaServerGroupTest, self).setUp()

    def _init_template(self, sg_template):
        template = template_format.parse(json.dumps(sg_template))
        stack = utils.parse_stack(template)
        self.sg = stack['ServerGroup']
        # create mock clients and objects
        nova = mock.MagicMock()
        self.sg.nova = mock.MagicMock(return_value=nova)
        self.sg_mgr = nova.server_groups

    def _create_sg(self, name):
        if name:
                sg = sg_template['resources']['ServerGroup']
                sg['properties']['name'] = name
                self._init_template(sg_template)
                self.sg_mgr.create.return_value = FakeGroup(name)
        else:
                try:
                        sg = sg_template['resources']['ServerGroup']
                        del sg['properties']['name']
                except Exception:
                        pass
                self._init_template(sg_template)
                name = 'test'
                n = name

                def fake_create(name, policies):
                        self.assertTrue(len(name) > 1)
                        return FakeGroup(n)
                self.sg_mgr.create = fake_create
        scheduler.TaskRunner(self.sg.create)()
        self.assertEqual((self.sg.CREATE, self.sg.COMPLETE),
                         self.sg.state)
        self.assertEqual(name, self.sg.resource_id)

    def test_sg_create(self):
        self._create_sg('test')
        expected_args = ()
        expected_kwargs = {'name': 'test',
                           'policies': ["anti-affinity"],
                           }
        self.sg_mgr.create.assert_called_once_with(*expected_args,
                                                   **expected_kwargs)

    def test_sg_create_no_name(self):
        self._create_sg(None)

    def test_sg_delete(self):
        self._create_sg('test')
        scheduler.TaskRunner(self.sg.delete)()
        self.sg_mgr.delete.assert_called_once_with('test')
        self.assertEqual((self.sg.DELETE, self.sg.COMPLETE),
                         self.sg.state)

    def test_sg_delete_not_found(self):
        self._create_sg('test')
        self.sg_mgr.delete.side_effect = fakes.fake_exception()
        scheduler.TaskRunner(self.sg.delete)()
        self.sg_mgr.delete.assert_called_once_with('test')
        self.assertEqual((self.sg.DELETE, self.sg.COMPLETE),
                         self.sg.state)
