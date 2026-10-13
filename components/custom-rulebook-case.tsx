import Link from 'next/link';
import {ArrowUpRight} from 'lucide-react';
import {explorer,type CustomRulebookCase} from '@/lib/domain';

export function CustomRulebookCaseView({proof}:{proof:CustomRulebookCase}){
 const ruling=proof.disputes.find(d=>d.item.song.key===proof.targetKey),rescore=proof.rescore;
 const chart=proof.weeks[0];
 const rulingReceipt=Object.entries(proof.transactions).reverse().find(([name])=>name.startsWith('custom-ruling')&&!name.includes('child'))?.[1];
 return <section className="custom-rulebook-case" id="custom-rulebook" aria-labelledby="custom-case-heading">
  <div className="custom-case-heading"><div><h2 id="custom-case-heading">Custom rulebook</h2><p>Lead credits only · Four players · Four historical weeks · No GEN deposits</p></div>{proof.leagueId&&<Link className="text-link" href={'/?league='+proof.leagueId+'#custom-rulebook'}>Open case league<ArrowUpRight size={16}/></Link>}</div>
  <p>In the May 25 chart week, Post Malone was drafted for “Fortnight.” The generic reader permits featured credits. This league’s frozen rulebook requires a lead credit.</p>
  <p className="fine-print">Recorded custom-rulebook proof{proof.recordedAt?' · '+new Date(proof.recordedAt).toLocaleDateString('en-GB'):''}. Custom eligibility is applied through a finalized dispute for each challenged item.</p>
  <ol className="custom-case-sequence">
   <li><h3>Generic chart match</h3><strong>{proof.genericMatch?'No. '+proof.genericMatch.position:'Awaiting finalized read'}</strong><p>{proof.targetRow?.artist_credit??'The actual chart credit appears after the read finalizes.'}</p>{proof.genericMatch&&<p>{proof.genericMatch.reason}</p>}{chart?.source&&<a className="text-link" href={chart.source} target="_blank" rel="noreferrer">Original chart evidence<ArrowUpRight size={14}/></a>}</li>
   <li><h3>Frozen-rulebook ruling</h3><strong>{ruling?.verdict?.replaceAll('_',' ')??'Awaiting ruling'}</strong>{ruling?.rule_quote&&<blockquote>“{ruling.rule_quote}”</blockquote>}{ruling?.evidence_quote&&<p>Evidence: “{ruling.evidence_quote}”</p>}{ruling?.reason&&<p>{ruling.reason}</p>}{rulingReceipt&&<a className="text-link" href={explorer(rulingReceipt)} target="_blank" rel="noreferrer">Ruling receipt<ArrowUpRight size={14}/></a>}</li>
   <li><h3>Code-calculated rescore</h3><strong>{rescore?`${rescore.genericPoints} → ${rescore.correctedPoints} points`:'Awaiting scored week'}</strong>{rescore&&<><p>Chart position {rescore.genericPosition} → {rescore.correctedPosition}. Challenger’s {rescore.pointsBond}-point bond: <b>{rescore.bondStatus.toLowerCase()}</b>. GEN bond: {rescore.genBondWei} wei.</p><a className="text-link" href={explorer(rescore.receipt)} target="_blank" rel="noreferrer">Rescore and bond-return receipt<ArrowUpRight size={14}/></a></>}</li>
  </ol>
 </section>;
}
