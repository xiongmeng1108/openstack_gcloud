# -*- coding:utf-8 -*-
__author__ = 'xm'
import sqlalchemy as sa
from sqlalchemy import orm
#from dbgp.client import brk
from neutron.api.v2 import attributes
from neutron.db import db_base_plugin_v2
from neutron.db import model_base
from neutron.db import models_v2
from neutron.db import external_net_db
from neutron.openstack.common import log as logging
import string
import socket
import struct
from netaddr import *

from neutron.extensions import gcloud_qos

LOG = logging.getLogger(__name__)

class SubnetIpInfoMixin(object):
    """
    statistics ip of subnets.
    """
    def get_ipinfo(self, context, id, fields=None):
        subnet_id = id
        ip_used_num = context.session.query(models_v2.IPAllocation).filter_by(subnet_id=subnet_id)
        ip_used_num = ip_used_num.count()
        ip_total_num = 0
        records = context.session.query(models_v2.IPAllocationPool).filter_by(subnet_id=subnet_id).all()
        if records:
            for record in records:
                first_ip = record.first_ip
                last_ip = record.last_ip
                num1 = socket.ntohl(struct.unpack("I", socket.inet_aton(first_ip))[0])
                num2 = socket.ntohl(struct.unpack("I", socket.inet_aton(last_ip))[0])
                num = num2 - num1 + 1
                ip_total_num += num

            ip_free_num = ip_total_num - ip_used_num
            ipinfo = {"subnet_id": subnet_id, "ip_used_num": ip_used_num, "ip_free_num": ip_free_num, "ip_total_num": ip_total_num}
            return ipinfo
        else:
            LOG.error(_("no IPAllocationPool for subnet_id=%s exist!"), subnet_id)
            ipinfo= {"subnet_id": subnet_id, "ip_used_num": 0, "ip_free_num": 0, "ip_total_num": 0}
            return ipinfo


    def get_ipinfos(self, context, filters=None, fields=None,
                    sorts=None, limit=None, marker=None,
                    page_reverse=False, offset=None):
        #brk(host="10.10.12.21", port=49175)
        ipinfos=[]
        #从数据库externalnetwork表中获取所有的外网网络
        external_nets = context.session.query(external_net_db.ExternalNetwork).all()
        external_nets_ids = []
        for net in external_nets:
            external_nets_ids.append(net.network_id)
        #获取所有的子网
        query = context.session.query(models_v2.Subnet)
        query.order_by("id")
        subnets = query.all()
        if subnets:
            if filters and filters.get('router:external', None) and filters.get('router:external', None)[0] == u'false':
                    for subnet in subnets:
                        if subnet["network_id"] in external_nets_ids:
                            continue
                        else:
                            ip_used_num = context.session.query(models_v2.IPAllocation).filter_by(subnet_id=subnet["id"])
                            ip_used_num = ip_used_num.count()
                            ip_total_num = 0
                            records = context.session.query(models_v2.IPAllocationPool).filter_by(subnet_id=subnet["id"]).all()
                            if records:
                                for record in records:
                                    first_ip = record.first_ip
                                    last_ip = record.last_ip
                                    num1 = socket.ntohl(struct.unpack("I", socket.inet_aton(first_ip))[0])
                                    num2 = socket.ntohl(struct.unpack("I", socket.inet_aton(last_ip))[0])
                                    num = num2 - num1 + 1
                                    ip_total_num += num
                            else:
                                LOG.error(_("no IPAllocationPool for subnet_id=%s exist!"), subnet["id"])
                                continue
                            ip_free_num = ip_total_num - ip_used_num
                            ipinfo = {"subnet_id": subnet["id"], "ip_used_num": ip_used_num, "ip_free_num": ip_free_num, "ip_total_num": ip_total_num}
                            ipinfos.append(ipinfo)
            else:
                for subnet in subnets:
                    if subnet["network_id"] not in external_nets_ids:
                        continue
                    else:
                        ip_used_num = context.session.query(models_v2.IPAllocation).filter_by(subnet_id=subnet["id"])
                        ip_used_num = ip_used_num.count()
                        ip_total_num = 0
                        records = context.session.query(models_v2.IPAllocationPool).filter_by(subnet_id=subnet["id"]).all()
                        if records:
                            for record in records:
                                first_ip = record.first_ip
                                last_ip = record.last_ip
                                num1 = socket.ntohl(struct.unpack("I", socket.inet_aton(first_ip))[0])
                                num2 = socket.ntohl(struct.unpack("I", socket.inet_aton(last_ip))[0])
                                num = num2 - num1 + 1
                                ip_total_num += num
                        else:
                            LOG.error(_("no IPAllocationPool for subnet_id=%s exist!"), subnet["id"])
                            continue
                        ip_free_num = ip_total_num - ip_used_num
                        ipinfo = {"subnet_id": subnet["id"], "ip_used_num": ip_used_num, "ip_free_num": ip_free_num, "ip_total_num": ip_total_num}
                        ipinfos.append(ipinfo)
        else:
            LOG.error("no subnet exist!")
        return ipinfos

    ###add by xm at 2015.9.18 for bug5917 : 本来使用以上2个方法get_ipinfo_orig/get_ipinfos_orig，后来由于BUG需要，重新设计统计方法
    ###以上方法暂时保留，作参考
    #2015.12.21 腾正项目需求，统计分配池内的IP个数，故修改get_ipinfo_orig和get_ipinfos_orig为get_ipinfo/ipinfos，并使用
    """
    statistics ip of subnets.
    """
    def get_ipinfo_bak(self, context, id, fields=None):
        subnet_id = id
        ip_used_num = context.session.query(models_v2.IPAllocation).filter_by(subnet_id=subnet_id)
        ip_used_num = ip_used_num.count()
        subnet = context.session.query(models_v2.Subnet).filter_by(id=subnet_id).first()
        if subnet:
            ip=IPNetwork(subnet['cidr'])
            ip_total_num = ip.size - 1
            ip_free_num = ip_total_num - ip_used_num
            ipinfo = {"subnet_id": subnet_id, "ip_used_num": ip_used_num, "ip_free_num": ip_free_num, "ip_total_num": ip_total_num}
            return ipinfo
        else:
            LOG.error(_("no subnet with subnet_id=%s exist!"), subnet_id)
            ipinfo= {"subnet_id": subnet_id, "ip_used_num": 0, "ip_free_num": 0, "ip_total_num": 0}
            return ipinfo

    def get_ipinfos_bak(self, context, filters=None, fields=None,
                    sorts=None, limit=None, marker=None,
                    page_reverse=False, offset=None):
        #brk(host="10.10.12.21", port=49175)
        ipinfos=[]
        #从数据库externalnetwork表中获取所有的外网网络
        external_nets = context.session.query(external_net_db.ExternalNetwork).all()
        external_nets_ids = []
        for net in external_nets:
            external_nets_ids.append(net.network_id)
        #获取所有的子网
        query = context.session.query(models_v2.Subnet)
        query.order_by("id")
        subnets = query.all()
        if subnets:
            if filters and filters.get('router:external', None) and filters.get('router:external', None)[0] == u'false':
                    for subnet in subnets:
                        if subnet["network_id"] in external_nets_ids:
                            continue
                        else:
                            ip_used_num = context.session.query(models_v2.IPAllocation).filter_by(subnet_id=subnet["id"])
                            ip_used_num = ip_used_num.count()
                            ip=IPNetwork(subnet['cidr'])
                            ip_total_num = ip.size - 1
                            ip_free_num = ip_total_num - ip_used_num
                            ipinfo = {"subnet_id": subnet["id"], "ip_used_num": ip_used_num, "ip_free_num": ip_free_num, "ip_total_num": ip_total_num}
                            ipinfos.append(ipinfo)
            else:
                for subnet in subnets:
                    if subnet["network_id"] not in external_nets_ids:
                        continue
                    else:
                        ip_used_num = context.session.query(models_v2.IPAllocation).filter_by(subnet_id=subnet["id"])
                        ip_used_num = ip_used_num.count()
                        ip=IPNetwork(subnet['cidr'])
                        ip_total_num = ip.size -1
                        ip_free_num = ip_total_num - ip_used_num
                        ipinfo = {"subnet_id": subnet["id"], "ip_used_num": ip_used_num, "ip_free_num": ip_free_num, "ip_total_num": ip_total_num}
                        ipinfos.append(ipinfo)
        else:
            LOG.error("no subnet exist!")
        return ipinfos