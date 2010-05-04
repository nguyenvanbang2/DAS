#!/usr/bin/env python
#-*- coding: ISO-8859-1 -*-

"""
DBS service
"""
__revision__ = "$Id: dbs_service.py,v 1.18 2009/11/27 19:17:28 valya Exp $"
__version__ = "$Revision: 1.18 $"
__author__ = "Valentin Kuznetsov"

import types

from DAS.services.abstract_service import DASAbstractService
from DAS.utils.utils import map_validator, xml_parser

class DBSService(DASAbstractService):
    """
    Helper class to provide DBS service
    """
    def __init__(self, config):
        DASAbstractService.__init__(self, 'dbs', config)
        self.reserved = ['api', 'apiversion']
        self.map = self.dasmapping.servicemap(self.name, 'javaservlet')
        map_validator(self.map)
        self.notationmap = self.notations()

    def get_notations(self, api):
        """Return notations used for given API"""
        notations = dict(self.notationmap[''])
        if  self.notationmap.has_key(api):
            notations.update(self.notationmap[api])
        return notations

    def parser(self, source, api, args=None):
        """
        DBS data-service parser.
        """
        notations = self.get_notations(api)
        add = None
        if  api == 'listBlocks':
            tag = 'block'
        elif api == 'listFiles':
            tag = 'file'
        else:
            msg = 'DBSService::parser, unsupported %s API %s' \
                % (self.name, api)
            raise Exception(msg)
        gen = xml_parser(notations, source, tag, add)
#        gen = xml_parser(source, tag, add)
        for row in gen:
            yield row
