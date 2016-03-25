# -*- coding:utf-8 -*-
from heat.openstack.common import log as logging
from heat.engine import resource
from heat.engine import attributes
from heat.engine import constraints
from heat.engine import properties
from heat.common.i18n import _
from heat.common import short_id
import time
LOG = logging.getLogger(__name__)
from client import ComputeClient

class Server(resource.Resource):

  #
  #  资源配置参数
    PROPERTIES = (
        ALIAS, HOSTNAME, IMAGE_ID,  MAX_COUNT, STORAGE_TYPE, CORE, MEMORY,
        SGROUP, NETWORK, SUBNET, PASSWORD, VOLUMEID, STACKID,USER_DATA_FORMAT,USER_DATA,VGID,
    ) = (
    "alias", "hostname", "imageId", "maxCount", "storageType",
    "core",  "memory", "sgroup", "network", "subnet", 'password', 'volumeId', "stackId",
    'user_data_format',  'user_data', 'vgId',
    )

    _SOFTWARE_CONFIG_FORMATS = (
        HEAT_CFNTOOLS, RAW, SOFTWARE_CONFIG
    ) = (
        'HEAT_CFNTOOLS', 'RAW', 'SOFTWARE_CONFIG'
    )
   #资源运行状态的属性值
    ATTRIBUTES = (
     INSTANCE_ID, FIRST_IP, FIRST_PORT_ID, HOST_NAME
    ) = (
     "instaceId", "first_address", "first_port_id", "host_name"
    )
   #资源配置参数约束
    properties_schema = {
      ALIAS: properties.Schema(
          properties.Schema.STRING,
          _('Server Alias.'),
          update_allowed=True
      ),
      HOSTNAME: properties.Schema(
          properties.Schema.STRING,
          _('Server Hostname.'),
          update_allowed=False
      ),
      VOLUMEID: properties.Schema(
          properties.Schema.STRING,
          _('volume id.'),
          update_allowed=False
      ),
      IMAGE_ID: properties.Schema(
          properties.Schema.STRING,
          _("server image id"),
          required=True,
          update_allowed=False
      ),
      MAX_COUNT: properties.Schema(
          properties.Schema.INTEGER,
          _("server count"),
          default=1,
          update_allowed=False

      ),
      STORAGE_TYPE: properties.Schema(
          properties.Schema.STRING,
          _("vlume storage type"),
          default="local",
          update_allowed=False

      ),
      CORE: properties.Schema(
          properties.Schema.INTEGER,
          _("vm cpu count"),
          default=1,
          update_allowed=True
      ),
      MEMORY: properties.Schema(
          properties.Schema.INTEGER,
          _("vm memory count"),
          default=512,
          update_allowed=True
      ),

      SGROUP: properties.Schema(
          properties.Schema.STRING,
          _("security group id"),
          update_allowed=True
      ),

      NETWORK: properties.Schema(
          properties.Schema.STRING,
          _("network  id"),
          required=True,
          update_allowed=True
      ),

       SUBNET: properties.Schema(
          properties.Schema.STRING,
          _("subnet  id"),
          required=True,
          update_allowed=True
      ),

       PASSWORD: properties.Schema(
          properties.Schema.STRING,
          _("vm password"),
          default="123456",
          update_allowed=True
      ),
      STACKID: properties.Schema(
          properties.Schema.STRING,
          _("id of parents stack "),
          default="owner",
          update_allowed=True
      ),
      USER_DATA: properties.Schema(
            properties.Schema.STRING,
            _('User data script to be executed by cloud-init.'),
            default=''
        ),
      USER_DATA_FORMAT: properties.Schema(
            properties.Schema.STRING,
            _('How the user_data should be formatted for the server. For '
              'HEAT_CFNTOOLS, the user_data is bundled as part of the '
              'heat-cfntools cloud-init boot configuration data. For RAW '
              'the user_data is passed to Nova unmodified. '
              'For SOFTWARE_CONFIG user_data is bundled as part of the '
              'software config data, and metadata is derived from any '
              'associated SoftwareDeployment resources.'),
            default=RAW,
            constraints=[
                constraints.AllowedValues(_SOFTWARE_CONFIG_FORMATS),
            ]
        ),
        VGID: properties.Schema(
          properties.Schema.STRING,
          _("name of storge pool"),
          update_allowed=False
      ),

    }
    attributes_schema = {
      INSTANCE_ID: attributes.Schema(
          _("instance id")
      ),
      FIRST_IP: attributes.Schema(
          _("first ip")
      ),
      FIRST_PORT_ID: attributes.Schema(
          _("first port id")
      ),
      HOST_NAME: attributes.Schema(
          _("host of vm")
      )
    }

    def __init__(self, name, json_snippet, stack):
        self.client = ComputeClient(stack.context)
        self.inst_id = None
        self.core = None
        self.memory = None
        self.vm_config = dict()
        super(Server, self).__init__(name, json_snippet, stack)
    #创建资源
    def handle_create(self):
        LOG.debug(_("G_cloud  server create"))
        properties = dict()
        for key, value in self.properties.items():
            if key == self.USER_DATA:
                if self.properties[self.USER_DATA] and self.properties[self.USER_DATA_FORMAT] == self.RAW:
                    properties['userdata'] = self.properties[self.USER_DATA]
            else:
                properties[key] = self.properties[key]
        properties.pop(self.USER_DATA_FORMAT)
        properties.update({"alias": short_id.generate_id()})
        properties.update({"netcardName": short_id.generate_id()})
        if self.properties[self.STACKID] == "owner":
            properties.update({"appId": self.stack.id})
        else:
            properties.update({"appId": self.properties[self.STACKID]})
        #if self.properties[self.CREATE_USER_ID] != "owner":
        #    properties.update({"createUserId": self.properties[self.CREATE_USER_ID]})
        #properties.update({"appType": self.stack.stack_apps_style})
        #properties.update({"appName": self.stack.app_name})
        properties[self.NETWORK] = self.properties[self.SUBNET]
        properties.pop(self.SUBNET)
        server = self.client.create(properties)
        if server['success']:
            self.inst_id = server['data'][0]['instanceId']
            self.resource_id_set(self.inst_id)
        return server
        #return  {"server": {"id": "i-abcd", "firstIp": "192.168.4.5"}}

    #更新资源
    def handle_update(self, json_snippet=None, tmpl_diff=None, prop_diff=None):

         if self.CORE in prop_diff or self.MEMORY in prop_diff:
             prop_diff['instanceId'] = self.resource_id
             prop_diff['diskSize'] = 0
             core = prop_diff.get("core", None)
             memory = prop_diff.get("memory", None)
             prop_diff['autoStart']= 0
             prop_diff['isHa']= False
             prop_diff['cpu']= prop_diff['core']
             prop_diff.pop('core')
             if core:
                 self.vm_config['core'] = core
             if memory:
                 self.vm_config['memory'] = memory
             try:
                 server = self.client.config_vm(prop_diff)
             except Exception, e:
                 self.stack.error_codes.append('heat_server_task_00005')
                 raise e
             return server


    #删除资源
    def handle_delete(self):
        LOG.debug(_("G_cloud  server delete"))
        if self.resource_id is None:
            return
        return self.client.soft_delete(self.resource_id)


    def handle_suspend(self):
        LOG.debug(_("G_cloud  server stop"))
        return self.client.suspend(self.resource_id)



    def handle_resume(self):
        LOG.debug(_("G_cloud  server start"))
        return self.client.resume(self.resource_id)

    def _create(self, server):
         LOG.debug("gcloud create checking")
         if server['success']:
            inst_id = server['data'][0]['instanceId']
            status = self.client.detail(inst_id)
            if status:
                if status['state'] == "Extant":
                    LOG.debug("gcloud create suscess")
                    return True
                elif  status['state'] == "error":
                    self.stack.error_codes.append('heat_server_task_00001')
                    raise resource.ResourceUnknownStatus(
                        resource_status="error",
                        result=_('gcloud server create fail'))
                else:
                    return False
            else:
                self.stack.error_codes.append('heat_server_task_00001')
                raise resource.ResourceUnknownStatus(
                    resource_status="error",
                    result=_('gcloud server create fail'))
         else:
            self.stack.error_codes.append('heat_server_task_00001')
            raise resource.ResourceUnknownStatus(
                resource_status="error",
                result=_('gcloud server create fail'))

    #检查创建操作是否完成，返回True为完成，Fals为未完成
    def check_create_complete(self, server):
        try:
            return self._create(server)
        except Exception as ex:
            self.stack.error_codes.append('heat_server_task_00001')
            raise ex


    def check_update_complete(self, server):
        try:
            status = self.client.detail(self.resource_id)
        except Exception, e:
            self.stack.error_codes.append('heat_server_task_00002')
            raise e
        if status and status['state'] == "Extant":
            flag = len(self.vm_config)
            for key, value in self.vm_config.items():
                if value == status.get(key, None):
                    flag -= 1
            if flag == 0:
                return True
            else:
                return False

        else:
            return False


    def check_delete_complete(self, server):
        try:
            if self.resource_id is None:
                return True
            status = self.client.detail(self.resource_id)
        except Exception, e:
            self.stack.error_codes.append('heat_server_task_00002')
            raise e
        if status and status['trashed'] == "trashed":
            return True
        else:
            return False


    def check_suspend_complete(self, server):
        try:
            status = self.client.detail(self.resource_id)
        except Exception, e:
            self.stack.error_codes.append('heat_server_task_00002')
            raise e
        if status and status['state'] == "Shutoff":
            return True
        else:
            return False

    def check_resume_complete(self, server):
        try:
            status = self.client.detail(self.resource_id)
        except Exception, e:
            self.stack.error_codes.append('heat_server_task_00002')
            raise e
        if status and status['state'] == "Extant":
            return True
        else:
            return False

    def _get_first_ip(self):
        try_count = 0
        ip= None
        while  True:
            status = self.client.detail(self.resource_id)
            if status and status['ipAddress'] != "":
                ip = status['ipAddress']
                LOG.debug(_("the first address is %s") %ip)
                break
            else:
                if try_count == 4:
                    LOG.debug(_("get the  first ip timeout") )
                    break
                else:
                    try_count += 1
                    time.sleep(5)
        return ip


    def _get_first_port_id(self):
        try_count = 0
        id= None
        while True:
            status = self.client.detail(self.resource_id)
            if status['netCardIds']:
                id = status['netCardIds'][0]
                LOG.debug(_("the first port id  is %s") %id)
                break
            else:
                if try_count == 4:
                    LOG.debug(_("get the  first port id timeout") )
                    break
                else:
                    try_count += 1
                    time.sleep(5)
        return id

    def _get_host_name(self):
        try_count = 0
        host_name= None
        while True:
            status = self.client.detail(self.resource_id)
            host_name = status.get("hostName", None)
            if host_name:
                LOG.debug(_("host name   is %s") %host_name)
                break
            else:
                if try_count == 4:
                    LOG.debug(_("get host name timeout") )
                    break
                else:
                    try_count += 1
                    time.sleep(5)
        return host_name


    # 通过这个函数获取资源运行状态
    def _resolve_attribute(self, name):
        if name == self.INSTANCE_ID:
            return  self.resource_id
        elif name == self.FIRST_IP:
            return self._get_first_ip()
        elif name == self.FIRST_PORT_ID:
            return self._get_first_port_id()
        elif name == self.HOST_NAME:
            return self._get_host_name()






# 注册资源 Server 为上面的类
def resource_mapping():
    return {
        'OS::G-Cloud::Server': Server,
    }
