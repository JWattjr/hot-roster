"""Read-only verification: never imports signer(), reads secrets or signs a call."""
import base64
import hashlib
import importlib.metadata
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from eth_account import Account
from genlayer_py import create_client,studionet
from genlayer_py.types import TransactionHashVariant
from genlayer_py.provider import provider

assert importlib.metadata.version('genlayer-py')=='0.18.0'
ROOT=Path(__file__).resolve().parent.parent
proof=json.loads((ROOT/'deploy/proof.json').read_text(encoding='utf8'))
_post=provider.requests.post
_rpc_lock=threading.Lock()
_rpc_next=0.0
def browser_post(url,**kwargs):
    global _rpc_next
    kwargs['headers']={**kwargs.get('headers',{}),'User-Agent':'Mozilla/5.0 HotRosterProof/1.0'}
    kwargs.setdefault('timeout',60)
    for attempt in range(3):
        with _rpc_lock:
            start=max(time.monotonic(),_rpc_next)
            _rpc_next=start+2.6
        time.sleep(max(0,start-time.monotonic()))
        response=_post(url,**kwargs)
        if response.status_code not in (502,503,504) or attempt==2:return response
        print('Transient read-only RPC HTTP',response.status_code,'retry',attempt+1,flush=True)
        time.sleep(10)
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
    if result.get('value_credited') is True and result.get('type')==0 and result.get('consensus_data') is None:
        return result
    leader=(result.get('consensus_data',{}).get('leader_receipt') or [{}])[0]
    assert leader.get('execution_result') in ('SUCCESS','FINISHED_WITH_RETURN'),'Failed execution: '+h
    assert result.get('result_name') in (None,'AGREE','MAJORITY_AGREE','SUCCESS'),'Consensus rejected: '+h
    if isinstance(leader.get('result'),str):
        assert base64.b64decode(leader['result'])[:1]==b'\x00','Rollback: '+h
    return result

def verify_scoring(league,charts,moments,disputes):
    stats={p:{'points':0,'wins':0,'losses':0,'ties':0} for p in league['players']}
    adjustments={p:0 for p in league['players']}
    rulings={d['item_id']:d for d in disputes if d['status']=='RESOLVED'}
    claims={m['id']:m for m in moments}
    for i,week in enumerate(league['weeks']):
        assert week['status']=='CLOSED'
        expected={p:0 for p in league['players']}
        rows={r['position']:r for r in charts[i]['rows']}
        for song,match in zip(week['songs'],charts[i]['matches']):
            ruling=rulings.get('chart:'+league['id']+':'+str(i)+':'+song['key'],{})
            position=ruling['corrected_position'] if ruling.get('verdict')=='OVERTURNED' else match['position']
            row=rows.get(position,{'last_week':0,'debut':False})
            base=25 if position==1 else 15 if 2<=position<=10 else 8 if 11<=position<=40 else 3 if 41<=position<=100 else 0
            base+=5 if position>0 and row['debut'] else 0
            base+=3 if position>0 and row['last_week']-position>=10 else 0
            assert week['details'][song['key']]['position']==position
            assert week['details'][song['key']]['base']==base
            expected[song['owner']]+=base
        for key in week['claims']:
            claim=claims[key]
            ruling=rulings.get('moment:'+key,{})
            verdict=ruling['corrected_verdict'] if ruling.get('verdict')=='OVERTURNED' else claim['verdict']
            if claim['status']=='RESOLVED' and verdict=='AWARDED':
                card=next(c for c in league['cards'] if c['id']==claim['card']['id'])
                assert card==claim['card']
                expected[claim['song']['owner']]+=card['points']
        assert week['scores']==expected,'Weekly scoring differs from chart rows and frozen cards'
        for p,value in expected.items():stats[p]['points']+=value
        for a,b in league['schedule'][i]:
            if 'BYE' in (a,b):continue
            x,y=expected[a],expected[b]
            stats[a]['wins']+=int(x>y);stats[a]['losses']+=int(x<y);stats[a]['ties']+=int(x==y)
            stats[b]['wins']+=int(y>x);stats[b]['losses']+=int(y<x);stats[b]['ties']+=int(x==y)
    for d in disputes:
        if d['status']=='RESOLVED' and d['verdict']=='UPHELD':
            adjustments[d['challenger']]-=3
            adjustments[d['opponent']]+=3
    assert league['adjustments']==adjustments
    for row in league['standings']:
        stats[row['wallet']]['points']+=adjustments[row['wallet']]
        assert all(row[k]==value for k,value in stats[row['wallet']].items())
    expected_order=sorted(stats,key=lambda p:(-stats[p]['points'],-stats[p]['wins'],p))
    assert [r['wallet'] for r in league['standings']]==expected_order

