"""Resume the real replay; retain every transaction, never bypass frozen windows."""
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
for stage in [['draft']]+[step for i in range(6) for step in ([['week',str(i)]]+([['moments'],['disputes'],['bonds']] if i==4 else [])+[['close',str(i)]])]+[['settle']]:
    proof=json.loads((ROOT/'deploy/proof.json').read_text())
    league=proof.get('league',{})
    if stage[0]=='draft' and league.get('status') not in ('JOINING','DRAFTING'):continue
    if len(stage)>1 and league.get('weeks',[{}]*6)[int(stage[1])].get('status')=='CLOSED':continue
    print('REPLAY STAGE',*stage,flush=True)
    subprocess.run([sys.executable,str(ROOT/'scripts/release.py'),*stage],cwd=ROOT,check=True)
print('Replay transactions finished. Run the independent proof verifier before marking submission ready.',flush=True)
