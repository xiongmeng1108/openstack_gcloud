__author__ = 'Administrator'

import datetime
import time
import requests
import json
def string_toDatetime(string):
    return datetime.datetime.strptime(string, "%Y-%m-%d %H:%M:%S")

if __name__=="__main__":

  nested_json= {
    "heat_template_version": "2013-05-23",
    "description": "A load-balancer server",
    "parameters": {
        "image": {
            "type": "string",
            "description": "Image used for servers"
        },
        "key_name": {
            "type": "string",
            "description": "SSH key to connect to the servers"
        },
        "flavor": {
            "type": "string",
            "description": "flavor used by the servers"
        },
        "pool_id": {
            "type": "string",
            "description": "Pool to contact"
        },
        "metadata": {
            "type": "json"
        },
        "network": {
            "type": "string",
            "description": "Network used by the server"
        }
    },
    "resources": {
        "server": {
            "type": "OS::Nova::Server",
            "properties": {
                "flavor": {
                    "get_param": "flavor"
                },
                "image": {
                    "get_param": "image"
                },
                "key_name": {
                    "get_param": "key_name"
                },
                "metadata": {
                    "get_param": "metadata"
                },
                "networks": [
                    {
                        "network": {
                            "get_param": "network"
                        }
                    }
                ]
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
                        "server",
                        "first_address"
                    ]
                },
                "protocol_port": 80
            }
        }
    }
}
  ss = {
    "files": {
     # "file:///root/lb/lb_server.yaml": "{\"heat_template_version\": \"2013-05-23\", \"description\": \"A load-balancer server\", \"parameters\": {\"flavor\": {\"type\": \"string\", \"description\": \"flavor used by the servers\"}, \"network\": {\"type\": \"string\", \"description\": \"Network used by the server\"}, \"key_name\": {\"type\": \"string\", \"description\": \"SSH key to connect to the servers\"}, \"image\": {\"type\": \"string\", \"description\": \"Image used for servers\"}, \"pool_id\": {\"type\": \"string\", \"description\": \"Pool to contact\"}, \"metadata\": {\"type\": \"json\"}}, \"resources\": {\"member\": {\"type\": \"OS::Neutron::PoolMember\", \"properties\": {\"protocol_port\": 80, \"pool_id\": {\"get_param\": \"pool_id\"}, \"address\": {\"get_attr\": [\"server\", \"first_address\"]}}}, \"server\": {\"type\": \"OS::Nova::Server\", \"properties\": {\"key_name\": {\"get_param\": \"key_name\"}, \"flavor\": {\"get_param\": \"flavor\"}, \"networks\": [{\"network\": {\"get_param\": \"network\"}}], \"image\": {\"get_param\": \"image\"}, \"metadata\": {\"get_param\": \"metadata\"}}}}}"
    "file:///root/lb/lb_server.yaml": json.dumps(nested_json)
    },
    "disable_rollback": True,
    "parameters": {
        "network": "8ad84e12-7dbb-4ce5-8755-b624056d84c2",
        "subnet_id": "520f8818-eea5-4b74-9b3e-629940d54320",
        "external_network_id": "fb29d7ff-d4d1-483b-929b-53c67bcb7d48",
        "image": "9ffa79cb-182e-4705-b712-f87b1167f5cf",
        "key": "123",
        "flavor": "m1.tiny"
    },
    "iscaler": True,
    "enduser_id": "8ad84e12-7dbb-4ce5-8755-b624056d8433",
    "description": "just for test",
    "app_name": "test_create_scale",
    "stack_name": "test12345",
    "environment": {},
    "template": {
        "outputs": {
            "pool_ip_address": {
                "description": "The IP address of the load balancing pool",
                "value": {
                    "get_attr": [
                        "pool",
                        "vip",
                        "address"
                    ]
                }
            },
            "scale_dn_url": {
                "description": "This URL is the webhook to scale down the autoscaling group. You can invoke the scale-down operation by doing an HTTP POST to this URL; no body nor extra headers are needed.\n",
                "value": {
                    "get_attr": [
                        "web_server_scaledown_policy",
                        "alarm_url"
                    ]
                }
            },
            "scale_up_url": {
                "description": "This URL is the webhook to scale up the autoscaling group.  You can invoke the scale-up operation by doing an HTTP POST to this URL; no body nor extra headers are needed.\n",
                "value": {
                    "get_attr": [
                        "web_server_scaleup_policy",
                        "alarm_url"
                    ]
                }
            },
            "website_url": {
                "description": "This URL is the \"external\" URL that can be used to access the Wordpress site.\n",
                "value": {
                    "str_replace": {
                        "params": {
                            "host": {
                                "get_attr": [
                                    "lb_floating",
                                    "floating_ip_address"
                                ]
                            }
                        },
                        "template": "http://host/wordpress/"
                    }
                }
            },
            "ceilometer_query": {
                "description": "This is a Ceilometer query for statistics on the cpu_util meter Samples about OS::Nova::Server instances in this stack.  The -q parameter selects Samples according to the subject's metadata. When a VM's metadata includes an item of the form metering.X=Y, the corresponding Ceilometer resource has a metadata item of the form user_metadata.X=Y and samples about resources so tagged can be queried with a Ceilometer query term of the form metadata.user_metadata.X=Y.  In this case the nested stacks give their VMs metadata that is passed as a nested stack parameter, and this stack passes a metadata of the form metering.stack=Y, where Y is this stack's ID.",
                "value": {
                    "str_replace": {
                        "params": {
                            "stackval": {
                                "get_param": "OS::stack_id"
                            }
                        },
                        "template": "ceilometer statistics -m cpu_util -q metadata.user_metadata.stack=stackval -p 600 -a avg\n"
                    }
                }
            }
        },
        "heat_template_version": "2013-05-23",
        "description": "AutoScaling Wordpress",
        "parameters": {
            "network": {
                "type": "string",
                "description": "Network used by the server"
            },
            "key": {
                "type": "string",
                "description": "SSH key to connect to the servers"
            },
            "subnet_id": {
                "type": "string",
                "description": "subnet on which the load balancer will be located"
            },
            "external_network_id": {
                "type": "string",
                "description": "UUID of a Neutron external network"
            },
            "image": {
                "type": "string",
                "description": "Image used for servers"
            },
            "flavor": {
                "type": "string",
                "description": "flavor used by the web servers"
            }
        },
        "resources": {
            "lb": {
                "type": "OS::Neutron::LoadBalancer",
                "properties": {
                    "protocol_port": 80,
                    "pool_id": {
                        "get_resource": "pool"
                    }
                }
            },
            "monitor": {
                "type": "OS::Neutron::HealthMonitor",
                "properties": {
                    "delay": 5,
                    "max_retries": 5,
                    "type": "TCP",
                    "timeout": 5
                }
            },
            "cpu_alarm_high": {
                "type": "OS::Ceilometer::Alarm",
                "properties": {
                    "meter_name": "cpu_util",
                    "alarm_actions": [
                        {
                            "get_attr": [
                                "web_server_scaleup_policy",
                                "alarm_url"
                            ]
                        }
                    ],
                    "description": "Scale-up if the average CPU > 50% for 1 minute",
                    "matching_metadata": {
                        "metadata.user_metadata.stack": {
                            "get_param": "OS::stack_id"
                        }
                    },
                    "evaluation_periods": 1,
                    "period": 60,
                    "statistic": "avg",
                    "threshold": 50,
                    "comparison_operator": "gt"
                }
            },
            "web_server_scaleup_policy": {
                "type": "OS::Heat::ScalingPolicy",
                "properties": {
                    "auto_scaling_group_id": {
                        "get_resource": "asg"
                    },
                    "adjustment_type": "change_in_capacity",
                    "scaling_adjustment": 1,
                    "cooldown": 60
                }
            },
            "cpu_alarm_low": {
                "type": "OS::Ceilometer::Alarm",
                "properties": {
                    "meter_name": "cpu_util",
                    "alarm_actions": [
                        {
                            "get_attr": [
                                "web_server_scaledown_policy",
                                "alarm_url"
                            ]
                        }
                    ],
                    "description": "Scale-down if the average CPU < 15% for 10 minutes",
                    "matching_metadata": {
                        "metadata.user_metadata.stack": {
                            "get_param": "OS::stack_id"
                        }
                    },
                    "evaluation_periods": 1,
                    "period": 600,
                    "statistic": "avg",
                    "threshold": 15,
                    "comparison_operator": "lt"
                }
            },
            "asg": {
                "type": "OS::Heat::AutoScalingGroup",
                "properties": {
                    "min_size": 3,
                    "resource": {
                        "type": "file:///root/lb/lb_server.yaml",
                        "properties": {
                            "flavor": {
                                "get_param": "flavor"
                            },
                            "network": {
                                "get_param": "network"
                            },
                            "key_name": {
                                "get_param": "key"
                            },
                            "image": {
                                "get_param": "image"
                            },
                            "pool_id": {
                                "get_resource": "pool"
                            },
                            "metadata": {
                                "metering.stack": {
                                    "get_param": "OS::stack_id"
                                }
                            }
                        }
                    },
                    "max_size": 1
                }
            },
            "lb_floating": {
                "type": "OS::Neutron::FloatingIP",
                "properties": {
                    "floating_network_id": {
                        "get_param": "external_network_id"
                    },
                    "port_id": {
                        "get_attr": [
                            "pool",
                            "vip",
                            "port_id"
                        ]
                    }
                }
            },
            "pool": {
                "type": "OS::Neutron::Pool",
                "properties": {
                    "subnet_id": {
                        "get_param": "subnet_id"
                    },
                    "vip": {
                        "protocol_port": 80
                    },
                    "lb_method": "ROUND_ROBIN",
                    "protocol": "HTTP",
                    "monitors": [
                        {
                            "get_resource": "monitor"
                        }
                    ]
                }
            },
            "web_server_scaledown_policy": {
                "type": "OS::Heat::ScalingPolicy",
                "properties": {
                    "auto_scaling_group_id": {
                        "get_resource": "asg"
                    },
                    "adjustment_type": "change_in_capacity",
                    "scaling_adjustment": -1,
                    "cooldown": 60
                }
            }
        }
    }
}

