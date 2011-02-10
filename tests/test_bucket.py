from __future__ import with_statement

import urllib2
import unittest
import datetime
from nose.tools import eq_

import simples3
from simples3.utils import aws_md5, aws_urlquote, rfc822_fmt
from tests import MockHTTPResponse, BytesIO, g

from tests import setup_package, teardown_package
setup_package, teardown_package

class S3BucketTestCase(unittest.TestCase):
    def setUp(self):
        g.bucket.mock_reset()

    def tearDown(self):
        if g.bucket.mock_responses:
            raise RuntimeError("test run without exhausting mock_responses")

class MiscTests(S3BucketTestCase):
    def test_str(self):
        eq_(str(g.bucket), "<MockBucket johnsmith at "
                           "'http://johnsmith.s3.amazonaws.com'>")

    def test_repr(self):
        eq_(repr(g.bucket),
            "MockBucket('johnsmith', "
            "access_key='0PN5J17HBGZHT7JJ3X82', "
            "base_url='http://johnsmith.s3.amazonaws.com')")

    def test_timeout_disabled(self):
        g.bucket.timeout = 10.0
        with g.bucket.timeout_disabled():
            eq_(g.bucket.timeout, None)
        eq_(g.bucket.timeout, 10.0)

    def test_error_in_error(self):
        # a hairy situation: an error arising during the parsing of an error.
        def read(bs=4096):
            raise urllib2.URLError("something something dark side")
        FP = type("ErringFP", (object,),
                  {"read": read, "readline": read, "readlines": read})
        url = g.bucket.base_url + "/foo.txt"
        resp = MockHTTPResponse(FP(), {}, url, code=401)
        g.bucket.add_resp_obj(resp, status="401 Something something")
        try:
            g.bucket.get("foo.txt")
        except simples3.S3Error, e:
            assert "read_error" in e.extra

    def test_aws_md5_lit(self):
        val = "Hello!".encode("ascii")
        eq_(aws_md5(val), 'lS0sVtBIWVgzZ0e83ZhZDQ==')

    def test_aws_md5_fp(self):
        val = "Hello world!".encode("ascii")
        eq_(aws_md5(BytesIO(val)), 'hvsmnRkNLIX24EaM7KQqIA==')

    def test_aws_urlquote_funky(self):
        if hasattr(str, "decode"):
            val = "/bucket/\xc3\xa5der".decode("utf-8")
        else:
            val = "/bucket/\xe5der"
        eq_(aws_urlquote(val), "/bucket/%C3%A5der")

class GetTests(S3BucketTestCase):
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
        eq_(fp.read().decode("ascii"), "ohi")

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
            eq_(str(e), "The specified key does not exist. (code=404, "
                        "key='foo.txt', filename='http://johnsmith.s3."
                        "amazonaws.com/foo.txt')")

class InfoTests(S3BucketTestCase):
    headers = g.H("text/plain",
                  ("x-amz-meta-foo", "bar"),
                  ("last-modified", "Mon, 06 Sep 2010 19:34:18 GMT"),
                  ("content-length", "1234"))

    def test_info(self):
        g.bucket.add_resp("/foo.txt", self.headers, "")
        info = g.bucket.info("foo.txt")
        eq_(info["mimetype"], "text/plain")
        eq_(info["metadata"], {"foo": "bar"})

    def test_mapping(self):
        g.bucket.add_resp("/foo.txt", self.headers, "")
        assert "foo.txt" in g.bucket

    def test_mapping_not(self):
        g.bucket.add_resp("/foobar.txt", self.headers, "", status="404 Blah")
        assert "foobar.txt" not in g.bucket

class PutTests(S3BucketTestCase):
    def test_put(self):
        g.bucket.add_resp("/foo.txt", g.H("application/xml"), "OK!")
        g.bucket["foo.txt"] = "hello"
        hdrs = set(v.lower() for v in g.bucket.mock_requests[-1].headers)
        assert "content-length" in hdrs
        assert "content-type" in hdrs
        assert "content-md5" in hdrs
        assert "authorization" in hdrs

    def test_put_s3file(self):
        g.bucket.add_resp("/foo.txt", g.H("application/xml"), "OK!")
        g.bucket["foo.txt"] = simples3.S3File("hello")
        data = g.bucket.mock_requests[-1].get_data()
        eq_(data.decode("ascii"), "hello")

    def test_put_retry(self):
        eq_(g.bucket.mock_responses, [])
        xml = "<?xml etc... ?>"
        g.bucket.add_resp("/foo.txt", g.H("application/xml"), xml,
                          status="500 Internal Server Error")
        g.bucket.add_resp("/foo.txt", g.H("text/plain"), "OK!")
        g.bucket.put("foo.txt", "hello")
        eq_(len(g.bucket.mock_requests), 2)
        for req in g.bucket.mock_requests:
            eq_(req.get_method(), "PUT")
            eq_(req.get_selector(), "/foo.txt")
        eq_(g.bucket.mock_responses, [])

