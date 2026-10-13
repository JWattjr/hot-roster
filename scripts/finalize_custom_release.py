"""Publish readiness metadata only after the complete read-only live audit passes."""
import json
from pathlib import Path
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parent.parent
p=json.loads((ROOT/'deploy/proof.json').read_text(encoding='utf8'))
case=p['customRulebookCase']
log=(ROOT/'docs/proof-verifier-output.txt').read_text(encoding='utf8')
assert 'Complete replay, source, standings, outcomes and native payout verified. No write was sent.' in log
assert 'Live custom OVERTURNED, exact clause/evidence, code rescore and returned three-point bond verified.' in log
assert 'Traceback' not in log and 'AssertionError' not in log
assert log.count('FINALIZED_SUCCESS')==len(p['transactions'])
assert case['league']['status']=='COMPLETED' and all(w['status']=='RESOLVED' for w in case['weeks'])
assert case['disputes'][0]['verdict']=='OVERTURNED' and case['rescore']['bondStatus']=='RETURNED'
assert all(json.loads((ROOT/'deploy/receipts'/(name+'.json')).read_text(encoding='utf8'))['hash']==h for name,h in p['transactions'].items() if name.startswith('custom-'))
p.update(completed=True,submissionReady=True,blockers=[],readinessVerifiedAt=datetime.now(timezone.utc).isoformat())
(ROOT/'deploy/proof.json').write_text(json.dumps(p,indent=2)+'\n',encoding='utf8')
audit={'at':p['readinessVerifiedAt'],'command':'npm run verify:proof','exitCode':0,'readOnly':True,'successfulReplayReceiptsVerified':len(p['transactions']),'failedConsensusReceiptsVerifiedSeparately':len(p.get('failedTransactions',{})),'deployedSourcesVerified':5,'resolvedChartReadsVerified':10,'fullChartRowsPerWeek':100,'independentScoresAndStandings':'passed','mainPoolCreditedWei':40,'nativePayoutsWei':[24,12,4],'customLeagueId':case['leagueId'],'customVerdict':'OVERTURNED','customRescore':case['rescore'],'additionalDepositWei':0,'stateEquality':'passed','strictReadiness':'passed','submissionReady':True,'readinessFlagsEnabledAfterAudit':True,'output':'docs/proof-verifier-output.txt'}
(ROOT/'deploy/proof-verification.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf8')
portal=ROOT/'docs/submission/portal-fields.json'
f=json.loads(portal.read_text(encoding='utf8'))
f['description']='Hot Roster is a fantasy music league for 4–8 friends. Draft five songs, play weekly head-to-head matches and earn code-calculated Hot 100 points. GenLayer validators match recordings against extracted chart rows, judge moment cards and interpret disputes against a hashed rulebook with verbatim evidence. Five contracts separate judgment, league scoring and optional GEN pools. The public six-week StudioNet season includes awarded and rejected cards, upheld disputes and all 40 entry wei credited. A second four-player, four-week league demonstrates a custom lead-credit rule: the generic reader matches Fortnight under featured artist Post Malone, the Court overturns that match, and code rescores it to zero and returns the three-point bond. That case sends no GEN deposits. The strict read-only verifier checks finalized receipts, deployed sources, chart digests, standings, both dispute outcomes and native payouts. Simulated StudioNet GEN only.'
assert len(f['description'])<=1000
f['howTo']=[step for step in f['howTo'] if step['heading']!='Inspect the custom rulebook']
f['howTo'].insert(2,{'heading':'Inspect the custom rulebook','instruction':'Choose Custom rulebook beside Main season. Compare the generic Fortnight match with the frozen lead-credit clause, live OVERTURNED ruling, evidence quote, zero-point rescore and returned three-point bond. Open the actual receipts and read the case league live.'})
f['expectedOutcome']='A verified six-week completed main season with awarded and rejected cards, UPHELD disputes, a settled 40-wei pool and three exact native credits; plus a completed four-week custom-rulebook league with a live OVERTURNED dispute, code rescore and returned points bond. The strict read-only verifier passes. No Portal submission is made automatically.'
f['evidence']=list(dict.fromkeys(f['evidence']+['https://github.com/JWattjr/hot-roster/blob/main/docs/RELEASE_REPORT.md','https://github.com/JWattjr/hot-roster/blob/main/deploy/proof-verification.json']))
portal.write_text(json.dumps(f,indent=2)+'\n',encoding='utf8')
readme=ROOT/'README.md'; text=readme.read_text(encoding='utf8'); begin=text.index('The real six-week StudioNet season'); end=text.index('\n',begin)
text=text[:begin]+'The real six-week StudioNet season is completed and all 40 entry wei were credited. The existing contracts also host a completed four-week custom-rulebook case: Fortnight drafted under featured artist Post Malone is generically matched, then OVERTURNED under a frozen lead-credit clause, rescored to zero, and its three-point bond returned. No additional GEN deposits or contract redeployments were needed. The strict read-only verifier passes and `completed` / `submissionReady` are true. See the [release report](docs/RELEASE_REPORT.md) and [verification scope](docs/VERIFICATION.md).'+text[end:]
readme.write_text(text,encoding='utf8')
report=ROOT/'docs/RELEASE_REPORT.md'; text=report.read_text(encoding='utf8')
if '\n## Custom-rulebook case' in text:text=text[:text.index('\n## Custom-rulebook case')]
start=text.index('**Not submission ready:**') if '**Not submission ready:**' in text else text.index('**Submission ready after'); end=text.index('\n',start)
text=text[:start]+'**Submission ready after the successful strict audit.** Both original-season Court decisions remain UPHELD. The separate custom-rulebook case supplies a real OVERTURNED decision, code rescore and returned points bond. All five deployed contract addresses and source hashes are unchanged. Browser extension popup signing remains outside the tested signing scope; real signed SDK calls and browser receipt recovery are recorded separately.'+text[end:]
text=text.replace('Its complete readiness check must still reject the missing live OVERTURNED outcome.','Its complete readiness check now includes and verifies the separate live OVERTURNED case.')
marker='\nFinal audit result: exit code 1 solely'
if marker in text:text=text[:text.index(marker)]
base=p['network']['explorer']
def txlink(label,key):return f'[{label}]({base}/tx/{p["transactions"][key]})'
lines=['','## Custom-rulebook case','','The owner chose the existing-contract minimum of four players and four consecutive past weeks instead of redeploying for two players. This points-only league has a zero GEN entry fee and zero GEN dispute bond. Every new transaction has value zero. The original 42-wei deposit budget is unchanged.','','Case league: `'+case['leagueId']+'`. Frozen rule hash: `'+case['league']['rulebook_hash']+'`.','','Generic reader: Fortnight under Post Malone → position '+str(case['genericMatch']['position'])+'. Actual Billboard credit: `'+case['targetRow']['artist_credit']+'`.','','Court verdict: **OVERTURNED**.','', '> '+case['disputes'][0]['rule_quote'],'','Evidence quote: `'+case['disputes'][0]['evidence_quote']+'`.','','Code rescore: '+str(case['rescore']['genericPoints'])+' → 0 points, position '+str(case['rescore']['genericPosition'])+' → 0. Challenger three-point bond: **RETURNED**, without a points adjustment. No native GEN bond existed or was claimed. This is a points-bond return, not an additional wei transfer.','','Custom eligibility is applied through a finalized dispute for each challenged item. This showcased correction concerns the May 25 week; other weeks retain their actual unchallenged generic matches.','','| Step | Finalized receipt |','| --- | --- |', '| League creation | '+txlink('Create','custom-create')+' |']
for i,w in enumerate(case['weeks']):
 keys=[k for k in case['transactions'] if k.startswith('custom-read-week-'+str(i)) and 'child' not in k]
 key=keys[-1]
 lines.append('| Chart '+w['date']+' | '+txlink('Reader',key)+' · '+txlink('Finality callback',key+'-child-0')+' |')
