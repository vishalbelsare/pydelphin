
import re
from itertools import count

from delphin.util import LookaheadIterator
from delphin.sembase import (
    Lnk,
    _LnkMixin,
    Predicate,
    _Node,
    _Edge,
    _SemanticComponent,
    _XMRS,
    role_priority,
    property_priority)
from delphin.util import _bfs, _connected_components, accdict


PREDICATE_MODIFIER_ROLE = 'ARG1'


class Node(_Node):
    """
    An EDS node.

    Args:
        nodeid: node identifier
        predicate (:class:`~delphin.sembase.Predicate`): semantic
            predicate
        type (str, optional): node type (generally `x` or `e`)
        properties (dict, optional): mapping of morphosyntactic
            properties and values
        carg (str, optional): constant argument string
        lnk (:class:`Lnk`, optional): surface alignment
        surface (str, optional): surface string
        base (str, optional): base form
    Attributes:
        pred (:class:`~delphin.sembase.Predicate`): semantic
            predicate
        type (str): node type
        properties (dict): mapping of morphosyntactic
            properties and values
        carg (str): constant argument string
        lnk (:class:`Lnk`): surface alignment
        surface (str): surface string
        base (str): base form
        cfrom (int): surface alignment starting position
        cto (int): surface alignment ending position
    """


class Edge(_Edge):
    """
    EDS-style dependency edges.

    Args:
        start: nodeid of the start of the edge
        end: nodeid of the end of the edge
        role (str): role of the argument
    Attributes:
        start: nodeid of the start of the edge
        end: nodeid of the end of the edge
        role (str): role of the argument
    """

    __slots__ = ()

    def __init__(self, start, end, role):
        mode = _Edge.UNSPEC
        super(Edge, self).__init__(start, end, role, mode)

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return NotImplemented
        return (self.start == other.start and
                self.end == other.end and
                self.role == other.role)

    def __ne__(self, other):
        if not isinstance(other, Edge):
            return NotImplemented
        return not self.__eq__(other)


class EDS(_SemanticComponent):
    """
    An Elementary Dependency Structure (EDS) instance.

    EDS are semantic structures deriving from MRS, but they are not
    interconvertible with MRS and therefore do not share a common
    superclass (viz, :class:`~delphin.mrs.xmrs.Xmrs`) in PyDelphin,
    although this may change in a future version. EDS shares some
    common features with DMRS, so this class borrows some DMRS
    elements, such as :class:`Nodes <delphin.mrs.components.Node>`.

    Args:
        top: nodeid of the top node in the graph
        nodes: iterable of :class:`Nodes <delphin.mrs.components.Node>`
        edges: iterable of (start, role, end) triples
    """

    __slots__ = ('nodes', 'edges', '_nodeidx', '_edgestartidx', '_edgeendidx')

    def __init__(self, top=None, nodes=None, edges=None):
        super(EDS, self).__init__(top, None, None, None, None, None)

        if nodes is None: nodes = []
        if edges is None: edges = []

        self.top = top
        self.nodes = nodes
        self.edges = edges

        self._nodeidx = {node.nodeid: node for node in nodes}
        self._edgestartidx = accdict((edge.start, edge) for edge in edges)
        self._edgeendidx = accdict((edge.end, edge) for edge in edges)

    def to_xmrs(self):
        raise NotImplementedError('conversion from EDS is not supported')

    @classmethod
    def from_xmrs(cls, xmrs, predicate_modifiers=False):
        """
        Instantiate an EDS from an XMRS (lossy conversion).

        Args:
            xmrs (:class:`~delphin.sembase.XMRS`): XMRS instance to
                convert from
            predicate_modifiers (bool): if `True`, add
                predicate-modifier dependencies
        """
        # attempt to convert if necessary
        if not isinstance(xmrs, _XMRS):
            xmrs = xmrs.to_xmrs()

        top = xmrs.scope_representative(xmrs.top)
        nodes = _build_nodes(xmrs)
        edges = _build_edges(xmrs)
        if predicate_modifiers:
            edges.extend(_predicate_modifiers(xmrs, edges))
        idmap = _unique_id_map(xmrs, nodes, edges)
        for node in nodes:
            node.nodeid = idmap[node.nodeid]
        top = idmap[top]
        for edge in edges:
            edge.start = idmap[edge.start]
            edge.end = idmap[edge.end]

        return cls(top=top, nodes=nodes, edges=edges)

    def __eq__(self, other):
        if not isinstance(other, Eds):
            return False
        return (
            self.top == other.top and
            all(a == b for a, b in zip(self.nodes(), other.nodes())) and
            self._edges == other._edges
        )

    def node(self, nodeid):
        return self._nodeidx[nodeid]

    def edges_from(self, nodeid):
        self._nodeidx[nodeid]  # check if node exists in EDS at all
        return self._edgestartidx.get(nodeid, [])


