
"""
Serialization for the Indexed MRS format.
"""

from __future__ import print_function

import io
import re

from delphin.sembase import Lnk, Predicate
from delphin.mrs import (
    MRS,
    EP,
    HCons,
    ICons)
from delphin.mrs._mrs import var_sort
from delphin.util import safe_int, LookaheadIterator


##############################################################################
##############################################################################
# Pickle-API methods

def load(source, semi):
    """
    Deserialize Indexed MRS from a file (handle or filename)

    Args:
        source (str, file): input filename or file object
        semi (:class:`SemI`): the semantic interface for the grammar
            that produced the MRS
    Returns:
        a list of MRS objects
    """
    if hasattr(source, 'read'):
        ds = _decode(source, semi)
    else:
        with open(source) as fh:
            ds = _decode(fh, semi)
    return list(ds)


def loads(s, semi, single=False, encoding='utf-8'):
    """
    Deserialize Indexed MRS string representations

    Args:
        s (str): an Indexed MRS string
        semi (:class:`SemI`): the semantic interface for the grammar
            that produced the MRS
    Returns:
        a list of MRS objects
    """
    ds = _decode(s.splitlines(), semi)
    return list(ds)


def dump(ms, destination, semi, properties=True, indent=False, encoding='utf-8'):
    """
    Serialize MRS objects to Indexed MRS and write to a file

    Args:
        ms: an iterator of MRS objects to serialize
        destination: filename or file object where data will be written
        semi (:class:`SemI`): the semantic interface for the grammar
            that produced the MRS
        properties: if `False`, suppress morphosemantic properties
        indent (bool, int): if `True` or an integer value, add
            newlines and indentation
        encoding (str): if *destination* is a filename, write to the
            file with the given encoding; otherwise it is ignored
    """
    text = dumps(ms, semi, properties=properties, indent=indent)
    if hasattr(destination, 'write'):
        print(text, file=destination)
    else:
        with io.open(destination, 'w', encoding=encoding) as fh:
            print(text, file=fh)


def dumps(ms, semi, properties=True, indent=False):
    """
    Serialize MRS objects to an Indexed MRS representation

    Args:
        ms: an iterator of MRS objects to serialize
        semi (:class:`SemI`): the semantic interface for the grammar
            that produced the MRS
        properties: if `False`, suppress variable properties
        indent (bool, int): if `True` or an integer value, add
            newlines and indentation
    Returns:
        an Indexed MRS string representation of a corpus of MRS objects
    """
    return _encode(ms, semi, properties=properties, indent=indent)


def decode(s, semi):
    """
    Deserialize a MRS object from an Indexed MRS string.

    Args:
        s (str): an Indexed MRS string
        semi (:class:`SemI`): the semantic interface for the grammar
            that produced the MRS
    """
    tokens = LookaheadIterator(_lex(s.splitlines()))
    return _decode_indexed(tokens, semi)


def encode(d, semi, properties=True, indent=False):
    """
    Serialize a MRS object to an Indexed MRS string.

    Args:
        d: a MRS object
        semi (:class:`SemI`): the semantic interface for the grammar
            that produced the MRS
        properties (bool): if `False`, suppress variable properties
        indent (bool, int): if `True` or an integer value, add
            newlines and indentation
    Returns:
        an Indexed MRS-serialization of the MRS object
    """
    return _encode_indexed(d, semi, properties=properties, indent=indent)


##############################################################################
##############################################################################
# Decoding

_indexedmrs_lex_re = re.compile(
    r'''# regex-pattern                      gid  description
    <(-?\d+:-?\d+)>                        #   1  cfrom:cto lnk values
    |"([^"\\]*(?:\\.[^"\\]*)*)"            #   2  quoted strings
    |(<)                                   #   3  graph start
    |(>)                                   #   4  graph end
    |(\{)                                  #   5  list start
    |(\})                                  #   6  list end
    |(\()                                  #   7  arglist start
    |(\))                                  #   8  arglist end
    |(,)                                   #   9  list delimiter
    |(:)                                   #  10  property delimiter
    |([^\s"'()\/,:;<=>[\]{}]+)             #  11  identifiers and values
    |([^\s])                               #  12  unexpected
    ''',
    flags=re.VERBOSE|re.IGNORECASE)


