# Copyright 2015 OpenStack Foundation
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

"""add_portqos_gcloud-table

Revision ID: 500e4b3ab0cf
Revises: juno
Create Date: 2015-04-29 21:11:57.021479

"""

# revision identifiers, used by Alembic.
revision = '500e4b3ab0cf'
down_revision = 'juno'

from alembic import op
import sqlalchemy as sa




def upgrade():
    op.create_table(
        'gcloud_portqoss',
         sa.Column("port_id",sa.String(36),
                        sa.ForeignKey('ports.id', ondelete="CASCADE"),
                        nullable=False),
         sa.Column("ingress",sa.INT(), nullable=True),
         sa.Column("outgress",sa.INT(), nullable=True),
	 sa.UniqueConstraint('port_id')
    )

def downgrade():
    op.drop_table('portqos_gcloud')
