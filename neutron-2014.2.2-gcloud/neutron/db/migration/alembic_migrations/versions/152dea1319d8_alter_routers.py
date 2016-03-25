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

"""alter_routers

Revision ID: 152dea1319d8
Revises: 42662df97563
Create Date: 2015-05-19 14:46:37.882136

"""

# revision identifiers, used by Alembic.
revision = '152dea1319d8'
down_revision = '42662df97563'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "routers",
         sa.Column('create_time', sa.String(length=26), nullable=False)
    )
    op.add_column(
        "routers",
         sa.Column('user_id', sa.String(length=64), nullable=False)
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column(
        "routers",
        'create_time')
    op.drop_column(
        "routers",
        'user_id')
    ### end Alembic commands ###
