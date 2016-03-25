__author__ = 'luoyb'
from neutron.openstack.common import log
from neutron.db import portqos_db
from neutron.extensions import gcloud_qos
from neutron.common import topics
from neutron.plugins.ml2 import rpc

LOG = log.getLogger(__name__)

class QosPluginV2(portqos_db.PortQosMixin,gcloud_qos.GcloudQosPluginBase
                ):
    def __init__(self):
        self._setup_rpc()
    supported_extension_aliases = ["qos"]

    def update_qos(self, context,id, qos):
        qos = super(QosPluginV2,self).update_qos(context,id,qos)
        if qos:
            self._notify_update_qos_if_needed(context,qos)
        return qos

    def create_qos(self, context, qos):
        qos = super(QosPluginV2,self).create_qos(context,qos)
        if qos:
            self._notify_update_qos_if_needed(context,qos)
        return qos

    def get_qos(self, context, id, fields=None):
        return super(QosPluginV2,self).get_qos(context,id)

    def _notify_update_qos_if_needed(self, context,qos):
        self.notifier.qos_update(context, qos)

    def _setup_rpc(self):
        self.notifier = rpc.AgentNotifierApi(topics.AGENT)