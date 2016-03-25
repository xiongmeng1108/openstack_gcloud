floatIp_for_server = \
{
    "heat_template_version": "2013-05-23T00:00:00.000Z",
    "description": "floatIp  for server",
    "parameters": {
        "floating_ip": {
            "type": "string",
            "description": "public  ip"
        },
        "floating_network": {
            "type": "string",
            "description": "public  network"
        }
    },
    "resources": {
        "floating": {
            "type": "OS::G-Cloud::FloatingIP",
            "properties": {
                "fixed_ip_address": {
                    "get_attr": [
                        "gcloud-vm",
                        "first_address"
                    ]
                },
                "port_id":  {
                    "get_attr": [
                        "gcloud-vm",
                        "first_port_id"
                    ]
                },
                "floating_ip_address": {
                    "get_param": "floating_ip"
                },
                "floating_network": {
                    "get_param": "floating_network"
                }
            }
        }


    },

}

floatIP_for_lb =\
{
    "heat_template_version": "2013-05-23T00:00:00.000Z",
    "description": "A load-balancer server",
    "parameters": {
        "floating_ip": {
            "type": "string",
            "description": "public  ip"
        },
        "floating_network": {
            "type": "string",
            "description": "public  ip"
        }
    },
    "resources": {
        "floating": {
            "type": "OS::G-Cloud::FloatingIP",
            "properties": {
                "port_id": {
                    "get_attr": [
                        "lb",
                        "vip",
                        "port_id"
                    ]
                },
                "floating_ip_address": {
                    "get_param": "floating_ip"
                },
                "floating_network": {
                    "get_param": "floating_network"
                }
            }
        }
    },

}
