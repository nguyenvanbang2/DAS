#!/usr/bin/env python
#-*- coding: ISO-8859-1 -*-

"""
Phedex service
"""
__revision__ = "$Id: phedex_service.py,v 1.19 2010/02/05 21:23:13 valya Exp $"
__version__ = "$Revision: 1.19 $"
__author__ = "Valentin Kuznetsov"

from DAS.services.abstract_service import DASAbstractService
from DAS.utils.utils import map_validator, xml_parser
import types
import DAS.utils.jsonwrapper as json

class PhedexService(DASAbstractService):
    """
    Helper class to provide Phedex service
    """
    def __init__(self, config):
        DASAbstractService.__init__(self, 'phedex', config)
        self.map = self.dasmapping.servicemap(self.name)
        map_validator(self.map)
        self.notationmap = self.notations()

    def get_notations(self, api):
        """Return notations used for given API"""
        notations = dict(self.notationmap[''])
        if  self.notationmap.has_key(api):
            notations.update(self.notationmap[api])
        return notations

    def clean_params(self, api, params):
        """
        Clean all parameters to get as much as possible information
        from Phedex. Skip only those which marked as required.
        """
        if  api in ['nodes']:
            args = {}
            for key, val in self.map[api]['params'].items():
                if  val != 'required':
                    args[key] = val
                else:
                    args[key] = params[key]
            return args
        else:
            return params

    def parser(self, dformat, source, api, args):
        """
        Phedex data-service parser.
        """
        notations = self.get_notations(api)
        tags = []
        if  api == 'blockReplicas':
            prim_key = 'block'
        elif api == 'fileReplicas':
            prim_key = 'file'
            tags = 'block.name'
        elif api == 'nodes':
            prim_key = 'node'
        elif api == 'lfn2pfn':
            prim_key = 'mapping'
        else:
            msg = 'PhedexService::parser, unsupported %s API %s' \
                % (self.name, api)
            raise Exception(msg)
        gen = xml_parser(notations, source, prim_key, tags)
        for row in gen:
            yield row
