__author__ = 'Administrator'


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
import json
from oslo.config import cfg
import  random
import string
import six
import cProfile as profiler
import gc, pstats, time
import json
from sqlalchemy import func, or_, not_, and_
CONF = cfg.CONF

def profile(fn):
    def wrapper(*args, **kw):
        elapsed, stat_loader, result = _profile("/root/foo.txt", fn, *args, **kw)
        stats = stat_loader()
        stats.sort_stats('cumulative')
        stats.print_stats()
        # uncomment this to see who's calling what
        # stats.print_callers()
        return result
    return wrapper

def _profile(filename, fn, *args, **kw):
    load_stats = lambda: pstats.Stats(filename)
    gc.collect()

    began = time.time()
    profiler.runctx('result = fn(*args, **kw)', globals(), locals(),
                    filename=filename)
    ended = time.time()

    return ended - began, load_stats, locals()['result']



def  create_gcloud_template(values):
     fd=db_session.EngineFacade.from_config(CONF)
     gcloud_template=models.Gcloud_template()
     gcloud_template.update(values)
     gcloud_template.save(fd.get_session())
     return  gcloud_template

def test_display():
    fd=db_session.EngineFacade.from_config(CONF)
    session=fd.get_session()
    first=session.query(models.Gcloud_template).first()
    print first.gcloud_resources[0].content
    print  type(first.gcloud_resources[0].content)

def test_delete():
    fd=db_session.EngineFacade.from_config(CONF)
    session=fd.get_session()
    first=session.query(models.Gcloud_template).first()
    session.begin()
    session.delete(first)
    session.commit()
def  test_create():
    resources=[]
    ss={
           "content": {"a":"b"}
      #json.loads('{"name":"kkk","type":"ppp"}')
    }
    ss1={
           "content": {"123":"123"}
      #json.loads('{"name":"kkk","type":"ppp"}')
    }
    gcloud_resource=models.Gcloud_resource()
    gcloud_resource1=models.Gcloud_resource()
    gcloud_resource.update(ss)
    #gcloud_resource1.update(ss1)
    #resources.append(gcloud_resource)
    #resources.append(gcloud_resource1)
    values={
            "name": ''.join(random.sample(string.ascii_letters + string.digits, 8)),
            "content": {"fg":"gf"},
            # json.loads('{"name":"kkk","type":"ppp"}'),
            "description": "hello",
            "isShare": True,
            "type": "deplay",
            "createter": "zyk",
            "createter_id": "fdfsdfsdf",
            "gcloud_resource": gcloud_resource,
            "creater": None




    }
    create_gcloud_template(values)



def  test_query():
   fd=db_session.EngineFacade.from_config(CONF)
   session=fd.get_session()
   ob=session.query(models.Gcloud_template).filter(and_(getattr(models.Gcloud_template, 'name').like("z6%"),
                                                       getattr(models.Gcloud_template, 'creater').like("zyk%"))).all()
   print ob[0].name


def test_get_template():
   fd=db_session.EngineFacade.from_config(CONF)
   session=fd.get_session()
   ob=session.query(models.RawTemplate).filterby(id=10)
   return ob


def filter_result(filters):
   fd=db_session.EngineFacade.from_config(CONF)
   session=fd.get_session()
   #list=[]
   #for key, value   in six.iteritems(filters):
   #     print key ,value
   #     list.append(getattr(models.Gcloud_template, key).like("%s%s" %(value,"%")))
   #ob=session.query(models.Gcloud_template).filter(and_(*list)).all()
   ob=session.query(models.Gcloud_template).filter(
                                              ).all()
   #print  ob[0].name
   for t  in  ob:
       print t.name

def  test_filter(query, filters=None, model=None,join_model=None, part_match="name"):
     if filters:
            filters=filters.copy()
            #support create time filters
            created_time_first=filters.pop("create_time_first",None)
            created_time_end=filters.pop("create_time_end",None)
            if created_time_first or created_time_end :
                #define time range key ,default column name is create_time
                time_range_key=filters.pop("time_range_key",["created_at"])
                column = getattr(model, time_range_key[0], None)
                if column :
                    if created_time_first:
                        query = query.filter(column>=created_time_first)
                    if created_time_end:
                        query = query.filter(column<=created_time_end)


            part_name = filters.pop(part_match, None)
            if join_model:
                query = query.join(join_model)
            query.filter(and_(getattr(model, key) == value for key, value in six.iteritems(filters)))

            if part_name:
                #filter(User.name.like("user%"))
                return query.filter(getattr(models.Stack, part_match).like("%s%s%s" %("%",part_name, "%"))).filter(getattr(models.Stack, "owner_id")== None)
     return  query

import datetime
import time

def test_join():
    fd=db_session.EngineFacade.from_config(CONF)
    session=fd.get_session()
    query= session.query(models.Event).join(models.Event.stack)
    return query.filter_by(name="test12")

