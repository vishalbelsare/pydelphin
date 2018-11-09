
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
from delphin.exceptions import PyDelphinException


TOP_TYPE = '*top*'
STRING_TYPE = 'string'


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


class SemIError(PyDelphinException):
    """
    Raised when loading an invalid SEM-I.
    """


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
        self.type_hierarchy = hier = TypeHierarchy(TOP_TYPE)
        # validate and normalize inputs
        self.properties = set()
        subhier = {}
        for prop, data in dict(properties or []).items():
            subhier[prop] = data['parents'] or [TOP_TYPE]
            self.properties.add(prop)
        self.type_hierarchy.update(subhier)

        propcache = {}  # just for consistency checks during construction
        subhier = {}
        self.variables = {}
        for var, data in dict(variables or []).items():
            subhier[var] = data['parents'] or [TOP_TYPE]
            self.variables[var] = proplist = []
            propcache[var] = dict(data.get('properties', []))
            for k, v in data.get('properties', []):
                if v not in self.properties:
                    raise SemIError('undefined property value: {}'.format(v))
                proplist.append((k, v))
        self.type_hierarchy.update(subhier)

        self.roles = {}
        for role, data in dict(roles or []).items():
            var = data['value']
            if not (var == STRING_TYPE or var in self.variables):
                raise SemIError('undefined variable type: {}'.format(var))
            self.roles[role] = var

        self.predicates = {}
        subhier = {}
        for pred, data in dict(predicates or []).items():
            subhier[pred] = data['parents'] or [TOP_TYPE]
            synopses = []
            for synopsis_data in data['synopses']:
                synopsis = []
                for d in synopsis_data:
                    role, value, proplist = d['role'], d['value'], []
                    if role not in self.roles:
                        raise SemIError('undefined role: {}'.format(role))
                    if value == STRING_TYPE:
                        if d.get('properties', False):
                            raise SemIError('strings cannot define properties')
                    elif value not in self.variables:
                        raise SemIError('undefined variable type: {}'
                                        .format(value))
                    else:
                        proplist = []
                        for k, v in d.get('properties', []):
                            if k not in propcache[value]:
                                raise SemIError(
                                    "property '{}' not allowed on '{}'"
                                    .format(k, value))
                            if v not in self.properties:
                                raise SemIError('undefined property value: {}'
                                                .format(v))
                            _v = propcache[value].get(k)
                            if not self.type_hierarchy.compatible(v, _v):
                                raise SemIError(
                                    'incompatible property values: {}, {}'
                                    .format(v, _v))
                            proplist.append((k, v))
                    synopsis.append(
                        (role, value, proplist, d.get('optional', False)))
                synopses.append(synopsis)
            self.predicates[pred] = synopses
        self.type_hierarchy.update(subhier)

    @classmethod
    def from_dict(cls, d):
        """Instantiate a SemI from a dictionary representation."""
        return cls(**d)

    def to_dict(self):
        """Return a dictionary representation of the SemI."""
        hier = self.type_hierarchy
        def parents(x):
            ps = hier[x]
            if ps == [TOP_TYPE]:
                return []
            return ps
        variables={var: {'parents': parents(var),
                         'properties': [[k, v] for k, v in props]}
                   for var, props in self.variables.items()}
        properties={prop: {'parents': parents(prop)}
                    for prop in self.properties}
        roles={role: {'value': value} for role, value in self.roles.items()}
        predicates = {}
        for pred, synopses in self.predicates.items():
            synopses = [
                [{'role': role, 'value': value,
                  'properties': [[k, v] for k, v in properties],
                  'optional': optional}
                 for role, value, properties, optional in synopsis]
                for synopsis in synopses]
            predicates[pred] = {'parents': parents(pred), 'synopses': synopses}
        return dict(variables=variables,
                    properties=properties,
                    roles=roles,
                    predicates=predicates)
