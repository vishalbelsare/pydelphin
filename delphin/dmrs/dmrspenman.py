
"""
DMRS-PENMAN serialization and deserialization.
"""

import io

import penman

from delphin.sembase import Lnk, Predicate
from delphin.dmrs import DMRS, Node, Link
from delphin.dmrs._dmrs import FIRST_NODEID


def load(source):
    """
    Deserialize PENMAN graphs from a file (handle or filename)

    Args:
        source: filename or file object
    Returns:
        a list of DMRS objects
    """
    graphs = penman.load(fh)
    xs = [from_triples(g.triples()) for g in graphs]
    return xs


def loads(s):
    """
    Deserialize PENMAN graphs from a string

    Args:
        s (str): serialized PENMAN graphs
    Returns:
        a list of DMRS objects
    """
    graphs = penman.loads(s)
    xs = [from_triples(g.triples()) for g in graphs]
    return xs


def dump(ds, destination, properties=False, indent=True, encoding='utf-8'):
    """
    Serialize DMRS objects to a PENMAN file.

    Args:
        destination: filename or file object
        ds: iterator of :class:`~delphin.mrs.dmrs.DMRS` objects to
            serialize
        properties: if `True`, encode variable properties
        indent: if `True`, adaptively indent; if `False` or `None`,
            don't indent; if a non-negative integer N, indent N spaces
            per level
        encoding (str): if *destination* is a filename, write to the
            file with the given encoding; otherwise it is ignored
    """
    text = dumps(ds, properties=properties, indent=indent)
    if hasattr(destination, 'write'):
        print(text, file=destination)
    else:
        with io.open(destination, 'w', encoding=encoding) as fh:
            print(text, file=fh)


def dumps(ds, properties=False, indent=True):
    """
    Serialize DMRS objects to a PENMAN string.

    Args:
        ds: iterator of :class:`~delphin.mrs.dmrs.DMRS` objects to
            serialize
        properties: if `True`, encode variable properties
        indent: if `True`, adaptively indent; if `False` or `None`,
            don't indent; if a non-negative integer N, indent N spaces
            per level
    Returns:
        a PENMAN-serialization of the DMRS objects
    """
    codec = penman.PENMANCodec()
    to_graph = codec.triples_to_graph
    graphs = [to_graph(to_triples(d, properties=properties)) for d in ds]
    return penman.dumps(graphs, indent=indent)


def decode(s):
    """
    Deserialize a DMRS object from a PENMAN string.
    """
    return from_triples(penman.decode(s).triples())


def encode(d, properties=True, indent=False):
    """
    Serialize a DMRS object to a PENMAN string.

    Args:
        d: a DMRS object
        properties (bool): if `False`, suppress variable properties
        indent (bool, int): if `True` or an integer value, add
            newlines and indentation
    Returns:
        a PENMAN-serialization of the DMRS object
    """
    triples = to_triples(d, properties=properties)
    g = penman.PENMANCodec().triples_to_graph(triples)
    return penman.encode(g, indent=indent)


def to_triples(dmrs, short_pred=True, properties=True):
    """
    Encode *dmrs* as triples suitable for PENMAN serialization.
    """
    idmap = {}
    for i, node in enumerate(dmrs.nodes, 1):
        if node.predicate.pos == 'q':
            idmap[node.nodeid] = 'q' + str(i)
        else:
            idmap[node.nodeid] = '{}{}'.format(node.type or '_', i)
    getpred = Predicate.short_form if short_pred else Predicate.string
    ts = []
    for node in sorted(dmrs.nodes, key=lambda n: dmrs.top != n.nodeid):
        _id = idmap[node.nodeid]
        ts.append((_id, 'instance', getpred(node.predicate)))
        if node.lnk is not None:
            ts.append((_id, 'lnk', '"{}"'.format(str(node.lnk))))
        if node.carg is not None:
            ts.append((_id, 'carg', '"{}"'.format(node.carg)))
        if properties:
            for key, value in node.sortinfo.items():
                ts.append((_id, key.lower(), value))

    # if dmrs.top is not None:
    #     ts.append((None, 'top', dmrs.top))
    for link in dmrs.links:
        start = idmap[link.start]
        end = idmap[link.end]
        relation = '{}-{}'.format(link.role.upper(), link.post)
        ts.append((start, relation, end))
    return ts


def from_triples(triples, remap_nodeids=True):
    """
    Decode triples into a DMRS object.
    """
    top = lnk = surface = identifier = None
    nids, nd, edges = [], {}, []
    for src, rel, tgt in triples:
        src, tgt = str(src), str(tgt)  # hack for int-converted src/tgt
        if src is None and rel == 'top':
            top = tgt
            continue
        elif src not in nd:
            if top is None:
                top=src
            nids.append(src)
            nd[src] = {'pred': None, 'lnk': None, 'carg': None, 'si': []}
        if rel == 'instance':
            nd[src]['pred'] = Predicate.surface_or_abstract(tgt)
        elif rel == 'lnk':
            cfrom, cto = tgt.strip('"<>').split(':')
            nd[src]['lnk'] = Lnk.charspan(int(cfrom), int(cto))
        elif rel == 'carg':
            if (tgt[0], tgt[-1]) == ('"', '"'):
                tgt = tgt[1:-1]
            nd[src]['carg'] = tgt
        elif rel.islower():
            nd[src]['si'].append((rel, tgt))
        else:
            rargname, post = rel.rsplit('-', 1)
            edges.append((src, tgt, rargname, post))
    if remap_nodeids:
        nidmap = dict((nid, FIRST_NODEID+i) for i, nid in enumerate(nids))
    else:
        nidmap = dict((nid, nid) for nid in nids)
    nodes = [
        Node(
            nodeid=nidmap[nid],
            predicate=nd[nid]['pred'],
            sortinfo=nd[nid]['si'],
            lnk=nd[nid]['lnk'],
            carg=nd[nid]['carg']
        ) for i, nid in enumerate(nids)
    ]
    links = [Link(nidmap[s], nidmap[t], r, p) for s, t, r, p in edges]
    return DMRS(
        top=nidmap[top],
        nodes=nodes,
        links=links,
        lnk=lnk,
        surface=surface,
        identifier=identifier
    )

