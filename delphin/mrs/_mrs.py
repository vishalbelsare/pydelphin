
import re

from delphin.sembase import (
    _Node,
    _Edge,
    _IndividualConstraint,
    _SemanticComponent,
    _XMRS)

from delphin.util import accdict


UNKNOWNSORT    = 'u' # when nothing is known about the sort
HANDLESORT     = 'h' # for scopal relations
IVARG_ROLE     = 'ARG0'
RSTR_ROLE      = 'RSTR'
BODY_ROLE      = 'BODY'
CONSTARG_ROLE  = 'CARG'


class EP(_Node):
    """
    An MRS elementary predication (EP).

    EPs combine a predicate with various structural semantic
    properties. They must have a `predicate`, and `label`.
    Arguments and other properties are optional. Note nodeids are not a
    formal property of MRS (unlike DMRS, or the "anchors" of RMRS), but
    they are required for Pydelphin to uniquely identify EPs in an
    :class:`~delphin.mrs.xmrs.Xmrs`. Intrinsic arguments (`ARG0`) are
    not required, but they are important for many semantic operations,
    and therefore it is a good idea to include them.

    Args:
        predicate (:class:`Predicate`): semantic predicate
        label (str): scope handle
        args (dict, optional): mapping of roles to values
        carg (str, optional): constant argument
        lnk (:class:`Lnk`, optional): surface alignment
        surface (str, optional): surface string
        base (str, optional): base form
    Attributes:
        nodeid: a nodeid
        predicate (:class:`Predicate`): semantic predicate
        label (str): scope handle
        args (dict): mapping of roles to values
        carg (str): constant argument
        lnk (:class:`Lnk`): surface alignment
        surface (str): surface string
        base (str): base form
        cfrom (int): surface alignment starting position
        cto (int): surface alignment ending position
    """

    __slots__ = ('label', 'args')
    def __init__(self, predicate, label, args=None, carg=None,
                 lnk=None, surface=None, base=None):
        nodeid = None
        if args is None:
            args = {}
        type = var_sort(args.get(IVARG_ROLE, UNKNOWNSORT + '0'))
        properties = None
        super(EP, self).__init__(
            nodeid, predicate, type, properties, carg, lnk, surface, base)
        self.label = label
        self.args = args

    def __repr__(self):
        return '<{} object ({} ({})) at {}>'.format(
            self.__class__.__name__,
            self.predicate.string,
            str(self.iv or '?'),
            id(self)
        )

    # these properties are specific to the EP's qualities

    @property
    def intrinsic_variable(self):
        """
        The value of the intrinsic argument (likely `ARG0`).
        """
        if IVARG_ROLE in self.args:
            return self.args[IVARG_ROLE]
        return None

    #: A synonym for :attr:`EP.intrinsic_variable`
    iv = intrinsic_variable

    def is_quantifier(self):
        """
        Return `True` if this is a quantifier predication.
        """
        return RSTR_ROLE in self.args


class HCons(object):
    """
    A relation between two handles.

    Arguments:
        hi (str): hi handle (hole) of the constraint
        relation (str): relation of the constraint (nearly always
            `"qeq"`, but `"lheq"` and `"outscopes"` are also valid)
        lo (str): lo handle (label) of the constraint
    Attributes:
        hi (str): hi handle (hole) of the constraint
        relation (str): relation of the constraint
        lo (str): lo handle (label) of the constraint
    """

    __slots__ = ('hi', 'relation', 'lo')

    QEQ = 'qeq'  # Equality modulo Quantifiers
    LHEQ = 'lheq'  # Label-Handle Equality
    OUTSCOPES = 'outscopes'  # Outscopes

    def __init__(self, hi, relation, lo):
        self.hi = hi
        self.relation = relation
        self.lo = lo

    @classmethod
    def qeq(cls, hi, lo):
        return cls(hi, HCons.QEQ, lo)

    def __repr__(self):
        return '<HCons object ({} {} {}) at {}>'.format(
               str(self.hi), self.relation, str(self.lo), id(self)
        )


class ICons(_IndividualConstraint):
    """
    A relation between two variables.

    Arguments:
        left (str): left variable of the constraint
        relation (str): relation of the constraint
        right (str): right variable of the constraint
    Attributes:
        left (str): left variable of the constraint
        relation (str): relation of the constraint
        right (str): right variable of the constraint
    """


