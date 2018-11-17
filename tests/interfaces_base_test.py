
import pytest

from delphin.interfaces.base import ParseResponse, ParseResult
from delphin.mrs import simplemrs
from delphin.dmrs import dmrsjson
from delphin.eds import edsjson
from delphin.derivation import Derivation
from delphin.exceptions import XmrsDeserializationError
from delphin.tokens import YyTokenLattice

def test_ParseResult():
    r = ParseResult()
    assert len(r) == 0
    assert r.mrs() is None
    assert r.dmrs() is None
    assert r.eds() is None
    assert r.derivation() is None

    mrs_s = '[ TOP: h0 RELS: < ["_rain_v_1_rel" LBL: h1 ARG0: e2 ] > HCONS: < h0 qeq h1 > ]'
    mrs_d = {
        'top': 'h0',
        'relations': [
            {
                'predicate': '_rain_v_1',
                'label': 'h1',
                'arguments': {'ARG0': 'e2'}
            }
        ],
        'constraints': [
            {'relation': 'qeq', 'high': 'h0', 'low': 'h1'}
        ]
    }
    mrs = simplemrs.loads_one(mrs_s)

    r = ParseResult(mrs=mrs_s)
    assert len(r) == 1
    assert r['mrs'] == mrs_s
    assert r.mrs() == mrs

    r = ParseResult(mrs=mrs_d)
    assert len(r) == 1
    assert r['mrs'] == mrs_d
    assert r.mrs() == mrs

    r = ParseResult(mrs=mrs_d)
    assert len(r) == 1
    assert r['mrs'] == mrs_d
    assert r.mrs() == mrs

    # r = ParseResult(mrs='nonsense')
    # assert r['mrs'] == 'nonsense'
    # with pytest.raises(XmrsDeserializationError):
    #     r.mrs()

    dmrs_d = {
        'nodes': [
            {'nodeid': 10000, 'predicate': '_rain_v_1',
             'sortinfo': {'cvarsort': 'e'}}
        ],
        'links': [
            {'from': 0, 'to': 10000, 'rargname': None, 'post': 'H'}
        ]
    }
    dmrs = dmrsjson.from_dict(dmrs_d)

    r = ParseResult(dmrs=dmrs_d)
    assert len(r) == 1
    assert r['dmrs'] == dmrs_d
    assert r.dmrs() == dmrs

    # r = ParseResult(dmrs='nonsense')
    # assert len(r) == 1
    # assert r['dmrs'] == 'nonsense'
    # with pytest.raises(XmrsDeserializationError):
    #     r.dmrs()

    eds_d = {
        'top': 'e2',
        'nodes': {
            'e2': {
                'label': '_rain_v_1',
                'lnk': {'from': 3, 'to': 9},
                'edges': {}
            }
        }
    }
    eds_s = '{e2: e2:_rain_v_1<3:9>[]}'
    eds = edsjson.from_dict(eds_d)

    r = ParseResult(eds=eds_s)
    assert len(r) == 1
    assert r['eds'] == eds_s
    assert r.eds() == eds

    r = ParseResult(eds=eds_d)
    assert len(r) == 1
    assert r['eds'] == eds_d
    assert r.eds() == eds

    # r = ParseResult(eds='nonsense')
    # assert len(r) == 1
    # assert r['eds'] == 'nonsense'
    # with pytest.raises(XmrsDeserializationError):
    #     r.eds()

    # several changes were made to the below for compatibility:
    #  - removed head annotation (on W_PERIOD_PLR)
    #  - removed type info
    #  - removed from/to info
    #  - added start/end
    #  - escaped quotes
    #  - capitalized entity names

    deriv_s = '(189 SB-HD_MC_C 0.228699 0 2 (37 it 0.401245 0 1 ("it" 34 "token [ +FORM \\"it\\" +FROM #1=\\"0\\" +TO \\"2\\" ]")) (188 W_PERIOD_PLR -0.113641 1 2 (187 V_PST_OLR 0 1 2 (56 rain_v1 0 1 2 ("rained." 32 "token [ +FORM \\"rained.\\" +FROM #1=\\"3\\" +TO \\"10\\" ]")))))'
    deriv_d = {
        "id": 189, "entity": "SB-HD_MC_C", "label": "S", "score": 0.228699, "start": 0, "end": 2, "daughters": [  # , "type": "subjh_mc_rule"
            {"id": 37, "entity": "it", "score": 0.401245, "start": 0, "end": 1, "form": "it", "tokens": [  # , "type": "n_-_pr-it-x_le" , "from": 0, "to": 2
                {"id": 34, "tfs": "token [ +FORM \\\"it\\\" +FROM #1=\\\"0\\\" +TO \\\"2\\\" ]"}]},  # , "from": 0, "to": 2
            {"id": 188, "entity": "W_PERIOD_PLR", "score": -0.113641, "start": 1, "end": 2, "daughters": [  # , "type": "punctuation_period_rule"
                {"id": 187, "entity": "V_PST_OLR", "score": 0, "start": 1, "end": 2, "daughters": [  # , "type": "v_pst_inflrule"
                    {"id": 56, "entity": "rain_v1", "score": 0, "start": 1, "end": 2, "form": "rained.", "tokens": [  # , "type": "v_-_it_le", "from": 3, "to": 10
                        {"id": 32, "tfs": "token [ +FORM \\\"rained.\\\" +FROM #1=\\\"3\\\" +TO \\\"10\\\" ]"}]}]}]}]  # , "from": 3, "to": 10
    }
    deriv = Derivation.from_dict(deriv_d)

    r = ParseResult(derivation=deriv_s)
    assert len(r) == 1
    assert r['derivation'] == deriv_s
    assert r.derivation() == deriv

    r = ParseResult(derivation=deriv_d)
    assert len(r) == 1
    assert r['derivation'] == deriv_d
    assert r.derivation() == deriv

def test_ParseResponse():
    r = ParseResponse()
    assert len(r) == 0
    assert r.results() == []
    assert r.tokens() is None

    r = ParseResponse(key="val")
    assert len(r) == 1
    assert r['key'] == 'val'

    r = ParseResponse(results=[{}]) 
    assert len(r) == 1
    assert r['results'] == [{}]
    assert isinstance(r.results()[0], ParseResult)
    assert isinstance(r.result(0), ParseResult)

    toks_s = '(1, 0, 1, <0:4>, 1, "Dogs", 0, "null")'
    toks_d = [
        {'id': 1, 'start': 0, 'end': 1, 'from': 0, 'to': 4, "form": "Dogs"}
    ]
    toks = YyTokenLattice.from_list(toks_d)

    r = ParseResponse(tokens={'initial': toks_s})
    assert r['tokens']['initial'] == toks_s
    print(r.tokens('initial'))
    assert r.tokens('initial') == toks
    assert r.tokens('internal') == None

    r = ParseResponse(tokens={'initial': toks_d})
    assert r['tokens']['initial'] == toks_d
    assert r.tokens('initial') == toks
    assert r.tokens('internal') == None

    r = ParseResponse(tokens={'internal': toks_s})
    assert r['tokens']['internal'] == toks_s
    assert r.tokens('initial') == None
    assert r.tokens('internal') == toks
    assert r.tokens() == toks
