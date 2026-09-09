"""Native moving close-ups; debug setup is separate from real route qualification."""
import asyncio,json,os,sys
from pathlib import Path
from Xlib import X
from Xlib.ext import xtest
from native_client import Client
from desktop_input import focus,key
O=Path(os.environ['ATHEN_NATIVE_DIR']);ROOT=Path(__file__).resolve().parent
async def main():
 c=Client();d=focus();report={'complete':False,'clips':[],'note':'Real keys/wheel; debug positioning for tree, hall and Vex, real approach route for Finery. Recording excluded from performance samples.'}
 async def tap(name,seconds=.1):
  key(d,name,True)
  try:await asyncio.sleep(seconds)
  finally:key(d,name,False)
  await asyncio.sleep(.2)
 def snap():return json.loads((O/'snapshot.json').read_text())
 async def wheel(button,count):
  for _ in range(count):xtest.fake_input(d,X.ButtonPress,button);xtest.fake_input(d,X.ButtonRelease,button);d.sync();await asyncio.sleep(.05)
 try:
  await c.command({'action':'reset'});await c.command({'action':'view','camera':'follow'})
  route=[['approach',[12,0,0]],['finery_lane',[12,0,-18]],['finery_step',[13.96,.25,-18]],['finery_porch',[15.4,.5,-18]]]
  (O/'close-route.json').write_text(json.dumps(route))
  proc=await asyncio.create_subprocess_exec(sys.executable,str(ROOT/'walk_route.py'),str(O/'close-route.json'),'close-route-result.json');assert await proc.wait()==0
  for name,landmark,yaw in [('finery',None,90),('tree','hill_tree',-90),('hall','vanguard_hall',180),('vex','west_gate',-139)]:
   await c.command({'action':'view','camera':'follow'})
   if landmark:await c.command({'action':'goto','landmark':landmark})
   await c.command({'action':'cameraYaw','yaw':yaw});await asyncio.sleep(.4)
   d=focus();root=d.screen().root
   for wid in root.get_full_property(d.intern_atom('_NET_CLIENT_LIST'),X.AnyPropertyType).value:
    w=d.create_resource_object('window',wid);pid=w.get_full_property(d.intern_atom('_NET_WM_PID'),X.AnyPropertyType)
    if pid is not None and int(pid.value[0])==int(os.environ['ATHEN_NATIVE_PID']):origin=root.translate_coords(w,0,0);break
   xtest.fake_input(d,X.MotionNotify,x=origin.x+960,y=origin.y+540);d.sync()
   await wheel(4,18);assert snap()['camera']['firstPerson']
   video=await asyncio.create_subprocess_exec('ffmpeg','-hide_banner','-loglevel','error','-y','-f','x11grab','-framerate','30','-video_size','1920x1080','-i',os.environ.get('DISPLAY',':0')+f'+{origin.x},{origin.y}','-t','10','-c:v','libx264','-preset','ultrafast','-crf','22','-pix_fmt','yuv420p',str(O/(name+'-motion.mp4')))
   await asyncio.sleep(1);await c.command({'action':'capture','name':name+'-first-person'})
   await tap('a',.28);await asyncio.sleep(.5);await tap('d',.56);await asyncio.sleep(.5);await tap('a',.28)
   if name=='vex':await tap('e');assert snap()['session']['state']=='Dialogue';await c.command({'action':'capture','name':'vex-conversation'});await asyncio.sleep(1);await tap('Escape')
   assert await video.wait()==0
   report['clips'].append(name);await wheel(5,6)
  report['complete']=True
 finally:
  for k in ['w','a','s','d']:key(d,k,False)
  (O/'motion-report.json').write_text(json.dumps(report,indent=2));await c.command({'action':'quit'})
 print(json.dumps(report))
asyncio.run(main())
