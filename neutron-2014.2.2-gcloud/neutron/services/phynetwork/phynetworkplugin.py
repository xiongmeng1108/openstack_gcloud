# -*- coding:utf-8 -*-
__author__ = 'luoyb'
from neutron.extensions import phynetwork as phynetwork_ext
from neutron.openstack.common import log
from neutron.common.config import  cfg
from neutron.plugins.ml2 import config

LOG = log.getLogger(__name__)

class PhyNetworkPlugin(phynetwork_ext.PhyNetworkPluginBase):
    supported_extension_aliases = ["phynetwork"]

    def __init__(self):
        super(PhyNetworkPlugin, self).__init__()

    # def get_phynetworks(self, context, filters=None, fields=None):
    #      return [{"phydev":"eth0"}]

    def get_phynetworks(self, context, filters=None, fields=None):
        phynets = []
        try:
            net_type = filters['networkType'][0]
        except Exception:
            LOG.debug("no net_type spec! net_type=None")
            net_type = None
        if net_type is None:
            try:
                fp = open('/etc/neutron/plugins/ml2/ml2_conf.ini', 'r')
            except IOError:
                LOG.ERROR("cat not open file '/etc/neutron/plugins/ml2/ml2_conf.ini',exist??")
            else:
                for line in fp:
                    if line[:15] == "bridge_mappings":
                        index = line.find("=")
                        if index == -1:
                            LOG.debug(_("'bridge_mappings' no value in line:%s "), line)
                            continue
                        else:
                            index += 1
                            line = line[index:].strip()
                            nums = line.count(",")
                            while nums >= 0:
                                nums -= 1
                                index = line.find(",")
                                if index == -1:
                                    #the last key(phynetwork)
                                    si = line.index(":")
                                    key = line[:si].strip()
                                    phynets.append(key)
                                else:
                                    #not the last
                                    sl = line[:index].strip()
                                    si = line.find(":")
                                    if si == -1:
                                        LOG.ERROR(_(
                                            "line:%s  must like 'bridge_mappings = physnet2:br-ex,physnet3:br-ex'"),
                                                  line)
                                        break
                                    else:
                                        key = sl[:si].strip()
                                        phynets.append(key)
                                        line = line[index + 1:]
                fp.close()

        elif net_type == "flat":
            try:
                fp = open('/etc/neutron/plugins/ml2/ml2_conf.ini', 'r')
            except IOError:
                LOG.ERROR("cat not open file '/etc/neutron/plugins/ml2/ml2_conf.ini',exist??")
            else:
                for line in fp:
                    if line[:13] == "flat_networks":
                        index = line.find("=")
                        if index == -1:
                            LOG.debug(_("'flat_networks' no value in line:%s "), line)
                            continue
                        else:
                            index += 1
                            line = line[index:].strip()
                            nums = line.count(",")
                            while nums >= 0:
                                nums -= 1
                                index = line.find(",")
                                if index == -1:
                                    #the last one
                                    key = line.strip()
                                    phynets.append(key)
                                else:
                                    #not the last one
                                    index = line.index(",")
                                    key = line[:index].strip()
                                    phynets.append(key)
                                    line = line[index + 1:]
                fp.close()

        elif net_type == "vlan":
            try:
                fp = open('/etc/neutron/plugins/ml2/ml2_conf.ini', 'r')
            except IOError:
                LOG.ERROR("cat not open file '/etc/neutron/plugins/ml2/ml2_conf.ini',exist??")
            else:
                for line in fp:
                    if line[:19] == "network_vlan_ranges":
                        index = line.find("=")
                        if index == -1:
                            LOG.debug(_("'network_vlan_ranges' no value in line:%s "), line)
                            continue
                        else:
                            index += 1
                            line = line[index:].strip()
                            nums = line.count(",")
                            while nums >= 0:
                                nums -= 1
                                index = line.find(",")
                                if index == -1:
                                    #the last key(phynetwork)
                                    si = line.index(":")
                                    key = line[:si].strip()
                                    phynets.append(key)
                                else:
                                    #not the last
                                    sl = line[:index].strip()
                                    si = line.find(":")
                                    if si == -1:
                                        LOG.error(_(
                                            "line:%s  must like 'network_vlan_ranges = physnet2:32:44'"),
                                                  line)
                                        break
                                    else:
                                        key = sl[:si].strip()
                                        phynets.append(key)
                                        line = line[index + 1:]
                fp.close()

        else:
            LOG.error("networkType should one of [flat,vlan]")
        #add by xm-2015.8.25 for bug5783
        phynets = list(set(phynets))
        return [{"phydev": phynets}]

    def get_phynetwork(self, context, id, fields=None):
        return {"phydev": "eth0"}

    def get_networktypes_bak(self, context, filters=None, fields=None):
        nettypes=[]
        try:
                fp = open('/etc/neutron/plugins/ml2/ml2_conf.ini', 'r')
        except IOError:
            LOG.ERROR("cat not open file '/etc/neutron/plugins/ml2/ml2_conf.ini',exist??")
        else:
            for line in fp:
                if line[:12] == "tenant_network_types":
                    index = line.find("=")
                    if index == -1:
                        LOG.debug(_("'tenant_network_types' no value in line:%s "), line)
                        continue
                    else:
                        index += 1
                        line = line[index:].strip()
                        nums = line.count(",")
                        while nums >= 0:
                            nums -= 1
                            index = line.find(",")
                            if index == -1:
                                #the last one
                                key = line.strip()
                                nettypes.append(key)
                            else:
                                #not the last one
                                index = line.index(",")
                                key = line[:index].strip()
                                nettypes.append(key)
                                line = line[index + 1:]
            fp.close()
        #add by xm-2015.8.25 for bug5783
        nettypes = list(set(nettypes))
        return [{"nettype": nettypes}]


    def get_networktypes(self, context, filters=None, fields=None):
        nettypes=cfg.CONF.ml2.tenant_network_types
        return [{"nettype": nettypes}]
    #neutron/api/v2/router.py中使用 cfg.CONF.allow_sorting