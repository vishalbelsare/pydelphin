
delphin.semi
============

.. automodule:: delphin.semi

  Loading a SEM-I from a File
  ---------------------------

  .. autofunction:: load

  The SemI Class
  --------------

  .. autoclass:: SemI

    The data in the SEM-I can be directly inspected via the
    :attr:`variables`, :attr:`properties`, :attr:`roles`,
    :attr:`predicates`, and :attr:`type_hierarchy` attributes:

    >>> smi = semi.load('erg.smi')
    >>> smi.variables['e']
    [('PERF', 'bool'), ('PROGR', 'bool'), ('MOOD', 'bool'), ('TENSE', 'tense'), ('SF', 'sf')]
    >>> 'sf' in smi.properties
    True
    >>> smi.roles['ARG0']
    'i'
    >>> smi.predicates['can_able']
    [[('ARG0', 'e', [], False), ('ARG1', 'i', [], False), ('ARG2', 'p', [], False)]]
    >>> smi.type_hierarchy.descendants('some_q')
    ['_a_q', '_an+additional_q', '_another_q', '_many+a_q', '_some_q', '_some_q_indiv', '_such+a_q', '_what+a_q']

    There are also several methods for more convenient access to the
    type hierarchy and for matching predicate synopses. The former are
    the same as calling the methods on :attr:`type_hierarchy` directly,
    but they additionally case-normalize the type names.

    .. automethod:: subsumes
    .. automethod:: compatible
    .. automethod:: find_synopsis

    The :func:`load` module function is used to read the regular
    file-based SEM-I definitions, but there is also a dictionary
    representation which may be useful for, e.g., an HTTP API that
    makes use of SEM-Is.

    .. automethod:: from_dict
    .. automethod:: to_dict

  Exceptions
  ----------

  .. autoclass:: SemIError
    :show-inheritance:
