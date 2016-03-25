__author__ = 'Administrator'

just_auto_group={
    "description": "elastic extension  template",
    "heat_template_version": "2013-05-23",

    "parameters": {
        "imageId": {
            "description": "imageId of  servers",
            "type": "string"
        },
        "memory": {
            "description": "size  of  memory",
            "type": "number"
        },
        "core": {
            "type": "number"
        },
        "network": {
            "description": "Network used by the server",
            "type": "string"
        },
        "password": {
            "description": "password  of server",
            "type": "string"
        },
        "sgroup": {
            "type": "string"
        },
        "subnet": {
            "description": "subnet used by the server",
            "type": "string"
        },
         "cputil_threshold_high": {
            "type": "number",
            "description": "cpu_low_threshold",
            "constraints": [
                {
                    "range": {
                        "min": 0,
                        "max": 100
                    }
                }
            ]
        },
        "cputil_threshold_low": {
            "type": "number",
            "description": "cpu_high_threshold",
            "constraints": [
                {
                    "range": {
                        "min": 0,
                        "max": 100
                    }
                }
            ]
        }

    },
    "resources": {
        "asg": {
            "properties": {
                "cpu_resize": 1,
                "maxInst": 3,
                "max_cpu": 4,
                "max_mem": 9096,
                "mem_resize": 1024,
                "minInst": 1,
                "resource": {
                    "properties": {
                        "imageId": {
                            "get_param": "imageId"
                        },
                        "network": {"get_param": "network"},
                        "password": {
                            "get_param": "password"
                        },
                        "sgroup": {"get_param": "sgroup"},
                        "subnet": {
                            "get_param": "subnet"
                        },
                        "core": {
                            "get_param": "core"
                        },
                        "memory": {
                            "get_param": "memory"
                        },
                    },
                    "type": "lb_server.yaml"
                }
            },
            "type": "OS::Heat::G_CloudAutoScalingGroup"
        },

        "web_server_scaleout_policy": {
          "properties": {
            "adjustment_type": "scaleUpFirst",
            "auto_scaling_group_id": {
              "get_resource": "asg"
            },
            "cooldown": 60,
            "scaling_adjustment": 1
          },
          "type": "OS::Heat::ScalingPolicy"
        },
        "web_server_scaledown_policy": {
          "properties": {
            "adjustment_type": "scaleUpFirst",
            "auto_scaling_group_id": {
              "get_resource": "asg"
            },
            "cooldown": 60,
            "scaling_adjustment": -1
          },
          "type": "OS::Heat::ScalingPolicy"
        },
        "cputil_alarm_high": {
            "type": "OS::Ceilometer::Alarm",
            "properties": {
                "description": "Scale-up if the average cpu > {get_param: cputil_threshold_high} for 1 minute",
                "meter_name": "cpu_util",
                "statistic": "avg",
                "period": 60,
                "evaluation_periods": 1,
                "threshold": {
                    "get_param": "cputil_threshold_high"
                },
                "alarm_actions": [
                    {
                        "get_attr": [
                            "web_server_scaleout_policy",
                            "alarm_url"
                        ]
                    }
                ],
                "matching_metadata": {
                        "metadata.user_metadata.stack": "1fe9fe22-e7e5-4fcf-bd6a-0eb9ffec9ea6"
                 },
                "comparison_operator": "gt"
            }
        },
        "cputil_alarm_low": {
            "type": "OS::Ceilometer::Alarm",
            "properties": {
                "description": "Scale-down if the average CPU < {get_param: cputil_threshold_low}for 10 minutes",
                "meter_name": "cpu_util",
                "statistic": "avg",
                "period": 600,
                "evaluation_periods": 1,
                "threshold": {
                    "get_param": "cputil_threshold_low"
                },
                "alarm_actions": [
                    {
                        "get_attr": [
                            "web_server_scaledown_policy",
                            "alarm_url"
                        ]
                    }
                ],
                "matching_metadata": {
                        "metadata.user_metadata.stack": "1fe9fe22-e7e5-4fcf-bd6a-0eb9ffec9ea6"
                 },
                "comparison_operator": "lt"
            }
        }

    }
}

import json
import nest_template
request_body =  {
    "disable_rollback": True,
    "parameters": {
        "network": "8ad84e12-7dbb-4ce5-8755-b624056d84c2",
        "imageId": "520f8818-eea5-4b74-9b3e-629940d54320",
        "subnet": "520f8818-eea5-4b74-9b3e-629940d54320",
        "sgroup": "fb29d7ff-d4d1-483b-929b-53c67bcb7d48",
        "password": "m1.tiny",
        "core": 1,
        "memory":512,
        "cputil_threshold_high": 80,
        "cputil_threshold_low": 20,

    },
    "stack_name": "jjj-test-scale",
    "environment": {},
    "files": {
        "lb_server.yaml": json.dumps(nest_template.t)
    },
    "template": just_auto_group,
    "iscaler": False,
    "enduser_id": "8ad84e12-7dbb-4ce5-8755-b624056d8433",
    "description": "just for test",
    "app_name": "jjj-test-scale"
}