class MRS(_SemanticComponent):

    __slots__ = ('rels', 'hcons', 'icons', 'variables',
                 '_epidx', '_hcidx', '_icidx')

    def __init__(self, top=None, index=None, xarg=None,
                 rels=None, hcons=None, icons=None, variables=None,
                 lnk=None, surface=None, identifier=None):
        super(MRS, self).__init__(top, index, xarg, lnk, surface, identifier)
        if rels is None:
            rels = []
        if hcons is None:
            hcons = []
        if icons is None:
            icons = []
        if variables is None:
            variables = {}
        self.rels = rels
        self.hcons = hcons
        self.icons = icons
        self.variables = _fill_variables(
            variables, top, index, xarg, rels, hcons, icons)
        self._epidx = {ep.iv: ep for ep in rels if ep.iv is not None}
        self._hcidx = {hc.hi: hc for hc in hcons}
        self._icidx = {ic.left: ic for ic in icons}

    def to_xmrs(self):
        top = self.top
        if top in self._hcidx:
            top = self._hcidx[top].lo
        nodes, scopes, ivmap, next_nodeid = _build_xmrs_nodes_and_scopes(self)
        edges, unexpr_nodes = _build_xmrs_edges(
            self, nodes, scopes, ivmap, next_nodeid)
        nodes.extend(unexpr_nodes)
        icons = []
        for ic in self.icons:
            icons.append((nodemap.get(ic.left, ic.left),
                          ic.relation,
                          nodemap.get(ic.right, ic.right)))
        return _XMRS(top,
                     ivmap.get(self.index),
                     ivmap.get(self.xarg),
                     nodes,
                     scopes,
                     edges,
                     icons,
                     self.lnk,
                     self.surface,
                     self.identifier)

    @classmethod
    def from_xmrs(cls, x):
        # attempt to convert if necessary
        if not isinstance(x, _XMRS):
            x = x.to_xmrs()

        vgen = _VarGenerator(starting_vid=0)
        top = vgen.new('h')[0]
        lblmap, ivmap = _build_varmaps(x, vgen)
        rels, hcons = _build_structures(x, lblmap, ivmap, vgen)
        hcons = [HCons.qeq(top, lblmap[x.top])] + hcons
        icons = [ICons(ivmap[left], relation, ivmap[right])
                 for left, relation, right in x.icons]
        return cls(top=top,
                   index=ivmap.get(x.index),
                   xarg=ivmap.get(x.xarg),
                   rels=rels,
                   hcons=hcons,
                   icons=icons,
                   variables=vgen.store,
                   lnk=x.lnk,
                   surface=x.surface,
                   identifier=x.identifier)

    def properties(self, iv):
        return self.variables[iv]


def _fill_variables(vars, top, index, xarg, rels, hcons, icons):
    if top is not None and top not in vars:
        vars[top] = []
    if index is not None and index not in vars:
        vars[index] = []
    if xarg is not None and xarg not in vars:
        vars[xarg] = []
    for ep in rels:
        if ep.label not in vars:
            vars[ep.label] = []
        for role, value in ep.args.items():
            if role == IVARG_ROLE and not vars.get(value):
                vars[value] = list(ep.properties.items())
            elif role != CONSTARG_ROLE and value not in vars:
                vars[value] = []
    for hc in hcons:
        if hc.lo not in vars:
            vars[hc.lo] = []
        if hc.hi not in vars:
            vars[hc.hi] = []
    for ic in icons:
        if ic.left not in vars:
            vars[ic.left] = []
        if ic.right not in vars:
            vars[ic.right] = []
    return vars


def _build_xmrs_nodes_and_scopes(m):
    nodes = []
    ivmap = {}
    scopes = {}
    for i, ep in enumerate(m.rels, 10000):
        nodeid = str(i)
        if not ep.is_quantifier():
            ivmap[ep.iv] = nodeid
        scopes.setdefault(ep.label, set()).add(nodeid)
        nodes.append(_Node(nodeid,
                           ep.predicate,
                           ep.type,
                           m.properties(ep.iv),
                           carg=ep.carg,
                           lnk=ep.lnk,
                           surface=ep.surface,
                           base=ep.base))
    return nodes, scopes, ivmap, i + 1


