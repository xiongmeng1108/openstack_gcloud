#
#  programmer: xm
#  add time: 2015.06.02

import sqlalchemy

from heat.db.sqlalchemy import types as heat_db_types


def upgrade(migrate_engine):
    meta = sqlalchemy.MetaData()
    meta.bind = migrate_engine
    stack = sqlalchemy.Table('stack', meta, autoload=True)

    stack_apps_style = sqlalchemy.Column("stack_apps_style", sqlalchemy.String(256))
    stack_apps_style.create(stack)

    isscaler = sqlalchemy.Column("isscaler", sqlalchemy.Boolean, default=False)
    isscaler.create(stack)

    enduser = sqlalchemy.Column("enduser", sqlalchemy.String(255))
    enduser.create(stack)

    description = sqlalchemy.Column("description", sqlalchemy.String(255))
    description.create(stack)

    app_name = sqlalchemy.Column("app_name", sqlalchemy.String(255))
    app_name.create(stack)

def downgrade(migrate_engine):
    meta = sqlalchemy.MetaData(bind=migrate_engine)

    stack_table = sqlalchemy.Table('stack', meta, autoload=True)
    stack_table.c.stack_apps_style.drop()
    stack_table.c.isscaler.drop()
    stack_table.c.enduser.drop()
    stack_table.c.description.drop()
    stack_table.c.app_name.drop()



