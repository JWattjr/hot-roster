# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""Deterministic rosters, schedule, scoring, bonds and season finality."""
import json
import hashlib
import re
from datetime import datetime, timezone
from genlayer import *

CATALOG = {
    'TOUR_ANNOUNCED': {'id':'TOUR_ANNOUNCED','definition':'The primary artist officially announced new tour dates during the chart week. Rumours, old tour dates and festival lineups do not count.','points':6,'domains':['billboard.com','rollingstone.com','sabrinacarpenter.com','en.wikipedia.org']},
    'NEW_VERSION': {'id':'NEW_VERSION','definition':'An official remix, feature or deluxe version of the drafted song was actually released during the chart week. Announcements of future releases and versions of other songs do not count.','points':5,'domains':['billboard.com','rollingstone.com','en.wikipedia.org']},
    'AWARD': {'id':'AWARD','definition':'The primary artist won a Grammy, Billboard Music Award, BRIT Award, MTV Video Music Award or BET Award during the chart week. A nomination is not a win.','points':8,'domains':['billboard.com','grammy.com','brits.co.uk','mtv.com','bet.com','en.wikipedia.org']},
    'PRESS_SPOTLIGHT': {'id':'PRESS_SPOTLIGHT','definition':'The drafted song is the subject of a dedicated editorial article published during the chart week on Billboard, Rolling Stone or Pitchfork. Chart lists, list mentions and artist articles about another subject do not count.','points':3,'domains':['billboard.com','rollingstone.com','pitchfork.com']}
}

def now():
    return int(datetime.fromisoformat(str(gl.message_raw['datetime']).replace('Z','+00:00')).timestamp())

def require(ok, message):
    if not ok:
        raise gl.vm.UserError('[EXPECTED] ' + message)

def song(title, artist):
    title, artist = title.strip(), artist.strip()
    require(0 < len(title) <= 120 and 0 < len(artist) <= 100, 'song title and primary artist required')
    key = re.sub(r'\s+', ' ', title.casefold()) + '|' + re.sub(r'\s+', ' ', artist.casefold())
    return {'key':key,'title':title,'primary_artist':artist}

def points(position, last, debut):
    require(type(position) is int and 0 <= position <= 100, 'invalid chart position')
    base = 25 if position == 1 else 15 if 2 <= position <= 10 else 8 if 11 <= position <= 40 else 3 if 41 <= position <= 100 else 0
    return base + (5 if position and debut else 0) + (3 if position and last > 0 and last - position >= 10 else 0)

