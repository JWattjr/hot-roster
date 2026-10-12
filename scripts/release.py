"""Stage-by-stage release. Hashes persist before polling. Never auto-deposit."""
import hashlib
import json
import sys
import time
import subprocess
from datetime import datetime,timedelta
from chain import ROOT,client,transaction,read,save,signer,adjudication_label

NAMES={'League':'league.py','ChartReader':'chart_reader.py','MomentJudge':'moment_judge.py','RulebookCourt':'rulebook_court.py','SeasonPool':'season_pool.py'}
DATES=[(datetime(2024,5,25)+timedelta(weeks=i)).strftime('%Y-%m-%d') for i in range(6)]
SONGS=[('Espresso','Sabrina Carpenter'),('I Had Some Help (feat. Morgan Wallen)','Post Malone'),('Not Like Us','Kendrick Lamar'),('Million Dollar Baby','Tommy Richman'),('A Bar Song (Tipsy)','Shaboozey'),('Beautiful Things','Benson Boone'),('Too Sweet','Hozier'),('Lose Control','Teddy Swims'),('Birds Of A Feather','Billie Eilish'),('Lunch','Billie Eilish'),('Please Please Please','Sabrina Carpenter'),('Fortnight (feat. Post Malone)','Taylor Swift'),('Like That','Future & Metro Boomin'),('I Remember Everything','Zach Bryan'),('Pink Skies','Zach Bryan'),('Good Luck, Babe!','Chappell Roan'),('Saturn','SZA'),('Austin','Dasha'),("We Can't Be Friends (Wait For Your Love)",'Ariana Grande'),('Lovin On Me','Jack Harlow')]
EVIDENCE="https://en.wikipedia.org/w/index.php?title=Short_n%27_Sweet_Tour&oldid=1230356580"

proof=json.loads((ROOT/'deploy/proof.json').read_text())
c=client()
stage=sys.argv[1] if len(sys.argv)>1 else 'record'
def record():
    if proof.get('leagueId'):
        proof['league']=read(c,proof['contracts']['League']['address'],'get_league',[proof['leagueId']])
        proof['weeks']=[read(c,proof['contracts']['ChartReader']['address'],'get_read',[proof['leagueId'],i]) for i in range(6)]
        proof['moments']=[read(c,proof['contracts']['MomentJudge']['address'],'get_claim',[key]) for key in read(c,proof['contracts']['MomentJudge']['address'],'get_ids',[proof['leagueId']])]
        proof['disputes']=[read(c,proof['contracts']['RulebookCourt']['address'],'get_dispute',[key]) for key in read(c,proof['contracts']['RulebookCourt']['address'],'get_ids',[proof['leagueId']])]
        proof['pool']=read(c,proof['contracts']['SeasonPool']['address'],'get_pool',[proof['leagueId']])
        proof['recordedAt']=datetime.now().astimezone().isoformat()
        save(proof)

def write(name,contract,method,args,index=0,value=0):
    if method in ('adjudicate','read_week','verify_claim'):
        assert value==0
        name=adjudication_label(proof,name)
    if value:
        approval=ROOT/'.secrets/deposit-approval.json'
        require_approval=approval.exists() and json.loads(approval.read_text()).get('approvedTotalWei')=='42'
        if not require_approval:
            raise RuntimeError('No approved deposit budget; nothing submitted')
        journal=proof.setdefault('valueCalls',{key:('10' if key.startswith('entry-') else '1') for key in proof['transactions'] if key.startswith(('entry-','open-dispute-')) and '-child-' not in key})
        if name not in journal:
            if sum(map(int,journal.values()))+value>42:
                raise RuntimeError('Approved 42-wei cumulative deposit budget exhausted; nothing submitted')
            journal[name]=str(value)
            save(proof)
    return transaction(client(index),proof,name,proof['contracts'][contract]['address'],method,args,value=value)

def adjudicate(label,contract,key,index=0):
    method='get_claim' if contract=='MomentJudge' else 'get_dispute'
    for _ in range(3):
        current=read(c,proof['contracts'][contract]['address'],method,[key])
        if current.get('status')=='RESOLVED':return
        attempt=current.get('attempt',0) if current.get('status')=='PENDING_FINALITY' else current.get('attempt',0)+1
        name=adjudication_label(proof,label if attempt==1 else label+'-attempt-'+str(attempt))
        try:
            write(name,contract,'adjudicate',[key],index)
        except RuntimeError as error:
            if 'Finalized execution failed:' not in str(error):raise
            adjudication_label(proof,name)
            print('Retained terminal failed judgment; retrying a new zero-value submission:',name,flush=True)
    if read(c,proof['contracts'][contract]['address'],method,[key]).get('status')=='RESOLVED':return
    record()
    raise RuntimeError('Judgment remained retryable after three real attempts; receipts were retained.')

