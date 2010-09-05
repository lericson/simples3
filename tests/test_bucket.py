import unittest
import datetime
from nose.tools import eq_

import simples3
from simples3.utils import rfc822_fmt
from . import setup_package, teardown_package, g

setup_package, teardown_package

class S3Tests(unittest.TestCase):
    def setUp(self):
        g.bucket.mock_reset()

    def test_str(self):
        eq_(str(g.bucket), "<MockBucket johnsmith at "
                           "'http://johnsmith.s3.amazonaws.com'>")

    def test_repr(self):
        eq_(repr(g.bucket),
            "MockBucket('johnsmith', "
            "access_key='0PN5J17HBGZHT7JJ3X82', "
            "base_url='http://johnsmith.s3.amazonaws.com')")

    def test_get(self):
        dt = datetime.datetime(1990, 1, 31, 12, 34, 56)
        headers = g.H("text/plain",
            ("date", dt.strftime(rfc822_fmt)),
            ("x-amz-meta-foo", "bar"))
        g.bucket.add_resp("/foo.txt", headers, "ohi")
        fp = g.bucket["foo.txt"]
        eq_(fp.s3_info["mimetype"], "text/plain")
        eq_(fp.s3_info["metadata"], {"foo": "bar"})
        eq_(fp.s3_info["date"], dt)
        eq_(fp.read(), "ohi")

    def test_get_not_found(self):
        xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<Error><Code>NoSuchKey</Code>'
               '<Message>The specified key does not exist.</Message>'
               '<Key>foo.txt</Key>'
               '<RequestId>abcdef</RequestId>'
               '<HostId>abcdef</HostId>'
               '</Error>')
        g.bucket.add_resp("/foo.txt", g.H("application/xml"), xml,
                          status="404 Not Found")
        try:
            g.bucket.get("foo.txt")
        except simples3.KeyNotFound, e:
            eq_(e.key, "foo.txt")

    def test_put(self):
        g.bucket.add_resp("/foo.txt", g.H("application/xml"), "OK!")
        g.bucket["foo.txt"] = "hello"
        hdrs = map(str.lower, g.bucket.mock_requests[-1].headers)
        assert "content-length" in hdrs
        assert "content-type" in hdrs
        assert "content-md5" in hdrs
        assert "authorization" in hdrs

    def test_put_s3file(self):
        g.bucket.add_resp("/foo.txt", g.H("application/xml"), "OK!")
        g.bucket["foo.txt"] = simples3.S3File("hello")
        eq_(g.bucket.mock_requests[-1].get_data(), "hello")

    def test_put_retry(self):
        eq_(g.bucket.mock_responses, [])
        xml = "<?xml etc... ?>"
        g.bucket.add_resp("/foo.txt", g.H("application/xml"), xml,
                          status="500 Internal Server Error")
        g.bucket.add_resp("/foo.txt", g.H("text/plain"), "OK!")
        g.bucket.put("foo.txt", "hello")
        for req in g.bucket.mock_requests:
            eq_(req.get_method(), "PUT")
            eq_(req.get_selector(), "/foo.txt")
        eq_(g.bucket.mock_responses, [])

    def test_info(self):
        headers = g.H("text/plain", ("x-amz-meta-foo", "bar"))
        g.bucket.add_resp("/foo.txt", headers, "")
        info = g.bucket.info("foo.txt")
        eq_(info["mimetype"], "text/plain")
        eq_(info["metadata"], {"foo": "bar"})
        g.bucket.add_resp("/foo.txt", headers, "")
        assert "foo.txt" in g.bucket
        g.bucket.add_resp("/foobar.txt", headers, "", status="404 Blah")
        assert "foobar.txt" not in g.bucket

    # TODO def test_delete(self): ...
    # TODO def test_copy(self): ...
    # TODO def test_listdir(self): ...
