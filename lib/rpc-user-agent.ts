import 'server-only';
const marker=Symbol.for('hot-roster.rpc-user-agent');
const state=globalThis as typeof globalThis&{[marker]?:boolean};
if(!state[marker]){
 const original=globalThis.fetch;
 globalThis.fetch=async(input,init)=>{
  const url=typeof input==='string'?input:input instanceof URL?input.toString():input.url;
  if(url==='https://studio.genlayer.com/api'){
   const headers=new Headers(init?.headers??(input instanceof Request?input.headers:undefined));headers.set('User-Agent','Mozilla/5.0 HotRoster/1.0');
   return original(input,{...init,headers});
  }
  return original(input,init);
 };
 state[marker]=true;
}
