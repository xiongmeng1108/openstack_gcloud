__author__ = 'Administrator'

import token

import template.server as s
import  requests
import json

headers = {
    "Accept": "application/json",
    "X-Auth-Token": token.get_token(),
    "Content-Type": "application/json",

}
if __name__ == "__main__":


    e=requests.post("http://20.251.32.19:8004/v1/89be410401a5493198287bc84866a364/stacks?task_id=da0c69d9-f680-4030-a528-4e60e945f47e", data=json.dumps(s.request_scale_body), headers=headers)
    #e = requests.delete("http://20.251.32.19:8004/v1/89be410401a5493198287bc84866a364/stacks/test_create_gcloud_serverggg/6decfa0d-7122-42e8-9521-50fd5eaf3f59?task_id=da0c69d9-f680-4030-a528-4e60e945f47e", headers=headers)
    print  json.dumps(s.request_scale_body, indent=4)
    print e.text

