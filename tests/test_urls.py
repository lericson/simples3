import unittest
from tests import g
from nose.tools import eq_

class URLGenerationTests(unittest.TestCase):
    def test_make_url(self):
        eq_('http://johnsmith.s3.amazonaws.com/file.txt',
            g.bucket.make_url('file.txt'))
        eq_('http://johnsmith.s3.amazonaws.com/my%20key',
            g.bucket.make_url('my key'))

    def test_make_url_authed(self):
        # The expected query string is from S3 Developer Guide
        # "Example Query String Request Authentication" section.
        ou = ("http://johnsmith.s3.amazonaws.com/photos/puppy.jpg"
              "?AWSAccessKeyId=0PN5J17HBGZHT7JJ3X82&Expires=1175139620&"
              "Signature=rucSbH0yNEcP9oM2XNlouVI3BH4%3D")
        eq_(ou, g.bucket.make_url_authed("photos/puppy.jpg", expire=1175139620))

    def test_deprecated_url_for(self):
        eq_(g.bucket.make_url_authed("photos/puppy.jpg", expire=1175139620),
            g.bucket.url_for("photos/puppy.jpg", authenticated=True,
                             expire=1175139620))
        eq_(g.bucket.make_url("photos/puppy.jpg"),
            g.bucket.url_for("photos/puppy.jpg"))
