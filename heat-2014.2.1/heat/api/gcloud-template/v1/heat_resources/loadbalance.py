new_lb_resources = \
    {
    "heat_template_version": "2013-05-23T00:00:00.000Z",
    "description": "elastic extension  template",
    "parameters": {
        "protocol": {
            "type": "string",
            "description": "protocol of lb",
            "constraints": [
                {
                    "allowed_values": [
                        "HTTP",
                        "HTTPS",
                        "TCP"
                    ]
                }
            ]
        },
        "member_port": {
            "type": "number",
            "description": "port  of  member",
            "constraints": [
                {
                    "range": {
                        "min": 1,
                        "max": 65535
                    }
                }
            ]
        },
        "subnet": {
            "type": "string",
            "description": "Network used by the server"
        }
    },
    "resources": {
        "monitor": {
            "type": "OS::Neutron::HealthMonitor",
            "properties": {
                "type": "TCP",
                "delay": 5,
                "max_retries": 5,
                "timeout": 5
            }
        },
        "lb": {
            "type": "OS::Neutron::Pool",
            "properties": {
                "protocol": {
                    "get_param": "protocol"
                },
                "monitors": [
                    {
                        "get_resource": "monitor"
                    }
                ],
                "subnet_id": {
                    "get_param": "subnet"
                },
                "lb_method": "ROUND_ROBIN",
                "vip": {
                    "protocol_port": 80
                }
            }
        }
    }
}

existing_lb = \
    {
    "heat_template_version": "2013-05-23T00:00:00.000Z",
    "description": "elastic extension  template",
    "parameters": {
        "protocol_port": {
            "type": "number",
            "description": "port  of  member",
            "constraints": [
                {
                    "range": {
                        "min": 1,
                        "max": 65535
                    }
                }
            ]
        },
        "pool_id": {
            "type": "string",
            "description": "Pool to contact"
        }
    },
    "resources": {
        "lb": {
            "type": "OS::Neutron::LoadBalancer",
            "properties": {
                "protocol_port": {
                    "get_param": "protocol_port"
                },
                "pool_id": {
                    "get_resource": "pool"
                }
            }
        }
    }
}