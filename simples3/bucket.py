"""Bucket manipulation"""

import time
import hmac
import hashlib
import re
import httplib
import urllib
import urllib2
import datetime

from .utils import (_amz_canonicalize, metadata_headers, rfc822_fmt,
                    _iso8601_dt, aws_md5, aws_urlquote, guess_mimetype,
                    info_dict)

class S3Error(Exception):
    def __init__(self, message, **kwds):
        self.args = message, kwds.copy()
        self.msg, self.extra = self.args

    def __str__(self):
        rv = self.msg
        if self.extra:
            rv += " ("
            rv += ", ".join("%s=%r" % i for i in self.extra.items())
            rv += ")"
        return rv

    @classmethod
    def from_urllib(cls, e):
        """Try to read the real error from AWS."""
        self = cls("HTTP error")
        for attr in "reason", "code", "filename":
            if hasattr(e, attr):
                self.extra[attr] = getattr(e, attr)
        fp = getattr(e, "fp", None)
        if not fp:
            return self
        self.fp = fp
        # The latter part of this clause is to avoid some weird bug in urllib2
        # and AWS which has it read as if chunked, and AWS gives empty reply.
        try:
            self.data = data = fp.read()
        except (httplib.HTTPException, urllib2.URLError), e:
            self.extra["read_error"] = e
        else:
            begin, end = data.find("<Message>"), data.find("</Message>")
            if min(begin, end) >= 0:
                self.full_message = msg = data[begin + 9:end]
                self.msg = msg[:100]
                if self.msg != msg:
                    self.msg += "..."
        return self

    @property
    def code(self): return self.extra.get("code")

class StreamHTTPHandler(urllib2.HTTPHandler):
    pass

class StreamHTTPSHandler(urllib2.HTTPSHandler):
    pass

class AnyMethodRequest(urllib2.Request):
    def __init__(self, method, *args, **kwds):
        self.method = method
        urllib2.Request.__init__(self, *args, **kwds)

    def get_method(self):
        return self.method

class S3File(str):
    def __new__(cls, value, **kwds):
        return super(S3File, cls).__new__(cls, value)

    def __init__(self, value, **kwds):
        kwds["data"] = value
        self.kwds = kwds

    def put_into(self, bucket, key):
        return bucket.put(key, **self.kwds)

