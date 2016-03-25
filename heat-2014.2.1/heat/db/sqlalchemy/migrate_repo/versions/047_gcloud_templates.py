#
#  programmer: zhangyk
#  add time: 2015.5.19

import sqlalchemy

from heat.db.sqlalchemy import types as heat_db_types


def upgrade(migrate_engine):
    meta = sqlalchemy.MetaData()
    meta.bind = migrate_engine

    gcloud_template = sqlalchemy.Table(
        'gcloud_template', meta,
        sqlalchemy.Column('id', sqlalchemy.String(36), primary_key=True,
                          nullable=False),
        sqlalchemy.Column('name', sqlalchemy.String(255)),
        sqlalchemy.Column('created_at', sqlalchemy.DateTime),
        sqlalchemy.Column('updated_at', sqlalchemy.DateTime),
        sqlalchemy.Column('content', sqlalchemy.Text),
        sqlalchemy.Column('nested_content', sqlalchemy.Text),
        sqlalchemy.Column('type', sqlalchemy.String(50)),
        sqlalchemy.Column('creater', sqlalchemy.String(50)),
        sqlalchemy.Column('description', sqlalchemy.String(255)),
        sqlalchemy.Column('isShare', sqlalchemy.Boolean),
        sqlalchemy.Column('creater_id', sqlalchemy.String(36)),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    gcloud_resourcce = sqlalchemy.Table(
        'gcloud_resource', meta,
        sqlalchemy.Column('id', sqlalchemy.String(36), primary_key=True,
                          nullable=False),
        sqlalchemy.Column('gcloud_template_id',
                          sqlalchemy.String(36),
                          sqlalchemy.ForeignKey('gcloud_template.id'),
                          nullable=False),
        sqlalchemy.Column('content', sqlalchemy.Text),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )
    tables = (
        gcloud_template,
        gcloud_resourcce

    )
    for index, table in enumerate(tables):
        try:
            table.create()
        except Exception:
            # If an error occurs, drop all tables created so far to return
            # to the previously existing state.
            meta.drop_all(tables=tables[:index])
            raise


def downgrade(migrate_engine):
    meta = sqlalchemy.MetaData(bind=migrate_engine)
    template_table = sqlalchemy.Table('gcloud_template', meta, autoload=True)
    template_resource = sqlalchemy.Table('gcloud_resource', meta, autoload=True)
    template_resource.drop()
    template_table.drop()



