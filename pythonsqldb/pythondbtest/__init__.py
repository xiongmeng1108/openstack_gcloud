# -*- coding:utf-8 -*-
__author__ = 'luoyb'
from pythondbtest import api
import sys
from oslo.config import cfg
import sqlalchemy as sa

from oslo.db.sqlalchemy import models
from sqlalchemy.ext.declarative import declarative_base

BASEV2 =declarative_base(cls=models.ModelBase)
BASE=declarative_base()
class PortQos(BASEV2):
    """
    define qos
    """
    __tablename__ = 'gcloud_testtable'
    port_id = sa.Column(sa.String(36),
                        nullable=False,primary_key=True)
    ingress = sa.Column(sa.INT(), nullable=True)
    outgress = sa.Column(sa.INT(), nullable=True)


def main():
    #brk(host="10.10.10.20",port=49355)


    cfg.CONF(sys.argv[1:], project='pythondb')


    engine =api.get_engine()
    PortQos.metadata.create_all(engine)#create_table


    session=api.get_session()
    query=session.query(PortQos)
    query=query.order_by('port_id')
    count =query.count()
    print count #满足条件的总记录数目

    query=query.offset(0)#起始位置
    query=query.limit(1)#记录数目
    portQoss=query.all()


    if portQoss:
            for portQos in portQoss:
                print portQos.port_id
    print "success"


if __name__ == "__main__":
    main()