def string_toDatetime(string):
    return datetime.datetime.strptime(string, "%Y-%m-%d %H:%M:%S")
def test_list_events():
    fd=db_session.EngineFacade.from_config(CONF)
    session=fd.get_session()
   # "2015-04-13 09:29:47"
    query =  session.query(models.Event)
    filters= {
        "name" : "test",
        "create_time_first": string_toDatetime("2015-05-15 08:29:47"),
        "create_time_end":  string_toDatetime("2015-06-02 08:38:06"),
    }
    query = test_filter(query, filters, models.Event, models.Event.stack,"name")

    query=paginate_query(query, models.Event, limit=10, offset=3)

    for value  in   query:
        print "name %s datetime %s  resource %s "  %(value.stack.name, value.created_at.strftime('%Y-%m-%d %H:%M:%S'), value.resource_name)




def  test_filters(params):
    filter_whitelist = {
            'name': 'mixed',
            'creater': 'mixed',
    }

    filter_result(params)

def model_query( model):
   fd=db_session.EngineFacade.from_config(CONF)
   session=fd.get_session()
   return session.query(model)

def paginate_query(query, model, limit=None, sort_keys=None,
                    marker=None, sort_dir=None, offset=None):
    default_sort_keys = ['created_at']
    if not sort_keys:
        sort_keys = default_sort_keys
        if not sort_dir:
            sort_dir = 'desc'

    # This assures the order of the stacks will always be the same
    # even for sort_key values that are not unique in the database
    sort_keys = sort_keys + ['id']

    model_marker = None
    if marker:
        model_marker = model_query(model).get(marker)

    try:
        query = utils.paginate_query(query, model, None, sort_keys,
                                     model_marker, sort_dir)
        if offset is not None:
            query=query.offset(offset)


    except utils.InvalidSortKey as exc:
        raise exception.Invalid(reason=exc.message)

    if limit is not None:
        return query.limit(limit)

    else:
        return query


def test_offset():
   fd=db_session.EngineFacade.from_config(CONF)
   session=fd.get_session()
   ob=session.query(models.Gcloud_template).offset(20).all()
   for t  in  ob:
       print t.name
def test_page():
    fd=db_session.EngineFacade.from_config(CONF)
    session=fd.get_session()
    query=session.query(models.Gcloud_template)
    query=paginate_query(query, models.Gcloud_template, limit=10, offset=3,sort_keys=["name"])
    for  ob  in  query.all():
        print ob.name

#model, "deleted_at") == None
def test_owner(query, model, user_name_column, user_name, resource_name_column, resource_name):
    ob = query.filter(getattr(model, user_name_column) == user_name)\
        .filter(getattr(model, resource_name_column) == resource_name).\
        filter(getattr(model, "deleted_at") == None).first()
    if ob:
        return True
    else:
        return False
def test():
    fd=db_session.EngineFacade.from_config(CONF)
    session=fd.get_session()
    query=session.query(models.Stack)
    print test_owner(query, models.Stack, "username", "zhangyk", "name", "test123")

def stack_create_test():
    values = {
            'id':'111111',
            'name': "111",
            'raw_template_id': 8,
            'parameters': {"parameters": {"alias": "alias-test11", "hostname": "hostname-test11", "imageId": "imageId-test11"}, "resource_registry": {"resources": {}}},
            'owner_id': "111",
            'username': "111",
            'tenant': "111",
            'action': "CREATE",
            'status': "COMPLETE",
            'status_reason': "111",
            'timeout': 60,
            'disable_rollback': 1,
            'stack_user_project_id': "8bcbc26515234902a12a0185b2a64bdd",
            'updated_at': "2015-06-02 01:42:25",
            'user_creds_id': 8,
            'backup': 0,
            'enduser': "111111111111",
            # 'stack_apps_style': self.stack_apps_style,
            # 'isscaler': self.isscaler,
            # 'description': self.description
            'stack_apps_style': "ssss",
            'isscaler': 1,
            'description': "yyyy"
        }

    fd=db_session.EngineFacade.from_config(CONF)
    stack_ref = models.Stack()
    stack_ref.update(values)
    stack_ref.save(fd.get_session())
    return stack_ref

if __name__=="__main__":
    CONF(project="heat")

    #stack_create_test()
    #query=paginate_query()
    #for  key in  range(30):
    #     test_create()
    #create_gcloud_template(values)
    #test_create()
    #test_display()
    #test_delete()
    #test_query()
    #params={"creater": "zy","name": "26"}
    #test_filters(params)
    #test_query()
    #a=[1,2,2,2,4]
    #ss=[ key*2  for key  in a]
    #print  ss
    #test_offset()
    #test_page()
    #list = model_query(models.Gcloud_template)
    #for  t  in list:
    #   print t.name

    query = test_get_template()
    for value  in  query:
        print  json.dumps(value['files'])
    #test()