class S3Bucket(object):
    amazon_s3_base = "https://s3.amazonaws.com/"
    listdir_re = re.compile(r"^<Key>(.+?)</Key>"
                            r"<LastModified>(.{24})</LastModified>"
                            r"<ETag>(.+?)</ETag><Size>(\d+?)</Size>$")

    def __init__(self, name, access_key=None, secret_key=None, base_url=None):
        self.opener = self.build_opener()
        self.name = name
        self.access_key = access_key
        self.secret_key = secret_key
        if not base_url:
            self.base_url = self.amazon_s3_base + aws_urlquote(name)
        else:
            self.base_url = base_url

    def __str__(self):
        return "<%s %s at %r>" % (self.__class__.__name__, self.name, self.base_url)

    def __repr__(self):
        return self.__class__.__name__ + "(%r, access_key=%r, base_url=%r)" % (
            self.name, self.access_key, self.base_url)

    def __getitem__(self, name): return self.get(name)
    def __delitem__(self, name): return self.delete(name)
    def __setitem__(self, name, value):
        if hasattr(value, "put_into"):
            return value.put_into(self, name)
        else:
            return self.put(name, value)
    def __contains__(self, name):
        try:
            self.info(name)
        except KeyError:
            return False
        else:
            return True

    @classmethod
    def build_opener(cls):
        return urllib2.build_opener(StreamHTTPHandler, StreamHTTPSHandler)

    def sign_description(self, desc):
        """AWS-style sign data."""
        hasher = hmac.new(self.secret_key, desc.encode("utf-8"), hashlib.sha1)
        return hasher.digest().encode("base64").replace("\n", "")

    def make_description(self, method, key=None, data=None,
                         headers={}, subresource=None, bucket=None):
        # The signature descriptor is detalied in the developer's PDF on p. 65.
        res = self.canonicalized_resource(key, bucket=bucket)
        # Append subresource, if any.
        if subresource:
            res += "?" + subresource
        # Make description. :/
        return "\n".join((method, headers.get("Content-MD5", ""),
            headers.get("Content-Type", ""), headers.get("Date", ""))) + "\n" +\
            _amz_canonicalize(headers) + res

    def canonicalized_resource(self, key, bucket=None):
        res = "/"
        if bucket or bucket is None:
            res += aws_urlquote(bucket or self.name)
        res += "/"
        if key:
            res += aws_urlquote(key)
        return res

    def get_request_signature(self, method, key=None, data=None,
                              headers={}, subresource=None, bucket=None):
        return self.sign_description(self.make_description(method, key=key,
            data=data, headers=headers, subresource=subresource, bucket=bucket))

    def new_request(self, method, key=None, args=None, data=None, headers={}):
        headers = headers.copy()
        if data and "Content-MD5" not in headers:
            headers["Content-MD5"] = aws_md5(data)
        if "Date" not in headers:
            headers["Date"] = time.strftime(rfc822_fmt, time.gmtime())
        if "Authorization" not in headers:
            sign = self.get_request_signature(method, key=key, data=data,
                                              headers=headers)
            headers["Authorization"] = "AWS %s:%s" % (self.access_key, sign)
        url = self.make_url(key, args)
        return AnyMethodRequest(method, url, data=data, headers=headers)

    def make_url(self, key, args=None, arg_sep=";"):
        url = self.base_url + "/"
        if key:
            url += aws_urlquote(key)
        if args:
            if hasattr(args, "iteritems"):
                args_items = args.iteritems()
            elif hasattr(args, "items"):
                args_items = args.items()
            else:
                args_items = args
            url += "?" + arg_sep.join("=".join(map(urllib.quote_plus, item))
                                      for item in args_items)
        return url

    def open_request(self, request, errors=True):
            return self.opener.open(request)

    def make_request(self, method, key=None, args=None, data=None, headers={}):
        for retry_no in xrange(10):
            request = self.new_request(method, key=key, args=args,
                                       data=data, headers=headers)
            try:
                return self.open_request(request)
            except (urllib2.HTTPError, urllib2.URLError), e:
                # If S3 gives HTTP 500, we should try again.
                if getattr(e, "code", None) == 500:
                    continue
                raise S3Error.from_urllib(e)
        else:
            raise RuntimeError("ran out of retries")  # Shouldn't happen.

    def get(self, key):
        response = self.make_request("GET", key=key)
        response.s3_info = info_dict(dict(response.info()))
        return response

    def info(self, key):
        try:
            response = self.make_request("HEAD", key=key)
        except S3Error, e:
            if e.code == 404:
                raise KeyError(key)
            raise e
        rv = info_dict(dict(response.info()))
        response.close()
        return rv

    def put(self, key, data=None, acl=None, metadata={}, mimetype=None,
            transformer=None, headers={}):
        headers = headers.copy()
        headers.update({"Content-Type": mimetype or guess_mimetype(key)})
        headers.update(metadata_headers(metadata))
        if acl: headers["X-AMZ-ACL"] = acl
        if transformer: data = transformer(headers, data)
        headers.update({"Content-Length": str(len(data)),
                        "Content-MD5": aws_md5(data)})
        self.make_request("PUT", key=key, data=data, headers=headers).close()

    def delete(self, key):
        # In <=py25, urllib2 raises an exception for HTTP 204, and later
        # does not, so treat errors and non-errors as equals.
        try:
            resp = self.make_request("DELETE", key=key)
        except S3Error, e:
            resp = e
        resp.close()
        if 200 <= resp.code < 300:
            return True
        elif resp.code == 404:
            raise KeyError(key)
        else:
            raise S3Error.from_urllib(resp)

    # TODO Expose the conditional headers, x-amz-copy-source-if-*
    # TODO Add module-level documentation and doctests.
    def copy(self, source, key, acl=None, metadata=None,
             mimetype=None, headers={}):
        """Copy S3 file *source* on format '<bucket>/<key>' to *key*.

        If metadata is not None, replaces the metadata with given metadata,
        otherwise copies the previous metadata.

        Note that *acl* is not copied, but set to *private* by S3 if not given.
        """
        headers = headers.copy()
        headers.update({"Content-Type": mimetype or guess_mimetype(key)})
        headers["X-AMZ-Copy-Source"] = source
        if acl: headers["X-AMZ-ACL"] = acl
        if metadata is not None:
            headers["X-AMZ-Metadata-Directive"] = "REPLACE"
            headers.update(metadata_headers(metadata))
        else:
            headers["X-AMZ-Metadata-Directive"] = "COPY"
        self.make_request("PUT", key=key, headers=headers).close()

    def listdir(self, prefix=None, marker=None, limit=None, delimiter=None):
        """List contents of bucket.

        *prefix*, if given, predicates `key.startswith(prefix)`.
        *marker*, if given, predicates `key > marker`, lexicographically.
        *limit*, if given, predicates `len(keys) <= limit`.
        """
        mapping = (("prefix", prefix),
                   ("marker", marker),
                   ("max-keys", limit),
                   ("delimiter", delimiter))
        args = dict((k, v) for (k, v) in mapping if v is not None)
        response = self.make_request("GET", args=args)
        buffer = ""
        while True:
            data = response.read(4096)
            buffer += data
            while True:
                pos_end = buffer.find("</Contents>")
                if pos_end == -1:
                    break
                piece = buffer[buffer.index("<Contents>") + 10:pos_end]
                buffer = buffer[pos_end + 10:]
                info = piece[:piece.index("<Owner>")]
                mo = self.listdir_re.match(info)
                if not mo:
                    raise ValueError("unexpected: %r" % (piece,))
                key, modify, etag, size = mo.groups()
                # FIXME A little brittle I would say...
                etag = etag.replace("&quot;", '"')
                yield key, _iso8601_dt(modify), etag, int(size)
            if not data:
                break

    @staticmethod
    def _now():
        """
        Wraps datetime.now() for testability.
        """
        return datetime.datetime.now()

    def url_for(self, key, authenticated=False,
                expire=datetime.timedelta(minutes=5)):
        """Produce the URL for given S3 object key.

        *key* specifies the S3 object path relative to the
            base URL of the bucket.
        *authenticated* asks for URL query string authentication
            to be used; such URLs include a signature and expiration
            time, and may be used by HTTP client apps to gain
            temporary access to private S3 objects.
        *expire* indicates when the produced URL ceases to function,
            in seconds from 1970-01-01T00:00:00 UTC; if omitted, the URL
            will expire in 5 minutes from now.

        URL for a publicly accessible S3 object:
        >>> S3Bucket("bottle").url_for("the dregs")
        'https://s3.amazonaws.com/bottle/the%20dregs'

        Query string authenitcated URL example (fake S3 credentials are shown):
        >>> b = S3Bucket("johnsmith", access_key="0PN5J17HBGZHT7JJ3X82",
        ...     secret_key="uV3F3YluFJax1cknvbcGwgjvx4QpvB+leU8dUj2o")
        >>> b.url_for("foo.js", authenticated=True) # doctest: +ELLIPSIS
        'https://s3.amazonaws.com/johnsmith/foo.js?AWSAccessKeyId=...&Expires=...&Signature=...'
        """
        if authenticated:
            if not hasattr(expire, "timetuple"):
                # XXX isinstance, but who uses UNIX timestamps?
                if isinstance(expire, (int, long)):
                    expire = datetime.datetime.fromtimestamp(expire)
                else:
                    # Assume timedelta.
                    expire = self._now() + expire
            expire_desc = str(long(time.mktime(expire.timetuple())))
            auth_descriptor = "".join((
                "GET\n",
                "\n",
                "\n",
                expire_desc + "\n",
                self.canonicalized_resource(key)  # No "\n" by design!
            ))
            args = (("AWSAccessKeyId", self.access_key),
                    ("Expires", expire_desc),
                    ("Signature", self.sign_description(auth_descriptor)))
            return self.make_url(key, args, "&")
        else:
            return self.make_url(key)

    def put_bucket(self, config_xml=None, acl=None):
        if config_xml:
            headers = {"Content-Length": len(config_xml),
                       "Content-Type": "text/xml"}
        else:
            headers = {"Content-Length": "0"}
        if acl:
            headers["X-AMZ-ACL"] = acl
        resp = self.make_request("PUT", key=None, data=config_xml, headers=headers)
        resp.close()
        return resp.code == 200

    def delete_bucket(self):
        return self.delete(None)

class ReadOnlyS3Bucket(S3Bucket):
    """Read-only S3 bucket.

    Mostly useful for situations where urllib2 isn't available (e.g. Google App
    Engine), but you still want the utility functions (like generating
    authenticated URLs, and making upload HTML forms.)
    """

    def build_opener(self):
        return None
