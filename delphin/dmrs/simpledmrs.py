
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

from delphin.sembase import Lnk, Predicate
from delphin.dmrs import DMRS, Node, Link
from delphin.mrs.config import EQ_POST, CVARSORT, CONSTARG_ROLE


##############################################################################
##############################################################################
# Pickle-API methods


# def load(fh, single=False):
#     ms = deserialize(fh)
#     if single:
#         ms = next(ms)
#     return ms


# def loads(s, single=False, encoding='utf-8'):
#     ms = deserialize(BytesIO(bytes(s, encoding=encoding)))
#     if single:
#         ms = next(ms)
#     return ms


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

# tokenizer = re.compile(r'("[^"\\]*(?:\\.[^"\\]*)*"'
#                        r'|[^\s:#@\[\]<>"]+'
#                        r'|[:#@\[\]<>])')

# def deserialize(fh):
#     """deserialize a SimpleDmrs-encoded DMRS structure."""
#     raise NotImplementedError

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
    attrs = _encode_attrs(d)
    nodes = [_encode_node(node, properties) for node in d.nodes]
    links = [_encode_link(link) for link in d.links]
    return delim.join(['dmrs {'] + attrs + nodes + links) + end


def _encode_attrs(d):
    attrs = []
    if d.top is not None:
        attrs.append('top={}'.format(d.top))
    if d.index is not None:
        attrs.append('index={}'.format(d.index))
    if d.lnk is not None:
        attrs.append('lnk={}'.format(str(d.lnk)))
    if d.surface is not None:
        attrs.append('surface="{}"'.format(d.surface))
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
    if node.cvarsort is not None:
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