import token
headers = {
    "Accept": "application/json",
    "X-Auth-Token": token.get_token(),
    "Content-Type": "application/json",
    "X-Auth-Key": "123456789",
    "X-Auth-User": "zhangyk"


}

payload = ss
e=requests.post("http://20.251.32.19:8004/v1/a4f8c0eb051c48de90ae33c2c8c96087/stacks", data=json.dumps(payload), headers=headers)
print e.text
muban = {"template": {"files": {"lb_server.yaml": {"heat_template_version": "2013-05-23T00:00:00.000Z", "description": "A load-balancer server", "parameters": {"network": {"type": "string", "description": "Network used by the server"}, "sgroup": {"type": "string"}, "vol_size": {"type": "number", "description": "size  of  vol"}, "member_port": {"type": "number", "description": "port  of  member"}, "pool_id": {"type": "string", "description": "Pool to contact"}, "imageId": {"type": "string", "description": "imageId of  servers"}, "password": {"type": "string", "description": "password  of server"}}, "resources": {"member": {"type": "OS::Neutron::PoolMember", "properties": {"protocol_port": {"get_param": "member_port"}, "pool_id": {"get_param": "pool_id"}, "address": {"get_attr": ["server", "first_address"]}}}, "gcloud-vm": {"type": "OS::G-Cloud::server", "properties": {"sgroup:{get_param": "sgroup}", "core": 1024, "storageType": "local", "network:{get_param": "network }", "imageId": {"get_param": "imageId"}, "groupId:{get_param": "groupId }", "memory": 1024, "password": {"get_param": "password"}}}, "vol_att": {"type": "OS::Cinder::VolumeAttachment", "properties": {"instance_uuid": {"get_resource": "gcloud-vm"}, "mountpoint": "/dev/vdb", "volume_id": {"get_resource": "server_vol"}}}, "server_vol": {"type": "OS::Cinder::Volume", "properties": {"volume_type": "local", "size": {"get_param": "vol_size"}}}}}}, "name": "apache", "contents": {"outputs": {"website_url": {"value": {"str_replace": {"params": {"host": {"get_attr": ["floating", "floating_ip_address"]}}, "template": "http://host/"}}}}, "heat_template_version": "2013-05-23T00:00:00.000Z", "description": "elastic extension  template", "parameters": {"subnet": {"type": "string", "description": "subnet used by the server"}, "read_bytes_high_threshold": {"type": "number", "description": "read_bytes_high_threshold unit B", "constraints": [{"range": {"max": 1000000, "min": 0}}]}, "write_bytes_low_threshold": {"type": "number", "description": "write_bytes_low_threshold unit B", "constraints": [{"range": {"max": 1000000, "min": 0}}]}, "protocol": {"type": "string", "description": "protocol of lb", "constraints": [{"allowed_values": ["http", "https", "tcp"]}]}, "network": {"type": "string", "description": "Network used by the server"}, "sgroup": {"type": "string"}, "floating_network": {"type": "string", "description": "public  ip"}, "vol_size": {"type": "number", "description": "size  of  vol"}, "member_port": {"type": "number", "description": "port  of  member", "constraints": [{"range": {"max": 65535, "min": 1}}]}, "cputil_threshold_high": {"type": "number", "description": "cpu_low_threshold", "constraints": [{"range": {"max": 100, "min": 0}}]}, "imageId": {"type": "string", "description": "imageId of  servers"}, "memutil_threshold_high": {"type": "number", "description": "memutil_threshold_high", "constraints": [{"range": {"max": 100, "min": 0}}]}, "read_bytes_low_threshold": {"type": "number", "description": "read_bytes_low_threshold unit B", "constraints": [{"range": {"max": 1000000, "min": 0}}]}, "cputil_threshold_low": {"type": "number", "description": "cpu_high_threshold", "constraints": [{"range": {"max": 100, "min": 0}}]}, "memory": {"type": "number", "description": "size  of  memory"}, "write_bytes_high_threshold": {"type": "number", "description": "write_bytes_high_threshold unit B", "constraints": [{"range": {"max": 1000000, "min": 0}}]}, "password": {"type": "string", "description": "password  of server"}, "floating_ip": {"type": "string", "description": "public  ip"}, "memutil_threshold_low": {"type": "number", "description": "memutil_threshold_low", "constraints": [{"range": {"max": 100, "min": 0}}]}}, "resources": {"write_bytes_alarm_high": {"type": "OS::Ceilometer::Alarm", "properties": {"meter_name": "writes.bytes.rate", "alarm_actions": [{"get_attr": ["web_server_scaleup_policy", "alarm_url"]}], "description": "Scale-up if the average write_bytes > {get_param: write_bytes_high_threshold} for 1 minute", "matching_metadata": {"metadata.user_metadata.stack": {"get_param": "OS::stack_id"}}, "statistic": "avg", "threshold": {"get_param": "write_bytes_high_threshold"}, "evaluation_periods": 1, "period": 60, "comparison_operator": "gt"}}, "memutil_alarm_high": {"type": "OS::Ceilometer::Alarm", "properties": {"meter_name": "mem_util", "alarm_actions": [{"get_attr": ["web_server_scaleup_policy", "alarm_url"]}], "description": "Scale-up if the average  memory > {get_param: memutil_threshold_high} for 1 minute", "matching_metadata": {"metadata.user_metadata.stack": {"get_param": "OS::stack_id"}}, "statistic": "avg", "threshold": {"get_param": "memutil_threshold_high"}, "evaluation_periods": 1, "period": 60, "comparison_operator": "gt"}}, "read_bytes_alarm_high": {"type": "OS::Ceilometer::Alarm", "properties": {"meter_name": "read.bytes.rate", "alarm_actions": [{"get_attr": ["web_server_scaleup_policy", "alarm_url"]}], "description": "Scale-up if the average cpu > {get_param: read_bytes_high_threshold} for 1 minute", "matching_metadata": {"metadata.user_metadata.stack": {"get_param": "OS::stack_id"}}, "statistic": "avg", "threshold": {"get_param": "read_bytes_high_threshold"}, "evaluation_periods": 1, "period": 60, "comparison_operator": "gt"}}, "monitor": {"type": "OS::Neutron::HealthMonitor", "properties": {"delay": 5, "max_retries": 5, "type": "TCP", "timeout": 5}}, "web_server_scaleout_policy": {"type": "OS::Heat::ScalingPolicy", "properties": {"auto_scaling_group_id": {"get_resource": "asg"}, "adjustment_type": "scaleOutFirst", "scaling_adjustment": 1, "cooldown": 60}}, "memutil_alarm_low": {"type": "OS::Ceilometer::Alarm", "properties": {"meter_name": "mem_util", "alarm_actions": [{"get_attr": ["web_server_scaledown_policy", "alarm_url"]}], "description": "Scale-down if memory < {get_param: memutil_threshold_low}for 10 minutes", "matching_metadata": {"metadata.user_metadata.stack": {"get_param": "OS::stack_id"}}, "statistic": "avg", "threshold": {"get_param": "memutil_threshold_low"}, "evaluation_periods": 1, "period": 600, "comparison_operator": "lt"}}, "lb": {"type": "OS::Neutron::Pool", "properties": {"subnet_id": {"get_param": "network"}, "vip": {"protocol_port": 80}, "lb_method": "ROUND_ROBIN", "protocol": {"get_param": "protocol"}, "monitors": [{"get_resource": "monitor"}]}}, "read_bytes_alarm_low": {"type": "OS::Ceilometer::Alarm", "properties": {"meter_name": "read.bytes.rate", "alarm_actions": [{"get_attr": ["web_server_scaledown_policy", "alarm_url"]}], "description": "Scale-down if the average CPU < {get_param: read_bytes_low_threshold}for 10 minutes", "matching_metadata": {"metadata.user_metadata.stack": {"get_param": "OS::stack_id"}}, "statistic": "avg", "threshold": {"get_param": "read_bytes_low_threshold"}, "evaluation_periods": 1, "period": 600}}, "cputil_alarm_high": {"type": "OS::Ceilometer::Alarm", "properties": {"meter_name": "cpu_util", "alarm_actions": [{"get_attr": ["web_server_scaleup_policy", "alarm_url"]}], "description": "Scale-up if the average cpu > {get_param: cputil_threshold_high} for 1 minute", "matching_metadata": {"metadata.user_metadata.stack": {"get_param": "OS::stack_id"}}, "statistic": "avg", "threshold": {"get_param": "cputil_threshold_high"}, "evaluation_periods": 1, "period": 60, "comparison_operator": "gt"}}, "cputil_alarm_low": {"type": "OS::Ceilometer::Alarm", "properties": {"meter_name": "cpu_util", "alarm_actions": [{"get_attr": ["web_server_scaledown_policy", "alarm_url"]}], "description": "Scale-down if the average CPU < {get_param: cputil_threshold_low}for 10 minutes", "matching_metadata": {"metadata.user_metadata.stack": {"get_param": "OS::stack_id"}}, "statistic": "avg", "threshold": {"get_param": "cputil_threshold_low"}, "evaluation_periods": 1, "period": 600, "comparison_operator": "lt"}}, "write_bytes_alarm_low": {"type": "OS::Ceilometer::Alarm", "properties": {"meter_name": "write.bytes.rate", "alarm_actions": [{"get_attr": ["web_server_scaledown_policy", "alarm_url"]}], "description": "Scale-down if the average write_bytes <{get_param: write_bytes_low_threshold} for 1 minutes", "matching_metadata": {"metadata.user_metadata.stack": {"get_param": "OS::stack_id"}}, "statistic": "avg", "threshold": {"get_param": "write_bytes_low_threshold"}, "evaluation_periods": 1, "period": 60, "comparison_operator": "lt"}}, "asg": {"type": "OS::Heat::AutoScalingGroup", "properties": {"mem_resize": 1024, "max_cpu": 3, "minInst": 1, "resource": {"type": "lb_server.yaml", "properties": {"sgroup:{get_param": "sgroup}", "subnet": {"get_param": "subnet"}, "network:{get_param": "network }", "pool_id": {"get_resource": "lb"}, "imageId": {"get_param": "imageId"}, "password": {"get_param": "password"}, "size": {"get_param": "vol_size"}}}, "maxInst": 3, "max_mem": 4096, "cpu_resize": 1}}, "floating": {"type": "OS::Neutron::FloatingIP", "properties": {"port_id": {"get_attr": ["pool", "vip", "port_id"]}, "floating_ip_address": {"get_param": "floating_ip"}, "floating_network": {"get_param": "floating_network"}}}, "web_server_scaledown_policy": {"type": "OS::Heat::ScalingPolicy", "properties": {"auto_scaling_group_id": {"get_resource": "asg"}, "adjustment_type": "scaleOutFirst", "scaling_adjustment": -1, "cooldown": 60}}}}, "description": "for test", "type": "cluster", "id": "669b7168-2f2e-4dbd-b26a-6b87b8b5c8e0", "createTime": "2015-06-12 01:19:17", "user": "zhangyk"}}
print json.dumps(muban["template"]["contents"], sort_keys=True, indent=4)
