__author__ = 'Administrator'
import requests
import token
import json
if  __name__ == "__main__":
    #body = '{"port":{"network_id":"ec4229b6-004f-4c2c-a3c6-7068853beefe" ,"fixed_ips": [{"subnet_id": "936183e5-e053-46e2-8cfa-3ee95ce32a20", "ip_address": "192.128.19.122"}], "name":"private-port","admin_state_up":true}}'
    body =  '{"port":{"network_id":"ec4229b6-004f-4c2c-a3c6-7068853beefe","name":"sss-xm","fixed_ips": [{"subnet_id": "936183e5-e053-46e2-8cfa-3ee95ce32a20","ip_address": "198.128.19.111"}],"admin_state_up":true}}'
    headers = {
    "Accept": "application/json",
    "X-Auth-Token": token.get_token(),
    "Content-Type": "application/json",
   }
    e=requests.post("http://20.251.32.19:9696/v2.0/ports.json", data=body, headers=headers)
    print e.text
