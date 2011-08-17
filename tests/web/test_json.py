#!/usr/bin/env python

import pytest

from json import loads

from circuits.web import JSONController, Sessions

from .helpers import urlopen, build_opener, HTTPCookieProcessor
from .helpers import CookieJar


class Root(JSONController):

    def index(self):
        return {"success": True, "message": "Hello World!"}

    def test_sessions(self, name=None):
        if name:
            self.session["name"] = name
        else:
            name = self.session.get("name", "World!")

        return {"success": True, "message": "Hello %s" % name}

def test_simple(webapp):
    f = urlopen(webapp.server.base)
    data = f.read()
    data = data.decode("utf-8")
    d = loads(data)
    assert d["success"]
    assert d["message"] == "Hello World!"

def test_sessions(webapp):
    Sessions().register(webapp)

    cj = CookieJar()
    opener = build_opener(HTTPCookieProcessor(cj))

    f = opener.open("%s/test_sessions" % webapp.server.base)
    data = f.read()
    data = data.decode("utf-8")
    d = loads(data)
    assert d["success"]
    assert d["message"] == "Hello World!"

    f = opener.open("%s/test_sessions/test" % webapp.server.base)
    data = f.read()
    data = data.decode("utf-8")
    d = loads(data)
    assert d["success"]
    assert d["message"] == "Hello test"

    f = opener.open("%s/test_sessions" % webapp.server.base)
    data = f.read()
    data = data.decode("utf-8")
    d = loads(data)
    assert d["success"]
    assert d["message"] == "Hello test"
