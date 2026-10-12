import test from 'node:test';
import assert from 'node:assert/strict';
import {transactionState,rosterOnly,chartDates,score,draftTurn,type LeagueRecord} from '../lib/domain';
test('finality requires execution success and consensus agreement',()=>{
 assert.equal(transactionState({status:'ACCEPTED',txExecutionResultName:'FINISHED_WITH_RETURN'}),'ACCEPTED');
 assert.equal(transactionState({status:'FINALIZED',result_name:'MAJORITY_DISAGREE',txExecutionResultName:'FINISHED_WITH_RETURN'}),'FINALIZED_ERROR');
 assert.equal(transactionState({status:'FINALIZED',txExecutionResultName:'FINISHED_WITH_ERROR'}),'FINALIZED_ERROR');
 assert.equal(transactionState({status:'FINALIZED',txExecutionResultName:'FINISHED_WITH_RETURN'}),'FINALIZED_SUCCESS');
 assert.equal(transactionState({status:'FINALIZED',value_credited:true}),'FINALIZED_SUCCESS');
});
test('UI publishes only roster positions',()=>{
 const rows=Array.from({length:100},(_,i)=>({position:i+1,title:'Song '+i,artist_credit:'Artist',last_week:0,debut:false}));
 assert.deepEqual(rosterOnly({rows,matches:[{position:1,reason:'Same song'},{position:0,reason:'Absent'},{position:10,reason:'Same song'}]}).rows?.map(r=>r.position),[1,10]);
});
test('season dates and scoring boundaries',()=>{
 assert.deepEqual(chartDates('2024-05-25',4),['2024-05-25','2024-06-01','2024-06-08','2024-06-15']);
 assert.throws(()=>chartDates('2024-05-26',4));
 assert.equal(score(2,12,false),18);assert.equal(score(11,0,true),13);assert.equal(score(0,100,false),0);
});
test('snake reverses each round and preserves join order',()=>{
 const l={players:['a','b','c','d'],draft:[]} as unknown as LeagueRecord;
 const turns=Array.from({length:12},(_,i)=>{l.draft.length=i;return draftTurn(l)});
 assert.deepEqual(turns,['a','b','c','d','d','c','b','a','a','b','c','d']);
});
