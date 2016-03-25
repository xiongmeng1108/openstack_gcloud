# -*- coding:utf-8 -*-
__author__ = 'xm'
import sqlalchemy as sa
from neutron.db import model_base
from neutron.db import models_v2
from neutron.db import external_net_db
from neutron.openstack.common import log as logging
from netaddr import *
from sqlalchemy.orm import exc
from neutron.extensions import gcloud_nat as gcloud_nat_import
from neutron.db import common_db_mixin as base_db
from neutron import manager
from neutron.db import l3_db
from neutron.plugins.common import constants as service_constants

#import pdb

LOG = logging.getLogger(__name__)


class GcloudNat(model_base.BASEV2, models_v2.HasId, models_v2.HasCreateTime, models_v2.HasTenant):
    """Represents a router gateway port nat.

    This class is desgin for tengzheng project at 2015.12.7.
    """
    router_id = sa.Column(sa.String(36), sa.ForeignKey('routers.id'), nullable=False)
    port_id = sa.Column(sa.String(36), sa.ForeignKey('ports.id'), nullable=False)
    gw_port_id = sa.Column(sa.String(36), sa.ForeignKey('ports.id'), nullable=False)
    ext_ip = sa.Column(sa.String(64))
    int_ip = sa.Column(sa.String(64))
    ext_port = sa.Column(sa.Integer())
    int_port = sa.Column(sa.Integer())
    user_id = sa.Column(sa.String(64))
    vif_subnet_cidr = sa.Column(sa.String(64))
    vif_subnet_gateway = sa.Column(sa.String(64))

class GcloudNatPlus(model_base.BASEV2):
    """Used by gcloud_nat.

    Store gateway info of a router which has gcloud_nats.
    """
    router_id = sa.Column(sa.String(36), sa.ForeignKey('routers.id'), nullable=False, primary_key=True)
    network_id = sa.Column(sa.String(36))
    subnet_id = sa.Column(sa.String(36))
    ip_address = sa.Column(sa.String(64))

