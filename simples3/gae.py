"""Compatibility layer for Google App Engine

Use as you would normally do with :mod:`simples3`, only instead of
:class:`simples3.S3Bucket`, use :class:`simples3.gae.AppEngineS3Bucket`.
"""

import urllib2
from StringIO import StringIO
from urllib import addinfourl
from google.appengine.api import urlfetch
from simples3.bucket import S3Bucket

class _FakeDict(list):
    def iteritems(self):
        return self

def _http_open(req):
    resp = urlfetch.fetch(req.get_full_url(),
                          payload=req.get_data(),
                          method=req.get_method(),
                          headers=_FakeDict(req.header_items()))
    fp = StringIO(resp.content)
    rv = addinfourl(fp, resp.headers, req.get_full_url())
    rv.code = resp.status_code
    rv.msg = "?"
    return rv

class UrlFetchHTTPHandler(urllib2.HTTPHandler):
    def http_open(self, req):
        return _http_open(req)

class UrlFetchHTTPSHandler(urllib2.HTTPSHandler):
    def https_open(self, req):
        return _http_open(req)

class AppEngineS3Bucket(S3Bucket):
    @classmethod
    def build_opener(cls):
        # urllib likes to import ctypes. Why? Because on OS X, it uses it to
        # find proxy configurations. While that is nice and all (and a huge
        # f---ing kludge), it makes the GAE development server bork because the
        # platform makes urllib import ctypes, and that's not permissible on
        # App Engine (can't load dynamic libraries at all.)
        #
        # Giving urllib2 a ProxyHandler without any proxies avoids this look-up
        # trickery, and so is beneficial to our ends and goals in this pickle
        # of a situation.
        return urllib2.build_opener(UrlFetchHTTPHandler, UrlFetchHTTPSHandler,
                                    urllib2.ProxyHandler(proxies={}))
