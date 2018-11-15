
import logging
import re
from collections import namedtuple

from delphin.exceptions import XmrsError
from delphin.util import deprecated


# The classes below are generally just namedtuples with extra methods.
# The namedtuples sometimes have default values. thanks:
#   http://stackoverflow.com/a/16721002/1441112

# FUNCTIONS FOR ROLES AND PROPERTIES

def role_priority(role):
    """Return a representation of role priority for ordering."""
    # canonical order: LBL ARG* RSTR BODY *-INDEX *-HNDL CARG ...
    role = role.upper()
    return (
        role != 'LBL',
        role in ('BODY', 'CARG'),
        role
    )


def property_priority(prop):
    """Return a representation of property priority for ordering."""
    prop = prop.upper()
    proplist = (
        'PERS', 'NUM', 'GEND', 'IND', 'PT', 'PRONTYPE',
        'SF', 'TENSE', 'MOOD', 'PROG', 'PERF', 'ASPECT', 'PASS'
    )
    try:
        return (proplist.index(prop), prop)
    except ValueError:
        return (len(proplist), prop)

# LNKS

class Lnk(namedtuple('Lnk', ('type', 'data'))):
    """
    Surface-alignment information for predications.

    Lnk objects link predicates to the surface form in one of several
    ways, the most common of which being the character span of the
    original string.

    Args:
        type: the way the Lnk relates the semantics to the surface form
        data: the Lnk specifiers, whose quality depends on *type*
    Attributes:
        type: the way the Lnk relates the semantics to the surface form
        data: the Lnk specifiers, whose quality depends on *type*
    Note:
        Valid *types* and their associated *data* shown in the table
        below.

        =========  ===================  =========
        type       data                 example
        =========  ===================  =========
        charspan   surface string span  (0, 5)
        chartspan  chart vertex span    (0, 5)
        tokens     token identifiers    (0, 1, 2)
        edge       edge identifier      1
        =========  ===================  =========


    Example:
        Lnk objects should be created using the classmethods:

        >>> Lnk.charspan(0,5)
        '<0:5>'
        >>> Lnk.chartspan(0,5)
        '<0#5>'
        >>> Lnk.tokens([0,1,2])
        '<0 1 2>'
        >>> Lnk.edge(1)
        '<@1>'
    """

    # These types determine how a lnk on an EP or MRS are to be
    # interpreted, and thus determine the data type/structure of the
    # lnk data.
    CHARSPAN = 0  # Character span; a pair of offsets
    CHARTSPAN = 1  # Chart vertex span: a pair of indices
    TOKENS = 2  # Token numbers: a list of indices
    EDGE = 3  # An edge identifier: a number

    def __init__(self, type, data):
        # class methods below use __new__ to instantiate data, so
        # don't do it here
        if type not in (Lnk.CHARSPAN, Lnk.CHARTSPAN, Lnk.TOKENS, Lnk.EDGE):
            raise XmrsError('Invalid Lnk type: {}'.format(type))

    @classmethod
    def charspan(cls, start, end):
        """
        Create a Lnk object for a character span.

        Args:
            start: the initial character position (cfrom)
            end: the final character position (cto)
        """
        return cls(Lnk.CHARSPAN, (int(start), int(end)))

    @classmethod
    def chartspan(cls, start, end):
        """
        Create a Lnk object for a chart span.

        Args:
            start: the initial chart vertex
            end: the final chart vertex
        """
        return cls(Lnk.CHARTSPAN, (int(start), int(end)))

    @classmethod
    def tokens(cls, tokens):
        """
        Create a Lnk object for a token range.

        Args:
            tokens: a list of token identifiers
        """
        return cls(Lnk.TOKENS, tuple(map(int, tokens)))

    @classmethod
    def edge(cls, edge):
        """
        Create a Lnk object for an edge (used internally in generation).

        Args:
            edge: an edge identifier
        """
        return cls(Lnk.EDGE, int(edge))

    def __str__(self):
        if self.type == Lnk.CHARSPAN:
            return '<{}:{}>'.format(self.data[0], self.data[1])
        elif self.type == Lnk.CHARTSPAN:
            return '<{}#{}>'.format(self.data[0], self.data[1])
        elif self.type == Lnk.EDGE:
            return '<@{}>'.format(self.data)
        elif self.type == Lnk.TOKENS:
            return '<{}>'.format(' '.join(map(str, self.data)))

    def __repr__(self):
        return '<Lnk object {} at {}>'.format(str(self), id(self))

    def __eq__(self, other):
        return self.type == other.type and self.data == other.data


