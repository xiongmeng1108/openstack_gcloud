import jsonschema
from webob import exc
from heat.common.i18n import _
from functools import wraps
from heat.common import exception

gCloud_create_template_schema = {
    "type": "object",
    "properties": {
        "template": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "maxLength": 255, "minLength": 4},
                "type": {"enum": ["cluster", "deploy"]},
                "resources": {
                    "type": "object",
                    "properties": {
                        "InstanceResource": {
                            "type": "object",
                            "properties": {
                                    "attachVolumeType": {"enum": ["RBD", "Central", "Local"] },
                                    "instanceStorageType": {"enum": ["0", "1", "2"] },
                                    "isFloating": {"type": "boolean"},
                                     "memory": {"type": "number", "minimum": 256},
                                    "cpu": {"type": "number", "minimum": 1},
                            },
                            "required": ["instanceStorageType", "isFloating"]
                        },
                        "ScalingPolicyAlarmResource": {
                            "type": "object",
                            "properties": {
                                "alarmTypelist": {
                                    "type": "array",
                                    "items": {
                                        "enum": ["cpu_util", "cpu_load", "mem_util", "mem_free", "disk_io_read",
                                            "disk_io_write"]
                                    }
                                },
                                "policy": {
                                    "type": "object",
                                    "properties": {
                                        "policyType":  {"enum": ["scaleOutFirst", "scaleUpFirst", "scaleOut", "scaleUp"]},
                                        "minInst": {"type": "number", "minimum": 1},
                                        "maxInst": {"type": "number", "maximum": 400},
                                        "cpu_resize": {"type": "number"},
                                        "mem_resize": {"type": "number"},
                                        "max_cpu": {"type": "number", "maximum": 128},
                                        "max_mem": {"type": "number", "maximum": 32768}
                                    }
                                }
                            },
                            "required": ["alarmTypelist", "policy"]
                        },
                        "LoadBalanceResource": {
                            "type": "object",
                            "properties": {
                                "isFloating": {"type": "boolean"},
                                "type": {"enum": ["new", "hard", "exit"]}
                            },
                            "required": ["isFloating", "type"]
                        }
                    }
                }
            },
            "required": ["name", "type", "resources"]
        }
    },
    "required": ["template"]
}

need_change_int = ("minInst", "memory", "")

gCloud_direct_add_template_schema = {
    "type": "object",
    "properties": {
        "template": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "maxLength": 255, "minLength": 4},
                "type": {"enum": ["upload"]},
                "contents": {"type": "object"}

            },
            "required": ["name", "type", "contents"]
        }
    },
    "required": ["template"]
}


def create_template_request_validate(handler):
    """
    Decorator for validate create template request
    """
    @wraps(handler)
    def handler_validate(controller, req, **kwargs):

        try:
            jsonschema.validate(kwargs["body"], gCloud_create_template_schema)

        except jsonschema.ValidationError as ex:
            #msg = _("http request body is invalid (%s)") % ex
            #raise exc.HTTPBadRequest(msg)
            raise exception.GcloudTemplateRequestInvalid(input=ex.path[len(ex.path)-1])

        return handler(controller, req, **kwargs)

    return handler_validate


def direct_add_template_request_validate(handler):
    """
    Decorator for validate direct add  template request
    """
    @wraps(handler)
    def handler_validate(controller, req, **kwargs):

        try:
            jsonschema.validate(kwargs["body"], gCloud_direct_add_template_schema)

        except jsonschema.ValidationError as ex:
            #msg = _("http request body is invalid (%s)") % ex
            #raise exc.HTTPBadRequest(msg)
            raise exception.GcloudTemplateRequestInvalid(input=ex.path[len(ex.path)-1])

        return handler(controller, req, **kwargs)

    return handler_validate

