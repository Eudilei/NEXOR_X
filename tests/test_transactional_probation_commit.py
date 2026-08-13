from datetime import UTC, datetime
import pytest
from nexor_x.operations.post_recovery_probation import PostRecoveryProbationController

def normal(): return {'state':'NORMAL','new_entries_allowed':True,'hard_reasons':[],'caution_reasons':[]}

def test_evaluate_does_not_consume_slot(tmp_path):
    g=PostRecoveryProbationController(state_path=tmp_path/'p.json'); t=datetime(2026,8,13,10,0,tzinfo=UTC); g.start(now=t)
    r=g.evaluate(degradation=normal(),action='PAPER_OPEN',now=t)
    assert r['admitted_entries']==0 and g.status(now=t)['admitted_entries']==0

def test_success_commits(tmp_path):
    g=PostRecoveryProbationController(state_path=tmp_path/'p.json'); g.start()
    with g.successful_entry_transaction(action='PAPER_OPEN'): pass
    assert g.status()['admitted_entries']==1

def test_exception_does_not_commit(tmp_path):
    g=PostRecoveryProbationController(state_path=tmp_path/'p.json'); g.start()
    with pytest.raises(RuntimeError):
        with g.successful_entry_transaction(action='TESTNET_CREATE'):
            raise RuntimeError('fail')
    assert g.status()['admitted_entries']==0

def test_reduce_only_bypass(tmp_path):
    g=PostRecoveryProbationController(state_path=tmp_path/'p.json'); g.start()
    with g.successful_entry_transaction(action='TESTNET_CREATE',bypass=True): pass
    assert g.status()['admitted_entries']==0

def test_first_step_remains_zero_before_commit(tmp_path):
    g=PostRecoveryProbationController(state_path=tmp_path/'p.json'); g.start()
    r=g.evaluate(degradation=normal(),action='PAPER_OPEN')
    assert r['admitted_entries']==0