class _LnkMixin(object):
    """
    A mixin class for adding `cfrom` and `cto` properties on structures.

    By far the most common :class:`Lnk` type is for character spans,
    and these spans are conveniently described by `cfrom` and `cto`
    properties. This mixin is used by larger structures, such as
    :class:`ElementaryPredication`, :class:`Node`, and
    :class:`~delphin.mrs.xmrs.Xmrs`, to add `cfrom` and `cto`
    properties. These properties exist regardless of the whether the
    Lnk is a character span or not; if not, or if Lnk information is
    missing, they return the default value of `-1`.
    """

    __slots__ = ()

    @property
    def cfrom(self):
        """
        The initial character position in the surface string.

        Defaults to -1 if there is no valid cfrom value.
        """
        cfrom = -1
        try:
            if self.lnk.type == Lnk.CHARSPAN:
                cfrom = self.lnk.data[0]
        except AttributeError:
            pass  # use default cfrom of -1
        return cfrom

    @property
    def cto(self):
        """
        The final character position in the surface string.

        Defaults to -1 if there is no valid cto value.
        """
        cto = -1
        try:
            if self.lnk.type == Lnk.CHARSPAN:
                cto = self.lnk.data[1]
        except AttributeError:
            pass  # use default cto of -1
        return cto


# PREDICATES AND PREDICATIONS


