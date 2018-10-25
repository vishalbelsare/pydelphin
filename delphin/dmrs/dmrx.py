
"""
DMRX (XML for DMRS) serialization and deserialization.
"""

# Author: Michael Wayne Goodman <goodmami@uw.edu>

from __future__ import print_function

from collections import OrderedDict
import re
import xml.etree.ElementTree as etree

from delphin.sembase import Lnk, Predicate
from delphin.dmrs import DMRS, Node, Link
from delphin.mrs.config import QUANTIFIER_POS
from delphin.mrs.util import etree_tostring

##############################################################################
##############################################################################
# Pickle-API methods


def load(fh):
    """
    Deserialize DMRX from a file (handle or filename)

    Args:
        fh (str, file): input filename or file object
    Returns:
        a generator of Xmrs objects
    """
    ms = deserialize(fh)
    return ms


def loads(s):
    """
    Deserialize DMRX string representations

    Args:
        s (str): a DMRX string
    Returns:
        a generator of Xmrs objects
    """
    corpus = etree.fromstring(s)
    ds = (_deserialize_dmrs(dmrs_elem) for dmrs_elem in corpus)
    return ds


def dump(destination, ms, properties=True, pretty_print=False, **kwargs):
    """
    Serialize Xmrs objects to DMRX and write to a file

    Args:
        destination: filename or file object where data will be written
        ms: an iterator of Xmrs objects to serialize
        properties: if `False`, suppress variable properties
        pretty_print: if `True`, add newlines and indentation
    """
    text = dumps(ms,
                 properties=properties,
                 pretty_print=pretty_print,
                 **kwargs)

    if hasattr(destination, 'write'):
        print(text, file=destination)
    else:
        with open(destination, 'w') as fh:
            print(text, file=fh)


def dumps(ms, properties=True, pretty_print=False, **kwargs):
    """
    Serialize an Xmrs object to a DMRX representation

    Args:
        ms: an iterator of Xmrs objects to serialize
        properties: if `False`, suppress variable properties
        pretty_print: if `True`, add newlines and indentation
    Returns:
        a DMRX string representation of a corpus of Xmrs
    """
    if not pretty_print and kwargs.get('indent'):
        pretty_print = True
    return serialize(ms, properties=properties, pretty_print=pretty_print)


def decode(s):
    elem = etree.fromstring(s)
    return _deserialize_dmrs(elem)


def encode(d, properties=True, indent=False):
    elem = _encode_dmrs(d, properties=properties)

    if indent in ('LKB', 'Lkb', 'lkb', True):
        _indent(elem, indent=0, maxdepth=1, level=0)
    elif indent is not False and indent is not None:
        i = ' ' * indent
        _indent(elem, indent, maxdepth=3, level=0)

    s = etree_tostring(elem, encoding='unicode').rstrip()
    return s


##############################################################################
##############################################################################
# Decoding

def deserialize(fh):
    # <!ELEMENT dmrs-list (dmrs)*>
    # if memory becomes a big problem, consider catching start events,
    # get the root element (later start events can be ignored), and
    # root.clear() after decoding each mrs
    for _, elem in etree.iterparse(fh, events=('end',)):
        if elem.tag == 'dmrs':
            yield _deserialize_dmrs(elem)
            elem.clear()

def _deserialize_dmrs(elem):
    # <!ELEMENT dmrs (node|link)*>
    # <!ATTLIST dmrs
    #           cfrom CDATA #REQUIRED
    #           cto   CDATA #REQUIRED
    #           surface   CDATA #IMPLIED
    #           ident     CDATA #IMPLIED >
    elem = elem.find('.')  # in case elem is an ElementTree rather than Element
    return DMRS(nodes=list(map(_decode_node, elem.iter('node'))),
                links=list(map(_decode_link, elem.iter('link'))),
                top=elem.get('top'),
                index=elem.get('index'),
                xarg=elem.get('xarg'),
                lnk=_decode_lnk(elem),
                surface=elem.get('surface'),
                identifier=elem.get('ident'))


def _decode_node(elem):
    # <!ELEMENT node ((realpred|gpred), sortinfo)>
    # <!ATTLIST node
    #           nodeid CDATA #REQUIRED
    #           cfrom CDATA #REQUIRED
    #           cto   CDATA #REQUIRED
    #           surface   CDATA #IMPLIED
    #           base      CDATA #IMPLIED
    #           carg CDATA #IMPLIED >
    return Node(pred=_decode_pred(elem.find('*[1]')),
                nodeid=elem.get('nodeid'),
                sortinfo=_decode_sortinfo(elem.find('sortinfo')),
                lnk=_decode_lnk(elem),
                surface=elem.get('surface'),
                base=elem.get('base'),
                carg=elem.get('carg'))


def _decode_pred(elem):
    # <!ELEMENT realpred EMPTY>
    # <!ATTLIST realpred
    #           lemma CDATA #REQUIRED
    #           pos (v|n|j|r|p|q|c|x|u|a|s) #REQUIRED
    #           sense CDATA #IMPLIED >
    # <!ELEMENT gpred (#PCDATA)>
    if elem.tag == 'gpred':
        return Predicate.abstract(elem.text)
    elif elem.tag == 'realpred':
        return Predicate.realpred(elem.get('lemma'),
                             elem.get('pos') or None,
                             elem.get('sense'))


