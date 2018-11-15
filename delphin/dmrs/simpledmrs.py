
"""
Serialization for the SimpleDMRS format.

Note that this format is provided by PyDelphin and not defined
anywhere, so it should only be used for user's convenience and not
used as an interchange format or for other practical purposes. It was
created with human legibility in mind (e.g. for investigating DMRSs
at the command line, because XML (DMRX) is not easy to read).
Deserialization is not provided.
"""

from __future__ import print_function

import io
import re

from delphin.sembase import Lnk, Predicate
from delphin.dmrs import DMRS, Node, Link
from delphin.dmrs._dmrs import EQ_POST, CVARSORT
from delphin.util import safe_int, LookaheadIterator


##############################################################################
##############################################################################
# Pickle-API methods

def load(source):
    """
    Deserialize SimpleDMRS from a file (handle or filename)

    Args:
        source (str, file): input filename or file object
    Returns:
        a list of DMRS objects
    """
    if hasattr(source, 'read'):
        ds = _decode(source)
    else:
        with open(source) as fh:
            ds = _decode(fh)
    return list(ds)


def loads(s, encoding='utf-8'):
    """
    Deserialize SimpleDMRS string representations

    Args:
        s (str): a SimpleDMRS string
    Returns:
        a list of DMRS objects
    """
    ds = _decode(s.splitlines())
    return list(ds)


def dump(ds, destination, properties=True, indent=False, encoding='utf-8'):
    """
    Serialize DMRS objects to SimpleDMRS and write to a file

    Args:
        ds: an iterator of DMRS objects to serialize
        destination: filename or file object where data will be written
        properties: if `False`, suppress morphosemantic properties
        indent (bool, int): if `True` or an integer value, add
            newlines and indentation
        encoding (str): if *destination* is a filename, write to the
            file with the given encoding; otherwise it is ignored
    """
    text = dumps(ds, properties=properties, indent=indent)
    if hasattr(destination, 'write'):
        print(text, file=destination)
    else:
        with io.open(destination, 'w', encoding=encoding) as fh:
            print(text, file=fh)


def dumps(ds, properties=True, indent=False):
    """
    Serialize DMRS objects to a SimpleDMRS representation

    Args:
        ds: an iterator of DMRS objects to serialize
        properties: if `False`, suppress variable properties
        indent (bool, int): if `True` or an integer value, add
            newlines and indentation
    Returns:
        a SimpleDMRS string representation of a corpus of DMRS objects
    """
    return _encode(ds, properties=properties, indent=indent)


def decode(s):
    """
    Deserialize a DMRS object from a SimpleDMRS string.
    """
    tokens = LookaheadIterator(_lex(s.splitlines()))
    return _decode_dmrs(tokens)


def encode(d, properties=True, indent=False):
    """
    Serialize a DMRS object to a SimpleDMRS string.

    Args:
        d: a DMRS object
        properties (bool): if `False`, suppress variable properties
        indent (bool, int): if `True` or an integer value, add
            newlines and indentation
    Returns:
        a SimpleDMRS-serialization of the DMRS object
    """
    return _encode([d], properties=properties, indent=indent)


##############################################################################
##############################################################################
# Decoding

_simpledmrs_lex_re = re.compile(
    r'''# regex-pattern                      gid  description
    (\{)                                   #   1  graph start
    |(\})                                  #   2  graph end
    |(\[)                                  #   3  properties start
    |(\])                                  #   4  properties end
    |<(-?\d+:-?\d+)>                       #   5  cfrom:cto lnk values
    |\("([^"\\]*(?:\\.[^"\\]*)*)"\)        #   6  carg ("strings")
    |(:)                                   #   7  role start
    |(\/)                                  #   8  role/post delimiter
    |(=)                                   #   9  prop=val delimiter
    |(;)                                   #  10  statement terminator
    |(--|->)                               #  11  edge arrows
    |([^\s"'()\/:;<=>[\]{}]+)              #  12  identifiers and values
    |([^\s])                               #  13  unexpected
    ''',
    flags=re.VERBOSE|re.IGNORECASE)


def _lex(lineiter):
    """
    Lex the input string according to _simpledmrs_lex_re.

    Yields
        (gid, token, line_number)
    """
    lines = enumerate(lineiter, 1)
    lineno = pos = 0
    try:
        for lineno, line in lines:
            matches = _simpledmrs_lex_re.finditer(line)
            for m in matches:
                gid = m.lastindex
                if gid == 13:
                    raise ValueError('unexpected input: ' + line[pos:])
                else:
                    token = m.group(gid)
                    yield (gid, token, lineno)
    except StopIteration:
        pass


def _decode(lineiter):
    tokens = LookaheadIterator(_lex(lineiter))
    try:
        while tokens.peek():
            yield _decode_dmrs(tokens)
    except StopIteration:
        pass


