#coding=utf-8
__author__ = 'Administrator'
import datetime
import time
import requests
import json
import token
if  __name__=="__main__":

 test1={
    "template":{
        "name": "mysql自动部署12346",
        "type": "deploy",
        "description": "for test",
        "resources": {
            "InstanceResource": {
                "attachVolumeType": "RBD",  #attachVolumeType
                "instanceStorageType": "1",
                "isFloating": False,
                "cpu": 2,
                "memory": 1024,
               "maxCount": 1
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
                "attachVolumeType": "local",
                "instanceStorageType": "1",
                "isFloating": False,
                "core": 2,
                "memory": 1024,
            },
            "ScalingPolicyAlarmResource": {
                "alarmTypelist": ["cpu_util", "mem_util", "disk_io_read", "disk_io_write"],
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

 test_scaleOut={
    "template":{
        "name": "apache",
        "type": "cluster",
        "description": "for test",
        "resources": {
            "InstanceResource": {
                "attachVolumeType": "RBD",
                "instanceStorageType":"1",
                "isFloating": False,
                "core": 2,
                "memory": 1024,
            },
            "ScalingPolicyAlarmResource": {
               # "alarmTypelist": ["cpu_util", "mem_util", "disk_io_read", "disk_io_write"],
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
                "core": 1,
                "memory": 512,
            },
            "ScalingPolicyAlarmResource": {
               # "alarmTypelist": ["cpu_util", "mem_util", "disk_io_read", "disk_io_write"],
               "alarmTypelist": ["disk_io_read"],
                "policy": {
                    "policyType": "scaleUp",
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


 headers = {
    "Accept": "application/json",
    "X-Auth-Token": token.get_token(),
    "Content-Type": "application/json",

}
e=requests.post("http://20.251.44.13:8999/v1/templates", data=json.dumps(test1), headers=headers)
#print e.text
mess=json.loads(e.text)
print json.dumps(mess, sort_keys=True, indent=2)


