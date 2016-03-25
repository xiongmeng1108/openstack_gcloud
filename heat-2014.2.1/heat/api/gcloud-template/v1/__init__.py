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

import routes

from heat.api.openstack.v1 import actions
from heat.api.openstack.v1 import build_info
from heat.api.openstack.v1 import events
from heat.api.openstack.v1 import resources
from heat.api.openstack.v1 import software_configs
from heat.api.openstack.v1 import software_deployments
from heat.api.openstack.v1 import stacks
from heat.common import wsgi
import template

class API(wsgi.Router):

    """
    WSGI router for Heat v1 ReST API requests.
    """

    def __init__(self, conf, **local_conf):
        self.conf = conf
        mapper = routes.Mapper()
        #map.connect('/images',controller=a,action='search',conditions={'method':['GET']})
        #template
        template_resource = template.create_resource(conf)
        mapper.connect('/templates', controller=template_resource, action='create',conditions={'method': ['POST']})
        #add wll
        mapper.connect('/templates/count', controller=template_resource, action='template_count',conditions={'method': ['GET']})
        mapper.connect('/templates', controller=template_resource, action='index',conditions={'method': ['GET']})
        mapper.connect('/templates/{template_id}/details', controller=template_resource, action='show',conditions={'method': ['GET']})
        mapper.connect('/templates/{template_id}', controller=template_resource, action='get_template_contents',conditions={'method': ['GET']})
        mapper.connect('/templates/{template_id}', controller=template_resource, action='delete',conditions={'method': ['DELETE']})
        mapper.connect('/templates/add', controller=template_resource, action='direct_add',conditions={'method': ['POST']})



        #mapper.resource("template","templates",controller=template_resource)
        super(API, self).__init__(mapper)
