# Copyright 2016 OpenStack Foundation
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
#

"""gcloud_router_qos

Revision ID: 50d7f08a4bdb
Revises: feaf26edca9
Create Date: 2016-03-01 09:42:46.781921

"""

# revision identifiers, used by Alembic.
revision = '50d7f08a4bdb'
down_revision = 'feaf26edca9'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('gcloud_router_qoss',
    sa.Column('id', sa.String(length=36), server_default=sa.text(u"''"), nullable=False),
    sa.Column('name', sa.String(length=36), server_default=sa.text(u"''"), nullable=True),
    sa.Column('type', sa.String(length=36), nullable=True),
    sa.Column('max_rate', sa.BIGINT(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.Column('create_time', sa.String(length=26), nullable=False),
    sa.Column('user_id', sa.String(length=64), nullable=False),
    sa.Column('tenant_id', sa.String(length=255), nullable=False)
    )

    op.create_table('gcloud_router_qosrules',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('qos_id', sa.String(length=36), nullable=False),
    sa.Column('max_rate', sa.BIGINT(), autoincrement=False, nullable=False),
    sa.Column('name', sa.String(length=36), nullable=True),
    sa.Column('create_time', sa.String(length=26), nullable=False),
    sa.ForeignKeyConstraint(['qos_id'], [u'gcloud_router_qoss.id'], name=u'gcloud_route_qosrules_ibfk_1', ondelete=u'CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('gcloud_router_qosrule_binds',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('qos_id', sa.String(length=36), nullable=False),
    sa.Column('rule_id', sa.String(length=36), nullable=False),
    sa.Column('src_ip', sa.String(length=32), nullable=False),
    sa.Column('port_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=64), nullable=False),
    sa.Column('create_time', sa.String(length=26), nullable=False),
    sa.Column('ip_type', sa.String(length=26), nullable=False),
    sa.ForeignKeyConstraint(['port_id'], [u'ports.id'], name=u'gcloud_router_qosrule_binds_ibfk_3', ondelete=u'CASCADE'),
    sa.ForeignKeyConstraint(['qos_id'], [u'gcloud_router_qoss.id'], name=u'gcloud_router_qosrule_binds_ibfk_1', ondelete=u'CASCADE'),
    sa.ForeignKeyConstraint(['rule_id'], [u'gcloud_router_qosrules.id'], name=u'gcloud_router_qosrule_binds_ibfk_2', ondelete=u'CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    ### end Alembic commands ###




def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('gcloud_router_qosrule_binds')
    op.drop_table('gcloud_router_qosrules')
    op.drop_table('gcloud_router_qoss')


    ### end Alembic commands ###