def _decode_dmrs(tokens):
    top = index = xarg = lnk = surface = identifier = None
    assert tokens.next()[1] == 'dmrs'
    if tokens.peek()[0] == 12:
        identifier = safe_int(tokens.next()[1])
    assert tokens.next()[0] == 1
    gid = tokens.next()[0]
    if gid == 3:  # graph properties
        lnk = _decode_lnk(tokens)
        surface = _decode_carg(tokens)
        graphprops = dict(_decode_properties(tokens))
        if 'top' in graphprops:
            top = safe_int(graphprops.get('top'))
        if 'index' in graphprops:
            index = safe_int(graphprops.get('index'))
        if 'xarg' in graphprops:
            xarg = safe_int(graphprops.get('xarg'))
        gid, token, lineno = tokens.next()
    nodes = []
    links = []
    while gid == 12:
        nextgid = tokens.peek()[0]
        assert nextgid in (3, 7)
        nodeid = safe_int(token)
        if nextgid == 3:
            nodes.append(_decode_node(nodeid, tokens))
        else:
            links.append(_decode_edge(nodeid, tokens))
        gid, token, lineno = tokens.next()
        # node or edge?
    assert gid == 2
    return DMRS(top=top,
                index=index,
                xarg=xarg,
                nodes=nodes,
                links=links,
                lnk=lnk,
                surface=surface,
                identifier=identifier)


def _decode_lnk(tokens):
    lnk = None
    if tokens.peek()[0] == 5:
        cfrom, cto = tokens.next()[1].split(':')
        lnk = Lnk.charspan(cfrom, cto)
    return lnk


def _decode_carg(tokens):
    carg = None
    if tokens.peek()[0] == 6:
        carg = tokens.next()[1]
    return carg


def _decode_properties(tokens):
    props = []
    gid, token, lineno = tokens.next()
    if gid == 12:
        nextgid = tokens.peek()[0]
        # if not followed by =, it's the node type
        if nextgid in (4, 12):
            props.append((CVARSORT, token))
            gid, token, lineno = tokens.next()
        while gid == 12:
            prop = token
            assert tokens.next()[0] == 9
            gid, val, lineno = tokens.next()
            assert gid == 12
            props.append((prop, val))
            gid, token, lineno = tokens.next()
    assert gid == 4
    return props


def _decode_node(nodeid, tokens):
    assert tokens.next()[0] == 3
    gid, token, lineno = tokens.next()
    assert gid == 12
    predicate = Predicate.surface_or_abstract(token)
    lnk = _decode_lnk(tokens)
    carg = _decode_carg(tokens)
    sortinfo = _decode_properties(tokens)
    if not sortinfo:
        sortinfo = None
    assert tokens.next()[0] == 10
    return Node(nodeid, predicate, sortinfo=sortinfo, carg=carg, lnk=lnk)


def _decode_edge(start, tokens):
    assert tokens.next()[0] == 7
    gid, role, lineno = tokens.next()
    assert gid == 12
    assert tokens.next()[0] == 8
    gid, post, lineno = tokens.next()
    assert gid == 12
    assert tokens.next()[0] == 11
    gid, end, lineno = tokens.next()
    assert gid == 12
    assert tokens.next()[0] == 10
    return Link(start, safe_int(end), role, post)


##############################################################################
##############################################################################
# Encoding


_node = '{nodeid} [{pred}{lnk}{carg}{sortinfo}];'
_link = '{start}:{pre}/{post} {arrow} {end};'


def _encode(ds, properties=True, encoding='unicode', indent=2):
    if indent is None or indent is False:
        indent = None  # normalize False to None
        delim = ' '
    else:
        if indent is True:
            indent = 2
        delim = '\n'
    return delim.join(_encode_dmrs(d, properties, indent=indent) for d in ds)


def _encode_dmrs(d, properties, indent):
    if indent is None:
        delim = ' '
        end = ' }'
    else:
        delim = '\n' + ' ' * indent
        end = '\n}'
    if d.identifier is None:
        start = 'dmrs {'
    else:
        start = 'dmrs {} {{'.format(d.identifier)
    attrs = _encode_attrs(d)
    nodes = [_encode_node(node, properties) for node in d.nodes]
    links = [_encode_link(link) for link in d.links]
    return delim.join([start] + attrs + nodes + links) + end


def _encode_attrs(d):
    attrs = []
    if d.lnk is not None:
        attrs.append(str(d.lnk))
    if d.surface is not None:
        # join without space to lnk, if any
        attrs = [''.join(attrs + ['("{}")'.format(d.surface)])]
    if d.top is not None:
        attrs.append('top={}'.format(d.top))
    if d.index is not None:
        attrs.append('index={}'.format(d.index))
    if d.xarg is not None:
        attrs.append('xarg={}'.format(d.xarg))
    if attrs:
        attrs = ['[{}]'.format(' '.join(attrs))]
    return attrs


def _encode_node(node, properties):
    return _node.format(
        nodeid=node.nodeid,
        pred=str(node.predicate),
        lnk='' if node.lnk is None else str(node.lnk),
        carg='' if node.carg is None else '("{}")'.format(node.carg),
        sortinfo=_encode_sortinfo(node, properties))


def _encode_sortinfo(node, properties):
    sortinfo = []
    if node.cvarsort is not None and node.cvarsort != 'u':
        sortinfo.append(node.cvarsort)
    if properties and node.properties:
        sortinfo.extend('{}={}'.format(k, v)
                        for k, v in node.properties.items())
    if sortinfo:
        return ' ' + ' '.join(sortinfo)
    return ''


def _encode_link(link):
    return _link.format(
        start=link.start,
        pre=link.rargname or '',
        post=link.post,
        arrow='->' if link.rargname or link.post != EQ_POST else '--',
        end=link.end)
