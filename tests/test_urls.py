import unittest
from . import g

class URLGenerationTests(unittest.TestCase):
    def test_make_url(self):
        self.assertEquals('http://johnsmith.s3.amazonaws.com/file.txt',
            g.bucket.make_url('file.txt'))
        self.assertEquals('http://johnsmith.s3.amazonaws.com/my%20key',
            g.bucket.make_url('my key'))

    def test_make_url_authed(self):
        # The expected query string is from S3 Developer Guide
        # "Example Query String Request Authentication" section.
        ou = ("http://johnsmith.s3.amazonaws.com/photos/puppy.jpg"
              "?AWSAccessKeyId=0PN5J17HBGZHT7JJ3X82&Expires=1175139620&"
              "Signature=rucSbH0yNEcP9oM2XNlouVI3BH4%3D")
        gu = g.bucket.make_url_authed("photos/puppy.jpg", expire=1175139620)
        self.assertEquals(ou, gu)
