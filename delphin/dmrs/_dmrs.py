
from collections import defaultdict, MutableMapping

from delphin.sembase import (
    Lnk,
    _LnkMixin,
    Predicate,
    _Node,
    _Edge,
    _SemanticComponent,
    _XMRS)
from delphin.util import _connected_components, accdict


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


class Link(_Edge):
    """
    DMRS-style dependency link.

    Links are a way of representing arguments without variables. A
    Link encodes a start and end node, the role name, and the scopal
    relationship between the start and end (e.g. label equality, qeq,
    etc).

    Args:
        start: nodeid of the start of the Link
        end: nodeid of the end of the Link
        role (str): role of the argument
        post (str): "post-slash label" indicating the scopal
            relationship between the start and end of the Link;
            possible values are `NEQ`, `EQ`, `HEQ`, and `H`
    Attributes:
        start: nodeid of the start of the Link
        end: nodeid of the end of the Link
        role (str): role of the argument
        post (str): "post-slash label" indicating the scopal
            relationship between the start and end of the Link
    """

    __slots__ = ('_post')

    def __init__(self, start, end, role, post):
        self.start = start
        self.end = end
        self.role = role
        self.mode = None  # set in 'post' setter
        self.post = post

    def __repr__(self):
        return '<Link object (#{} :{}/{} #{}) at {}>'.format(
            self.start, self.rargname or '', self.post, self.end, id(self)
        )

    def __eq__(self, other):
        if not isinstance(other, Link):
            return NotImplemented
        return (self.start == other.start and
                self.end == other.end and
                self.role == other.role and
                self.post == other.post)

    def __ne__(self, other):
        if not isinstance(other, Link):
            return NotImplemented
        return not self.__eq__(other)

    @property
    def rargname(self):
        return self.role

    @rargname.setter
    def rargname(self, value):
        self.role = value

    @property
    def post(self):
        return self._post

    @post.setter
    def post(self, value):
        if value == EQ_POST and self.role in (BARE_EQ_ROLE, '', None):
            mode = _Edge.UNSPEC
        else:
            try:
                mode = {
                    EQ_POST: _Edge.VARARG,
                    NEQ_POST: _Edge.VARARG,
                    HEQ_POST: _Edge.LBLARG,
                    H_POST: _Edge.QEQARG
                }[value]
            except KeyError:
                raise ValueError("Invalid 'post' value: {}".format(value))
        self.mode == mode
        self._post = value


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
        self.links = links

        self._nodeidx = {n.nodeid: n for n in nodes}
        self._linkstartidx = accdict((link.start, link) for link in links)
        self._linkendidx = accdict((link.end, link) for link in links)

    def to_xmrs(self):
        scopes, scopemap = _build_scopes(self)
        top = scopemap.get(self.top)
        edges = _build_xmrs_edges(self, scopemap)
        return _XMRS(top=top,
                     index=self.index,
                     xarg=self.xarg,
                     nodes=self.nodes,
                     scopes=scopes,
                     edges=edges,
                     icons=None,
                     lnk=self.lnk,
                     surface=self.surface,
                     identifier=self.identifier)

    @classmethod
    def from_xmrs(cls, x):
        nodes = _build_nodes(x)
        reps = x.scope_representatives()
        links = _build_links(x, reps)
        topscope = x.scopemap[x.top]
        top = reps.get(topscope, [None])[0]
        return cls(top,
                   x.index,
                   x.xarg,
                   nodes,
                   links,
                   x.lnk,
                   x.surface,
                   x.identifier)


def _build_scopes(d):
    nodes = [node.nodeid for node in d.nodes]
    edges = [(link.start, link.end) for link in d.links
             if link.post == EQ_POST]
    components = _connected_components(nodes, edges)
    scopes = {i: nodeids for i, nodeids in enumerate(components, 1)}

    scopemap = {}
    for scopeid, nodeids in scopes.items():
        for nodeid in nodeids:
            scopemap[nodeid] = scopeid

    return scopes, scopemap


def _build_xmrs_edges(d, scopemap):
    edges = []
    for link in d.links:
        if link.role == BARE_EQ_ROLE:
            continue
        if link.post == H_POST:
            mode = _Edge.QEQARG
            tgt = scopemap[link.end]
        elif link.post == HEQ_POST:
            mode = _Edge.LBLARG
            tgt = scopemap[link.end]
        else:
            mode = _Edge.VARARG
            tgt = link.end
        edges.append(_Edge(link.start, tgt, link.role, mode))
    return edges

def _build_nodes(x):
    nodes = []
    for n in x.nodes:
        sortinfo = [(CVARSORT, n.type)] + list(n.properties.items())
        nodes.append(Node(
            n.nodeid, n.predicate, sortinfo, n.carg,
            n.lnk, n.surface, n.base))
    return nodes

def _build_links(x, reps):
    links = []
    scopemap = x.scopemap
    for edge in x.edges:
        src, tgt, role, mode = edge.start, edge.end, edge.role, edge.mode
        if mode == _Edge.VARARG:
            post = EQ_POST if scopemap[src] == scopemap[tgt] else NEQ_POST
        elif mode == _Edge.LBLARG:
            tgt = reps[tgt][0]
            post = HEQ_POST
        elif mode == _Edge.QEQARG:
            tgt = reps[tgt][0]
            post = H_POST
        # elif mode == _Edge.UNEXPR:
        #     ...
        else:
            raise ValueError('invalid XMRS edge: ({}, {}, {}, {})'
                             .format(src, tgt, role, mode))
        links.append(Link(src, tgt, role, post))
    return links
