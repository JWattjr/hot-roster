# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""Optional GEN pool, deterministic ties, deadline refunds and receipt-verified pulls."""
import json
import re
from datetime import datetime
from genlayer import *

RPC='https://studio.genlayer.com/api'

def now():
    return int(datetime.fromisoformat(str(gl.message_raw['datetime']).replace('Z','+00:00')).timestamp())

def require(ok,message):
    if not ok:
        raise gl.vm.UserError('[EXPECTED] '+message)

def allocation(standings,total,creator):
    require(len(standings)>0,'no standings')
    weights=[60,30,10] if len(standings)>=4 else [100]
    payouts={s['wallet']:0 for s in standings}
    i=0
    while i<len(standings):
        group=[standings[i]]
        j=i+1
        while j<len(standings) and standings[j]['points']==standings[i]['points']:
            group.append(standings[j])
            j+=1
        weight=sum(weights[i:j])
        each=(total*weight//100)//len(group)
        for s in group:
            payouts[s['wallet']]=each
        i=j
    payouts[creator]=payouts.get(creator,0)+total-sum(payouts.values())
    require(sum(payouts.values())==total,'allocation must conserve wei')
    return payouts

def receipt(hash_value):
    require(re.fullmatch(r'0x[0-9a-fA-F]{64}',hash_value) is not None,'transaction hash required')
    response=gl.nondet.web.post(RPC,body=json.dumps({'jsonrpc':'2.0','id':1,'method':'eth_getTransactionByHash','params':[hash_value]}).encode(),headers={'Content-Type':'application/json','User-Agent':'Mozilla/5.0 HotRoster/1.0'})
    require(response.status==200,'receipt RPC unavailable')
    result=json.loads(response.body.decode('utf8'))
    require(not result.get('error') and result.get('result') is not None,'receipt unavailable')
    return result['result']

@gl.evm.contract_interface
class Recipient:
    class View:
        pass
    class Write:
        pass

class SeasonPool(gl.Contract):
    league: Address
    records: TreeMap[str,str]

    def __init__(self,league: str):
        require(int(gl.message.chain_id)==61999,'StudioNet only')
        self.league=Address(league)

    @gl.public.write.payable
    def enter(self,league_id: str) -> None:
        league=json.loads(gl.get_contract_at(self.league).view().get_league(league_id))
        wallet=str(gl.message.sender_address).lower()
        require(league['status']=='JOINING' and now()<league['join_deadline'] and wallet in league['players'],'join before entry cutoff')
        value=int(gl.message.value)
        require(value==int(league['entry_fee']) and value>0,'pay the exact frozen entry fee')
        r=json.loads(self.records.get(league_id,'{}'))
        if not r:
            r={'league_id':league_id,'status':'OPEN','creator':league['creator'],'deadline':league['settle_deadline'],'rulebook_hash':league['rulebook_hash'],'entry_fee':league['entry_fee'],'entries':{},'total':'0','payouts':{},'claims':{},'paid':'0'}
        require(r['status']=='OPEN' and wallet not in r['entries'],'one entry per player')
        r['entries'][wallet]=str(value)
        r['total']=str(int(r['total'])+value)
        self.records[league_id]=json.dumps(r)

    @gl.public.write
    def settle(self,league_id: str) -> None:
        require(league_id in self.records,'no funded pool')
        r=json.loads(self.records[league_id])
        require(r['status']=='OPEN','pool already settled')
        league=json.loads(gl.get_contract_at(self.league).view().get_league(league_id))
        require(league['rulebook_hash']==r['rulebook_hash'],'rulebook differs from frozen entry')
        if league['status']=='COMPLETED' and now()<r['deadline']:
            require(all(p in r['entries'] for p in league['players']),'all players must be funded')
            r['payouts']= {p:str(v) for p,v in allocation(league['standings'],int(r['total']),r['creator']).items()}
            r['status']='SETTLING'
        else:
            require(now()>=r['deadline'],'wait for completed season or refund deadline')
            r['payouts']=r['entries'].copy()
            r['status']='REFUNDING'
        self.records[league_id]=json.dumps(r)
        gl.get_contract_at(gl.message.contract_address).emit(on='finalized').finalize_pool(league_id)

    @gl.public.write
    def finalize_pool(self,league_id: str) -> None:
        require(gl.message.sender_address==gl.message.contract_address,'self finality callback only')
        r=json.loads(self.records[league_id])
        if r['status'] in ('SETTLING','REFUNDING'):
            r['status']='SETTLED' if r['status']=='SETTLING' else 'REFUNDED'
            r['finalized_at']=now()
            self.records[league_id]=json.dumps(r)

    @gl.public.write
    def claim(self,league_id: str,attempt: int) -> None:
        r=json.loads(self.records[league_id])
        wallet=str(gl.message.sender_address).lower()
        require(r['status'] in ('SETTLED','REFUNDED'),'pool not final')
        amount=int(r['payouts'].get(wallet,'0'))
        previous=r['claims'].get(wallet)
        require(amount>0 and (previous is None or previous['status']=='FAILED'),'no unclaimed payout, or transfer still pending')
        require(attempt==(previous['attempt']+1 if previous else 1),'use next attempt number')
        require(int(self.balance)>=amount,'wait for native funds to return')
        r['claims'][wallet]={'status':'PENDING','attempt':attempt,'amount':str(amount),'requested_at':now(),'verification_deadline':now()+3600,'parent':'','child':''}
        self.records[league_id]=json.dumps(r)
        Recipient(Address(wallet)).emit_transfer(value=u256(amount),on='finalized')

    @gl.public.write
    def verify_claim(self,league_id: str,wallet: str,attempt: int,parent_hash: str,child_hash: str) -> None:
        r=json.loads(self.records[league_id])
        wallet=wallet.lower()
        claim=r['claims'].get(wallet)
        require(claim is not None and claim['attempt']==attempt and claim['status']=='PENDING','no matching pending claim')
        contract=str(gl.message.contract_address).lower()
        def verify():
            parent,child=receipt(parent_hash),receipt(child_hash)
            parent_final=parent.get('status_name',parent.get('status'))=='FINALIZED'
            child_final=child.get('status_name',child.get('status'))=='FINALIZED'
            require(parent_final and child_final,'transfer not final; retry verification')
            require(str(parent.get('from_address','')).lower()==wallet and str(parent.get('to_address','')).lower()==contract,'claim parent origin mismatch')
            require(child_hash in parent.get('triggered_transactions',[]) and child.get('triggered_by')==parent_hash,'unrelated native child')
            require(str(child.get('from_address','')).lower()==contract and str(child.get('to_address','')).lower()==wallet and int(child.get('value',0))==int(claim['amount']),'native transfer fields mismatch')
            # Bind attempt to original claim calldata, not just amount/wallet.
            data=parent.get('data',{})
            decoded=data.get('calldata',{}) if isinstance(data,dict) else {}
            # Receipt shape varies; decode original serialized calldata when needed.
            if not isinstance(decoded,dict) or 'method' not in decoded:
                import base64
                from genlayer.py import calldata
                encoded=parent.get('data',{}).get('calldata') if isinstance(parent.get('data'),dict) else None
                require(isinstance(encoded,str),'parent calldata unavailable')
                decoded=calldata.decode(base64.b64decode(encoded))
            require(decoded.get('method')=='claim' and list(decoded.get('args',[]))==[league_id,attempt],'parent is not this claim attempt')
            return {'paid':child.get('value_credited') is True,'parent':parent_hash,'child':child_hash}
        outcome=gl.eq_principle.strict_eq(verify)
        claim['status']='PAID' if outcome['paid'] else 'FAILED'
        claim['parent'],claim['child']=parent_hash,child_hash
        if outcome['paid']:
            r['paid']=str(int(r['paid'])+int(claim['amount']))
        self.records[league_id]=json.dumps(r)

    @gl.public.view
    def get_pool(self,league_id: str) -> str:
        return self.records.get(league_id,'{}')
