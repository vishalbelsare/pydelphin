
from collections import defaultdict, MutableMapping

from delphin.sembase import (
    Lnk,
    _LnkMixin,
    Predicate,
    _Node,
    _Edge,
    _SemanticComponent,
    _XMRS)
from delphin.mrs.components import (
    Link, links, nodes,
    HandleConstraint, _VarGenerator)
from delphin.util import safe_int, _bfs


TOP_NODEID   = 0
FIRST_NODEID = 10000
RSTR_ROLE    = 'RSTR' # DMRS establishes that quantifiers have a RSTR link
EQ_POST      = 'EQ'
HEQ_POST     = 'HEQ'
NEQ_POST     = 'NEQ'
H_POST       = 'H'
NIL_POST     = 'NIL'
CVARSORT     = 'cvarsort'
BARE_EQ_ROLE = 'MOD'


class Node(_Node):
    """
    A DMRS node.

    Nodes are very simple predications for DMRSs. Nodes don't have
    arguments or labels like :class:`ElementaryPredication` objects,
    but they do have a property for CARGs and contain their variable
    sort and properties in `sortinfo`.

    Args:
        nodeid: node identifier
        pred (:class:`Pred`): semantic predicate
        sortinfo (dict, optional): mapping of morphosyntactic
            properties and values; the `cvarsort` property is
            specified in this mapping
        lnk (:class:`Lnk`, optional): surface alignment
        surface (str, optional): surface string
        base (str, optional): base form
        carg (str, optional): constant argument string
    Attributes:
        pred (:class:`Pred`): semantic predicate
        sortinfo (dict): mapping of morphosyntactic
            properties and values; the `cvarsort` property is
            specified in this mapping
        lnk (:class:`Lnk`): surface alignment
        surface (str): surface string
        base (str): base form
        carg (str): constant argument string
        cfrom (int): surface alignment starting position
        cto (int): surface alignment ending position
    """

    __slots__ = 'properties'

    def __init__(self, nodeid, predicate, sortinfo=None, carg=None,
                 lnk=None, surface=None, base=None):
        if sortinfo is None:
            sortinfo = {}
        elif not isinstance(sortinfo, MutableMapping):
            sortinfo = dict(sortinfo)

        cvarsort = sortinfo.pop(CVARSORT, 'u')
        super(Node, self).__init__(nodeid, predicate, cvarsort,
                                   sortinfo, carg,
                                   lnk, surface, base)

    @property
    def cvarsort(self):
        """
        The "variable" type of the predicate.

        Note:
          DMRS does not use variables, but it is useful to indicate
          whether a node is an individual, eventuality, etc., so this
          property encodes that information.
        """
        return self.type

    @cvarsort.setter
    def cvarsort(self, value):
        self.type = value

    @property
    def sortinfo(self):
        """
        Morphosemantic property mapping with cvarsort.
        """
        d = dict(self.properties)
        if self.type is not None:
            d[CVARSORT] = self.type
        return d


class Link(object):
    """
    DMRS-style dependency link.

    Links are a way of representing arguments without variables. A
    Link encodes a start and end node, the role name, and the scopal
    relationship between the start and end (e.g. label equality, qeq,
    etc).

    Args:
        start: nodeid of the start of the Link
        end: nodeid of the end of the Link
        rargname (str): role of the argument
        post (str): "post-slash label" indicating the scopal
            relationship between the start and end of the Link;
            possible values are `NEQ`, `EQ`, `HEQ`, and `H`
    Attributes:
        start: nodeid of the start of the Link
        end: nodeid of the end of the Link
        rargname (str): role of the argument
        post (str): "post-slash label" indicating the scopal
            relationship between the start and end of the Link
    """

    __slots__ = ('start', 'end', 'role', 'post')

    def __init__(self, start, end, role, post):
        self.start = start
        self.end = end
        self.role = role
        self.post = post

    def __repr__(self):
        return '<Link object (#{} :{}/{} #{}) at {}>'.format(
            self.start, self.rargname or '', self.post, self.end, id(self)
        )

    @property
    def rargname(self):
        return self.role

    @rargname.setter
    def rargname(self, value):
        self.role = value


