#!/usr/bin/env python
#-*- coding: ISO-8859-1 -*-

"""
Abstract interface for DAS service
"""
__revision__ = "$Id: abstract_service.py,v 1.56 2009/12/11 16:37:56 valya Exp $"
__version__ = "$Revision: 1.56 $"
__author__ = "Valentin Kuznetsov"

import re
import time
import types
import urllib
import urllib2
import traceback
import DAS.utils.jsonwrapper as json

from DAS.utils.utils import dasheader, getarg, genkey
from DAS.utils.utils import row2das
from DAS.core.das_mongocache import compare_specs

from pymongo import DESCENDING, ASCENDING

class DASAbstractService(object):
    """
    Abstract class describing DAS service. It initialized with a name who
    is used to identify service parameters from DAS configuration file.
    Those parameters are keys, verbosity level, URL of the data-service.
    """
    def __init__(self, name, config):
        self.name = name
        try:
            sdict            = config[name]
            self.verbose     = int(sdict['verbose'])
            self.expire      = int(sdict['expire'])
            self.url         = sdict['url']
            self.logger      = config['logger']
            self.dasmapping  = config['dasmapping']
            self.analytics   = config['dasanalytics']
            self.mongoparser = config['mongoparser']
        except:
            traceback.print_exc()
            print config
            raise Exception('fail to parse DAS config')

        self.map        = {}   # to be defined by data-service implementation
        self._keys      = None # to be defined at run-time in self.keys
        self._params    = None # to be defined at run-time in self.parameters
        self._notations = {}   # to be defined at run-time in self.notations

        msg = 'DASAbstractService::__init__ %s' % self.name
        self.logger.info(msg)
        # define internal cache manager to put 'raw' results into cache
        if  config.has_key('rawcache') and config['rawcache']:
            self.localcache   = config['rawcache']
        else:
            msg = 'Undefined rawcache, please check your configuration'
            raise Exception(msg)

    def version(self):
        """Return data-services version, should be implemented in sub-classes"""
        return ''

    def keys(self):
        """
        Return service keys
        """
        if  self._keys:
            return self._keys
        srv_keys = []
        for api, params in self.map.items():
            for key in params['keys']:
                if  not key in srv_keys:
                    srv_keys.append(key)
        self._keys = srv_keys
        return srv_keys

    def parameters(self):
        """
        Return mapped service parameters
        """
        if  self._params:
            return self._params
        srv_params = []
        for api, params in self.map.items():
            for key in params['params']:
                param_list = self.dasmapping.api2das(self.name, key)
                for par in param_list:
                    if  not par in srv_params:
                        srv_params.append(par)
        self._params = srv_params
        return srv_params

    def notations(self):
        """
        Return a map of system notations.
        """
        if  self._notations:
            return self._notations
        for _, rows in self.dasmapping.notations(self.name).items():
            for row in rows:
                api = row['api']
                name = row['das_name']
                param = row['api_param']
                if  self._notations.has_key(api):
                    self._notations[api].update({param:name})
                else:
                    self._notations[api] = {param:name}
        return self._notations

    def getdata(self, url, params, headers=None):
        """
        Invoke URL call and retrieve data from data-service based
        on provided URL and set of parameters. All data will be parsed
        by data-service parsers to provide uniform JSON representation
        for further processing.
        """
        msg = 'DASAbstractService::%s::getdata(%s, %s)' \
                % (self.name, url, params)
        self.logger.info(msg)
        input_params = params
        # if necessary the data-service implementation will adjust parameters,
        # for instance, DQ need to parse the following input
        # Tracker_Global=GOOD&Tracker_Local1=1
        # into the following form
        # [{"Oper": "=", "Name": "Tracker_Global",  "Value": "GOOD"},...]
        self.adjust_params(params)

        # based on provided interface correctly deal with input parameters
        if  self.name == 'dq':
            encoded_data = json.dumps(params)
        else:
            encoded_data = urllib.urlencode(params, doseq=True)
        req = urllib2.Request(url)
        if  headers:
            for key, val in headers.items():
                req.add_header(key, val)
        if  not encoded_data:
            encoded_data = None
        data = urllib2.urlopen(req, encoded_data)
        return data

    def call(self, query):
        """
        Invoke service API to execute given query.
        Return results as a collect list set.
        """
        msg = 'DASAbstractService::%s::call(%s)' \
                % (self.name, query)
        self.logger.info(msg)

        # check the cache if there are records with given input query
        qhash = genkey(query)
        dasquery = {'spec': {'das.qhash': qhash, 'das.system': self.name}, 
                    'fields': None}
        if  self.localcache.incache(query=dasquery):
            self.analytics.update(self.name, query)
            return
        # check the cache contains records with similar queries
#        if  self.localcache.similar_queries(self.name, query):
#            self.analytics.update(self.name, query)
#            return
        # check the cache if there are records with given parameters
