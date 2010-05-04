#!/usr/bin/env python
#-*- coding: ISO-8859-1 -*-

"""
Core class for Data Aggregation Service (DAS) framework.
It performs the following tasks:
- registers data-services found in DAS configuration file (das.cfg).
- invoke data-service subqueries and either multiplex results or
combine them together for presentation layer (CLI or WEB).
- creates DAS views
"""

from __future__ import with_statement

__revision__ = "$Id: das_core.py,v 1.10 2009/05/11 20:18:20 valya Exp $"
__version__ = "$Revision: 1.10 $"
__author__ = "Valentin Kuznetsov"

import re
import os
import time
import types
import traceback

from DAS.core.qlparser import dasqlparser, QLParser
from DAS.core.das_viewmanager import DASViewManager

from DAS.utils.utils import cartesian_product, gen2list
from DAS.utils.das_config import das_readconfig
from DAS.utils.logger import DASLogger

#from DAS.services.dbs.dbs_service import DBSService
#from DAS.services.sitedb.sitedb_service import SiteDBService
#from DAS.services.phedex.phedex_service import PhedexService
#from DAS.services.monitor.monitor_service import MonitorService
#from DAS.services.lumidb.lumidb_service import LumiDBService

#from DAS.services.runsum.runsum_service import RunSummaryService

class DASCore(object):
    """
    DAS core class:
    service_keys = {'service':{list of keys]}
    service_maps = {('service1', 'service2'):'key'}
    """
    def __init__(self, mode=None, debug=None):
        dasconfig    = das_readconfig()
        self.mode    = mode # used to distinguish html vs cli 
        dasconfig['mode'] = mode
        verbose = dasconfig['verbose']
        self.stdout  = debug
        if  type(debug) is types.IntType:
            self.verbose = debug
            dasconfig['verbose'] = debug
            for system in dasconfig['systems']:
                sysdict = dasconfig[system]
                sysdict['verbose'] = debug
        else:
            self.verbose = verbose

        self.logger  = DASLogger(verbose=self.verbose, stdout=debug)
        dasconfig['logger'] = self.logger

        self.viewmgr = DASViewManager()

        self.cache_servers  = dasconfig['cache_servers']
        self.cache_lifetime = dasconfig['cache_lifetime']
        self.couch_servers  = dasconfig['couch_servers']
        self.couch_lifetime = dasconfig['couch_lifetime']

        # plug-in architecture: loop over registered data-services in
        # dasconfig; load appropriate module/class; register data
        # service with DASCore.
        for name in dasconfig['systems']:
            try:
                dasroot = os.environ['DAS_ROOT']
                klass   = 'src/python/DAS/services/%s/%s_service.py'\
                    % (name, name)
                srvfile = os.path.join(dasroot, klass)
                with file(srvfile) as srvclass:
                    for line in srvclass:
                        if  line.find('(DASAbstractService)') != -1:
                            klass = line.split('(DASAbstractService)')[0]
                            klass = klass.split('class ')[-1] 
                            break
                stm = "from DAS.services.%s.%s_service import %s\n" \
                    % (name, name, klass)
                obj = compile(str(stm), '<string>', 'exec')
                eval(obj) # load class def
                klassobj = '%s(dasconfig)' % klass
                setattr(self, name, eval(klassobj))
            except:
                traceback.print_exc()
                msg = "Unable to load %s plugin (%s_service.py)" \
                % (name, name)
                raise Exception(msg)

        # explicit architecture
