#add by luoyibing

from oslo.config import cfg


gcloud_identity_report_opts = [
    cfg.StrOpt('admin_tenant_name',
               default="admin",
               help=_('Default admin_tenant_name. ')),
    cfg.IntOpt('report_floatingIp_interval',
               default=60,
               help=_('report monitor secondes .'
                      'A negative value means unlimited.')),
    cfg.StrOpt('admin_user',
               default="admin",
               help=_('Default admin user. ')),
    cfg.StrOpt('admin_password',
               default="gcloud123",
               help=_('Default admin password. ')),
    cfg.StrOpt('region_id',
               default=None,
               help=_('Default region id. ')),

]
cfg.CONF.register_opts(gcloud_identity_report_opts, "gc_identity_report")
