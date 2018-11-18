
"""
MRS-JSON serialization and deserialization.
"""

import io
import json

from delphin.sembase import Lnk, Predicate
from delphin.mrs import (MRS, EP, HCons, ICons, var_sort)


def load(source):
    """
    Deserialize a MRS-JSON file (handle or filename) to MRS objects

    Args:
        source: filename or file object
    Returns:
        a list of MRS objects
    """
    if hasattr(source, 'read'):
        data = json.load(source)
    else:
        with open(source) as fh:
            data = json.load(fh)
    return [from_dict(d) for d in data]


def loads(s):
    """
    Deserialize a MRS-JSON string to MRS objects

    Args:
        s (str): a MRS-JSON string
    Returns:
        a list of MRS objects
    """
    data = json.loads(s)
    return [from_dict(d) for d in data]


def dump(ms, destination, properties=True, indent=False, encoding='utf-8'):
    """
    Serialize MRS objects to a MRS-JSON file.

    Args:
        ms: iterator of :class:`~delphin.mrs.MRS` objects to
            serialize
        destination: filename or file object
        properties: if `True`, encode variable properties
        indent: if `True`, adaptively indent; if `False` or `None`,
            don't indent; if a non-negative integer N, indent N spaces
            per level
        encoding (str): if *destination* is a filename, write to the
            file with the given encoding; otherwise it is ignored
    """
    if indent is False:
        indent = None
    elif indent is True:
        indent = 2
    data = [to_dict(m, properties=True) for m in ms]
    if hasattr(destination, 'write'):
        json.dump(data, destination, indent=indent)
    else:
        with io.open(destination, 'w', encoding=encoding) as fh:
            json.dump(data, fh)


def dumps(ms, properties=True, indent=False):
    """
    Serialize MRS objects to a MRS-JSON string.

    Args:
        ms: iterator of :class:`~delphin.mrs.MRS` objects to
            serialize
        properties: if `True`, encode variable properties
        indent: if `True`, adaptively indent; if `False` or `None`,
            don't indent; if a non-negative integer N, indent N spaces
            per level
    Returns:
        a MRS-JSON-serialization of the MRS objects
    """
    if indent is False:
        indent = None
    elif indent is True:
        indent = 2
    data = [to_dict(m, properties=properties) for m in ms]
    return json.dumps(data, indent=indent)


def decode(s):
    """
    Deserialize a MRS object from a MRS-JSON string.
    """
    return from_dict(json.loads(s))


def encode(m, properties=True, indent=False):
    """
    Serialize a MRS object to a MRS-JSON string.

    Args:
        m: a MRS object
        properties (bool): if `False`, suppress variable properties
        indent (bool, int): if `True` or an integer value, add
            newlines and indentation
    Returns:
        a MRS-JSON-serialization of the MRS object
    """
    if indent is False:
        indent = None
    elif indent is True:
        indent = 2
    return json.dumps(to_dict(m, properties=properties), indent=indent)


def to_dict(m, short_pred=True, properties=True):
    """
    Encode the MRS as a dictionary suitable for JSON serialization.
    """
    def _lnk(obj):
        return {'from': obj.cfrom, 'to': obj.cto}
    def _ep(ep):
        p = ep.predicate.short_form() if short_pred else str(ep.predicate)
        d = dict(label=ep.label, predicate=p, arguments=ep.args)
        if ep.lnk is not None: d['lnk'] = _lnk(ep)
        return d
    def _hcons(hc):
        return {'relation':hc.relation, 'high':hc.hi, 'low':hc.lo}
    def _icons(ic):
        return {'relation':ic.relation, 'left':ic.left, 'right':ic.right}
    def _var(v):
        d = {'type': var_sort(v)}
        if properties and m.properties(v):
            d['properties'] = m.properties(v)
        return d

    d = dict(
        relations=[_ep(ep) for ep in m.rels],
        constraints=([_hcons(hc) for hc in m.hcons] +
                     [_icons(ic) for ic in m.icons]),
        variables={v: _var(v) for v in m.variables}
    )
    if m.top is not None: d['top'] = m.top
    if m.index is not None: d['index'] = m.index
    # if m.xarg is not None: d['xarg'] = m.xarg
    # if m.lnk is not None: d['lnk'] = m.lnk
    # if m.surface is not None: d['surface'] = m.surface
    # if m.identifier is not None: d['identifier'] = m.identifier
    return d


def from_dict(d):
    """
    Decode a dictionary, as from `to_dict()`, into an MRS object.
    """
    def _lnk(o):
        return None if o is None else Lnk.charspan(o['from'], o['to'])
    def _ep(ep):
        return EP(
            Predicate.surface_or_abstract(ep['predicate']),
            ep['label'],
            args=ep.get('arguments', {}),
            lnk=_lnk(ep.get('lnk')),
            surface=ep.get('surface'),
            base=ep.get('base')
        )
    eps = [_ep(rel) for rel in d.get('relations', [])]
    hcons = [HCons(c['high'], c['relation'], c['low'])
             for c in d.get('constraints', []) if 'high' in c]
    icons = [ICons(c['left'], c['relation'], c['right'])
             for c in d.get('constraints', []) if 'left' in c]
    variables = {var: data.get('properties', {})
                 for var, data in d.get('variables', {}).items()}
    return MRS(
        top=d.get('top'),
        index=d.get('index'),
        xarg=d.get('xarg'),
        rels=eps,
        hcons=hcons,
        icons=icons,
        variables=variables,
        lnk=_lnk(d.get('lnk')),
        surface=d.get('surface'),
        identifier=d.get('identifier')
    )
