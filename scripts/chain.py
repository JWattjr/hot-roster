"""Pinned release SDK, browser UA, explicit budgets, durable hashes and bounded polls."""
import importlib.metadata
import json
import time
from pathlib import Path
from eth_account import Account
from genlayer_py import create_client, studionet
from genlayer_py.types import TransactionHashVariant
from genlayer_py.provider import provider

ROOT = Path(__file__).resolve().parent.parent
assert importlib.metadata.version('genlayer-py') == '0.18.0'
_post = provider.requests.post
def browser_post(url, **kwargs):
    kwargs['headers'] = {**kwargs.get('headers', {}), 'User-Agent': 'Mozilla/5.0 HotRoster/1.0'}
    kwargs.setdefault('timeout', 60)
    return _post(url, **kwargs)
provider.requests.post = browser_post

def signer(index=0):
    directory = ROOT / '.secrets'
    directory.mkdir(exist_ok=True)
    path = directory / 'demo-accounts.json'
    if not path.exists():
        path.write_text(json.dumps([Account.create().key.hex() for _ in range(4)]))
    keys = json.loads(path.read_text())
    return Account.from_key(keys[index])

def client(index=0):
    return create_client(chain=studionet, account=signer(index))

def fees(c):
    try:
        result = c.estimate_transaction_fees({'leaderTimeunitsAllocation': 300, 'validatorTimeunitsAllocation': 600, 'totalMessageFees': 0, 'rotations': [2]})
    except Exception as error:
        if 'missing fee_manager_contract and sim_getFeeConfig' not in str(error):
            raise
        # Pinned SDK explicitly supports the legacy ABI when only feeValue=0
        # is given. StudioNet 61999 has no FeeManager; EVM gasPrice is 0 in
        # SDK _prepare_transaction for this chain. Never fake a policy quote.
        return {'feeValue': 0}
    # Require human approval before any fee deposit on a non-gasless endpoint.
    if int(result['feeValue']) != 0:
        raise RuntimeError('Network now charges fees; owner approval is needed before a fee deposit')
    return {'distribution': result['distribution'], 'feeValue': result['feeValue']}

def successful(r):
    if r.get('value_credited') is True and r.get('status')=='FINALIZED':
        return True
    leader = (r.get('consensus_data', {}).get('leader_receipt') or [{}])[0]
    status = r.get('status_name', r.get('statusName', r.get('status')))
    execution = r.get('txExecutionResultName', leader.get('execution_result'))
    consensus = r.get('result_name', r.get('resultName'))
    return status in ('FINALIZED', 7, '7') and execution in ('SUCCESS', 'FINISHED_WITH_RETURN') and consensus in (None, 'AGREE', 'MAJORITY_AGREE', 'SUCCESS')

def raw(c, hash_value):
    return c.provider.make_request('eth_getTransactionByHash', [hash_value])['result']

def final(c, hash_value, name, seconds=1800):
    directory = ROOT / 'deploy/receipts'
    directory.mkdir(exist_ok=True)
    for attempt in range(seconds // 10):
        r = raw(c, hash_value)
        if r and r.get('status_name', r.get('status')) in ('FINALIZED', 7, '7'):
            (directory / (name + '.json')).write_text(json.dumps(r, indent=2), encoding='utf8')
            if not successful(r):
                raise RuntimeError('Finalized execution failed: ' + name + ' ' + str(r.get('result_name')))
            print(name, hash_value, 'FINALIZED_SUCCESS', flush=True)
            return r
        if attempt % 6 == 0:
            print(name, 'waiting', r.get('status') if r else 'submitted', flush=True)
        time.sleep(10)
    raise RuntimeError('Still pending; rerun to resume saved hash ' + hash_value)

def read(c, address, method, args=None):
    value = c.read_contract(address, method, args=args or [], transaction_hash_variant=TransactionHashVariant.LATEST_FINAL)
    time.sleep(2.2)
    return json.loads(value) if isinstance(value, str) and value.startswith(('{', '[')) else value

def save(proof):
    target=ROOT/'deploy/proof.json'
    current=json.loads(target.read_text(encoding='utf8')) if target.exists() else {}
    for key in ('sourceCommit','website','github'):
        if current.get(key) and not proof.get(key):
            proof[key]=current[key]
    temporary=ROOT/'deploy/proof.json.tmp'
    temporary.write_text(json.dumps(proof,indent=2),encoding='utf8')
    temporary.replace(target)

def transaction(c, proof, name, address=None, method=None, args=None, code=None, value=0):
    if name not in proof['transactions']:
        budget = fees(c)
        h = c.deploy_contract(code, args=args or [], fees=budget) if code is not None else c.write_contract(address, method, args=args or [], value=value, fees=budget)
        proof['transactions'][name] = h.hex() if hasattr(h, 'hex') else str(h)
        if not proof['transactions'][name].startswith('0x'):
            proof['transactions'][name] = '0x' + proof['transactions'][name]
        save(proof)
    receipt = final(c, proof['transactions'][name], name)
    for i, child in enumerate(receipt.get('triggered_transactions') or []):
        child_name = name + '-child-' + str(i)
        proof['transactions'][child_name] = child
        save(proof)
        final(c, child, child_name)
    return receipt
