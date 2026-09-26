"""Repeat only the measured traversal after a verified completed warm-up and interruption."""
import asyncio,ast,json,os,statistics,sys,time
from pathlib import Path
from native_client import Client
from desktop_input import focus,key
ROOT=Path(__file__).resolve().parent;OUT=Path(os.environ['ATHEN_NATIVE_DIR'])
for node in ast.parse((ROOT/'check_building_traversal.py').read_text()).body:
 if isinstance(node,ast.FunctionDef)and node.name in ['percentile','summarize']:exec(compile(ast.Module(body=[node],type_ignores=[]),'existing frame statistics','exec'))
async def main():
 assert json.loads((OUT/'warmup-route.json').read_text())['complete'],'Warm-up must already be complete'
 assert not (OUT/'traversal-performance.json').exists(),'Preserve previous results'
 c=Client();d=focus()
 if json.loads((OUT/'snapshot.json').read_text())['session']['state']=='Paused':
  key(d,'Escape',True);await asyncio.sleep(.08);key(d,'Escape',False);await asyncio.sleep(.3)
 await c.command({'action':'view','camera':'follow'});await c.command({'action':'timeReset'});await c.command({'action':'timePause','paused':True});await c.command({'action':'settingsSnapshot'});await c.command({'action':'timeState'})
 settings=json.loads((OUT/'settings.json').read_text());assert settings['renderScale']==1 and not settings['video']['vSync'] and settings['video']['frameLimit']==0
 report={'complete':False,'scope':__doc__,'settings':settings,'lighting':json.loads((OUT/'time-state.json').read_text()),'warmup':'warmup-route.json','retainedInterruption':'traversal-interruption.json','utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
 await c.command({'action':'profileStart'})
 try:
  p=await asyncio.create_subprocess_exec(sys.executable,str(ROOT/'walk_route.py'),str(OUT/'all-building-route.json'),'measured-route.json');code=await p.wait();assert code==0,'Measured traversal failed'
  await c.command({'action':'profileStop'});frames=json.loads((OUT/'profile.json').read_text());(OUT/'traversal-frames.json').write_text(json.dumps(frames))
  report['allFrames']=summarize(frames);report['movingFrames']=summarize([f for f in frames if f['state']=='Play'and f['speed']>1]);s=report['allFrames'];report['meetsCurrentFrameTimeTarget']=s['averageFps']>=60 and s['p99Ms']<=16.67;report['complete']=True
  report['counterNotes']='Unavailable nonpositive counters are null. Submitted triangles include render passes. No video encoder during this measured pass.'
  print(json.dumps(s),flush=True)
 finally:(OUT/'traversal-performance.json').write_text(json.dumps(report,indent=2))
asyncio.run(main())
