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

from heat.engine import attributes
from heat.engine import properties
from heat.engine.resources.neutron import neutron
from heat.engine.resources.neutron import port
from heat.engine.resources.neutron import router
from heat.engine import support


class FloatingIP(neutron.NeutronResource):
    PROPERTIES = (
        FLOATING_NETWORK_ID, FLOATING_NETWORK,
        VALUE_SPECS, PORT_ID, FIXED_IP_ADDRESS,
        FLOATING_IP_ADDRESS
    ) = (
        'floating_network_id', 'floating_network',
        'value_specs', 'port_id', 'fixed_ip_address',
        'floating_ip_address',
    )

    ATTRIBUTES = (
        ROUTER_ID, TENANT_ID, FLOATING_NETWORK_ID_ATTR, FIXED_IP_ADDRESS_ATTR,
        FLOATING_IP_ADDRESS_ATTR, PORT_ID_ATTR, SHOW,
    ) = (
        'router_id', 'tenant_id', 'floating_network_id', 'fixed_ip_address',
        'floating_ip_address', 'port_id', 'show',
    )

    properties_schema = {
        FLOATING_NETWORK_ID: properties.Schema(
            properties.Schema.STRING,
            support_status=support.SupportStatus(
                support.DEPRECATED,
                _('Use property %s.') % FLOATING_NETWORK),
            required=False
        ),
        FLOATING_NETWORK: properties.Schema(
            properties.Schema.STRING,
            _('Network to allocate floating IP from.'),
            required=False
        ),
        VALUE_SPECS: properties.Schema(
            properties.Schema.MAP,
            _('Extra parameters to include in the "floatingip" object in the '
              'creation request. Parameters are often specific to installed '
              'hardware or extensions.'),
            default={}
        ),
        PORT_ID: properties.Schema(
            properties.Schema.STRING,
            _('ID of an existing port with at least one IP address to '
              'associate with this floating IP.'),
            update_allowed=True
        ),
        FIXED_IP_ADDRESS: properties.Schema(
            properties.Schema.STRING,
            _('IP address to use if the port has multiple addresses.'),
            update_allowed=True
        ),
        FLOATING_IP_ADDRESS: properties.Schema(
            properties.Schema.STRING,
            _('Fixed Floating Ip Address.'),
            update_allowed=True
        ),
    }

    attributes_schema = {
        ROUTER_ID: attributes.Schema(
            _('ID of the router used as gateway, set when associated with a '
              'port.')
        ),
        TENANT_ID: attributes.Schema(
            _('The tenant owning this floating IP.')
        ),
        FLOATING_NETWORK_ID_ATTR: attributes.Schema(
            _('ID of the network in which this IP is allocated.')
        ),
        FIXED_IP_ADDRESS_ATTR: attributes.Schema(
            _('IP address of the associated port, if specified.')
        ),
        FLOATING_IP_ADDRESS_ATTR: attributes.Schema(
            _('The allocated address of this IP.')
        ),
        PORT_ID_ATTR: attributes.Schema(
            _('ID of the port associated with this IP.')
        ),
        SHOW: attributes.Schema(
            _('All attributes.')
        ),
    }

    def add_dependencies(self, deps):
        super(FloatingIP, self).add_dependencies(deps)

        for resource in self.stack.itervalues():
            # depend on any RouterGateway in this template with the same
            # network_id as this floating_network_id
            if resource.has_interface('OS::Neutron::RouterGateway'):
                gateway_network = resource.properties.get(
                    router.RouterGateway.NETWORK) or resource.properties.get(
                        router.RouterGateway.NETWORK_ID)
                floating_network = self.properties.get(
                    self.FLOATING_NETWORK) or self.properties.get(
                        self.FLOATING_NETWORK_ID)
                if gateway_network == floating_network:
                    deps += (self, resource)

            # depend on any RouterInterface in this template which interfaces
            # with the same subnet that this floating IP's port is assigned
            # to
            elif resource.has_interface('OS::Neutron::RouterInterface'):

                def port_on_subnet(resource, subnet):
                    if not resource.has_interface('OS::Neutron::Port'):
                        return False
                    for fixed_ip in resource.properties.get(
                            port.Port.FIXED_IPS):

                        port_subnet = (
                            fixed_ip.get(port.Port.FIXED_IP_SUBNET)
                            or fixed_ip.get(port.Port.FIXED_IP_SUBNET_ID))
                        return subnet == port_subnet
                    return False

                interface_subnet = (
                    resource.properties.get(router.RouterInterface.SUBNET) or
                    resource.properties.get(router.RouterInterface.SUBNET_ID))
                for d in deps.graph(self):
                    if port_on_subnet(d, interface_subnet):
                        deps += (self, resource)
                        break

    def validate(self):
        super(FloatingIP, self).validate()
        self._validate_depr_property_required(
            self.properties, self.FLOATING_NETWORK, self.FLOATING_NETWORK_ID)

    def handle_create(self):

        props = self.prepare_properties(
            self.properties,
            self.physical_resource_name())
        self.client_plugin().resolve_network(props, self.FLOATING_NETWORK,
                                             'floating_network_id')
        #add start by zhangyk
        if "floating_ip_address" in props:
            if props['floating_ip_address'] == "auto":
                props.pop("floating_ip_address")
         #add  end
        try:
            fip = self.neutron().create_floatingip({
            'floatingip': props})['floatingip']
            self.resource_id_set(fip['id'])
        except Exception,e:
             self.stack.error_codes.append('heat_server_task_00003')
             raise  e

    def _show_resource(self):
        return self.neutron().show_floatingip(self.resource_id)['floatingip']

    def handle_delete(self):
        client = self.neutron()
        try:
            client.delete_floatingip(self.resource_id)
        except Exception as ex:
            #self.stack.error_codes.append('heat_server_task_00004')
            self.client_plugin().ignore_not_found(ex)

    def handle_update(self, json_snippet, tmpl_diff, prop_diff):
        if prop_diff:
            neutron_client = self.neutron()

            port_id = prop_diff.get(self.PORT_ID,
                                    self.properties.get(self.PORT_ID))

            fixed_ip_address = prop_diff.get(
                self.FIXED_IP_ADDRESS,
                self.properties.get(self.FIXED_IP_ADDRESS))

            request_body = {
                'floatingip': {
                    'port_id': port_id,
                    'fixed_ip_address': fixed_ip_address}}

            neutron_client.update_floatingip(self.resource_id, request_body)


