#
#  programmer: zyk
#  add time: 2015.09.06

import sqlalchemy

from heat.db.sqlalchemy import types as heat_db_types

def upgrade(migrate_engine):
    meta = sqlalchemy.MetaData()
    meta.bind = migrate_engine
    stack = sqlalchemy.Table('stack', meta, autoload=True)

    template_id = sqlalchemy.Column("template_id", sqlalchemy.String(256))
    template_id.create(stack)

def downgrade(migrate_engine):
    meta = sqlalchemy.MetaData(bind=migrate_engine)
    stack_table = sqlalchemy.Table('stack', meta, autoload=True)
    stack_table.c.template_id.drop()



