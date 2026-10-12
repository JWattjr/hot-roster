import {NextRequest,NextResponse} from 'next/server';
export async function POST(request:NextRequest){try{
 const {url}=await request.json() as {url:string};
 const parsed=new URL(url);
 const wiki=parsed.hostname==='en.wikipedia.org'&&parsed.pathname==='/w/index.php'&&/^[1-9]\d*$/.test(parsed.searchParams.get('oldid')??'');
 const archive=parsed.hostname==='web.archive.org'&&/^\/web\/\d{14}id_\/https?:\/\//.test(parsed.pathname);
 if(parsed.protocol!=='https:'||parsed.username||parsed.password||parsed.port||!(wiki||archive))return NextResponse.json({error:'Use an exact archive.org id_ capture or Wikipedia permanent revision.'},{status:400});
 const response=await fetch(url,{headers:{'User-Agent':'Mozilla/5.0 HotRoster/1.0'},signal:AbortSignal.timeout(15000),redirect:'error'});
 if(!response.ok)throw Error('Evidence returned '+response.status+'. Try a reviewer-accessible permanent link.');
 const page=await response.text();
 const text=page.replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1>/gi,' ').replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim().slice(0,1800);
 return NextResponse.json({url,text,label:'Browser preview only. Validators independently verify the source and eligibility.'});
}catch(e){return NextResponse.json({error:e instanceof Error?e.message:'Preview unavailable. Open the evidence link directly.'},{status:422})}}
