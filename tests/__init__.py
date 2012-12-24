#!/usr/bin/env python

import datetime
import urllib2
from nose.tools import eq_

try:
    from io import BytesIO
except ImportError:
    # 2to3 translates cStringIO to io, so this looks silly on Python 3.x
    from cStringIO import StringIO as BytesIO

import simples3
from simples3.utils import rfc822_fmtdate

# httplib.HTTPMessage is useless for mocking contexts, use own
class MockHTTPMessage(object):
    def __init__(self, d=None):
        self._m = {}
        if not d:
            return
        if hasattr(d, "iteritems"):
            d = d.iteritems()
        for n, v in d:
            self[n] = v

    def __iter__(self): return self.iteritems()
    def __getitem__(self, n): return self._m[unicode(n).lower()]
    def __setitem__(self, n, v): self._m[unicode(n).lower()] = v
    def __delitem__(self, n): del self._m[unicode(n).lower()]
    def items(self): return self._m.items()
    def iteritems(self): return self._m.iteritems()

class MockHTTPResponse(object):
    def __init__(self, fp, headers, url, code=None):
        self.fp = fp
        self.read = fp.read
        self.readline = fp.readline
        self.readlines = fp.readlines
        self.headers = MockHTTPMessage(headers)
        self.url = url
        self.code = code

    def close(self):
        self.read = self.readline = self.readlines = None
        self.fp.close()
        self.fp = None

    def fileno(self): return None
    def info(self): return self.headers
    def getcode(self): return self.code
    def geturl(self): return self.url

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

class MockBucketMixin(object):
    def __init__(self, *a, **k):
        self.mock_responses = []
        self.mock_requests = []
        super(MockBucketMixin, self).__init__(*a, **k)

    def build_opener(self):
        mockhttp = MockHTTPHandler(self.mock_responses, self.mock_requests)
        return urllib2.build_opener(mockhttp)

    def add_resp(self, path, headers, data, status="200 OK"):
        fp = BytesIO(data.encode("utf-8"))
        msg = MockHTTPMessage(headers)
        url = self.base_url + path
        resp = MockHTTPResponse(fp, msg, url)
        return self.add_resp_obj(resp, status=status)

    def add_resp_obj(self, resp, status="200 OK"):
        resp.code, resp.msg = status.split(" ", 1)
        resp.code = int(resp.code)
        self.mock_responses.append(resp)

    def mock_reset(self):
        self.mock_responses[:] = []
        self.mock_requests[:] = []

class MockBucket(MockBucketMixin, simples3.S3Bucket):
    pass

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
        ("Date", rfc822_fmtdate(n))])
    msg["Content-Type"] = ctype
    for h, v in hpairs:
        msg[h] = v
    return msg

g.H = H