def _build_nodes(x):
    nodes = []
    for n in x.nodes:
        nodes.append(Node(
            n.nodeid, n.predicate, n.type, n.properties, n.carg,
            n.lnk, n.surface, n.base))
    return nodes


def _build_edges(x):
    edges = []
    for edge in x.edges:
        src, tgt, role, mode = edge.start, edge.end, edge.role, edge.mode
        if mode == _Edge.INTARG:
            continue
        elif mode in (_Edge.LBLARG, _Edge.QEQARG):
            tgt = x.scope_representative(tgt)
            if role == 'RSTR':
                role = 'BV'
        # elif mode == _Edge.UNEXPR:
        #     ...
        elif mode in (_Edge.VARARG, _Edge.UNSPEC):
            pass  # nothing to do
        else:
            raise ValueError('invalid XMRS edge: ({}, {}, {}, {})'
                             .format(src, tgt, role, mode))
        edges.append(Edge(src, tgt, role))
    return edges


def _predicate_modifiers(xmrs, edges):
    components = _connected_components(
        [node.nodeid for node in xmrs.nodes],
        [(edge.start, edge.end) for edge in edges])
    pm_edges = []
    if len(components) > 1:
        ccmap = {}
        for i, component in enumerate(components):
            for n in component:
                ccmap[n] = i
        for scopeid in xmrs.scopes:
            reps = xmrs.scope_representatives(scopeid)
            if len(reps) > 1:
                pm_edges.extend(_pm_edges(xmrs, reps[0], reps[1:], ccmap))
    return pm_edges


def _pm_edges(xmrs, first, rest, ccmap):
    edges = []
    joined = set([ccmap[first]])
    for other in rest:
        other_component = ccmap[other]
        other_edge = x.edgemap[other].get(PREDICATE_MODIFIER_ROLE)
        if other_component not in joined and other_edge is not None:
            other_target = xmrs.nodemap[other_edge.end]
            if other_target.type == 'u':
                edges.append(Edge(other, PREDICATE_MODIFIER_ROLE, first))
                joined.add(occ)
    return edges


def _unique_id_map(xmrs, nodes, edges):
    new_ids = ('_{}'.format(i) for i in count(start=1))
    idmap = {}
    used = {}
    for node in nodes:
        nid = node.nodeid
        iv = xmrs.ivmap.get(nid)
        if iv is None or xmrs.is_quantifier(nid):
            iv = next(new_ids)
        idmap[nid] = iv
        used.setdefault(iv, set()).add(nid)
    # If more than one node shares the intrinsic variable, pick out a
    # winner similar to scope representatives; the others get new ids.
    # Note that this should only happen with ill-formed MRSs.
    for _id, nids in used.items():
        if len(nids) > 1:
            nids = sorted(nids, key=lambda n: any(edge.end in nids
                                                  for edge in edges
                                                  if edge.start == n))
            for nid in nids[1:]:
                idmap[nid] = next(new_ids)
    return idmap


##############################################################################
##############################################################################
# Codec API

def load(source):
    """
    Deserialize an EDS file (handle or filename) to EDS objects

    Args:
        source: filename or file object
    Returns:
        a list of EDS objects
    """
    if hasattr(source, 'read'):
        data = _decode(source)
    else:
        with open(source) as fh:
            data = _decode(fh)
    return list(data)


def loads(s):
    """
    Deserialize an EDS string to EDS objects

    Args:
        s (str): an EDS string
    Returns:
        a list of EDS objects
    """
    data = _decode(s.splitlines())
    return list(data)


