
"""
Semantic Interface (SEM-I)

Semantic interfaces (SEM-Is) describe the inventory of semantic
components in a grammar, including variables, properties, roles, and
predicates. This information can be used for validating semantic
structures or for filling out missing information in incomplete
representations.

.. seealso::
  - Wiki on SEM-I: http://moin.delph-in.net/SemiRfc

"""


import re
from os.path import dirname, join as pjoin

from delphin.tfs import TypeHierarchy


_SEMI_SECTIONS = (
    'variables',
    'properties',
    'roles',
    'predicates',
)

_variable_entry_re = re.compile(
    r'(?P<var>[^ <:.]+)'
    r'(?: < (?P<parents>[^ &:.]+(?: & [^ &:.]+)*))?'
    r'(?: : (?P<properties>[^ ]+ [^ ,.]+(?:, [^ ]+ [^ ,.]+)*))?'
    r'\s*\.\s*$',
    re.U
)

_property_entry_re = re.compile(
    r'(?P<type>[^ <.]+)'
    r'(?: < (?P<parents>[^ &.]+(?: & [^ &.]+)*))?'
    r'\s*\.\s*$',
    re.U
)

_role_entry_re = re.compile(
    r'(?P<role>[^ :]+) : (?P<value>[^ .]+)\s*\.\s*$',
    re.U
)

_predicate_entry_re = re.compile(
    r'(?P<pred>[^ <:.]+)'
    r'(?: < (?P<parents>[^ &:.]+(?: & [^ &:.]+)*))?'
    r'(?: : (?P<synposis>.*[^ .]))?'
    r'\s*\.\s*$',
    re.U
)

_synopsis_re = re.compile(
    r'\s*(?P<optional>\[\s*)?'
    r'(?P<role>[^ ]+) (?P<value>[^ ,.{\]]+)'
    r'(?:\s*\{\s*(?P<properties>[^ ]+ [^ ,}]+(?:, [^ ]+ [^ ,}]+)*)\s*\})?'
    r'(?(optional)\s*\])'
    r'(?:\s*(?:,\s*|$))',
    re.U
)

TOP = '*top*'


def load(fn):
    """
    Read the SEM-I beginning at the filename *fn* and return the SemI.

    Args:
        fn: the filename of the top file for the SEM-I. Note: this must
            be a filename and not a file-like object.
    Returns:
        The SemI defined by *fn*
    """
    data = _read_file(fn, dirname(fn))
    return SemI(**data)


