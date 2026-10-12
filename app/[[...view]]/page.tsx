import {Suspense} from 'react';
import proof from '@/deploy/proof.json';
import {rosterOnly,type Snapshot} from '@/lib/domain';
import {RosterApp} from '@/components/roster-app';
export default async function Page({params}:{params:Promise<{view?:string[]}>}){
 const {view}=await params;
 const recorded=proof as unknown as Snapshot;
 const snapshot={...recorded,weeks:recorded.weeks.map(rosterOnly)};
 return <Suspense fallback={<div className="loading-page">Loading the scoreboard…</div>}><RosterApp initial={snapshot} view={view?.[0]??'season'}/></Suspense>;
}
