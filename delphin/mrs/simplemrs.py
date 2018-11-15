
"""
Serialization functions for the SimpleMRS format.
"""


# Author: Michael Wayne Goodman <goodmami@uw.edu>

import io
import re

from delphin.util import LookaheadIterator
from delphin.sembase import (
    Lnk, Predicate, role_priority, property_priority)
from delphin.mrs import (EP, HCons, ICons, MRS, var_sort)

TOP_FEATURE = 'TOP'

# versions are:
#  * 1.0 long running standard
#  * 1.1 added support for MRS-level lnk, surface and EP-level surface
_default_version = 1.1
_latest_version = 1.1

_valid_hcons = ['qeq', 'lheq', 'outscopes']

# pretty-print options
_default_mrs_delim = '\n'

##############################################################################
##############################################################################
# Pickle-API methods


def load(source):
    """
    Deserialize SimpleMRSs from a file (handle or filename)

    Args:
        source (str, file): input filename or file object
    Returns:
        a list of MRS objects
    """
    if hasattr(source, 'read'):
        ms = _decode(source)
    else:
        with open(source) as fh:
            ms = _decode(fh)
    return list(ms)


def loads(s, encoding='utf-8'):
    """
    Deserialize SimpleMRS string representations

    Args:
        s (str): a SimpleMRS string
    Returns:
        a list of MRS objects
    """
    ms = _decode(s.splitlines())
    return list(ms)


def dump(ms, destination, properties=True, indent=False, encoding='utf-8'):
    """
    Serialize MRS objects to SimpleMRS and write to a file

    Args:
        ms: an iterator of MRS objects to serialize
        destination: filename or file object where data will be written
        properties: if `False`, suppress morphosemantic properties
        indent (bool, int): if `True` or an integer value, add
            newlines and indentation
        encoding (str): if *destination* is a filename, write to the
            file with the given encoding; otherwise it is ignored
    """
    text = dumps(ms, properties=properties, indent=indent)
    if hasattr(destination, 'write'):
        print(text, file=destination)
    else:
        with io.open(destination, 'w', encoding=encoding) as fh:
            print(text, file=fh)


def dumps(ms, properties=True, indent=False):
    """
    Serialize MRS objects to a SimpleMRS representation

    Args:
        ms: an iterator of MRS objects to serialize
        properties: if `False`, suppress variable properties
        indent (bool, int): if `True` or an integer value, add
            newlines and indentation
    Returns:
        a SimpleMRS string representation of a corpus of MRS objects
    """
    return _encode(ms, properties=properties, indent=indent)


def decode(s):
    """
    Deserialize an MRS object from a SimpleMRS string.
    """
    tokens = LookaheadIterator(_lex(s.splitlines()))
    return _decode_mrs(tokens)


def encode(m, properties=True, indent=False):
    """
    Serialize a MRS object to a SimpleMRS string.

    Args:
        m: an MRS object
        properties (bool): if `False`, suppress variable properties
        indent (bool, int): if `True` or an integer value, add
            newlines and indentation
    Returns:
        a SimpleMRS-serialization of the MRS object
    """
    return _encode([m], properties=properties, indent=indent)


##############################################################################
##############################################################################
# Deserialization

_simplemrs_lex_re = re.compile(
    r'''# regex-pattern                      gid  description
    (\[)                                   #   1  graph/EP/properties start
    |(\])                                  #   2  graph/EP/properties end
    |<(-?\d+:-?\d+)>                       #   3  char span lnk values
    |<(-?\d+\#-?\d+)>                      #   4  chart span lnk values
    |<(\d+(?:\s+\d+)*)>                    #   5  token lnk values
    |<@(\d+)>                              #   6  edge identifier lnk values
    |"([^"\\]*(?:\\.[^"\\]*)*)"            #   7  double-quoted "strings"
    |'([^ \n:<>\[\]])                      #   8  single-quoted 'symbol
    |(<)                                   #   9  list start
    |(>)                                   #  10  list end
    |([^\s:<>\[\]]+):                      #  11  feature
    |((?:[^ \n\]<]+|<(?![-0-9:#@ ]*>))+)   #  12  variables, predicates
    |([^\s])                               #  13  unexpected
    ''',
    flags=re.VERBOSE|re.IGNORECASE)


