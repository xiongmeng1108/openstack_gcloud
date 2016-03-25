__author__ = 'Administrator'



import template.autoScaleTemplate as s
import requests
import json
import token

headers = {
    "Accept": "application/json",
    "X-Auth-Token": token.get_token(),
    "Content-Type": "application/json",


}
if __name__ == "__main__":

    e=requests.post("http://20.251.32.19:8004/v1/a4f8c0eb051c48de90ae33c2c8c96087/stacks", data=json.dumps(s.request_body), headers=headers)
    print e.text

