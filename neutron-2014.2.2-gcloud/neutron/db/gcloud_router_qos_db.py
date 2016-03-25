# -*- coding:utf-8 -*-
__author__ = 'luoyb'
import sqlalchemy as sa
from neutron.db import model_base
from neutron.db import models_v2
from neutron.openstack.common import log as logging
from neutron.db import common_db_mixin as base_db
from neutron.extensions import gcloud_router_qos
from sqlalchemy.orm import exc
from neutron.openstack.common import uuidutils

LOG = logging.getLogger(__name__)

class GcloudRouterQos(model_base.BASEV2, models_v2.HasId, models_v2.HasUserId,models_v2.HasCreateTime, models_v2.HasTenant):
    """Represents a  Router Qos .

    This class is desgin for tengzheng project at 2016.3.2.
    """

    __tablename__ = 'gcloud_router_qoss'

    name = sa.Column(sa.String(length=36), server_default=sa.text(u"''"), nullable=True)
    type = sa.Column(sa.String(length=36), nullable=True)
    max_rate = sa.Column(sa.BIGINT(), autoincrement=False, nullable=False)

class GcloudRouterQosRule(model_base.BASEV2,models_v2.HasId,models_v2.HasCreateTime):
    __tablename__ = 'gcloud_router_qosrules'

    name = sa.Column( sa.String(length=36), server_default=sa.text(u"''"), nullable=True)
    max_rate = sa.Column(sa.BIGINT(), autoincrement=False, nullable=False)
    qos_id=sa.Column(sa.String(36), sa.ForeignKey('gcloud_router_qoss.id', ondelete="CASCADE"))

class GcloudRouterQosRuleBind(model_base.BASEV2,models_v2.HasId,models_v2.HasCreateTime,models_v2.HasUserId):
    __tablename__ = 'gcloud_router_qosrule_binds'

    qos_id = sa.Column(sa.String(36), sa.ForeignKey('gcloud_router_qoss.id', ondelete="CASCADE"),nullable=False)
    rule_id = sa.Column(sa.String(length=36), sa.ForeignKey('gcloud_router_qosrules.id',ondelete="CASCADE") ,nullable=False)
    src_ip = sa.Column(sa.String(length=32), nullable=False)
    ip_type = sa.Column(sa.String(length=26), nullable=False)
    port_id = sa.Column(sa.String(length=36), sa.ForeignKey('ports.id', ondelete="CASCADE"),nullable=False)

