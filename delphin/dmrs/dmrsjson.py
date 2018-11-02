
"""
DMRS-JSON serialization and deserialization.
"""

import io
import json

from delphin.sembase import Lnk, Predicate
from delphin.dmrs import DMRS, Node, Link


def load(source):
    """
    Deserialize a DMRS-JSON file (handle or filename) to DMRS objects

    Args:
        source: filename or file object
    Returns:
        a list of DMRS objects
    """
    if hasattr(source, 'read'):
        data = json.load(source)
    else:
        with open(source) as fh:
            data = json.load(fh)
    return [from_dict(d) for d in data]


def loads(s):
    """
    Deserialize a DMRS-JSON string to DMRS objects

    Args:
        s (str): a DMRS-JSON string
    Returns:
        a list of DMRS objects
    """
    data = json.loads(s)
    return [from_dict(d) for d in data]


def dump(ds, destination, properties=True, indent=False, encoding='utf-8'):
    """
    Serialize DMRS objects to a DMRS-JSON file.

    Args:
        destination: filename or file object
        ds: iterator of :class:`~delphin.dmrs.DMRS` objects to
            serialize
        properties: if `True`, encode variable properties
        indent: if `True`, adaptively indent; if `False` or `None`,
            don't indent; if a non-negative integer N, indent N spaces
            per level
        encoding (str): if *destination* is a filename, write to the
            file with the given encoding; otherwise it is ignored
    """
    if indent is False:
        indent = None
    elif indent is True:
        indent = 2
    data = [to_dict(d, properties=True) for d in ds]
    if hasattr(destination, 'write'):
        json.dump(data, destination, indent=indent)
    else:
        with io.open(destination, 'w', encoding=encoding) as fh:
            json.dump(data, fh)


def dumps(ds, properties=True, indent=False):
    """
    Serialize DMRS objects to a DMRS-JSON string.

    Args:
        ds: iterator of :class:`~delphin.dmrs.DMRS` objects to
            serialize
        properties: if `True`, encode variable properties
        indent: if `True`, adaptively indent; if `False` or `None`,
            don't indent; if a non-negative integer N, indent N spaces
            per level
    Returns:
        a DMRS-JSON-serialization of the DMRS objects
    """
    if indent is False:
        indent = None
    elif indent is True:
        indent = 2
    data = [to_dict(d, properties=properties) for d in ds]
    return json.dumps(data, indent=indent)


def decode(s):
    """
    Deserialize a DMRS object from a DMRS-JSON string.
    """
    return from_dict(json.loads(s))


def encode(d, properties=True, indent=False):
    """
    Serialize a DMRS object to a DMRS-JSON string.

    Args:
        d: a DMRS object
        properties (bool): if `False`, suppress variable properties
        indent (bool, int): if `True` or an integer value, add
            newlines and indentation
    Returns:
        a DMRS-JSON-serialization of the DMRS object
    """
    if indent is False:
        indent = None
    elif indent is True:
        indent = 2
    return json.dumps(to_dict(d, properties=properties), indent=indent)


def to_dict(dmrs, short_pred=True, properties=True):
    """
    Encode *dmrs* as a dictionary suitable for JSON serialization.
    """
    getpred = Predicate.short_form if short_pred else Predicate.string
    nodes=[]
    for node in dmrs.nodes:
        n = dict(nodeid=node.nodeid,
                 predicate=getpred(node.predicate))
        if node.lnk is not None:
            n['lnk'] = {'from': node.cfrom, 'to': node.cto}
        if properties and node.sortinfo:
            n['sortinfo'] = node.sortinfo
        if node.surface is not None:
            n['surface'] = node.surface
        if node.base is not None:
            n['base'] = node.base
        if node.carg is not None:
            n['carg'] = node.carg
        nodes.append(n)
    links=[]
    for link in dmrs.links:
        links.append({
            'from': link.start, 'to': link.end,
            'rargname': link.rargname, 'post': link.post
        })
    d = dict(nodes=nodes, links=links)
    for attr in ('top', 'index', 'xarg', 'lnk', 'surface', 'identifier'):
        val = getattr(dmrs, attr, None)
        if val is not None:
            d[attr] = val
    return d


def from_dict(d):
    """
    Decode a dictionary, as from :func:`to_dict`, into a DMRS object.
    """
    def _lnk(x):
        return None if x is None else Lnk.charspan(x['from'], x['to'])
    nodes = []
    for node in d.get('nodes', []):
        nodes.append(Node(
            node['nodeid'],
            node['predicate'],
            sortinfo=node.get('sortinfo'),
            lnk=_lnk(node.get('lnk')),
            surface=node.get('surface'),
            base=node.get('base'),
            carg=node.get('carg')))
    links = []
    for link in d.get('links', []):
        links.append(Link(
            link['from'],
            link['to'],
            link.get('rargname'),
            link.get('post')))
    return DMRS(
        top=d.get('top'),
        index=d.get('index'),
        xarg=d.get('xarg'),
        nodes=nodes,
        links=links,
        lnk=_lnk(d.get('lnk')),
        surface=d.get('surface'),
        identifier=d.get('identifier')
    )
