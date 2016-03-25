from datetime import datetime
from datetime import timedelta
import sys

from oslo.config import cfg
from oslo.db.sqlalchemy import session as db_session
from oslo.db.sqlalchemy import utils
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy.orm.session import Session

from heat.common import crypt
from heat.common import exception
from heat.common.i18n import _
from heat.db.sqlalchemy import filters as db_filters
from heat.db.sqlalchemy import migration
from heat.db.sqlalchemy import models
from heat.rpc import api as rpc_api


"""
stack_ref = models.Stack()
    stack_ref.update(values)
    stack_ref.save(_session(context))
    return stack_ref
"""

