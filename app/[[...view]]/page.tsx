import {Suspense} from 'react';
import proof from '@/deploy/proof.json';
import {recordedSnapshot,type Snapshot} from '@/lib/domain';
import {RosterApp} from '@/components/roster-app';
export default async function Page({params,searchParams}:{params:Promise<{view?:string[]}>;searchParams:Promise<{league?:string}>}){
 const [{view},{league}]=await Promise.all([params,searchParams]);
 const recorded=proof as unknown as Snapshot;
 const snapshot=recordedSnapshot(recorded,league);
 return <Suspense fallback={<div className="loading-page">Loading the scoreboard…</div>}><RosterApp initial={snapshot} view={view?.[0]??'season'}/></Suspense>;
}
