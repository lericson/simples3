"""
    simples3.htstream
    ~~~~~~~~~~~~~~~~~

    HTTP streaming. In Python. Oh, the amazement!

    First, create an `HTRequest` instance. The convenience method
    :meth:`-HTRequest.from_url` parser a URL and gets the arguments from there.

    >>> req = HTRequest.from_url("http://www.example.net/")

    To stream up data, one uses the :meth:`-HTRequest.send` method. It takes a
    file-like object (i.e., one that has a callable :attr:`read` attribute).

    Because of how HTTP uploads work, you'll need to know the size of the
    content on beforehand. To accomodate this, one can either specify the size
    via the `size` keyword argument, or let the output object provide a
    :meth:`size` method.

    >>> class Outputter(object):
    ...     def __init__(self, v): self.v = v
    ...     def read(self, n=None): return self.v
    ...     def size(self): return len(self.v)
    ... 
    >>> output = Outputter("Hello world! " * 1024)
    >>> req.send(output)
    >>> 

    Most likely, the output object's read method will eat up the whole file.
    For this reason, :meth:`-HTRequest.send` takes a keyword argument
    `bufsize` which defaults to 8192, or eight KiB.

    Even so, it's still possible and very feasible that the amount of data read
    from the `output` object won't be the amount of data sent to the remote
    server. For this reason, a callback can be specified using the `progress`
    keyword argument.

    >>> def show_progress(req, n_bytes, n_sent, n_chunk):
    ...     print "%.2f%% done" % (float(n_sent) / n_bytes * 100)
    ... 
    >>> req.send(output, progress=show_progress)
"""

import urlparse
import socket
import errno

def socket_from_url(url, family=socket.AF_UNSPEC):
    """Create and connect a socket to *url*.

    Tries all addresses possible for the specified *url*, otherwise raises
    ``socket.error`` with ``errno.ECONNREFUSED``.

    >>> socket_from_url("http://python.org/")  # doctest: +ELLIPSIS
    ('', ('82.94.164.162', 80), <socket._socketobject object at ...>)
    """
    if not hasattr(url, "geturl"):
        url = urlparse.urlsplit(url)

    if url.scheme != "http":
        raise ValueError("scheme must be 'http'")

    host = url.hostname
    port = url.port or url.scheme

    tried_addrs = []
    addrs = socket.getaddrinfo(host, port, family, socket.SOCK_STREAM)
    for (af, st, proto, canonname, sockaddr) in addrs:
        sock = socket.socket(af, st, proto)
        try:
            sock.connect(sockaddr)
        except socket.error, e:
            if e.errno != errno.ECONNREFUSED:
                raise
            tried_addrs.append((canonname, sockaddr))
        else:
            return (canonname, sockaddr, sock)
    else:
        raise socket.error(errno.ECONNREFUSED, tried_addrs)

class HTRequest(object):
    request_fmt = "%s %s HTTP/1.0"

    def __init__(self, sock, method="POST", path="/", headers=[]):
        self.sock = sock
        self.method = method
        self.path = path
        self.headers = list(headers)

    @classmethod
    def from_url(cls, url, family=socket.AF_UNSPEC, **kwds):
        if not hasattr(url, "geturl"):
            url = urlparse.urlsplit(url)
        _, addr, sock = socket_from_url(url, family=family)
        kwds.setdefault("headers", [])
        kwds["headers"].append(("Host", url.netloc))
        if "path" not in kwds:
            reqpath = url.path
            if url.query:
                reqpath += "?" + url.query
            kwds["path"] = reqpath
        self = cls(sock, **kwds)
        self.get_full_url = url.geturl
        return self

    def get_full_url(self):
        addr, port = self.sock.getpeername()
        port_sufx = ""
        if port == 443:
            scheme = "https"
        elif port == 80:
            scheme = "http"
        else:
            scheme = "http"
            port_sufx = ":" + str(port)
        return "%s://%s%s%s" % (scheme, addr, port_sufx, self.path)

    def send(self, output, size=None, bufsize=8192, progress=None):
        if size is None:
            if not hasattr(output, "size"):
                raise TypeError("specify size or implement "
                                "size() on the output object")
            size = output.size()
        self._send_preamble(size=size)
        if progress:
            progress(self, size, 0, 0)
        self._send_output(output, size, bufsize=bufsize, progress=progress)
        return self._read_resp()

    def _send_preamble(self, size):
        hdrs = list(self.headers)
        hdrs.append(("Content-Length", str(size)))
        data = self.request_fmt % (self.method, self.path)
        data += "".join("%s: %s\r\n" % v for v in self.headers)
        data += "\r\n"
        while data:
            data = data[self.sock.send(data):]

    def _send_output(self, output, size, bufsize=8192, progress=None):
        buf = []
        n_sent = 0
        while True:
            if not any(buf):
                n_rem = size - n_sent
                r_num = min(n_rem, bufsize)
                buf.append(output.read(r_num))
                buf[:] = ["".join(buf)[:r_num]]
                if not buf[0]:
                    break
            n_it_sent = self.sock.send(buf[0])
            buf[:] = [buf[0][n_it_sent:]]
            n_sent += n_it_sent
            if progress:
                progress(self, size, n_sent, n_it_sent)
        if n_sent != size:
            raise ValueError("size and sent data mismatch")

    def _read_resp(self):
        # Let httplib handle the response part.
        from httplib import HTTPResponse
        from urllib import addinfourl
        resp = HTTPResponse(self.sock, strict=True, method=self.method)
        resp.begin()
        if resp.will_close:
            self.sock.close()
        else:
            # TODO Should make something of this, I suppose.
            self._active_resp = resp
        # Courtesy of urllib2, weird stuff going on here.
        resp.recv = resp.read
        fp = socket._fileobject(resp, close=True)
        rv = addinfourl(fp, resp.msg, self.get_full_url())
        rv.code = resp.status
        rv.msg = resp.reason
        return rv

if __name__ == "__main__":
    class Outputter(object):
        def __init__(self, v): self.v = v
        def read(self, n=4096): return self.v[:n]
        def size(self): return len(self.v)

    output = Outputter("Hello world! " * 32 * 1024)

    def show_progress(req, n_bytes, n_sent, n_chunk):
        print (req, n_bytes, n_sent, n_chunk)
        print "%.2f%% done" % (float(n_sent) / n_bytes * 100)

    req = HTRequest.from_url("http://bsg.lericson.se/request-dumper.php", family=socket.AF_INET)
    resp = req.send(output, progress=show_progress)
    print resp.url
    print resp.code, resp.headers
    print resp.read()
    raise SystemExit

    import doctest
    doctest.testmod()
