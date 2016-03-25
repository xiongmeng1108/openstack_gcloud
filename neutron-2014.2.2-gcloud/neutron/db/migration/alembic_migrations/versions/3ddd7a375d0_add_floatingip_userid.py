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

"""add_floatingIp_userId

Revision ID: 3ddd7a375d0
Revises: 1963b9d4f438
Create Date: 2015-09-01 10:44:05.193072

"""

# revision identifiers, used by Alembic.
revision = '3ddd7a375d0'
down_revision = '1963b9d4f438'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


def upgrade():

	op.add_column(
        "floatingips",
         sa.Column('user_id',sa.String(length=64), nullable=True)
         )

def downgrade():
        op.drop_column(
        "floatingips",
        'user_id')
