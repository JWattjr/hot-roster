import 'server-only';
import './rpc-user-agent';
import {createClient} from 'genlayer-js';
import {studionet} from 'genlayer-js/chains';
import {TransactionHashVariant} from 'genlayer-js/types';
import type {TransactionHash} from 'genlayer-js/types';
import proof from '@/deploy/proof.json';
import {rosterOnly,transactionState,type Snapshot,type LeagueRecord,type ChartRead,type Moment,type Dispute,type Pool} from './domain';
const client=createClient({chain:studionet,endpoint:'https://studio.genlayer.com/api'});
const contracts=proof.contracts as Record<string,{address:string}>;
let calls:number[]=[];
const cache=new Map<string,{at:number;value:unknown}>();
const inflight=new Map<string,Promise<unknown>>();
async function limited<T>(key:string,fn:()=>Promise<T>,ttl=30000,immutable:(value:T)=>boolean=()=>false):Promise<T>{
 const old=cache.get(key);if(old&&(immutable(old.value as T)||Date.now()-old.at<ttl))return old.value as T;
 const active=inflight.get(key);if(active)return active as Promise<T>;
 calls=calls.filter(t=>Date.now()-t<3600000);
 if(calls.length>=450||calls.filter(t=>Date.now()-t<60000).length>=24)throw Error('StudioNet read budget reached. Retry in a minute.');
 calls.push(Date.now());
 const promise=fn().then(value=>{cache.set(key,{at:Date.now(),value});return value}).finally(()=>inflight.delete(key));inflight.set(key,promise);return promise;
}
async function read<T>(contract:string,method:string,args:unknown[]=[],ttl=30000,immutable:(value:T)=>boolean=()=>false):Promise<T>{
 const address=contracts[contract]?.address;if(!address)throw Error(contract+' deployment is not recorded yet.');
 return limited(contract+method+JSON.stringify(args),async()=>{const v=await client.readContract({address:address as `0x${string}`,functionName:method,args:args as never[],transactionHashVariant:TransactionHashVariant.LATEST_FINAL});return (typeof v==='string'&&/^[\[{]/.test(v)?JSON.parse(v):v) as T},ttl,immutable);
}
export async function leagueSnapshot(id:string):Promise<Snapshot>{
 const league=await read<LeagueRecord>('League','get_league',[id],30000,value=>value.status==='COMPLETED');
 const resolved=(value:{status?:string})=>value.status==='RESOLVED';
 const momentIds=await read<string[]>('MomentJudge','get_ids',[id],60000,()=>league.status==='COMPLETED');
 const disputeIds=await read<string[]>('RulebookCourt','get_ids',[id],60000,()=>league.status==='COMPLETED');
 const moments:Moment[]=[],disputes:Dispute[]=[];
 for(const key of momentIds)moments.push(await read<Moment>('MomentJudge','get_claim',[key],30000,resolved));
 for(const key of disputeIds)disputes.push(await read<Dispute>('RulebookCourt','get_dispute',[key],30000,resolved));
 const pool=await read<Pool>('SeasonPool','get_pool',[id]);
 const weeks:ChartRead[]=[];
 for(let i=0;i<league.weeks.length;i++){
  if(league.weeks[i].status==='OPEN'){weeks.push({});continue}
  const chart=await read<ChartRead>('ChartReader','get_read',[id,i],30000,value=>resolved(value)||league.weeks[i].status==='CLOSED');
  weeks.push(rosterOnly(chart));
 }
 return {league,weeks,moments,disputes,pool,recordedAt:new Date().toISOString(),contracts:(proof as unknown as Snapshot).contracts,transactions:{},completed:league.status==='COMPLETED'};
}
export async function transaction(hash:string){
 return limited('tx:'+hash,async()=>{
  const r=await client.getTransaction({hash:hash as TransactionHash}) as unknown as Record<string,unknown>;
  const state=transactionState(r);
  let appealDeadline:number|null=null;
  if(state==='ACCEPTED'){
   const windowSeconds=await limited('finality-window',()=>client.request({method:'sim_getFinalityWindowTime' as never}),300000);
   const start=Number(r.timestamp_awaiting_finalization),processing=Number(r.appeal_processing_time??0),failed=Number(r.appeal_failed??0);
   if(r.leader_only===false&&r.appealed!==true&&start>0&&Number(windowSeconds)>0&&processing>=0&&Number.isInteger(failed)&&failed>=0)appealDeadline=start+processing+Number(windowSeconds)*0.8**failed;
  }
  const leader=(r.consensus_data as {leader_receipt?:{genvm_result?:unknown}[]})?.leader_receipt?.[0];
  const result=(r.consensus_data as {leader_receipt?:{result?:{payload?:{readable?:string}}}[]})?.leader_receipt?.[0]?.result;
  let createdLeagueId:string|null=null;
  try{const id=JSON.parse(result?.payload?.readable??'null');if(typeof id==='string'&&/^league-\d+$/.test(id)&&state==='FINALIZED_SUCCESS')createdLeagueId=id;}catch{}
  return {hash,state,createdLeagueId,children:state==='FINALIZED_SUCCESS'?(r.triggered_transactions??[]):[],appealDeadline,error:state==='FINALIZED_ERROR'?JSON.stringify(leader?.genvm_result??r.result_name??'Contract execution failed').slice(0,500):null};
 },10000,value=>value.state==='FINALIZED_SUCCESS'||value.state==='FINALIZED_ERROR');
}
