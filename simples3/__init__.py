r"""A simple Amazon AWS S3 interface

Access to a bucket is done via the ``S3Bucket`` class. It has three required
arguments::

    >>> s = S3Bucket(bucket,
    ...              access_key=access_key,
    ...              secret_key=secret_key)
    ... 
    >>> print s  # doctest: +ELLIPSIS
    <S3Bucket ... at 'https://s3.amazonaws.com/...'>

or if you'd like to use the use-any-domain-you-want stuff, set *base_url* to
something like ``http://s3.example.com``::

    >>> s = S3Bucket(bucket,
    ...              access_key=access_key,
    ...              secret_key=secret_key,
    ...              base_url=base_url)
    >>> print s  # doctest: +ELLIPSIS
    <S3Bucket ... at 'http...'>

Note that missing slash above, it's important. Think of it as
"The prefix to which all calls are made." Also the scheme can be `https` or
regular `http`, or any other urllib2-compatible scheme (as in you could
register your own scheme.)

Now, let's start doing something useful. Start out by putting a simple file
onto there::

    >>> s.put("my file", "my content")

Alright, and fetch it back::

    >>> f = s.get("my file")
    >>> f.read()
    'my content'

Nice and tidy, but what if we want to know more about our fetched file? Easy::

    >>> f.s3_info["modify"]  # doctest: +ELLIPSIS
    datetime.datetime(...)
    >>> f.s3_info["mimetype"]
    'application/octet-stream'
    >>> f.s3_info.keys()
    ['mimetype', 'modify', 'headers', 'date', 'size', 'metadata']
    >>> f.close()

Note that the type was octet stream. That's simply because we didn't specify
anything else. Do that using the `mimetype` keyword argument::

    >>> s.put("my new file!", "Improved content!\nMultiple lines!",
    ...       mimetype="text/plain")

Let's be cool and use the very Pythonic API to do fetch::

    >>> f = s["my new file!"]
    >>> print f.read()
    Improved content!
    Multiple lines!
    >>> f.s3_info["mimetype"]
    'text/plain'
    >>> f.close()

Great job, huh. Now, let's delete it::

    >>> del s["my new file!"]

Could've used the `delete` method instead, but we didn't.

If you just want to know about a key, ask and ye shall receive::

    >>> from pprint import pprint
    >>> s["This is a testfile."] = S3File("Hi!", metadata={"hairdo": "Secret"})
    >>> pprint(s.info("This is a testfile."))  # doctest: +ELLIPSIS
    {'date': datetime.datetime(...),
     'headers': {'content-length': '3',
                 'content-type': 'application/octet-stream',
                 'date': '...',
                 'etag': '"..."',
                 'last-modified': '...',
                 'server': 'AmazonS3',
                 'x-amz-id-2': '...',
                 'x-amz-meta-hairdo': 'Secret',
                 'x-amz-request-id': '...'},
     'metadata': {'hairdo': 'Secret'},
     'mimetype': 'application/octet-stream',
     'modify': datetime.datetime(...),
     'size': 3}

Notable is that you got the metadata parsed out in the `metadata` key. You
might also have noticed how the file was uploaded, using an `S3File` object
like that. That's a nicer way to do it, in a way.

The `S3File` simply takes its keyword arguments, and passes them on to `put`
later. Other than that, it's a str subclass.

And the last dict-like behavior is in tests::

    >>> "This is a testfile." in s
    True
    >>> del s["This is a testfile."]
    >>> "This is a testfile." in s
    False

You can also set a canned ACL using `put`, which is very simple::

    >>> s.put("test/foo", "test", acl="public-read")
    >>> s.put("test/bar", "rawr", acl="public-read")

Boom. What's more? Listing the bucket::

    >>> for (key, modify, etag, size) in s.listdir(prefix="test/"):
    ...     print "%r (%r) is size %r, modified %r" % (key, etag, size, modify)
    ... # doctest: +ELLIPSIS
    'test/bar' ('"..."') is size 4, modified datetime.datetime(...)
    'test/foo' ('"..."') is size 4, modified datetime.datetime(...)

That about sums the basics up.
"""

__version__ = "1.0"

from .bucket import S3File, S3Bucket, S3Error, KeyNotFound
S3File, S3Bucket, S3Error, KeyNotFound  # pyflakes
__all__ = "S3File", "S3Bucket", "S3Error"
