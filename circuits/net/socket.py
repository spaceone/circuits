from __future__ import absolute_import

from circuits.core import handler, BaseComponent

from .events import (
    close, closed, connect, connected, disconnect,
    disconnected, error, read, ready, write
)
from .sockets import SocketType, Server as SSocket, Client as SClient


class Socket(BaseComponent):

    events = ('connect', 'disconnect', 'connected', 'disconnected',\
              'read', 'error', 'write', 'close', 'ready', 'closed')

    def __init__(self, channel):
        super(Socket, self).__init__(channel=channel)
        self._sockets = set()

    def bind(self, interface):
        socket = self.__get_socket_component(interface)
        socket.register(self)
        self._sockets.add(socket)

        # add a handler which redirects all events
        # of the real socket channel into this channel
        @handler(*self.events, channel=socket.channel)
        def _handler(self_, event, *args, **kwargs):
            assert self_ is socket
            if event.value.manager is not socket:
                # make sure that only events which come directly from this
                # socket are fired into the main channel
                return
            event = event.__class__(*args, **kwargs)
            socket.fire(event, self.channel)
        _handler.event = True
        socket.addHandler(_handler)

        # add a handler which redirects all events
        # of this main channel into all socket channels
        @handler(*self.events, channel=self.channel)
        def _handler(self_, event, *args, **kwargs):
            if event.value.manager in self._sockets:
                return
            if event.value.manager is socket:
                return
            if event.value.manager is not self:
                # ignore any event which does not come from ourself
                return
            event = event.__class__(*args, **kwargs)
            self.fire(event, socket.channel)
        _handler.event = True
        self.addHandler(_handler)

    def __get_socket_component(self, interface):
        if isinstance(interface, BaseComponent):
            return interface
        socket_type, context, interface = self.parse_interface_type(interface)
        context['channel'] = '%s_%s' % (self.channel, id(interface))
        return socket_type(**context)

    def parse_interface_type(self, interface):
        raise NotImplementedError


class Server(Socket):
    def parse_interface_type(self, interface):
        context, interface = parse_interface_type(interface)
        return SSocket, context, interface


class Client(Socket):
    def parse_interface_type(self, interface):
        context, interface = parse_interface_type(interface)
        return SClient, context, interface


def parse_interface_type(self, interface):
    return {}, interface  # TODO: parse URI, etc.
