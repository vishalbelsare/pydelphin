
"""
Classes and functions for working with the components of \*MRS objects.
"""

import re
import logging
import warnings
from collections import namedtuple, MutableMapping
from itertools import starmap

from delphin.exceptions import (XmrsError, XmrsStructureError)
from delphin.util import deprecated
from .config import (
    IVARG_ROLE, CONSTARG_ROLE, RSTR_ROLE,
    UNKNOWNSORT, HANDLESORT, CVARSORT, QUANTIFIER_POS,
    EQ_POST, HEQ_POST, NEQ_POST, H_POST,
    BARE_EQ_ROLE
)
# for backward compatibility
from delphin.sembase import (
    Lnk,
    _LnkMixin,
    Predicate as Pred,
    split_pred_string,
    is_valid_pred_string,
    normalize_pred_string)

# The classes below are generally just namedtuples with extra methods.
# The namedtuples sometimes have default values. thanks:
#   http://stackoverflow.com/a/16721002/1441112


# VARIABLES and LNKS

var_re = re.compile(r'^([-\w]*\D)(\d+)$')


@deprecated(final_version='1.0.0', alternative='delphin.mrs.var_split')
def sort_vid_split(vs):
    """
    Split a valid variable string into its variable sort and id.

    Examples:
        >>> sort_vid_split('h3')
        ('h', '3')
        >>> sort_vid_split('ref-ind12')
        ('ref-ind', '12')
    """
    match = var_re.match(vs)
    if match is None:
        raise ValueError('Invalid variable string: {}'.format(str(vs)))
    else:
        return match.groups()


@deprecated(final_version='1.0.0', alternative='delphin.mrs.var_sort')
def var_sort(v):
    """
    Return the sort of a valid variable string.

    Examples:
        >>> var_sort('h3')
        'h'
        >>> var_sort('ref-ind12')
        'ref-ind'
    """
    return sort_vid_split(v)[0]


@deprecated(final_version='1.0.0', alternative='delphin.mrs.var_id')
def var_id(v):
    """
    Return the integer id of a valid variable string.

    Examples:
        >>> var_id('h3')
        3
        >>> var_id('ref-ind12')
        12
    """
    return int(sort_vid_split(v)[1])


class _VarGenerator(object):
    """
    Simple class to produce variables, incrementing the vid for each
    one.
    """

    @deprecated(final_version='1.0.0', alternative='delphin.msr._VarGenerator')
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


# LINKS and CONSTRAINTS

class Link(namedtuple('Link', ('start', 'end', 'rargname', 'post'))):
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
    @deprecated(final_version='1.0.0', alternative='delphin.dmrs.Link')
    def __new__(cls, start, end, rargname, post):
        return super(Link, cls).__new__(
            cls, start, end, rargname, post
        )

    def __repr__(self):
        return '<Link object (#{} :{}/{}> #{}) at {}>'.format(
            self.start, self.rargname or '', self.post, self.end, id(self)
        )


@deprecated(final_version='1.0.0')
def links(xmrs):
    """Return the list of Links for the *xmrs*."""

    # Links exist for every non-intrinsic argument that has a variable
    # that is the intrinsic variable of some other predicate, as well
    # as for label equalities when no argument link exists (even
    # considering transitivity).
    links = []
    prelinks = []

    _eps = xmrs._eps
    _hcons = xmrs._hcons
    _vars = xmrs._vars

    lsh = xmrs.labelset_heads
    lblheads = {v: lsh(v) for v, vd in _vars.items() if 'LBL' in vd['refs']}

    top = xmrs.top
    if top is not None:
        prelinks.append((0, top, None, top, _vars[top]))

    for nid, ep in _eps.items():
        for role, val in ep[3].items():
            if role == IVARG_ROLE or val not in _vars:
                continue
            prelinks.append((nid, ep[2], role, val, _vars[val]))

    for src, srclbl, role, val, vd in prelinks:
        if IVARG_ROLE in vd['refs']:
            tgtnids = [n for n in vd['refs'][IVARG_ROLE]
                       if not _eps[n].is_quantifier()]
            if len(tgtnids) == 0:
                continue  # maybe some bad MRS with a lonely quantifier
            tgt = tgtnids[0]  # what do we do if len > 1?
            tgtlbl = _eps[tgt][2]
            post = EQ_POST if srclbl == tgtlbl else NEQ_POST
        elif val in _hcons:
            lbl = _hcons[val][2]
            if lbl not in lblheads or len(lblheads[lbl]) == 0:
                continue  # broken MRS; log this?
            tgt = lblheads[lbl][0]  # sorted list; first item is most "heady"
            post = H_POST
        elif 'LBL' in vd['refs']:
            if val not in lblheads or len(lblheads[val]) == 0:
                continue  # broken MRS; log this?
            tgt = lblheads[val][0]  # again, should be sorted already
            post = HEQ_POST
        else:
            continue  # CARGs, maybe?
        links.append(Link(src, tgt, role, post))

    # now EQ links unattested by arg links
    for lbl, heads in lblheads.items():
        # I'm pretty sure this does what we want
        if len(heads) > 1:
            first = heads[0]
            for other in heads[1:]:
                links.append(Link(other, first, BARE_EQ_ROLE, EQ_POST))
        # If not, something like this is more explicit
        # lblset = self.labelset(lbl)
        # sg = g.subgraph(lblset)
        # ns = [nid for nid, deg in sg.degree(lblset).items() if deg == 0]
        # head = self.labelset_head(lbl)
        # for n in ns:
        #     links.append(Link(head, n, post=EQ_POST))
    def _int(x):
        try:
            return int(x)
        except ValueError:
            return 0
    return sorted(
        links,
        key=lambda link: (_int(link.start), _int(link.end), link.rargname)
    )


