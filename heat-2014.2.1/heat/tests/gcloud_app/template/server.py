#coding=utf-8
__author__ = 'Administrator'
import json
import requests
import token
t = {
    "description": "A load-balancer server",
    "heat_template_version": "2013-05-23",
    "parameters": {
        "imageId": {
            "description": "imageId of  servers",
            "type": "string"
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
            "type": "string"
        },

    },
    "resources": {
        "gcloud-vm": {
            "properties": {
                "core": 1024,
                "imageId": {
                    "get_param": "imageId"
                },
                "memory": 1024,
                "network": {"get_param": "network"},
                 "subnet": {"get_param": "subnet"},
                "password": {
                    "get_param": "password"
                },
               "sgroup": {"get_param": "sgroup"},
                "storageType": "local"
            },
            "type": "OS::G-Cloud::Server"
        },



    }
}

test1={
    "template":{
        "name": "http集群",
        "type": "deploy",
        "description": "for test",
        "resources": {
            "InstanceResource": {
                "attachVolumeType": "RBD",
                "instanceStorageType": "1",
                "isFloating": True,
                "cpu": 2,
                "memory": 333,
            }
        }
    }

 }

test_scaleOutFirst={
    "template":{
        "name": "apache",
        "type": "cluster",
        "description": "for test",
        "resources": {
            "InstanceResource": {
                #"attachVolumeType": "RBD",
                "instanceStorageType": "1",
                "isFloating": False,
                "cpu": 1,
                "memory": 300,
            },
            "ScalingPolicyAlarmResource": {
                "alarmTypelist": ["cpu_util"],
                "policy": {
                    "policyType": "scaleOutFirst",
                    "minInst": 1,
                    "maxInst": 3,
                    "cpu_resize": 1,
                    "mem_resize": 1024,
                    "max_cpu":  3,
                    "max_mem":  4096,

                }

            },
            "LoadBalanceResource": {
                 "isFloating": True,
                 "type": "new"
            }
        }
    }

}

test_scaleUpFirst={
    "template":{
        "name": "apache",
        "type": "cluster",
        "description": "for test",
        "resources": {
            "InstanceResource": {
                "attachVolumeType": "RBD",
                "instanceStorageType": "1",
                "isFloating": False,
                "cpu": 2,
                "memory": 300,
            },
            "ScalingPolicyAlarmResource": {
                "alarmTypelist": ["disk_io_read","cpu_util", "disk_io_write"],
                "policy": {
                    "policyType": "scaleUpFirst",
                    "minInst": 1,
                    "maxInst": 2,
                    "cpu_resize": 1,
                    "mem_resize": 1024,
                    "max_cpu":  2,
                    "max_mem":  4096,

                }

            },
            "LoadBalanceResource": {
                 "isFloating": True,
                 "type": "new"
            }
        }
    }

}

test_scaleOut={
    "template":{
        "name": "apache",
        "type": "cluster",
        "description": "for test",
        "resources": {
            "InstanceResource": {
               # "attachVolumeType": "RBD",
                "instanceStorageType": "1",
                "isFloating": False,
                "cpu": 1,
                "memory": 289,
            },
            "ScalingPolicyAlarmResource": {
                #"alarmTypelist": ["cpu_util", "mem_util", "disk_io_read", "disk_io_write"],
                "alarmTypelist": ["cpu_util"],
                "policy": {
                    "policyType": "scaleOut",
                    "minInst": 1,
                    "maxInst": 3,

                }

            },
            "LoadBalanceResource": {
                 "isFloating": True,
                 "type": "new"
            }
        }
    }

}






just_server = {
        "heat_template_version": "2013-05-23",
        "description": "g_cloud  server",
        "parameters": {
            "network": {
                "type": "string",
                "description": "Network used by the server"
            },
            "sgroup": {
                "type": "string"
            },
            "subnet": {
                "type": "string",
                "description": "subnet used by the server"
            },
            "imageId": {
                "type": "string",
                "description": "imageId of  servers"
            },
            "password": {
                "type": "string",
                "description": "password  of server"
            },
            "maxCount": {
                "type": "number"
            }
        },
        "resources": {
            "gcloud-vm": {
                "type": "OS::G-Cloud::Server",
                "properties": {
                    "core": 1,
                    "network": {
                        "get_param": "network"
                    },
                    "sgroup": {
                        "get_param": "sgroup"
                    },
                    "subnet": {
                        "get_param": "subnet"
                    },
                    "storageType": "1",
                    "imageId": {
                        "get_param": "imageId"
                    },
                    "memory": 234,
                    "password": {
                        "get_param": "password"
                    },
                    "maxCount": {
                        "get_param": "maxCount"
                    }
                }
            },

        }
    }

