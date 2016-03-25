# -*- coding:utf-8 -*-
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


class API(wsgi.Router):

    """
    WSGI router for Heat v1 ReST API requests.
    """

    def __init__(self, conf, **local_conf):
        self.conf = conf
        mapper = routes.Mapper()

        # Stacks others add by xm-20160604
        stacks_resource = stacks.create_resource(conf)
        stacks_path = "/{tenant_id}"
        with mapper.submapper(controller=stacks_resource,
                              path_prefix=stacks_path) as stack_other_mapper:

            stack_other_mapper.connect("stack_gcloud_index",
                              "/stacks_gcloud",
                              action="list_stacks_for_G_cloud",
                              conditions={'method': 'GET'})
        # Stacks others add by xm-20160619
        stacks_resource = stacks.create_resource(conf)
         #alter by xm-20160630-from "/" to "" 发现如果为"/"时，发送api需要2个斜线（ http://controller:8004/v1//stacks/report），
         # 故去掉，保证请求如下格式：http://controller:8004/v1/stacks/report
        stacks_path = "/{tenant_id}"
        with mapper.submapper(controller=stacks_resource,
                              path_prefix=stacks_path) as stack_other_mapper:

            stack_other_mapper.connect("stacks_report",
                              "/stacks/report",
                              action="list_stacks_report_for_G_cloud",
                              conditions={'method': 'GET'})
            stack_other_mapper.connect("update_stack_for_G_cloud",
                              "/stacks/{stack_id}",
                              action="update_stack_for_G_cloud",
                              conditions={'method': 'PUT'})

        # Stacks others add by xm-20160630
        stacks_resource = stacks.create_resource(conf)
        stacks_path = ""
        with mapper.submapper(controller=stacks_resource,
                              path_prefix=stacks_path) as stack_other_mapper:

            stack_other_mapper.connect("stacks_name_get_by_stack_id",
                              "/stacks/{stack_id}",
                              action="get_stack_name_by_stack_id_for_G_cloud",
                              conditions={'method': 'GET'})



        # Stacks
        stacks_resource = stacks.create_resource(conf)
        with mapper.submapper(controller=stacks_resource,
                              path_prefix="/{tenant_id}") as stack_mapper:
            # Template handling
            stack_mapper.connect("template_validate",
                                 "/validate",
                                 action="validate_template",
                                 conditions={'method': 'POST'})
            stack_mapper.connect("resource_types",
                                 "/resource_types",
                                 action="list_resource_types",
                                 conditions={'method': 'GET'})
            stack_mapper.connect("resource_schema",
                                 "/resource_types/{type_name}",
                                 action="resource_schema",
                                 conditions={'method': 'GET'})
            stack_mapper.connect("generate_template",
                                 "/resource_types/{type_name}/template",
                                 action="generate_template",
                                 conditions={'method': 'GET'})

            # Stack collection
            stack_mapper.connect("stack_index",
                                 "/stacks",
                                 action="index",
                                 conditions={'method': 'GET'})
            stack_mapper.connect("stack_create",
                                 "/stacks",
                                 action="create",
                                 conditions={'method': 'POST'})
            stack_mapper.connect("stack_preview",
                                 "/stacks/preview",
                                 action="preview",
                                 conditions={'method': 'POST'})
            stack_mapper.connect("stack_detail",
                                 "/stacks/detail",
                                 action="detail",
                                 conditions={'method': 'GET'})

            # Stack data
            stack_mapper.connect("stack_lookup",
                                 "/stacks/{stack_name}",
                                 action="lookup")
            # \x3A matches on a colon.
            # Routes treats : specially in its regexp
            stack_mapper.connect("stack_lookup",
                                 r"/stacks/{stack_name:arn\x3A.*}",
                                 action="lookup")
            subpaths = ['resources', 'events', 'template', 'actions']
            path = "{path:%s}" % '|'.join(subpaths)
            stack_mapper.connect("stack_lookup_subpath",
                                 "/stacks/{stack_name}/" + path,
                                 action="lookup",
                                 conditions={'method': 'GET'})
            stack_mapper.connect("stack_lookup_subpath_post",
                                 "/stacks/{stack_name}/" + path,
                                 action="lookup",
                                 conditions={'method': 'POST'})
            stack_mapper.connect("stack_show",
                                 "/stacks/{stack_name}/{stack_id}",
                                 action="show",
                                 conditions={'method': 'GET'})
            stack_mapper.connect("stack_template",
                                 "/stacks/{stack_name}/{stack_id}/template",
                                 action="template",
                                 conditions={'method': 'GET'})

            # Stack update/delete
            stack_mapper.connect("stack_update",
                                 "/stacks/{stack_name}/{stack_id}",
                                 action="update",
                                 conditions={'method': 'PUT'})
            stack_mapper.connect("stack_update_patch",
                                 "/stacks/{stack_name}/{stack_id}",
                                 action="update_patch",
                                 conditions={'method': 'PATCH'})
            stack_mapper.connect("stack_delete",
                                 "/stacks/{stack_name}/{stack_id}",
                                 action="delete",
                                 conditions={'method': 'DELETE'})

            # Stack abandon
            stack_mapper.connect("stack_abandon",
                                 "/stacks/{stack_name}/{stack_id}/abandon",
                                 action="abandon",
                                 conditions={'method': 'DELETE'})

            stack_mapper.connect("stack_snapshot",
                                 "/stacks/{stack_name}/{stack_id}/snapshots",
                                 action="snapshot",
                                 conditions={'method': 'POST'})

            stack_mapper.connect("stack_snapshot_show",
                                 "/stacks/{stack_name}/{stack_id}/snapshots/"
                                 "{snapshot_id}",
                                 action="show_snapshot",
                                 conditions={'method': 'GET'})

            stack_mapper.connect("stack_snapshot_delete",
                                 "/stacks/{stack_name}/{stack_id}/snapshots/"
                                 "{snapshot_id}",
                                 action="delete_snapshot",
                                 conditions={'method': 'DELETE'})

            stack_mapper.connect("stack_list_snapshots",
                                 "/stacks/{stack_name}/{stack_id}/snapshots",
                                 action="list_snapshots",
                                 conditions={'method': 'GET'})

        # Resources
        resources_resource = resources.create_resource(conf)
        stack_path = "/{tenant_id}/stacks/{stack_name}/{stack_id}"
        with mapper.submapper(controller=resources_resource,
                              path_prefix=stack_path) as res_mapper:

            # Resource collection
            res_mapper.connect("resource_index",
                               "/resources",
                               action="index",
                               conditions={'method': 'GET'})

            # Resource data
            res_mapper.connect("resource_show",
                               "/resources/{resource_name}",
                               action="show",
                               conditions={'method': 'GET'})
            res_mapper.connect("resource_metadata_show",
                               "/resources/{resource_name}/metadata",
                               action="metadata",
                               conditions={'method': 'GET'})
            res_mapper.connect("resource_signal",
                               "/resources/{resource_name}/signal",
                               action="signal",
                               conditions={'method': 'POST'})

        # Events
        events_resource = events.create_resource(conf)
        with mapper.submapper(controller=events_resource,
                              path_prefix=stack_path) as ev_mapper:

            # Stack event collection
            ev_mapper.connect("event_index_stack",
                              "/events",
                              action="index",
                              conditions={'method': 'GET'})
            # Resource event collection
            ev_mapper.connect("event_index_resource",
                              "/resources/{resource_name}/events",
                              action="index",
                              conditions={'method': 'GET'})

            # Event data
            ev_mapper.connect("event_show",
                              "/resources/{resource_name}/events/{event_id}",
                              action="show",
                              conditions={'method': 'GET'})
        # Events others
        events_resource = events.create_resource(conf)
        events_path = "/{tenant_id}"
        with mapper.submapper(controller=events_resource,
                              path_prefix=events_path) as ev_other_mapper:

            ev_other_mapper.connect("event_index",
                              "/events",
                              action="list_events_for_G_cloud",
                              conditions={'method': 'GET'})



        # Actions
        actions_resource = actions.create_resource(conf)
        with mapper.submapper(controller=actions_resource,
                              path_prefix=stack_path) as ac_mapper:

            ac_mapper.connect("action_stack",
                              "/actions",
                              action="action",
                              conditions={'method': 'POST'})

        # Info
        info_resource = build_info.create_resource(conf)
        with mapper.submapper(controller=info_resource,
                              path_prefix="/{tenant_id}") as info_mapper:

            info_mapper.connect('build_info',
                                '/build_info',
                                action='build_info',
                                conditions={'method': 'GET'})

        # Software configs
        software_config_resource = software_configs.create_resource(conf)
        with mapper.submapper(
            controller=software_config_resource,
            path_prefix="/{tenant_id}/software_configs"
        ) as sc_mapper:

            sc_mapper.connect("software_config_create",
                              "",
                              action="create",
                              conditions={'method': 'POST'})

            sc_mapper.connect("software_config_show",
                              "/{config_id}",
                              action="show",
                              conditions={'method': 'GET'})

            sc_mapper.connect("software_config_delete",
                              "/{config_id}",
                              action="delete",
                              conditions={'method': 'DELETE'})

        # Software deployments
        sd_resource = software_deployments.create_resource(conf)
        with mapper.submapper(
            controller=sd_resource,
            path_prefix='/{tenant_id}/software_deployments'
        ) as sa_mapper:

            sa_mapper.connect("software_deployment_index",
                              "",
                              action="index",
                              conditions={'method': 'GET'})

            sa_mapper.connect("software_deployment_metadata",
                              "/metadata/{server_id}",
                              action="metadata",
                              conditions={'method': 'GET'})

            sa_mapper.connect("software_deployment_create",
                              "",
                              action="create",
                              conditions={'method': 'POST'})

            sa_mapper.connect("software_deployment_show",
                              "/{deployment_id}",
                              action="show",
                              conditions={'method': 'GET'})

            sa_mapper.connect("software_deployment_update",
                              "/{deployment_id}",
                              action="update",
                              conditions={'method': 'PUT'})

            sa_mapper.connect("software_deployment_delete",
                              "/{deployment_id}",
                              action="delete",
                              conditions={'method': 'DELETE'})

        super(API, self).__init__(mapper)
