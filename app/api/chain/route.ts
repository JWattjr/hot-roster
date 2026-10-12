import {NextRequest,NextResponse} from 'next/server';
import {leagueSnapshot,transaction} from '@/lib/server-chain';
export async function GET(request:NextRequest){try{
 const id=request.nextUrl.searchParams.get('league'),hash=request.nextUrl.searchParams.get('tx');
 if(hash&&/^0x[0-9a-f]{64}$/i.test(hash))return NextResponse.json(await transaction(hash));
 if(id&&/^league-[1-9][0-9]{0,7}$/.test(id))return NextResponse.json(await leagueSnapshot(id));
 return NextResponse.json({error:'Provide a valid league ID or transaction hash.'},{status:400});
}catch(e){return NextResponse.json({error:e instanceof Error?e.message:'Chain read failed. Retry.'},{status:503})}}
