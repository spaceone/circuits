# Module:	__init__
# Date:		8th November 2008
# Author:	James Mills, prologic at shortcircuit dot net dot au

"""Circuits Tools

circuits.tools contains a standard set of tools for circuits. These
tools are installed as executables with a prefix of "circuits."
"""

def walk(x, f, d=0, v=None):
    if not v:
        v = set()
    yield f(d, x)
    for c in x.components.copy():
        if c not in v:
            v.add(c)
            for r in walk(c, f, d + 1, v):
                yield r

def edges(x, e=None, v=None):
    if not e:
        e = set()
    if not v:
        v = set()
    for c in x.components.copy():
        if c not in v:
            v.add(c)
            e.add((x.name, c.name))
            edges(c, e, v)
    return e

def dotgraph(x, filename=None):
    import pydot
    g = pydot.graph_from_edges(edges(x), directed=True)
    return g.write_png(filename or "%s.png" % x.name, prog="dot")

def root(x):
    if x.manager == x:
        return x
    else:
        return root(x.manager)

def kill(x):
    for c in x.components.copy():
        kill(c)
    x.unregister()

def graph(x):
    """Display a directed graph of the Component structure of x

    @param x: A Component or Manager to graph
    @type  x: Component or Manager

    @return: A directed graph representing x's Component sturcture.
    @rtype:  str
    """

    def printer(d, x):
        return "%s* %s" % (" " * d, x)

    return "\n".join(walk(x, printer))
    
def reprhandler(x):
    """Display a nicely formatted Event Handler, x

    @param x: An Event Handler
    @type  x: function or method

    @return: A nicely formatted representation of the Event Handler, x
    @rtype:  str
    """

    if not hasattr(x, "handler"):
        raise TypeError("%r is not an Event Handler" % x)

    format = "<handler (%s) {f: %s, t: %r, p: %d}>"
    channels = ",".join(x.channels)
    f = x.filter
    t = x.target or ""
    p = x.priority
    return format % (channels, f, t, p)

def inspect(x):
    """Display an inspection report of the Component or Manager x

    @param x: A Component or Manager to graph
    @type  x: Component or Manager

    @return: A detailed inspection report of x
    @rtype:  str
    """

    s = []
    write = s.append

    write(" Registered Components: %d\n" % len(x.components))
    for component in x.components:
        write("  %s\n" % component)
    write("\n")

    write(" Tick Functions: %d\n" % len(x._ticks))
    for tick in x._ticks:
        write("  %s\n" % tick)
    write("\n")

    write(" Channels and Event Handlers: %d\n" % len(x.channels))
    for (t, c) in x.channels:
        write("  %s:%s; %d\n" % (t, c, len(x.channels[(t, c)])))
        for handler in x.channels[(t, c)]:
            write("   %s\n" % reprhandler(handler))

    return "".join(s)
