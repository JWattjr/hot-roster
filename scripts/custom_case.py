"""Resumable real custom-rulebook replay on the five existing contracts.

Every call is zero value. No funding, entry deposit, GEN bond or deployment.
"""
import json
import sys
import time
from datetime import datetime, timezone
from chain import ROOT, client, read, save, transaction, adjudication_label, successful

RULEBOOK="""Custom rulebook: lead credits only.
Featured appearances do not count: the drafted primary artist must be the lead credit on the matching recording.
If the drafted primary artist is listed only after Featuring, feat., or with in the Billboard artist credit, the recording is ineligible for that roster and its correct chart position is 0. Matching the song title and finding the artist anywhere in the credit is insufficient. Joint lead credits before a featuring marker are eligible.
Eligibility is evaluated under this frozen league rulebook. Generic ChartReader matches can be challenged through RulebookCourt; only finalized rulings affect code-calculated scores.
Code awards 25 points at position 1, 15 at 2-10, 8 at 11-40, 3 at 41-100, and 0 when ineligible or absent. Eligible debuts add 5; eligible climbs of ten or more places add 3. Five songs per roster, snake draft, one swap per player and week before the read. Challenger posts a three-point bond. An overturned dispute returns that bond without a point forfeiture. This league plays only for points, with no GEN entry fee or GEN bond."""
DATES=['2024-05-25','2024-06-01','2024-06-08','2024-06-15']
NAMES=['Lead Credit Radio','Feature Check','Primary Rotation','Rulebook FM']
p=json.loads((ROOT/'deploy/proof.json').read_text(encoding='utf8'))
c=client()
case=p.setdefault('customRulebookCase',{'version':1,'name':'Custom rulebook','requestedPlayers':2,'actualPlayers':4,'minimumWeeks':4,'constraint':'Existing League requires 4-8 players and 4-8 Saturday weeks. Used minimum supported size without redeployment.','entryFeeWei':'0','additionalDepositWei':'0','rulebook':RULEBOOK,'dates':DATES,'transactions':{},'weeks':[],'moments':[],'disputes':[]})

def write(label,contract,method,args,index=0):
    label='custom-'+label
    if method in ('read_week','adjudicate'):
        label=adjudication_label(p,label)
    path=ROOT/'deploy/receipts'/(label+'.json')
    if label in p['transactions'] and path.exists():
        prior=json.loads(path.read_text(encoding='utf8'))
        children=prior.get('triggered_transactions') or []
        saved_children=[ROOT/'deploy/receipts'/(label+'-child-'+str(i)+'.json') for i in range(len(children))]
        if prior.get('hash')==p['transactions'][label] and int(prior.get('value',-1))==0 and successful(prior) and all(f.exists() and successful(json.loads(f.read_text(encoding='utf8'))) and json.loads(f.read_text(encoding='utf8'))['hash']==h for f,h in zip(saved_children,children)):
            return prior
    receipt=transaction(client(index),p,label,p['contracts'][contract]['address'],method,args,value=0)
    case['transactions']={k:v for k,v in p['transactions'].items() if k.startswith('custom-')}
    save(p)
    return receipt

def snapshot():
    if not case.get('leagueId'):return
    lid=case['leagueId']
    case['league']=read(c,p['contracts']['League']['address'],'get_league',[lid])
    case['weeks']=[read(c,p['contracts']['ChartReader']['address'],'get_read',[lid,i]) if w['status']!='OPEN' else {} for i,w in enumerate(case['league']['weeks'])]
    ids=read(c,p['contracts']['RulebookCourt']['address'],'get_ids',[lid])
    case['disputes']=[read(c,p['contracts']['RulebookCourt']['address'],'get_dispute',[key]) for key in ids]
    case['recordedAt']=datetime.now(timezone.utc).isoformat()
    save(p)

def create():
    write('create','League','create',['Custom Rulebook · Lead Credits',json.dumps(DATES),4,json.dumps(['TOUR_ANNOUNCED']),RULEBOOK,0,300])
    if not case.get('leagueId'):
        receipt=json.loads((ROOT/'deploy/receipts/custom-create.json').read_text(encoding='utf8'))
        # Locate by immutable creator/rule hash/name instead of racing get_ids[-1].
        import hashlib
        wanted=hashlib.sha256(RULEBOOK.encode()).hexdigest()
        for lid in reversed(read(c,p['contracts']['League']['address'],'get_ids')):
            league=read(c,p['contracts']['League']['address'],'get_league',[lid])
            if league['rulebook_hash']==wanted and league['creator']==p['demoPlayers'][0]['wallet'] and league['name']=='Custom Rulebook · Lead Credits':
                case['leagueId']=lid
                break
        assert case.get('leagueId'),'Finalized custom creation not found'
        save(p)
    for i,name in enumerate(NAMES):write('join-'+str(i),'League','join',[case['leagueId'],name],i)
    snapshot()