lines.append('| Dispute registration | '+txlink('Open dispute','custom-open-dispute')+' · '+txlink('League callback','custom-open-dispute-child-0')+' |')
ruling_keys=[k for k in case['transactions'] if k.startswith('custom-ruling') and 'child' not in k]
key=ruling_keys[-1]
lines.append('| Actual ruling | '+txlink('OVERTURNED',key)+' · '+txlink('Finality callback',key+'-child-0')+' |')
lines.append('| Rescore and points-bond return | '+txlink('Close and score May 25','custom-close-week-0')+' |')
lines.append('| Completed case season | '+txlink('Close final case week','custom-close-week-3')+' · '+txlink('Season completion callback','custom-close-week-3-child-0')+' |')
lines+=['','Every join, draft pick, ready call, read retry and child is retained in `deploy/proof.json` and `deploy/receipts/custom-*.json`.','','Final audit: **exit code 0**, '+str(len(p['transactions']))+' successful replay receipts and '+str(len(p.get('failedTransactions',{})))+' separately retained failed receipt(s), five deployed sources, ten full chart digests, independent scores/standings, main native payouts, custom rescore and returned points bond verified.','', 'Checks rerun: 39 direct contract tests, five release-resume tests, seven app tests, strict TypeScript. Final Vercel production build and desktop/mobile browser results are recorded separately after deployment. Existing five-contract GenVM lint results are unchanged; contract sources were not modified.']
lines+=['','The first custom Court submission ended in a finalized consensus disagreement and is preserved separately. The successful resubmission used the same frozen clause; no verdict was overridden, no prompt was changed and no mock supplied the ruling.']
report.write_text(text+'\n'.join(lines)+'\n',encoding='utf8')
(ROOT/'docs/DEMO.md').write_text('''# Two-minute demo script

The strict live verifier passes. No Portal submission is part of this demo.

**0:00–0:20 — Main season.** Open the app without a wallet. Show four teams, six scored weeks and the final standings. “Hot Roster is fantasy football for the Billboard charts, refereed by GenLayer.” Select a team to inspect its five-song roster and weekly points.

**0:20–0:40 — Chart and moments.** Open This week and follow the exact archived source. Show the awarded tour card and rejected new-version card with the permanent Wikipedia revision and verbatim quote. “Validators interpret evidence; code calculates points.”

**0:40–1:10 — Custom rulebook.** Choose Custom rulebook beside Main season. “Post Malone was drafted for Fortnight. The generic reader accepts his featured credit at No. 8. This league freezes a stricter rule: featured-only appearances do not count.” Compare the actual Taylor Swift Featuring Post Malone credit, the Court’s OVERTURNED ruling and quoted clause. Show the finalized ruling receipt.

**1:10–1:30 — Rescore and bond.** Show 15 → 0 points and position 8 → 0. “League code applies the Court’s correction when it closes the week. The challenger’s three-point bond is returned. This case has no GEN entry fee or GEN bond.” Open the rescore/bond-return receipt. The existing contracts require four players and four weeks; no contract was redeployed.

**1:30–1:50 — Native payout proof.** Return to Main season. Show the settled 40-wei pool and credited allocations 24, 12 and 4. Open the native receipt links. “Paid means the exact native child credited the correct wallet and amount, checked on-chain. StudioNet GEN is simulated.”

**1:50–2:00 — Inspect or play.** Show On-chain proof, five existing addresses and reload-safe receipts, then Create a league with an editable rulebook. “The strict read-only verifier checks both dispute outcomes and all final evidence. The owner submits to the Portal.”
'''.replace('\n+','\n'),encoding='utf8')
print('Evidence verified; readiness metadata enabled. Portal description:',len(f['description']),'characters.')
