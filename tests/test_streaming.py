from __future__ import with_statement

import StringIO

from nose.tools import eq_

from simples3 import streaming
from simples3.utils import aws_md5
from tests import MockBucketMixin, H

class StreamingMockBucket(MockBucketMixin, streaming.StreamingS3Bucket):
    pass

def _verify_headers(headers, contents):
    assert "Content-length" in headers
    assert str(len(contents)) == headers['Content-length']
    assert "Content-type" in headers
    assert "Content-md5" in headers
    content_md5 = aws_md5(contents.encode("ascii"))
    assert content_md5 == headers['Content-md5']
    assert "Authorization" in headers

def _put_contents(bucket, key, contents):
    bucket.add_resp("/%s" % key, H("application/xml"), "OK!")
    bucket[key] = contents
    _verify_headers(bucket.mock_requests[-1].headers, contents)

def _put_file_contents(bucket, key, contents):
    bucket.add_resp("/%s" % key, H("application/xml"), "OK!")

    fp = StringIO.StringIO(contents)
    try:
        bucket.put_file(key, fp, size=len(contents))
    finally:
        fp.close()

    _verify_headers(bucket.mock_requests[-1].headers, contents)

def _test_put(bucket):
    L = []
    bucket.add_resp("/test.py", H("application/xml"), "OK!")
    with open(__file__, 'rb') as fp:
        bucket.put_file("test.py", fp, progress=lambda *a: L.append(a))
    for total, curr, read in L:
        if read == 0:
            eq_(total, curr)
        else:
            assert curr >= read
    assert L[-1][2] == 0, 'Last progress() has read=0'

def _test_put_multiple(bucket):
    _put_contents(bucket, "bar.txt", "hi mom, how are you")
    _put_contents(bucket, "foo.txt", "hello")

def _test_put_file(bucket):
    _put_file_contents(bucket, "foo.txt", "hello")

def _test_put_file_multiple(bucket):
    _put_file_contents(bucket, "bar.txt", "hi mom, how are you")
    _put_file_contents(bucket, "foo.txt", "hello")

def _streaming_test_iter(bucket):
    # yield lambda: _test_put(bucket)
    yield lambda: _test_put_multiple(bucket)
    yield lambda: _test_put_file(bucket)
    yield lambda: _test_put_file_multiple(bucket)

def test_streaming():
    bucket = StreamingMockBucket("johnsmith",
        access_key="0PN5J17HBGZHT7JJ3X82",
        secret_key="uV3F3YluFJax1cknvbcGwgjvx4QpvB+leU8dUj2o",
        base_url="http://johnsmith.s3.amazonaws.com")
    for f in _streaming_test_iter(bucket):
        bucket.mock_reset()
        yield f
        if bucket.mock_responses:
            raise RuntimeError("test run without exhausting mock_responses")