def dump(es, destination, properties=True, show_status=False,
         predicate_modifiers=False, indent=False, encoding='utf-8'):
    """
    Serialize EDS objects to an EDS file.

    Args:
        destination: filename or file object
        es: iterator of :class:`~delphin.eds.EDS` objects to
            serialize
        properties: if `True`, encode variable properties
        show_status (bool): if `True`, indicate disconnected components
        predicate_modifiers (bool): apply EDS predicate modification
            when *es* are not EDSs and must be converted
        indent: if `True`, adaptively indent; if `False` or `None`,
            don't indent; if a non-negative integer N, indent N spaces
            per level
        encoding (str): if *destination* is a filename, write to the
            file with the given encoding; otherwise it is ignored
    """
    string = dumps(es, properties, show_status, predicate_modifiers, indent)
    if hasattr(destination, 'write'):
        print(string, file=destination)
    else:
        with io.open(destination, 'w', encoding=encoding) as fh:
            print(string, file=fh)


def dumps(es, properties=True, show_status=False, predicate_modifiers=False,
          indent=False):
    """
    Serialize EDS objects to an EDS string.

    Args:
        es: iterator of :class:`~delphin.eds.EDS` objects to
            serialize
        properties: if `True`, encode variable properties
        show_status (bool): if `True`, indicate disconnected components
        predicate_modifiers (bool): apply EDS predicate modification
            when *es* are not EDSs and must be converted
        indent: if `True`, adaptively indent; if `False` or `None`,
            don't indent; if a non-negative integer N, indent N spaces
            per level
    Returns:
        an EDS-serialization of the EDS objects
    """
    if indent is None or indent is False:
        delim = ' '
    else:
        delim = '\n'
    return delim.join(
        encode(e, properties, show_status, predicate_modifiers, indent)
        for e in es)


def decode(s):
    """
    Deserialize an EDS object from an EDS string.
    """
    tokens = LookaheadIterator(_lex(s.splitlines()))
    return _decode_eds(tokens)


def encode(e, properties=True, show_status=False, predicate_modifiers=False,
           indent=False):
    """
    Serialize an EDS object to an EDS string.

    Args:
        e: an EDS object
        properties (bool): if `False`, suppress variable properties
        show_status (bool): if `True`, indicate disconnected components
        predicate_modifiers (bool): apply EDS predicate modification
            when *e* is not an EDS and must be converted
        indent (bool, int): if `True` or an integer value, add
            newlines and indentation
    Returns:
        an EDS-serialization of the EDS object
    """
    if indent is None or indent is False:
        indent = False
    else:
        indent = True
    return _encode_eds(e, properties, show_status, predicate_modifiers, indent)


##############################################################################
##############################################################################
# Decoding

_eds_lex_re = re.compile(
    r'''# regex-pattern                      gid  description
    (\{)                                   #   1  graph/properties start
    |(\})                                  #   2  graph/properties end
    |(\||\((?:cyclic *)?(?:fragmented)?\)) #   3  node/graph statuses
    |<(-?\d+:-?\d+)>                       #   4  char span lnk values
    |<(-?\d+\#-?\d+)>                      #   5  chart span lnk values
    |<(\d+(?:\s+\d+)*)>                    #   6  token lnk values
    |<@(\d+)>                              #   7  edge identifier lnk values
    |\("([^"\\]*(?:\\.[^"\\]*)*)"\)        #   8  carg ("strings")
    |([:,])                                #   9  delimiters
    |(\[)                                  #  10  roles start
    |(\])                                  #  11  roles end
    |([^ \n:,<\(\[\]\{\}]+)                #  12  variables, predicates
    |([^\s])                               #  13  unexpected
    ''',
    flags=re.VERBOSE|re.IGNORECASE)


def _lex(lineiter):
    """
    Lex the input string according to _eds_lex_re.

    Yields
        (gid, token, line_number)
    """
    lines = enumerate(lineiter, 1)
    lineno = pos = 0
    try:
        for lineno, line in lines:
            matches = _eds_lex_re.finditer(line)
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
            yield _decode_eds(tokens)
    except StopIteration:
        pass


def _decode_eds(tokens):
    assert tokens.next()[0] == 1
    gid, top, lineno = tokens.next()
    assert gid == 12
    assert tokens.next()[0] == 9
    nodes = []
    edges = []
    gid, token, lineno = tokens.next()
    while gid in (3, 12):
        if gid == 3:
            pass  # ignore graph/node status
        else:
            start = token
            assert tokens.next()[0] == 9
            nodes.append(_decode_node(start, tokens))
            edges.extend(_decode_edges(start, tokens))
        gid, token, lineno = tokens.next()
    return EDS(top=top, nodes=nodes, edges=edges)


