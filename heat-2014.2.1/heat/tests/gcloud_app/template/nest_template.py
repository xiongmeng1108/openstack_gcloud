__author__ = 'Administrator'
t = {
        "description": "A load-balancer server",
        "heat_template_version": "2013-05-23",
        "parameters": {
          "core": {
            "type": "number"
          },
          "imageId": {
            "description": "imageId of  servers",
            "type": "string"
          },
          "member_port": {
            "description": "port  of  member",
            "type": "number"
          },
          "memory": {
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
          "pool_id": {
            "description": "Pool to contact",
            "type": "string"
          },
          "sgroup": {
            "type": "string"
          },
          "subnet": {
            "description": "subnet used by the server",
            "type": "string"
          },
            "stackId": {
            "type": "string"
        },
        },
        "resources": {
          "gcloud-vm": {
            "properties": {
              "core": {
                "get_param": "core"
              },
              "imageId": {
                "get_param": "imageId"
              },
              "memory": {
                "get_param": "memory"
              },
             "network":{"get_param": "network" },
              "password": {
                "get_param": "password"
              },
              "sgroup": {
                "get_param": "sgroup"
              },
              "storageType": "1",
              "subnet": {
                "get_param": "subnet"
              },
               "stackId": {
                    "get_param": "stackId"
                },
            },
            "type": "OS::G-Cloud::Server"
          },
          "member": {
            "properties": {
              "address": {
                "get_attr": [
                  "gcloud-vm",
                  "first_address"
                ]
              },
              "pool_id": {
                "get_param": "pool_id"
              },
              "protocol_port": {
                "get_param": "member_port"
              }
            },
            "type": "OS::Neutron::PoolMember"
          },
        }

    }