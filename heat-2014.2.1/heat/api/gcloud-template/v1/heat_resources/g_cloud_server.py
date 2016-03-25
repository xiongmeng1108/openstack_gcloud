serverResource=\
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
       #    "description": "password  of server"
       # },
        "memory": {
            "type": "number",
            "description": "size  of  memory"
        },
        "core": {
            "type": "number"
        },
        "maxCount": {
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
                    #    "password": {
                    #        "get_param": "password"
                    #    },
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
                },
                "minInst": {
                    "get_param": "maxCount"
                }
            }
        },


    },

}


nestedTemplateResource= \
{
    "heat_template_version": "2013-05-23",
    "description": "A load-balancer server",
    "parameters": {
        "imageId": {
            "type": "string",
            "description": "imageId of  servers"
        },
        "storageType": {
            "type": "string"
        },
        "core": {
            "type": "number"
        },
        "memory": {
            "type": "number"
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
        #"password": {
        #    "type": "string",
        #    "description": "password  of server"
       #},
        "stackId": {
            "type": "string"
        },
        "vgId": {
            "type": "string"
        },

    },
    "resources": {
        "gcloud-vm": {
            "type": "OS::G-Cloud::Server",
            "properties": {
                "imageId": {
                    "get_param": "imageId"
                },
                "storageType": {
                    "get_param": "storageType"
                },
                "core": {
                    "get_param": "core"
                },
                "memory": {
                    "get_param": "memory"
                },
                "network":{"get_param": "network" },
                 "subnet": {"get_param": "subnet"},
                 "sgroup": {"get_param": "sgroup"},
                #"password": {
                #    "get_param": "password"
               #},
                "stackId": {
                    "get_param": "stackId"
                },
                "vgId": {
                    "get_param": "vgId"
                },

            }
        },

    }
}


