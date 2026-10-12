const original=globalThis.fetch;
globalThis.fetch=async(input,init)=>{
 if(typeof init?.body==='string'){
  let body;try{body=JSON.parse(init.body)}catch{}
  if(body?.method==='eth_gasPrice'||body?.method==='eth_maxPriorityFeePerGas')return new Response(JSON.stringify({jsonrpc:'2.0',id:body.id,result:'0x3b9aca00'}),{headers:{'content-type':'application/json'}});
 }
 return original(input,init);
};
