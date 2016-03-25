import requests
from oslo.config import cfg
from neutron.openstack.common import log as logging
import json
from oslo.config import cfg
LOG = logging.getLogger(__name__)
#cfg.CONF

def get_token_id(context):
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

    auth_url = cfg.CONF.auth_url
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
            if v["name"] == name and cfg.CONF.auth_region == v['endpoints'][0].get('region', None):
                target = v
                break
        return target['endpoints'][0].get('publicURL',"http://localhost//")
    else:
        #raise exception.ServiceUrlNotFound(text=response.text)
        raise Exception(response.text)



def g_cloud_request(url, properties, context, prefix):
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

    token_id = get_token_id(context)
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



"""
class GcloudComputeRequestException(exception.HeatException):
    msg_fmt = _('%(message)s')

    def __init__(self, message=_('unknown reason'), **kwargs):
        super(GcloudComputeRequestException, self).__init__(message=message, **kwargs)

"""


def check_response(response):
    data = response.get("data", None)
    if data:
        return data
    else:
        raise Exception("get vm info error")








class ComputeClient(object):
    def __init__(self,):
        self.context = {
          "username": cfg.CONF.admin_user,
          "password": cfg.CONF.admin_password,
          "tenantName": cfg.CONF.admin_tenant_name
        }
        LOG.debug("compute client init and  context is %s" %self.context)
        self.public_url = get_public_url(self.context, cfg.CONF.auth_url+"/tokens", "gcompute")


    def detail(self, inst_id):
        properties = dict()
        properties['id'] = inst_id
        response = g_cloud_request(self.public_url+"/vm/detail.do", properties, self.context, "desic")
        #return response.get("data", None)
        return check_response(response)
















