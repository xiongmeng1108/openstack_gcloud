__author__ = 'luoyb'
import sqlalchemy as sa
from sqlalchemy import orm

from neutron.api.v2 import attributes
from neutron.db import db_base_plugin_v2
from neutron.db import model_base
from neutron.db import models_v2
from neutron.openstack.common import log as logging

from neutron.extensions import gcloud_qos

LOG = logging.getLogger(__name__)


class PortQos(model_base.BASEV2):
    """
    define qos
    """
    __tablename__ = 'gcloud_portqoss'
    port_id = sa.Column(sa.String(36),
                        sa.ForeignKey('ports.id', ondelete="CASCADE"),
                        nullable=False,primary_key=True)
    ingress = sa.Column(sa.BIGINT, nullable=True)
    outgress = sa.Column(sa.BIGINT, nullable=True)


    # Add a relationship to the Port model in order to instruct SQLAlchemy to
    # eagerly load extra_port_qos
    ports = orm.relationship(
        models_v2.Port,
        backref=orm.backref("qos", lazy='joined',uselist=False,cascade='delete'))





class PortQosMixin(object):
    """Mixin class to add extra options to the Qos file
    and associate them to a port.
    """

    def _extend_port_dict_qos(self,res,port):
        port_qos=port.get('qos')
        res['qos']=self._make_port_qos_dict(port_qos)
        return res

    def _get_qos(self,context,port_id):
         port_qos = context.session.query(PortQos).filter_by(port_id=port_id).first()
         return self._make_port_qos_dict(port_qos)

    def _create_or_update_qos(self,context,id,qos):
        if not qos:
            raise "qos is null"
        qos= qos['qos']
        if id:
                qos['port_id']=id
        port= context.session.query(models_v2.Port).filter_by(id = qos['port_id']).first()
        if not port:
            raise gcloud_qos.QosPortNotFound(id = qos['port_id'])
        port_qos=None
        with context.session.begin(subtransactions=True):
              port_qos = context.session.query(PortQos).filter_by(port_id = qos['port_id']).first()
              if port_qos:
                    port_qos.update(qos)
              else:
                    port_qos = PortQos(
                        port_id=qos['port_id'],
                        ingress=qos.get('ingress'),
                        outgress=qos.get('outgress'))
                    context.session.add(port_qos)
        return self._make_port_qos_dict(port_qos)


    def _make_port_qos_dict(self,port_qos):
        res={}
        if port_qos:
             res = {"port_id": port_qos["port_id"],
               'ingress': port_qos['ingress'],
               "outgress": port_qos["outgress"]
              }
        return res

    def update_qos(self, context,id,qos):
        return  self._create_or_update_qos(context,id,qos)



    def create_qos(self, context, qos):
        return self._create_or_update_qos(context=context,id=None,qos=qos)

    def get_qos(self, context, id, fields=None):
        return self._get_qos(context,port_id=id)

    db_base_plugin_v2.NeutronDbPluginV2.register_dict_extend_funcs(
        attributes.PORTS, ['_extend_port_dict_qos'])

