__author__ = 'Administrator'

import token
from template.server import request_body
import  requests
import json

headers = {
    "Accept": "application/json",
    "X-Auth-Token": token.get_token(),
    "Content-Type": "application/json",
#template
}
if __name__ == "__main__":

    print  json.dumps(request_body, indent=4)
    e=requests.put("http://20.251.32.19:8004/v1/89be410401a5493198287bc84866a364/stacks/gcloud-serverwe34565/2e0839ac-15fa-49e7-8ac7-026c6728635b", data=json.dumps(request_body), headers=headers)
    #e = requests.delete("http://20.251.32.19:8004/v1/89be410401a5493198287bc84866a364/stacks/test_create_gcloud_serverggg/6decfa0d-7122-42e8-9521-50fd5eaf3f59?task_id=da0c69d9-f680-4030-a528-4e60e945f47e", headers=headers)
    print e.text