def _decode_sortinfo(elem):
    # <!ELEMENT sortinfo EMPTY>
    # <!ATTLIST sortinfo
    #           cvarsort (x|e|i|u) #IMPLIED
    #           num  (sg|pl|u) #IMPLIED
    #           pers (1|2|3|1-or-3|u) #IMPLIED
    #           gend (m|f|n|m-or-f|u) #IMPLIED
    #           sf (prop|ques|comm|prop-or-ques|u) #IMPLIED
    #           tense (past|pres|fut|tensed|untensed|u) #IMPLIED
    #           mood (indicative|subjunctive|u) #IMPLIED
    #           prontype (std_pron|zero_pron|refl|u) #IMPLIED
    #           prog (plus|minus|u) #IMPLIED
    #           perf (plus|minus|u) #IMPLIED
    #           ind  (plus|minus|u) #IMPLIED >
    # note: Just accept any properties, since these are ERG-specific
    return elem.attrib


def _decode_link(elem):
    # <!ELEMENT link (rargname, post)>
    # <!ATTLIST link
    #           from CDATA #REQUIRED
    #           to   CDATA #REQUIRED >
    # <!ELEMENT rargname (#PCDATA)>
    # <!ELEMENT post (#PCDATA)>
    return Link(start=elem.get('from'),
                end=elem.get('to'),
                rargname=getattr(elem.find('rargname'), 'text', None),
                post=getattr(elem.find('post'), 'text', None))


def _decode_lnk(elem):
    return Lnk.charspan(elem.get('cfrom', '-1'), elem.get('cto', '-1'))

##############################################################################
##############################################################################
# Encoding


def serialize(ds, properties=True, encoding='unicode', pretty_print=False):
    e = etree.Element('dmrs-list')
    for d in ds:
        e.append(_encode_dmrs(d, properties))
    # for now, pretty_print=True is the same as pretty_print='LKB'
    if pretty_print in ('LKB', 'lkb', 'Lkb', True):
        lkb_pprint_re = re.compile(r'(<dmrs[^>]+>|</node>|</link>|</dmrs>)')
        string = str(etree_tostring(e, encoding=encoding))
        return lkb_pprint_re.sub(r'\1\n', string)
    # pretty_print is only lxml. Look into tostringlist, maybe?
    # return etree.tostring(e, pretty_print=pretty_print, encoding='unicode')
    return etree_tostring(e, encoding=encoding)


def _encode_dmrs(d, properties):
    attributes = OrderedDict([('cfrom', str(d.cfrom)),
                              ('cto', str(d.cto))])
    if d.top is not None:
        attributes['top'] = str(d.top)
    if d.index is not None:
        attributes['index'] = str(d.index)
    if d.xarg is not None:
        attributes['xarg'] = str(d.xarg)
    if d.surface is not None:
        attributes['surface'] = d.surface
    if d.identifier is not None:
        attributes['ident'] = d.identifier
    e = etree.Element('dmrs', attrib=attributes)
    for node in d.nodes:
        e.append(_encode_node(node, properties))
    for link in d.links:
        e.append(_encode_link(link))
    return e


def _encode_node(node, properties):
    attributes = OrderedDict([('nodeid', str(node.nodeid)),
                              ('cfrom', str(node.cfrom)),
                              ('cto', str(node.cto))])
    if node.surface is not None:
        attributes['surface'] = node.surface
    if node.base is not None:
        attributes['base'] = node.base
    if node.carg is not None:
        attributes['carg'] = node.carg
    e = etree.Element('node', attrib=attributes)
    e.append(_encode_pred(node.predicate))
    e.append(_encode_sortinfo(node, properties))
    return e


def _encode_pred(pred):
    if pred.type == Predicate.ABSTRACT:
        e = etree.Element('gpred')
        e.text = pred.string.strip('"\'')
    elif pred.type in (Predicate.REALPRED, Predicate.SURFACE):
        attributes = {}
        attributes['lemma'] = pred.lemma
        if pred.pos is None:
            attributes['pos'] = ""
        else:
            attributes['pos'] = pred.pos
        if pred.sense is not None:
            attributes['sense'] = str(pred.sense)
        e = etree.Element('realpred', attrib=attributes)
    return e


def _encode_sortinfo(node, properties):
    attributes = OrderedDict()
    # return empty <sortinfo/> for quantifiers
    if node.predicate.pos == QUANTIFIER_POS:
        return etree.Element('sortinfo')  # return empty <sortinfo/>
    if properties and node.sortinfo:
        for k, v in node.sortinfo.items():
            attributes[k.lower()] = str(v)
    e = etree.Element('sortinfo', attrib=attributes or {})
    return e


def _encode_link(link):
    e = etree.Element('link',
                      attrib={'from': str(link.start),
                              'to': str(link.end)})
    rargname = etree.Element('rargname')
    rargname.text = link.rargname
    post = etree.Element('post')
    post.text = link.post
    e.append(rargname)
    e.append(post)
    return e

# inspired by Fredrik Lundh's indent() function:
#   http://effbot.org/zone/element-lib.htm
def _indent(elem, indent, maxdepth, level):
    if level == maxdepth:
        return
    curind = '\n' + ' ' * indent * level
    nxtind = '\n' + ' ' * indent * (level + 1)
    if len(elem):
        if not elem.text:
            elem.text = nxtind
        elem.tail = curind
        for elem in elem:
            _indent(elem, indent, maxdepth, level + 1)
        elem.tail = curind
    else:
        elem.tail = curind
