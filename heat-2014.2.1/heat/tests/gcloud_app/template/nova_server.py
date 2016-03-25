t ={
  "heat_template_version": "2013-05-23",
  "description": "The heat template is used to demo the 'console_urls' attribute\nof OS::Nova::Server.\n",
  "parameters": {
    "image": {
      "type": "string"
    },
    "flavor": {
      "type": "string",
      "default": "m1.tiny"
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
        "image": {
          "get_param": "image"
        },
        "flavor": {
          "get_param": "flavor"
        },
        "metadata": {
           "metering.stack": "1fe9fe22-e7e5-4fcf-bd6a-0eb9ffec9ea6"
        },
        "networks": [
          {
            "network": {
              "get_param": "network"
            }
          }
        ]
      }
    }
  },

}

request_body =  {
    "disable_rollback": True,
    "parameters": {
        "image": "centos7-two",
        "flavor": "m1.tiny",
        "network": "1309dfd4-ba56-4b1f-bb7b-61f58e960b72"
    },
    "stack_name": "test_create_nova_serve12345r",
    "environment": {},
    "template": t,
    "iscaler": False,
    "enduser_id": "8ad84e12-7dbb-4ce5-8755-b624056d8433",
    "description": "just for test",
    "app_name": "test_create_nova_server124556"
}