def _build_xmrs_edges(m, nodes, scopes, ivmap, next_nodeid):
    edges = []
    unexpr_nodes = []
    for node, ep in zip(nodes, m.rels):
        for role, tgt in ep.args.items():
            if role == IVARG_ROLE and not ep.is_quantifier():
                edges.append(_Edge(node.nodeid, tgt, role, _Edge.INTARG))
            elif role not in (BODY_ROLE, CONSTARG_ROLE):
                if tgt in scopes:
                    mode = _Edge.LBLARG
                elif tgt in m._hcidx:
                    tgt = m._hcidx[tgt].lo
                    mode = _Edge.QEQARG
                elif tgt in ivmap:
                    tgt = ivmap[tgt]
                    mode = _Edge.VARARG
                else:
                    if tgt not in ivmap:
                        unexpr_nodeid = str(next_nodeid)
                        next_nodeid += 1
                        ivmap[tgt] = unexpr_nodeid
                        type = var_sort(tgt)
                        unexpr_nodes.append(_Node.unexpressed(
                            unexpr_nodeid, type,
                            dict(m.variables.get(tgt, []))))
                    tgt = ivmap[tgt]
                    mode = _Edge.UNEXPR
                edges.append(_Edge(node.nodeid, tgt, role, mode))
    return edges, unexpr_nodes


def _build_varmaps(x, vgen):
    lblmap = {}
    # use any explicit intrinsic variables
    ivmap = dict(x.ivmap)
    # for the rest, build new ones
    for scopeid, nodeids in x.scopes.items():
        label = lblmap.get(scopeid)
        if label is None:
            label = vgen.new(HANDLESORT)[0]
            lblmap[scopeid] = label
        for nodeid in nodeids:
            iv = ivmap.get(nodeid)
            if iv is None:
                node = x.nodemap[nodeid]
                iv = vgen.new(node.type, node.properties)[0]
                ivmap[nodeid] = iv
    return lblmap, ivmap


def _build_structures(x, lblmap, ivmap, vgen):
    rels = []
    hcons = []
    nodeedges = accdict((edge.start, edge) for edge in x.edges)
    for node in x.nodes:
        args = {}
        if node.type is not None:
            args[IVARG_ROLE] = ivmap[node.nodeid]
        for edge in nodeedges.get(node.nodeid, []):
            end, role, mode = edge.end, edge.role, edge.mode
            if mode == _Edge.VARARG:
                args[role] = ivmap[end]
            elif mode == _Edge.LBLARG:
                args[role] = lblmap[end]
            elif mode == _Edge.QEQARG:
                hole = vgen.new(HANDLESORT)[0]
                args[role] = hole
                hcons.append(HCons.qeq(hole, lblmap[end]))
            elif mode == _Edge.UNEXPR:
                if end not in ivmap:
                    unexpr = x.nodemap[end]
                    ivmap[end] = vgen.new(unexpr.type,
                                          unexpr.properties)[0]
                args[role] = ivmap[end]
        nodescope = x.scopemap[node.nodeid]
        label = lblmap[nodescope]
        rels.append(EP(
            node.predicate, label, args=args, carg=node.carg,
            lnk=node.lnk, surface=node.surface, base=node.base))
    return rels, hcons


# VARIABLES

var_re = re.compile(r'^([-\w]*\D)(\d+)$')


def var_split(vs):
    """
    Split a valid variable string into its variable sort and id.

    Examples:
        >>> var_split('h3')
        ('h', '3')
        >>> var_split('ref-ind12')
        ('ref-ind', '12')
    """
    match = var_re.match(vs)
    if match is None:
        raise ValueError('Invalid variable string: {}'.format(str(vs)))
    else:
        return match.groups()


def var_sort(v):
    """
    Return the sort of a valid variable string.

    Examples:
        >>> var_sort('h3')
        'h'
        >>> var_sort('ref-ind12')
        'ref-ind'
    """
    return var_split(v)[0]


def var_id(v):
    """
    Return the integer id of a valid variable string.

    Examples:
        >>> var_id('h3')
        3
        >>> var_id('ref-ind12')
        12
    """
    return int(var_split(v)[1])


class _VarGenerator(object):
    """
    Simple class to produce variables, incrementing the vid for each
    one.
    """

    def __init__(self, starting_vid=1):
        self.vid = starting_vid
        self.index = {}  # to map vid to created variable
        self.store = {}  # to recall properties from varstrings

    def new(self, sort, properties=None):
        """
        Create a new variable for the given *sort*.
        """
        if sort is None:
            sort = UNKNOWNSORT
        # find next available vid
        vid, index = self.vid, self.index
        while vid in index:
            vid += 1
        varstring = '{}{}'.format(sort, vid)
        index[vid] = varstring
        if properties is None:
            properties = []
        self.store[varstring] = properties
        self.vid = vid + 1
        return (varstring, properties)
