
from delphin.sembase import (
    Lnk,
    _LnkMixin,
    Predicate,
    _Node,
    _Edge,
    _SemanticComponent,
    _XMRS)
from delphin.util import _connected_components, accdict


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

        # # if requested, find additional dependencies not captured already
        # if predicate_modifiers is True:
        #     func = non_argument_modifiers(role='ARG1', only_connecting=True)
        #     addl_deps = func(xmrs, deps)
        # elif predicate_modifiers is False or predicate_modifiers is None:
        #     addl_deps = {}
        # elif hasattr(predicate_modifiers, '__call__'):
        #     addl_deps = predicate_modifiers(xmrs, deps)
        # else:
        #     raise TypeError('a boolean or callable is required')

        # for nid, deplist in addl_deps.items():
        #     deps.setdefault(nid, []).extend(deplist)

        # ids = _unique_ids(eps, deps)
        # root = _find_root(xmrs)
        # if root is not None:
        #     root = ids[root]
        # edges = [(ids[a], rarg, ids[b]) for a, deplist in deps.items()
        #                                 for rarg, b in deplist]

        return cls(top=top, nodes=nodes, edges=edges)

    def __eq__(self, other):
        if not isinstance(other, Eds):
            return False
        return (
            self.top == other.top and
            all(a == b for a, b in zip(self.nodes(), other.nodes())) and
            self._edges == other._edges
        )


def non_argument_modifiers(role='ARG1', only_connecting=True):
    """
    Return a function that finds non-argument modifier dependencies.

    Args:
        role (str): the role that is assigned to the dependency
        only_connecting (bool): if `True`, only return dependencies
            that connect separate components in the basic dependencies;
            if `False`, all non-argument modifier dependencies are
            included

    Returns:
        a function with signature `func(xmrs, deps)` that returns a
        mapping of non-argument modifier dependencies

    Examples:
        The default function behaves like the LKB:

        >>> func = non_argument_modifiers()

        A variation is similar to DMRS's MOD/EQ links:

        >>> func = non_argument_modifiers(role="MOD", only_connecting=False)
    """
    def func(xmrs, edges):
        components = _connected_components(
            [node.nodeid for node in xmrs.nodes],
            [(edge.start, edge.end) for edge in edges])

        ccmap = {}
        for i, component in enumerate(components):
            for n in component:
                ccmap[n] = i

        addl = {}
        if not only_connecting or len(components) > 1:
            lsh = xmrs.labelset_heads
            lblheads = {v: lsh(v) for v, vd in xmrs._vars.items()
                        if 'LBL' in vd['refs']}
            for heads in lblheads.values():
                if len(heads) > 1:
                    first = heads[0]
                    joined = set([ccmap[first]])
                    for other in heads[1:]:
                        occ = ccmap[other]
                        srt = var_sort(xmrs.args(other).get(role, 'u0'))
                        needs_edge = not only_connecting or occ not in joined
                        edge_available = srt == 'u'
                        if needs_edge and edge_available:
                            addl.setdefault(other, []).append((role, first))
                            joined.add(occ)
        return addl

    return func


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
        if mode in (_Edge.LBLARG, _Edge.QEQARG):
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
