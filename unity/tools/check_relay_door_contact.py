"""Real-input approach and sustained movement against Relay's closed-door proxy."""
import asyncio,json,os,sys,math
from pathlib import Path
from native_client import Client
from desktop_input import focus,key
O=Path(os.environ['ATHEN_NATIVE_DIR']);T=Path(__file__).resolve().parent
async def main():
 p=await asyncio.create_subprocess_exec(sys.executable,str(T/'walk_route.py'),str(O/'proximity-route.json'),'door-contact-approach.json');assert await p.wait()==0
 c=Client();d=focus();await c.command({'action':'cameraYaw','yaw':-90});await asyncio.sleep(.2)
 def snap():return json.loads((O/'snapshot.json').read_text())
 before=snap();key(d,'w',True)
 try:
  await asyncio.sleep(.8);first=snap();await asyncio.sleep(.8);second=snap()
 finally:key(d,'w',False)
 a=first['player']['position'];b=second['player']['position'];report=dict(complete=False,before=before,firstContact=first,continuedPressure=second,continuedDisplacement=math.dist(a,b))
 (O/'door-contact.json').write_text(json.dumps(report,indent=2))
 assert -17.9<b[0]<-17.35 and abs(b[2]+18)<.1 and second['player']['grounded'],b
 assert math.dist(a,b)<.025,'Controller passes through the authored closed door'
 report['complete']=True;(O/'door-contact.json').write_text(json.dumps(report,indent=2));print('Closed-door contact passes',b)
asyncio.run(main())
