
import pytest

from delphin.sembase import Predicate
from delphin.dmrs import DMRS, Node, Link, simpledmrs

@pytest.fixture
def it_rains_heavily_dmrs():
    d = DMRS(
        20, 10, None,
        nodes=[Node(10, Predicate.surface('_rain_v_1'),
                    sortinfo={'cvarsort': 'e', 'TENSE': 'past'}),
               Node(20, Predicate.surface('_heavy_a_1'), sortinfo={'cvarsort': 'e'})],
        links=[Link(20, 10, 'ARG1', 'EQ')])
    return d

def test_encode(it_rains_heavily_dmrs):
    assert simpledmrs.encode(DMRS()) == 'dmrs { }'

    assert simpledmrs.encode(it_rains_heavily_dmrs) == (
        'dmrs {'
        ' [top=20 index=10]'
        ' 10 [_rain_v_1 e TENSE=past];'
        ' 20 [_heavy_a_1 e];'
        ' 20:ARG1/EQ -> 10;'
        ' }')

    assert simpledmrs.encode(it_rains_heavily_dmrs, indent=True) == (
        'dmrs {\n'
        '  [top=20 index=10]\n'
        '  10 [_rain_v_1 e TENSE=past];\n'
        '  20 [_heavy_a_1 e];\n'
        '  20:ARG1/EQ -> 10;\n'
        '}')

    assert simpledmrs.encode(
        it_rains_heavily_dmrs, properties=False, indent=True) == (
            'dmrs {\n'
            '  [top=20 index=10]\n'
            '  10 [_rain_v_1 e];\n'
            '  20 [_heavy_a_1 e];\n'
            '  20:ARG1/EQ -> 10;\n'
            '}')