def verify_custom_case(case):
    assert case and case.get('leagueId'),'No live custom-rulebook league recorded'
    league=read(proof['contracts']['League']['address'],'get_league',[case['leagueId']])
    assert league==case['league'] and league['status']=='COMPLETED','Custom league is not finalized and completed'
    assert len(league['players'])==4 and len(league['dates'])==4 and league['entry_fee']=='0'
    assert hashlib.sha256(league['rulebook'].encode()).hexdigest()==league['rulebook_hash']
    charts=[]
    for i in range(4):
        chart=read(proof['contracts']['ChartReader']['address'],'get_read',[league['id'],i])
        assert chart==case['weeks'][i] and chart.get('status')=='RESOLVED'
        assert len(chart['rows'])==100 and len(chart['matches'])==20
        assert hashlib.sha256(json.dumps(chart['rows'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==chart['digest']
        assert chart['songs']==league['weeks'][i]['songs']
        charts.append(chart)
        print('Custom chart',chart['date'],'100 rows and frozen match vector verified.',flush=True)
    ids=read(proof['contracts']['RulebookCourt']['address'],'get_ids',[league['id']])
    assert ids==[d['id'] for d in case['disputes']]
    actual=[]
    for saved in case['disputes']:
        ruling=read(proof['contracts']['RulebookCourt']['address'],'get_dispute',[saved['id']])
        assert ruling==saved and ruling['rulebook']==league['rulebook']
        assert ruling['rule_quote'] in league['rulebook'] and ruling['rulebook_hash']==league['rulebook_hash']
        assert ruling['item']['url']==charts[ruling['week']]['source'] and ruling['item']['digest']==charts[ruling['week']]['digest']
        assert ruling['evidence_quote'] in json.dumps(charts[ruling['week']]['rows'],ensure_ascii=False)
        assert ruling['gen_bond']=='0' and ruling['bond_recipient']==ruling['challenger']
        actual.append(ruling)
    target=next(d for d in actual if d['item']['song']['key']==case['targetKey'])
    assert target['status']=='RESOLVED' and target['verdict']=='OVERTURNED' and target['corrected_position']==0
    assert target['item']['song']['title']=='Fortnight' and target['item']['song']['primary_artist']=='Post Malone'
    generic=charts[target['week']]['matches'][next(i for i,s in enumerate(charts[target['week']]['songs']) if s['key']==case['targetKey'])]
    assert generic==case['genericMatch'] and generic['position']>0 and generic['position']==target['item']['original_verdict']
    row=next(r for r in charts[0]['rows'] if r['position']==generic['position'])
    assert row==case['targetRow']
    import re
    lead=re.split(r'\b(?:Featuring|feat\.|with)\b',row['artist_credit'],maxsplit=1,flags=re.I)[0]
    assert 'Post Malone' in row['artist_credit'] and 'Post Malone' not in lead
    detail=league['weeks'][target['week']]['details'][case['targetKey']]
    assert detail['position']==0 and detail['base']==0
    bond=league['bonds'][target['id']]
    assert bond['status']=='RETURNED' and bond['bond']==3 and bond['challenger']==target['challenger']
    assert league['adjustments'][target['challenger']]==0
    rescore=case['rescore']
    assert rescore['receipt']==proof['transactions']['custom-close-week-0']
    assert rescore['genericPosition']==generic['position'] and rescore['genericPoints']==15
    assert rescore['correctedPosition']==0 and rescore['correctedPoints']==0
    assert rescore['bondStatus']=='RETURNED' and rescore['pointsBond']==3 and rescore['genBondWei']=='0'
    assert case['transactions']=={k:v for k,v in proof['transactions'].items() if k.startswith('custom-')}
    verify_scoring(league,charts,case['moments'],actual)
    print('Live custom OVERTURNED, exact clause/evidence, code rescore and returned three-point bond verified.',flush=True)
    return actual
def main():
    receipts={}
    # Independent immutable receipt reads overlap network latency. Every actual
    # RPC POST shares the 2.6-second gate, keeping starts below 24 per minute.
    items=list(proof['transactions'].items())
    with ThreadPoolExecutor(max_workers=4) as pool:
        for (name,h),receipt in zip(items,pool.map(verify_receipt,[h for _,h in items])):
            receipts[name]=receipt
            if name.startswith('custom-'):assert int(receipt['value'])==0,'Custom case sent an unapproved deposit'
            print(name,h,'FINALIZED_SUCCESS',flush=True)
    for name,h in proof.get('failedTransactions',{}).items():
        failed=c.provider.make_request('eth_getTransactionByHash',[h])['result']
        assert failed['status']=='FINALIZED' and int(failed['value'])==0
        assert not failed.get('triggered_transactions')
        leader=(failed.get('consensus_data',{}).get('leader_receipt') or [{}])[0]
        assert leader.get('execution_result') not in ('SUCCESS','FINISHED_WITH_RETURN') or failed.get('result_name') not in ('AGREE','MAJORITY_AGREE','SUCCESS')
        print(name,h,'FINALIZED_ERROR (retained separately)',flush=True)
        time.sleep(2.6)
    funding=json.loads((ROOT/'deploy/funding.json').read_text())
    assert sum(int(t['wei']) for t in funding['transfers'].values())==42
    for transfer in funding['transfers'].values():
        credit=verify_receipt(transfer['hash'])
        assert credit.get('type')==0 and credit['value_credited'] is True
        assert credit['to_address'].lower()==transfer['wallet'] and int(credit['value'])==int(transfer['wei'])
        time.sleep(2.6)
    adapter=json.loads((ROOT/'deploy/wallet-adapter-check.json').read_text())
    assert int(verify_receipt(adapter['hash'])['value'])==0
    time.sleep(2.6)
    rejected=json.loads((ROOT/'deploy/wallet-adapter-rejection-check.json').read_text())
    rejected_receipt=c.provider.make_request('eth_getTransactionByHash',[rejected['hash']])['result']
    assert rejected_receipt['status']=='FINALIZED' and int(rejected_receipt['value'])==0
    rejection=rejected_receipt['consensus_data']['leader_receipt'][0]
    assert rejection['execution_result']=='ERROR'
    assert base64.b64decode(rejection['result'])==b'\x01[EXPECTED] owner configures once'
    time.sleep(2.6)
    assert sum(map(int,proof['valueCalls'].values()))==42,'Deposit budget differs from approved entries and bonds'
    for name,contract in proof['contracts'].items():
        source=(ROOT/'contracts'/contract['source']).read_text(encoding='utf8')
        assert hashlib.sha256(source.encode()).hexdigest()==contract['sha256'],'Local source hash changed: '+name
        deployed=c.provider.make_request('gen_getContractCode',[contract['address']])['result']
        raw=base64.b64decode(deployed) if isinstance(deployed,str) else b''
        assert hashlib.sha256(raw).hexdigest()==contract['sha256'],'Deployed source differs: '+name
        print('Deployed source verified:',name,flush=True)
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
        assert dispute['bond_claimed'] and dispute['gen_bond']=='1','Dispute bond has not been paid'
        parent=receipts['claim-bond-'+dispute['id']]
        credit=receipts['claim-bond-'+dispute['id']+'-child-0']
        assert credit['hash'] in parent['triggered_transactions']
        assert credit['value_credited'] is True and int(credit['value'])==1
        assert credit['to_address'].lower()==dispute['bond_recipient']
    verify_scoring(league,proof['weeks'],proof['moments'],proof['disputes'])
    custom_disputes=verify_custom_case(proof.get('customRulebookCase'))
    missing=[]
    for verdict in ('AWARDED','NOT_AWARDED'):
        if not any(m['verdict']==verdict for m in proof['moments']):missing.append('Missing live '+verdict+' card')
    for verdict in ('OVERTURNED','UPHELD'):
        if not any(d['status']=='RESOLVED' and d['verdict']==verdict for d in proof['disputes']+custom_disputes):missing.append('Missing live '+verdict+' dispute')
    pool=read(proof['contracts']['SeasonPool']['address'],'get_pool',[league['id']])
    assert pool==proof['pool'] and pool['status']=='SETTLED'
    assert sum(map(int,pool['payouts'].values()))==int(pool['total'])==40
    percentages=[60,30,10] if len(league['standings'])>=4 else [100]
    expected_payouts={p:0 for p in league['players']}
    rank=0
    while rank<len(league['standings']):
        tied=[row for row in league['standings'] if row['points']==league['standings'][rank]['points']]
        share=40*sum(percentages[rank:rank+len(tied)])//(100*len(tied))
        for row in tied:expected_payouts[row['wallet']]=share
        rank+=len(tied)
    expected_payouts[league['creator']]+=40-sum(expected_payouts.values())
    assert {p:int(v) for p,v in pool['payouts'].items()}==expected_payouts
    winner=league['standings'][0]['wallet']
    claim=pool['claims'][winner]
    assert claim['status']=='PAID'
    credit=verify_receipt(claim['child'])
    assert credit['value_credited'] is True and credit['to_address'].lower()==winner and int(credit['value'])==int(claim['amount'])
    time.sleep(2.6)
    assert int(pool['paid'])==40,'All allocated entry wei have not been paid'
    for recipient,amount in pool['payouts'].items():
        if int(amount)==0:continue
        paid=pool['claims'][recipient]
        assert paid['status']=='PAID' and int(paid['amount'])==int(amount)
        transfer=verify_receipt(paid['child'])
        assert transfer['value_credited'] is True and transfer['to_address'].lower()==recipient
        assert int(transfer['value'])==int(amount)
        time.sleep(2.6)
    assert league['status']=='COMPLETED' and proof['sourceCommit']
    print('Six chart reads, deployed sources, final standings and exact native winner credit verified.',flush=True)
    assert not missing,'; '.join(missing)
    print('Complete replay, source, standings, outcomes and native payout verified. No write was sent. Readiness flags may now be enabled.')
if __name__=='__main__':main()
