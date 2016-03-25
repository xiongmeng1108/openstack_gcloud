__author__ = 'Administrator'



import template.server as s
import  requests
import json
import token
headers = {
    "Accept": "application/json",
    "X-Auth-Token": token.get_token(),
    "Content-Type": "application/json",
    "G-Task-Id": "f8f15b11-d7fe-4132-ac4a-17fa3c85f29e"

}
if __name__ == "__main__":

    e=requests.post("http://20.251.44.13:8004/v1/854b9f54e643442eb5083d35790274f7/stacks", data=json.dumps(s.request_body), headers=headers)
    print  json.dumps(s.request_body, indent=4)
    print e.status_code
    print e.text
