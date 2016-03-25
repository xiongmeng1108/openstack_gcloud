groupResources = \
{
    "heat_template_version": "2013-05-23",
    "description": "elastic extension  template",
    "parameters": {
        "imageId": {
            "type": "string",
            "description": "imageId of  servers"
        },
        "sgroup": {
            "type": "string"
        },
        "network": {
            "type": "string",
            "description": "Network used by the server"
        },
        "subnet": {
            "type": "string",
            "description": "subnet used by the server"
        },
       # "password": {
       #     "type": "string",
       #     "description": "password  of server"
       # },
        "memory": {
            "type": "number",
            "description": "size  of  memory"
        },
        "core": {
            "type": "number"
        },
         "inst_pool": {
            "type": "string",
            "description": "name of vm location  storage pool"
        }

    },
    "resources": {
        "asg": {
            "type": "OS::Heat::G_CloudAutoScalingGroup",
            "properties": {
                "resource": {
                    "type": "lb_server.yaml",
                    "properties": {
                        "imageId": {
                            "get_param": "imageId"
                        },
                        "network": {"get_param": "network" },
                        "subnet": {"get_param": "subnet"},
                       "sgroup": {"get_param": "sgroup"},
                      #  "password": {
                      #      "get_param": "password"
                      #  },
                        "pool_id": {
                            "get_resource": "lb"
                        },
                        "core": {
                            "get_param": "core"
                        },
                        "memory": {
                            "get_param": "memory"
                        },
                         "stackId":{
                             "get_param": "OS::stack_id"
                         },
                          "vgId": {
                              "get_param": "inst_pool"
                         },


                    }
                }
            }
        },
        "web_server_scaleout_policy": {
            "type": "OS::Heat::ScalingPolicy",
            "properties": {
                "adjustment_type": "change_in_capacity_by_scaleOut",
                "auto_scaling_group_id": {
                    "get_resource": "asg"
                },
                "cooldown": 60,
                "scaling_adjustment": 1
            }
        },
        "web_server_scaledown_policy": {
            "type": "OS::Heat::ScalingPolicy",
            "properties": {
                "adjustment_type": "change_in_capacity_by_scaleOut",
                "auto_scaling_group_id": {
                    "get_resource": "asg"
                },
                "cooldown": 60,
                "scaling_adjustment": -1
            }
        }
    },

}




groupResources_extra_volume = \
{
    "parameters": {
        "vol_size": {
            "description": "size  of  vol",
            "type": "number"
        },
        "volume_pool":{
            "type": "string",
            "description": "name of volume pool"
        }
    },

}








