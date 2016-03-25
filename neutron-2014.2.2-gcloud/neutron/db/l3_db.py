# -*- coding:utf-8 -*-
# Copyright 2012 VMware, Inc.  All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#from dbgp.client import brk
import netaddr
import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import exc
from sqlalchemy import func #add by gcloud for counting floatingip number
from neutron.api.rpc.agentnotifiers import l3_rpc_agent_api
from neutron.api.v2 import attributes
from neutron.common import constants as l3_constants
from neutron.common import exceptions as n_exc
from neutron.common import rpc as n_rpc
from neutron.common import utils
from neutron.db import model_base
from neutron.db import models_v2
from neutron.extensions import external_net
from neutron.extensions import l3
from neutron import manager
from neutron.openstack.common import log as logging
from neutron.openstack.common import uuidutils
from neutron.plugins.common import constants
from neutron.openstack.common import timeutils
import neutron.db.api as db
from neutron.plugins.common import constants as plugin_constants
from neutron.api.v2 import attributes as attr
from neutron.db import sqlalchemyutils
#from neutron.db import l3_attrs_db
#import neutron.db.gcloud_nat_db as gc_nat
from neutron.plugins.common import constants as service_constants
from oslo.config import cfg

LOG = logging.getLogger(__name__)


DEVICE_OWNER_ROUTER_INTF = l3_constants.DEVICE_OWNER_ROUTER_INTF
DEVICE_OWNER_ROUTER_GW = l3_constants.DEVICE_OWNER_ROUTER_GW
DEVICE_OWNER_FLOATINGIP = l3_constants.DEVICE_OWNER_FLOATINGIP
EXTERNAL_GW_INFO = l3.EXTERNAL_GW_INFO

# Maps API field to DB column
# API parameter name and Database column names may differ.
# Useful to keep the filtering between API and Database.
API_TO_DB_COLUMN_MAP = {'port_id': 'fixed_port_id'}
CORE_ROUTER_ATTRS = ('id', 'name', 'tenant_id', 'admin_state_up', 'status', 'user_id', 'create_time')


class RouterPort(model_base.BASEV2):
    router_id = sa.Column(
        sa.String(36),
        sa.ForeignKey('routers.id', ondelete="CASCADE"),
        primary_key=True)
    port_id = sa.Column(
        sa.String(36),
        sa.ForeignKey('ports.id', ondelete="CASCADE"),
        primary_key=True)
    # The port_type attribute is redundant as the port table already specifies
    # it in DEVICE_OWNER.However, this redundancy enables more efficient
    # queries on router ports, and also prevents potential error-prone
    # conditions which might originate from users altering the DEVICE_OWNER
    # property of router ports.
    port_type = sa.Column(sa.String(255))
    subnet_id = sa.Column(sa.String(36))
    port = orm.relationship(
        models_v2.Port,
        backref=orm.backref('routerport', uselist=False, cascade="all,delete"))



class Router(model_base.BASEV2, models_v2.HasId, models_v2.HasCreateTime,models_v2.HasTenant):
    """Represents a v2 neutron router."""

    name = sa.Column(sa.String(255))
    status = sa.Column(sa.String(16))
    admin_state_up = sa.Column(sa.Boolean)
    gw_port_id = sa.Column(sa.String(36), sa.ForeignKey('ports.id'))
    gw_port = orm.relationship(models_v2.Port, lazy='joined')
    attached_ports = orm.relationship(
        RouterPort,
        backref='router',
        lazy='dynamic')
    #create_time = sa.Column(sa.String(26), default=timeutils.strtime(timeutils.now_cst_time()),
    #                        nullable=False)
    user_id = sa.Column(sa.String(64),  nullable=False)
#"""

class GcloudQueueQos(model_base.BASEV2,models_v2.HasCreateTime):
    floating_port_id = sa.Column(
        sa.String(36),
        sa.ForeignKey('ports.id', ondelete="CASCADE"),
        primary_key=True)
    src_ip=sa.Column(sa.String(32))
    max_rate=sa.Column(sa.BIGINT)
    min_rate=sa.Column(sa.BIGINT)

#"""
class FloatingIP(model_base.BASEV2, models_v2.HasId, models_v2.HasTenant):
    """Represents a floating IP address.

    This IP address may or may not be allocated to a tenant, and may or
    may not be associated with an internal port/ip address/router.
    """

    floating_ip_address = sa.Column(sa.String(64), nullable=False)
    floating_network_id = sa.Column(sa.String(36), nullable=False)
    floating_port_id = sa.Column(sa.String(36), sa.ForeignKey('ports.id'),
                                 nullable=False)
    fixed_port_id = sa.Column(sa.String(36), sa.ForeignKey('ports.id'))
    fixed_ip_address = sa.Column(sa.String(64))
    router_id = sa.Column(sa.String(36), sa.ForeignKey('routers.id'))
    # Additional attribute for keeping track of the router where the floating
    # ip was associated in order to be able to ensure consistency even if an
    # aysnchronous backend is unavailable when the floating IP is disassociated
    last_known_router_id = sa.Column(sa.String(36))
    status = sa.Column(sa.String(16))
    router = orm.relationship(Router, backref='floating_ips')
    user_id = sa.Column(sa.String(64),  nullable=True)
    type = sa.Column(sa.String(32),  nullable=True)

