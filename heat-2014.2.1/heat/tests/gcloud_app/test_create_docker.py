__author__ = 'Administrator'

import token

import template.nova_server as s
import  requests
import json

t ={
  "heat_template_version": "2013-05-23",
  "description": "Heat template to deploy Docker containers to an existing host",
  "resources": {
    "nginx-01": {
      "type": "DockerInc::Docker::Container",
      "properties": {
        "image": "nginx",
        "docker_endpoint": "tcp://127.0.0.1:2376",
        "port_bindings": {
          "8080": 82
        }
      }
    }
  }
}

headers = {
    "Accept": "application/json",
    "X-Auth-Token": token.get_token(),
    "Content-Type": "application/json",


}

request_body =  {
    "disable_rollback": True,
    "stack_name": "test_create_docker",
    "environment": {},
    "template": t,
    "iscaler": False,
    "enduser_id": "8ad84e12-7dbb-4ce5-8755-b624056d8433",
    "description": "just for test",
    "app_name": "test_create_docker"
}
if __name__ == "__main__":

    e=requests.post("http://20.251.32.19:8004/v1/89be410401a5493198287bc84866a364/stacks", data=json.dumps(request_body), headers=headers)
    print e.text



