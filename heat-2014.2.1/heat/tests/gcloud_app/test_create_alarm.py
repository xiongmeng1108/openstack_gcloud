__author__ = '95'

import unittest
import token
import requests
import json
import template.alarm  as s
headers = {
    "Accept": "application/json",
    "X-Auth-Token": token.get_token(),
    "Content-Type": "application/json",
    "X-Auth-Key": "123456789",
    "X-Auth-User": "zhangyk"


}


if __name__ == '__main__':
    e=requests.post("http://20.251.32.19:8004/v1/a4f8c0eb051c48de90ae33c2c8c96087/stacks", data=json.dumps(s.request_body), headers=headers)
    print e.text
