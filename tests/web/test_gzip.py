#!/usr/bin/env python

from gzip import decompress
from urllib.request import build_opener, Request

from circuits import handler, Component

from circuits.web import Controller
from circuits.web.tools import gzip

class Gzip(Component):

    channel = "web"

    def response_started(self, event, response_event):
        event[0] = gzip(response_event[0])

class Root(Controller):

    def index(self):
        return "Hello World!"

def test(webapp):
    from circuits import Debugger
    Debugger().register(webapp)

    gzip = Gzip()
    gzip.register(webapp)

    request = Request(webapp.server.base)
    request.add_header("Accept-Encoding", "gzip")
    opener = build_opener()

    f = opener.open(request)
    s = decompress(f.read())
    assert s == b"Hello World!"

    gzip.unregister()
