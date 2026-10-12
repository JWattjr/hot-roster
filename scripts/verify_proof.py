"""Read-only verification: never imports signer(), reads secrets or signs a call."""
import base64
import hashlib
import importlib.metadata
import json
import time
from pathlib import Path
from eth_account import Account
from genlayer_py import create_client,studionet
from genlayer_py.types import TransactionHashVariant
from genlayer_py.provider import provider

assert importlib.metadata.version('genlayer-py')=='0.18.0'
ROOT=Path(__file__).resolve().parent.parent
proof=json.loads((ROOT/'deploy/proof.json').read_text(encoding='utf8'))
_post=provider.requests.post
def browser_post(url,**kwargs):
    kwargs['headers']={**kwargs.get('headers',{}),'User-Agent':'Mozilla/5.0 HotRosterProof/1.0'}
    kwargs.setdefault('timeout',60)
    return _post(url,**kwargs)
provider.requests.post=browser_post
# Disposable caller only: gen_call requires an account, but no method signs.
c=create_client(chain=studionet,account=Account.create())
def read(address,method,args):
    result=c.read_contract(address,method,args=args,transaction_hash_variant=TransactionHashVariant.LATEST_FINAL)
    time.sleep(2.6)
    return json.loads(result) if isinstance(result,str) else result
def verify_receipt(h):
    result=c.provider.make_request('eth_getTransactionByHash',[h])['result']
    assert result['status']=='FINALIZED','Not final: '+h
    if result.get('value_credited') is True:
        return result
    leader=(result.get('consensus_data',{}).get('leader_receipt') or [{}])[0]
    assert leader.get('execution_result') in ('SUCCESS','FINISHED_WITH_RETURN'),'Failed execution: '+h
    assert result.get('result_name') in (None,'AGREE','MAJORITY_AGREE','SUCCESS'),'Consensus rejected: '+h
    if isinstance(leader.get('result'),str):
        assert base64.b64decode(leader['result'])[:1]==b'\x00','Rollback: '+h
    return result
def main():
    receipts={}
    for name,h in proof['transactions'].items():
        receipts[name]=verify_receipt(h)
        print(name,h,'FINALIZED_SUCCESS',flush=True)
        time.sleep(2.6)
    for name,contract in proof['contracts'].items():
        source=(ROOT/'contracts'/contract['source']).read_text(encoding='utf8')
        assert hashlib.sha256(source.encode()).hexdigest()==contract['sha256'],'Local source hash changed: '+name
        deployed=c.provider.make_request('gen_getContractCode',[contract['address']])['result']
        raw=base64.b64decode(deployed) if isinstance(deployed,str) else b''
        assert hashlib.sha256(raw).hexdigest()==contract['sha256'],'Deployed source differs: '+name
        time.sleep(2.6)
    assert proof.get('leagueId'),'No replay league created'
    league=read(proof['contracts']['League']['address'],'get_league',[proof['leagueId']])
    assert league==proof['league'],'Recorded league differs from finalized state'
    assert hashlib.sha256(league['rulebook'].encode()).hexdigest()==league['rulebook_hash']
    for i in range(6):
        chart=read(proof['contracts']['ChartReader']['address'],'get_read',[league['id'],i])
        assert chart==proof['weeks'][i],'Recorded chart differs from finalized state'
        assert chart.get('status')=='RESOLVED' and len(chart['rows'])==100,'Incomplete week '+str(i+1)
        assert hashlib.sha256(json.dumps(chart['rows'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==chart['digest']
        assert len(chart['matches'])==20 and chart['songs']==league['weeks'][i]['songs']
    for moment in proof['moments']:
        assert read(proof['contracts']['MomentJudge']['address'],'get_claim',[moment['id']])==moment
    for dispute in proof['disputes']:
        assert read(proof['contracts']['RulebookCourt']['address'],'get_dispute',[dispute['id']])==dispute
        assert dispute['rule_quote'] in league['rulebook']
    missing=[]
    for verdict in ('AWARDED','NOT_AWARDED'):
        if not any(m['verdict']==verdict for m in proof['moments']):missing.append('Missing live '+verdict+' card')
    for verdict in ('OVERTURNED','UPHELD'):
        if not any(d['verdict']==verdict for d in proof['disputes']):missing.append('Missing live '+verdict+' dispute')
    pool=read(proof['contracts']['SeasonPool']['address'],'get_pool',[league['id']])
    assert pool==proof['pool'] and pool['status']=='SETTLED'
    assert sum(map(int,pool['payouts'].values()))==int(pool['total'])==40
    winner=league['standings'][0]['wallet']
    claim=pool['claims'][winner]
    assert claim['status']=='PAID'
    credit=verify_receipt(claim['child'])
    assert credit['value_credited'] is True and credit['to_address'].lower()==winner and int(credit['value'])==int(claim['amount'])
    assert league['status']=='COMPLETED' and proof['sourceCommit']
    print('Six chart reads, deployed sources, final standings and exact native winner credit verified.',flush=True)
    assert not missing,'; '.join(missing)
    assert proof['completed'],'Manifest does not claim completion'
    print('Complete replay, source, standings, outcomes and native payout verified. No write was sent.')
if __name__=='__main__':main()
