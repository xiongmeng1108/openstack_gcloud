__author__ = 'xm'
from neutron.openstack.common import log
from neutron.db import gcloud_nat_db
from neutron.extensions import gcloud_nat
from neutron.common import topics
from neutron.plugins.ml2 import rpc

LOG = log.getLogger(__name__)

class NatPluginV2(gcloud_nat_db.GcloudNatMixin, gcloud_nat.GcloudNatPluginBase):
    def __init__(self):
        super(NatPluginV2, self).__init__()

    supported_extension_aliases = ["gcloud_nat"]

    def get_gcloud_nat(self, context, id, fields=None):
        return super(NatPluginV2, self).get_gcloud_nat(context, id)

    def get_gcloud_nats(self, context, filters=None, fields=None,
                    sorts=None, limit=None, marker=None,
                    page_reverse=False, offset=None):
        return super(NatPluginV2, self).get_gcloud_nats(context, filters=filters, fields=fields,
                    sorts=sorts, limit=limit, marker=marker,
                    page_reverse=page_reverse, offset=offset)

    def create_gcloud_nat(self, context, gcloud_nat):
        return super(NatPluginV2, self).create_gcloud_nat(context, gcloud_nat)

    def update_gcloud_nat(self, context, id, gcloud_nat):
        return super(NatPluginV2, self).update_gcloud_nat(context, id, gcloud_nat)

    def delete_gcloud_nat(self, context, id):
        return super(NatPluginV2, self).delete_gcloud_nat(context, id)
