
import pytest

from delphin.sembase import Predicate, _XMRS, _Node, _Edge
from delphin.eds import EDS, Node, Edge

p = Predicate.surface

@pytest.fixture
def dogs_bark():
    return {
        'top': '_1',
        'nodes': [Node('_1', p('_bark_v_1_rel'), type='e'),
                  Node('_2', p('udef_q_rel')),
                  Node('_3', p('_dog_n_1_rel'), type='x')],
        'edges': [Edge('_1', '_3', 'ARG1'),
                  Edge('_2', '_3', 'BV')]}


@pytest.fixture
def dogs_bark_from_mrs():
    return {
        'top': 'e2',
        'nodes': [Node('e2', p('_bark_v_1_rel'), type='e'),
                  Node('_1', p('udef_q_rel')),
                  Node('x4', p('_dog_n_1_rel'), type='x')],
        'edges': [Edge('e2', 'x4', 'ARG1'),
                  Edge('_1', 'x4', 'BV')]}


def test_empty_EDS():
    d = EDS()
    assert d.top is None
    assert d.index is None
    assert d.xarg is None
    assert d.nodes == []
    assert d.edges == []


def test_basic_EDS(dogs_bark):
    d = EDS(**dogs_bark)
    assert d.top == '_1'
    assert d.index is None
    assert d.xarg is None
    assert len(d.nodes) == 3
    assert d.nodes[0].predicate == '_bark_v_1_rel'
    assert d.nodes[1].predicate == 'udef_q_rel'
    assert d.nodes[2].predicate == '_dog_n_1_rel'
    assert len(d.edges) == 2
    assert d.edges[0].role == 'ARG1'
    assert d.edges[1].role == 'BV'


def test_EDS_from_xmrs(dogs_bark, dogs_bark_from_mrs):
    x = _XMRS(0, 10000, None,
              [Node(10000, p('_bark_v_1_rel'), type='e'),
               Node(10001, p('udef_q_rel')),
               Node(10002, p('_dog_n_1_rel'), type='x')],
              {0: {10000}, 1: {10001}, 2: {10002}},
              [_Edge(10000, 10002, 'ARG1', _Edge.VARARG),
               _Edge(10001, 2, 'RSTR', _Edge.QEQARG)],
              [],
              None, None, None)
    d = EDS.from_xmrs(x)
    assert d.nodes == dogs_bark['nodes']
    assert d.edges == dogs_bark['edges']

    x = _XMRS(0, 10000, None,
              [Node(10000, p('_bark_v_1_rel'), type='e'),
               Node(10001, p('udef_q_rel')),
               Node(10002, p('_dog_n_1_rel'), type='x')],
              {0: {10000}, 1: {10001}, 2: {10002}},
              [_Edge(10000, 'e2', 'ARG0', _Edge.INTARG),
               _Edge(10001, 'x4', 'ARG0', _Edge.INTARG),
               _Edge(10002, 'x4', 'ARG0', _Edge.INTARG),
               _Edge(10000, 10002, 'ARG1', _Edge.VARARG),
               _Edge(10001, 2, 'RSTR', _Edge.QEQARG)],
              [],
              None, None, None)
    d = EDS.from_xmrs(x)
    assert d.nodes == dogs_bark_from_mrs['nodes']
    assert d.edges == dogs_bark_from_mrs['edges']


# test when TOP is QEQ and HEQ