class DeleteTests(S3BucketTestCase):
    def test_delete(self):
        g.bucket.add_resp("/foo.txt", g.H("application/xml"), "<ok />")
        assert g.bucket.delete("foo.txt")
        req = g.bucket.mock_requests[-1]
        eq_(req.get_method(), "DELETE")

    def test_delete_not_found(self):
        g.bucket.add_resp("/foo.txt", g.H("application/xml"),
                          "<notfound />", status="404 Not Found")
        assert not g.bucket.delete("foo.txt")

    def test_delete_other_error(self):
        g.bucket.add_resp("/foo.txt", g.H("application/xml"),
                          "<wat />", status="403 What's Up?")
        try:
            g.bucket.delete("foo.txt")
        except simples3.S3Error, e:
            eq_(e.extra.get("key"), "foo.txt")
            eq_(e.code, 403)
        else:
            assert False, "did not raise exception"

class CopyTests(S3BucketTestCase):
    def test_copy_metadata(self):
        g.bucket.add_resp("/bar", g.H("application/xml"), "<ok />")
        g.bucket.copy("foo/bar", "bar", acl="public")
        req = g.bucket.mock_requests[-1]
        eq_(req.get_method(), "PUT")
        eq_(req.headers["X-amz-copy-source"], "foo/bar")
        eq_(req.headers["X-amz-metadata-directive"], "COPY")

    def test_copy_replace_metadata(self):
        g.bucket.add_resp("/bar", g.H("application/xml"), "<ok />")
        g.bucket.copy("foo/bar", "bar", metadata={}, acl="public")
        req = g.bucket.mock_requests[-1]
        eq_(req.headers["X-amz-metadata-directive"], "REPLACE")

class ListDirTests(S3BucketTestCase):
    def test_listdir(self):
        xml = """
<?xml version="1.0" encoding="UTF-8"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
    <Name>bucket</Name>
    <Prefix></Prefix>
    <Marker></Marker>
    <MaxKeys>1000</MaxKeys>
    <IsTruncated>false</IsTruncated>
    <Contents>
        <Key>my-image.jpg</Key>
        <LastModified>2009-10-12T17:50:30.000Z</LastModified>
        <ETag>&quot;fba9dede5f27731c9771645a39863328&quot;</ETag>
        <Size>434234</Size>
        <StorageClass>STANDARD</StorageClass>
        <Owner>
            <ID>0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef</ID>
            <DisplayName>johndoe</DisplayName>
        </Owner>
    </Contents>
    <Contents>
        <Key>my-third-image.jpg</Key>
        <LastModified>2009-10-12T17:50:30.000Z</LastModified>
        <ETag>&quot;1b2cf535f27731c974343645a3985328&quot;</ETag>
        <Size>64994</Size>
        <StorageClass>STANDARD</StorageClass>
        <Owner>
            <ID>0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef</ID>
            <DisplayName>johndoe</DisplayName>
        </Owner>
    </Contents>
</ListBucketResult>
""".lstrip()
        g.bucket.add_resp("/", g.H("application/xml"), xml)
        reftups = (
            ('my-image.jpg', datetime.datetime(2009, 10, 12, 17, 50, 30),
             '"fba9dede5f27731c9771645a39863328"', 434234),
            ('my-third-image.jpg', datetime.datetime(2009, 10, 12, 17, 50, 30),
             '"1b2cf535f27731c974343645a3985328"', 64994))
        next_reftup = iter(reftups).next
        for tup in g.bucket.listdir():
            eq_(len(tup), 4)
            eq_(tup, next_reftup())
            key, mtype, etag, size = tup

class ModifyBucketTests(S3BucketTestCase):
    def test_bucket_put(self):
        g.bucket.add_resp("/", g.H("application/xml"), "<ok />")
        g.bucket.put_bucket(acl="private")
        req = g.bucket.mock_requests[-1]
        eq_(req.get_method(), "PUT")
        eq_(req.headers["X-amz-acl"], "private")

    def test_bucket_put_conf(self):
        g.bucket.add_resp("/", g.H("application/xml"), "<ok />")
        g.bucket.put_bucket("<etc>etc</etc>", acl="public")
        req = g.bucket.mock_requests[-1]
        eq_(req.get_method(), "PUT")
        eq_(req.headers["X-amz-acl"], "public")

    def test_bucket_delete(self):
        g.bucket.add_resp("/", g.H("application/xml"), "<ok />")
        g.bucket.delete_bucket()
        req = g.bucket.mock_requests[-1]
        eq_(req.get_method(), "DELETE")