def _lex(lineiter):
    """
    Lex the input string according to _simpledmrs_lex_re.

    Yields
        (gid, token, line_number)
    """
    lines = enumerate(lineiter, 1)
    lineno = pos = 0
    try:
        for lineno, line in lines:
            matches = _indexedmrs_lex_re.finditer(line)
            for m in matches:
                gid = m.lastindex
                if gid == 12:
                    raise ValueError('unexpected input: ' + line[pos:])
                else:
                    token = m.group(gid)
                    yield (gid, token, lineno)
    except StopIteration:
        pass


def _decode(lineiter, semi):
    tokens = LookaheadIterator(_lex(lineiter))
    try:
        while tokens.peek():
            yield _decode_indexed(tokens, semi)
    except StopIteration:
        pass


def _decode_indexed(tokens, semi):
    xarg = icons = lnk = surface = identifier = None
    variables = {}
    assert tokens.next()[0] == 3
    top, index = _decode_hook(tokens, variables)
    rels = _decode_rels(tokens, variables, semi)
    hcons = _decode_cons(tokens, HCons)
    gid = tokens.next()[0]
    if gid == 9:
        icons = _decode_cons(tokens, ICons)
        gid = tokens.next()[0]
    assert gid == 4
    _match_properties(variables, semi)
    return MRS(top=top,
               index=index,
               xarg=xarg,
               rels=rels,
               hcons=hcons,
               icons=icons,
               variables=variables,
               lnk=lnk,
               surface=surface,
               identifier=identifier)


def _decode_hook(tokens, variables):
    gid, top, lineno = tokens.next()
    assert gid == 11
    assert tokens.next()[0] == 9
    gid, index, lineno = tokens.next()
    assert gid == 11
    gid = tokens.next()[0]
    if gid == 10:
        variables[index] = _decode_proplist(tokens)
        gid = tokens.next()[0]
    assert gid == 9
    return top, index


def _decode_proplist(tokens):
    proplist = []
    while tokens.peek()[0] == 11:
        proplist.append(tokens.next()[1])
        if tokens.peek()[0] == 10:
            tokens.next()
        else:
            break
    return proplist


def _decode_rels(tokens, variables, semi):
    rels = []
    assert tokens.next()[0] == 5
    gid, token, lineno = tokens.next()
    while gid == 11:
        rels.append(_decode_rel(token, tokens, variables, semi))
        gid = tokens.next()[0]
        if gid == 9:
            gid, token, lineno = tokens.next()
        else:
            break
    assert gid == 6
    assert tokens.next()[0] == 9
    return rels


def _decode_rel(label, tokens, variables, semi):
    assert tokens.next()[0] == 10
    gid, pred, lineno = tokens.next()
    assert gid == 11
    lnk = _decode_lnk(tokens)
    arglist, carg = _decode_arglist(tokens, variables)
    argtypes = [var_sort(arg) for arg in arglist]
    synopsis = semi.find_synopsis(pred, variables=argtypes)
    args = {d[0]: v for d, v in zip(synopsis, arglist)}
    return EP(
        Predicate.surface_or_abstract(pred),
        label=label,
        args=args,
        carg=carg,
        lnk=lnk,
        surface=None,
        base=None)


def _decode_lnk(tokens):
    lnk = None
    if tokens.peek()[0] == 1:
        cfrom, cto = tokens.next()[1].split(':')
        lnk = Lnk.charspan(cfrom, cto)
    return lnk


