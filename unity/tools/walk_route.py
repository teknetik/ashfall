import asyncio,json,math,pathlib,time,sys
import os
if os.environ.get("ATHEN_NATIVE_DIR"):
 from native_client import Client
else:
 from fastmcp import Client
from desktop_input import focus,key
ROOT=pathlib.Path(__file__).resolve().parents[1]
CAP=pathlib.Path(os.environ.get('ATHEN_NATIVE_DIR',ROOT/'AthenHill/Captures'));OUT=pathlib.Path(os.environ.get('ATHEN_EVIDENCE',ROOT/'evidence/U2'));OUT.mkdir(exist_ok=True)
ROUTE=[('west_stair_approach',(12,0,0)),('hill_tree',(4,1.5,0)),('hill_southwest',(4,1.5,4)),('south_stair_top',(0,1.5,4)),('south_stair_bottom',(0,0,12)),('ring_approach',(0,0,31)),('ring_gate',(0,.5,36)),('ring_departure',(0,0,31)),('west_lane_south',(13,0,28)),('west_lane_north',(13,0,-29)),('lattice_approach',(0,0,-31)),('lattice_jack',(0,.5,-36.5))]
if len(sys.argv)>1: ROUTE=json.loads(pathlib.Path(sys.argv[1]).read_text())
REPORT_NAME=sys.argv[2] if len(sys.argv)>2 else 'keyboard-route.json'
async def main():
 d=focus();report=[]
 async with Client('http://127.0.0.1:18081/mcp',timeout=60) as c:
  await c.call_tool('set_active_instance',{'instance':'AthenHill@7f7f353bae1a07d0'})
  async def command(j):
   (CAP/'debug-command.json').write_text(json.dumps(j))
   await c.call_tool('execute_menu_item',{'menu_path':'Athen Hill/Diagnostics/Apply command'})
  async def snapshot():
   await c.call_tool('execute_menu_item',{'menu_path':'Athen Hill/Diagnostics/Write snapshot'})
   return json.loads((CAP/'snapshot.json').read_text())
  if (await snapshot())['session']['state']=='Paused':
   key(d,'Escape',True);await asyncio.sleep(.08);key(d,'Escape',False);await asyncio.sleep(.25)
  await command({'action':'reset'});await asyncio.sleep(.3)
  start=await snapshot();report.append({'checkpoint':'west_gate','snapshot':start});print('START',start['player'],flush=True)
  try:
   for name,target in ROUTE:
    started=time.monotonic();lastdist=999;stalls=0
    while True:
     s=await snapshot();p=s['player']['position'];dx=target[0]-p[0];dz=target[2]-p[2];dist=math.hypot(dx,dz)
     if dist<.20:break
     if time.monotonic()-started>35:raise RuntimeError('Timed out reaching '+name)
     if abs(lastdist-dist)<.01:stalls+=1
     else:stalls=0
     if stalls>=5:raise RuntimeError('Blocked before '+name+' at '+str(p))
     lastdist=dist
     await command({'action':'cameraYaw','yaw':math.degrees(math.atan2(dx,dz))});await asyncio.sleep(.08)
     key(d,'w',True)
     try:await asyncio.sleep(min(2,max(.025,(dist-.1)/3.4)))
     finally:key(d,'w',False)
    await asyncio.sleep(.15);s=await snapshot()
    if not s['player']['grounded'] or abs(s['player']['position'][1]-target[1])>.15:raise RuntimeError('Bad ground at '+name+': '+str(s['player']))
    report.append({'checkpoint':name,'snapshot':s});print('PASS',name,s['player'],flush=True)
    (OUT/REPORT_NAME).write_text(json.dumps({'complete':False,'checkpoints':report},indent=2))
   (OUT/REPORT_NAME).write_text(json.dumps({'complete':True,'checkpoints':report},indent=2))
  except Exception as e:
   (OUT/REPORT_NAME).write_text(json.dumps({'complete':False,'error':str(e),'checkpoints':report,'last':await snapshot()},indent=2));raise
  finally:key(d,'w',False)
asyncio.run(main())