def _lex(lineiter):
    """
    Lex the input string according to _simplemrs_lex_re.

    Yields
        (gid, token, line_number)
    """
    lines = enumerate(lineiter, 1)
    lineno = pos = 0
    try:
        for lineno, line in lines:
            matches = _simplemrs_lex_re.finditer(line)
            for m in matches:
                gid = m.lastindex
                if gid == 11:
                    token = m.group(gid).upper()  # upcase features
                elif gid in (8, 12):
                    token = m.group(gid).lower()  # downcase symbols
                elif gid == 13:
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
            yield _decode_mrs(tokens)
    except StopIteration:
        pass


def _decode_mrs(tokens):
    top = index = xarg = lnk = surface = identifier = None
    rels = []
    hcons = []
    icons = []
    variables = {}
    assert tokens.next()[0] == 1
    lnk = _decode_lnk(tokens)
    if tokens.peek()[0] == 7:
        surface = tokens.next()[1]
    gid, token, lineno = tokens.next()
    while gid == 11:
        if token in ('LTOP', 'TOP'):
            gid, top, lineno = tokens.next()
            assert gid == 12
        elif token == 'INDEX':
            index = _decode_variable(tokens, variables)
        elif token == 'RELS':
            assert tokens.next()[0] == 9
            while tokens.peek()[0] != 10:
                rels.append(_decode_rel(tokens, variables))
            assert tokens.next()[0] == 10
        elif token == 'HCONS':
            assert tokens.next()[0] == 9
            while tokens.peek()[0] != 10:
                hcons.append(_decode_cons(tokens, HCons, variables))
            assert tokens.next()[0] == 10
        elif token == 'ICONS':
            assert tokens.next()[0] == 9
            while tokens.peek()[0] != 10:
                icons.append(_decode_cons(tokens, ICons, variables))
            assert tokens.next()[0] == 10
        else:
            raise ValueError('invalid token: ' + token)
        gid, token, lineno = tokens.next()
    assert gid == 2
    return MRS(top=top, index=index, xarg=xarg,
               rels=rels, hcons=hcons, icons=icons, variables=variables,
               lnk=lnk, surface=surface, identifier=identifier)


def _decode_lnk(tokens):
    lnk = None
    if tokens.peek()[0] in (3, 4, 5, 6):
        gid, token, lineno = tokens.next()
        if gid == 3:
            lnk = Lnk.charspan(*token.split(':'))
        elif gid == 4:
            lnk = Lnk.chartspan(*token.split('#'))
        elif gid == 5:
            lnk = Lnk.tokens(token.split())
        elif gid == 6:
            lnk = Lnk.edge(token)
    return lnk


def _decode_variable(tokens, variables):
    gid, var, lineno = tokens.next()
    assert gid == 12
    if var not in variables:
        variables[var] = {}
    props = variables[var]
    if tokens.peek()[0] == 1:
        tokens.next()
        gid, token, lineno = tokens.next()
        if gid == 12:
            vartype = token
            gid, token, lineno = tokens.next()
        while gid == 11:
            gid, value, lineno = tokens.next()
            assert gid == 12
            props[token] = value
            gid, token, value = tokens.next()
        assert gid == 2
    return var


def _decode_rel(tokens, variables):
    args = {}
    carg = surface = None
    assert tokens.next()[0] == 1
    # The first elements are: predicate lnk? surface? label
    gid, token, lineno = tokens.next()
    assert gid in (7, 8, 12)
    predicate = Predicate.surface_or_abstract(token)
    lnk = _decode_lnk(tokens)
    gid, token, lineno = tokens.next()
    if gid == 7:
        surface = token
        gid, token, lineno = tokens.next()
    assert gid == 11 and token == 'LBL'
    gid, label, lineno = tokens.next()
    assert gid == 12
    # any remaining are arguments or a constant
    gid, role, lineno = tokens.next()
    while gid == 11:
        if role == 'CARG':
            gid, carg, lineno = tokens.next()
            assert gid == 7
        else:
            value = _decode_variable(tokens, variables)
            args[role] = value
        gid, role, lineno = tokens.next()
    assert gid == 2
    return EP(predicate,
              label,
              args=args,
              carg=carg,
              lnk=lnk,
              surface=surface,
              base=None)


