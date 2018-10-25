
import pytest

from delphin.sembase import Predicate, _XMRS, _Node, _Edge
from delphin.dmrs import DMRS, Node, Link

p = Predicate.surface

@pytest.fixture
def dogs_bark():
    return {
        'top': 10000,
        'index': 10000,
        'nodes': [Node(10000, p('_bark_v_1_rel'), sortinfo={'cvarsort': 'e'}),
                  Node(10001, p('udef_q_rel')),
                  Node(10002, p('_dog_n_1_rel'), sortinfo={'cvarsort': 'x'})],
        'links': [Link(10000, 10002, 'ARG1', 'NEQ'),
                  Link(10001, 10002, 'RSTR', 'H')]}


def test_empty_DMRS():
    d = DMRS()
    assert d.top is None
    assert d.index is None
    assert d.xarg is None
    assert d.nodes == []
    assert d.links == []


def test_basic_DMRS(dogs_bark):
    d = DMRS(**dogs_bark)
    assert d.top == 10000
    assert d.index == 10000
    assert d.xarg is None
    assert len(d.nodes) == 3
    assert d.nodes[0].predicate == '_bark_v_1_rel'
    assert d.nodes[1].predicate == 'udef_q_rel'
    assert d.nodes[2].predicate == '_dog_n_1_rel'
    assert len(d.links) == 2
    assert d.links[0].role == 'ARG1'
    assert d.links[1].role == 'RSTR'


def test_DMRS_from_xmrs(dogs_bark):
    x = _XMRS(10000, 10000, None,
              dogs_bark['nodes'],
              {0: {10000}, 1: {10001}, 2: {10002}},
              [_Edge(10000, 10002, 'ARG1', _Edge.VARARG),
               _Edge(10001, 2, 'RSTR', _Edge.QEQARG)],
              [],
              None, None, None)
    d = DMRS.from_xmrs(x)
    assert d.nodes == dogs_bark['nodes']
    assert d.links == dogs_bark['links']

def test_DMRS_to_xmrs(dogs_bark):
    d = DMRS(**dogs_bark)
    x = d.to_xmrs()
    assert x.nodes == d.nodes
    assert len(x.scopes) == 3
    # assert x.edges == [
    #     _Edge(

# test when TOP is QEQ and HEQ