class L3_NAT_dbonly_mixin(l3.RouterPluginBase):
    """Mixin class to add L3/NAT router methods to db_base_plugin_v2."""

    router_device_owners = (
        DEVICE_OWNER_ROUTER_INTF,
        DEVICE_OWNER_ROUTER_GW,
        DEVICE_OWNER_FLOATINGIP
    )

    @property
    def _core_plugin(self):
        return manager.NeutronManager.get_plugin()

    def _get_router(self, context, router_id):
        try:
            router = self._get_by_id(context, Router, router_id)
        except exc.NoResultFound:
            raise l3.RouterNotFound(router_id=router_id)
        return router

    def _get_router_port(self, context, router_id, port_id):
        query = context.session.query(RouterPort)
        return query.filter(
            RouterPort.router_id == router_id,
            RouterPort.port_id == port_id
        )

    def _get_subnet_num_by_router_id(self, router_id):
        # #add by xm-20150525-for get_routers 返回子网数量（暂时不考虑ha的路由：以后考虑方向当为ha时，
        # 默认+1：因为routerports表中不显示network:router_ha_interface记录，另外由于同一个ha路由会接入同一个ha子网的多个端口，所以不能通过ports的device_id查询）
        session = db.get_session()
        query = session.query(models_v2.Port).filter_by(device_id=router_id)
        subnet_num = query.count()
        #for ha路由
        # router_extra_attrs = session.query(l3_attrs_db.RouterExtraAttributes).filter_by(router_id=router_id).first()
        # if router_extra_attrs and router_extra_attrs.ha:
        #     subnet_num +=1
        return subnet_num

    def _make_router_dict(self, router, fields=None, process_extensions=True):
        res = dict((key, router[key]) for key in CORE_ROUTER_ATTRS)
        if router['gw_port_id']:
            ext_gw_info = {
                'network_id': router.gw_port['network_id'],
                'external_fixed_ips': [{'subnet_id': ip["subnet_id"],
                                        'ip_address': ip["ip_address"]}
                                       for ip in router.gw_port['fixed_ips']]}
        else:
            ext_gw_info = None
        res.update({
            EXTERNAL_GW_INFO: ext_gw_info,
            'gw_port_id': router['gw_port_id'],
        })
        #add by xm-20150528
        res.update({"subnet_num": self._get_subnet_num_by_router_id(router["id"])})

        # NOTE(salv-orlando): The following assumes this mixin is used in a
        # class inheriting from CommonDbMixin, which is true for all existing
        # plugins.
        if process_extensions:
            self._apply_dict_extend_functions(l3.ROUTERS, res, router)
        return self._fields(res, fields)

    def _create_router_db(self, context, router, tenant_id):
        """Create the DB object."""
        with context.session.begin(subtransactions=True):
            # pre-generate id so it will be available when
            # configuring external gw port
            router_db = Router(id=uuidutils.generate_uuid(),
                               tenant_id=tenant_id,
                               name=router['name'],
                               admin_state_up=router['admin_state_up'],
                               status="ACTIVE",
                               user_id=context.user)
            context.session.add(router_db)
            return router_db

    def create_router(self, context, router):
        r = router['router']
        gw_info = r.pop(EXTERNAL_GW_INFO, None)
        tenant_id = self._get_tenant_id_for_create(context, r)
        with context.session.begin(subtransactions=True):
            router_db = self._create_router_db(context, r, tenant_id)
            if gw_info:
                self._update_router_gw_info(context, router_db['id'],
                                            gw_info, router=router_db)
        return self._make_router_dict(router_db)

    def _update_router_db(self, context, router_id, data, gw_info):
        """Update the DB object."""
        with context.session.begin(subtransactions=True):
            router_db = self._get_router(context, router_id)
            if data:
                router_db.update(data)
            return router_db

    def update_router(self, context, id, router):
        r = router['router']
        gw_info = r.pop(EXTERNAL_GW_INFO, attributes.ATTR_NOT_SPECIFIED)
        # check whether router needs and can be rescheduled to the proper
        # l3 agent (associated with given external network);
        # do check before update in DB as an exception will be raised
        # in case no proper l3 agent found
        if gw_info != attributes.ATTR_NOT_SPECIFIED:
            candidates = self._check_router_needs_rescheduling(
                context, id, gw_info)
            # Update the gateway outside of the DB update since it involves L2
            # calls that don't make sense to rollback and may cause deadlocks
            # in a transaction.
            self._update_router_gw_info(context, id, gw_info)
        else:
            candidates = None
        router_db = self._update_router_db(context, id, r, gw_info)
        if candidates:
            l3_plugin = manager.NeutronManager.get_service_plugins().get(
                constants.L3_ROUTER_NAT)
            l3_plugin.reschedule_router(context, id, candidates)
        return self._make_router_dict(router_db)

    def _check_router_needs_rescheduling(self, context, router_id, gw_info):
        """Checks whether router's l3 agent can handle the given network

        When external_network_bridge is set, each L3 agent can be associated
        with at most one external network. If router's new external gateway
        is on other network then the router needs to be rescheduled to the
        proper l3 agent.
        If external_network_bridge is not set then the agent
        can support multiple external networks and rescheduling is not needed

        :return: list of candidate agents if rescheduling needed,
        None otherwise; raises exception if there is no eligible l3 agent
        associated with target external network
        """
        # TODO(obondarev): rethink placement of this func as l3 db manager is
        # not really a proper place for agent scheduling stuff
        network_id = gw_info.get('network_id') if gw_info else None
        if not network_id:
            return

        nets = self._core_plugin.get_networks(
            context, {external_net.EXTERNAL: [True]})
        # nothing to do if there is only one external network
        if len(nets) <= 1:
            return

        # first get plugin supporting l3 agent scheduling
        # (either l3 service plugin or core_plugin)
        l3_plugin = manager.NeutronManager.get_service_plugins().get(
            constants.L3_ROUTER_NAT)
        if (not utils.is_extension_supported(
                l3_plugin,
                l3_constants.L3_AGENT_SCHEDULER_EXT_ALIAS) or
            l3_plugin.router_scheduler is None):
            # that might mean that we are dealing with non-agent-based
            # implementation of l3 services
            return

        cur_agents = l3_plugin.list_l3_agents_hosting_router(
            context, router_id)['agents']
        for agent in cur_agents:
            ext_net_id = agent['configurations'].get(
                'gateway_external_network_id')
            ext_bridge = agent['configurations'].get(
                'external_network_bridge', 'br-ex')
            if (ext_net_id == network_id or
                    (not ext_net_id and not ext_bridge)):
                return

        # otherwise find l3 agent with matching gateway_external_network_id
        active_agents = l3_plugin.get_l3_agents(context, active=True)
        router = {
            'id': router_id,
            'external_gateway_info': {'network_id': network_id}
        }
        candidates = l3_plugin.get_l3_agent_candidates(context,
                                                       router,
                                                       active_agents)
        if not candidates:
            msg = (_('No eligible l3 agent associated with external network '
                     '%s found') % network_id)
            raise n_exc.BadRequest(resource='router', msg=msg, gcloud_code='neutron_server_l3route_000010')

        return candidates

    def _create_router_gw_port(self, context, router, network_id):
        # Port has no 'tenant-id', as it is hidden from user
        gw_port = self._core_plugin.create_port(context.elevated(), {
            'port': {'tenant_id': '',  # intentionally not set
                     'network_id': network_id,
                     'mac_address': attributes.ATTR_NOT_SPECIFIED,
                     'fixed_ips': attributes.ATTR_NOT_SPECIFIED,
                     'device_id': router['id'],
                     'device_owner': DEVICE_OWNER_ROUTER_GW,
                     'admin_state_up': True,
                     'name': ''}})

        ## alter by xm at 2015.12.7 for tz project
        #before is :
        # if not gw_port['fixed_ips']:
        #     self._core_plugin.delete_port(context.elevated(), gw_port['id'],
        #                                   l3_port_check=False)
        #     msg = (_('No IPs available for external network %s') %
        #            network_id)
        #     raise n_exc.BadRequest(resource='router', msg=msg,gcloud_code='neutron_server_l3route_000008')
        #changed to :
        allow_gcloud_nat = cfg.CONF.allow_gcloud_nat
        #LOG.debug(_("111111 create_router 8888 ! allow_gcloud_nat=%d"), allow_gcloud_nat)
        if not allow_gcloud_nat and not gw_port['fixed_ips']:
            self._core_plugin.delete_port(context.elevated(), gw_port['id'],
                                          l3_port_check=False)
            msg = (_('No IPs available for external network %s') %
                   network_id)
            raise n_exc.BadRequest(resource='router', msg=msg,gcloud_code='neutron_server_l3route_000008')
        ##end of delete 2015.12.7
        #LOG.debug(_("111111 create_router 8888 ! gw_port=%s"), gw_port)
        with context.session.begin(subtransactions=True):
            router.gw_port = self._core_plugin._get_port(context.elevated(),
                                                         gw_port['id'])
            router_port = RouterPort(
                router_id=router.id,
                port_id=gw_port['id'],
                port_type=DEVICE_OWNER_ROUTER_GW,
                #add by xm-20150523: for routers records in get_subnets:method 2
                #subnet_id=gw_port['fixed_ips'][0]['subnet_id']
                #changed by xm-2015.12.7 for tz project
                subnet_id=self._tz_get_subnet_id(gw_port)
            )
            context.session.add(router)
            context.session.add(router_port)

    def _tz_get_subnet_id(self, port):
        '''
        add by xm at 2015.12.7 for tz project
        '''
        subnet_id = ''
        if port and port['fixed_ips']:
            subnet_id = port['fixed_ips'][0]['subnet_id']
        return subnet_id

    def tz_update_routerport_subnet_id(self, context, router_id, port_id, subnet_id, port_type=DEVICE_OWNER_ROUTER_GW):
        '''
        add by xm at 2015.12.7 for tz project
        add subnet_id to the RouterPort when create a nat
        '''
        with context.session.begin(subtransactions=True):
            router_port = RouterPort(
                router_id=router_id,
                port_id=port_id,
                port_type=port_type,
                subnet_id=subnet_id
            )
            context.session.add(router_port)

    def _validate_gw_info(self, context, gw_port, info):
        network_id = info['network_id'] if info else None
        if network_id:
            network_db = self._core_plugin._get_network(context, network_id)
            if not network_db.external:
                msg = _("Network %s is not an external network") % network_id
                raise n_exc.BadRequest(resource='router', msg=msg, gcloud_code='neutron_server_l3route_000009')
        return network_id

    def _delete_current_gw_port(self, context, router_id, router, new_network):
        """Delete gw port, if it is attached to an old network."""
        is_gw_port_attached_to_existing_network = (
            router.gw_port and router.gw_port['network_id'] != new_network)
        admin_ctx = context.elevated()
        if is_gw_port_attached_to_existing_network:
            if self.get_floatingips_count(
                admin_ctx, {'router_id': [router_id]}):
                raise l3.RouterExternalGatewayInUseByFloatingIp(
                    router_id=router_id, net_id=router.gw_port['network_id'])
            with context.session.begin(subtransactions=True):
                gw_port = router.gw_port
                router.gw_port = None
                context.session.add(router)
                context.session.expire(gw_port)
            self._core_plugin.delete_port(
                admin_ctx, gw_port['id'], l3_port_check=False)

    def _create_gw_port(self, context, router_id, router, new_network):
        new_valid_gw_port_attachment = (
            new_network and (not router.gw_port or
                             router.gw_port['network_id'] != new_network))
        if new_valid_gw_port_attachment:
            subnets = self._core_plugin._get_subnets_by_network(context,
                                                                new_network)
            for subnet in subnets:
                self._check_for_dup_router_subnet(context, router,
                                                  new_network, subnet['id'],
                                                  subnet['cidr'])
            self._create_router_gw_port(context, router, new_network)

    def _update_router_gw_info(self, context, router_id, info, router=None):
        # TODO(salvatore-orlando): guarantee atomic behavior also across
        # operations that span beyond the model classes handled by this
        # class (e.g.: delete_port)
        router = router or self._get_router(context, router_id)
        gw_port = router.gw_port
        network_id = self._validate_gw_info(context, gw_port, info)
        self._delete_current_gw_port(context, router_id, router, network_id)
        self._create_gw_port(context, router_id, router, network_id)

    def _ensure_router_not_in_use(self, context, router_id):
        admin_ctx = context.elevated()
        router = self._get_router(context, router_id)
        if self.get_floatingips_count(
            admin_ctx, filters={'router_id': [router_id]}):
            raise l3.RouterInUse(router_id=router_id)
        device_owner = self._get_device_owner(context, router)
        if any(rp.port_type == device_owner
               for rp in router.attached_ports.all()):
            raise l3.RouterInUse(router_id=router_id)
        return router

    def delete_router(self, context, id):
        with context.session.begin(subtransactions=True):
            router = self._ensure_router_not_in_use(context, id)

            #TODO(nati) Refactor here when we have router insertion model
            vpnservice = manager.NeutronManager.get_service_plugins().get(
                constants.VPN)
            if vpnservice:
                vpnservice.check_router_in_use(context, id)

            router_ports = router.attached_ports.all()
            # Set the router's gw_port to None to avoid a constraint violation.
            router.gw_port = None
            for rp in router_ports:
                self._core_plugin._delete_port(context.elevated(), rp.port.id)
            context.session.delete(router)

    def get_router(self, context, id, fields=None):
        router = self._get_router(context, id)
        return self._make_router_dict(router, fields)

    def _get_network_ids_by_network_name(self, context, network_names):
        networks = context.session.query(models_v2.Network).filter(models_v2.Network.name.in_(network_names)).all()
        if networks:
                return [ network["id"] for network in networks]
        return [""]

    def _get_routers_query(self, context, filters=None, sorts=None, limit=None, marker_obj=None,
                           page_reverse=False, offset=None):
        #brk(host="10.10.0.90",port=50269)
        l3plugin = manager.NeutronManager.get_service_plugins()[plugin_constants.L3_ROUTER_NAT]
        query = l3plugin._model_query(context, Router)

        egi = filters.pop("external_gateway_info", {})
        egi = attr.convert_kvp_list_to_dict(egi)
        network_names_from_egi = egi.get('network_name', None)
        network_ids_from_egi = egi.get("network_id", None)
        network_ids = []
        if network_names_from_egi is not None:
            network_ids_from_network_names = self._get_network_ids_by_network_name(context, network_names_from_egi)
            if network_ids_from_egi:
                network_ids = list(set(network_ids) & set(network_ids_from_network_names))
            else:
                network_ids = network_ids_from_network_names
        else:
            network_ids = network_ids_from_egi

        if network_names_from_egi or network_ids_from_egi:
            query = query.join(Router.gw_port)
            query = query.filter(models_v2.Port.network_id.in_(network_ids))

        query = self._apply_filters_to_query(query, Router, filters)
        if limit and page_reverse and sorts:
            sorts = [(s[0], not s[1]) for s in sorts]
        query = sqlalchemyutils.paginate_query(query, Router, limit,
                                               sorts, marker_obj, offset)
        return query

    def get_routers(self, context, filters=None, fields=None,
                    sorts=None, limit=None, marker=None,
                    page_reverse=False, offset=None):
        marker_obj = self._get_marker_obj(context, 'router', limit, marker)
        # #self=L3RouterPlugin    neutron/db/common_db_mixin.py:_get_collection()
        # return self._get_collection(context, Router,
        #                             self._make_router_dict,
        #                             filters=filters, fields=fields,
        #                             sorts=sorts,
        #                             limit=limit,
        #                             marker_obj=marker_obj,
        #                             page_reverse=page_reverse, offset=offset)
        query = self._get_routers_query(context, filters=filters,sorts=sorts, limit=limit, marker_obj=marker_obj,
                                        page_reverse=page_reverse, offset=offset)
        items = [self._make_router_dict(c, fields) for c in query]
        if limit and page_reverse:
            items.reverse()
        return items


    def get_routers_count(self, context, filters=None):
        # return self._get_collection_count(context, Router,
        #                                   filters=filters)
        return self._get_routers_query(context, filters).count()

    def _check_for_dup_router_subnet(self, context, router,
                                     network_id, subnet_id, subnet_cidr):
        try:
            # It's possible these ports are on the same network, but
            # different subnets.
            new_ipnet = netaddr.IPNetwork(subnet_cidr)
            #LOG.debug(_("111111 create_router 2345 ! attached_ports=%s"), router.attached_ports.__dict__)
            for p in (rp.port for rp in router.attached_ports):
                for ip in p['fixed_ips']:
                    if ip['subnet_id'] == subnet_id:
                        msg = (_("Router already has a port on subnet %s")
                               % subnet_id)
                        raise n_exc.BadRequest(resource='router', msg=msg ,gcloud_code='neutron_server_l3route_000001')
                    sub_id = ip['subnet_id']
                    cidr = self._core_plugin._get_subnet(context.elevated(),
                                                         sub_id)['cidr']
                    ipnet = netaddr.IPNetwork(cidr)
                    match1 = netaddr.all_matching_cidrs(new_ipnet, [cidr])
                    match2 = netaddr.all_matching_cidrs(ipnet, [subnet_cidr])
                    if match1 or match2:
                        data = {'subnet_cidr': subnet_cidr,
                                'subnet_id': subnet_id,
                                'cidr': cidr,
                                'sub_id': sub_id}
                        msg = (_("Cidr %(subnet_cidr)s of subnet "
                                 "%(subnet_id)s overlaps with cidr %(cidr)s "
                                 "of subnet %(sub_id)s") % data)
                        raise n_exc.BadRequest(resource='router', msg=msg , gcloud_code='neutron_server_l3route_000002')
        except exc.NoResultFound:
            pass

    def _get_device_owner(self, context, router=None):
        """Get device_owner for the specified router."""
        # NOTE(armando-migliaccio): in the base case this is invariant
        return DEVICE_OWNER_ROUTER_INTF

    def _validate_interface_info(self, interface_info):
        port_id_specified = interface_info and 'port_id' in interface_info
        subnet_id_specified = interface_info and 'subnet_id' in interface_info
        if not (port_id_specified or subnet_id_specified):
            msg = _("Either subnet_id or port_id must be specified")
            raise n_exc.BadRequest(resource='router', msg=msg , gcloud_code='neutron_server_l3route_000003')
        if port_id_specified and subnet_id_specified:
            msg = _("Cannot specify both subnet-id and port-id")
            raise n_exc.BadRequest(resource='router', msg=msg  , gcloud_code='neutron_server_l3route_000004')
        return port_id_specified, subnet_id_specified

    def _add_interface_by_port(self, context, router, port_id, owner):
        with context.session.begin(subtransactions=True):
            port = self._core_plugin._get_port(context, port_id)
            if port['device_id']:
                raise n_exc.PortInUse(net_id=port['network_id'],
                                      port_id=port['id'],
                                      device_id=port['device_id'])
            fixed_ips = [ip for ip in port['fixed_ips']]
            if len(fixed_ips) != 1:
                msg = _('Router port must have exactly one fixed IP')
                raise n_exc.BadRequest(resource='router', msg=msg ,gcloud_code='neutron_server_l3route_000005')
            subnet_id = fixed_ips[0]['subnet_id']
            subnet = self._core_plugin._get_subnet(context, subnet_id)
            self._check_for_dup_router_subnet(context, router,
                                              port['network_id'],
                                              subnet['id'],
                                              subnet['cidr'])
            port.update({'device_id': router.id, 'device_owner': owner})
            return port

    def _add_interface_by_subnet(self, context, router, subnet_id, owner):
        subnet = self._core_plugin._get_subnet(context, subnet_id)
        if not subnet['gateway_ip']:
            msg = _('Subnet for router interface must have a gateway IP')
            raise n_exc.BadRequest(resource='router', msg=msg  ,gcloud_code='neutron_server_l3route_000006')
        self._check_for_dup_router_subnet(context, router,
                                          subnet['network_id'],
                                          subnet_id,
                                          subnet['cidr'])
        fixed_ip = {'ip_address': subnet['gateway_ip'],
                    'subnet_id': subnet['id']}

        return self._core_plugin.create_port(context, {
            'port':
            {'tenant_id': subnet['tenant_id'],
             'network_id': subnet['network_id'],
             'fixed_ips': [fixed_ip],
             'mac_address': attributes.ATTR_NOT_SPECIFIED,
             'admin_state_up': True,
             'device_id': router.id,
             'device_owner': owner,
             'name': ''}})

    @staticmethod
    def _make_router_interface_info(
            router_id, tenant_id, port_id, subnet_id):
        return {
            'id': router_id,
            'tenant_id': tenant_id,
            'port_id': port_id,
            'subnet_id': subnet_id
        }

    def add_router_interface(self, context, router_id, interface_info):
        router = self._get_router(context, router_id)
        add_by_port, add_by_sub = self._validate_interface_info(interface_info)
        device_owner = self._get_device_owner(context, router_id)

        if add_by_port:
            port = self._add_interface_by_port(
                context, router, interface_info['port_id'], device_owner)
        elif add_by_sub:
            # ###add by xm at 2015.9.1 for bug 6061 ---begin---
            # if 'name' in interface_info and interface_info['name'] is not None:
            #     name = interface_info['name']
            # else:
            #     name = ''
            # ###end
            # port = self._add_interface_by_subnet(
            #     context, router, interface_info['subnet_id'], device_owner, name)
            port = self._add_interface_by_subnet(
                context, router, interface_info['subnet_id'], device_owner)

        with context.session.begin(subtransactions=True):
            router_port = RouterPort(
                port_id=port['id'],
                router_id=router.id,
                port_type=device_owner,
                subnet_id=port['fixed_ips'][0]['subnet_id']
            )
            context.session.add(router_port)

        return self._make_router_interface_info(
            router.id, port['tenant_id'], port['id'],
            port['fixed_ips'][0]['subnet_id'])



    def get_floatingip_qos(self,context,id,fields=None):
        floating_port_id=id
        floatingip_qos=self._get_floatingip_qos(context,floating_port_id)
        if floatingip_qos:
            ipAllocation=context.session.query(models_v2.IPAllocation).filter_by(port_id=floatingip_qos['floating_port_id']).first()
            if ipAllocation:
                subnet_id=ipAllocation["subnet_id"]
                subnet=context.session.query(models_v2.Subnet).filter_by(id=subnet_id).first()
                floatingip_qos["type"]=subnet["type"]
                LOG.debug("type %s"%(floatingip_qos["type"]))
        return self._make_floatingip_qos_dict(floatingip_qos)
    def _get_floatingip_qos(self,context,floating_port_id=None):
        qos= context.session.query(GcloudQueueQos).filter_by(floating_port_id = floating_port_id).first()
        return  qos

    def _confirm_router_interface_not_in_use(self, context, router_id,
                                             subnet_id):
        subnet_db = self._core_plugin._get_subnet(context, subnet_id)
        subnet_cidr = netaddr.IPNetwork(subnet_db['cidr'])
        fip_qry = context.session.query(FloatingIP)
        for fip_db in fip_qry.filter_by(router_id=router_id):
            if netaddr.IPAddress(fip_db['fixed_ip_address']) in subnet_cidr:
                raise l3.RouterInterfaceInUseByFloatingIP(
                    router_id=router_id, subnet_id=subnet_id)

    def _remove_interface_by_port(self, context, router_id,
                                  port_id, subnet_id, owner):
        qry = context.session.query(RouterPort)
        qry = qry.filter_by(
            port_id=port_id,
            router_id=router_id,
            port_type=owner
        )
        try:
            port_db = qry.one().port
        except exc.NoResultFound:
            raise l3.RouterInterfaceNotFound(router_id=router_id,
                                             port_id=port_id)
        port_subnet_id = port_db['fixed_ips'][0]['subnet_id']
        if subnet_id and port_subnet_id != subnet_id:
            raise n_exc.SubnetMismatchForPort(
                port_id=port_id, subnet_id=subnet_id)
        subnet = self._core_plugin._get_subnet(context, port_subnet_id)
        self._confirm_router_interface_not_in_use(
            context, router_id, port_subnet_id)
        self._core_plugin.delete_port(context, port_db['id'],
                                      l3_port_check=False)
        return (port_db, subnet)

    def _remove_interface_by_subnet(self, context,
                                    router_id, subnet_id, owner):
        self._confirm_router_interface_not_in_use(
            context, router_id, subnet_id)
        subnet = self._core_plugin._get_subnet(context, subnet_id)

        try:
            rport_qry = context.session.query(models_v2.Port).join(RouterPort)
            ports = rport_qry.filter(
                RouterPort.router_id == router_id,
                RouterPort.port_type == owner,
                models_v2.Port.network_id == subnet['network_id']
            )

            for p in ports:
                if p['fixed_ips'][0]['subnet_id'] == subnet_id:
                    self._core_plugin.delete_port(context, p['id'],
                                                  l3_port_check=False)
                    return (p, subnet)
        except exc.NoResultFound:
            pass
        raise l3.RouterInterfaceNotFoundForSubnet(router_id=router_id,
                                                  subnet_id=subnet_id)

    def remove_router_interface(self, context, router_id, interface_info):
        if not interface_info:
            msg = _("Either subnet_id or port_id must be specified")
            raise n_exc.BadRequest(resource='router', msg=msg ,gcloud_code='neutron_server_l3route_000007')
        port_id = interface_info.get('port_id')
        subnet_id = interface_info.get('subnet_id')
        device_owner = self._get_device_owner(context, router_id)
        if port_id:
            port, subnet = self._remove_interface_by_port(context, router_id,
                                                          port_id, subnet_id,
                                                          device_owner)
        elif subnet_id:
            port, subnet = self._remove_interface_by_subnet(
                context, router_id, subnet_id, device_owner)

        return self._make_router_interface_info(router_id, port['tenant_id'],
                                                port['id'], subnet['id'])

    def _get_floatingip(self, context, id):
        try:
            floatingip = self._get_by_id(context, FloatingIP, id)
        except exc.NoResultFound:
            raise l3.FloatingIPNotFound(floatingip_id=id)
        return floatingip

    def _make_floatingip_dict(self, floatingip, fields=None):
        res = {'id': floatingip['id'],
               'tenant_id': floatingip['tenant_id'],
               'floating_ip_address': floatingip['floating_ip_address'],
               'floating_network_id': floatingip['floating_network_id'],
               'router_id': floatingip['router_id'],
               'port_id': floatingip['fixed_port_id'],
               'fixed_ip_address': floatingip['fixed_ip_address'],
               'floating_port_id': floatingip['floating_port_id'],
               'status': floatingip['status'],
               'user_id': floatingip['user_id'],#add by luoyibing 20150901
               'type': floatingip['type']} # add by xm at 20160304
        return self._fields(res, fields)

    def _make_floatingip_qos_dict(self, floatingip_qos, fields=None):
        res={}
        if floatingip_qos:
            res = {
                'src_ip': floatingip_qos['src_ip'],
                'floating_port_id': floatingip_qos['floating_port_id'],
                'max_rate': floatingip_qos['max_rate'],
                'min_rate': floatingip_qos.get('min_rate',None)
                }
            type = floatingip_qos.get("type")
            if type:
               res["type"]=type
        return self._fields(res, fields)

    def _get_interface_ports_for_network(self, context, network_id):
        router_intf_qry = context.session.query(RouterPort)
        router_intf_qry = router_intf_qry.join(models_v2.Port)
        return router_intf_qry.filter(
            models_v2.Port.network_id == network_id,
            RouterPort.port_type == DEVICE_OWNER_ROUTER_INTF
        )

    def _get_gateway_ports_for_network(self, context, network_id):
        router_intf_qry = context.session.query(RouterPort)
        router_intf_qry = router_intf_qry.join(models_v2.Port)
        return router_intf_qry.filter(
            models_v2.Port.network_id == network_id,
            RouterPort.port_type == DEVICE_OWNER_ROUTER_GW
        )

    def _get_router_for_floatingip(self, context, internal_port,
                                   internal_subnet_id,
                                   external_network_id):
        subnet_db = self._core_plugin._get_subnet(context,
                                                  internal_subnet_id)
        if not subnet_db['gateway_ip']:
            msg = (_('Cannot add floating IP to port on subnet %s '
                     'which has no gateway_ip') % internal_subnet_id)
            raise n_exc.BadRequest(resource='floatingip', msg=msg, gcloud_code='neutron_server_floatingip_100003')

        router_intf_ports = self._get_interface_ports_for_network(
            context, internal_port['network_id'])

        # ###add by xm at 2015.9.18 for bug 6621
        # router_gw_ports = self._get_gateway_ports_for_network(
        #     context, external_network_id)
        # if router_gw_ports:
        #     router_id_for_gw = router_gw_ports.first().router.id
        # ###end-by xm

        # This joins on port_id so is not a cross-join
        routerport_qry = router_intf_ports.join(models_v2.IPAllocation)
        routerport_qry = routerport_qry.filter(
            models_v2.IPAllocation.subnet_id == internal_subnet_id
        )

        router_port = routerport_qry.first()

        ### alter by xm at 2015.9.18 for bug 6621
        # if router_port and router_port.router.gw_port:
        #     return router_port.router.id
        # alter as follow:
        if router_port and router_port.router.gw_port and router_port.router.gw_port.network_id == external_network_id:
            #add by xm at 2015.10.14 for bug 6776
            #LOG.debug(_("2222 345 %s %s %s"),router_port.router.id,context.user_id,context.gc_resource_type)
            if context.gc_resource_type == '0':
                router_query = context.session.query(Router).filter(
                Router.user_id == context.user_id,
                Router.id == router_port.router.id
                ).first()
                if router_query:
                    return router_port.router.id
                else:
                    LOG.error(_("gc_resource_type=0 of the user=%s in this zone,and the router=%s "
                                "not belong to the user!"), context.user_id,router_port.router.id)
                    raise l3.RouterNotFound(router_id=router_port.router.id)
            #end 2015.10.14
            return router_port.router.id
        ###end-by xm 2015.9.18

        raise l3.ExternalGatewayForFloatingIPNotFound(
            subnet_id=internal_subnet_id,
            external_network_id=external_network_id,
            port_id=internal_port['id'])

    def _internal_fip_assoc_data(self, context, fip):
        """Retrieve internal port data for floating IP.

        Retrieve information concerning the internal port where
        the floating IP should be associated to.
        """
        internal_port = self._core_plugin._get_port(context, fip['port_id'])
        if not internal_port['tenant_id'] == fip['tenant_id']:
            port_id = fip['port_id']
            if 'id' in fip:
                floatingip_id = fip['id']
                data = {'port_id': port_id,
                        'floatingip_id': floatingip_id}
                msg = (_('Port %(port_id)s is associated with a different '
                         'tenant than Floating IP %(floatingip_id)s and '
                         'therefore cannot be bound.') % data)
            else:
                msg = (_('Cannot create floating IP and bind it to '
                         'Port %s, since that port is owned by a '
                         'different tenant.') % port_id)
            raise n_exc.BadRequest(resource='floatingip', msg=msg, gcloud_code='neutron_server_floatingip_100004')

        internal_subnet_id = None
        if 'fixed_ip_address' in fip and fip['fixed_ip_address']:
            internal_ip_address = fip['fixed_ip_address']
            for ip in internal_port['fixed_ips']:
                if ip['ip_address'] == internal_ip_address:
                    internal_subnet_id = ip['subnet_id']
            if not internal_subnet_id:
                msg = (_('Port %(id)s does not have fixed ip %(address)s') %
                       {'id': internal_port['id'],
                        'address': internal_ip_address})
                raise n_exc.BadRequest(resource='floatingip', msg=msg, gcloud_code='neutron_server_floatingip_100005')
        else:
            ips = [ip['ip_address'] for ip in internal_port['fixed_ips']]
            if not ips:
                msg = (_('Cannot add floating IP to port %s that has'
                         'no fixed IP addresses') % internal_port['id'])
                raise n_exc.BadRequest(resource='floatingip', msg=msg, gcloud_code='neutron_server_floatingip_100006')
            if len(ips) > 1:
                msg = (_('Port %s has multiple fixed IPs.  Must provide'
                         ' a specific IP when assigning a floating IP') %
                       internal_port['id'])
                raise n_exc.BadRequest(resource='floatingip', msg=msg, gcloud_code='neutron_server_floatingip_100007')
            internal_ip_address = internal_port['fixed_ips'][0]['ip_address']
            internal_subnet_id = internal_port['fixed_ips'][0]['subnet_id']
        return internal_port, internal_subnet_id, internal_ip_address

    def get_assoc_data(self, context, fip, floating_network_id):
        """Determine/extract data associated with the internal port.

        When a floating IP is associated with an internal port,
        we need to extract/determine some data associated with the
        internal port, including the internal_ip_address, and router_id.
        The confirmation of the internal port whether owned by the tenant who
        owns the floating IP will be confirmed by _get_router_for_floatingip.
        """
        (internal_port, internal_subnet_id,
         internal_ip_address) = self._internal_fip_assoc_data(context, fip)
        router_id = self._get_router_for_floatingip(context,
                                                    internal_port,
                                                    internal_subnet_id,
                                                    floating_network_id)

        return (fip['port_id'], internal_ip_address, router_id)

    def _check_and_get_fip_assoc(self, context, fip, floatingip_db):
        port_id = internal_ip_address = router_id = None
        if (('fixed_ip_address' in fip and fip['fixed_ip_address']) and
            not ('port_id' in fip and fip['port_id'])):
            msg = _("fixed_ip_address cannot be specified without a port_id")
            raise n_exc.BadRequest(resource='floatingip', msg=msg ,gcloud_code='neutron_server_floatingip_100001')
        if 'port_id' in fip and fip['port_id']:
            port_id, internal_ip_address, router_id = self.get_assoc_data(
                context,
                fip,
                floatingip_db['floating_network_id'])
            fip_qry = context.session.query(FloatingIP)
            try:
                fip_qry.filter_by(
                    fixed_port_id=fip['port_id'],
                    floating_network_id=floatingip_db['floating_network_id'],
                    fixed_ip_address=internal_ip_address).one()
                raise l3.FloatingIPPortAlreadyAssociated(
                    port_id=fip['port_id'],
                    fip_id=floatingip_db['id'],
                    floating_ip_address=floatingip_db['floating_ip_address'],
                    fixed_ip=internal_ip_address,
                    net_id=floatingip_db['floating_network_id'])
            except exc.NoResultFound:
                pass
        return port_id, internal_ip_address, router_id

    def _update_fip_assoc(self, context, fip, floatingip_db, external_port):
        previous_router_id = floatingip_db.router_id
        port_id, internal_ip_address, router_id = (
            self._check_and_get_fip_assoc(context, fip, floatingip_db))
        floatingip_db.update({'fixed_ip_address': internal_ip_address,
                              'fixed_port_id': port_id,
                              'router_id': router_id,
                              'last_known_router_id': previous_router_id})

    #add by xm-2015.6.16- 创建浮动IP时（create_floating_ip）运行指定floating_ip_address参数（"floating_ip_address": "11.11.0.141"）
    # 同时修改neutron/extensions/l3.py:  'allow_post': True,
    def _create_fixed_ips(self, fip):
        res=[]
        subnet_id=fip.get('subnet_id',None)
        f_ip_address = fip.get('floating_ip_address', None)
        if f_ip_address is None and subnet_id is None:
            return attributes.ATTR_NOT_SPECIFIED
        else:
             if f_ip_address:
                 res= [{'ip_address': f_ip_address}]
             if subnet_id:
                 res.append({'subnet_id': subnet_id})
        return res

    def create_floatingip(self, context, floatingip,
            initial_status=l3_constants.FLOATINGIP_STATUS_ACTIVE):

        fip = floatingip['floatingip']
        tenant_id = self._get_tenant_id_for_create(context, fip)
        fip_id = uuidutils.generate_uuid()
        f_net_id = fip['floating_network_id']
        type=fip['type']
        if not self._core_plugin._network_is_external(context, f_net_id):
            msg = _("Network %s is not a valid external network") % f_net_id
            raise n_exc.BadRequest(resource='floatingip', msg=msg ,gcloud_code='neutron_server_floatingip_100002')
        #add date 2015-12-08,alter by 2016/1/18
        subnet_ids=[]#recording  subnet id
        #subnet_id=None
        if type:#according subnet type to find subnets info ,and add subnet id to subnet_ids array
            filters={"type":[type],"network_id":[f_net_id]}
            LOG.debug("filters %r",filters)
            subnets=self._core_plugin.get_subnets(context,filters)
            if subnets:
                for subnet in subnets:
                    subnet_ids.append(subnet.get("id"))
            else:
                msg = _("Network %s is not has type network") % f_net_id
                raise n_exc.BadRequest(resource='floatingip', msg=msg ,gcloud_code='neutron_server_floatingip_100008')
        #subnet_ids=['fedbb546-dbab-4838-852e-f770a52b0995','920df58c-b159-4725-a830-83e6589018d1']
        floatingip_db=None
        count=len(subnet_ids)
        if count>0:# according subnet id to create floating ip port
            for subnet_id in subnet_ids:
                count=count-1
                fip["subnet_id"]=subnet_id
                LOG.debug("subnet_id %s"%(subnet_id))
                try:
                  floatingip_db=self._create_floatingip_internal(context=context,f_net_id=f_net_id,fip=fip,fip_id=fip_id,tenant_id=tenant_id,initial_status=initial_status)
                except :
                  LOG.debug("subnet_id %s is not has not enough ip"%(subnet_id))
                  if count<1:
                     raise n_exc.ExternalIpAddressExhausted(net_id=f_net_id)
                if floatingip_db:
                    break
        else:#this is not  subnet_id
             floatingip_db=self._create_floatingip_internal(context=context,f_net_id=f_net_id,fip=fip,fip_id=fip_id,tenant_id=tenant_id,initial_status=initial_status)
        return self._make_floatingip_dict(floatingip_db)

    def _create_floatingip_internal(self,context,f_net_id,fip,fip_id,tenant_id,initial_status):
        with context.session.begin(subtransactions=True):
                    # This external port is never exposed to the tenant.
                    # it is used purely for internal system and admin use when
                    # managing floating IPs.
                    external_port = self._core_plugin.create_port(context.elevated(), {
                        'port':
                        {'tenant_id': '',  # tenant intentionally not set
                         'network_id': f_net_id,
                         'mac_address': attributes.ATTR_NOT_SPECIFIED,
                         #'fixed_ips': attributes.ATTR_NOT_SPECIFIED,
                         'fixed_ips': self._create_fixed_ips(fip),
                         'admin_state_up': True,
                         'device_id': fip_id,
                         'device_owner': DEVICE_OWNER_FLOATINGIP,
                         'name': ''}})
                    # Ensure IP addresses are allocated on external port
                    if not external_port['fixed_ips']:
                        raise n_exc.ExternalIpAddressExhausted(net_id=f_net_id)

                    floating_fixed_ip = external_port['fixed_ips'][0]
                    floating_ip_address = floating_fixed_ip['ip_address']
                    floatingip_db = FloatingIP(
                        id=fip_id,
                        tenant_id=tenant_id,
                        status=initial_status,
                        floating_network_id=fip['floating_network_id'],
                        floating_ip_address=floating_ip_address,
                        floating_port_id=external_port['id'],
                        type=fip['type'],
                        user_id=context.user) #add by luoyibing 20150901
                    fip['tenant_id'] = tenant_id
                    # Update association with internal port
                    # and define external IP address
                    self._update_fip_assoc(context, fip,
                                           floatingip_db, external_port)
                    context.session.add(floatingip_db)
                    return  floatingip_db

    def _update_floatingip(self, context, id, floatingip):
        fip = floatingip['floatingip']
        with context.session.begin(subtransactions=True):
            floatingip_db = self._get_floatingip(context, id)
            old_floatingip = self._make_floatingip_dict(floatingip_db)
            fip['tenant_id'] = floatingip_db['tenant_id']
            fip['id'] = id
            fip_port_id = floatingip_db['floating_port_id']
            self._update_fip_assoc(context, fip, floatingip_db,
                                   self._core_plugin.get_port(
                                       context.elevated(), fip_port_id))
        return old_floatingip, self._make_floatingip_dict(floatingip_db)

    def _floatingips_to_router_ids(self, floatingips):
        return list(set([floatingip['router_id']
                         for floatingip in floatingips
                         if floatingip['router_id']]))

    def update_floatingip(self, context, id, floatingip):
        _old_floatingip, floatingip = self._update_floatingip(
            context, id, floatingip)
        return floatingip

    def update_floatingip_status(self, context, floatingip_id, status):
        """Update operational status for floating IP in neutron DB."""
        fip_query = self._model_query(context, FloatingIP).filter(
            FloatingIP.id == floatingip_id)
        fip_query.update({'status': status}, synchronize_session=False)

    def _delete_floatingip(self, context, id):
        floatingip = self._get_floatingip(context, id)
        router_id = floatingip['router_id']
        with context.session.begin(subtransactions=True):
            context.session.delete(floatingip)
            self._core_plugin.delete_port(context.elevated(),
                                          floatingip['floating_port_id'],
                                          l3_port_check=False)
        return router_id

    def delete_floatingip(self, context, id):
        self._delete_floatingip(context, id)

    def get_floatingip(self, context, id, fields=None):
        floatingip = self._get_floatingip(context, id)
        #alter by xm at 20160304 for tz project in router_qos
        #before is:
        #return self._make_floatingip_dict(floatingip, fields)
        #change to:
        floating_ip = self._make_floatingip_dict(floatingip, fields=None)
        gcloud_router_qos_plugin = manager.NeutronManager.get_service_plugins().get(service_constants.GCLOUD_ROUTER_QOS)
        if gcloud_router_qos_plugin:
            gcloud_router_qos_plugin.get_floating_router_qos(context, floating_ip=floating_ip)
        return floating_ip
        #end 20160304

    def get_floatingips(self, context, filters=None, fields=None,
                        sorts=None, limit=None, marker=None,
                        page_reverse=False):
        marker_obj = self._get_marker_obj(context, 'floatingip', limit,
                                          marker)
        if filters is not None:
            for key, val in API_TO_DB_COLUMN_MAP.iteritems():
                if key in filters:
                    filters[val] = filters.pop(key)

        #alter by xm at 20160304 for tz project in router_qos
        #before is:
        # return self._get_collection(context, FloatingIP,
        #                             self._make_floatingip_dict,
        #                             filters=filters, fields=fields,
        #                             sorts=sorts,
        #                             limit=limit,
        #                             marker_obj=marker_obj,
        #                             page_reverse=page_reverse)
        #change to:
        floating_ips = self._get_collection(context, FloatingIP,
                                    self._make_floatingip_dict,
                                    filters=filters, fields=fields,
                                    sorts=sorts,
                                    limit=limit,
                                    marker_obj=marker_obj,
                                    page_reverse=page_reverse)
        gcloud_router_qos_plugin = manager.NeutronManager.get_service_plugins().get(service_constants.GCLOUD_ROUTER_QOS)
        if gcloud_router_qos_plugin:
            gcloud_router_qos_plugin.get_floating_router_qoss(context, floating_ips=floating_ips)
        return floating_ips
        #end 20160304

    def get_floating_router_qoss(self, context, res):
        gcloud_router_qos_plugin = manager.NeutronManager.get_service_plugins().get(service_constants.GCLOUD_ROUTER_QOS)
        if gcloud_router_qos_plugin:
            for i in res:
                i.update({"router_qosrule": {"qos_id": "xm_test-qos_id", "max_rate": "xm_test-max_rate"}})
        else:
            LOG.debug(_('No plugin for gcloud_router_qos registered'))

    def delete_disassociated_floatingips(self, context, network_id):
        query = self._model_query(context, FloatingIP)
        query = query.filter_by(floating_network_id=network_id,
                                fixed_port_id=None,
                                router_id=None)
        for fip in query:
            self.delete_floatingip(context, fip.id)

    def get_floatingips_count(self, context, filters=None):
        return self._get_collection_count(context, FloatingIP,
                                          filters=filters)

    def get_userid_floatingips_count(self, context,filter=None):
        session=None
        if context is None:
             session=context.session
        else:
             session = db.get_session()
        with session.begin():
             return session.query(FloatingIP.user_id, func.count('*').label("floatingip_count")).group_by(FloatingIP.user_id).all()

    def prevent_l3_port_deletion(self, context, port_id):
        """Checks to make sure a port is allowed to be deleted.

        Raises an exception if this is not the case.  This should be called by
        any plugin when the API requests the deletion of a port, since some
        ports for L3 are not intended to be deleted directly via a DELETE
        to /ports, but rather via other API calls that perform the proper
        deletion checks.
        """
        port_db = self._core_plugin._get_port(context, port_id)
        if port_db['device_owner'] in self.router_device_owners:
            # Raise port in use only if the port has IP addresses
            # Otherwise it's a stale port that can be removed
            fixed_ips = port_db['fixed_ips']
            if fixed_ips:
                raise l3.L3PortInUse(port_id=port_id,
                                     device_owner=port_db['device_owner'])
            else:
                LOG.debug(_("Port %(port_id)s has owner %(port_owner)s, but "
                            "no IP address, so it can be deleted"),
                          {'port_id': port_db['id'],
                           'port_owner': port_db['device_owner']})

    def disassociate_floatingips(self, context, port_id):
        """Disassociate all floating IPs linked to specific port.

        @param port_id: ID of the port to disassociate floating IPs.
        @param do_notify: whether we should notify routers right away.
        @return: set of router-ids that require notification updates
                 if do_notify is False, otherwise None.
        """
        router_ids = set()

        with context.session.begin(subtransactions=True):
            fip_qry = context.session.query(FloatingIP)
            floating_ips = fip_qry.filter_by(fixed_port_id=port_id)
            for floating_ip in floating_ips:
                router_ids.add(floating_ip['router_id'])
                floating_ip.update({'fixed_port_id': None,
                                    'fixed_ip_address': None,
                                    'router_id': None})
        return router_ids

    ###add by xm at 2015.9.7 for bug 6080 ---begin (no use)
    def delete_floatingips_for_gcloud7(self, context, port_id):
        """floatingips in gcloud7 only have "post and delete", not have "associate and disassociate".

        @param port_id: ID of the port to delete floating IPs.
        """
        with context.session.begin(subtransactions=True):
            fip_qry = context.session.query(FloatingIP)
            floating_ips = fip_qry.filter_by(fixed_port_id=port_id)
            for floating_ip in floating_ips:
                self.delete_floatingip(context, floating_ip.id)

    ###add by xm at 2015.9.7 for bug 6080 ---begin (use)
    def delete_lb_vip_for_gcloud7(self, context, port_id, floatingips=[]):
        """floatingips in gcloud7 only have "post and delete", not have "associate and disassociate".

        @param port_id: ID of the port to delete floating IPs.
        """
        with context.session.begin(subtransactions=True):
            fip_qry = context.session.query(FloatingIP)
            floating_ip = fip_qry.filter_by(fixed_port_id=port_id).first()
        if floating_ip:
            floatingips.insert(0, floating_ip.floating_ip_address)
            raise n_exc.Conflict


    def _build_routers_list(self, context, routers, gw_ports):
        for router in routers:
            gw_port_id = router['gw_port_id']
            # Collect gw ports only if available
            if gw_port_id and gw_ports.get(gw_port_id):
                router['gw_port'] = gw_ports[gw_port_id]
        return routers

    def _get_sync_routers(self, context, router_ids=None, active=None):
        """Query routers and their gw ports for l3 agent.

        Query routers with the router_ids. The gateway ports, if any,
        will be queried too.
        l3 agent has an option to deal with only one router id. In addition,
        when we need to notify the agent the data about only one router
        (when modification of router, its interfaces, gw_port and floatingips),
        we will have router_ids.
        @param router_ids: the list of router ids which we want to query.
                           if it is None, all of routers will be queried.
        @return: a list of dicted routers with dicted gw_port populated if any
        """
        filters = {'id': router_ids} if router_ids else {}
        if active is not None:
            filters['admin_state_up'] = [active]
        router_dicts = self.get_routers(context, filters=filters)
        gw_port_ids = []
        if not router_dicts:
            return []
        for router_dict in router_dicts:
            gw_port_id = router_dict['gw_port_id']
            if gw_port_id:
                gw_port_ids.append(gw_port_id)
        gw_ports = []
        if gw_port_ids:
            gw_ports = dict((gw_port['id'], gw_port)
                            for gw_port in
                            self.get_sync_gw_ports(context, gw_port_ids))
        # NOTE(armando-migliaccio): between get_routers and get_sync_gw_ports
        # gw ports may get deleted, which means that router_dicts may contain
        # ports that gw_ports does not; we should rebuild router_dicts, but
        # letting the callee check for missing gw_ports sounds like a good
        # defensive approach regardless
        return self._build_routers_list(context, router_dicts, gw_ports)

    def _get_sync_floating_ips(self, context, router_ids):
        """Query floating_ips that relate to list of router_ids."""
        if not router_ids:
            return []
        return self.get_floatingips(context, {'router_id': router_ids})

    def get_sync_gw_ports(self, context, gw_port_ids):
        if not gw_port_ids:
            return []
        filters = {'id': gw_port_ids}
        gw_ports = self._core_plugin.get_ports(context, filters)
        if gw_ports:
            self._populate_subnet_for_ports(context, gw_ports)
        return gw_ports

    def get_sync_interfaces(self, context, router_ids, device_owners=None):
        """Query router interfaces that relate to list of router_ids."""
        device_owners = device_owners or [DEVICE_OWNER_ROUTER_INTF]
        if not router_ids:
            return []
        qry = context.session.query(RouterPort)
        qry = qry.filter(
            RouterPort.router_id.in_(router_ids),
            RouterPort.port_type.in_(device_owners)
        )

        # TODO(markmcclain): This is suboptimal but was left to reduce
        # changeset size since it is late in cycle
        ports = [rp.port.id for rp in qry]
        interfaces = self._core_plugin.get_ports(context, {'id': ports})
        if interfaces:
            self._populate_subnet_for_ports(context, interfaces)
        return interfaces

    def _populate_subnet_for_ports(self, context, ports):
        """Populate ports with subnet.

        These ports already have fixed_ips populated.
        """
        if not ports:
            return

        def each_port_with_ip():
            for port in ports:
                fixed_ips = port.get('fixed_ips', [])
                if len(fixed_ips) > 1:
                    LOG.info(_("Ignoring multiple IPs on router port %s"),
                             port['id'])
                    continue
                elif not fixed_ips:
                    # Skip ports without IPs, which can occur if a subnet
                    # attached to a router is deleted
                    ###add by xm for tz project at 2015.12.10
                    #old is:
                    # LOG.info(_("Skipping port %s as no IP is configure on it"), port['id'])
                    #     continue
                    #change to:
                    #when has config allow_gcloud_nat=True in neutron.conf, allow gateway_port no been allocated IP
                    # in this case, add gcloud_nat_flag='yes' in fixed_ips. used for next line 1315
                    if port['device_owner'] == DEVICE_OWNER_ROUTER_GW and cfg.CONF.allow_gcloud_nat:
                        #LOG.debug(_("111111 1281"))
                        fixed_ips = [{"gcloud_nat_flag": "yes"}]
                    else:
                        LOG.info(_("Skipping port %s as no IP is configure on it"), port['id'])
                        continue
                    ###end 2015.12.10
                yield (port, fixed_ips[0])

        network_ids = set(p['network_id'] for p, _ in each_port_with_ip())
        filters = {'network_id': [id for id in network_ids]}
        fields = ['id', 'cidr', 'gateway_ip',
                  'network_id', 'ipv6_ra_mode']

        subnets_by_network = dict((id, []) for id in network_ids)
        for subnet in self._core_plugin.get_subnets(context, filters, fields):
            subnets_by_network[subnet['network_id']].append(subnet)

        for port, fixed_ip in each_port_with_ip():
            port['extra_subnets'] = []
            for subnet in subnets_by_network[port['network_id']]:
                subnet_info = {'id': subnet['id'],
                               'cidr': subnet['cidr'],
                               'gateway_ip': subnet['gateway_ip'],
                               'ipv6_ra_mode': subnet['ipv6_ra_mode']}
                ###alter by xm for tz project at 2015.12.10
                #old is:
                # if subnet['id'] == fixed_ip['subnet_id']:
                #         port['subnet'] = subnet_info
                #     else:
                #         port['extra_subnets'].append(subnet_info)
                #change to:
                #because when allow_gcloud_nat(tz project) and port is gateway_port,
                #the gateway_port can has not be allocated ip, if this: fixed_ip['gcloud_nat_flag'] ='yes'
                #in this case, we used this subnet, first one of the ext-network which has geteway_ip.
                if port['device_owner'] == DEVICE_OWNER_ROUTER_GW and fixed_ip.get("gcloud_nat_flag", None) == "yes":
                    if subnet_info['gateway_ip']:
                        #LOG.info("111111 1317")
                        port['subnet'] = subnet_info
                    else:
                        port['extra_subnets'].append(subnet_info)
                else:
                    if subnet['id'] == fixed_ip['subnet_id']:
                        port['subnet'] = subnet_info
                    else:
                        port['extra_subnets'].append(subnet_info)
                #end 2015.12.10

    def _process_floating_ips(self, context, routers_dict, floating_ips):
        for floating_ip in floating_ips:
            router = routers_dict.get(floating_ip['router_id'])
            if router:
                router_floatingips = router.get(l3_constants.FLOATINGIP_KEY,
                                                [])
                router_floatingips.append(floating_ip)
                router[l3_constants.FLOATINGIP_KEY] = router_floatingips

    def _process_interfaces(self, routers_dict, interfaces):
        for interface in interfaces:
            router = routers_dict.get(interface['device_id'])
            if router:
                router_interfaces = router.get(l3_constants.INTERFACE_KEY, [])
                router_interfaces.append(interface)
                router[l3_constants.INTERFACE_KEY] = router_interfaces

    def _process_floating_ip_qoss(self, routers_dict, floating_ip_qoss):
        if floating_ip_qoss:
            for qos in floating_ip_qoss:
               router = routers_dict.get(qos['router_id'])
               if router:
                  router_qoss = router.get(l3_constants.FLOATING_IP_QOS_KEY, [])
                  router_qoss.append(qos)
                  router[l3_constants.FLOATING_IP_QOS_KEY] = router_qoss

    def _process_gcloud_nats(self, routers_dict, gcloud_nats):
        if gcloud_nats:
            for gcloud_nat in gcloud_nats:
               router = routers_dict.get(gcloud_nat['router_id'])
               if router:
                  gcloud_nats = router.get(l3_constants.GCLOUD_NAT_KEY, [])
                  gcloud_nats.append(gcloud_nat)
                  router[l3_constants.GCLOUD_NAT_KEY] = gcloud_nats

    def _get_router_info_list(self, context, router_ids=None, active=None,
                              device_owners=None):
        """Query routers and their related floating_ips, interfaces."""
        with context.session.begin(subtransactions=True):
            routers = self._get_sync_routers(context,
                                             router_ids=router_ids,
                                             active=active)
            #LOG.debug(_("111111 l3_db.py line 1303 routers=%s"), routers)
            router_ids = [router['id'] for router in routers]
            interfaces = self.get_sync_interfaces(
                context, router_ids, device_owners)
            floating_ips = self._get_sync_floating_ips(context, router_ids)
            for fip in floating_ips:
                fip["cidr"]=self._get_subnet_cidr(context, fip["floating_port_id"])
            #floating_ip_qoss=self._get_floatingip_qoss(context, floating_ips)
            ###add by xm for tz project at 2015.12.11
            gcloud_nat_plugin = manager.NeutronManager.get_service_plugins().get(service_constants.GCLOUD_NAT)
            gcloud_nats = None
            if gcloud_nat_plugin:
                gcloud_nats = gcloud_nat_plugin.get_gcloud_nats_tz(context, router_ids)
            gateway_qoss=self._get_gateway_qoss(context,router_ids)
            #if floating_ip_qoss is None:
            floating_ip_qoss=[]
            #if  gateway_qoss:
            #          floating_ip_qoss.extend(gateway_qoss)

            ###end 2015.12.11
            return (routers, interfaces, floating_ips, floating_ip_qoss, gcloud_nats)
    def _get_gateway_qoss(self,context,router_ids):
        #get gateway port qoss
        floating_ip_qoss=None
        if router_ids:
            portInfo=self._core_plugin.get_ports(context,filters={'device_id':router_ids,"device_owner":["network:router_gateway"]})
            if portInfo:
                gateway_port_infos={portInfo["id"]:portInfo["device_id"] for portInfo  in portInfo}
                floating_ip_qoss= self._get_collection(context, GcloudQueueQos,
                                    self._make_floatingip_qos_dict,
                                    filters={'floating_port_id': gateway_port_infos.keys()}
                                    )
            #add router_info
                if  floating_ip_qoss:
                        for  qos  in floating_ip_qoss:
                           qos["router_id"]=gateway_port_infos.get(qos["floating_port_id"])
        return  floating_ip_qoss

    def _get_floatingip_qoss(self,context,floating_ips=None):
        """
        according floating_port_ids to get floatingip info
        """
        LOG.debug(" %r"%(floating_ips))

        floating_port_infos= {floating_ip["floating_ip_address"]:floating_ip["router_id"] for floating_ip in floating_ips }

        if len(floating_port_infos)==0:
            return None
        floating_ip_qoss= self._get_collection(context, GcloudQueueQos,
                                    self._make_floatingip_qos_dict,
                                    filters={'src_ip': floating_port_infos.keys()}
                                    )
        if floating_ip_qoss:
                for  qos  in floating_ip_qoss:
                 qos["router_id"]=floating_port_infos.get(qos["src_ip"])
        return floating_ip_qoss


    def _get_subnet_cidr(self, context, port_id):
        ob = context.session.query(models_v2.Subnet).join(models_v2.IPAllocation).filter\
            (models_v2.IPAllocation.port_id == port_id).first()
        LOG.debug("kyz %s" %ob)
        if ob:
            return ob.cidr[-2:]
        else:
            return "32"



    def get_router_by_router_id_tz(self, context, router_id):
        router= self._get_router(context, router_id)
        return router

    def update_routerports_table(self, context, router_id=None, port_id=None, subnet_id=None):
        #LOG.debug(_("111111 6666 router_id=%s  port_id=%s"),router_id, port_id)
        routerport_db = self._get_router_port(context, router_id, port_id)
        #LOG.debug(_("111111 7777 routerport_db=%s"), routerport_db)
        routerport_db.update({"subnet_id":subnet_id})
        #LOG.debug(_("111111 8888 routerport_db=%s"), routerport_db)

    def tz_delete_gateway_ip(self, context, gcloud_nat_db, ipallocation):
        router_db =self.get_router_by_router_id_tz(context, gcloud_nat_db["router_id"])
        gw_port_id = router_db["gw_port_id"]
        self.update_routerports_table(context,gcloud_nat_db["router_id"], gw_port_id, subnet_id=None)
        core_plugin = manager.NeutronManager.get_plugin()
        core_plugin.tz_delete_allocated_ips_of_gateway_port(context, ipallocation)

    def get_sync_data(self, context, router_ids=None, active=None):
        routers, interfaces, floating_ips, floating_ip_qoss, gcloud_nats= self._get_router_info_list(
            context, router_ids=router_ids, active=active)
        #LOG.debug(_("111111 l3_db.py line 1332 gcloud_nats=%s"),gcloud_nats)
        routers_dict = dict((router['id'], router) for router in routers)
        self._process_floating_ips(context, routers_dict, floating_ips)
        self._process_interfaces(routers_dict, interfaces)
        self._process_floating_ip_qoss(routers_dict,floating_ip_qoss)
        self._process_gcloud_nats(routers_dict, gcloud_nats)
        return routers_dict.values()

    def delete_floatingIp_qos(self,context,floating_port_id):
         context.session.query(GcloudQueueQos).filter_by(floating_port_id =floating_port_id ).delete()


    def remove_router_gatewayip(self, context, router_id=None):
        #update portp info,delete ip info
      with context.session.begin(subtransactions=True):
        router=self._get_router(context,router_id)
        if router:
            gcloud_natPlugin = manager.NeutronManager.get_service_plugins().get(service_constants.GCLOUD_NAT)
            if  gcloud_natPlugin:
            #delete all nat info,include ip info
                 gcloud_natPlugin.delete_gcloud_nats(context,router_id)
            gcloud_router_qos_plugin = manager.NeutronManager.get_service_plugins().get(service_constants.GCLOUD_ROUTER_QOS)
            if  gcloud_router_qos_plugin:
                router_qosrule_binds=gcloud_router_qos_plugin.get_router_qosrule_binds(context,filters={"port_id":[router["gw_port_id"]]})
                if router_qosrule_binds and len(router_qosrule_binds)>0:
                    gcloud_router_qos_plugin.delete_router_qosrule_bind(context,id=router_qosrule_binds[0]["id"])
            #for ip in router]
            if router.gw_port['fixed_ips'] and len(router.gw_port['fixed_ips'])>0:
               self.tz_delete_gateway_ip(context,gcloud_nat_db={"router_id":router_id},ipallocation=router.gw_port['fixed_ips'][0])
            #delete qos
            #self.delete_floatingIp_qos(context,router["gw_port_id"])
        #notify router info
            self.notify_router_updated(context, router_id, "remove_router_gatewayip", {})


