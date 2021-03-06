
from datetime import datetime

import pytest

from delphin import tsql
from delphin import itsdb
from delphin.exceptions import TSQLSyntaxError

from .commands_test import mini_testsuite as ts0


def test_parse_query():
    parse = lambda s: tsql._parse_query(s)
    with pytest.raises(TSQLSyntaxError):
        parse('info relations')
    with pytest.raises(TSQLSyntaxError):
        parse('set max-results 5')
    with pytest.raises(TSQLSyntaxError):
        parse('insert into item i-id values 10')


def test_parse_select():
    parse = lambda s: tsql._parse_select(s)
    with pytest.raises(TSQLSyntaxError):
        parse('*')
    # with pytest.raises(TSQLSyntaxError):
    #     parse('i-input from item report "%s"')

    assert parse('i-input') == {
        'querytype': 'select',
        'projection': ['i-input'],
        'tables': [],
        'where': None}

    assert parse('i-input i-wf') == {
        'querytype': 'select',
        'projection': ['i-input', 'i-wf'],
        'tables': [],
        'where': None}

    assert parse('i-input i-wf from item') == {
        'querytype': 'select',
        'projection': ['i-input', 'i-wf'],
        'tables': ['item'],
        'where': None}

    assert parse('i-input mrs from item result') == {
        'querytype': 'select',
        'projection': ['i-input', 'mrs'],
        'tables': ['item', 'result'],
        'where': None}


def test_parse_select_complex_identifiers():
    parse = lambda s: tsql._parse_select(s)
    assert parse('item:i-input') == {
        'querytype': 'select',
        'projection': ['item:i-input'],
        'tables': [],
        'where': None}

    assert parse('item:i-id@i-input') == {
        'querytype': 'select',
        'projection': ['item:i-id', 'item:i-input'],
        'tables': [],
        'where': None}

    assert parse('item:i-id@result:mrs') == {
        'querytype': 'select',
        'projection': ['item:i-id', 'result:mrs'],
        'tables': [],
        'where': None}

    assert parse('item:i-id@i-input mrs') == {
        'querytype': 'select',
        'projection': ['item:i-id', 'item:i-input', 'mrs'],
        'tables': [],
        'where': None}


def test_parse_select_where():
    parse = lambda s: tsql._parse_select(s)
    assert parse('i-input where i-wf = 2') == {
        'querytype': 'select',
        'projection': ['i-input'],
        'tables': [],
        'where': ('==', ('i-wf', 2))}

    assert parse('i-input where i-date < 2018-01-15')['where'] == (
        '<', ('i-date', datetime(2018, 1, 15)))

    assert parse('i-input where i-date > 15-jan-2018(15:00:00)')['where'] == (
        '>', ('i-date', datetime(2018, 1, 15, 15, 0, 0)))

    assert parse('i-input where i-input ~ "Abrams"')['where'] == (
        '~', ('i-input', 'Abrams'))

    assert parse("i-input where i-input !~ 'Browne'")['where'] == (
        '!~', ('i-input', 'Browne'))

    assert parse('i-input '
                 'where i-wf = 2 & i-input ~ \'[Dd]og\'')['where'] == (
        'and', (('==', ('i-wf', 2)),
                ('~', ('i-input', '[Dd]og'))))

    assert parse('i-input '
                 'where i-id = 10 | i-id = 20 & i-wf = 2')['where'] == (
        'or', (('==', ('i-id', 10)),
               ('and', (('==', ('i-id', 20)),
                        ('==', ('i-wf', 2))))))

    assert parse('i-input '
                 'where (i-id = 10 | i-id = 20) & !i-wf = 2')['where'] == (
        'and', (('or', (('==', ('i-id', 10)),
                        ('==', ('i-id', 20)))),
                ('not', ('==', ('i-wf', 2)))))


def test_select(ts0):
    ts = itsdb.TestSuite(str(ts0))
    assert list(tsql.select('i-input', ts)) == [
        ['It rained.'], ['Rained.'], ['It snowed.']]
    assert list(tsql.select('i-input from item', ts)) == [
        ['It rained.'], ['Rained.'], ['It snowed.']]
    assert list(tsql.select('i-input from item item', ts)) == [
        ['It rained.'], ['Rained.'], ['It snowed.']]
    assert list(tsql.select('i-input from result', ts)) == [
        ['It rained.'], ['It snowed.']]
    assert list(tsql.select('i-input from item result', ts)) == [
        ['It rained.'], ['It snowed.']]
    assert list(tsql.select('i-id i-input', ts)) == [
        [10, 'It rained.'], [20, 'Rained.'], [30, 'It snowed.']]
    res = ts['result']
    assert list(tsql.select('i-id mrs', ts)) == [
        [10, res[0]['mrs']], [30, res[1]['mrs']]]
    with pytest.raises(tsql.TSQLSyntaxError):
        tsql.select('*', ts)
    assert list(tsql.select('* from item', ts, cast=False)) == ts['item']


def test_select_where(ts0):
    ts = itsdb.TestSuite(str(ts0))
    assert list(tsql.select('i-input where i-input ~ "It"', ts)) == [
        ['It rained.'], ['It snowed.']]
    assert list(tsql.select('i-input where i-input ~ "It" or i-id = 20', ts)) == [
        ['It rained.'], ['Rained.'], ['It snowed.']]
    assert list(tsql.select('i-input where i-date >= 2018-02-01', ts)) == [
        ['It rained.'], ['Rained.'], ['It snowed.']]
    assert list(tsql.select('i-input where readings > 0', ts)) == [
        ['It rained.'], ['It snowed.']]