def draft():
    lid=case['leagueId']
    write('start-draft','League','start_draft',[lid])
    songs=[(s['title'],s['primary_artist']) for s in p['league']['draft']]
    songs[0]=('Fortnight','Post Malone')
    original=next(i for i,s in enumerate(songs) if s[1]=='Taylor Swift')
    songs[original]=('Espresso','Sabrina Carpenter')
    for i,(title,artist) in enumerate(songs):
        owner=i%4 if i//4%2==0 else 3-i%4
        write('pick-'+str(i),'League','pick',[lid,title,artist],owner)
    league=read(c,p['contracts']['League']['address'],'get_league',[lid])
    case['targetKey']=next(s['key'] for s in league['draft'] if s['title']=='Fortnight' and s['primary_artist']=='Post Malone')
    save(p)
    snapshot()

def chart(i):
    lid=case['leagueId']
    write('lock-week-'+str(i),'League','lock_week',[lid])
    for attempt in range(1,5):
        state=read(c,p['contracts']['ChartReader']['address'],'get_read',[lid,i])
        if state.get('status')=='RESOLVED':return state
        label='read-week-'+str(i)+(('-attempt-'+str(attempt)) if attempt>1 else '')
        try:write(label,'ChartReader','read_week',[lid,i])
        except RuntimeError as error:
            if 'Finalized execution failed:' not in str(error):raise
            adjudication_label(p,'custom-'+label)
        state=read(c,p['contracts']['ChartReader']['address'],'get_read',[lid,i])
        if state.get('status')=='RESOLVED':return state
    snapshot()
    raise RuntimeError('Chart remains retryable after four actual attempts; all results retained')

def dispute():
    lid=case['leagueId']
    chart_state=read(c,p['contracts']['ChartReader']['address'],'get_read',[lid,0])
    index=next(i for i,s in enumerate(chart_state['songs']) if s['key']==case['targetKey'])
    generic=chart_state['matches'][index]
    case['genericMatch']=generic
    case['targetRow']=next((row for row in chart_state['rows'] if row['position']==generic['position']),None)
    save(p)
    assert generic['position']>0,'Generic reader did not credit target; preserve result and choose another honest case'
    write('open-dispute','RulebookCourt','open_dispute',[lid,0,'chart',case['targetKey'],"The frozen lead-credit clause excludes featured-only appearances. The drafted primary artist is Post Malone, while the chart row credits Taylor Swift Featuring Post Malone. Please apply the league eligibility clause to this same chart evidence."],1)
    ids=read(c,p['contracts']['RulebookCourt']['address'],'get_ids',[lid])
    case['disputeId']=ids[0]
    save(p)
    for attempt in range(1,5):
        state=read(c,p['contracts']['RulebookCourt']['address'],'get_dispute',[case['disputeId']])
        if state.get('status')=='RESOLVED':break
        label='ruling'+(('-attempt-'+str(attempt)) if attempt>1 else '')
        try:write(label,'RulebookCourt','adjudicate',[case['disputeId']],1)
        except RuntimeError as error:
            if 'Finalized execution failed:' not in str(error):raise
            adjudication_label(p,'custom-'+label)
    snapshot()
    actual=case['disputes'][0]
    assert actual['status']=='RESOLVED' and actual['verdict']=='OVERTURNED','Actual verdict retained; no override or mock. Create a clearer frozen case if necessary.'

def close(i):
    lid=case['leagueId']
    for owner in range(4):write('ready-'+str(i)+'-'+str(owner),'League','ready',[lid],owner)
    state=read(c,p['contracts']['ChartReader']['address'],'get_read',[lid,i])
    until=state['finalized_at']+300
    while time.time()<until:
        print('Honoring custom dispute window; remaining seconds',max(0,int(until-time.time())),flush=True)
        time.sleep(min(30,max(1,until-time.time())))
    write('close-week-'+str(i),'League','close_week',[lid])
    if i==0:
        snapshot()
        league=case['league']; key=case['targetKey']; ruling=case['disputes'][0]
        detail=league['weeks'][0]['details'][key]; bond=league['bonds'][ruling['id']]
        assert detail['position']==0 and detail['base']==0,'League did not apply finalized correction'
        assert bond['status']=='RETURNED' and bond['bond']==3
        assert league['adjustments'][ruling['challenger']]==0
        case['rescore']={'week':0,'songKey':key,'genericPosition':case['genericMatch']['position'],'genericPoints':15,'correctedPosition':detail['position'],'correctedPoints':detail['base'],'bondStatus':bond['status'],'pointsBond':bond['bond'],'challenger':ruling['challenger'],'genBondWei':ruling['gen_bond'],'receipt':p['transactions']['custom-close-week-0']}
        save(p)

stage=sys.argv[1] if len(sys.argv)>1 else 'all'
if stage=='create':create()
elif stage=='draft':draft()
elif stage=='week':chart(int(sys.argv[2]))
elif stage=='dispute':dispute()
elif stage=='close':close(int(sys.argv[2]))
elif stage=='record':snapshot()
elif stage=='all':
    if not case.get('leagueId'):create()
    if not case.get('targetKey'):draft()
    for i in range(4):
        league=read(c,p['contracts']['League']['address'],'get_league',[case['leagueId']])
        if league['weeks'][i]['status']=='CLOSED':continue
        chart(i)
        if i==0:dispute()
        close(i)
    snapshot()
    assert case['league']['status']=='COMPLETED'
    print('Real custom case completed; generic match, OVERTURNED correction, rescore and returned points bond retained.',flush=True)
else:raise RuntimeError('Unknown custom replay stage')