class L3RpcNotifierMixin(object):
    """Mixin class to add rpc notifier attribute to db_base_plugin_v2."""

    @property
    def l3_rpc_notifier(self):
        if not hasattr(self, '_l3_rpc_notifier'):
            self._l3_rpc_notifier = l3_rpc_agent_api.L3AgentNotifyAPI()
        return self._l3_rpc_notifier

    @l3_rpc_notifier.setter
    def l3_rpc_notifier(self, value):
        self._l3_rpc_notifier = value

    def notify_router_updated(self, context, router_id,
                              operation=None, data=None):
        if router_id:
            self.l3_rpc_notifier.routers_updated(
                context, [router_id], operation, data)

    def notify_routers_updated(self, context, router_ids,
                               operation=None, data=None):
        if router_ids:
            self.l3_rpc_notifier.routers_updated(
                context, router_ids, operation, data)

    def notify_router_deleted(self, context, router_id):
        self.l3_rpc_notifier.router_deleted(context, router_id)


class L3_NAT_db_mixin(L3_NAT_dbonly_mixin, L3RpcNotifierMixin):
    """Mixin class to add rpc notifier methods to db_base_plugin_v2."""

    def update_router(self, context, id, router):
        r = router['router']
        payload = {'gw_exists':
                   r.get(EXTERNAL_GW_INFO, attributes.ATTR_NOT_SPECIFIED) !=
                   attributes.ATTR_NOT_SPECIFIED}
        router_dict = super(L3_NAT_db_mixin, self).update_router(context,
                                                                 id, router)
        self.notify_router_updated(context, router_dict['id'], None, payload)
        return router_dict

    def delete_router(self, context, id):
        super(L3_NAT_db_mixin, self).delete_router(context, id)
        self.notify_router_deleted(context, id)

    def notify_router_interface_action(
            self, context, router_interface_info, action):
        l3_method = '%s_router_interface' % action
        super(L3_NAT_db_mixin, self).notify_routers_updated(
            context, [router_interface_info['id']], l3_method,
            {'subnet_id': router_interface_info['subnet_id']})

        mapping = {'add': 'create', 'remove': 'delete'}
        notifier = n_rpc.get_notifier('network')
        router_event = 'router.interface.%s' % mapping[action]
        notifier.info(context, router_event,
                      {'router_interface': router_interface_info})

    def add_router_interface(self, context, router_id, interface_info):
        router_interface_info = super(
            L3_NAT_db_mixin, self).add_router_interface(
                context, router_id, interface_info)
        self.notify_router_interface_action(
            context, router_interface_info, 'add')
        return router_interface_info

    def remove_router_interface(self, context, router_id, interface_info):
        router_interface_info = super(
            L3_NAT_db_mixin, self).remove_router_interface(
                context, router_id, interface_info)
        self.notify_router_interface_action(
            context, router_interface_info, 'remove')
        return router_interface_info

    def create_floatingip(self, context, floatingip,
            initial_status=l3_constants.FLOATINGIP_STATUS_ACTIVE):
        floatingip_dict = super(L3_NAT_db_mixin, self).create_floatingip(
            context, floatingip, initial_status)
        router_id = floatingip_dict['router_id']
        self.notify_router_updated(context, router_id, 'create_floatingip', {})
        return floatingip_dict

    def update_floatingip(self, context, id, floatingip):
        old_floatingip, floatingip = self._update_floatingip(
            context, id, floatingip)
        router_ids = self._floatingips_to_router_ids(
            [old_floatingip, floatingip])
        super(L3_NAT_db_mixin, self).notify_routers_updated(
            context, router_ids, 'update_floatingip', {})
        return floatingip
    def update_floatingip_qos(self, context,id,floatingip_qos):
        floatingip_qos= floatingip_qos['floatingip_qos']
        floatingip_qos["floating_port_id"]=floating_port_id=id
        change=False
        router_id=None
        with context.session.begin(subtransactions=True):
             #get floating_ip_port_id in floatingip_queue_qos
             #LOG.debug(" 0")
             qos=self._get_floatingip_qos(context,floating_port_id)
             #if has ,update
             if qos:
                  if qos["max_rate"]!=floatingip_qos["max_rate"]:
                        LOG.debug(" floating qos is exist,now update floating src %s ,max_rate %d"%(qos["src_ip"],floatingip_qos["max_rate"]))
                        qos["max_rate"]=floatingip_qos["max_rate"]
                        qos.update(qos)
                        change=True
                        floatingipInfo= context.session.query(FloatingIP).filter_by(floating_port_id =floatingip_qos['floating_port_id'] ).first()
                        if floatingipInfo:
                              router_id=floatingipInfo["router_id"]
                        else:
                            #support gateway id
                             portInfo= context.session.query(models_v2.Port).filter_by(id =floatingip_qos['floating_port_id'] ).first()
                             if portInfo:
                                 LOG.debug("update gateway qos,routerId %s",portInfo["device_id"])
                                 router_id=portInfo["device_id"]
                  floatingip_qos=qos
             #if has no,create
             else:
                #first check  floatingip.and get range classid ,annd create tables record

               floatingipInfo= context.session.query(FloatingIP).filter_by(floating_port_id =floatingip_qos['floating_port_id'] ).first()
               if floatingipInfo:#floatingIp

                    floatingip_qos["class_id"]=None
                    floatingip_qos["src_ip"]=floatingipInfo["floating_ip_address"]
                    floatingipModel=GcloudQueueQos(src_ip= floatingip_qos["src_ip"],
                                                   floating_port_id=floatingip_qos['floating_port_id'],
                                                   max_rate=floatingip_qos["max_rate"],
                                                   min_rate=None)

                    LOG.debug(" add floating ip qos,src_ip %s,max_rate %d"%(floatingip_qos["src_ip"],floatingip_qos["max_rate"]))
                    context.session.add(floatingipModel)
                    change=True
                    router_id=floatingipInfo["router_id"]
               else: #gateway
                     portInfo= context.session.query(models_v2.Port).filter_by(id =floatingip_qos['floating_port_id'] ).first()
                     if  portInfo:
                           #get src_ip
                           ipAllocation=context.session.query(models_v2.IPAllocation).filter_by(port_id =floatingip_qos['floating_port_id'] ).first()
                           floatingip_qos["src_ip"]=ipAllocation["ip_address"]
                           floatingipModel=GcloudQueueQos(src_ip= floatingip_qos["src_ip"],
                                                   floating_port_id=floatingip_qos['floating_port_id'],
                                                   max_rate=floatingip_qos["max_rate"],
                                                   min_rate=None)
                           context.session.add(floatingipModel)
                           change=True
                           router_id=portInfo["device_id"]
                     else:#not find port_id
                        LOG.debug("port_id %s  is not exist in port infos"%(floating_port_id))
                        return {}
        if change:
                #get router_id
                if  router_id:
                    LOG.debug(" update router_id %s "%(router_id))
                    self.notify_router_updated(context,router_id,"update_floating_ip_qos",{})
        return self._make_floatingip_qos_dict(floatingip_qos)

    def delete_floatingip(self, context, id):
        router_id = self._delete_floatingip(context, id)
        self.notify_router_updated(context, router_id, 'delete_floatingip', {})

    def disassociate_floatingips(self, context, port_id, do_notify=True):
        """Disassociate all floating IPs linked to specific port.

        @param port_id: ID of the port to disassociate floating IPs.
        @param do_notify: whether we should notify routers right away.
        @return: set of router-ids that require notification updates
                 if do_notify is False, otherwise None.
        """
        router_ids = super(L3_NAT_db_mixin, self).disassociate_floatingips(
            context, port_id)
        if do_notify:
            self.notify_routers_updated(context, router_ids)
            # since caller assumes that we handled notifications on its
            # behalf, return nothing
            return

        return router_ids

    def notify_routers_updated(self, context, router_ids):
        super(L3_NAT_db_mixin, self).notify_routers_updated(
            context, list(router_ids), 'disassociate_floatingips', {})

    #add by xm-20150528-for _make_subnet_dict()/_get_routers_by_subnet_id
    def _get_routers_by_subnet_id(self, subnet_id):
        routers = []
        session = db.get_session()
        query = session.query(RouterPort).filter_by(subnet_id=subnet_id)
        records = query.all()
        if records:
            for record in records:
                query_router = session.query(Router).filter_by(id=record.router_id).first()
                router = {"router_id": record.router_id, "router_name": query_router.name}
                routers.append(router)
        return routers


    def  create_router_gatewayip(self,context,router_id,gateway_info):
        LOG.debug("create_router_gatewayip  called in router_id=%s gateway_info=%s" % (router_id, gateway_info))
        #get router_id router associated network id
        with context.session.begin(subtransactions=True):
            router=self._get_router(context, router_id)
            fixed_ips=router.gw_port["fixed_ips"]
            if fixed_ips and len(fixed_ips)>0:
                return self._make_gatewayip_dict(context,router_id)
            #gw_port = router.gw_port
            gw_port=manager.NeutronManager.get_plugin().get_port(context,id=router.gw_port["id"])
            LOG.debug("create_router_gatewayip  gw_port=%s" % (gw_port))
            gw_port_id = gw_port["id"]
            type=gateway_info["type"]
            network_id=gw_port["network_id"]
            #according network id and operate type to get subnet
            subnets=manager.NeutronManager.get_plugin().get_subnets(context,filters={"type": [type], "network_id": [network_id]})
            LOG.debug("create_router_gatewayip subnets=%s" % (subnets))
            if subnets is None or len(subnets)==0:
                  msg = _("Network %s is not has type network") % network_id
                  raise n_exc.BadRequest(resource='floatingip', msg=msg ,gcloud_code='neutron_server_floatingip_100008')
            count=0
            for subnet in subnets:
                try:
                  subnet_id=subnet["id"]
                  gw_port.update({"flag_tz_branch": "allocate_ip_by_subnet_id"})
                  gw_port.update({"fixed_ips":[{"subnet_id":subnet_id}]})
                  ips=manager.NeutronManager.get_plugin().tz_allocate_ips_for_gateway_port(context, gw_port, flag=False)
                  self.update_routerports_table(context, router_id=router_id, port_id=gw_port['id'], subnet_id=ips[0]['subnet_id'])
                  break;
                except :
                    LOG.debug("subnet_id %s is not has not enough ip"%(subnet_id))
                count = count+1
            if count >= len(subnets):
                 raise n_exc.ExternalIpAddressExhausted(net_id=network_id)
        return self._make_gatewayip_dict(context,router_id)


    def _make_gatewayip_dict(self,context,router_id):
        res={}
        router=self._get_router(context,router_id)
        res["router_id"]=router_id
        gw_port=router.gw_port
        res["port_id"]=gw_port["id"]
        fixed_ips=gw_port["fixed_ips"]
        if fixed_ips and len(fixed_ips)>0:
             res["subnet_id"]=fixed_ips[0].subnet_id
             res["ip_address"]=fixed_ips[0].ip_address
             subnet=manager.NeutronManager.get_plugin().get_subnet(context,id=res["subnet_id"])
             res["type"]=subnet["type"]
        res["network_id"]=gw_port["network_id"]


        return res

    def  get_router_gatewayip(self, context, router_id):
        return self._make_gatewayip_dict(context,router_id)
