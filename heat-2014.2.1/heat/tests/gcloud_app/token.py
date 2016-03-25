

import requests
import json
headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",

}

body= {"auth":{"tenantName": "admin","passwordCredentials":{"username":"admin","password":"gcloud123"}}}

def get_token():
    e=requests.post("http://20.251.44.13:5000/v2.0/tokens", data=json.dumps(body), headers=headers)
    print e.status_code== 200
    return json.loads(e.text)["access"]["token"]["id"]



if __name__ == "__main__":
    print get_token()