class  GcloudRouterQosmixin(base_db.CommonDbMixin,gcloud_router_qos.GcloudRouterQosPluginBase):
    def _make_router_qos_dict(self, router_qos,fields=None):
        res = {'id': router_qos['id'],
               'name': router_qos['name'],
               'type':router_qos['type'],
               'max_rate':router_qos['max_rate'],
               'user_id':router_qos['user_id'],
               'tenant_id':router_qos['tenant_id'],
               'create_time':router_qos['create_time']
               }
        #LOG.debug("res %r"%(res))
        return self._fields(res,fields=None)

    def _make_router_qosrule_bind_dict(self,router_qosrule_bind,fields=None):
          res = {'id': router_qosrule_bind['id'],
               'ip_type':router_qosrule_bind['ip_type'],
               'user_id':router_qosrule_bind['user_id'],
               'src_ip':router_qosrule_bind['src_ip'],
               'qos_id':router_qosrule_bind['qos_id'],
               'rule_id':router_qosrule_bind['rule_id'],
               'create_time':router_qosrule_bind['create_time'],
                'port_id':router_qosrule_bind['port_id']
               }
          return self._fields(res, fields)


    def _make_router_qosrule_dict(self, router_qosrule ,fields=None):
        res = {'id': router_qosrule['id'],
               'name': router_qosrule['name'],
               'max_rate':router_qosrule['max_rate'],
               'qos_id':router_qosrule['qos_id']
               }
        return self._fields(res, fields)
    def _get_qosrule_by_id(self,context,rule_id):
        try:
            return self._get_by_id(context,GcloudRouterQosRule,id=rule_id)
        except exc.NoResultFound:
            raise gcloud_router_qos.RouterQosRuleNotFound(id=rule_id)




    def create_router_qos(self, context, router_qos):
        """
        :param router_qos: "router_qos":{"***":"",*******}
        :return:{*****}
        """
        LOG.debug(_("create_router_qos() called"))
        LOG.debug(_("input %r called" %(router_qos)))
        router_qos_value=router_qos["router_qos"]

        with context.session.begin(subtransactions=True):
            router_qos_db = GcloudRouterQos(id=uuidutils.generate_uuid(),
                                   tenant_id=context.tenant_id,
                                   name=router_qos_value['name'],
                                   type=router_qos_value['type'],
                                   max_rate=router_qos_value['max_rate'],
                                   user_id=context.user)
            context.session.add(router_qos_db)
        return self._make_router_qos_dict(router_qos_db)

    def _get_router_qos_by_id(self,context,id):

        try:
            return self._get_by_id(context,GcloudRouterQos,id)
        except exc.NoResultFound:
            raise gcloud_router_qos.RouterQosNotFound(id=id)
    def get_router_qos(self,context,id,fields=None):
        """

        :param context:
        :param id:
        :return:{*****}
        """
        LOG.debug(_("get_router_qos() called"))
        router_qos= self._get_router_qos_by_id(context=context,id=id)
        return self._make_router_qos_dict(router_qos)

    def update_router_qos(self, context,id,router_qos):
        """

        :param context:
        :param id:
        :param router_qos:
        :return:
        """
        LOG.debug(_("update_router_qos() called"))
        router_qos = router_qos['router_qos']
        with context.session.begin(subtransactions=True):
            count = context.session.query(GcloudRouterQos).filter_by(id=id).update(router_qos)
            if not count:
                 raise gcloud_router_qos.RouterQosNotFound(id=id)
        return self.get_router_qos(context,id)

    def update_router_qosrule(self, context,id,router_qosrule):
        """

        :param context:
        :param id:
        :param router_qos:
        :return:
        """
        LOG.debug(_("update_router_qosrule() called"))
        router_qosrule = router_qosrule['router_qosrule']
        with context.session.begin(subtransactions=True):
            count = context.session.query(GcloudRouterQosRule).filter_by(id=id).update(router_qosrule)
            if not count:
                 raise gcloud_router_qos.RouterQosRuleNotFound(rule_id=id)
        return self.get_router_qosrule(context,id)


    def get_router_qoss(self, context, filters=None, fields=None, sorts=None, limit=None, marker=None,
                        page_reverse=False,offset=None):
        """

        :param context:
        :param filters:
        :param fields:
        :param sorts:
        :param limit:
        :param marker:
        :param page_reverse:
        :return:
        """
        LOG.debug(_("get_router_qoss() called"))
        return self._get_collection(context,GcloudRouterQos,self._make_router_qos_dict,filters=filters,fields=fields,offset=offset)

    def get_router_qoss_count(self, context,filters=None):
        LOG.debug(_("get_router_qoss_count() called"))
        return self._get_collection_count(context,GcloudRouterQos,filters=filters)

    def create_router_qosrule(self, context, router_qosrule):
        LOG.debug(_("create_router_qosrule() called"))
        LOG.debug(_("input %r " %(router_qosrule)))
        router_qosrule_value=router_qosrule["router_qosrule"]

        with context.session.begin(subtransactions=True):
            router_qosrule_db = GcloudRouterQosRule(id=uuidutils.generate_uuid(),
                                   name=router_qosrule_value['name'],
                                   max_rate=router_qosrule_value['max_rate'],
                                   qos_id=router_qosrule_value['qos_id']
                                  )
            context.session.add(router_qosrule_db)
        return self._make_router_qosrule_dict(router_qosrule_db)

    def get_router_qosrule(self,context,id,fields=None):
        router_qosrule=self._get_qosrule_by_id(context,rule_id=id)
        return self._make_router_qosrule_dict(router_qosrule)

    def get_router_qosrules(self, context, filters=None, fields=None, sorts=None, limit=None, marker=None,
                            page_reverse=False,offset=None):
      LOG.debug(_("get_router_qosrules() called"))
      return self._get_collection(context,GcloudRouterQosRule,self._make_router_qosrule_dict,filters=filters,fields=fields,offset=offset)

    def get_router_qosrules_count(self, context, filters=None):
      LOG.debug(_("get_router_qosrules_count() called"))
      self._get_collection_count(context,GcloudRouterQosRule,filters=filters)

    def create_router_qosrule_bind(self, context, router_qosrule_bind):
      LOG.debug(_("create_router_qosrule_bind() called"))
      LOG.debug(_("create_router_qosrule() called"))
      LOG.debug(_("input %r " %(router_qosrule_bind)))
      router_qosrule_bind_value=router_qosrule_bind["router_qosrule_bind"]
      with context.session.begin(subtransactions=True):
            router_qosrule_bind_db = GcloudRouterQosRuleBind(id=uuidutils.generate_uuid(),
                                   qos_id=router_qosrule_bind_value['qos_id'],
                                   rule_id=router_qosrule_bind_value['rule_id'],
                                   src_ip=router_qosrule_bind_value['src_ip'],
                                   port_id=router_qosrule_bind_value['port_id'],
                                   user_id=context.user,
                                   ip_type=router_qosrule_bind_value['ip_type']
                                  )
            context.session.add(router_qosrule_bind_db)
      return self._make_router_qosrule_bind_dict(router_qosrule_bind_db)


    def delete_router_qosrule_bind(self, context, id):
        LOG.debug(_("delete_router_qosrule_bind() called"))
        with context.session.begin(subtransactions=True):
            router_qosrule_bind = self._get_router_qosrule_bind(context,id)
            context.session.delete(router_qosrule_bind)
    def delete_router_qos(self, context, id):
        LOG.debug(_("delete_router_qos() called"))
        with context.session.begin(subtransactions=True):
            router_qos = self._get_router_qos_by_id(context,id)
            context.session.delete(router_qos)

    def get_router_qosrule_binds(self, context,filters=None, fields=None,
                        sorts=None, limit=None, marker=None,
                        page_reverse=False,offset=None):
        LOG.debug(_("get_router_qosrule_binds() called"))
        return self._get_collection(context,GcloudRouterQosRuleBind ,self._make_router_qosrule_bind_dict,filters=filters,
                             sorts=sorts, limit=limit,
                              page_reverse=page_reverse,
                                    offset=offset)

    def get_router_qosrule_binds_count(self, context,filters=None):
        LOG.debug(_("get_router_qosrule_binds_count() called"))
        return self._get_collection_count(context,GcloudRouterQosRuleBind,filters=filters)

    def _get_router_qosrule_bind(self,context,id):
        try:
            return self._get_by_id(context,GcloudRouterQosRuleBind,id)
        except exc.NoResultFound:
            raise gcloud_router_qos.RouterQosRuleBindNotFound(id=id)

    def get_router_qosrule_bind(self, context, id, fields=None):
        LOG.debug(_("get_router_qosrule_bind() called"))
        qosrule_bind=self._get_router_qosrule_bind(context,id)
        return self._make_router_qosrule_bind_dict(qosrule_bind)

