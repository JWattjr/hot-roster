export type Song={key:string;title:string;primary_artist:string;owner?:string};
export type Card={id:string;definition:string;points:number;domains:string[]};
export type Detail={song:Song;position:number;last_week:number;debut:boolean;base:number;moments:number;reason:string};
export type Week={status:string;songs:Song[];scores:Record<string,number>;details:Record<string,Detail>;ready:string[];swaps:Record<string,unknown>;claims:string[];disputes:string[];locked_at:number;read_deadline:number;claim_deadline?:number;closed_at:number};
export type LeagueRecord={id:string;name:string;creator:string;dates:string[];max_players:number;roster_size:number;cards:Card[];rulebook:string;rulebook_hash:string;entry_fee:string;dispute_seconds:number;replay:boolean;settle_deadline:number;status:string;players:string[];names:Record<string,string>;rosters:Record<string,Song[]>;draft:(Song&{owner:string})[];schedule:string[][][];weeks:Week[];current_week:number;standings:{wallet:string;name:string;points:number;wins:number;losses:number;ties:number}[]};
export type ChartRead={status?:string;verdict?:string;songs?:Song[];matches?:{position:number;reason:string}[];rows?:{position:number;title:string;artist_credit:string;last_week:number;debut:boolean}[];source?:string;source_kind?:string;digest?:string;finalized_at?:number;date?:string;reason?:string};
export type Moment={id:string;status:string;week:number;song:Song;card:Card;url:string;verdict:string|null;quote:string;reason:string;deadline:number;finalized_at?:number;claimant:string};
export type Dispute={id:string;status:string;week:number;item_id:string;item:{kind:string;song:Song;url:string;original_verdict:string|number};argument:string;challenger:string;opponent:string;verdict:string|null;rule_quote:string;evidence_quote:string;reason:string;deadline:number;finalized_at?:number;corrected_position?:number;corrected_verdict?:string;bond_recipient?:string;gen_bond:string;bond_claimed:boolean};
export type Pool={status?:string;entries?:Record<string,string>;total?:string;payouts?:Record<string,string>;claims?:Record<string,{status:string;attempt:number;amount:string;parent:string;child:string;verification_deadline:number}>;paid?:string;deadline?:number};
export type Snapshot={league?:LeagueRecord;weeks:ChartRead[];moments:Moment[];disputes:Dispute[];pool:Pool|null;recordedAt?:string;completed?:boolean;submissionReady?:boolean;contracts:Record<string,{address:string;sha256:string;source:string}>;transactions:Record<string,string>;sourceCommit?:string|null;blockers?:string[];probeContract?:string};
export type TxState='SUBMITTED'|'PENDING'|'ACCEPTED'|'FINALIZED_SUCCESS'|'FINALIZED_ERROR';
export type TrackedTx={hash:string;label:string;account:string;state:TxState;created:number;children?:string[];appealDeadline?:number|null;error?:string};
export function transactionState(r:Record<string,unknown>):TxState{
 const consensus=r.consensus_data as {leader_receipt?:{execution_result?:string;result?:unknown}[]}|undefined;
 const status=String(r.status_name??r.statusName??r.status??'');
 if(status==='FINALIZED'||status==='7'){
  if(r.value_credited===true&&String(r.type)==='0'&&!r.consensus_data)return 'FINALIZED_SUCCESS';
  const execution=String(r.txExecutionResultName??consensus?.leader_receipt?.[0]?.execution_result??'');
  const agreement=String(r.result_name??r.resultName??'');
  return ['SUCCESS','FINISHED_WITH_RETURN'].includes(execution)&&(!agreement||['AGREE','MAJORITY_AGREE','SUCCESS'].includes(agreement))?'FINALIZED_SUCCESS':'FINALIZED_ERROR';
 }
 if(status==='ACCEPTED'||status==='6')return 'ACCEPTED';
 return status?'PENDING':'SUBMITTED';
}
export function rosterOnly(chart:ChartRead):ChartRead{
 const positions=new Set(chart.matches?.map(m=>m.position)??[]);
 return {...chart,rows:chart.rows?.filter(row=>positions.has(row.position))};
}
export function shortAddress(value:string){return value.slice(0,6)+'…'+value.slice(-4)}
export function draftTurn(league:LeagueRecord){const i=league.draft.length,n=league.players.length;return n?league.players[Math.floor(i/n)%2===0?i%n:n-1-i%n]:null}
export function score(position:number,last:number,debut:boolean){return (position===1?25:position>=2&&position<=10?15:position<=40&&position>=11?8:position<=100&&position>=41?3:0)+(position>0&&debut?5:0)+(position>0&&last-position>=10?3:0)}
export function chartDates(first:string,count:number){const date=new Date(first+'T00:00:00Z');if(!Number.isFinite(date.getTime())||date.getUTCDay()!==6||count<4||count>8)throw Error('Choose a Saturday and 4–8 weeks.');return Array.from({length:count},(_,i)=>new Date(date.getTime()+i*604800000).toISOString().slice(0,10))}
export const explorer=(hash:string)=>'https://explorer-studio.genlayer.com/tx/'+hash;
