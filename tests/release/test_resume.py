"""A failed zero-value judgment may be retried; pending calls and deposits may not."""
import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts import chain

HASH='0x'+'a'*64

def setup_journal(monkeypatch,tmp_path,receipt=None):
    monkeypatch.setattr(chain,'ROOT',tmp_path)
    monkeypatch.setattr(chain,'save',lambda proof:None)
    directory=tmp_path/'deploy/receipts'
    directory.mkdir(parents=True)
    if receipt is not None:
        (directory/'judge.json').write_text(json.dumps(receipt),encoding='utf8')
    return {'transactions':{'judge':HASH}}

def failed_receipt(**changes):
    return {'hash':HASH,'status':'FINALIZED','value':0,'result_name':'MAJORITY_DISAGREE',
            'consensus_data':{'leader_receipt':[{'execution_result':'ERROR'}]},
            'triggered_transactions':[],**changes}

def test_pending_hash_is_retained(monkeypatch,tmp_path):
    proof=setup_journal(monkeypatch,tmp_path)
    assert chain.adjudication_label(proof,'judge')=='judge'
    assert proof['transactions']['judge']==HASH and not proof['failedTransactions']

def test_failed_zero_value_receipt_is_retained_separately(monkeypatch,tmp_path):
    proof=setup_journal(monkeypatch,tmp_path,failed_receipt())
    assert chain.adjudication_label(proof,'judge')=='judge-submission-2'
    assert proof['failedTransactions']=={'judge':HASH} and not proof['transactions']
    assert chain.adjudication_label(proof,'judge')=='judge-submission-2'
    proof['transactions']['judge-submission-2']='0x'+'b'*64
    assert chain.adjudication_label(proof,'judge')=='judge-submission-2'

@pytest.mark.parametrize('changes',[{'value':1},{'hash':'0x'+'c'*64},{'triggered_transactions':['0x'+'d'*64]}])
def test_deposit_mismatched_hash_and_emitted_child_block_resubmission(monkeypatch,tmp_path,changes):
    proof=setup_journal(monkeypatch,tmp_path,failed_receipt(**changes))
    with pytest.raises(AssertionError):chain.adjudication_label(proof,'judge')
    assert proof['transactions']['judge']==HASH
