
from delphin import semi

def test_variables(tmpdir):
    p = tmpdir.join('a.smi')
    p.write('variables:\n'
            '  u.\n'
            '  i < u.\n'
            '  e < i : PERF bool, TENSE tense.')
    s = semi.load(str(p))
    assert len(s.variables) == 3
    assert all([v in s.variables for v in 'uie'])
    assert len(s.variables['u']['parents']) == 1
    assert len(s.variables['i']['parents']) == 1
    assert len(s.variables['e']['parents']) == 1
    assert s.variables['u']['properties'] == []
    assert s.variables['i']['properties'] == []
    assert s.variables['e']['properties'] == [
        ['PERF', 'bool'], ['TENSE', 'tense']]

def test_properties(tmpdir):
    p = tmpdir.join('a.smi')
    p.write('properties:\n'
            '  bool.\n'
            '  + < bool.\n'
            '  - < bool.\n')
    s = semi.load(str(p))
    assert len(s.properties) == 3
    assert all([x in s.properties for x in ('bool', '+', '-')])
    assert len(s.properties['bool']['parents']) == 1
    assert len(s.properties['+']['parents']) == 1
    assert len(s.properties['-']['parents']) == 1

def test_roles(tmpdir):
    p = tmpdir.join('a.smi')
    p.write('roles:\n'
            '  ARG0 : i.\n'
            '  CARG : string.')
    s = semi.load(str(p))
    assert len(s.roles) == 2
    assert all([r in s.roles for r in ('ARG0', 'CARG')])
    assert s.roles['ARG0']['value'] == 'i'
    assert s.roles['CARG']['value'] == 'string'

def test_predicates(tmpdir):
    p = tmpdir.join('a.smi')
    p.write('predicates:\n'
            '  existential_q.\n'
            '  _the_q < existential_q.\n'
            '  _predicate_n_1 : ARG0 x { IND + }.\n'
            '  _predicate_v_of : ARG0 e, ARG1 i, ARG2 p, [ ARG3 i ].\n'
            '  _predominant_a_1 : ARG0 e, ARG1 e.\n'
            '  _predominant_a_1 : ARG0 e, ARG1 p.')
    s = semi.load(str(p))
    assert set(s.predicates) == {'existential_q', '_the_q', '_predicate_n_1',
                                 '_predicate_v_of', '_predominant_a_1'}
    assert s.predicates['_the_q']['parents'] == ['existential_q']
    assert s.predicates['_predicate_n_1']['parents'] == ['*top*']
    assert s.predicates['_predicate_v_of']['parents'] == ['*top*']
    assert s.predicates['_predominant_a_1']['parents'] == ['*top*']
    assert len(s.predicates['_the_q']['synopses']) == 0
    assert len(s.predicates['_predicate_n_1']['synopses']) == 1
    assert len(s.predicates['_predicate_v_of']['synopses']) == 1
    assert len(s.predicates['_predominant_a_1']['synopses']) == 2

def test_include(tmpdir):
    a = tmpdir.join('a.smi')
    b = tmpdir.join('b.smi')
    tmpdir.mkdir('sub')
    c = tmpdir.join('sub', 'c.smi')
    d = tmpdir.join('sub', 'd.smi')
    a.write('predicates:\n'
            '  abstract_q : ARG0 x, RSTR h, BODY h.\n'
            '  can_able.\n'
            '  _able_a_1 < can_able.\n'
            'include: b.smi\n'
            'include: sub/c.smi')
    b.write('predicates:\n'
            '  existential_q < abstract_q.\n'
            '  _able_a_1 : ARG0 e, ARG1 p.')
    c.write('predicates:\n'
            '  universal_q < abstract_q\n'
            '  _able_a_1 : ARG0 e, ARG1 i, ARG2 h.\n'
            'include: d.smi')
    d.write('variables:\n'
            '  u.\n'
            '  i < u.\n'
            'properties:\n'
            '  tense.\n'
            '  pres < tense.\n'
            'roles:\n'
            '  ARG0 : i.')
    s = semi.load(str(a))
    assert len(s.variables) == 2
    assert len(s.properties) == 2
    assert len(s.roles) == 1
    assert 'abstract_q' in s.predicates
    assert 'existential_q' in s.predicates
    assert 'can_able' in s.predicates
    assert '_able_a_1' in s.predicates
    assert 'can_able' in s.predicates['_able_a_1']['parents']
    assert len(s.predicates['_able_a_1']['synopses']) == 2

def test_comments(tmpdir):
    p = tmpdir.join('a.smi')
    p.write('; comment\n'
            'variables:\n'
            '  ; comment\n'
            '  u.\n'
            '  ; x < u.\n'
            '  i < u.\n'
            '  e < i : PERF bool, TENSE tense.')
    s = semi.load(str(p))
    assert len(s.variables) == 3
    assert 'x' not in s.variables

