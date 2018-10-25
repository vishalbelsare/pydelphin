
import pytest

from delphin.sembase import Predicate
from delphin.dmrs import DMRS, Node, Link, dmrx

@pytest.fixture
def empty_dmrs():
    return DMRS()

@pytest.fixture
def it_rains_dmrs():
    d = DMRS(
        10, 10, None,
        nodes=[Node(10, Predicate.surface('_rain_v_1'), sortinfo={'cvarsort': 'e'})],
        links=[])
    return d

@pytest.fixture
def it_rains_heavily_dmrs():
    d = DMRS(
        20, 10, None,
        nodes=[Node(10, Predicate.surface('_rain_v_1'), sortinfo={'cvarsort': 'e'}),
               Node(20, Predicate.surface('_heavy_v_1'), sortinfo={'cvarsort': 'e'})],
        links=[Link(20, 10, 'ARG1', 'EQ')])
    return d

def test_encode(empty_dmrs, it_rains_dmrs, it_rains_heavily_dmrs):
    assert dmrx.encode(empty_dmrs) == '<dmrs cfrom="-1" cto="-1" />'
    assert dmrx.encode(empty_dmrs, indent=True) == (
        '<dmrs cfrom="-1" cto="-1" />')

    assert dmrx.encode(it_rains_dmrs) == (
        '<dmrs cfrom="-1" cto="-1" index="10" top="10">'
        '<node cfrom="-1" cto="-1" nodeid="10">'
        '<realpred lemma="rain" pos="v" sense="1" />'
        '<sortinfo cvarsort="e" />'
        '</node></dmrs>')
    assert dmrx.encode(it_rains_dmrs, indent=True) == (
        '<dmrs cfrom="-1" cto="-1" index="10" top="10">\n'
        '<node cfrom="-1" cto="-1" nodeid="10">'
        '<realpred lemma="rain" pos="v" sense="1" />'
        '<sortinfo cvarsort="e" />'
        '</node>\n'
        '</dmrs>')
    assert dmrx.encode(it_rains_dmrs, indent=2) == (
        '<dmrs cfrom="-1" cto="-1" index="10" top="10">\n'
        '  <node cfrom="-1" cto="-1" nodeid="10">\n'
        '    <realpred lemma="rain" pos="v" sense="1" />\n'
        '    <sortinfo cvarsort="e" />\n'
        '  </node>\n'
        '</dmrs>')
