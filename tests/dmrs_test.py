
import pytest

from delphin.sembase import Predicate, _XMRS, _Node, _Edge
from delphin.dmrs import DMRS, Node, Link

p = Predicate.surface

@pytest.fixture
def dogs_bark():
    return {
        'top': 1,
        'index': 1,
        'nodes': [Node(1, p('_bark_v_1_rel'), sortinfo={'cvarsort': 'e'}),
                  Node(2, p('_udef_q_rel')),
                  Node(3, p('_dog_n_1_rel'), sortinfo={'cvarsort': 'x'})],
        'links': [Link(1, 3, 'ARG1', 'NEQ'),
                  Link(2, 3, 'RSTR', 'H')]}

def test_empty_DMRS():
    d = DMRS()
    assert d.top is None
    assert d.index is None
    assert d.xarg is None
    assert d.nodes == []
    assert d.links == []

def test_basic_DMRS(dogs_bark):
    d = DMRS(**dogs_bark)
    assert d.top is 1
    assert d.index is 1
    assert d.xarg is None
    assert len(d.nodes) == 3
    assert d.nodes[0].predicate == '_bark_v_1_rel'
    assert d.nodes[1].predicate == '_udef_q_rel'
    assert d.nodes[2].predicate == '_dog_n_1_rel'
    assert len(d.links) == 2
    assert d.links[0].role == 'ARG1'
    assert d.links[1].role == 'RSTR'


def test_DMRS_from_xmrs(dogs_bark):
    x = _XMRS(1, 1, None,
              dogs_bark['nodes'], {0: {1}, 1: {2}, 2: {3}},
              [_Edge(1, 3, 'ARG1', _Edge.VARARG),
               _Edge(2, 3, 'RSTR', _Edge.QEQARG)],
              None, None, None)
    d = DMRS.from_xmrs(x)

# test when TOP is QEQ and HEQ