def test_to_dict(tmpdir):
    p = tmpdir.join('a.smi')
    p.write('variables:\n'
            '  u.\n'
            '  i < u.\n'
            '  e < i : TENSE tense.\n'
            'properties:\n'
            '  tense.\n'
            '  pres < tense.\n'
            'roles:\n'
            '  ARG0 : i.\n'
            '  ARG1 : u.\n'
            'predicates:\n'
            '  existential_q.\n'
            '  _the_q < existential_q.\n'
            '  _predicate_n_1 : ARG0 x { IND + }.\n'
            '  _predicate_v_of : ARG0 e, ARG1 i, ARG2 p, [ ARG3 i ].\n'
            '  _predominant_a_1 : ARG0 e, ARG1 e.\n'
            '  _predominant_a_1 : ARG0 e, ARG1 p.')
    s = semi.load(str(p))
    assert s.to_dict() == {
        'variables': {
            'u': {'parents': ['*top*'], 'properties': []},
            'i': {'parents': ['u'], 'properties': []},
            'e': {'parents': ['i'], 'properties': [['TENSE', 'tense']]}
        },
        'properties': {
            'tense': {'parents': ['*top*']},
            'pres': {'parents': ['tense']}
        },
        'roles': {
            'ARG0': {'value': 'i'},
            'ARG1': {'value': 'u'}
        },
        'predicates': {
            'existential_q': {
                'parents': ['*top*'],
                'synopses': []
            },
            '_the_q': {
                'parents': ['existential_q'],
                'synopses': []
            },
            '_predicate_n_1': {
                'parents': ['*top*'],
                'synopses': [
                    [{'role': 'ARG0', 'value': 'x',
                      'properties': [['IND', '+']], 'optional': False}]
                ]
            },
            '_predicate_v_of': {
                'parents': ['*top*'],
                'synopses': [
                    [
                        {'role': 'ARG0', 'value': 'e',
                         'properties': [], 'optional': False},
                        {'role': 'ARG1', 'value': 'i',
                         'properties': [], 'optional': False},
                        {'role': 'ARG2', 'value': 'p',
                         'properties': [], 'optional': False},
                        {'role': 'ARG3', 'value': 'i',
                         'properties': [], 'optional': True}
                    ]
                ]
            },
            '_predominant_a_1': {
                'parents': ['*top*'],
                'synopses': [
                    [
                        {'role': 'ARG0', 'value': 'e',
                         'properties': [], 'optional': False},
                        {'role': 'ARG1', 'value': 'e',
                         'properties': [], 'optional': False}
                    ],
                    [
                        {'role': 'ARG0', 'value': 'e',
                         'properties': [], 'optional': False},
                        {'role': 'ARG1', 'value': 'p',
                         'properties': [], 'optional': False}
                    ]
                ]
            }
        }
    }

def test_from_dict(tmpdir):
    p = tmpdir.join('a.smi')
    p.write('variables:\n'
            '  u.\n'
            '  i < u.\n'
            '  e < i : TENSE tense.\n'
            'properties:\n'
            '  tense.\n'
            '  pres < tense.\n'
            'roles:\n'
            '  ARG0 : i.\n'
            '  ARG1 : u.\n'
            'predicates:\n'
            '  existential_q.\n'
            '  _the_q < existential_q.\n'
            '  _predicate_n_1 : ARG0 x { IND + }.\n'
            '  _predicate_v_of : ARG0 e, ARG1 i, ARG2 p, [ ARG3 i ].\n'
            '  _predominant_a_1 : ARG0 e, ARG1 e.\n'
            '  _predominant_a_1 : ARG0 e, ARG1 p.')
    s1 = semi.load(str(p))
    s2 = semi.SemI.from_dict({
        'variables': {
            'u': {'parents': ['*top*'], 'properties': []},
            'i': {'parents': ['u'], 'properties': []},
            'e': {'parents': ['i'], 'properties': [('TENSE', 'tense')]}
        },
        'properties': {
            'tense': {'parents': []},
            'pres': {'parents': ['tense']}
        },
        'roles': {
            'ARG0': {'value': 'i'},
            'ARG1': {'value': 'u'}
        },
        'predicates': {
            'existential_q': {
                'parents': ['*top*'],
                'synopses': []
            },
            '_the_q': {
                'parents': ['existential_q'],
                'synopses': []
            },
            '_predicate_n_1': {
                'parents': [],
                'synopses': [
                    [{'role': 'ARG0', 'value': 'x', 'properties': [('IND', '+')]}]
                ]
            },
            '_predicate_v_of': {
                'parents': [],
                'synopses': [
                    [
                        {'role': 'ARG0', 'value': 'e'},
                        {'role': 'ARG1', 'value': 'i'},
                        {'role': 'ARG2', 'value': 'p'},
                        {'role': 'ARG3', 'value': 'i', 'optional': True}
                    ]
                ]
            },
            '_predominant_a_1': {
                'parents': [],
                'synopses': [
                    [
                        {'role': 'ARG0', 'value': 'e'},
                        {'role': 'ARG1', 'value': 'e'}
                    ],
                    [
                        {'role': 'ARG0', 'value': 'e'},
                        {'role': 'ARG1', 'value': 'p'}
                    ]
                ]
            }
        }
    })
    assert s1.variables == s2.variables
    assert s1.properties == s2.properties
    assert s1.roles == s2.roles
    assert s1.predicates == s2.predicates