def _read_file(fn, basedir):
    data = {
        'variables': [],
        'properties': [],
        'roles': [],
        'predicates': {},
    }
    section = None

    for line in open(fn, 'r'):
        line = line.lstrip()

        if not line or line.startswith(';'):
            continue

        match = re.match(r'(?P<name>[^: ]+):\s*$', line)
        if match is not None:
            name = match.group('name')
            if name not in _SEMI_SECTIONS:
                raise ValueError('Invalid SEM-I section: {}'.format(name))
            else:
                section = name
            continue

        match = re.match(r'include:\s*(?P<filename>.+)$', line, flags=re.U)
        if match is not None:
            include_fn = pjoin(basedir, match.group('filename').rstrip())
            include_data = _read_file(include_fn, dirname(include_fn))
            data['variables'].extend(include_data.get('variables', []))
            data['properties'].extend(include_data.get('properties', []))
            data['roles'].extend(include_data.get('roles', []))
            for pred, d in include_data['predicates'].items():
                if pred not in data['predicates']:
                    data['predicates'][pred] = {
                        'parents': [],
                        'synopses': []
                    }
                if d.get('parents'):
                    data['predicates'][pred]['parents'] = d['parents']
                if d.get('synopses'):
                    data['predicates'][pred]['synopses'].extend(d['synopses'])

        if section == 'variables':
            # e.g. e < i : PERF bool, TENSE tense.
            match = _variable_entry_re.match(line)
            if match is not None:
                identifier = match.group('var')
                supertypes = match.group('parents') or []
                if supertypes:
                    supertypes = supertypes.split(' & ')
                properties = match.group('properties') or []
                if properties:
                    pairs = properties.split(', ')
                    properties = [pair.split() for pair in pairs]
                v = {'parents': supertypes, 'properties': properties}
                # v = type(identifier, supertypes, d)
                data['variables'].append((identifier, v))
            else:
                raise ValueError('Invalid entry: {}'.format(line))

        elif section == 'properties':
            # e.g. + < bool.
            match = _property_entry_re.match(line)
            if match is not None:
                _type = match.group('type')
                supertypes = match.group('parents') or []
                if supertypes:
                    supertypes = supertypes.split(' & ')
                data['properties'].append((_type, {'parents': supertypes}))
            else:
                raise ValueError('Invalid entry: {}'.format(line))

        elif section == 'roles':
            # e.g. + < bool.
            match = _role_entry_re.match(line)
            if match is not None:
                rargname, value = match.group('role'), match.group('value')
                data['roles'].append((rargname, {'value': value}))
            else:
                raise ValueError('Invalid entry: {}'.format(line))

        elif section == 'predicates':
            # e.g. _predicate_n_1 : ARG0 x { IND + }.
            match = _predicate_entry_re.match(line)
            if match is not None:
                pred = match.group('pred')
                if pred not in data['predicates']:
                    data['predicates'][pred] = {
                        'parents': [],
                        'synopses': []
                    }
                sups = match.group('parents')
                if sups:
                    data['predicates'][pred]['parents'] = sups.split(' & ')
                synposis = match.group('synposis')
                roles = []
                if synposis:
                    for rolematch in _synopsis_re.finditer(synposis):
                        d = rolematch.groupdict()
                        propstr = d['properties'] or ''
                        d['properties'] = [pair.split()
                                           for pair in propstr.split(', ')
                                           if pair.strip() != '']
                        d['optional'] = bool(d['optional'])
                        roles.append(d)
                    data['predicates'][pred]['synopses'].append(roles)

    return data


class SemI(object):
    """
    A semantic interface.

    SEM-Is describe the semantic inventory for a grammar. These include
    the variable types, valid properties for variables, valid roles
    for predications, and a lexicon of predicates with associated roles.

    Args:
        variables: a mapping of (var, {'parents': [...], 'properties': [...]})
        properties: a mapping of (prop, {'parents': [...]})
        roles: a mapping of (role, {'value': ...})
        predicates: a mapping of (pred, {'parents': [...], 'synopses': [...]})
    """
    def __init__(self,
                 variables=None,
                 properties=None,
                 roles=None,
                 predicates=None):
        hier = {}
        # validate and normalize inputs
        self.variables = {}
        for var, data in dict(variables or []).items():
            _validate_parents(var, data, hier)
            self.variables[var] = dict(
                parents=hier[var],
                properties=[[k, v] for k, v in data['properties']])

        self.properties = {}
        for prop, data in dict(properties or []).items():
            _validate_parents(prop, data, hier)
            self.properties[prop] = {'parents': hier[prop]}

        self.roles = {}
        for role, data in dict(roles or []).items():
            self.roles[role] = {'value': data['value']}

        self.predicates = {}
        for pred, data in dict(predicates or []).items():
            _validate_parents(pred, data, hier)
            synopses = []
            for synopsis in data['synopses']:
                synopses.append(list(
                    dict(role=d['role'],
                         value=d['value'],
                         properties=[
                             [k, v] for k, v in d.get('properties', [])],
                         optional=d.get('optional', False))
                    for d in synopsis))
            self.predicates[pred] = dict(
                parents=hier[pred],
                synopses=synopses)

        self.type_hierarchy = TypeHierarchy(TOP, hier)

    @classmethod
    def from_dict(cls, d):
        """Instantiate a SemI from a dictionary representation."""
        return cls(**d)

    def to_dict(self):
        """Return a dictionary representation of the SemI."""
        return dict(
            variables=dict(self.variables),
            properties=dict(self.properties),
            roles=dict(self.roles),
            predicates=dict(self.predicates))


def _validate_parents(key, data, hier):
    parents = list(data['parents'] or [TOP])  # if no parents, TOP is implied
    if key in hier:
        raise ValueError('type \'{}\' is defined more than once'.format(key))
    hier[key] = parents
