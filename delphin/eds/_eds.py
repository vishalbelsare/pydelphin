
from itertools import count

from delphin.sembase import (
    Lnk,
    _LnkMixin,
    Predicate,
    _Node,
    _Edge,
    _SemanticComponent,
    _XMRS)
from delphin.util import _connected_components, accdict


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
            xmrs (:class:`~delphin.mrs.xmrs.Xmrs`): Xmrs instance to
                convert from
            predicate_modifiers (function, bool): function that is
                called as `func(xmrs, deps)` after finding the basic
                dependencies (`deps`), returning a mapping of
                predicate-modifier dependencies; the form of `deps` and
                the returned mapping are `{head: [(role, dependent)]}`;
                if *predicate_modifiers* is `True`, the function is
                created using :func:`non_argument_modifiers` as:
                `non_argument_modifiers(role="ARG1", connecting=True);
                if *predicate_modifiers* is `False`, only the basic
                dependencies are returned
        """
        top = xmrs.scope_representative(xmrs.top)
        nodes = _build_nodes(xmrs)
        edges = _build_edges(xmrs)
        if predicate_modifiers:
            edges.extend(_predicate_modifiers(xmrs, edges))
        idmap = _unique_id_map(xmrs, nodes, edges)
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