class Predicate(namedtuple('Predicate', 'type lemma pos sense string')):
    """
    A semantic predicate.

    **Abstract** predicates don't begin with an underscore, and they
    generally are defined as types in a grammar. **Surface** predicates
    always begin with an underscore (ignoring possible quotes), and are
    often defined as strings in a lexicon.

    In PyDelphin, Predicates are equivalent if they have the same lemma,
    pos, and sense, and are both abstract or both surface preds. Other
    factors are ignored for comparison, such as their being surface-,
    abstract-, or real-preds, whether they are quoted or not, whether
    they end with `_rel` or not, or differences in capitalization.
    Hashed Predicate objects (e.g., in a dict or set) also use the
    normalized form. However, unlike with equality comparisons,
    Predicate-formatted strings are not treated as equivalent in a hash.

    Args:
        type: the type of predicate; valid values are
            Predicate.ABSTRACT, Predicate.REALPRED, and
            Predicate.SURFACE, although in practice Predicates are
            instantiated via classmethods that select the type
        lemma: the lemma of the predicate
        pos: the part-of-speech; a single, lowercase character
        sense: the (often omitted) sense of the predicate
    Returns:
        a Predicate object
    Attributes:
        type: predicate type (Predicate.ABSTRACT,
            Predicate.REALPRED, and Predicate.SURFACE)
        lemma: lemma component of the predicate
        pos: part-of-speech component of the predicate
        sense: sense component of the predicate
    Example:
        Predicates are compared using their string representations.
        Surrounding quotes (double or single) are ignored, and
        capitalization doesn't matter. In addition, preds may be
        compared directly to their string representations:

        >>> p1 = Predicate.surface('_dog_n_1_rel')
        >>> p2 = Predicate.realpred(lemma='dog', pos='n', sense='1')
        >>> p3 = Predicate.abstract('dog_n_1_rel')
        >>> p1 == p2
        True
        >>> p1 == '_dog_n_1_rel'
        True
        >>> p1 == p3
        False
    """
    pred_re = re.compile(
        r'_?(?P<lemma>.*?)_'  # match until last 1 or 2 parts
        r'((?P<pos>[a-z])_)?'  # pos is always only 1 char
        r'((?P<sense>([^_\\]|(?:\\.))+)_)?'  # no unescaped _s
        r'(?P<end>rel)$',
        re.IGNORECASE
    )
    # Predicate types (used mainly in I/O, not internally in PyDelphin)
    ABSTRACT = GRAMMARPRED = 0  # only a string allowed (quoted or not)
    REALPRED = 1  # may explicitly define lemma, pos, sense
    SURFACE = STRINGPRED = 2  # quoted string form of realpred

    def __eq__(self, other):
        if other is None:
            return False
        if not isinstance(other, Predicate):
            other = Predicate.surface(other)
        return self.short_form().lower() == other.short_form().lower()

    def __str__ (self):
        return self.string

    def __repr__(self):
        return '<Predicate object {} at {}>'.format(self.string, id(self))

    def __hash__(self):
        return hash(self.short_form())

    @classmethod
    @deprecated(final_version='1.0.0', alternative='Predicate.surface()')
    def stringpred(cls, predstr):
        """Instantiate a Predicate from its quoted string representation."""
        return cls.surface(predstr)

    @classmethod
    def surface(cls, predstr):
        """Instantiate a Predicate from its quoted string representation."""
        lemma, pos, sense, _ = split_pred_string(predstr)
        return cls(Predicate.SURFACE, lemma, pos, sense, predstr)

    @classmethod
    @deprecated(final_version='1.0.0', alternative='Predicate.abstract()')
    def grammarpred(cls, predstr):
        """Instantiate a Predicate from its symbol string."""
        return cls.abstract(predstr)

    @classmethod
    def abstract(cls, predstr):
        """Instantiate a Predicate from its symbol string."""
        lemma, pos, sense, _ = split_pred_string(predstr)
        return cls(Predicate.ABSTRACT, lemma, pos, sense, predstr)

    @classmethod
    @deprecated(final_version='1.0.0',
                alternative='Predicate.surface_or_abstract()')
    def string_or_grammar_pred(cls, predstr):
        """Instantiate a Predicate from either its surface or abstract symbol."""
        return cls.surface_or_abstract(predstr)

    @classmethod
    def surface_or_abstract(cls, predstr):
        """Instantiate a Predicate from either its surface or abstract symbol."""
        if predstr.strip('"').lstrip("'").startswith('_'):
            return cls.surface(predstr)
        else:
            return cls.abstract(predstr)

    @classmethod
    def realpred(cls, lemma, pos, sense=None):
        """Instantiate a Predicate from its components."""
        string_tokens = [lemma]
        if pos is not None:
            string_tokens.append(pos)
        if sense is not None:
            sense = str(sense)
            string_tokens.append(sense)
        predstr = '_'.join([''] + string_tokens + ['rel'])
        return cls(Predicate.REALPRED, lemma, pos, sense, predstr)

    def short_form(self):
        """
        Return the pred string without quotes or a `_rel` suffix.

        The short form is the same as the normalized form from
        :func:`normalize_pred_string`.

        Example:

            >>> p = Predicate.surface('"_cat_n_1_rel"')
            >>> p.short_form()
            '_cat_n_1'
        """
        return normalize_pred_string(self.string)

    @deprecated(final_version='1.0.0')
    def is_quantifier(self):
        """
        Return `True` if the predicate has a quantifier part-of-speech.

        *Deprecated since v0.6.0*
        """
        return self.pos.lower() == 'q'


