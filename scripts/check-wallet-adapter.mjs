// Real SDK call through the app's EIP-1193 adapter. No browser extension is emulated.
// The signer remains in this local Node process; only zero-value readiness or expected rejection checks are allowed.
import {existsSync,readFileSync,writeFileSync} from 'node:fs';
import {privateKeyToAccount} from 'viem/accounts';
import {connectWallet} from '../lib/wallet.ts';
import {TransactionHashVariant} from 'genlayer-js/types';
const rpcURL='https://studio.genlayer.com/api';
const expectError=process.argv.includes('--expected-error');
const recordFile=expectError?'deploy/wallet-adapter-rejection-check.json':'deploy/wallet-adapter-check.json';
const checkedMethod=expectError?'configure':'ready';
const originalFetch=globalThis.fetch;
let last=0;
globalThis.fetch=async(input,init)=>{
 const url=typeof input==='string'?input:input instanceof URL?input.href:input.url;
 if(url===rpcURL){
  await new Promise(resolve=>setTimeout(resolve,Math.max(0,4000-(Date.now()-last))));last=Date.now();
  const headers=new Headers(init?.headers);headers.set('User-Agent','Mozilla/5.0 HotRosterWalletCheck/1.0');
  return originalFetch(input,{...init,headers});
 }
 return originalFetch(input,init);
};
async function rpc(method,params=[]){
 const response=await fetch(rpcURL,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',id:1,method,params})});
 const value=await response.json();if(!response.ok||value.error)throw Error(value.error?.message??'RPC unavailable');return value.result;
}
const proof=JSON.parse(readFileSync('deploy/proof.json','utf8'));
const keys=JSON.parse(readFileSync('.secrets/demo-accounts.json','utf8'));
const account=privateKeyToAccount('0x'+keys[0].replace(/^0x/,''));
const previous=existsSync(recordFile)?JSON.parse(readFileSync(recordFile,'utf8')):null;
const output=previous?.wallet===account.address&&previous?.method===checkedMethod?previous:{at:new Date().toISOString(),scope:'Local Node EIP-1193 transport with real signing; browser extension UI remains unverified',wallet:account.address,method:checkedMethod,expectedState:expectError?'FINALIZED_ERROR':'FINALIZED_SUCCESS',valueWei:'0',hash:null,status:'NOT_SUBMITTED'};
const save=()=>writeFileSync(recordFile,JSON.stringify(output,null,2));
globalThis.window={ethereum:{request:async({method,params=[]})=>{
 if(method==='eth_requestAccounts')return [account.address];
 if(method==='eth_chainId')return '0xf22f';
 if(method==='eth_sendTransaction'){
  const tx=params[0];if(BigInt(tx.value)!==0n)throw Error('Only the zero-value smoke call is authorized here');
  const raw=await account.signTransaction({chainId:61999,type:'legacy',to:tx.to,data:tx.data,nonce:Number(BigInt(tx.nonce)),gas:BigInt(tx.gas),gasPrice:BigInt(tx.gasPrice),value:0n});
  return rpc('eth_sendRawTransaction',[raw]);
 }
 return rpc(method,params);
}}};
try{
 if(output.status===(expectError?'FINALIZED_ERROR':'FINALIZED_SUCCESS')){console.log('Recorded adapter check already finalized',output.hash);process.exit(0)}
 const wallet=await connectWallet(hash=>{output.hash=hash;output.status='SUBMITTED';save()});
 if(!output.hash){
  if(!expectError){
   const league=await wallet.client.readContract({address:proof.contracts.League.address,functionName:'get_league',args:[proof.leagueId],transactionHashVariant:TransactionHashVariant.LATEST_FINAL});
   const state=typeof league==='string'?JSON.parse(league):league;
   if(state.status!=='ACTIVE'||state.weeks[state.current_week].status!=='LOCKED')throw Error('Check requires an active locked week');
  }
  const args=expectError?['ChartReader','MomentJudge','RulebookCourt','SeasonPool'].map(name=>proof.contracts[name].address):[proof.leagueId];
  output.hash=await wallet.client.writeContract({address:proof.contracts.League.address,functionName:checkedMethod,args,value:0n});
 }
 output.status='SUBMITTED';save();
 for(let i=0;i<180;i++){
  const receipt=await rpc('eth_getTransactionByHash',[output.hash]);
  if(receipt?.status==='FINALIZED'){
   const leader=receipt.consensus_data?.leader_receipt?.[0];
   output.status=leader?.execution_result==='SUCCESS'&&['AGREE','MAJORITY_AGREE',undefined].includes(receipt.result_name)?'FINALIZED_SUCCESS':'FINALIZED_ERROR';
   output.receipt=receipt;save();
   if(output.status!==(expectError?'FINALIZED_ERROR':'FINALIZED_SUCCESS'))throw Error('Real adapter call did not produce the expected execution outcome');
   console.log(output.status,output.hash);process.exit(0);
  }
  console.log('Wallet adapter receipt',receipt?.status??'submitted');
  await new Promise(resolve=>setTimeout(resolve,10000));
 }
 throw Error('Pending receipt retained; do not submit another smoke call');
}catch(error){output.error=error.shortMessage??error.message;save();console.error(output.error);process.exit(1)}