#        if  self.localcache.incache(query=mongo_query):
#            self.analytics.update(self.name, query)
#            return

        # ask data-service api to get results, they'll be store them in
        # cache, so return at the end what we have in cache.
        result = self.api(query)

    def adjust_params(self, args):
        """
        Data-service specific parser to adjust parameters according to
        specifications.
        """
        pass

    def data2das(self, gen, api):
        """
        Convert keys in resulted rows into DAS notations.
        """
        for row in gen:
            row2das(self.dasmapping.notation2das, self.name, api, row)
            yield row

    def insert_apicall(self, url, api, api_params):
        """
        Remove obsolete apicall records and
        insert into Analytics DB provided information about API call.
        """
        spec = {'apicall.expire':{'$lt' : int(time.time())}}
        self.analytics.col.remove(spec)
        doc  = dict(sytsem=self.name, url=url, api=api, api_params=api_params,
                        expire=time.time()+self.expire)
        self.analytics.col.insert(dict(apicall=doc))
        index_list = [(key, DESCENDING) for key in (url, api)]
        self.analytics.col.ensure_index(index_list)

    def pass_apicall(self, url, api, api_params):
        """
        Filter provided apicall wrt existing apicall records in Analytics DB.
        """
        spec = {'apicall.expire':{'$lt' : int(time.time())}}
        self.analytics.col.remove(spec)
        spec = {'apicall.url':url, 'apicall.api':api}
        msg  = 'DBSAbstractService::pass_apicall, %s, API=%s, args=%s'\
        % (self.name, api, api_params)
        for row in self.analytics.col.find(spec):
            input_query = dict(spec=api_params)
            exist_query = dict(spec=row['apicall']['api_params'])
            if  compare_specs(input_query, exists_query):
                msg += '\nwill re-use existing api call with args=%s'\
                % row['apicall']['api_params']
                self.logger.info(msg)
                return True
        return False

    def lookup_keys(self, api):
        """
        Return look-up keys of data output for given data-service API.
        """
        lkeys = []
        for key in self.map[api]['keys']:
            for lkey in self.dasmapping.lookup_keys(self.name, key, api=api):
                if  lkey not in lkeys:
                    lkeys.append(lkey)
        return lkeys

    def inspect_params(self, api, args):
        """
        Perform API parameter inspection. Check if API accept a range
        of parameters, etc.
        """
        for key, value in args.items():
            if  type(value) is types.DictType:
                minval = None
                maxval = None
                for oper, val in value.items():
                    if  oper == '$in':
                        minval = int(val[0])
                        maxval = int(val[-1])
                    elif oper == '$lt':
                        maxval = int(val) - 1
                    elif oper == '$lte':
                        maxval = int(val)
                    elif oper == '$gt':
                        minval = int(val) + 1
                    elif oper == '$gte':
                        minval = int(val)
                    else:
                        msg  = 'DASAbstractService::inspect_params, API=%s'\
                                % api
                        msg += ' does not support operator %s' % oper
                        raise Exception(msg)
                args[key] = range(minval, maxval)
        return args

    def clean_params(self, api, args):
        """
        For some data-services it's easier to call API with parameters
        matching wild-card pattern. For instance, instead of passing 
        site name into SiteDB API, we will call SiteDB API without
        parameters (with wildcard). Must be implemented in sub-classes.
        """
        return args

    def patterns(self, api, args):
        """
        Define how to deal with patterns at API level. Some API accept a 
        star, '*', as pattern parameter, some use another schema, e.g.
        SiteDB don't use '*', and instead it should be drop-off from parameter.
        Must be implemented in sub-classes
        """
        return args

    def api(self, query):
        """
        Data service api method, can be defined by data-service class.
        It parse input query and invoke appropriate data-service API
        call. All results are store into localcache.
        """
        self.logger.info('DASAbstractService::%s::api(%s)' \
                % (self.name, query))
        selkeys, cond = self.mongoparser.decompose(query)
        mongo_query = query
        result = False
        for url, api, args in self.apimap(query):
            try:
                args = self.inspect_params(api, args)
                args = self.clean_params(api, args)
                args = self.patterns(api, args)
                msg  = 'DASAbstractService::%s::api found %s, %s' \
                    % (self.name, api, str(args))
                self.logger.info(msg)
                time0   = time.time()
                data    = self.getdata(url, args)
#                gen     = self.parser(data, api, args)
#                genrows = self.data2das(gen, api)
                genrows = self.parser(data, api, args)
                ctime   = time.time() - time0
                self.analytics.add_api(self.name, query, api, args)
                header  = dasheader(self.name, query, api, url, args, ctime,
                    self.expire, self.version())
                header['lookup_keys'] = self.lookup_keys(api)
                header['selection_keys'] = selkeys
                self.localcache.update_cache(mongo_query, genrows, header)
                msg  = 'DASAbstractService::%s cache has been updated,' \
                        % self.name
                self.logger.info(msg)
                self.insert_apicall(url, api, args)
                result = True
            except:
                msg  = 'Fail to process: url=%s, api=%s, args=%s' \
                        % (url, api, args)
                msg += traceback.format_exc()
                self.logger.info(msg)
        return result

    def apimap(self, query):
        """
        This method analyze the input query and create apimap
        dictionary which includes url, api, parameters and
        data services interface (JSON, XML, etc.)
        In a long term we can store this results into API db.
        """
        cond = getarg(query, 'spec', {})
        skeys = getarg(query, 'fields', [])
        for api, value in self.map.items():
            if  value['params'].has_key('api'):
                url = self.url # JAVA, e.g. http://host/Servlet
            else: # if we have http://host/api?...
                url = self.url + '/' + api
            args = value['params']
            if  skeys:
                if  not set(value['keys']) & set(query['fields']):
                    continue
            else:
                found = False
                for key, val in cond.items():
                    entity = key.split('.')[0] # key either entity.attr or just entity
                    for apiparam in self.dasmapping.das2api(self.name, entity):
                        if  args.has_key(apiparam):
                            found = True
                            break
                if  not found:
                    continue
            for key, val in cond.items():
                if  not self.dasmapping.check_daskey(self.name, key):
                    continue # skip if condition key is not valid for this system
                entity = key.split('.')[0] # key either entity.attr or just entity
                for apiparam in self.dasmapping.das2api(self.name, entity):
                    if  args.has_key(apiparam):
                        args[apiparam] = val
            # check that there is no "required" parameter left in args,
            # since such api will not work
            if 'required' in args.values():
                continue
            # check if analytics db has a similar API call
            if  self.pass_apicall(url, api, args):
                continue
            yield url, api, args
