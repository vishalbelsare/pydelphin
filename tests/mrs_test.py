
import pytest

from delphin.sembase import Predicate, _XMRS, _Node, _Edge
from delphin.mrs import (
    EP,
    HCons,
    MRS)

p = Predicate.surface

@pytest.fixture
def dogs_bark():
    return {
        'top': 'h0',
        'index': 'e2',
        'rels': [EP(p('_bark_v_1_rel'), 'h1',
                     args={'ARG0': 'e2', 'ARG1': 'x4'}),
                  EP(p('udef_q_rel'), 'h3',
                     args={'ARG0': 'x4', 'RSTR': 'h5', 'BODY': 'h7'}),
                  EP(p('_dog_n_1_rel'), 'h6', args={'ARG0': 'x4'})],
        'hcons': [HCons.qeq('h0', 'h1'),
                  HCons.qeq('h5', 'h6')],
        'variables': {
            'e2': [('TENSE', 'pres')],
            'x4': [('NUM', 'pl')]}}


def test_empty_MRS():
    m = MRS()
    assert m.top is None
    assert m.index is None
    assert m.xarg is None
    assert len(m.rels) == 0
    assert len(m.hcons) == 0
    assert len(m.icons) == 0
    assert m.variables == {}


def test_basic_MRS(dogs_bark):
    m = MRS(**dogs_bark)
    assert m.top is 'h0'
    assert m.index is 'e2'
    assert m.xarg is None
    assert len(m.rels) == 3
    assert len(m.hcons) == 2
    assert len(m.icons) == 0
    assert m.variables == {
        'h0': [],
        'h1': [],
        'e2': [('TENSE', 'pres')],
        'h3': [],
        'x4': [('NUM', 'pl')],
        'h5': [],
        'h6': [],
        'h7': []}


def test_MRS_from_xmrs(dogs_bark):
    x = _XMRS(1, 1, None,
              [_Node(1, p('_bark_v_1_rel'), 'e'),
               _Node(2, p('udef_q_rel'), None),
               _Node(3, p('_dog_n_1_rel'), 'x')],
              {0: {1}, 1: {2}, 2: {3}},
              [_Edge(1, 3, 'ARG1', _Edge.VARARG),
               _Edge(2, 2, 'RSTR', _Edge.QEQARG)],
              [],
              None, None, None)
    m = MRS.from_xmrs(x)

def test_MRS_to_xmrs(dogs_bark):
    m = MRS(**dogs_bark)
    x = m.to_xmrs()
    assert len(x.nodes) == 3
    assert len(x.scopes) == 3