def split_pred_string(predstr):
    """
    Split *predstr* and return the (lemma, pos, sense, suffix) components.

    Examples:
        >>> Predicate.split_pred_string('_dog_n_1_rel')
        ('dog', 'n', '1', 'rel')
        >>> Predicate.split_pred_string('quant_rel')
        ('quant', None, None, 'rel')
    """
    predstr = predstr.strip('"\'')  # surrounding quotes don't matter
    rel_added = False
    if not predstr.lower().endswith('_rel'):
        logging.debug('Predicate does not end in "_rel": {}'
                      .format(predstr))
        rel_added = True
        predstr += '_rel'
    match = Predicate.pred_re.search(predstr)
    if match is None:
        logging.debug('Unexpected predicate string: {}'.format(predstr))
        return (predstr, None, None, None)
    # _lemma_pos(_sense)?_end
    return (match.group('lemma'), match.group('pos'),
            match.group('sense'), None if rel_added else match.group('end'))


def is_valid_pred_string(predstr):
    """
    Return `True` if *predstr* is a valid predicate string.

    Examples:
        >>> is_valid_pred_string('"_dog_n_1_rel"')
        True
        >>> is_valid_pred_string('_dog_n_1')
        True
        >>> is_valid_pred_string('_dog_noun_1')
        False
        >>> is_valid_pred_string('dog_noun_1')
        True
    """
    predstr = predstr.strip('"').lstrip("'")
    # this is a stricter regex than in Predicate, but doesn't check POS
    return re.match(
        r'_([^ _\\]|\\.)+_[a-z](_([^ _\\]|\\.)+)?(_rel)?$'
        r'|[^_]([^ \\]|\\.)+(_rel)?$',
        predstr
    ) is not None


def normalize_pred_string(predstr):
    """
    Normalize the predicate string *predstr* to a conventional form.

    This makes predicate strings more consistent by removing quotes and
    the `_rel` suffix, and by lowercasing them.

    Examples:
        >>> normalize_pred_string('"_dog_n_1_rel"')
        '_dog_n_1'
        >>> normalize_pred_string('_dog_n_1')
        '_dog_n_1'
    """
    tokens = [t for t in split_pred_string(predstr)[:3] if t is not None]
    if predstr.lstrip('\'"')[:1] == '_':
        tokens = [''] + tokens
    return '_'.join(tokens).lower()


class _Node(_LnkMixin):

    __slots__ = ('nodeid', 'predicate', 'type',
                 'properties', 'carg',
                 'lnk', 'surface', 'base')

    def __init__(self, nodeid, predicate, type=None,
                 properties=None, carg=None,
                 lnk=None, surface=None, base=None):
        self.nodeid = nodeid
        self.predicate = predicate
        self.type = type
        if properties is None:
            properties = {}
        self.properties = properties
        self.carg = carg
        self.lnk = lnk
        self.surface = surface
        self.base = base

    @classmethod
    def unexpressed(cls, nodeid, type, properties=None):
        return cls(nodeid, None, type, properties)

    def __repr__(self):
        return '<{} object ({} [{}{}]{}) at {}>'.format(
            self.__class__.__name__,
            self.nodeid,
            str(self.predicate),
            str(self.lnk) if self.lnk is not None else '',
            ' "{}"'.format(self.carg) if self.carg is not None else '',
            id(self)
        )

    def __eq__(self, other):
        if not isinstance(other, _Node):
            return NotImplemented
        return (self.predicate == other.predicate and
                self.type == other.type and
                self.properties == other.properties and
                self.carg == other.carg)

    def __ne__(self, other):
        if not isinstance(other, _Node):
            return NotImplemented
        return not self.__eq__(other)


class _Edge(object):

    __slots__ = ('start', 'end', 'role', 'mode')

    # edge "modes"
    UNSPEC = 0  # mode is unspecified
    INTARG = 1  # intrinsic argument ('end' is variable)
    VARARG = 2  # regular variable argument
    LBLARG = 3  # argument is a scope identifier
    QEQARG = 4  # argument is qeq to a scope identifier
    UNEXPR = 5  # argument is unexpressed ('end' is variable)

    def __init__(self, start, end, role, mode):
        self.start = start
        self.end = end
        self.role = role
        self.mode = mode

    def __repr__(self):
        return '<{} object ({} -{}-> {}) at {}>'.format(
            self.__class__.__name__,
            self.start,
            self.role,
            self.end,
            id(self))


