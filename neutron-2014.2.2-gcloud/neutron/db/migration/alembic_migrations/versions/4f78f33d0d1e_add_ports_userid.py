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

"""add_ports_userid

Revision ID: 4f78f33d0d1e
Revises: 6cceab5905b
Create Date: 2015-05-18 10:18:17.844881

"""

# revision identifiers, used by Alembic.
revision = '4f78f33d0d1e'
down_revision = '6cceab5905b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "ports",
         sa.Column('user_id',sa.String(length=64), nullable=True)
    )


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column(
        "ports",
        'user_id')
