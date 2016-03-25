nestedTemplateResource= \
{
    "heat_template_version": "2013-05-23",
    "description": "A load-balancer server",
    "parameters": {
        "imageId": {
            "type": "string",
            "description": "imageId of  servers"
        },
        "pool_id": {
            "type": "string",
            "description": "Pool to contact"
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
        #   "type": "string",
        #    "description": "password  of server"
      #  },
        "member_port": {
            "type": "number",
            "description": "port  of  member"
        },
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
               # "password": {
               #     "get_param": "password"
               # },
                "stackId": {
                    "get_param": "stackId"
                },
                 "vgId": {
                    "get_param": "vgId"
                },
            }
        },
        "member": {
            "type": "OS::Neutron::PoolMember",
            "properties": {
                "pool_id": {
                    "get_param": "pool_id"
                },
                "address": {
                    "get_attr": [
                        "gcloud-vm",
                        "first_address"
                    ]
                },
                "protocol_port": {
                    "get_param": "member_port"
                },
                "instance_id": {
                    "get_attr": [
                        "gcloud-vm",
                        "instaceId"
                    ]
                },
            }
        }
    }
}