"""Misc. S3-related utilities."""

import urllib
import hashlib
import datetime
import mimetypes

def _amz_canonicalize(headers):
    r"""Canonicalize AMZ headers in that certain AWS way.

    >>> _amz_canonicalize({"x-amz-test": "test"})
    'x-amz-test:test\n'
    >>> _amz_canonicalize({"x-amz-first": "test",
    ...                    "x-amz-second": "hello"})
    'x-amz-first:test\nx-amz-second:hello\n'
    >>> _amz_canonicalize({})
    ''
    """
    rv = {}
    for header, value in headers.iteritems():
        header = header.lower()
        if header.startswith("x-amz-"):
            rv.setdefault(header, []).append(value)
    parts = []
    for key in sorted(rv):
        parts.append("%s:%s\n" % (key, ",".join(rv[key])))
    return "".join(parts)

def metadata_headers(metadata):
    return dict(("X-AMZ-Meta-" + h, v) for h, v in metadata.iteritems())

def headers_metadata(headers):
    return dict((h[11:], v) for h, v in headers.iteritems()
                            if h.lower().startswith("x-amz-meta-"))

rfc822_fmt = '%a, %d %b %Y %H:%M:%S GMT'
iso8601_fmt = '%Y-%m-%dT%H:%M:%S.000Z'

def _rfc822_dt(v): return datetime.datetime.strptime(v, rfc822_fmt)
def _iso8601_dt(v): return datetime.datetime.strptime(v, iso8601_fmt)

def aws_md5(data):
    """Make an AWS-style MD5 hash (digest in base64).

    >>> aws_md5("Hello!")
    'lS0sVtBIWVgzZ0e83ZhZDQ=='
    """
    return hashlib.md5(data).digest().encode("base64")[:-1]

def aws_urlquote(value):
    r"""AWS-style quote a URL part.

    >>> aws_urlquote("/bucket/a key")
    '/bucket/a%20key'
    >>> aws_urlquote(u"/bucket/\xe5der")
    '/bucket/%C3%A5der'
    """
    if isinstance(value, unicode):
        value = value.encode("utf-8")
    return urllib.quote(value, "/")

def guess_mimetype(fn, default="application/octet-stream"):
    """Guess a mimetype from filename *fn*."""
    if "." not in fn:
        return default
    bfn, ext = fn.lower().rsplit(".", 1)
    if ext == "jpg": ext = "jpeg"
    return mimetypes.guess_type(bfn + "." + ext)[0] or default

def info_dict(headers):
    rv = {"headers": headers, "metadata": headers_metadata(headers)}
    if "content-length" in headers:
        rv["size"] = int(headers["content-length"])
    if "content-type" in headers:
        rv["mimetype"] = headers["content-type"]
    if "date" in headers:
        rv["date"] = _rfc822_dt(headers["date"]),
    if "last-modified" in headers:
        rv["modify"] = _rfc822_dt(headers["last-modified"])
    return rv

def name(o):
    """Find the name of *o*.

    Functions:
    >>> name(name)
    'name'
    >>> def my_fun(): pass
    >>> name(my_fun)
    'my_fun'

    Classes:
    >>> name(Exception)
    'exceptions.Exception'
    >>> class MyKlass(object): pass
    >>> name(MyKlass)
    'MyKlass'

    Instances:
    >>> name(Exception()), name(MyKlass())
    ('exceptions.Exception', 'MyKlass')

    Types:
    >>> name(str), name(object), name(int)
    ('str', 'object', 'int')

    Type instances:
    >>> name("Hello"), name(True), name(None), name(Ellipsis)
    ('str', 'bool', 'NoneType', 'ellipsis')
    """
    if hasattr(o, "__name__"):
        rv = o.__name__
        modname = getattr(o, "__module__", None)
        # This work-around because Python does it itself,
        # see typeobject.c, type_repr.
        # Note that Python only checks for __builtin__.
        if modname and modname[:2] + modname[-2:] != "____":
            rv = o.__module__ + "." + rv
    else:
        for o in getattr(o, "__mro__", o.__class__.__mro__):
            rv = name(o)
            # If there is no name for the this baseclass, this ensures we check
            # the next rather than say the object has no name (i.e., return
            # None)
            if rv is not None:
                break
    return rv

if __name__ == "__main__":
    import doctest
    doctest.testmod()
