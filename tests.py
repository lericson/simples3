#!/usr/bin/env python

import time
import unittest
import simples3
import datetime

class S3BucketTests(unittest.TestCase):
    def setUp(self):
        # Use the same fake S3 credentials as in S3 Developer Guide.
        self.bucket = simples3.S3Bucket('johnsmith',
            access_key='0PN5J17HBGZHT7JJ3X82',
            secret_key='uV3F3YluFJax1cknvbcGwgjvx4QpvB+leU8dUj2o',
            base_url='http://johnsmith.s3.amazonaws.com')

    def test_url_for(self):
        self.assertEquals('http://johnsmith.s3.amazonaws.com/file.txt',
            self.bucket.url_for('file.txt'))
        self.assertEquals('http://johnsmith.s3.amazonaws.com/my%20key',
            self.bucket.url_for('my key'))

    def test_url_for_with_auth(self):
        # The expected query string is from S3 Developer Guide
        # "Example Query String Request Authentication" section.
        x = ("http://johnsmith.s3.amazonaws.com/photos/puppy.jpg"
             "?AWSAccessKeyId=0PN5J17HBGZHT7JJ3X82&Expires=1175139620&"
             "Signature=rucSbH0yNEcP9oM2XNlouVI3BH4%3D")
        self.assertEquals(x,
            self.bucket.url_for('photos/puppy.jpg', authenticated=True,
                                expire=1175139620))

    def test_url_for_with_auth_default_expire(self):
        # Poor man's dynamic scoping is used to
        # stub out S3Bucket._now() method.
        t0 = 1239800000.01234
        _orig_func = self.bucket._now
        self.bucket._now = lambda: datetime.datetime.fromtimestamp(t0)
        try:
            # Note: expected expiration value is 300 seconds (5 min) greater.
            self.failUnless('Expires=1239800300' in
                self.bucket.url_for('file.txt', authenticated=True))
        finally:
            self.bucket._now = _orig_func

if __name__ == "__main__":
    import doctest
    import sys

    module = __import__(__name__)
    suite = unittest.TestLoader().loadTestsFromModule(module)
    suite.addTest(doctest.DocTestSuite(simples3))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(not result.wasSuccessful())