test_scaleUp={
    "template":{
        "name": "apache",
        "type": "cluster",
        "description": "for test",
        "resources": {
            "InstanceResource": {
                #"attachVolumeType": "local",
                "instanceStorageType": "1",
                "isFloating": False,
                "cpu": 1,
                "memory": 512,

            },
            "ScalingPolicyAlarmResource": {
                "alarmTypelist": ["cpu_util"],
                "policy": {
                    "policyType": "scaleUp",
                    "cpu_resize": 1,
                    # "minInst": 1,
                    "mem_resize": 1024,
                    "max_cpu":  3,
                    "max_mem":  4096,
                    'minInst': 1

                }

            },
            "LoadBalanceResource": {
                 "isFloating": True,
                 "type": "new"
            }
        }
    }

}


def getTemplate(t):
    headers = {
    "Accept": "application/json",
    "X-Auth-Token": token.get_token(),
    "Content-Type": "application/json",

   }
    e=requests.post("http://20.251.32.19:8999/v1/templates", data=json.dumps(t), headers=headers)
    mess=json.loads(e.text)
    #print mess
    #t = mess['template']['contents']
    return mess

request_body =  {
    "disable_rollback": True,
    "files": getTemplate(test1)['template']['files'],
    "parameters": {
        "network": "bba5a0a8-3d12-45c0-a770-dfd9e1787d5c",
        "imageId": "e5ae19c0-0093-45a2-bf78-09b4a7c78337",
        "subnet": "7c7f9d3d-5206-4029-9db4-57636812bb3d",
        "sgroup": "286deb58-053a-47d6-a58e-7dc2ab6ca796",
        "password": "m1.tiny",
        "maxCount": 2,
        "floating_ip": "auto",
        "floating_network": "fb29d7ff-d4d1-483b-929b-53c67bcb7d48",
        "vol_size": 10


    },
    "stack_name": "gcloud-serverw123",
    "environment": {},
    "template": getTemplate(test1)['template']['contents'],
    "iscaler": False,
    "enduser_id": "8ad84e12-7dbb-4ce5-8755-b624056d8433",
    "description": "just for test",
    "app_name": "gcloud-serverert123",

}
from nest_template import t as nested_json
request_scale_body =  {
    "disable_rollback": True,
      "files": getTemplate(test_scaleUpFirst)['template']['files'],
    "parameters": {
        "network": "322ca833-79b4-45f9-82fa-3dca31f7d330",
        "imageId": "e5ae19c0-0093-45a2-bf78-09b4a7c78337",
        "subnet": "03096d5e-d633-4dde-814a-f32d8d7ec58c",
        "sgroup": "286deb58-053a-47d6-a58e-7dc2ab6ca796",
        "password": "m1.tiny",
        #"maxCount": 1,
        "floating_ip": "auto",
        "floating_network": "fb29d7ff-d4d1-483b-929b-53c67bcb7d48",
        "cputil_threshold_high": 90,
        "cputil_threshold_low": 20,
        "member_port": 80,
        "protocol": "HTTP",
        "vol_size": 10,
       "read_bytes_high_threshold": 1000000,
       "read_bytes_low_threshold": 200,
       "write_bytes_high_threshold": 1000000,
       "write_bytes_low_threshold": 200


    },
    "stack_name": "gcloud-scaleupfirst",
    "environment": {},
    "template": getTemplate(test_scaleUpFirst)['template']['contents'],
    "isscaler": True,
    "enduser_id": "8ad84e12-7dbb-4ce5-8755-b624056d8433",
    "description": "just for test",
    "app_name": "gcloud-scaleupfirst",

}

