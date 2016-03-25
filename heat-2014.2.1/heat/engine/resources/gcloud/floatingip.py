# -*- coding:utf-8 -*-
from heat.openstack.common import log as logging
from client import NeutronClient
from heat.engine import properties
from heat.engine.resources.neutron import neutron
from heat.engine import attributes
from heat.engine import resource
LOG = logging.getLogger(__name__)

class FloatingIP(resource.Resource):
    PROPERTIES = (
        FLOATING_NETWORK,
        PORT_ID,
        FLOATING_IP_ADDRESS,
        FIXED_IP_ADDRESS
    ) = (
        'floating_network',
        'port_id',
        'floating_ip_address',
        'fixed_ip_address'
    )
    ATTRIBUTES = (
        FLOATING_IP_ADDRESS_ATTR
    ) = (
        'floating_ip_address',
    )

    properties_schema = {
        FLOATING_NETWORK: properties.Schema(
            properties.Schema.STRING,
            _('Network to allocate floating IP from.'),
            required=True
        ),
        PORT_ID: properties.Schema(
            properties.Schema.STRING,
            _('ID of an existing port with at least one IP address to '
              'associate with this floating IP.'),
            update_allowed=True
        ),
        FLOATING_IP_ADDRESS: properties.Schema(
            properties.Schema.STRING,
            _('Fixed Floating Ip Address.'),
            update_allowed=True
        ),
        FIXED_IP_ADDRESS: properties.Schema(
            properties.Schema.STRING,
            _('IP address to use if the port has multiple addresses.'),
            update_allowed=True
        )
    }

    attributes_schema = {

        FLOATING_IP_ADDRESS_ATTR: attributes.Schema(
            _('The allocated address of this IP.')
        ),

    }

    def __init__(self, name, json_snippet, stack):
        self.client = NeutronClient(stack.context)
        super(FloatingIP, self).__init__(name, json_snippet, stack)

    #创建浮动IP并绑定到port
    def handle_create(self):
        LOG.debug(_("G_Cloud floatingip create and associate"))
        properties = dict()
        for key, value in self.properties.items():
            if key == self.FLOATING_IP_ADDRESS:
                if self.properties[key] != "auto":
                    properties.update({"floatingIpAddress": self.properties[key]})
            if key == self.FLOATING_NETWORK:
                properties.update({"floatingNetworkId": self.properties[key]})
            if key == self.PORT_ID:
                properties.update({"portId": self.properties[key]})
        try:
            floatingip = self.client.create(properties)
            LOG.debug(_("G_Cloud floatingip create and associate %s"),floatingip)
            self.resource_id_set(floatingip['data']['id'])
        except Exception, e:
            self.stack.error_codes.append('heat_server_task_00003')
            LOG.debug(_("G_Cloud floatingip create and associate xxx %s"), e.message)
            raise e
        return floatingip

    #从port上解绑并删除浮动IP
    def handle_delete(self):
        LOG.debug(_("G_Cloud floatingip disassociate and delete"))
        try:
            self.client.delete(self.resource_id)
        except Exception as ex:
            self.stack.error_codes.append('heat_server_task_00004')
            self.client_plugin().ignore_not_found(ex)

    def _resolve_attribute(self, name):
        if name == self.FLOATING_IP_ADDRESS_ATTR:
            try:
                response = self.client.detail(self.resource_id)
                if response['success']:
                    float_ip = response['success']['data']['floatingIpAddress']
                    LOG.debug("the floating ip is %s"  %float_ip)
                    return float_ip
                else:
                    raise Exception("get float ip error")

            except Exception as ex:
                self.stack.error_codes.append('heat_server_task_00003')
                self.client_plugin().ignore_not_found(ex)

def resource_mapping():
    return {
        'OS::G-Cloud::FloatingIP': FloatingIP,
    }
