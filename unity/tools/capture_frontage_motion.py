"""Record real first-person proximity input at the two installed frontages.
Both frontages use real approaches. A direct diagnostic start at Basic General
can overlap Mira and is unsuitable for first-person visual evidence.
"""
import ast,asyncio,json,os,sys
from pathlib import Path
from Xlib import X
from Xlib.ext import xtest
from native_client import Client
from desktop_input import focus,key
O=Path(os.environ['ATHEN_NATIVE_DIR']);ROOT=Path(__file__).resolve().parent
SELECTED=sys.argv[1] if len(sys.argv)>1 else None
assert SELECTED in (None,'relay_works','basic_general')
async def main():
 c=Client();report=dict(complete=False,note=__doc__,clips=[]);d=focus()
 def snap():return json.loads((O/'snapshot.json').read_text())
 async def tap(k,seconds):
  key(d,k,True)
  try:await asyncio.sleep(seconds)
  finally:key(d,k,False)
 async def wheel(button,count):
  for _ in range(count):xtest.fake_input(d,X.ButtonPress,button);xtest.fake_input(d,X.ButtonRelease,button);d.sync();await asyncio.sleep(.05)
 route=[('relay_lane',(12,0,0)),('north_lane_west',(12,0,-22.8)),('north_lane_east',(-12,0,-22.8)),('relay_approach',(-12,0,-18)),('relay_porch',(-16,.5,-18)),('relay_door_contact',(-17.45,.5,-18))]
 (O/'proximity-route.json').write_text(json.dumps(route,indent=2))
 try:
  if SELECTED!='basic_general':
   proc=await asyncio.create_subprocess_exec(sys.executable,str(ROOT/'walk_route.py'),str(O/'proximity-route.json'),'proximity-route-result.json');assert await proc.wait()==0
  for name,landmark,yaw in [('relay_works',None,-90),('basic_general','basic_general',180)]:
   if SELECTED and name!=SELECTED:continue
   if landmark:
    node=next(n for n in ast.parse((ROOT/'check_salvage.py').read_text()).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ROUTE' for t in n.targets))
    steps=ast.literal_eval(node.value);steps=steps[:next(i for i,v in enumerate(steps) if v[0]=='general_porch')+1]
    (O/'basic-general-proximity-route.json').write_text(json.dumps(steps,indent=2))
    proc=await asyncio.create_subprocess_exec(sys.executable,str(ROOT/'walk_route.py'),str(O/'basic-general-proximity-route.json'),'basic-general-proximity-route-result.json');assert await proc.wait()==0
   focus();await c.command({'action':'view','camera':'follow'})
   if landmark:name='basic_general-approach'
   await c.command({'action':'cameraYaw','yaw':yaw});await asyncio.sleep(.3)
   root=d.screen().root
   for wid in root.get_full_property(d.intern_atom('_NET_CLIENT_LIST'),X.AnyPropertyType).value:
    w=d.create_resource_object('window',wid);pid=w.get_full_property(d.intern_atom('_NET_WM_PID'),X.AnyPropertyType)
    if pid is not None and int(pid.value[0])==int(os.environ['ATHEN_NATIVE_PID']):origin=root.translate_coords(w,0,0);break
   else:raise RuntimeError('Native window missing')
   xtest.fake_input(d,X.MotionNotify,x=origin.x+960,y=origin.y+540);d.sync();await wheel(4,18);assert snap()['camera']['firstPerson']
   path=O/(name+'-first-person-motion.mp4');assert not path.exists()
   video=await asyncio.create_subprocess_exec('ffmpeg','-hide_banner','-loglevel','error','-f','x11grab','-framerate','30','-video_size','1920x1080','-i',os.environ.get('DISPLAY',':0')+f'+{origin.x},{origin.y}','-t','10','-c:v','libx264','-preset','ultrafast','-crf','22','-pix_fmt','yuv420p',str(path))
   await asyncio.sleep(.8);await c.command({'action':'capture','name':name+'-first-person'});before=snap()
   await tap('a',.2);await asyncio.sleep(.4);await tap('d',.4);await asyncio.sleep(.4);await tap('a',.2)
   assert await video.wait()==0;report['clips'].append(dict(name=name,file=path.name,before=before,after=snap()));await wheel(5,6)
  report['complete']=True
 finally:
  for k in ['w','a','s','d']:key(d,k,False)
  (O/('frontage-motion-'+SELECTED+'.json' if SELECTED else 'frontage-motion.json')).write_text(json.dumps(report,indent=2))
 print(str(len(report['clips']))+' first-person frontage clips complete')
asyncio.run(main())
