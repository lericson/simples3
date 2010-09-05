#!/usr/bin/env python

import datetime
import urllib2
from urllib import addinfourl
from StringIO import StringIO
from nose.tools import eq_

import simples3
from simples3.utils import rfc822_fmt

# httplib.HTTPMessage is useless for mocking contexts, use own
class MockHTTPMessage(object):
    def __init__(self, d=None):
        self._m = {}
        if not d:
            return
        if hasattr(d, "items"):
            d = d.items()
        for n, v in d:
            self[n] = v

    def __iter__(self): return self.iteritems()
    def __getitem__(self, n): return self._m[unicode(n).lower()]
    def __setitem__(self, n, v): self._m[unicode(n).lower()] = v
    def __delitem__(self, n): del self._m[unicode(n).lower()]
    def items(self): return self._m.items()
    def iteritems(self): return self._m.iteritems()

class MockHTTPHandler(urllib2.HTTPHandler):
    def __init__(self, resps, reqs):
        self.resps = resps
        self.reqs = reqs

    def http_open(self, req):
        resp = self.resps.pop(0)
        eq_(resp.geturl(), req.get_full_url())
        return resp

    def http_request(self, req):
        req = urllib2.HTTPHandler.http_request(self, req)
        self.reqs.append(req)
        return req

# TODO Will need a second mock handler when adding support for HTTPS

class MockBucket(simples3.S3Bucket):
    def __init__(self, *a, **k):
        self.mock_responses = []
        self.mock_requests = []
        super(MockBucket, self).__init__(*a, **k)

    def build_opener(self):
        mockhttp = MockHTTPHandler(self.mock_responses, self.mock_requests)
        return urllib2.build_opener(mockhttp)

    def add_resp(self, path, headers, data, status="200 OK"):
        fp = StringIO(data)
        msg = MockHTTPMessage(headers)
        url = self.base_url + path
        resp = addinfourl(fp, msg, url)
        resp.code, resp.msg = status.split(" ", 1)
        resp.code = int(resp.code)
        self.mock_responses.append(resp)

    def mock_reset(self):
        self.mock_responses[:] = []
        self.mock_requests[:] = []

g = type("Globals", (object,), {})()

def setup_package():
    # Use the fake S3 credentials from the S3 Developer Guide
    g.bucket = MockBucket("johnsmith",
        access_key="0PN5J17HBGZHT7JJ3X82",
        secret_key="uV3F3YluFJax1cknvbcGwgjvx4QpvB+leU8dUj2o",
        base_url="http://johnsmith.s3.amazonaws.com")

def teardown_package():
    del g.bucket

def H(ctype, *hpairs):
    n = datetime.datetime.now()
    msg = MockHTTPMessage([
        ("x-amz-request-id", "abcdef"),
        ("x-amz-id-2", "foobar"),
        ("Server", "AmazonS3"),
        ("Date", n.strftime(rfc822_fmt))])
    msg["Content-Type"] = ctype
    for h, v in hpairs:
        msg[h] = v
    return msg

g.H = H
