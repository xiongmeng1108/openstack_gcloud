__author__ = '95'


import requests
import json
def get_public_url(token_id, auth_url, name):
    body = {
        "auth":{
            "tenantName": "admin",
            "token": {
                "id": token_id
            }
        }
    }
    headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    }
    response = requests.post(auth_url, data=json.dumps(body), headers=headers)
    print response.text
    response_json= json.loads(response.text)
    print json.dumps(response_json, indent=4)
    target=None
    for v in response_json["access"]["serviceCatalog"]:
        print v["name"]
        if v["name"] == name:
            target = v
            break
    print target
    print target['endpoints'][0].get('pulibcURL1',None)
def test_url(url, properties, prdfix):
    url = url+"?"
    for key ,value in properties.items():
        part = "%s.%s=%s&" %(prdfix, key,  value)
        url+=part
    print url[:-1]

def test(a,*b,**c):
    print  (a,b,c)

def test2():
    raise  Exception
    #return 8+8
def test1():
    print "ddd"
    yield 1
    yield 2+3
    yield test2()
    yield 3
class A(object):
    def __init__(self):
        self.a= "123"

class B(A):
   pass
import json
if __name__ =="__main__":
    #get_public_url( "b93b3ddde2244f43b205c481eccf758a", "http://20.251.32.19:35357/v2.0/"+"/tokens")

    #test_url("http://20.251.32.19:35357/v2.0/", {"A":2,"B":3}, "ric")
    get_public_url("bdb41e009bb641b9bf97e6d549c5bc76","http://20.251.32.19:5000/v2.0/tokens", "gcompute" )
    #t=test1()
    #print next(t)
    #print  next(t)
    #try:
       # next(t)
    #except:
     #   print "ddd"
     #b= B()
     #print b.c
     #next(t)