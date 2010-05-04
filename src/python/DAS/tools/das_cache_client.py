#!/usr/bin/env python
#pylint: disable-msg=C0301,C0103

"""
DAS cache client tools 
"""
__revision__ = "$Id: das_cache_client.py,v 1.6 2009/05/29 18:29:48 valya Exp $"
__version__ = "$Revision: 1.6 $"
__author__ = "Valentin Kuznetsov"

from DAS.web.utils import urllib2_request, httplib_request
from optparse import OptionParser

class DASOptionParser: 
    """
    DAS cache client option parser
    """
    def __init__(self):
        self.parser = OptionParser()
        self.parser.add_option("-v", "--verbose", action="store", 
                               type="int", default=0, dest="verbose",
             help="verbose output")
        self.parser.add_option("--query", action="store", type="string", 
                               default=False, dest="query",
             help="specify query for your request")
        self.parser.add_option("--input", action="store", type="string", 
                               default=False, dest="input",
             help="specify input for your request; the input should be in a form of dict")
        self.parser.add_option("--host", action="store", type="string", 
                               default='http://localhost:8011', dest="host",
             help="specify host name, e.g. http://hostname:port")
        self.parser.add_option("--idx", action="store", type="int", 
                               default=0, dest="idx",
             help="start index for returned result set, aka pagination, use w/ limit")
        self.parser.add_option("--limit", action="store", type="int", 
                               default=10, dest="limit",
             help="limit number of returned results")
        self.parser.add_option("--lib", action="store", type="string", 
                               default='urllib2', dest="lib",
             help="specify which lib to use, httplib or urllib2 (default)")
        self.parser.add_option("--request", action="store", type="string", 
                               default='GET', dest="request",
             help="specify request type: GET, POST, PUT, DELETE")
        self.parser.add_option("--format", action="store", type="string", 
                               default='json', dest="format",
             help="specify desired format output: JSON, XML")
    def getOpt(self):
        """
        Returns parse list of options
        """
        return self.parser.parse_args()
#
# main
#
if __name__ == '__main__':
    optManager   = DASOptionParser()
    (opts, args) = optManager.getOpt()

    host    = opts.host
    debug   = opts.verbose
    request = opts.request
    if  opts.input:
        params = eval(opts.input)
    elif opts.query:
        params = {'query':opts.query, 'idx':opts.idx, 'limit':opts.limit}
    else:
        msg = 'You need to provide either input dict or query.'
        raise Exception(msg)
    path    = '/rest/%s/%s' % (opts.format.lower(), opts.request.upper())

    if  opts.lib == 'urllib2':
        if  host[-1] == '/':
            host = host[:-1]
        data = urllib2_request(host+path, params, debug)
    elif opts.lib == 'httplib':
        data = httplib_request(host, path, params, request, debug)
    else:
        raise Exception('Unsupported lib %s' % opts.lib)
    print data
