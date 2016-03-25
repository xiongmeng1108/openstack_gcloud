from neutron.openstack.common import log

from neutron.db.gcloud_router_qos_db import GcloudRouterQosmixin
from  neutron.extensions import gcloud_router_qos
from neutron.common import constants as com_const

from neutron import manager
from neutron.plugins.common import constants as service_constants
from neutron.plugins.common import constants as plugin_constants

LOG = log.getLogger(__name__)

#class RouterQosPluginV2(GcloudRouterQosPluginBase,GcloudRouterQosmixin,GcloudRouterQosRulemixin,GcloudRouterQosRuleBindmixin):
class RouterQosPluginV2(GcloudRouterQosmixin):
    """
    implement interface
    """
    supported_extension_aliases = ["gcloud_router_qos"]



    @property
    def plugin(self):
        if not hasattr(self, '_plugin'):
            self._plugin = manager.NeutronManager.get_plugin()
        return self._plugin

    @property
    def l3plugin(self):
        if not hasattr(self, '_l3plugin'):
            self._l3plugin = manager.NeutronManager.get_service_plugins()[
                plugin_constants.L3_ROUTER_NAT]
        return self._l3plugin

    def _update_router_qos_dict(self, router_qos_value ,ip_num=0 ):
        """
        router qos contain ip number
        :param router_qos_value:
        :param ip_num:
        :return:
        """
        if router_qos_value:
            router_qos_value.update({"ip_num":ip_num})

        LOG.debug("_make_router_qos_dict %r"%(router_qos_value))
        return router_qos_value

    def __init__(self):
        super(RouterQosPluginV2, self).__init__()
    def _compare_band_type(self,context,qos_id,port_id,type):
        """
        compare qos type and port type,eg qos type  DIANXIN,and floating type DIANXIN
        if not the samc, will raise exception
        :param context:
        :param qos_id:
        :param port_id:
        :param type:operate type
        :return:
        """
        #get qos type
        router_qos=self.get_router_qos(context,id=qos_id)
        #according ip_type and port_id to get ip_src
        if com_const.BGP==router_qos["type"]:#not limit operate type
            return
        LOG.debug("router_qos type %s, ip type %s" %(router_qos["type"],type))
        if type and type!=router_qos["type"]:
            raise gcloud_router_qos.RouterQosTypeNotSame(port_id=port_id,qos_id=qos_id)

    def _get_floatingips_info(self,context,port_ids):
        """
        acording floating ip port ids to  get floating ip infos
        :param context:
        :param port_ids:["port_id",]
        :return dict
        """
       # ip_infos= self._l3plugin = manager.NeutronManager.get_service_plugins()[
        #        plugin_constants.L3_ROUTER_NAT].get_floatingips_for_qos(context,filters={"floating_port_id":port_ids})
       # ip_infos=self._get_l3plugin().get_floatingips(context,filters={"floating_port_id":port_ids})
        ip_infos= manager.NeutronManager.get_service_plugins()[ plugin_constants.L3_ROUTER_NAT].get_floatingips(context,filters={"floating_port_id":port_ids})
        for ip_info in ip_infos:
            #LOG.debug("ipinfo:%r" %(ip_info))
            ip_info.update({"src_ip":ip_info["floating_ip_address"]})
        return ip_infos
    def _get_gatewayips_info(self,context,port_ids):
        #wait,contain router_id ,and gateway id,ip address
        ip_infos=manager.NeutronManager.get_plugin().get_infos_of_gateways(context,ports=port_ids)
        if ip_infos:
            for ip_info in ip_infos:
                ip_info.update({"src_ip":ip_info["ip_address"]})
        return ip_infos

    def _get_gateway_type(self,context,subnet_id):
        """
        get gateway subnet type
        :param context:
        :param subnet_id:
        :return:
        """
        subnet=manager.NeutronManager.get_plugin().get_subnet(context,id=subnet_id)
        return subnet["type"]

    def _get_router_id(self,context,port_id,ip_type):
        ip_infos=None
        if ip_type==com_const.FLOATINGIP:
            ip_infos=self._get_floatingips_info(context,port_ids=[port_id])
        elif ip_type==com_const.GATEWAY:
            ip_infos=self._get_gatewayips_info(context,port_ids=[port_id])
        if ip_infos:
            return ip_infos[0]["router_id"]
        else:
            return None

    def _get_ip_info(self,context,port_id,ip_type):
        """
        :param context:
        :param port_id:
        :param ip_type: floatingip or gateway
        :return dict
        """
        ip_info=None
        if ip_type==com_const.FLOATINGIP:
            ip_infos=self._get_floatingips_info(context,port_ids=[port_id])
            if ip_infos:
                ip_info=ip_infos[0]
        elif ip_type==com_const.GATEWAY:
            ip_infos=self._get_gatewayips_info(context,port_ids=[port_id])
            if ip_infos:
                ip_info=ip_infos[0]
                if ip_info:
                    #according subnet id to get type
                    type=self._get_gateway_type(context,subnet_id=ip_info["subnet_id"])
                    ip_info["type"]=type
        if ip_info is None:
            raise gcloud_router_qos.RouterIpInfoNotInFound(port_id=port_id)
        return ip_info

    def _get_router_ids(self,context,qos_rule_binds):
        """

        :param context:
        :param qos_rule_binds: qos_rule_bind
        :return: list,contain router_id,default []
        """

        floatingIp_ports=[]
        gateway_port_ids=[]
        for qos_rule_bind in qos_rule_binds:
            if qos_rule_bind["ip_type"]==com_const.FLOATINGIP:
                floatingIp_ports.append(qos_rule_bind["port_id"])
            else:
                gateway_port_ids.append(qos_rule_bind["port_id"])
        router_ids=set([])
        if len(floatingIp_ports)>0:
           floatingip_infos=self._get_floatingips_info(context,port_ids=floatingIp_ports)
           if floatingip_infos and len(floatingip_infos)>0:
             for floatingip_info in floatingip_infos:
                   router_ids.add(floatingip_info["router_id"])
        if len(gateway_port_ids)>0:
           gatewayip_infos=self._get_gatewayips_info(context,port_ids=gateway_port_ids)
           if gatewayip_infos and len(gatewayip_infos)>0:
             for gatewayip_info in gatewayip_infos:
                 router_ids.add(gatewayip_info["router_id"])
        return list(router_ids)

    def _notify_router_update_qos(self,context,router_id):
             #self.l3plugin().notify_router_updated(context,router_id,"update_router_qos",{})
            LOG.debug("_notify_router_update_qos router_id %s" %(router_id))

            manager.NeutronManager.get_service_plugins()[plugin_constants.L3_ROUTER_NAT].\
                notify_router_updated(context,router_id,"update_router_qos",{})

    def create_router_qosrule_bind(self, context, router_qosrule_bind):
        """
        accosiate ip to qos rule
        :param context:
        :param router_qosrule_bind:
        :return:
        """
        LOG.debug(_("create_router_qosrule_bind() called"))
        LOG.debug(_("input %r called" %(router_qosrule_bind)))
        session = context.session
        router_qosrule_bind_value=router_qosrule_bind["router_qosrule_bind"]
        with session.begin(subtransactions=True):
            port_id=router_qosrule_bind_value["port_id"]
            #check  port_id is in qos rule,if it is exist,rasie execption
            count=self.get_router_qosrule_binds_count(context=context,filters={"port_id":[port_id]})
            if count and count>0:
                raise gcloud_router_qos.RouterQosPortIdInUse(port_id=port_id)
            qos_rule=super(RouterQosPluginV2, self).get_router_qosrule(context,id=router_qosrule_bind_value["rule_id"])
            router_qosrule_bind_value["qos_id"]=qos_rule["qos_id"]
            #get port_id ipInfo
            ip_info=self._get_ip_info(context,port_id,router_qosrule_bind_value["ip_type"])
            #compare type, compare ip type and qos_type
            self._compare_band_type(context,qos_rule["qos_id"],port_id,ip_info["type"])
            #save qos rule
            router_qosrule_bind_value.update({"src_ip":ip_info["src_ip"]})

            router_qosrule_bind_value=super(RouterQosPluginV2, self).create_router_qosrule_bind(context=context, router_qosrule_bind=router_qosrule_bind)
            #check  ip is in  router? if it is in router, update l3 agent
            if ip_info["router_id"]:
                self._notify_router_update_qos(context,router_id=ip_info["router_id"])
            LOG.debug("router qosrule %r"%(router_qosrule_bind_value))
        return router_qosrule_bind_value


    def create_router_qos(self, context, router_qos):
        """
        create router_qos and create default router qos rule
        :param context:
        :param router_qos:
        :return:
        """
        LOG.debug(_("create_router_qos() called"))
        session = context.session
        with session.begin(subtransactions=True):
            result=super(RouterQosPluginV2, self).create_router_qos(context, router_qos)#db create
            router_qos_rule_value= {"max_rate":result["max_rate"],"qos_id":result["id"],"name":result["name"]}
            router_qos_rule={"router_qosrule":router_qos_rule_value}
            super(RouterQosPluginV2, self).create_router_qosrule(context, router_qos_rule)

            return self._update_router_qos_dict(result)


    def get_router_qoss(self, context, filters=None, fields=None, sorts=None, limit=None, marker=None,
                        page_reverse=False,offset=None):
        LOG.debug(_("get_router_qoss() called"))
        router_qos_values=super(RouterQosPluginV2, self).get_router_qoss(context, filters, fields, sorts, limit, marker, page_reverse,offset)
        if router_qos_values:
            for router_qos_value in  router_qos_values:
                ip_num=super(RouterQosPluginV2, self).get_router_qosrule_binds_count(context,filters={"qos_id":[router_qos_value["id"]]})
                router_qos_value=self._update_router_qos_dict( router_qos_value=router_qos_value ,ip_num=ip_num )
        return  router_qos_values

    def delete_router_qosrule_bind(self, context, id,fields=None):
        LOG.debug(_("delete_router_qosrule_bind() called"))
        session = context.session
        with session.begin(subtransactions=True):
                qosrule_bind_value=super(RouterQosPluginV2, self).get_router_qosrule_bind(context=context,id=id)
                #get rule router_id
                router_id=self._get_router_id(context,port_id=qosrule_bind_value["port_id"],ip_type=qosrule_bind_value["ip_type"])
                #delete bind
                super(RouterQosPluginV2, self).delete_router_qosrule_bind(context, id)
                #notify l3 agent
                if router_id:
                    self._notify_router_update_qos(context,router_id)


    def delete_router_qos(self, context , id):
        LOG.debug(_("delete_router_qos() called"))
        LOG.debug(_("input id %s" %(id)))
        session = context.session
        router_ids=None
        with session.begin(subtransactions=True):
            #get ip number
            #ip_num=super(RouterQosPluginV2, self).get_router_qosrule_binds_count(context,filters={"qos_id":[id]})
            qosrule_binds=super(RouterQosPluginV2, self).get_router_qosrule_binds(context,filters={"qos_id":[id]})
            if qosrule_binds and len(qosrule_binds)>0:
                 #get router_ids ,wait
                 router_ids=self._get_router_ids(context,qos_rule_binds=qosrule_binds)
            router_qos=super(RouterQosPluginV2, self).delete_router_qos(context=context, id=id)
        # notify router_ids
        if router_ids and len(router_ids)>0:
            for router_id in router_ids:
                self._notify_router_update_qos(context,router_id)



    def update_router_qos(self, context, id, router_qos):
        LOG.debug("update_router_qos() in call")
        router_qos_value=router_qos["router_qos"]
        session = context.session
        change=False #db change
        update_band=False #update router band limit

        with session.begin(subtransactions=True):

            result=super(RouterQosPluginV2, self).get_router_qos(context,id)
            if  result["name"]!=router_qos_value.get("name",None):
                result["name"]=router_qos_value.get("name",None)
                change=True
            if result["max_rate"]!=router_qos_value["max_rate"]:
                result["max_rate"]=router_qos_value["max_rate"]
                change=update_band=True
            if change:#db change
                #update router qos
                update_router_qos={"router_qos":result}
                result=super(RouterQosPluginV2, self).update_router_qos(context,id,update_router_qos)
                if update_band:#band change
                    #update default qos rule
                    update_router_qosrule_values = self.get_router_qosrules(context,filters={"qos_id":[id]})
                    if  update_router_qosrule_values:
                        update_router_qosrule_value=update_router_qosrule_values[0]
                        update_router_qosrule_value["max_rate"]=result["max_rate"]
                        update_router_qosrule ={"router_qosrule": update_router_qosrule_value}
                        super(RouterQosPluginV2, self).update_router_qosrule(context,update_router_qosrule_value["id"],router_qosrule=update_router_qosrule)

        #get ip number
        ipNum = self.get_router_qosrule_binds_count(context,filters={"qos_id":[id]})

        # is notify l3 agents,wait
        if update_band:
             if ipNum>0:
                 qosrule_binds=super(RouterQosPluginV2, self).get_router_qosrule_binds(context,filters={"qos_id":[id]})
                 if qosrule_binds and len(qosrule_binds)>0:
                  #get router_ids ,wait
                      router_ids=self._get_router_ids(context,qos_rule_binds=qosrule_binds)
                      if router_ids and len(router_ids)>0:
                           for router_id in router_ids:
                               self._notify_router_update_qos(context,router_id)
        return self._update_router_qos_dict( result ,ipNum )


    def get_router_qos(self, context, id, fields=None):
        LOG.debug("get_router_qos() in call")
        router_qos_value=super(RouterQosPluginV2, self).get_router_qos(context=context, id=id, fields=fields)
        ip_number=self.get_router_qosrule_binds_count(context, filters={'qos_id':[id]})
        return  self._update_router_qos_dict(router_qos_value,ip_number)

    def get_sync_router_all_qos(self,context, routers):
        """
        get_sync_router_all_qos :according ip infos to find qos rule bind info ,and update routers qos
        :param context:
        :param routers:
        :return:routers
        """
        LOG.debug("get_sync_router_all_qos() in call")
        for router in routers:
            src_ips=[]
            floatingip_infos=router.get(com_const.FLOATINGIP_KEY,[])
            for floatingip_info in  floatingip_infos:
                src_ips.append(floatingip_info["floating_ip_address"])
            gateway_info=router.get("external_gateway_info", None)
            if  gateway_info:
                external_fixed_ips=gateway_info.get("external_fixed_ips")
                if external_fixed_ips and len(external_fixed_ips)>0:
                     src_ips.append(external_fixed_ips[0].get("ip_address"))
            #LOG.debug("src_ips %r" %(src_ips))
            if len(src_ips) > 0:
                with context.session.begin(subtransactions=True):
                  router_qosrule_binds=super(RouterQosPluginV2, self).get_router_qosrule_binds(context,filters={"src_ip":src_ips})
                  if router_qosrule_binds:
                       rule_ids=set([])
                       #get rule ids for query router_qosrules
                       for router_qosrule_bind in router_qosrule_binds:#get src_ip rule_id
                             rule_ids.add(router_qosrule_bind["rule_id"])
                       #get router qos rules  according to rule ids
                       router_qosrules=super(RouterQosPluginV2, self).get_router_qosrules(context,filters={"id":list(rule_ids)})
                       rule_id_max_rate_dicts={}
                       #build map
                       for  router_qosrule in router_qosrules:
                           #rule_id_max_rate_dicts.update({router_qosrule["id"]:router_qosrule["max_rate"]})
                           rule_id_max_rate_dicts.update({router_qosrule["id"]:{"rule_id":router_qosrule["id"],"max_rate":router_qosrule["max_rate"]}})
                       router_qoss=self._make_get_sync_router_qoss_dict(router_qosrule_binds,rule_id_max_rate_dicts)
                       #LOG.debug("router_qoss %r" %(router_qoss))
                       router.update({com_const.FLOATING_IP_QOS_KEY:router_qoss})
        return routers

    def _make_get_sync_router_qoss_dict(self, router_qosrule_binds, rule_id_max_rate_dicts):
        """

        :param router_qosrule_binds:
        :param rule_id_max_rate_dicts:
        :return: {"rule_id5":{"max_rate":2048,"src_ips":["11.168.10.1","11.168.20.1","11.0.0.1"]},****}
        """

        for router_qosrule_bind in router_qosrule_binds:
            rule_id=router_qosrule_bind["rule_id"]
            rule_id_max_rate_value=rule_id_max_rate_dicts[rule_id]
            src_ips=rule_id_max_rate_value.get("src_ips",None)
            if not src_ips:
                rule_id_max_rate_value.update({"src_ips":[router_qosrule_bind["src_ip"]]})
            else:
                src_ips.append(router_qosrule_bind["src_ip"])

            #res.append( dict((key, router_qosrule_bind[key]) for key in ["src_ip","max_rate"]))
        LOG.debug("router_qoss %r" %(rule_id_max_rate_dicts))
        return rule_id_max_rate_dicts

    def  get_floating_router_qos(self,context,floating_ip):
        """
        get floating ip router qos rule info
        :param context:
        :param floating_ip:
        :return:floating_ip
        """
        LOG.debug("get_floating_router_qos() in call,%r" %(floating_ip))
        #get floatingip accosicate qos rule
        router_qosrule_binds=super(RouterQosPluginV2, self).get_router_qosrule_binds(context,filters={"src_ip":[floating_ip["floating_ip_address"]]})
        if router_qosrule_binds and  len(router_qosrule_binds)>0:
             #get router_qosrule
                router_qosrule=super(RouterQosPluginV2, self).get_router_qosrule(context,id=router_qosrule_binds[0].get("rule_id"))
                floating_ip.update({"router_qosrule":router_qosrule})
        return floating_ip

    def  get_floating_router_qoss(self,context,floating_ips):
        """
        get router qos rules of floating ips
        :param self:
        :param context:
        :param floating_ips:
        :return: floating_ips
        """
        #get floatingip accosicate qos rule
        if floating_ips and len(floating_ips)>0:
              src_ips=[floating_ip["floating_ip_address"] for floating_ip in floating_ips]
              #get ip  amd  rule_id binds
              router_qosrule_binds=super(RouterQosPluginV2, self).get_router_qosrule_binds(context,filters={"src_ip":src_ips})
              if router_qosrule_binds and len(router_qosrule_binds)>0:
                  src_ip_and_rule_id_dicts={}
                  rule_ids=set([])
                  #storage ip src and rule_id map
                  for router_qosrule_bind in router_qosrule_binds:
                     src_ip_and_rule_id_dicts.update({router_qosrule_bind["src_ip"]:router_qosrule_bind["rule_id"]})
                     rule_ids.add(router_qosrule_bind["rule_id"])
                  # get router_qosrules according to rule_id
                  router_qosrules=super(RouterQosPluginV2, self).get_router_qosrules(context,filters={"id":list(rule_ids)})
                  #storage rule_id qos_rule map
                  router_qos_rule_map={}
                  for router_qosrule in  router_qosrules:
                      router_qos_rule_map.update({router_qosrule["id"]:router_qosrule})
                  # update floating_ip info according to map infos
                  for floating_ip in floating_ips:
                      rule_id=src_ip_and_rule_id_dicts.get(floating_ip["floating_ip_address"],None)
                      if rule_id:
                          router_qosrule=router_qos_rule_map.get(rule_id,{})
                          floating_ip.update({"router_qosrule":router_qosrule})
        return  floating_ips