class HandleConstraint(
        namedtuple('HandleConstraint', ('hi', 'relation', 'lo'))):
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

    @deprecated(final_version='1.0.0',
                alternative='delphin.mrs.HandleConstraint')
    def __init__(self, hi, relation, lo):
        pass

    QEQ = 'qeq'  # Equality modulo Quantifiers
    LHEQ = 'lheq'  # Label-Handle Equality
    OUTSCOPES = 'outscopes'  # Outscopes

    @classmethod
    def qeq(cls, hi, lo):
        return cls(hi, HandleConstraint.QEQ, lo)

    def __repr__(self):
        return '<HandleConstraint object ({} {} {}) at {}>'.format(
               str(self.hi), self.relation, str(self.lo), id(self)
        )


@deprecated(final_version='1.0.0')
def hcons(xmrs):
    """Return the list of all HandleConstraints in *xmrs*."""
    return [
        HandleConstraint(hi, reln, lo)
        for hi, reln, lo in sorted(xmrs.hcons(), key=lambda hc: var_id(hc[0]))
    ]


class IndividualConstraint(
        namedtuple('IndividualConstraint', ['left', 'relation', 'right'])):
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
    @deprecated(final_version='1.0.0',
                alternative='delphin.mrs.IndividualConstraint')
    def __init__(self, left, relation, right):
        pass


@deprecated(final_version='1.0.0')
def icons(xmrs):
    """Return the list of all IndividualConstraints in *xmrs*."""
    return [
        IndividualConstraint(left, reln, right)
        for left, reln, right in sorted(xmrs.icons(),
                                        key=lambda ic: var_id(ic[0]))
    ]


# NODES AND PREDICATIONS

class Node(
    namedtuple('Node', ('nodeid', 'pred', 'sortinfo',
                        'lnk', 'surface', 'base', 'carg')),
    _LnkMixin):
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

    @deprecated(final_version='1.0.0', alternative='delphin.dmrs.Node')
    def __new__(cls, nodeid, pred, sortinfo=None,
                 lnk=None, surface=None, base=None, carg=None):
        if sortinfo is None:
            sortinfo = {}
        elif not isinstance(sortinfo, MutableMapping):
            sortinfo = dict(sortinfo)
        return super(Node, cls).__new__(
            cls, nodeid, pred, sortinfo, lnk, surface, base, carg
        )

    def __repr__(self):
        lnk = ''
        if self.lnk is not None:
            lnk = str(self.lnk)
        return '<Node object ({} [{}{}]) at {}>'.format(
            self.nodeid, self.pred.string, lnk, id(self)
        )

    # note: without overriding __eq__, comparisons of sortinfo will be
    #       be different if they are OrderedDicts and not in the same
    #       order. Maybe this isn't a big deal?
    # def __eq__(self, other):
    #     # not doing self.__dict__ == other.__dict__ right now, because
    #     # functions like self.get_property show up there
    #     snid = self.nodeid
    #     onid = other.nodeid
    #     return ((None in (snid, onid) or snid == onid) and
    #             self.pred == other.pred and
    #             # make one side a regular dict for unordered comparison
    #             dict(self.sortinfo.items()) == other.sortinfo and
    #             self.lnk == other.lnk and
    #             self.surface == other.surface and
    #             self.base == other.base and
    #             self.carg == other.carg)

    def __lt__(self, other):
        warnings.warn("Deprecated", DeprecationWarning)
        x1 = (self.cfrom, self.cto, self.pred.pos != QUANTIFIER_POS,
              self.pred.lemma)
        try:
            x2 = (other.cfrom, other.cto, other.pred.pos != QUANTIFIER_POS,
                  other.pred.lemma)
            return x1 < x2
        except AttributeError:
            return NotImplemented

    @property
    def cvarsort(self):
        """
        The "variable" type of the predicate.

        Note:
          DMRS does not use variables, but it is useful to indicate
          whether a node is an individual, eventuality, etc., so this
          property encodes that information.
        """
        return self.sortinfo.get(CVARSORT)

    @cvarsort.setter
    def cvarsort(self, value):
        self.sortinfo[CVARSORT] = value

    @property
    def properties(self):
        """
        Morphosemantic property mapping.

        Unlike :attr:`sortinfo`, this does not include `cvarsort`.
        """
        d = dict(self.sortinfo)
        if CVARSORT in d:
            del d[CVARSORT]
        return d

    def is_quantifier(self):
        """
        Return `True` if the Node's predicate appears to be a quantifier.

        *Deprecated since v0.6.0*
        """
        warnings.warn(
            'Deprecated; try checking xmrs.nodeids(quantifier=True)',
            DeprecationWarning
        )
        return self.pred.is_quantifier()