class DMRS(_SemanticComponent):
    """
    Dependency Minimal Recursion Semantics (DMRS) class.

    DMRS instances have a list of Node objects and a list of Link
    objects. There are no variables or handles, so these will need to
    be created in order to make an Xmrs object. The *top* node may be
    set directly via a parameter or may be implicitly set via a Link
    from the special nodeid 0. If both are given, the link is
    ignored. The *index* and *xarg* nodes may only be set via
    parameters.

    Args:
        nodes: an iterable of Node objects
        links: an iterable of Link objects
        top: the scopal top node
        index: the non-scopal top node
        xarg: the external argument node
        lnk: the Lnk object associating the MRS to the surface form
        surface: the surface string
        identifier: a discourse-utterance id

    Example:

    >>> rain = Node(10000, Predicate.surface('_rain_v_1_rel'),
    >>>             sortinfo={'cvarsort': 'e'})
    >>> ltop_link = Link(0, 10000, post='H')
    >>> d = DMRS([rain], [ltop_link])
    """

    __slots__ = ('nodes', 'links', '_nodeidx', '_linkstartidx', '_linkendidx')

    def __init__(self, top=None, index=None, xarg=None,
                 nodes=None, links=None,
                 lnk=None, surface=None, identifier=None):
        super(DMRS, self).__init__(top, index, xarg, lnk, surface, identifier)

        if nodes is None:
            nodes = []
        if links is None:
            links = []
        self.nodes = nodes
        self._nodeidx = {n.nodeid: n for n in nodes}
        self.links = links
        self._linkstartidx = {l.start: l for l in links}
        self._linkendidx = {l.end: l for l in links}

    def to_xmrs(self):
        scopes = _scopes(self)
        edges = _xmrs_edges(self, scopes)
        return XMRS(
            top=top,
            index=index,
            xarg=xarg,
            nodes=self.nodes,
            scopes=scopes,
            edges=edges)

    @classmethod
    def from_xmrs(cls, x):
        reps = x.scope_representatives()
        nodes = []
        for n in x.nodes:
            sortinfo = [(CVARSORT, n.type)] + list(n.properties.items())
            nodes.append(Node(
                n.nodeid, n.predicate, sortinfo, n.carg,
                n.lnk, n.surface, n.base))
        scopemap = x.scopemap
        links = []
        for (src, tgt, role, mode) in x.edges:
            tgtscope = scopemap[tgt]
            if mode == _Edge.VARARG:
                post = EQ_POST if scopemap[src] == tgtscope else NEQ_POST
            elif mode == _Edge.LBLARG:
                tgt = reps[tgtscope][0]
                post = HEQ_POST
            elif mode == _Edge.QEQARG:
                tgt = reps[tgtscope][0]
                post = H_POST
            else:
                raise ValueError('invalid XMRS edge: ({}, {}, {}, {})'
                                 .format(src, tgt, role, mode))
            links.append(Link(src, tgt, role, post))
        topscope = scopemap[x.top]
        top = reps.get(topscope, [None])[0]
        return cls(top, x.index, x.xarg, nodes, links,
                   x.lnk, x.surface, x.identifier)


def _scopes(d):
    nodes = [node.nodeid for node in d.nodes]
    edges = [(link.start, link.end) for link in d.links]
    components = _connected_components(nodes, edges)
    scopes = {}
    for i, component in enumerate(components, 1):
        for nodeid in component:
            scopes[nodeid] = i
    return scopes


def _xmrs_edges(d, scopes):
    edges = []
    for link in d.links:
        if link.role == BARE_EQ_ROLE:
            continue
        if link.post == H_POST:
            mode = _XMRS.QEQARG
            tgt = scopes[link.end]
        elif link.post == HEQ_POST:
            mode = _XMRS.LBLARG
            tgt = scopes[link.end]
        else:
            mode = _XMRS.VARARG
            tgt = link.end
        edges.append((linkstart, link.role, mode, tgt))