def schedule(players, count):
    ring = players[:]
    if len(ring) % 2:
        ring.append('BYE')
    rounds = []
    for _ in range(len(ring)-1):
        rounds.append([[ring[i],ring[-1-i]] for i in range(len(ring)//2)])
        ring = [ring[0],ring[-1]] + ring[1:-1]
    return [rounds[i % len(rounds)] for i in range(count)]

class League(gl.Contract):
    owner: Address
    records: TreeMap[str,str]
    ids: DynArray[str]
    reader: Address
    judge: Address
    court: Address
    pool: Address
    configured: bool

    def __init__(self):
        self.owner = gl.message.sender_address
        self.configured = False

    def _get(self, league_id):
        require(league_id in self.records, 'league not found')
        return json.loads(self.records[league_id])

    def _save(self, r):
        self.records[r['id']] = json.dumps(r, sort_keys=True, separators=(',',':'))

    def _member(self, r):
        wallet = str(gl.message.sender_address).lower()
        require(wallet in r['players'], 'join this league first')
        return wallet

    @gl.public.write
    def configure(self, reader: str, judge: str, court: str, pool: str) -> None:
        require(gl.message.sender_address == self.owner and not self.configured, 'owner configures once')
        addresses = [Address(a) for a in [reader,judge,court,pool]]
        require(len(set(str(a) for a in addresses)) == 4, 'distinct contracts required')
        self.reader,self.judge,self.court,self.pool = addresses
        self.configured = True

    @gl.public.write
    def create(self, name: str, dates_json: str, max_players: int, cards_json: str, rulebook: str, entry_fee: int, dispute_seconds: int) -> str:
        require(self.configured, 'deployment wiring incomplete')
        dates, card_ids = json.loads(dates_json),json.loads(cards_json)
        require(0 < len(name.strip()) <= 80 and 4 <= max_players <= 8, 'name and 4–8 player capacity required')
        require(isinstance(dates,list) and 4 <= len(dates) <= 8 and len(set(dates)) == len(dates), '4–8 distinct Saturday weeks required')
        stamps = []
        for date in dates:
            require(re.fullmatch(r'\d{4}-\d{2}-\d{2}', date) is not None, 'ISO chart date required')
            parsed = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
            require(parsed.weekday() == 5, 'chart dates are Saturdays')
            stamps.append(int(parsed.timestamp()))
        require(stamps == sorted(stamps) and all(stamps[i]-stamps[i-1] == 604800 for i in range(1,len(stamps))), 'consecutive chart weeks required')
        require(isinstance(card_ids,list) and len(set(card_ids)) == len(card_ids) and all(c in CATALOG for c in card_ids), 'choose catalog cards')
        require(80 <= len(rulebook) <= 12000 and 0 <= entry_fee <= 100 * 10**18 and 60 <= dispute_seconds <= 604800, 'invalid rules, fee or dispute window')
        wallet = str(gl.message.sender_address).lower()
        league_id = 'league-' + str(len(self.ids)+1)
        historical = stamps[-1]+86400 < now()
        r = {'id':league_id,'name':name.strip(),'creator':wallet,'dates':dates,'chart_stamps':stamps,'max_players':max_players,'roster_size':5,'cards':[CATALOG[c] for c in card_ids],'rulebook':rulebook,'rulebook_hash':hashlib.sha256(rulebook.encode()).hexdigest(),'entry_fee':str(entry_fee),'dispute_seconds':dispute_seconds,'replay':historical,'created':now(),'join_deadline':now()+86400,'draft_deadline':now()+172800,'settle_deadline':max(now()+7*86400,stamps[-1]+14*86400),'status':'JOINING','players':[],'names':{},'rosters':{},'draft':[],'schedule':[],'weeks':[{'status':'OPEN','songs':[],'scores':{},'details':{},'ready':[],'swaps':{},'claims':[],'disputes':[],'locked_at':0,'read_deadline':0,'closed_at':0} for _ in dates],'current_week':0,'bonds':{},'adjustments':{},'standings':[]}
        self._save(r)
        self.ids.append(league_id)
        return league_id

    @gl.public.write
    def join(self, league_id: str, display_name: str) -> None:
        r = self._get(league_id)
        wallet = str(gl.message.sender_address).lower()
        require(r['status'] == 'JOINING' and now() < r['join_deadline'], 'joining closed')
        require(wallet not in r['players'] and len(r['players']) < r['max_players'], 'already joined or league full')
        require(0 < len(display_name.strip()) <= 40, 'player name required')
        r['players'].append(wallet)
        r['names'][wallet] = display_name.strip()
        r['rosters'][wallet] = []
        r['adjustments'][wallet] = 0
        self._save(r)

    @gl.public.write
    def start_draft(self, league_id: str) -> None:
        r = self._get(league_id)
        require(str(gl.message.sender_address).lower() == r['creator'], 'creator starts draft')
        require(r['status'] == 'JOINING' and 4 <= len(r['players']) <= 8 and now() < r['draft_deadline'], 'need 4–8 players before draft deadline')
        if int(r['entry_fee']):
            funded = json.loads(gl.get_contract_at(self.pool).view().get_pool(league_id))
            require(all(p in funded.get('entries',{}) for p in r['players']), 'every player must pay entry fee')
        r['status'] = 'DRAFTING'
        r['schedule'] = schedule(r['players'],len(r['dates']))
        self._save(r)

    @gl.public.write
    def pick(self, league_id: str, title: str, primary_artist: str) -> None:
        r = self._get(league_id)
        wallet = self._member(r)
        require(r['status'] == 'DRAFTING' and now() < r['draft_deadline'], 'draft closed')
        n, i = len(r['players']),len(r['draft'])
        turn = r['players'][i % n if (i//n)%2 == 0 else n-1-i%n]
        require(wallet == turn, 'wait for your snake-draft turn')
        selected = song(title,primary_artist)
        require(all(s['key'] != selected['key'] for s in r['draft']), 'song already drafted')
        r['draft'].append({**selected,'owner':wallet})
        r['rosters'][wallet].append(selected)
        if len(r['draft']) == n*5:
            r['status'] = 'ACTIVE'
        self._save(r)

    @gl.public.write
    def swap(self, league_id: str, slot: int, title: str, primary_artist: str) -> None:
        r = self._get(league_id)
        wallet = self._member(r)
        week = r['weeks'][r['current_week']]
        require(r['status'] == 'ACTIVE' and week['status'] == 'OPEN', 'swap before the chart is locked')
        require(wallet not in week['swaps'] and 0 <= slot < 5, 'one swap per player per week')
        if not r['replay']:
            require(now() < r['chart_stamps'][r['current_week']], 'swap before chart Saturday')
        selected = song(title,primary_artist)
        require(all(s['key'] != selected['key'] for roster in r['rosters'].values() for s in roster), 'choose an undrafted song')
        week['swaps'][wallet] = {'out':r['rosters'][wallet][slot],'in':selected}
        r['rosters'][wallet][slot] = selected
        self._save(r)

    @gl.public.write
    def lock_week(self, league_id: str) -> None:
        r = self._get(league_id)
        self._member(r)
        require(r['status'] == 'ACTIVE', 'season not active')
        i = r['current_week']
        week = r['weeks'][i]
        require(week['status'] == 'OPEN' and now() >= r['chart_stamps'][i], 'chart week is not ready')
        week.update({'status':'LOCKED','songs':[{**s,'owner':p} for p in r['players'] for s in r['rosters'][p]],'locked_at':now(),'read_deadline':min(now()+86400,r['settle_deadline']),'claim_deadline':min(now()+86400,r['settle_deadline'])})
        self._save(r)

    @gl.public.write
    def register_claim(self, league_id: str, week: int, claim_id: str) -> None:
        require(gl.message.sender_address == self.judge, 'MomentJudge only')
        r = self._get(league_id)
        w = r['weeks'][week]
        require(r['status'] == 'ACTIVE' and week == r['current_week'] and w['status'] == 'LOCKED' and now() < w['claim_deadline'], 'claims closed')
        require(claim_id not in w['claims'] and len(w['claims']) < 24, 'claim already registered or capacity reached')
        w['claims'].append(claim_id)
        w['ready'] = []
        self._save(r)

    @gl.public.write
    def register_dispute(self, league_id: str, week: int, dispute_id: str, challenger: str, opponent: str, bond: int) -> None:
        require(gl.message.sender_address == self.court, 'RulebookCourt only')
        r = self._get(league_id)
        w = r['weeks'][week]
        require(r['status'] == 'ACTIVE' and week == r['current_week'] and w['status'] == 'LOCKED', 'week closed')
        require(dispute_id not in w['disputes'] and challenger in r['players'] and opponent in r['players'] and challenger != opponent and bond == 3, 'invalid points bond')
        require(sum(v['bond'] for v in r['bonds'].values() if v['challenger']==challenger and v['status']=='OPEN') + 3 <= 6, 'at most two open points bonds')
        r['bonds'][dispute_id] = {'challenger':challenger,'opponent':opponent,'bond':3,'status':'OPEN'}
        w['disputes'].append(dispute_id)
        w['ready'] = []
        self._save(r)

    @gl.public.write
    def ready(self, league_id: str) -> None:
        r = self._get(league_id)
        wallet = self._member(r)
        w = r['weeks'][r['current_week']]
        require(r['status'] == 'ACTIVE' and w['status'] == 'LOCKED', 'lock chart week first')
        if wallet not in w['ready']:
            w['ready'].append(wallet)
        self._save(r)

    def _score(self, r, i):
        w = r['weeks'][i]
        chart = json.loads(gl.get_contract_at(self.reader).view().get_read(r['id'],i))
        chart_ok = chart.get('status') == 'RESOLVED'
        require(chart_ok or now() >= w['read_deadline'], 'chart read retryable until deadline')
        scores = {p:0 for p in r['players']}
        details = {s['key']:{'song':s,'position':0,'last_week':0,'debut':False,'base':0,'moments':0,'reason':'Chart unavailable at deadline'} for s in w['songs']}
        if chart_ok:
            require(chart['songs'] == w['songs'], 'chart roster differs from frozen week')
            for s, match in zip(w['songs'],chart['matches']):
                position = match['position']
                item = 'chart:' + r['id'] + ':' + str(i) + ':' + s['key']
                ruling = json.loads(gl.get_contract_at(self.court).view().get_item_ruling(item))
                if ruling.get('status') == 'RESOLVED' and ruling['verdict']=='OVERTURNED':
                    position = ruling['corrected_position']
                row = next((row for row in chart['rows'] if row['position']==position), None)
                last, debut = (row['last_week'],row['debut']) if row else (0,False)
                value = points(position,last,debut)
                details[s['key']].update({'position':position,'last_week':last,'debut':debut,'base':value,'reason':match['reason']})
                scores[s['owner']] += value
        for claim_id in w['claims']:
            claim = json.loads(gl.get_contract_at(self.judge).view().get_claim(claim_id))
            require(claim.get('status') == 'RESOLVED' or now() >= w['claim_deadline'], 'moment judgment still retryable')
            if claim.get('status') != 'RESOLVED':
                continue
            verdict = claim['verdict']
            ruling = json.loads(gl.get_contract_at(self.court).view().get_item_ruling('moment:'+claim_id))
            if ruling.get('status') == 'RESOLVED' and ruling['verdict'] == 'OVERTURNED':
                verdict = ruling['corrected_verdict']
            if verdict == 'AWARDED':
                owner = next(s['owner'] for s in w['songs'] if s['key']==claim['song']['key'])
                scores[owner] += claim['card']['points']
                details[claim['song']['key']]['moments'] += claim['card']['points']
        for dispute_id in w['disputes']:
            ruling = json.loads(gl.get_contract_at(self.court).view().get_dispute(dispute_id))
            require(ruling.get('status') == 'RESOLVED' or now() >= ruling['deadline'], 'dispute not resolved')
            bond = r['bonds'][dispute_id]
            if bond['status'] == 'OPEN':
                if ruling.get('verdict') == 'UPHELD' and ruling.get('status') == 'RESOLVED':
                    r['adjustments'][bond['challenger']] -= bond['bond']
                    r['adjustments'][bond['opponent']] += bond['bond']
                bond['status'] = 'RETURNED' if ruling.get('verdict') != 'UPHELD' else 'FORFEITED'
        w['scores'],w['details'] = scores,details

    @gl.public.write
    def close_week(self, league_id: str) -> None:
        r = self._get(league_id)
        require(r['status'] == 'ACTIVE', 'season not active')
        i, w = r['current_week'],r['weeks'][r['current_week']]
        require(w['status']=='LOCKED', 'lock chart first')
        require(len(w['ready'])==len(r['players']) or now() >= w['claim_deadline'], 'all players ready or claim deadline required')
        chart = json.loads(gl.get_contract_at(self.reader).view().get_read(league_id,i))
        require(chart.get('status') != 'RESOLVED' or now() >= chart['finalized_at']+r['dispute_seconds'], 'chart dispute window still open')
        for claim_id in w['claims']:
            claim = json.loads(gl.get_contract_at(self.judge).view().get_claim(claim_id))
            require(claim.get('status') != 'RESOLVED' or now() >= claim['finalized_at']+r['dispute_seconds'], 'moment dispute window still open')
        self._score(r,i)
        w['status'],w['closed_at'] = 'CLOSED',now()
        if i+1 == len(r['dates']):
            r['status'] = 'CLOSING'
        else:
            r['current_week'] += 1
        self._standings(r)
        self._save(r)
        if r['status']=='CLOSING':
            gl.get_contract_at(gl.message.contract_address).emit(on='finalized').finalize_season(league_id)

    def _standings(self, r):
        stats = {p:{'wallet':p,'name':r['names'][p],'points':r['adjustments'][p],'wins':0,'losses':0,'ties':0} for p in r['players']}
        for i,w in enumerate(r['weeks']):
            if w['status'] != 'CLOSED':
                continue
            for p in r['players']:
                stats[p]['points'] += w['scores'][p]
            for a,b in r['schedule'][i]:
                if 'BYE' in (a,b):
                    continue
                x,y = w['scores'][a],w['scores'][b]
                stats[a]['wins'] += int(x>y)
                stats[b]['wins'] += int(y>x)
                stats[a]['losses'] += int(x<y)
                stats[b]['losses'] += int(y<x)
                stats[a]['ties'] += int(x==y)
                stats[b]['ties'] += int(x==y)
        r['standings'] = sorted(stats.values(),key=lambda s:(-s['points'],-s['wins'],s['wallet']))

    @gl.public.write
    def finalize_season(self, league_id: str) -> None:
        require(gl.message.sender_address == gl.message.contract_address, 'self finality callback only')
        r = self._get(league_id)
        if r['status']=='CLOSING':
            r['status'],r['finalized_at'] = 'COMPLETED',now()
            self._save(r)

    @gl.public.write
    def cancel_expired(self, league_id: str) -> None:
        r = self._get(league_id)
        require(r['status'] != 'COMPLETED' and now() >= r['settle_deadline'], 'season settlement deadline not reached')
        r['status'] = 'CANCELLED'
        self._save(r)

    @gl.public.view
    def get_league(self, league_id: str) -> str:
        return json.dumps(self._get(league_id))

    @gl.public.view
    def get_ids(self) -> list[str]:
        return list(self.ids)

    @gl.public.view
    def get_config(self) -> dict:
        return {'configured':self.configured,'reader':str(self.reader),'judge':str(self.judge),'court':str(self.court),'pool':str(self.pool)}

    @gl.public.view
    def get_catalog(self) -> str:
        return json.dumps(list(CATALOG.values()))