@deprecated(final_version='1.0.0')
def nodes(xmrs):
    """Return the list of Nodes for *xmrs*."""
    nodes = []
    _props = xmrs.properties
    varsplit = sort_vid_split
    for p in xmrs.eps():
        sortinfo = None
        iv = p.intrinsic_variable
        if iv is not None:
            sort, _ = varsplit(iv)
            sortinfo = _props(iv)
            sortinfo[CVARSORT] = sort
        nodes.append(
            Node(p.nodeid, p.pred, sortinfo, p.lnk, p.surface, p.base, p.carg)
        )
    return nodes


class ElementaryPredication(
    namedtuple('ElementaryPredication',
               ('nodeid', 'pred', 'label', 'args', 'lnk', 'surface', 'base')),
    _LnkMixin):
    """
    An MRS elementary predication (EP).

    EPs combine a predicate with various structural semantic
    properties. They must have a `nodeid`, `pred`, and `label`.
    Arguments and other properties are optional. Note nodeids are not a
    formal property of MRS (unlike DMRS, or the "anchors" of RMRS), but
    they are required for Pydelphin to uniquely identify EPs in an
    :class:`~delphin.mrs.xmrs.Xmrs`. Intrinsic arguments (`ARG0`) are
    not required, but they are important for many semantic operations,
    and therefore it is a good idea to include them.

    Args:
        nodeid: a nodeid
        pred (:class:`Pred`): semantic predicate
        label (str): scope handle
        args (dict, optional): mapping of roles to values
        lnk (:class:`Lnk`, optional): surface alignment
        surface (str, optional): surface string
        base (str, optional): base form
    Attributes:
        nodeid: a nodeid
        pred (:class:`Pred`): semantic predicate
        label (str): scope handle
        args (dict): mapping of roles to values
        lnk (:class:`Lnk`): surface alignment
        surface (str): surface string
        base (str): base form
        cfrom (int): surface alignment starting position
        cto (int): surface alignment ending position
    """

    @deprecated(final_version='1.0.0',
                alternative='delphin.mrs.ElementaryPredication')
    def __new__(cls, nodeid, pred, label, args=None,
                 lnk=None, surface=None, base=None):
        if args is None:
            args = {}
        # else:
        #     args = dict((a.rargname, a) for a in args)
        return super(ElementaryPredication, cls).__new__(
            cls, nodeid, pred, label, args, lnk, surface, base
        )

    def __repr__(self):
        return '<ElementaryPredication object ({} ({})) at {}>'.format(
            self.pred.string, str(self.iv or '?'), id(self)
        )

    def __lt__(self, other):
        warnings.warn("Deprecated", DeprecationWarning)
        x1 = (self.cfrom, self.cto, -self.is_quantifier(), self.pred.lemma)
        try:
            x2 = (other.cfrom, other.cto, -other.is_quantifier(),
                  other.pred.lemma)
            return x1 < x2
        except AttributeError:
            return NotImplemented

    # these properties are specific to the EP's qualities

    @property
    def intrinsic_variable(self):
        """
        The value of the intrinsic argument (likely `ARG0`).
        """
        if IVARG_ROLE in self.args:
            return self.args[IVARG_ROLE]
        return None

    #: A synonym for :attr:`ElementaryPredication.intrinsic_variable`
    iv = intrinsic_variable

    @property
    def carg(self):
        """
        The value of the constant argument.
        """
        return self.args.get(CONSTARG_ROLE, None)

    def is_quantifier(self):
        """
        Return `True` if this is a quantifier predication.
        """
        return RSTR_ROLE in self.args


@deprecated(final_version='1.0.0')
def elementarypredications(xmrs):
    """
    Return the list of :class:`ElementaryPredication` objects in *xmrs*.
    """
    return list(starmap(ElementaryPredication, xmrs.eps()))


@deprecated(final_version='1.0.0')
def elementarypredication(xmrs, nodeid):
    """
    Retrieve the elementary predication with the given nodeid.

    Args:
        nodeid: nodeid of the EP to return
    Returns:
        :class:`ElementaryPredication`
    Raises:
        :py:exc:`KeyError` if no EP matches
    """
    return ElementaryPredication(*xmrs.ep(nodeid))
