__author__ = 'xm'
from neutron.openstack.common import log
from neutron.db import subnetipinfo_db
from neutron.extensions import gcloud_ipinfo
from neutron.common import topics
from neutron.plugins.ml2 import rpc

LOG = log.getLogger(__name__)

class IpInfoPluginV2(subnetipinfo_db.SubnetIpInfoMixin, gcloud_ipinfo.GcloudIpInfoPluginBase):
    def __init__(self):
        super(IpInfoPluginV2, self).__init__()

    supported_extension_aliases = ["ipinfo"]

    def get_ipinfo(self, context, id, fields=None):
        return super(IpInfoPluginV2, self).get_ipinfo(context, id)

    def get_ipinfos(self, context, filters=None, fields=None,
                    sorts=None, limit=None, marker=None,
                    page_reverse=False, offset=None):
        return super(IpInfoPluginV2, self).get_ipinfos(context, filters=filters, fields=fields,
                    sorts=sorts, limit=limit, marker=marker,
                    page_reverse=page_reverse, offset=offset)