if stage=='deploy':
    for name,file in NAMES.items():
        if name in proof['contracts']:
            continue
        code=(ROOT/'contracts'/file).read_text(encoding='utf8')
        args=[] if name=='League' else [proof['contracts']['League']['address']]
        r=transaction(c,proof,'deploy-'+name,code=code,args=args)
        proof['contracts'][name]={'address':r.get('recipient',r.get('to_address')),'source':file,'sha256':hashlib.sha256(code.encode()).hexdigest()}
        save(proof)
    write('wire-contracts','League','configure',[proof['contracts'][name]['address'] for name in ['ChartReader','MomentJudge','RulebookCourt','SeasonPool']])
    proof['demoPlayers']=[{'wallet':signer(i).address.lower(),'name':name} for i,name in enumerate(['Late Night Radio','The B-Sides','Heavy Rotation','No Skips'])]
    save(proof)
elif stage=='create':
    # Creation fixes fees but sends zero value. Funding is a separate gated step.
    rulebook=(ROOT/'lib/rules.ts').read_text(encoding='utf8').split('`')[1]
    write('create-demo','League','create',['After Hours · Summer 2024',json.dumps(DATES),4,json.dumps(['TOUR_ANNOUNCED','NEW_VERSION','AWARD','PRESS_SPOTLIGHT']),rulebook,10,1800])
    ids=read(c,proof['contracts']['League']['address'],'get_ids')
    proof['leagueId']=ids[-1]
    for i,player in enumerate(proof['demoPlayers']):
        write('join-'+str(i),'League','join',[proof['leagueId'],player['name']],i)
    record()
elif stage=='fund':
    approval=ROOT/'.secrets/deposit-approval.json'
    if not approval.exists() or json.loads(approval.read_text()).get('approvedTotalWei')!='42':
        raise RuntimeError('Owner must approve 40 wei of entry deposits plus two 1-wei dispute bonds. No deposit submitted.')
    for i in range(4):
        write('entry-'+str(i),'SeasonPool','enter',[proof['leagueId']],i,10)
    proof['approvedDepositWei']='42'
    save(proof)
    record()
elif stage=='draft':
    write('start-draft','League','start_draft',[proof['leagueId']])
    for i,(title,artist) in enumerate(SONGS):
        player=i%4 if i//4%2==0 else 3-i%4
        write('pick-'+str(i),'League','pick',[proof['leagueId'],title,artist],player)
    record()
elif stage=='week':
    i=int(sys.argv[2])
    if i==4:
        league=read(c,proof['contracts']['League']['address'],'get_league',[proof['leagueId']])
        if league['weeks'][i]['status']=='OPEN':
            owner=proof['demoPlayers'][3]['wallet']
            slot=next(n for n,s in enumerate(league['rosters'][owner]) if s['primary_artist']=='Taylor Swift')
            incoming='Fortnight (feat. Post Malone) [BLOND:ISH Remix]'
            write('demo-swap-remix-week-4','League','swap',[proof['leagueId'],slot,incoming,'Taylor Swift'],3)
            proof['demoSwap']={'week':i,'wallet':owner,'slot':slot,'incoming':incoming,'primary_artist':'Taylor Swift','officialReleaseURL':'https://music.apple.com/us/song/1747337110','releaseDate':'2024-05-22'}
            save(proof)
    write('lock-week-'+str(i),'League','lock_week',[proof['leagueId']])
    current=read(c,proof['contracts']['ChartReader']['address'],'get_read',[proof['leagueId'],i])
    if current.get('status')!='RESOLVED':
        attempt=current.get('attempt',0) if current.get('status')=='PENDING_FINALITY' else current.get('attempt',0)+1
        label='read-week-'+str(i) if attempt==1 else 'read-week-'+str(i)+'-attempt-'+str(attempt)
        write(label,'ChartReader','read_week',[proof['leagueId'],i])
    chart=read(c,proof['contracts']['ChartReader']['address'],'get_read',[proof['leagueId'],i])
    if chart.get('status')!='RESOLVED':
        record()
        raise RuntimeError('Chart extraction unavailable. Recorded real outcome; do not pretend it scored a season.')
    record()
elif stage=='moments':
    r=read(c,proof['contracts']['League']['address'],'get_league',[proof['leagueId']])
    i=r['current_week']
    if i!=4:
        raise RuntimeError('Tour announced June 20: run moments in chart week ending June 22')
    selected=next(s for s in r['weeks'][i]['songs'] if s['title']=='Espresso')
    for card in ['TOUR_ANNOUNCED','NEW_VERSION']:
        name='moment-'+card
        write(name,'MomentJudge','claim',[proof['leagueId'],i,selected['key'],card,EVIDENCE])
        ids=read(c,proof['contracts']['MomentJudge']['address'],'get_ids',[proof['leagueId']])
        claim_id=next(key for key in ids if read(c,proof['contracts']['MomentJudge']['address'],'get_claim',[key])['card']['id']==card)
        adjudicate('judge-'+card,'MomentJudge',claim_id)
    record()
