#!/usr/bin/env python
#-*- coding: ISO-8859-1 -*-

"""
Dashboard service
"""
__revision__ = "$Id"
__version__ = "$Revision"
__author__ = "Valentin Kuznetsov"

import time
import types
import urllib
import xml.etree.cElementTree as ET
from DAS.services.abstract_service import DASAbstractService
from DAS.utils.utils import map_validator, dasheader

def convert_datetime(sec):
    """Convert seconds since epoch to date format used in dashboard"""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(sec))

class DashboardService(DASAbstractService):
    """
    Helper class to provide Dashboard service
    """
    def __init__(self, config):
        DASAbstractService.__init__(self, 'dashboard', config)
        self.headers = {'Accept': 'text/xml'}
        self.map = self.dasmapping.servicemap(self.name)
        map_validator(self.map)

    def parser(self, source, api, params=None):
        """
        Dashboard data-service parser.
        """
        close = False
        if  type(source) is types.InstanceType:
            data = source.read()
            close = True
        else:
            data = source

        try:
            elem  = ET.fromstring(data)
        except:
            print "data='%s'" % data
            raise Exception('Unable to parse dashboard output')
        for i in elem:
            if  i.tag == 'summaries':
                for j in i:
                    row = {}
                    for k in j.getchildren():
                        name = k.tag
                        row[name] = k.text
                    if  params:
                        for key, val in params.items():
                            if  not row.has_key(key):
                                row[key] = val
                    rowkey = self.map[api]['keys'][0]
                    yield {rowkey : row}
        if  close:
            source.close()

    def api(self, query):
        """
        A service worker. It parses input query, invoke service API 
        and return results in a list with provided row.
        """
        api    = self.map.keys()[0] # we have only one key
        url    = self.map[api]['url']
        expire = self.map[api]['expire']
        args   = dict(self.map[api]['params'])
        date1  = time.strftime("%Y-%m-%d %H:%M:%S", \
                 time.gmtime(time.time()-24*60*60))
        date2  = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        args['date1'] = date1
        args['date2'] = date2
        cond   = query['spec']
        for key, value in cond.items():
            if  type(value) is not types.DictType: # we got equal condition
                if  key == 'date':
                    if  type(value) is not types.ListType \
                    and len(value) != 2:
                        msg  = 'Dashboard service requires 2 time stamps.'
                        msg += 'Please use either date last XXh format or'
                        msg += 'date in YYYYMMDD-YYYYMMDD'
                        raise Exception(msg)
                    args['date1'] = convert_datetime(value[0])
                    args['date2'] = convert_datetime(value[1])
                else:
                    for param in self.dasmapping.das2api(self.name, key):
                        args[param] = value
            else: # we got some operator, e.g. key :{'$in' : [1,2,3]}
                # TODO: not sure how to deal with them right now, will throw
                msg = 'JobSummary does not support operator %s' % oper
                raise Exception(msg)

        url = url + '/' + api + '?%s' % urllib.urlencode(args)

        time0 = time.time()
        params = {} # all params are passed in url
        res = self.getdata(url, params, headers=self.headers)
        genrows = self.parser(res, api, args)
        ctime = time.time() - time0
        self.write_to_cache(query, expire, url, api, args, genrows, ctime)
