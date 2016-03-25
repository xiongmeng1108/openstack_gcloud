import requests
from oslo.config import cfg
from heat.openstack.common import log as logging
import json
from heat.common.i18n import _
from oslo.config import cfg
from heat.common import exception
LOG = logging.getLogger(__name__)
#cfg.CONF

def get_token_id(context):
    body = {
        "auth": {
            "tenantName": "admin",
            "passwordCredentials": {
            "username": context.username,
            "password": context.password
           }
        }
    }
    headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    }
    if context.auth_url:
        auth_url = context.auth_url
    else:
        auth_url = cfg.CONF.keystone_authtoken.auth_uri
    response = requests.post(auth_url+"/tokens", data=json.dumps(body), headers=headers)
    if response.status_code == 200 or response.status_code == 203:
        response_json = json.loads(response.text)
        return response_json["access"]["token"]["id"]
    else:
        raise exception.ServiceUrlNotFound(text=response.text)




def get_public_url(context, auth_url, name):

    body = {
        "auth": {
            "tenantName": "admin",
            "passwordCredentials": {
            "username": context.username,
            "password": context.password
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
            if v["name"] == name:
                for endpoint in v['endpoints']:
                    if cfg.CONF.region_name_for_services == endpoint.get('region', None):
                        return endpoint.get('adminURL',"http://localhost//")

        return "http://localhost//"
    else:
        raise exception.ServiceUrlNotFound(text=response.text)


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
    if context.auth_token is None:
        token_id = get_token_id(context)
    else:
        token_id = context.auth_token
    headers = {
    "X-Auth-Token": token_id,
    "G-Auth-ResourceType": 1,
    }
    result = requests.get(url,params=params, headers=headers)
    LOG.debug(_("response is  %s and the url is  %s") % (result.text, result.url))
    json_mess = None
    try:
        json_mess = json.loads(result.text)
    except Exception, e:
        LOG.debug(_("Exception is  %s") %e)
        #json_mess = {"success": "error"}
        raise  e

    return json_mess


class GcloudTaskStatusReport(object):

    def __init__(self, context):
        self.context = context
        if self.context.auth_url:
            self.auth_url = self.context.auth_url
        else:
            self.auth_url = cfg.CONF.keystone_authtoken.auth_uri

        self.public_url = get_public_url(context, self.auth_url+"/tokens", "glog")

    def report_task_status(self, properties):
        response = g_cloud_request(self.public_url+"/log/feedback.do", properties, self.context, None)
        return response




class GcloudComputeRequestException(exception.HeatException):
    msg_fmt = _('%(message)s')

    def __init__(self, message=_('unknown reason'), **kwargs):
        super(GcloudComputeRequestException, self).__init__(message=message, **kwargs)




def check_response(response):
    data = response.get("data", None)
    if data:
        return data
    else:
        if response.get('ComputeError',{"code": "unknown reason"}).get('code', None) ==\
               "compute_controller_vm_291001" or response.get('ComputeError',
              {"code": "unknown reason"}).get('code', None) == "compute_controller_vm_290001":
            # just for vm  not found
            return {"trashed": "trashed", "status": "error"}
        #else:
        #    raise GcloudComputeRequestException(**response.get('ComputeError', {"message": "unknown reason"}))
        #if response.get('ComputeError',None) is not None:
        #    return {"trashed": "trashed", "state": "error"}
        else:
            raise GcloudComputeRequestException(**response.get('ComputeError', {"message": "unknown reason"}))



class VolumeClient(object):

    def __init__(self, context):

        self.private_ip = None
        self.context = context
        if self.context.auth_url:
            self.auth_url = self.context.auth_url
        else:
            self.auth_url = cfg.CONF.keystone_authtoken.auth_uri
        #cfg.CONF.region_name_for_services
        #self.public_url_compute = get_public_url(context, self.auth_url+"/tokens", "gcompute")
        self.public_url = get_public_url(context, self.auth_url+"/tokens", "esb")+"%s%s" %("/",cfg.CONF.region_name_for_services)

    def create(self, properties):
        response = g_cloud_request(self.public_url+"/volume/create.do", properties, self.context, None)
        return response

    def delete(self, volume_id):
        properties = dict()
        properties['volume_id[0]'] = volume_id
        properties['operation'] = "delete"
        response = g_cloud_request(self.public_url+"/volume/logical_delete.do", properties, self.context, None)
        return response

    def detail(self, volume_id):
        properties = dict()
        properties['volume_id'] = volume_id
        response = g_cloud_request(self.public_url+"/volume/info.do", properties, self.context, None)
        return response


class ComputeClient(object):
    def __init__(self, context):

        self.private_ip = None
        self.context = context
        if self.context.auth_url:
            self.auth_url = self.context.auth_url
        else:
            self.auth_url = cfg.CONF.keystone_authtoken.auth_uri
        #cfg.CONF.region_name_for_services
        self.public_url_compute = get_public_url(context, self.auth_url+"/tokens", "gcompute")
        self.public_url = get_public_url(context, self.auth_url+"/tokens", "esb")+"%s%s" %("/",cfg.CONF.region_name_for_services)

    def create(self, properties):
        response = g_cloud_request(self.public_url+"/vm/create_image.do", properties, self.context, "ric")
        return response

    def detail(self, inst_id):
        properties = dict()
        properties['instanceId'] = inst_id
        response = g_cloud_request(self.public_url_compute+"/vm/detail.do", properties, self.context, "desic")
        #return response.get("data", None)
        return check_response(response)


    def soft_delete(self, inst_id):
        properties = dict()
        properties['instanceId[0]'] = inst_id
        properties['isAppDelete'] = "true"
        response = g_cloud_request(self.public_url+"/trash/logical_delete_vm.do", properties, self.context, "ldins")
        #return response.get("data", None)
        return response

    def delete(self, inst_id):
        properties = dict()
        properties['instanceIds[0]'] = inst_id
        response = g_cloud_request(self.public_url+"/vm/delete.do", properties, self.context, "dv")
        #return response.get("data", None)
        return response


    def suspend(self, inst_id):
        properties = dict()
        properties['instanceIds'] = inst_id
        response = g_cloud_request(self.public_url_compute+"/vm/stop.do", properties, self.context, "sdic")
        #return response.get("data", None)
        return response

    def resume(self, inst_id):
        properties = dict()
        properties['instanceIds'] = inst_id
        response = g_cloud_request(self.public_url_compute+"/vm/start.do", properties, self.context, "sic")
        #return response.get("data", None)
        return response

    def config_vm(self, properties):
        response = g_cloud_request(self.public_url+"/vm/config.do", properties, self.context, "chgc")
        return response

    def attach_volume(self, inst_id, volume_id):
        properties = dict()
        properties['instanceId'] = inst_id
        properties['volumeId'] = volume_id
        return g_cloud_request(self.public_url_compute+"/vm/attach_vo.do", properties, self.context, "ao")

    def detach_volume(self, inst_id, volume_id):
        properties = dict()
        properties['instanceId'] = inst_id
        properties['volumeId'] = volume_id
        return  g_cloud_request(self.public_url_compute+"/vm/detach_vo.do", properties, self.context, "dv")

    def list_volume(self, inst_id):
        properties = dict()
        properties['instanceId'] = inst_id
        return g_cloud_request(self.public_url_compute+"/volume/info_list.do", properties, self.context, "vf")
        #return g_cloud_request(self.public_url+"/volume/info_page", properties, self.context, "vf")


class NeutronClient(object):
    def __init__(self, context):
        self.private_ip = None
        self.context = context
        if self.context.auth_url:
            self.auth_url = self.context.auth_url
        else:
            self.auth_url = cfg.CONF.keystone_authtoken.auth_uri
        self.public_url = get_public_url(context, self.auth_url+"/tokens", "esb")+"%s%s" %("/",cfg.CONF.region_name_for_services)

    def create(self, properties):
        try:
            response = g_cloud_request(self.public_url+"/network/create_floatingip.do", properties, self.context, None)
            if not response.get("success",False):
                raise Exception("create and associate floatingip failed!")
        except Exception,e:
             raise e
        return response


    def delete(self, floatingipId):
        properties = dict()
        properties['floatingipId'] = floatingipId
        #properties['portId'] = ""
        #g_cloud_request(self.public_url+"/network/update_floatingip.do", properties, self.context, None)
        #properties.pop('portId')
        response = g_cloud_request(self.public_url+"/network/delete_floatingip.do", properties, self.context, None)
        return response

    def detail(self, floatingipId):
        properties = dict()
        properties['floatingipId'] = floatingipId
        response = g_cloud_request(self.public_url+"/network/info_floatingip.do", properties, self.context, None)
        return response










