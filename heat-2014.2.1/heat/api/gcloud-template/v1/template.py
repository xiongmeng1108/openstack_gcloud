from heat.common import wsgi
from heat.common import serializers
from heat.openstack.common import log as logging
from heat.common.i18n import _
from functools import wraps
from util import validate
from heat_resources import g_cloud_server, volume, floating_ip, nested_template, auto_scaling_group, loadbalance, alarm
from heat.db.sqlalchemy import models
from heat.db import api as db_api
from heat.api.openstack.v1 import util
import copy
import json
import six
import pytz
from pytz import timezone
from webob import exc

LOG = logging.getLogger(__name__)


def translate_filters(filters):
    new_filters = {}
    for key, value in six.iteritems(filters):
        if key == "user":
            new_filters["creater"] = value
        else:
            new_filters[key] = value
    return new_filters


def get_deep_copy(inst):
    return copy.deepcopy(inst)


def create_template_return_info(t):
    info = {
        "template": {
            "name": t.name,
            "id": t.id,
            "user": t.creater,
            "type": t.type,
            "description": t.description,
            "createTime":  t.created_at.replace(tzinfo=pytz.utc).astimezone
            (timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S"),
            "contents": t.content,
            "files": {
                "lb_server.yaml": json.dumps(t.nested_content)
            }


        }
    }
    return info


def get_template_details_response_info(templates):

    info = None
    for t in templates:

        info = {
            "template": {
                "name": t.name,
                "id": t.id,
                "user": t.creater,
                "type": t.type,
                "description": t.description,
                "createTime":  t.created_at.replace(tzinfo=pytz.utc).astimezone
                (timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S"),
                "resources": t.gcloud_resource.content,



            }
        }
    return info


def validate_policy(type, policy):
    keys = [key for key in policy.iterkeys()]
    extra = None
    if type == "scaleOut":
        validate_keys= set(["minInst", "maxInst"])

    if type =="scaleUp":
        validate_keys= set(["cpu_resize", "mem_resize", "max_cpu", "max_mem", 'minInst'])

    if type == "scaleOutFirst"  or type == "scaleUpFirst":
        validate_keys= set(["cpu_resize", "mem_resize", "max_cpu", "max_mem","minInst", "maxInst"])

    if set(keys)-validate_keys:
        raise exc.HTTPBadRequest("policy request is not right")


def get_index_template_response_info(templates):

    response = {
        "templates": []
    }
    for t in templates:
        item = {
            "name": t.name,
            "id": t.id,
            "user": t.creater,
            "type": t.type,
            "description": t.description,
            "createTime":  t.created_at.replace(tzinfo=pytz.utc).astimezone
            (timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S")
        }
        response["templates"].append(item)

    return response



def get_value_or_default(r, key, default):
    if key in r:
        return r[key]
    else:
        return default

class TemplateController(object):

        REQUEST_SCOPE = 'template'

        def __init__(self, options):
            self.options = options

        @validate.create_template_request_validate
        def create(self, req, body):

            inst = template_inst(req.context, **body["template"])
            inst.generate_content()
            gcloud_template = inst.save()
            return create_template_return_info(gcloud_template)

        def index(self, req):

            filter_whitelist = {
                'name': 'single',
                'type': 'single',
                'user': 'single',
            }
            whitelist = {
                'limit': 'single',
                'offset': 'single',
                'sort_dir': 'single',
                'sort_keys': 'multi',
            }
            params = util.get_allowed_params(req.params, whitelist)
            filter_params = util.get_allowed_params(req.params, filter_whitelist)
            templates = db_api.template_get_all(req.context, filters=translate_filters(filter_params), **params)

            return get_index_template_response_info(templates)

        def show(self, req, template_id):

            LOG.debug(_("show template  %s  details") % template_id)
            templates = db_api.template_get(req.context, template_id)
            return get_template_details_response_info(templates)



        #def get_template_contents(self, req, template_id):
        #    LOG.debug(_("get template  %s  contents") % template_id)
        #    templates = db_api.template_get(req.context, template_id)
        #    return get_template_return_info(templates.first())


        def delete(self, req, template_id):
            LOG.debug(_("deleting template and the id  is %s") % template_id)
            db_api.template_delete(req.context, template_id)


        @validate.direct_add_template_request_validate
        def direct_add(self, req, body):
            LOG.debug(_("direct add template ") )
            inst = template_inst(req.context, **body["template"])
            gcloud_template = inst.save()
            return create_template_return_info(gcloud_template)

        def get_template_contents(self, req, template_id):
            LOG.debug(_("get %s template contents") %template_id )
            templates = db_api.template_get(req.context, template_id)
            for t in templates:
                return create_template_return_info(t)


        def template_count(self, req):
            count = db_api.template_get_count(req.context)
            return {"count": count}





class template_inst(object):

    def __init__(self, context=None,   name=None, type=None, description=None, resources=None, contents=None):

        self.context = context
        self.user_id = context.user_id
        self.creater = context.username
        self.name = name
        self.type = type
        self.description = description
        self.resources = resources
        self.nested_content = None
        self.content = contents




    def generate_content(self):

        if self.resources.has_key("InstanceResource") \
                and  self.resources.has_key("ScalingPolicyAlarmResource"):
            LOG.debug(_("prepare create autocale resource  template"))
            self.get_autoscale_resource_content()

        elif self.resources.has_key("InstanceResource"):
            LOG.debug(_("prepare create  instanceResource template"))
            self.get_instance_resource_content()
        else:
            msg = _("http request body is invalid")
            raise exc.HTTPBadRequest(msg)

        if self.content is None:
            msg = _("http request body is invalid,and template is null")
            raise exc.HTTPBadRequest(msg)

    def save(self):

        values= {
            "content": self.resources
        }
        gcloud_template_resource = models.Gcloud_resource()

        gcloud_template_resource.update(values)
        values = {
            "name": self.name,
            "content": self.content,
            "nested_content": self.nested_content,
            "description": self.description,
            "isShare": True,
            "type": self.type,
            "creater_id": self.user_id,
            "creater": self.creater,
            "gcloud_resource": gcloud_template_resource
        }
        return db_api.template_create(self.context,values)




    def get_autoscale_resource_content(self):

        nested_content = get_deep_copy(nested_template.nestedTemplateResource)
        main_template = get_deep_copy(auto_scaling_group.groupResources)
        ## update nested
        properties = {
            "storageType": get_value_or_default(self.resources["InstanceResource"], "instanceStorageType", "1"),
           #  "volumeId": {
           #      "get_resource": "server_vol"
           #      },
        }
        self.update_resource_properties(nested_content, properties, "gcloud-vm")

        ##update volume
        if self.resources["InstanceResource"].has_key("attachVolumeType"):
            volume_template = get_deep_copy(volume.volumeResource)
            properties = {
                "volume_type": self.resources["InstanceResource"]["attachVolumeType"]

            }

            self.update_resource_properties(volume_template, properties, "server_vol")
            self.update_resources_and_parameters(nested_content, volume_template)

            extra_volume_template = get_deep_copy(auto_scaling_group.groupResources_extra_volume)
            self.update_resources_and_parameters(main_template, extra_volume_template)
            properties={
                "vol_size": {"get_param": "vol_size"},
                "volume_pool": {"get_param": "volume_pool"},
            }
            self.update_autoScalingGroup_nest_properties(main_template,properties)



        ##update policy

        temp_policy = get_deep_copy(self.resources["ScalingPolicyAlarmResource"]["policy"])
        properties = {
            "adjustment_type": temp_policy.pop("policyType")
        }
        validate_policy(properties["adjustment_type"], temp_policy)
        self.update_resource_properties(main_template, properties, "web_server_scaleout_policy")
        self.update_resource_properties(main_template, properties, "web_server_scaledown_policy")
        self.update_resource_properties(main_template, temp_policy, "asg")

        ##update alarm
        for key in self.resources["ScalingPolicyAlarmResource"]["alarmTypelist"]:
            if key in alarm.map_alarm:
                self.update_resources_and_parameters(main_template, alarm.map_alarm[key])

        #update load_balance
        if self.resources.has_key("LoadBalanceResource"):
            if self.resources["LoadBalanceResource"]["type"] == "new":
                self.update_resources_and_parameters(main_template, get_deep_copy(loadbalance.new_lb_resources))
                properties={
                    "member_port": {
                        "get_param": "member_port"
                    }
                }
                self.update_autoScalingGroup_nest_properties(main_template,properties)

            if self.resources["LoadBalanceResource"]["isFloating"]:
                self.update_resources_and_parameters(main_template, get_deep_copy(floating_ip.floatIP_for_lb))

        #update memory and  core
        properties={
            "memory": get_value_or_default(self.resources["InstanceResource"], "memory", 1024),
            "core": get_value_or_default(self.resources["InstanceResource"], "cpu", 1),
        }
        self.update_autoScalingGroup_nest_properties(main_template,properties)
        self.content = main_template
        self.nested_content = nested_content
        LOG.debug( _("the nested template is %s") %json.dumps(nested_content, sort_keys=True, indent=4))
        LOG.debug(_("create  autoscale_resource template finish and  template is %s ") %json.dumps(main_template, sort_keys=True, indent=4))





    def get_instance_resource_content(self):

        main_template = get_deep_copy(g_cloud_server.serverResource)
        nested_content = get_deep_copy(g_cloud_server.nestedTemplateResource)
        properties = {
            "storageType": get_value_or_default(self.resources["InstanceResource"], "instanceStorageType", "1"),
        }
        self.update_resource_properties(nested_content, properties, "gcloud-vm")

        ##update volume
        if self.resources["InstanceResource"].has_key("attachVolumeType"):
            volume_template = get_deep_copy(volume.volumeResource)
            properties = {
                "volume_type": self.resources["InstanceResource"]["attachVolumeType"]

            }

            self.update_resource_properties(volume_template, properties, "server_vol")
            self.update_resources_and_parameters(nested_content, volume_template)

            extra_volume_template = get_deep_copy(auto_scaling_group.groupResources_extra_volume)
            self.update_resources_and_parameters(main_template, extra_volume_template)
            properties={
                "vol_size": {"get_param": "vol_size"},
                "volume_pool": {"get_param": "volume_pool"},
            }
            self.update_autoScalingGroup_nest_properties(main_template,properties)

        if  self.resources["InstanceResource"].has_key("isFloating") and self.resources["InstanceResource"]["isFloating"]:
            self.update_resources_and_parameters(nested_content, floating_ip.floatIp_for_server.copy())
            main_template['parameters'].update(floating_ip.floatIp_for_server.copy()['parameters'])
            properties = {
                "floating_ip": {
                    "get_param": "floating_ip"
                },
                "floating_network": {
                    "get_param": "floating_network"
                }
            }
            self.update_autoScalingGroup_nest_properties(main_template,properties)

        #update memory and  core
        properties={
            "memory": get_value_or_default(self.resources["InstanceResource"], "memory", 1024),
            "core": get_value_or_default(self.resources["InstanceResource"], "cpu", 1),
        }
        self.update_autoScalingGroup_nest_properties(main_template,properties)
        self.content = main_template
        self.nested_content = nested_content
        LOG.debug( _("the nested template is %s") %json.dumps(nested_content, sort_keys=True, indent=4))
        LOG.debug(_("create  autoscale_resource template finish and  template is %s ") %json.dumps(main_template, sort_keys=True, indent=4))




    def update_resources_and_parameters(self, main_template, *templates):

            for template in templates:

                if main_template.has_key("parameters") and template.has_key("parameters"):

                    main_template["parameters"].update(template["parameters"])
                if main_template.has_key("resources") and template.has_key("resources"):
                    main_template["resources"].update(template["resources"])
                if template.has_key("outputs"):
                    main_template["outputs"] = {}
                    main_template["outputs"].update(template["outputs"])

            return main_template

    def update_resource_properties(self, template, properties, resource_key, change=0):

        if change == 0:
            template["resources"][resource_key]["properties"].update(properties)
        else:
            template["resources"][resource_key+str(change)] = template["resources"].pop(resource_key)

        for key, value in properties.items():
            if template["parameters"].has_key(key) and not isinstance(value, dict):
                template["parameters"].pop(key)

        return template

    def update_autoScalingGroup_nest_properties(self, template, properties):

        template["resources"]["asg"]["properties"]["resource"]["properties"].update(properties)
        for key, value in properties.items():
            if template["parameters"].has_key(key) and not isinstance(value, dict):
                template["parameters"].pop(key)



def create_resource(options):
    """
    template resource factory method.
    """
    deserializer = wsgi.JSONRequestDeserializer()
    serializer = serializers.JSONResponseSerializer()
    return wsgi.Resource(TemplateController(options), deserializer, serializer)

