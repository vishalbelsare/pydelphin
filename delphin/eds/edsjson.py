
"""
EDS-JSON serialization and deserialization.
"""

import io
import json

from delphin.sembase import Lnk, Predicate
from delphin.eds import EDS, Node, Edge


def load(source):
    """
    Deserialize a EDS-JSON file (handle or filename) to EDS objects

    Args:
        source: filename or file object
    Returns:
        a list of EDS objects
    """
    if hasattr(source, 'read'):
        data = json.load(source)
    else:
        with open(source) as fh:
            data = json.load(fh)
    return [from_dict(d) for d in data]


def loads(s):
    """
    Deserialize a EDS-JSON string to EDS objects

    Args:
        s (str): a EDS-JSON string
    Returns:
        a list of EDS objects
    """
    data = json.loads(s)
    return [from_dict(d) for d in data]


def dump(es, destination, properties=True, indent=False, encoding='utf-8'):
    """
    Serialize EDS objects to a EDS-JSON file.

    Args:
        destination: filename or file object
        es: iterator of :class:`~delphin.eds.EDS` objects to
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
    data = [to_dict(e, properties=True) for e in es]
    if hasattr(destination, 'write'):
        json.dump(data, destination, indent=indent)
    else:
        with io.open(destination, 'w', encoding=encoding) as fh:
            json.dump(data, fh)


def dumps(es, properties=True, indent=False):
    """
    Serialize EDS objects to a EDS-JSON string.

    Args:
        es: iterator of :class:`~delphin.eds.EDS` objects to
            serialize
        properties: if `True`, encode variable properties
        indent: if `True`, adaptively indent; if `False` or `None`,
            don't indent; if a non-negative integer N, indent N spaces
            per level
    Returns:
        a EDS-JSON-serialization of the EDS objects
    """
    if indent is False:
        indent = None
    elif indent is True:
        indent = 2
    data = [to_dict(e, properties=properties) for e in es]
    return json.dumps(data, indent=indent)


def decode(s):
    """
    Deserialize a EDS object from a EDS-JSON string.
    """
    return from_dict(json.loads(s))


def encode(eds, properties=True, indent=False):
    """
    Serialize a EDS object to a EDS-JSON string.

    Args:
        e: a EDS object
        properties (bool): if `False`, suppress variable properties
        indent (bool, int): if `True` or an integer value, add
            newlines and indentation
    Returns:
        a EDS-JSON-serialization of the EDS object
    """
    if indent is False:
        indent = None
    elif indent is True:
        indent = 2
    return json.dumps(to_dict(eds, properties=properties), indent=indent)


def to_dict(eds, properties=True):
    """
    Encode the EDS as a dictionary suitable for JSON serialization.
    """
    nodes = {}
    for node in eds.nodes:
        nd = {
            'label': node.predicate.short_form(),
            'edges': {edge.role: edge.end
                      for edge in eds.edges_from(node.nodeid)}
        }
        if node.lnk is not None:
            nd['lnk'] = {'from': node.cfrom, 'to': node.cto}
        if properties:
            if node.type is not None:
                nd['type'] = node.type
            props = node.properties
            if props:
                nd['properties'] = props
        if node.carg is not None:
            nd['carg'] = node.carg
        nodes[node.nodeid] = nd
    return {'top': eds.top, 'nodes': nodes}


def from_dict(d):
    """
    Decode a dictionary, as from :meth:`to_dict`, into an EDS object.
    """
    makepred, charspan = Predicate.surface_or_abstract, Lnk.charspan
    top = d.get('top')
    nodes, edges = [], []
    for nodeid, node in d.get('nodes', {}).items():
        props = node.get('properties', None)
        nodetype = node.get('type')
        lnk = None
        if 'lnk' in node:
            lnk = charspan(node['lnk']['from'], node['lnk']['to'])
        nodes.append(
            Node(nodeid=nodeid,
                 predicate=makepred(node['label']),
                 type=nodetype,
                 properties=props,
                 carg=node.get('carg'),
                 lnk=lnk))
        edges.extend((nodeid, role, end)
                     for role, end in node.get('edges', {}).items())
    nodes.sort(key=lambda n: (n.cfrom, -n.cto))
    return EDS(top, nodes=nodes, edges=edges)
