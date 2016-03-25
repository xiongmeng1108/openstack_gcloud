from testtools import TestCase
from oslo.config import cfg
from heat.common import context
from heat.db  import api as db_api
from heat.db.sqlalchemy import models
args = ['--config-file', '/etc/heat_test/heat_test.conf']
cfg.CONF(args)
class TestStackDbApi(TestCase):
    _TABLES_ESTABLISHED = False
    def setUp(self):
        super(TestStackDbApi, self).setUp()
        self.context = context.get_admin_context()
        engine = db_api.get_engine()
        if  not TestStackDbApi._TABLES_ESTABLISHED:
            models.BASE.metadata.create_all(engine)
            TestStackDbApi._TABLES_ESTABLISHED = True

        def clear_tables():
             with engine.begin() as conn:
                for table in reversed(
                        models.BASE.metadata.sorted_tables):
                    conn.execute(table.delete())

        self.addCleanup(clear_tables)

    def test_template_create(self):
        values= {
            "content": "abcdefr"
        }
        gcloud_template_resource = models.Gcloud_resource()
        values = {
            "name": "dfdf",
            "content": {"fdfdf":"dfdf"},
            "nested_content": {"asdfg": "ccxcx"},
            "description": "hello",
            "isShare": True,
            "type": "abcd",
            "creater_id": "fdfdf",
            "creater": "fdfsfs",
            "gcloud_resource": gcloud_template_resource
        }
        db_api.template_create(self.context, values)