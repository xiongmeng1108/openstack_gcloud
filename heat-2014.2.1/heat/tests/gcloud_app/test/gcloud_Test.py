__author__ = 'Administrator'

import unittest
import requests

import json

def get_token():
    headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",

}

    body= {"auth":{"tenantName": "admin","passwordCredentials":{"username":"admin","password":"ADMIN_PASS"}}}
    e=requests.post("http://20.251.32.19:5000/v2.0/tokens", data=json.dumps(body), headers=headers)
    return json.loads(e.text)["access"]["token"]["id"]
t = {
      "description": "g_cloud  server",
      "heat_template_version": "2013-05-23",
      "outputs": {
        "website_url": {
          "value": {
            "str_replace": {
              "params": {
                "host": {
                  "get_attr": [
                    "floating",
                    "floating_ip_address"
                  ]
                }
              },
              "template": "http://host/"
            }
          }
        }
      },
      "parameters": {
      },
      "resources": {
        "floating": {
          "properties": {
            "fixed_ip_address":  "12.12.3.4",
            "floating_ip_address": "12.34.56.5",
            "floating_network": "322ca833-79b4-45f9-82fa-3dca31f7d330",
            "port_id": "fdfdgdfgfdg"
          },
          "type": "OS::Neutron::FloatingIP"
        },


      }
}

headers = {
    "Accept": "application/json",
    "X-Auth-Token": get_token(),
    "Content-Type": "application/json",

}
class MyTestCase(unittest.TestCase):
    def test_something(self):
        self.assertEqual(True, False)


    def test_create_floating(self):
        request_body =  {
    "disable_rollback": True,

    "stack_name": "gcloud-folating",
    "environment": {},
    "template": t,
    "iscaler": False,
    "enduser_id": "8ad84e12-7dbb-4ce5-8755-b624056d8433",
    "description": "just for test",
    "app_name": "folating",

    }
        e=requests.post("http://20.251.32.19:8004/v1/89be410401a5493198287bc84866a364/stacks?task_id=da0c69d9-f680-4030-a528-4e60e945f47e", data=json.dumps(request_body), headers=headers)
        #e = requests.delete("http://20.251.32.19:8004/v1/89be410401a5493198287bc84866a364/stacks/test_create_gcloud_serverggg/6decfa0d-7122-42e8-9521-50fd5eaf3f59?task_id=da0c69d9-f680-4030-a528-4e60e945f47e", headers=headers)
        print e.text



if __name__ == '__main__':
    unittest.main()