elif stage=='disputes':
    # Challenge genuine results. Expected outcomes are never injected on-chain.
    r=read(c,proof['contracts']['League']['address'],'get_league',[proof['leagueId']])
    i=r['current_week']
    chart=read(c,proof['contracts']['ChartReader']['address'],'get_read',[proof['leagueId'],i])
    selected=next(s for s in chart['songs'] if s['primary_artist']=='Post Malone')
    challenger=2  # This demo wallet holds the two owner-approved bond wei.
    chart_case=('featured','chart',selected['key'],'The featured Morgan Wallen credit represents the same I Had Some Help recording. Apply the frozen featured-credit rule; uphold if the reader already matched it correctly.')
    remix_index=next((n for n,s in enumerate(chart['songs']) if 'BLOND:ISH Remix' in s['title']),None)
    expected=next((row for row in chart['rows'] if row['title'].casefold()=='fortnight' and 'Taylor Swift' in row['artist_credit']),None)
    if remix_index is not None and expected is not None and chart['matches'][remix_index]['position']!=expected['position']:
        remix=chart['songs'][remix_index]
        chart_case=('remix','chart',remix['key'],'The drafted Fortnight BLOND:ISH remix is an official version of the same underlying Taylor Swift song, with Post Malone featured. The frozen rulebook explicitly counts official remixes and featured credits. The original reader position '+str(chart['matches'][remix_index]['position'])+' differs from the Fortnight row in the same dated chart. Re-read that row and apply the frozen rule; determine the correction independently.')
    cases=[chart_case,('tour','moment',next(m['id'] for m in proof['moments'] if m['card']['id']=='TOUR_ANNOUNCED'),'The source must show an official tour announcement with new dates during this chart week, rather than a rumour or festival lineup. Review the original award under the frozen rulebook.')]
    judgments=[]
    for label,kind,key,argument in cases:
        write('open-dispute-'+label,'RulebookCourt','open_dispute',[proof['leagueId'],i,kind,key,argument],challenger,1)
        ids=read(c,proof['contracts']['RulebookCourt']['address'],'get_ids',[proof['leagueId']])
        dispute_id=next(d for d in ids if read(c,proof['contracts']['RulebookCourt']['address'],'get_dispute',[d])['item']['kind']==kind)
        judgments.append((label,dispute_id))
    # Register both cases while their windows are open before a slow judgment.
    for label,dispute_id in judgments:
        adjudicate('rule-dispute-'+label,'RulebookCourt',dispute_id,challenger)
    record()
elif stage=='bonds':
    for ruling in proof.get('disputes',[]):
        recipient=ruling['bond_recipient'] if ruling['status']=='RESOLVED' else ruling['challenger']
        idx=next(i for i,p in enumerate(proof['demoPlayers']) if p['wallet']==recipient)
        receipt=write('claim-bond-'+ruling['id'],'RulebookCourt','claim_bond',[ruling['id']],idx)
        child=receipt['triggered_transactions'][0]
        credit=json.loads((ROOT/'deploy/receipts'/('claim-bond-'+ruling['id']+'-child-0.json')).read_text())
        assert credit.get('value_credited') is True and credit['to_address'].lower()==recipient and int(credit['value'])==1
    record()
elif stage=='close':
    i=int(sys.argv[2])
    for p in range(4):
        write('ready-'+str(i)+'-'+str(p),'League','ready',[proof['leagueId']],p)
    r=read(c,proof['contracts']['League']['address'],'get_league',[proof['leagueId']])
    chart=read(c,proof['contracts']['ChartReader']['address'],'get_read',[proof['leagueId'],i])
    deadlines=[chart.get('finalized_at',0)+r['dispute_seconds']]
    for claim_id in r['weeks'][i]['claims']:
        claim=read(c,proof['contracts']['MomentJudge']['address'],'get_claim',[claim_id])
        if claim.get('status')=='RESOLVED':
            deadlines.append(claim['finalized_at']+r['dispute_seconds'])
    while time.time()<max(deadlines):
        remaining=max(deadlines)-time.time()
        print('Frozen dispute window:',int(remaining),'seconds remaining before week',i+1,'can close',flush=True)
        time.sleep(min(60,remaining+1))
    write('close-week-'+str(i),'League','close_week',[proof['leagueId']])
    record()
elif stage=='settle':
    write('settle-pool','SeasonPool','settle',[proof['leagueId']])
    record()
    winner=proof['league']['standings'][0]['wallet']
    idx=next(i for i,p in enumerate(proof['demoPlayers']) if p['wallet']==winner)
    write('claim-winner','SeasonPool','claim',[proof['leagueId'],1],idx)
    receipt=json.loads((ROOT/'deploy/receipts/claim-winner.json').read_text())
    child=receipt['triggered_transactions'][0]
    write('verify-winner-credit','SeasonPool','verify_claim',[proof['leagueId'],winner,1,proof['transactions']['claim-winner'],child],idx)
    record()
    for recipient,amount in proof['pool']['payouts'].items():
        if recipient==winner or int(amount)==0:continue
        idx=next(i for i,p in enumerate(proof['demoPlayers']) if p['wallet']==recipient)
        label='claim-player-'+str(idx)
        receipt=write(label,'SeasonPool','claim',[proof['leagueId'],1],idx)
        child=receipt['triggered_transactions'][0]
        write('verify-player-'+str(idx)+'-credit','SeasonPool','verify_claim',[proof['leagueId'],recipient,1,proof['transactions'][label],child],idx)
    record()
else:
    record()