def _decode_node(start, tokens):
    gid, pred, lineno = tokens.next()
    assert gid == 12
    predicate = Predicate.surface_or_abstract(pred.lower())
    nodetype = carg = lnk = None
    properties = {}
    gid, token, lineno = tokens.next()
    # lnk values (surface alignment)
    if gid in (4, 5, 6, 7):
        if gid == 4:
            lnk = Lnk.charspan(*token.split(':'))
        elif gid == 5:
            lnk = Lnk.chartspan(*token.split('#'))
        elif gid == 6:
            lnk = Lnk.tokens(token.split())
        elif gid == 7:
            lnk = Lnk.edge(token)
        gid, token, lineno = tokens.next()
    # constants
    if gid == 8:
        carg = token
        gid, token, lineno = tokens.next()
    # properties
    if gid == 1:
        gid, nodetype, lineno = tokens.next()
        assert gid == 12
        gid, prop, lineno = tokens.next()
        while gid == 12:
            gid, val, lineno = tokens.next()
            assert gid == 12
            properties[prop.upper()] = val.lower()
            gid = tokens.next()[0]
            if gid == 9:
                gid, prop, lineno = tokens.next()
        assert gid == 2
        gid, token, lineno = tokens.next()
    assert gid == 10  # edges begin next
    return Node(start, predicate, nodetype, properties, carg, lnk)


def _decode_edges(start, tokens):
    edges = []
    gid, role, lineno = tokens.next()
    while gid == 12:
        role = role.upper()
        gid, end, lineno = tokens.next()
        assert gid == 12
        edges.append(Edge(start, end, role))
        gid = tokens.next()[0]
        if gid == 9:
            gid, role, lineno = tokens.next()
    assert gid == 11
    return edges


##############################################################################
##############################################################################
# Encoding


def _encode_eds(e, properties, show_status, predicate_modifiers, indent):
    # attempt to convert if necessary
    if not isinstance(e, EDS):
        e = EDS.from_xmrs(e, predicate_modifiers=predicate_modifiers)

    # do something predictable for empty EDS
    if len(e.nodes) == 0:
        return '{:\n}' if indent else '{:}'

    # determine if graph is connected
    g = {node.nodeid: set() for node in e.nodes}
    for node in e.nodes:
        for edge in e.edges_from(node.nodeid):
            g[node.nodeid].add(edge.end)
            g[edge.end].add(node.nodeid)
    nidgrp = _bfs(g, start=e.top)

    status = ''
    if show_status and nidgrp != set(g):
        status = ' (fragmented)'
    delim = '\n' if indent else ' '
    connected = ' ' if indent else ''
    disconnected = '|' if show_status else ' '

    ed_list = []
    for node in e.nodes:
        membership = connected if node.nodeid in nidgrp else disconnected
        edges = e.edges_from(node.nodeid)
        ed_list.append(membership + _encode_node(node, edges, properties))

    return '{{{top}{status}{delim}{ed_list}{enddelim}}}'.format(
        top=e.top + ':' if e.top is not None else ':',
        status=status,
        delim=delim,
        ed_list=delim.join(ed_list),
        enddelim='\n' if indent else ''
    )

def _encode_node(node, edges, properties):
    parts = [node.nodeid, ':', node.predicate.short_form()]
    if node.lnk is not None:
        parts.append(str(node.lnk))
    if node.carg is not None:
        parts.append('("{}")'.format(node.carg))
    if properties and (node.properties or node.type is not None):
        proplist = []
        if node.type is not None:
            proplist.append(node.type)
        for prop in sorted(node.properties, key=property_priority):
            proplist.append('{} {}'.format(prop, node.properties[prop]))
        parts.append('{{{}}}'.format(', '.join(proplist)))
    parts.append('[')
    edgelist = []
    for edge in sorted(edges, key=lambda edge: role_priority(edge.role)):
        edgelist.append('{} {}'.format(edge.role, edge.end))
    parts.append(', '.join(edgelist))
    parts.append(']')
    return ''.join(parts)
