"""Verify the new Humanoid actually walks, loops, and remains at ground level."""
import asyncio,json,os,math
from pathlib import Path
from native_client import Client
out=Path(os.environ['ATHEN_NATIVE_DIR'])
async def main():
 samples=[]
 async with Client() as c:
  for i in range(30):
   await c.command({'action':'actorSnapshot'})
   actors=json.loads((out/'actors.json').read_text()); assert len(actors)==9
   a=next(a for a in actors if a['name']=='npc_yard_mechanic');samples.append(a)
   (out/'mechanic-animation.json').write_text(json.dumps({'complete':False,'samples':samples},indent=2))
   assert a['humanoid'] and a['CurrentClip']=='walk',a
   assert a['rendererCount']==1 and a['triangles']<=7000,a
   assert -.08<=a['meshLow']<=.14 and 1.5<=a['meshHigh']<=1.9,a
   assert 33.99<=a['position'][0]<=38.01 and  -16.01<=a['position'][2]<=-11.99,a
   await asyncio.sleep(.7)
  assert max(math.dist(a['leftFoot'],samples[0]['leftFoot']) for a in samples)>.08,'Frozen gait'
  assert max(math.dist(a['position'],samples[0]['position']) for a in samples)>3,'Frozen walker'
  assert samples[-1]['normalizedTime']-samples[0]['normalizedTime']>3,'Walk animation did not loop'
  positions=[a['position'] for a in samples]
  sides={'west':any(abs(p[0]-34)<.02 for p in positions),'east':any(abs(p[0]-38)<.02 for p in positions),'north':any(abs(p[2]+16)<.02 for p in positions),'south':any(abs(p[2]+12)<.02 for p in positions)}
  assert all(sides.values()),sides
  report={'complete':True,'samples':samples,'allFourPatrolSidesObserved':sides,'minimumSoleY':min(a['meshLow'] for a in samples),'maximumSoleY':max(a['meshLow'] for a in samples)}
  (out/'mechanic-animation.json').write_text(json.dumps(report,indent=2));print('PASS: mechanic Humanoid gait, route, loops and sole height',flush=True)
asyncio.run(main())