def _decode_cons(tokens, cls, variables):
    lhs = _decode_variable(tokens, variables)
    gid, relation, lineno = tokens.next()
    assert gid == 12
    rhs = _decode_variable(tokens, variables)
    return cls(lhs, relation, rhs)


##############################################################################
##############################################################################
# Encoding

def _encode(ms, properties=True, encoding='unicode', indent=False):
    if indent is None or indent is False:
        indent = False  # normalize None to False
        delim = ' '
    else:
        indent = True  # normalize integers to True
        delim = '\n'
    return delim.join(_encode_mrs(m, properties, indent) for m in ms)


def _encode_mrs(m, properties, indent):
    delim = '\n  ' if indent else ' '
    if properties:
        varprops = {v: m.properties(v) for v in m.variables}
    else:
        varprops = {}
    parts = [
        _encode_surface_info(m),
        _encode_hook(m, varprops, indent),
        _encode_rels(m.rels, varprops, indent),
        _encode_hcons(m.hcons),
        _encode_icons(m.icons, varprops)
    ]
    return '[ {} ]'.format(
        delim.join(
            ' '.join(tokens) for tokens in parts if tokens))


def _encode_surface_info(m):
    tokens = []
    if m.lnk is not None and m.lnk.data != (-1, -1):
        tokens.append(str(m.lnk))
    if m.surface is not None:
        tokens.append('"{}"'.format(m.surface))
    return tokens


def _encode_hook(m, varprops, indent):
    delim = '\n  ' if indent else ' '
    tokens = []
    if m.top is not None:
        tokens.append('{}: {}'.format(TOP_FEATURE, m.top))
    if m.index is not None:
        tokens.append('INDEX: {}'.format(_encode_variable(m.index, varprops)))
    if tokens:
        tokens = [delim.join(tokens)]
    return tokens


def _encode_variable(var, varprops):
    tokens = [var]
    if varprops.get(var):
        tokens.append('[')
        tokens.append(var_sort(var))
        for prop in sorted(varprops[var], key=property_priority):
            val = varprops[var][prop]
            tokens.append(prop + ':')
            tokens.append(val)
        tokens.append(']')
        del varprops[var]
    return ' '.join(tokens)


def _encode_rels(rels, varprops, indent):
    delim = ('\n  ' + ' ' * len('RELS: < ')) if indent else ' '
    tokens = []
    for rel in rels:
        pred = '{}{}'.format(rel.predicate.string,
                             '' if rel.lnk is None else str(rel.lnk))
        reltoks = ['[', pred]
        if rel.surface is not None:
            reltoks.append('"{}"'.format(rel.surface))
        reltoks.extend(('LBL:', rel.label))
        for arg in sorted(rel.args, key=role_priority):
            val = rel.args[arg]
            reltoks.extend((arg + ':', _encode_variable(val, varprops)))
        if rel.carg is not None:
            reltoks.extend(('CARG:', '"{}"'.format(rel.carg)))
        reltoks.append(']')
        tokens.append(' '.join(reltoks))
    if tokens:
        tokens = ['RELS: <'] + [delim.join(tokens)] + ['>']
    return tokens

def _encode_hcons(hcons):
    tokens = ['{} {} {}'.format(hc.hi, hc.relation, hc.lo)
              for hc in hcons]
    if tokens:
        tokens = ['HCONS: <'] + [' '.join(tokens)] + ['>']
    return tokens


def _encode_icons(icons, varprops):
    tokens = ['{} {} {}'.format(_encode_variable(ic.left, varprops),
                                ic.relation,
                                _encode_variable(ic.right, varprops))
              for ic in icons]
    if tokens:
        tokens = ['ICONS: <'] + [' '.join(tokens)] + ['>']
    return tokens