class _IndividualConstraint(object):

    __slots__ = ('left', 'relation', 'right')

    def __init__(self, left, relation, right):
        self.left = left
        self.relation = relation
        self.right = right


class _SemanticComponent(_LnkMixin):

    __slots__ = ('top', 'index', 'xarg', 'lnk', 'surface', 'identifier')

    def __init__(self, top, index, xarg, lnk, surface, identifier):
        self.top = top
        self.index = index
        self.xarg = xarg
        self.lnk = lnk
        self.surface = surface
        self.identifier = identifier


class _XMRS(_SemanticComponent):
    """
    Args:
        top (int): scopeid of top scope
        index (str): nodeid of top predication
        xarg (str): nodeid of external argument
        nodes (list): list of :class:`_Node` objects
        scopes (dict): map of scopeid (e.g., a label) to a set of nodeids
        edges (list): list of (nodeid, role, mode, target) tuples
        icons (list): list of (source, relation, target) tuples
        lnk: surface alignment of the whole structure
        surface: surface form of the whole structure
        identifier: corpus-level identifier
    """
    def __init__(self, top, index, xarg,
                 nodes, scopes, edges, icons,
                 lnk, surface, identifier):
        super(_XMRS, self).__init__(top, index, xarg, lnk, surface, identifier)
        self.nodes = nodes
        self.scopes = scopes
        self.edges = edges
        self.icons = icons

        self.nodemap = {node.nodeid: node for node in nodes}

        self.scopemap = {}
        for scopeid, nodeids in scopes.items():
            for nodeid in nodeids:
                self.scopemap[nodeid] = scopeid
        self._nested_scopes = {}
        self._scope_reps = {}

        self.edgemap = {node.nodeid: {} for node in nodes}
        self.quantifiermap = {}
        self.ivmap = {}
        for edge in self.edges:
            self.edgemap[edge.start][edge.role] = edge
            if edge.role == 'RSTR':
                self.quantifiermap[edge.start] = edge.end
            elif edge.mode == _Edge.INTARG:
                self.ivmap[edge.start] = edge.end

    def is_quantifier(self, nodeid):
        return nodeid in self.quantifiermap

    def scope_representative(self, scopeid):
        reps = self.scope_representatives(scopeid)
        if reps:
            return reps[0]
        return None

    def scope_representatives(self, scopeid):
        if scopeid not in self._scope_reps:
            scope_nodeids = self.scopes[scopeid]
            if len(scope_nodeids) == 1:
                self._scope_reps[scopeid] = list(scope_nodeids)
            else:
                nested_scope = self._nested_scope(scopeid)
                candidates = []
                for nodeid in scope_nodeids:
                    edges = [edge for edge in self.edgemap.get(nodeid, [])
                             if edge.mode == _Edge.VARARG]
                    if all(edge.end not in nested_scope for edge in edges):
                        candidates.append(nodeid)
                if len(candidates) > 1:
                    qs = set(self.qeqmap).union(self.qeqmap.values())
                    rank = {}
                    for nodeid in candidates:
                        node = self.nodemap[nodeid]
                        if nodeid in qs:
                            rank[nodeid] = 0
                        elif node.predicate.type == Predicate.ABSTRACT:
                            rank[nodeid] = 2
                        elif nodeid :
                            rank[nodeid] = 1
                    candidates.sort(key=lambda n: rank[n])
                self._scope_reps = candidates
        return self._scope_reps[scopeid]

    def _nested_scope(self, scopeid):
        if scopeid not in self._nested_scopes:
            self._nested_scopes[scopeid] = ns = set(self.scopes[scopeid])
            for nodeid in list(ns):
                for edge in self.edgemap.get(nodeid, []):
                    if edge.mode in (_Edge.LBLARG, _Edge.QEQARG):
                        ns.update(self._nested_scope(edge.end))
        return self._nested_scopes[scopeid]
