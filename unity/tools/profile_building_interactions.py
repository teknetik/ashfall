"""Profile real-input native city-loop checks separately from the walking route."""
import asyncio,collections,json,os,sys,statistics
from pathlib import Path
from native_client import Client
from desktop_input import focus
O=Path(os.environ['ATHEN_NATIVE_DIR']);ROOT=Path(__file__).resolve().parent
async def main():
 c=Client();focus();await c.command({'action':'profileStart'})
 p=await asyncio.create_subprocess_exec(sys.executable,str(ROOT/'city_loop_check.py'));code=await p.wait()
 focus();await c.command({'action':'profileStop'});frames=json.loads((O/'profile.json').read_text());(O/'interaction-frames.json').write_text(json.dumps(frames))
 def stats(rows):
  v=sorted(r['dt']*1000 for r in rows);return dict(frames=len(v),seconds=sum(v)/1000,averageFps=len(v)*1000/sum(v),p50Ms=statistics.median(v),p95Ms=v[min(len(v)-1,int(len(v)*.95))],p99Ms=v[min(len(v)-1,int(len(v)*.99))],maxMs=max(v))
 report=dict(complete=code==0,scope=__doc__,allFrames=stats(frames),byState={s:stats([v for v in frames if v['state']==s])for s in sorted({v['state']for v in frames})})
 (O/'interaction-performance.json').write_text(json.dumps(report,indent=2));assert code==0;print(json.dumps(report['allFrames']))
asyncio.run(main())
