
"""
EDS-PENMAN serialization and deserialization.
"""

import io

import penman

from delphin.sembase import (Lnk, Predicate, role_priority, property_priority)
from delphin.eds import (EDS, Node, Edge)


def load(source):
    """
    Deserialize a EDS-PENMAN file (handle or filename) to EDS objects.

    Args:
        source: filename or file object
    Returns:
        a list of EDS objects
    """
    graphs = penman.load(source)
    xs = [from_triples(g.triples()) for g in graphs]
    return xs


def loads(s):
    """
    Deserialize a EDS-PENMAN string to EDS objects.

    Args:
        s (str): a EDS-PENMAN string
    Returns:
        a list of EDS objects
    """
    graphs = penman.loads(s)
    xs = [from_triples(g.triples()) for g in graphs]
    return xs


def dump(es, destination, properties=True, predicate_modifiers=False,
         indent=False, encoding='utf-8'):
    """
    Serialize EDS objects to a EDS-PENMAN file.

    Args:
        destination: filename or file object
        es: iterator of :class:`~delphin.eds.EDS` objects to
            serialize
        properties: if `True`, encode variable properties
        predicate_modifiers (bool): apply EDS predicate modification
            when *es* are not EDSs and must be converted
        indent: if `True`, adaptively indent; if `False` or `None`,
            don't indent; if a non-negative integer N, indent N spaces
            per level
        encoding (str): if *destination* is a filename, write to the
            file with the given encoding; otherwise it is ignored
    """
    text = dumps(es, properties=properties,
                 predicate_modifiers=predicate_modifiers, indent=indent)
    if hasattr(destination, 'write'):
        print(text, file=destination)
    else:
        with io.open(destination, 'w', encoding=encoding) as fh:
            print(text, file=fh)


def dumps(es, properties=True, predicate_modifiers=False, indent=False):
    """
    Serialize EDS objects to a EDS-PENMAN string.

    Args:
        es: iterator of :class:`~delphin.eds.EDS` objects to
            serialize
        properties: if `True`, encode variable properties
        predicate_modifiers (bool): apply EDS predicate modification
            when *es* are not EDSs and must be converted
        indent: if `True`, adaptively indent; if `False` or `None`,
            don't indent; if a non-negative integer N, indent N spaces
            per level
    Returns:
        a EDS-PENMAN-serialization of the EDS objects
    """
    codec = penman.PENMANCodec()
    to_graph = codec.triples_to_graph
    graphs = [to_graph(to_triples(e, properties=properties,
                                  predicate_modifiers=predicate_modifiers))
              for e in es]
    return penman.dumps(graphs, indent=indent)


def decode(s):
    """
    Deserialize a EDS object from a EDS-PENMAN string.
    """
    return from_triples(penman.decode(s).triples())


def encode(eds, properties=True, predicate_modifiers=False, indent=False):
    """
    Serialize a EDS object to a EDS-PENMAN string.

    Args:
        e: a EDS object
        properties (bool): if `False`, suppress variable properties
        predicate_modifiers (bool): apply EDS predicate modification
            when *eds* is not an EDS and must be converted
        indent (bool, int): if `True` or an integer value, add
            newlines and indentation
    Returns:
        a EDS-PENMAN-serialization of the EDS object
    """
    triples = to_triples(eds, properties=properties,
                         predicate_modifiers=predicate_modifiers)
    g = penman.PENMANCodec().triples_to_graph(triples)
    return penman.encode(g, indent=indent)


def to_triples(e, properties=True, predicate_modifiers=False):
    """
    Encode the Eds as triples suitable for PENMAN serialization.
    """
    # attempt to convert if necessary
    if not isinstance(e, EDS):
        e = EDS.from_xmrs(e, predicate_modifiers)

    triples = []
    # sort nodeids just so top var is first
    nodes = sorted(e.nodes, key=lambda n: n.nodeid != e.top)
    for node in nodes:
        nid = node.nodeid
        triples.append((nid, 'predicate', node.predicate.short_form()))
        if node.lnk:
            triples.append((nid, 'lnk', '"{}"'.format(str(node.lnk))))
        if node.carg:
            triples.append((nid, 'carg', '"{}"'.format(node.carg)))
        if properties:
            if node.type is not None:
                triples.append((nid, 'type', node.type))
            for prop in sorted(node.properties, key=property_priority):
                triples.append((nid, prop, node.properties[prop]))
        edges = sorted(e.edges_from(nid), key=lambda x: role_priority(x.role))
        for edge in edges:
            triples.append((nid, edge.role, edge.end))
    return triples


def from_triples(cls, triples):
    """
    Decode triples, as from :func:`to_triples`, into an EDS object.
    """
    nids, nd, edges = [], {}, []
    for src, rel, tgt in triples:
        if src not in nd:
            nids.append(src)
            nd[src] = {'pred': None, 'type': None, 'props': [],
                       'lnk': None, 'carg': None}
        if rel == 'predicate':
            nd[src]['pred'] = Predicate.surface_or_abstract(tgt)
        elif rel == 'lnk':
            nd[src]['lnk'] = Lnk(tgt)
        elif rel == 'carg':
            if (tgt[0], tgt[-1]) == ('"', '"'):
                tgt = tgt[1:-1]
            nd[src]['carg'] = tgt
        elif rel == 'type':
            nd[src]['type'] = tgt
        elif rel.islower():
            nd[src]['props'].append((rel, tgt))
        else:
            edges.append(Edge(src, tgt, rel))
    nodes = [Node(nid,
                  nd[nid]['pred'],
                  type=nd[nid]['type'],
                  properties=nd[nid]['props'],
                  carg=nd[nid]['carg'],
                  lnk=nd[nid]['lnk'])
             for nid in nids]
    top = nids[0] if nids else None
    return cls(top=top, nodes=nodes, edges=edges)
