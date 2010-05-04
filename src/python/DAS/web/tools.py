#!/usr/bin/env python
#-*- coding: ISO-8859-1 -*-

"""
Web tools.
"""

__license__ = "GPL"
__revision__ = "$Id: tools.py,v 1.5 2010/04/07 18:19:31 valya Exp $"
__version__ = "$Revision: 1.5 $"
__author__ = "Valentin Kuznetsov"
__email__ = "vkuznet@gmail.com"

# system modules
import os
import types
import logging
import plistlib

from datetime import datetime, timedelta
from time import mktime
from wsgiref.handlers import format_date_time

# cherrypy modules
import cherrypy
from cherrypy import log as cplog
from cherrypy import expose

# cheetag modules
from Cheetah.Template import Template
from Cheetah import Version

from json import JSONEncoder

class Page(object):
    """
    __Page__

    Page is a base class that holds a configuration
    """
    def __init__(self):
        self.name = "Page"

    def warning(self, msg):
        """Define warning log"""
        if  msg:
            self.log(msg, logging.WARNING)

    def exception(self, msg):
        """Define exception log"""
        if  msg:
            self.log(msg, logging.ERROR)

    def debug(self, msg):
        """Define debug log"""
        if  msg:
            self.log(msg, logging.DEBUG)

    def info(self, msg):
        """Define info log"""
        if  msg:
            self.log(msg, logging.INFO)

    def log(self, msg, severity):
        """Define log level"""
        if type(msg) != str:
            msg = str(msg)
        if  msg:
            cplog(msg, context=self.name,
                    severity=severity, traceback=False)

class TemplatedPage(Page):
    """
    TemplatedPage is a class that provides simple Cheetah templating
    """
    def __init__(self, config):
        Page.__init__(self)
        templatedir = '%s/%s' % (__file__.rsplit('/', 1)[0], 'templates')
        if  not os.path.isdir(templatedir):
            templatedir  = os.environ['DAS_ROOT'] + '/src/templates'
        self.templatedir = config.get('templatedir', templatedir)
        self.name = "TemplatedPage"
        self.debug("Templates are located in: %s" % self.templatedir)
        self.debug("Using Cheetah version: %s" % Version)

    def templatepage(self, ifile=None, *args, **kwargs):
        """
        Template page method.
        """
        search_list = []
        if len(args) > 0:
            search_list.append(args)
        if len(kwargs) > 0:
            search_list.append(kwargs)
        templatefile = "%s/%s.tmpl" % (self.templatedir, ifile)
        if os.path.exists(templatefile):
            template = Template(file=templatefile, searchList=search_list)
            return template.respond()
        else:
            self.warning("%s not found at %s" % (ifile, self.templatedir))
            return "Template %s not known" % ifile

def auth(func):
    """CherryPy expose auth decorator"""
    @expose
    def wrapper (self, *args, **kwds):
        """Decorator wrapper"""
        headers = cherrypy.request.headers
        if  cherrypy.request.method == 'POST' or\
            cherrypy.request.method == 'PUT':
            body = cherrypy.request.body.read()
        print "\n### auth::header", headers
        redirect_to = 'http://localhost:8400/'
        raise cherrypy.HTTPRedirect(redirect_to)
        raise cherrpypy.HTTPError(401, 'You are not authorized to access \
                this resource')
        data = func (self, *args, **kwds)
        return data
    return wrapper

def exposexml (func):
    """CherryPy expose XML decorator"""
    @expose
    def wrapper (self, *args, **kwds):
        """Decorator wrapper"""
        data = func (self, *args, **kwds)
        if  type(data) is types.ListType:
            results = data
        else:
            results = [data]
        cherrypy.response.headers['Content-Type'] = "application/xml"
        return self.templatepage('das_xml', resultlist = results)
    return wrapper

def exposeplist (func):
    """
    Return data in XML plist format, 
    see http://docs.python.org/library/plistlib.html#module-plistlib
    """
    @expose
    def wrapper (self, *args, **kwds):
        """Decorator wrapper"""
        data_struct = func(self, *args, **kwds)
        plist_str = plistlib.writePlistToString(data_struct)
        cherrypy.response.headers['Content-Type'] = "application/xml+plist"
        return plist_str
    return wrapper

def exposetext (func):
    """CherryPy expose Text decorator"""
    @expose
    def wrapper (self, *args, **kwds):
        """Decorator wrapper"""
        data = func (self, *args, **kwds)
        cherrypy.response.headers['Content-Type'] = "text/plain"
        return data
    return wrapper

def exposejson (func):
    """CherryPy expose JSON decorator"""
    @expose
    def wrapper (self, *args, **kwds):
        """Decorator wrapper"""
        encoder = JSONEncoder()
        data = func (self, *args, **kwds)
        cherrypy.response.headers['Content-Type'] = "text/json"
        try:
            jsondata = encoder.encode(data)
            return jsondata
        except:
            Exception("Fail to JSONtify obj '%s' type '%s'" \
                % (data, type(data)))
    return wrapper

def exposejs (func):
    """CherryPy expose JavaScript decorator"""
    @expose
    def wrapper (self, *args, **kwds):
        """Decorator wrapper"""
        data = func (self, *args, **kwds)
        cherrypy.response.headers['Content-Type'] = "application/javascript"
        return data
    return wrapper

def exposecss (func):
    """CherryPy expose CSS decorator"""
    @expose
    def wrapper (self, *args, **kwds):
        """Decorator wrapper"""
        data = func (self, *args, **kwds)
        cherrypy.response.headers['Content-Type'] = "text/css"
        return data
    return wrapper

def make_timestamp(seconds=0):
    """Create timestamp"""
    then = datetime.now() + timedelta(seconds=seconds)
    return mktime(then.timetuple())

def make_rfc_timestamp(seconds=0):
    """Create RFC timestamp"""
    return format_date_time(make_timestamp(seconds))

def exposedasjson (func):
    """
    This will prepend the DAS header to the data and calculate the checksum of
    the data to set the etag correctly
    """
    @expose
    def wrapper (self, *args, **kwds):
        """Decorator wrapper"""
        encoder = JSONEncoder()
        data = func(self, *args, **kwds)
        cherrypy.response.headers['Content-Type'] = "text/json"
        try:
            jsondata = encoder.encode(data)
            return jsondata
        except:
            Exception("Failed to JSONtify obj '%s' type '%s'" \
                % (data, type(data)))
    return wrapper

def exposedasplist (func):
    """
    Return data in XML plist format, 
    see http://docs.python.org/library/plistlib.html#module-plistlib
    """
    @expose
    def wrapper (self, *args, **kwds):
        """Decorator wrapper"""
        data_struct = func(self, *args, **kwds)
        plist_str = plistlib.writePlistToString(data_struct)
        cherrypy.response.headers['Content-Type'] = "application/xml"
        return plist_str
    return wrapper

