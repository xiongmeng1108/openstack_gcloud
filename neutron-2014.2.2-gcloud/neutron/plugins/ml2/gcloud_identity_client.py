
from neutron import context

import requests

from neutron.openstack.common import log as logging
import json

LOG = logging.getLogger(__name__)
#cfg.CONF

def get_token_id(context,auth_uri=None):
    body = {
        "auth": {
            "tenantName": context.get("tenantName","admin"),
            "passwordCredentials": {
            "username": context.get("username", "admin"),
            "password": context.get("password", "admin")
           }
        }
    }
    headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    }

    auth_url = auth_uri
    response = requests.post(auth_url+"/tokens", data=json.dumps(body), headers=headers)
    if response.status_code == 200 or response.status_code == 203:
        response_json = json.loads(response.text)
        return response_json["access"]["token"]["id"]
    else:
       raise Exception(response.text)





def get_public_url(context, auth_url, name):

    body = {
        "auth": {
            "tenantName": context.get("tenantName","admin"),
            "passwordCredentials": {
            "username":  context.get("username", "admin"),
            "password": context.get("password", "admin")
           }
        }
    }
    headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    }
    response = requests.post(auth_url, data=json.dumps(body), headers=headers)
    if response.status_code == 200 or response.status_code == 203:
        response_json= json.loads(response.text)
        target=None
        for v in response_json["access"]["serviceCatalog"]:
            if v["name"] == name: #and cfg.CONF.auth_region == v['endpoints'][0].get('region', None):
                target = v
                break
        if target:
            #LOG.debug("response is region %s " % (target['endpoints'][0].get('region', None)))
            #LOG.debug("response is url %s " %(target['endpoints'][0].get('adminURL',None)))
            #LOG.debug("response is url %s " %(json.dumps(response_json, indent=4)))
            return target['endpoints'][0].get('adminURL',None), target['endpoints'][0].get('region', None)
        else:
            LOG.debug("get_public_url is not found")
            return None
    else:
        #raise exception.ServiceUrlNotFound(text=response.text)
        raise Exception(response.text)



def g_cloud_request(url, properties, context, prefix,keystone_uri):
    params = {}
    for key, value in properties.items():
        if prefix:
            n_key = "%s.%s" %(prefix, key)
        else:
            n_key = key
        params[n_key] = value
    #params["token_id"] = token_id
    ##just for  test
    #params["loginUser.userId"] = "5f309439e6aa44619201c333e45f9933"
    ###end

    token_id = get_token_id(context,auth_uri=keystone_uri)
    headers = {
    "X-Auth-Token": token_id
    }
    result = requests.get(url,params=params, headers=headers)
    LOG.debug("response is  %s and the url is  %s" % (result.text, result.url))
    json_mess = None
    try:
        json_mess = json.loads(result.text)
    except Exception, e:
        LOG.debug("Exception is  %s" %e)
        #json_mess = {"success": "error"}
        raise  e

    return json_mess

class Client(object):

    def __init__(self,user_name=None,user_pass=None,tenantName=None,auth_url=None,region_id=None):
        self.ctx = context.Context(user_id=None, tenant_id=None, roles=None,
                              user_name=user_name, tenant_name=None,
                              request_id=None, auth_token=None)
        self.context={"tenantName":tenantName,
                      "username":user_name,
                      "password":user_pass}
        self.auth_url=auth_url
        self.gc_identiry_url , self.region_id= get_public_url(self.context, auth_url+"/tokens", "gcidentity")
        self.region_id=region_id

    def report_floatingip_count(self,userId=None,count=None):
        try:
             #get token
             #create request and response
            properties = dict()
            properties['userId'] = userId
            properties['floatingIp']=count
            properties['regionId']=self.region_id
            properties['cpu']=-1
            properties['storage']=-1
            properties['memory']=-1
            #cpu=xxx&memory=xxx&storage=xxx&floatingIp=
            if self.gc_identiry_url is None:
                LOG.error("report_floatingip_count can not found gcloud-identity service")
                return
            response = g_cloud_request(self.gc_identiry_url+"/user/resource_used.do", properties, self.context,None,self.auth_url)
        except Exception, e:
             LOG.debug("Exception is  %s" %e)
             raise  e