class GcloudNatMixin(base_db.CommonDbMixin):
    """Operator of gcloud nat.

    For router gateway nat add/delete/update/get
    """
    def get_gcloud_nat(self, context, id, fields=None):
        #LOG.debug(_("111111 get_gcloud_nat %s"), id)
        gcloud_nat_db = self._get_gcloud_nat(context, id)
        nat = self._make_gcloud_nat_dict(gcloud_nat_db)
        #nat = {"ext_ip":"11.11.11.11", "ext_port":2222, "int_ip":"192.0.0.10", "int_port": 22}
        #LOG.debug(_("111111 get_gcloud_nat nat %s"), nat)
        return nat

    def get_gcloud_nats(self, context, filters=None, fields=None,
                    sorts=None, limit=None, marker=None,
                    page_reverse=False, offset=None):
        #LOG.debug(_("111111 gets %s"))
        # nats=[]
        # nat = {"ext_ip":"11.11.11.11", "ext_port":2222, "int_ip":"192.0.0.10", "int_port": 22}
        # nats.append(nat)
        # nats.append(nat)
        # return nats
        LOG.debug(_("get_gcloud_nats FILTERS=%s"), filters)
        return self._get_collection(context, GcloudNat,
                                    self._make_gcloud_nat_dict,
                                    filters=filters, fields=fields,
                                    sorts=sorts,
                                    limit=limit,
                                    page_reverse=page_reverse)

    def create_gcloud_nat(self, context, gcloud_nat):
        nat = gcloud_nat['gcloud_nat']
        #FILTERS={u'router_id': [u'111'], u'port_id': [u'222']}
        filters1 = {"ext_port": [nat["ext_port"]], "router_id": [nat["router_id"]]}
        filters2 = {"int_port": [nat["int_port"]],  "port_id": [nat["port_id"]]}
        counter1 = self.get_gcloud_nats_count(context, filters1)
        if counter1 >= 1:
            raise gcloud_nat_import.InvalidateGcloudNatRule1(router_id=nat["router_id"], ext_port=nat["ext_port"])
        counter2 = self.get_gcloud_nats_count(context, filters2)
        if counter2 >= 1:
            raise gcloud_nat_import.InvalidateGcloudNatRule2(port_id=nat["port_id"], int_port=nat["int_port"])

        tenant_id = self._get_tenant_id_for_create(context, nat)
        l3plugin = manager.NeutronManager.get_service_plugins().get(service_constants.L3_ROUTER_NAT)
        core_plugin = manager.NeutronManager.get_plugin()
        if not l3plugin:
            LOG.error("NO l3plugin service! please config and start l3 router service_plugin!")
        router = l3plugin.get_router_by_router_id_tz(context, nat["router_id"])
        #LOG.debug(_("111111 create 3 find vm_port router=%s"),router.__dict__)
        vm_port, vm_subnet = core_plugin.tz_get_port(context, nat["port_id"])
        #LOG.debug(_("111111 create 3 find vm_port end vm_subnet=%s"),vm_subnet)
        if not self.check_router_has_router_interface_by_port(context, vm_port, nat["router_id"]):
            LOG.debug("router %s not have subnet %s router interface" %(nat["router_id"], vm_port.fixed_ips[0]["subnet_id"]))
            raise gcloud_nat_import.SubnetNotHAveRouterInterface(port_id=nat["port_id"])
        int_ip = vm_port.fixed_ips[0]["ip_address"]
        vif_subnet_cidr = vm_subnet.get("cidr", None)
        vif_subnet_gateway = vm_subnet.get("gateway_ip", None)
        LOG.debug(_("create_gcloud_nat vif_subnet_cidr=%s vif_subnet_gateway=%s"),vif_subnet_cidr,vif_subnet_gateway)
        try:
            gw_port = router.gw_port
            gw_port_id = gw_port["id"]
        except Exception:
            raise gcloud_nat_import.GatewayNotSet(router_id=nat["router_id"])
        with context.session.begin(subtransactions=True):
            #add a record in ipallocations table
            gcloud_nat_plus = self.get_gcloud_nat_plus_by_router_id(context, nat["router_id"])
            #LOG.debug(_("111111 create 2222 gcloud_nat_plus=%s"), gcloud_nat_plus)
            #pdb.set_trace()
            if not gcloud_nat_plus:
                if gw_port.fixed_ips and len(gw_port.fixed_ips) >= 1:
                    ips = gw_port.fixed_ips
                    LOG.debug(_("create_gcloud_nat ips=%s"), ips)
                else:
                    LOG.debug("tz_allocate_ips_for_gateway_port call")
                    ips = core_plugin.tz_allocate_ips_for_gateway_port(context, gw_port)
                #LOG.debug(_("111111 create 4444 ips=%s"),ips)
                #ips =[{'ip_address':"10.10.10.2",'subnet_id': "xxxxxxxx-xxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx","network_id":"xxxx"}]
                nat_plus_db = GcloudNatPlus(
                    router_id=nat["router_id"],
                    network_id=ips[0]["network_id"],
                    subnet_id=ips[0]["subnet_id"],
                    ip_address=ips[0]["ip_address"]
                )
                context.session.add(nat_plus_db)
                #update routerports tables: add subnet_id
                l3plugin.update_routerports_table(context, router_id=nat["router_id"], port_id=gw_port['id'], subnet_id=ips[0]['subnet_id'])
                #add a record in gcloudnats table
                #LOG.debug(_("111111 create 5555 ips=%s"),ips)
                ext_ip = ips[0]['ip_address']
            else:
                ext_ip = gcloud_nat_plus["ip_address"]
                #LOG.debug(_("111111 create 5555 ext_ip=%s"), ext_ip)

            gcloud_nat_db = GcloudNat(
                tenant_id=tenant_id,
                router_id=nat["router_id"],
                port_id=nat["port_id"],
                gw_port_id=gw_port_id,
                ext_ip=ext_ip,
                ext_port=nat["ext_port"],
                int_ip=int_ip,
                int_port=nat["int_port"],
                vif_subnet_cidr=vif_subnet_cidr,
                vif_subnet_gateway=vif_subnet_gateway,
                user_id=context.user)
            context.session.add(gcloud_nat_db)
        response = self._make_gcloud_nat_dict(gcloud_nat_db)
        router_id = nat['router_id']
        l3plugin.notify_router_updated(context, router_id, 'create_gcloud_nat', {})
        return response

    def delete_gcloud_nat(self, context, id):
        with context.session.begin(subtransactions=True):
            gcloud_nat_db = self._get_gcloud_nat(context, id)
            counter=self._get_collection_count(context, GcloudNat, filters={"router_id": [gcloud_nat_db["router_id"]]})
            #LOG.debug(_("111111 delete %s counter=%d"), id, counter)
            context.session.delete(gcloud_nat_db)
            #delete for bug 7358: do not delete gateway_ip before out of date( called api of delete of all gcloud_nats)
            #路由的网关IP不随最后一个gcloud_nat映射而删除，因为存在用户购买过期时间，只有过期了才通过调用routers/remove_router_gatewayip
            # 接口删除
            # if counter == 1:
            #     gcloud_nat_plus = self.get_gcloud_nat_plus_by_router_id(context, gcloud_nat_db["router_id"])
            #     if gcloud_nat_plus:
            #         LOG.debug(_("111111 delete gcloud_nat_plus=%s"), gcloud_nat_plus)
            #         context.session.delete(gcloud_nat_plus)
            #         LOG.debug(_("111111 delete DDDD gcloud_nat_plus=%s"), gcloud_nat_plus)
            #         #此处添加port_id
            #         self._get_l3_plugin().tz_delete_gateway_ip(context, gcloud_nat_db, gcloud_nat_plus)
            #         LOG.debug(_("111111 delete FFFF"))
        #LOG.debug(_("111111 delete DFDFD"))
        self._get_l3_plugin().notify_routers_updated(context, [gcloud_nat_db["router_id"]])

    def update_gcloud_nat(self, context, id, gcloud_nat):
        LOG.debug(_("update_gcloud_nat update id=%s gcloud_nat=%s"), id, gcloud_nat)
        nat = gcloud_nat['gcloud_nat']
        with context.session.begin(subtransactions=True):
            gcloud_nat_db = self._get_gcloud_nat(context, id)
            if nat:
                gcloud_nat_db.update(nat)
            #LOG.debug(_("111111 update gcloud_nat_db=%s"),gcloud_nat_db["router_id"])
        #LOG.debug(_("111111 update gcloud_nat_db=%s"),gcloud_nat_db["router_id"])
        self._get_l3_plugin().notify_routers_updated(context, [gcloud_nat_db["router_id"]])
        return self._make_gcloud_nat_dict(gcloud_nat_db)

    def _make_gcloud_nat_dict(self, gcloud_nat_db, fields=None):
        resp={"id": gcloud_nat_db["id"], "router_id": gcloud_nat_db["router_id"], "port_id": gcloud_nat_db["port_id"],
              "gw_port_id": gcloud_nat_db["gw_port_id"],
              "ext_ip": gcloud_nat_db["ext_ip"], "ext_port": gcloud_nat_db["ext_port"],
              "int_ip": gcloud_nat_db["int_ip"], "int_port": gcloud_nat_db["int_port"],
              "user_id": gcloud_nat_db["user_id"], "create_time": gcloud_nat_db["create_time"]}
        return resp

    def _get_gcloud_nat(self, context, nat_id):
        try:
            nat = self._get_by_id(context, GcloudNat, nat_id)
        except exc.NoResultFound:
            raise gcloud_nat.NatNotFound(nat_id=nat_id)
        return nat

    def get_gcloud_nats_tz(self, context, router_ids=None):
        """According router_ids to get gcloud_nats
        """
        #LOG.debug("111111 in get_gcloud_nats %r"%(router_ids))
        if not router_ids:
            return []
        #gcloud_nats=[]
        gcloud_nats = self._get_collection(context, GcloudNat,
                                    self._make_gcloud_nat_dict_2,
                                    filters={'router_id': router_ids}
                                    )
        #LOG.debug("111111 in get_gcloud_nats 7777 %r"%(gcloud_nats))
        return gcloud_nats

    def _make_gcloud_nat_dict_2(self, gcloud_nat, fields=None):
        res={}
        if gcloud_nat:
           res = {
               'router_id': gcloud_nat['router_id'],
               'port_id': gcloud_nat['port_id'],
               'ext_ip': gcloud_nat['ext_ip'],
               'ext_port': gcloud_nat['ext_port'],
               'int_ip': gcloud_nat['int_ip'],
               'int_port': gcloud_nat['int_port'],
               "vif_subnet_cidr": gcloud_nat['vif_subnet_cidr'],
               "vif_subnet_gateway": gcloud_nat['vif_subnet_gateway']
              }
        return self._fields(res, fields)

    def _get_l3_plugin(self):
        l3plugin = manager.NeutronManager.get_service_plugins().get(service_constants.L3_ROUTER_NAT)
        return l3plugin

    def get_gcloud_nat_plus_by_router_id(self,context, router_id):
        query = context.session.query(GcloudNatPlus)
        return query.filter(
            GcloudNatPlus.router_id == router_id
        ).first()

    def del_gcloud_nat_plus_by_router_id(context, router_id):
        nat_plus_db = query = context.session.query(GcloudNatPlus).filter(
            GcloudNatPlus.router_id == router_id
        )
        context.session.delete(nat_plus_db)


    def get_gcloud_nats_count(self, context, filters=None):

        return self._get_collection_count(context, GcloudNat,
                                          filters=filters)

    def delete_gcloud_nats(self,context,router_id):
        """
        delete gcloud nat and remove gw info,called by router remove gateway ip
        """
        with context.session.begin(subtransactions=True):
           context.session.query(GcloudNat).filter(GcloudNat.router_id==router_id ).delete()
           #context.session.delete(gcloud_nat_db)
           nat_ipallocaiton=context.session.query(GcloudNatPlus).filter(GcloudNatPlus.router_id == router_id ).first()
           if nat_ipallocaiton:
              context.session.delete(nat_ipallocaiton)
              gcloud_nat_db={}
              gcloud_nat_db["router_id"]=router_id
              self._get_l3_plugin().tz_delete_gateway_ip(context, gcloud_nat_db, ipallocation=nat_ipallocaiton)



    def check_router_has_router_interface_by_port(self, context, port,router_id):
        rport_qry = context.session.query(l3_db.RouterPort)
        ports = rport_qry.filter(
                l3_db.RouterPort.router_id == router_id,
                l3_db.RouterPort.port_type == "network:router_interface",
                l3_db.RouterPort.subnet_id == port.fixed_ips[0]["subnet_id"]
            )
        if ports.first():
            return True
        else:
            return False