def _decode_arglist(tokens, variables):
    arglist = []
    carg = None
    assert tokens.next()[0] == 7
    gid, arg, lineno = tokens.next()
    while gid != 8:
        if gid == 11:
            gid = tokens.next()[0]
            if gid == 10:
                variables[arg] = _decode_proplist(tokens)
                gid = tokens.next()[0]
            arglist.append(arg)
        else:
            assert gid == 2
            carg = arg
            gid = tokens.next()[0]
        if gid == 9:
            gid, arg, lineno = tokens.next()
        else:
            break
    assert gid == 8
    return arglist, carg


def _decode_cons(tokens, cls):
    cons = []
    assert tokens.next()[0] == 5
    gid, lhs, lineno = tokens.next()
    while gid == 11:
        gid, reln, lineno = tokens.next()
        assert gid == 11
        gid, rhs, lineno = tokens.next()
        assert gid == 11
        cons.append(cls(lhs, reln, rhs))
        gid = tokens.next()[0]
        if gid == 9:
            gid, lhs, lineno = tokens.next()
        else:
            break
    assert gid == 6
    return cons


def _match_properties(variables, semi):
    for var, propvals in variables.items():
        if not propvals:
            continue
        semiprops = semi.variables[var_sort(var)]
        assert len(semiprops) == len(propvals)
        assert all(semi.subsumes(sp[1], pv)
                   for sp, pv in zip(semiprops, propvals))
        variables[var] = {sp[0]: pv for sp, pv in zip(semiprops, propvals)}


##############################################################################
##############################################################################
# Encoding


def _encode(ms, semi, properties, indent):
    if indent is None or indent is False:
        delim = ' '
    else:
        delim = '\n'
    return delim.join(
        _encode_indexed(m, properties, indent=indent)
        for m in ms)


def _encode_indexed(m, semi, properties, indent):
    # attempt to convert if necessary
    if not isinstance(m, MRS):
        m = MRS.from_xmrs(m)

    if indent is None or indent is False:
        i1 = ',{{{}}}'
        i2 = i3 = ','
        start = '<'
        end = '>'
        hook = '{},{}'
    else:
        if indent is True:
            indent = 2
        i1 = ',\n' + (' ' * indent) + '{{' + (' ' * (indent - 1)) + '{} }}'
        i2 = ',\n' + ('  ' * indent)
        i3 = ', '
        start = '< '
        end = ' >'
        hook = '{}, {}'

    if properties:
        varprops = _prepare_variable_properties(m, semi)
    else:
        varprops = {}

    body = [
        hook.format(m.top, _encode_variable(m.index, varprops)),
        i1.format(i2.join(_encode_rel(ep, semi, varprops, i3)
                          for ep in m.rels)),
        i1.format(i2.join(_encode_hcons(hc)
                          for hc in m.hcons))
    ]
    if m.icons:
        body.append(i1.format(_encode_icons(ic)
                              for ic in m.icons))

    return start + ''.join(body) + end


def _prepare_variable_properties(m, semi):
    proplists = {}
    for var, varprops in m.variables.items():
        if varprops:
            proplists[var] = [varprops.get(key, val).upper()
                              for key, val in semi.variables[var_sort(var)]]
    return proplists


def _encode_variable(var, varprops):
    if var in varprops:
        props = ':' + ':'.join(varprops[var])
        del varprops[var]
    else:
        props = ''
    return var + props


def _encode_rel(ep, semi, varprops, delim):
    synopsis = semi.find_synopsis(ep.predicate.short_form(),
                                  roles=list(ep.args))
    args = [_encode_variable(ep.args[d[0]], varprops)
            for d in synopsis]
    if ep.carg is not None:
        args.append('"{}"'.format(ep.carg))
    return '{label}:{pred}{lnk}({args})'.format(
        label=ep.label,
        pred=ep.predicate.short_form(),
        lnk=str(ep.lnk) if ep.lnk is not None else '',
        args=delim.join(args))


def _encode_hcons(hc):
    return '{} {} {}'.format(hc.hi, hc.relation, hc.lo)


def _encode_icons(ic):
    return '{} {} {}'.format(ic.left, ic.relation, ic.right)
