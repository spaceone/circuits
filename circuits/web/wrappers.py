# Module:   wrappers
# Date:     13th September 2007
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""Request/Response Wrappers

This module implements the Request and Response objects.
"""


from io import BytesIO, IOBase
from time import strftime, time

try:
    from Cookie import SimpleCookie
except ImportError:
    from http.cookies import SimpleCookie  # NOQA

from .utils import url
from .headers import Headers
from ..six import binary_type
from .errors import HTTPError
from circuits.tools import deprecated
from circuits.net.sockets import BUFSIZE
from .constants import HTTP_STATUS_CODES, SERVER_VERSION

try:
    unicode
except NameError:
    unicode = str


def file_generator(input, chunkSize=BUFSIZE):
    chunk = input.read(chunkSize)
    while chunk:
        yield chunk
        chunk = input.read(chunkSize)
    input.close()


class Host(object):
    """An internet address.

    name should be the client's host name. If not available (because no DNS
    lookup is performed), the IP address should be used instead.
    """

    ip = "0.0.0.0"
    port = 80
    name = "unknown.tld"

    def __init__(self, ip, port, name=None):
        self.ip = ip
        self.port = port
        if name is None:
            name = ip
        self.name = name

    def __repr__(self):
        return "Host(%r, %r, %r)" % (self.ip, self.port, self.name)


class HTTPStatus(object):

    __slots__ = ("_reason", "_status",)

    def __init__(self, status=200, reason=None):
        self._status = status
        self._reason = reason or HTTP_STATUS_CODES[status]

    def __int__(self):
        return self._status

    def __lt__(self, other):
        if isinstance(other, int):
            return self._status < other
        return super(HTTPStatus, self).__lt__(other)

    def __gt__(self, other):
        if isinstance(other, int):
            return self._status > other
        return super(HTTPStatus, self).__gt__(other)

    def __eq__(self, other):
        if isinstance(other, int):
            return self._status == other
        return super(HTTPStatus, self).__eq__(other)

    def __str__(self):
        return "{0:d} {1:s}".format(self._status, self._reason)

    def __repr__(self):
        return "<Status (status={0:d} reason={1:s}>".format(
            self._status, self._reason
        )

    @property
    def status(self):
        return self._status

    @property
    def reason(self):
        return self._reason


class Request(object):
    """Creates a new Request object to hold information about a request.

    :param sock: The socket object of the request.
    :type  sock: socket.socket

    :param method: The requested method.
    :type  method: str

    :param scheme: The requested scheme.
    :type  scheme: str

    :param path: The requested path.
    :type  path: str

    :param protocol: The requested protocol.
    :type  protocol: str

    :param qs: The query string of the request.
    :type  qs: str
    """

    server = None
    """@cvar: A reference to the underlying server"""

    scheme = "http"
    protocol = (1, 1)
    host = ""
    local = Host("127.0.0.1", 80)
    remote = Host("", 0)

    xhr = False

    index = None
    script_name = ""

    login = None
    handled = False

    args = None
    kwargs = None

    def __init__(self, sock, method, scheme, path, protocol, qs):
        "initializes x; see x.__class__.__doc__ for signature"

        self.sock = sock
        self.method = method
        self.scheme = scheme or Request.scheme
        self.path = path
        self.protocol = protocol
        self.qs = qs
        self.cookie = SimpleCookie()

        self._headers = None

        if sock:
            name = sock.getpeername()
            if name:
                self.remote = Host(*name)
            else:
                name = sock.getsockname()
                self.remote = Host(name, "", name)

        self.body = BytesIO()

    @property
    def headers(self):
        return self._headers

    @headers.setter
    def headers(self, headers):
        self._headers = headers

        if "Cookie" in self.headers:
            rawcookies = self.headers["Cookie"]
            if not isinstance(rawcookies, str):
                rawcookies = rawcookies.encode('utf-8')
            self.cookie.load(rawcookies)

        host = self.headers.get("Host", None)
        if not host:
            host = self.local.name or self.local.ip
        self.base = "%s://%s" % (self.scheme, host)

        self.xhr = self.headers.get(
            "X-Requested-With", "").lower() == "xmlhttprequest"

    def __repr__(self):
        protocol = "HTTP/%d.%d" % self.protocol
        return "<Request %s %s %s>" % (self.method, self.path, protocol)

    def url(self, *args, **kwargs):
        return url(self, *args, **kwargs)

    @property
    def local(self):
        if not hasattr(self, "server"):
            return

        return Host(self.server.host, self.server.port)


class Body(object):
    """Response Body"""

    def __get__(self, response, cls=None):
        if response is None:
            return self
        else:
            return response._body

    def __set__(self, response, value):
        if response == value:
            return

        if isinstance(value, binary_type):
            if value:
                value = [value]
            else:
                value = []
        elif isinstance(value, IOBase):
            response.stream = True
            value = file_generator(value)
        elif isinstance(value, HTTPError):
            value = [str(value)]
        elif value is None:
            value = []

        response._body = value


class Status(object):
    """Response Status"""

    def __get__(self, response, cls=None):
        if response is None:
            return self
        else:
            return response._status

    def __set__(self, response, value):
        value = HTTPStatus(value) if isinstance(value, int) else value

        response._status = value


class Response(object):
    """Response(sock, request) -> new Response object

    A Response object that holds the response to
    send back to the client. This ensure that the correct data
    is sent in the correct order.
    """

    body = Body()
    status = Status()

    done = False
    close = False
    stream = False
    chunked = False

    def __init__(self, request, encoding='utf-8', status=None):
        "initializes x; see x.__class__.__doc__ for signature"

        self.request = request
        self.encoding = encoding

        self._body = []
        self._status = HTTPStatus(status if status is not None else 200)

        self.time = time()

        self.headers = Headers([])
        self.headers.add_header("Date", strftime("%a, %d %b %Y %H:%M:%S %Z"))

        if self.request.server is not None:
            self.headers.add_header("Server", self.request.server.http.version)
        else:
            self.headers.add_header("X-Powered-By", SERVER_VERSION)

        self.cookie = self.request.cookie

        self.protocol = "HTTP/%d.%d" % self.request.protocol

        self._encoding = encoding

    def __repr__(self):
        return "<Response %s %s (%d)>" % (
            self.status,
            self.headers.get("Content-Type"),
            (len(self.body) if isinstance(self.body, str) else 0)
        )

    def __str__(self):
        self.prepare()
        protocol = self.protocol
        status = "{0:s}".format(self.status)
        headers = str(self.headers)
        return "{0:s} {1:s}\r\n{2:s}".format(protocol, status, headers)

    @property
    @deprecated
    def code(self):
        return self.status.status

    @property
    @deprecated
    def message(self):
        return self.status.reason

    def prepare(self):
        # Set a default content-Type if we don't have one.
        self.headers.setdefault(
            "Content-Type", "text/html; charset={0:s}".format(self.encoding)
        )

        cLength = None
        if self.body is not None:
            if isinstance(self.body, bytes):
                cLength = len(self.body)
            elif isinstance(self.body, unicode):
                cLength = len(self.body.encode(self._encoding))
            elif isinstance(self.body, list):
                cLength = sum(
                    [
                        len(s.encode(self._encoding))
                        if not isinstance(s, bytes)
                        else len(s) for s in self.body
                        if s is not None
                    ]
                )

        if cLength is not None:
            self.headers["Content-Length"] = str(cLength)

        for k, v in self.cookie.items():
            self.headers.add_header("Set-Cookie", v.OutputString())

        status = self.status

        if status == 413:
            self.close = True
        elif "Content-Length" not in self.headers:
            if status < 200 or status in (204, 205, 304):
                pass
            else:
                if self.protocol == "HTTP/1.1" \
                        and self.request.method != "HEAD" \
                        and self.request.server is not None \
                        and not cLength == 0:
                    self.chunked = True
                    self.headers.add_header("Transfer-Encoding", "chunked")
                else:
                    self.close = True

        if (self.request.server is not None
                and "Connection" not in self.headers):
            if self.protocol == "HTTP/1.1":
                if self.close:
                    self.headers.add_header("Connection", "close")
            else:
                if not self.close:
                    self.headers.add_header("Connection", "Keep-Alive")

        if self.headers.get("Transfer-Encoding", "") == "chunked":
            self.chunked = True