class FloatingIPAssociation(neutron.NeutronResource):
    PROPERTIES = (
        FLOATINGIP_ID, PORT_ID, FIXED_IP_ADDRESS,
    ) = (
        'floatingip_id', 'port_id', 'fixed_ip_address',
    )

    properties_schema = {
        FLOATINGIP_ID: properties.Schema(
            properties.Schema.STRING,
            _('ID of the floating IP to associate.'),
            required=True,
            update_allowed=True
        ),
        PORT_ID: properties.Schema(
            properties.Schema.STRING,
            _('ID of an existing port with at least one IP address to '
              'associate with this floating IP.'),
            required=True,
            update_allowed=True
        ),
        FIXED_IP_ADDRESS: properties.Schema(
            properties.Schema.STRING,
            _('IP address to use if the port has multiple addresses.'),
            update_allowed=True
        ),
    }

    def handle_create(self):
        props = self.prepare_properties(self.properties, self.name)

        floatingip_id = props.pop(self.FLOATINGIP_ID)

        self.neutron().update_floatingip(floatingip_id, {
            'floatingip': props})['floatingip']
        self.resource_id_set('%s:%s' % (floatingip_id, props[self.PORT_ID]))

    def handle_delete(self):
        if not self.resource_id:
            return
        client = self.neutron()
        (floatingip_id, port_id) = self.resource_id.split(':')
        try:
            client.update_floatingip(
                floatingip_id,
                {'floatingip': {'port_id': None}})
        except Exception as ex:
            self.client_plugin().ignore_not_found(ex)

    def handle_update(self, json_snippet, tmpl_diff, prop_diff):
        if prop_diff:
            (floatingip_id, port_id) = self.resource_id.split(':')
            neutron_client = self.neutron()
            # if the floatingip_id is changed, disassociate the port which
            # associated with the old floatingip_id
            if self.FLOATINGIP_ID in prop_diff:
                try:
                    neutron_client.update_floatingip(
                        floatingip_id,
                        {'floatingip': {'port_id': None}})
                except Exception as ex:
                    self.client_plugin().ignore_not_found(ex)

            # associate the floatingip with the new port
            floatingip_id = (prop_diff.get(self.FLOATINGIP_ID) or
                             floatingip_id)
            port_id = prop_diff.get(self.PORT_ID) or port_id

            fixed_ip_address = (prop_diff.get(self.FIXED_IP_ADDRESS) or
                                self.properties.get(self.FIXED_IP_ADDRESS))

            request_body = {
                'floatingip': {
                    'port_id': port_id,
                    'fixed_ip_address': fixed_ip_address}}

            neutron_client.update_floatingip(floatingip_id, request_body)
            self.resource_id_set('%s:%s' % (floatingip_id, port_id))


def resource_mapping():
    return {
        'OS::Neutron::FloatingIP': FloatingIP,
        'OS::Neutron::FloatingIPAssociation': FloatingIPAssociation,
    }