#        self.dbs     = DBSService(dasconfig)
#        self.sitedb  = SiteDBService(dasconfig)
#        self.phedex  = PhedexService(dasconfig)
#        self.monitor = MonitorService(dasconfig)
#        self.lumidb  = LumiDBService(dasconfig)
#        self.runsum  = RunSummaryService(dasconfig)

        self.service_maps = dasconfig['mapping']
        self.service_keys = {}
        # loop over systems and get system keys,
        # add mapping keys to final list
        for name in dasconfig['systems']: 
            skeys = getattr(self, name).keys()
            for k, v in self.service_maps.items():
                if  list(k).count(name):
                    skeys += [s for s in v if not skeys.count(s)]
            self.service_keys[getattr(self, name).name] = skeys
        self.qlparser = QLParser(self.service_keys)

    def keys(self):
        """
        return map of data service keys
        """
        return self.service_keys

    def plot(self, query):
        """plot data for requested query"""
        results = self.result(query)
        for item in results:
            print item
        return

    def get_view(self, name=None):
        """return DAS view"""
        if  name:
            return self.viewmgr.get(name)
        return self.viewmgr.all()

    def create_view(self, name, query):
        """create DAS view"""
        return self.viewmgr.create(name, query)

    def update_view(self, name, query):
        """update DAS view"""
        return self.viewmgr.update(name, query)

    def delete_view(self, name):
        """delete DAS view"""
        return self.viewmgr.delete(name)

    def viewanalyzer(self, input):
        """
        Simple parser input and look-up if it's view or DAS query
        """
        pat = re.compile('^view')
        if  pat.match(input):
            qlist = input.replace('view ', '').strip().split()
            name  = qlist[0]
            cond  = ''
            if  len(qlist) > 1:
                cond = ' '.join(qlist[1:])
            query = self.viewmgr.get(name) + ' ' + cond
        else:
            query = input
        return query

    def result(self, query):
        """
        Wrap returning results into returning list
        """
        res = [i for i in self.call(query)]
        return res

    def json(self, query):
        """
        Wrap returning results into DAS header and return JSON dict.
        """
        # TODO: replace request_url, version with real values
        init_time   = time.time()

        rdict = {}
        rdict['request_timestamp'] = str(init_time)
        rdict['request_url'] = ''
        rdict['request_version'] = __version__
        rdict['request_expires'] = ''
        rdict['request_call'] = ''
        rdict['call_time'] = ''
        rdict['request_query'] = query

        results  = self.result(query)
        end_time = time.time()

        rdict['call_time'] = str(end_time-init_time)
        rdict['results'] = results
        return rdict

    def call(self, uinput):
        """
        Top level DAS api which execute a given query using underlying
        data-services. It follows the following steps:
        Step 1. identify data-sercices in questions, based on selection keys
                and where clause conditions
        Step 2. construct worksflow and execute data-service calls with found
                sub-queries.
        Step 3. Collect results into service sets, multiplex them together
                using cartesian product, and return result set back to the user
        Return a list of generators containing results for further processing.
        """
        query = self.viewanalyzer(uinput)
        self.logger.info("DASCore::call, user input '%s'" % uinput)
        self.logger.info("DASCore::call, DAS query '%s'" % query)

        params   = self.qlparser.params(query)
        sellist  = params['selkeys']
        ulist    = params['unique_keys']
        services = params['unique_services']
        daslist  = params['daslist']
        self.logger.info('DASCore::call, unique set of keys %s' % ulist)
        self.logger.info('DASCore::call, unique set of services %s' % services)
        # main loop, it goes over query dict in daslist. The daslist
        # contains subqueries (in a form of dict={system:subquery}) to
        # be executed by underlying systems. The number of entreis in daslist
        # is determined by number of logical OR operators which separates
        # conditions applied to data-services. For example, if we have
        # find run where dataset=/a/b/c or hlt=ok we will have 2 entries:
        # - list of runs from DBS
        # - list of runs from run-summary
        # while if we have
        # find run where dataset=/a/b/c/ and hlt=ok we end-up with 1 entry
        # find all runs in DBS and make cartesian product with those found
        # in run-summary.
        for qdict in daslist:
            self.logger.info('DASCore::call, qdict = %s' % str(qdict))
            rdict = {}
            for service in services:
                # find if we already run one service whose results
                # can be used in current one
                cond_dict = self.find_cond_dict(service, rdict)
                if  qdict.has_key(service):
                    squery = qdict[service]
                    res = getattr(getattr(self, service), 'call')\
                                 (squery, ulist, cond_dict)
                    rdict[service] = res
                else:
                    qqq = "find " + ','.join(sellist)
                    res = getattr(getattr(self, service), 'call')\
                                    (qqq, ulist, cond_dict)
                    rdict[service] = res
            # if result dict contains only single result set just return it
            systems = rdict.keys()
            if  len(systems) == 1:
                for entry in rdict[systems[0]]:
                    yield entry
                continue

            # find pairs who has relationships, e.g. (dbs, phedex),
            # and make cartesian product out of them based on found relation keys
            list0 = rdict[systems[0]]
            list1 = rdict[systems[1]]
            idx  = 2
            while 1:
                product = cartesian_product(list0, list1)
                if  idx >= len(systems):
                    break
                list0 = [i for i in product] # may be I should do: list0 = product
                list1 = rdict[systems[idx]]
                idx += 1
            for entry in product:
                yield entry

    def find_cond_dict(self, service, rdict):
        """
        For given service find if it contains in provided result dict
        a key. If so, return a dictionary with values for those found
        keys.
        """
        cond_dict = {}
        if  rdict:
            for key in rdict.keys():
                map1 = (key, service)
                map2 = (service, key)
                for mmm in [map1, map2]:
                    if  self.service_maps.has_key(mmm):
                        skey = self.service_maps[mmm]
                        for skey in self.service_maps[mmm]:
                            prev = list(set(\
                                   [item[skey] for item in rdict[key]\
                                        if item.has_key(skey)]))
                            if  prev:
                                cond_dict[skey] = prev
        return cond_dict

