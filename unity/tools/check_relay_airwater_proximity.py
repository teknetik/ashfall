"""Real-input first-person inspection of Relay and Air + Water; not a timing run."""
import asyncio,json,math,os,time
from pathlib import Path
from Xlib import X
from Xlib.ext import xtest
from native_client import Client
from desktop_input import focus,key

OUT=Path(os.environ['ATHEN_NATIVE_DIR'])
async def main():
 c=Client();d=focus();report={'complete':False,'checkpoints':[],'views':[]}
 def snap():return json.loads((OUT/'snapshot.json').read_text())
 async def tap(name,duration):
  key(d,name,True)
  try:await asyncio.sleep(duration)
  finally:key(d,name,False)
 async def walk(name,target):
  start=time.monotonic()
  while True:
   p=snap()['player']['position'];dx=target[0]-p[0];dz=target[2]-p[2];dist=math.hypot(dx,dz)
   if dist<.17:break
   assert time.monotonic()-start<35,(name,p)
   await c.command({'action':'cameraYaw','yaw':math.degrees(math.atan2(dx,dz))})
   await tap('w',min(1.5,max(.03,(dist-.08)/3.4)));await asyncio.sleep(.18)
  s=snap();assert s['player']['grounded'] and abs(s['player']['position'][1]-target[1])<.15,s
  report['checkpoints'].append({'name':name,'snapshot':s})
 root=d.screen().root;window=None
 for wid in root.get_full_property(d.intern_atom('_NET_CLIENT_LIST'),X.AnyPropertyType).value:
  w=d.create_resource_object('window',wid);pid=w.get_full_property(d.intern_atom('_NET_WM_PID'),X.AnyPropertyType)
  if pid is not None and int(pid.value[0])==int(os.environ['ATHEN_NATIVE_PID']):window=w;break
 assert window is not None
 origin=root.translate_coords(window,0,0);g=window.get_geometry();cx=origin.x+g.width//2;cy=origin.y+g.height//2
 async def drag(dx,dy):
  xtest.fake_input(d,X.MotionNotify,x=cx,y=cy);d.sync();await asyncio.sleep(.15)
  xtest.fake_input(d,X.ButtonPress,1);d.sync();await asyncio.sleep(.15)
  try:
   for i in range(1,21):
    xtest.fake_input(d,X.MotionNotify,x=cx+round(dx*i/20),y=cy+round(dy*i/20));d.sync();await asyncio.sleep(.04)
  finally:xtest.fake_input(d,X.ButtonRelease,1);d.sync()
  await asyncio.sleep(.3)
 video=None
 try:
  if snap()['session']['state']=='Paused':await tap('Escape',.1)
  await c.command({'action':'view','camera':'follow'});await c.command({'action':'reset'})
  await c.command({'action':'timeReset'});await c.command({'action':'timePause','paused':True})
  await walk('west lane',[12,0,0]);await walk('north west lane',[12,0,-22.8]);await walk('north east lane',[-12,0,-22.8]);await walk('Relay approach',[-12,0,-19.3]);await walk('Relay close',[-16.25,.5,-19.3])
  await c.command({'action':'cameraYaw','yaw':-90})
  xtest.fake_input(d,X.MotionNotify,x=cx,y=cy);d.sync()
  for _ in range(10):
   xtest.fake_input(d,X.ButtonPress,4);xtest.fake_input(d,X.ButtonRelease,4);d.sync();await asyncio.sleep(.1)
  await asyncio.sleep(.4);assert snap()['camera']['firstPerson'],snap()['camera']
  await drag(0,-round(snap()['camera']['pitch']/.13))
  path=OUT/'relay-airwater-first-person.mp4';assert not path.exists(),'Preserve previous recording'
  video=await asyncio.create_subprocess_exec('ffmpeg','-hide_banner','-loglevel','error','-f','x11grab','-framerate','30','-video_size','1920x1080','-i',os.environ.get('DISPLAY',':0')+f'+{origin.x},{origin.y}','-t','100','-c:v','libx264','-preset','ultrafast','-crf','22','-pix_fmt','yuv420p',str(path),stdin=asyncio.subprocess.PIPE)
  for family in ['relay','airwater-door','airwater-filters']:
   await c.command({'action':'cameraYaw','yaw':-90});await asyncio.sleep(.4)
   await c.command({'action':'capture','name':'first-person-'+family})
   before=snap();await drag(-110,-45);after=snap()
   assert abs(after['camera']['yaw']-before['camera']['yaw'])>5,'Mouse-look did not respond'
   assert after['camera']['firstPerson'] and not after['camera']['overlaps'],after['camera']
   report['views'].append({'family':family,'before':before,'afterLook':after})
   await drag(220,90);await drag(-110,-45)
   if family=='relay':
    await walk('Relay departure',[-12,0,-19.3]);await walk('Air Water approach',[-12,0,-10.35]);await walk('Air Water door',[-16.25,.5,-10.35])
   elif family=='airwater-door':
    await walk('Air Water filter approach',[-16.25,.5,-7.3])
  report['complete']=True
 finally:
  key(d,'w',False)
  if video:await video.communicate(b'q');report['videoExit']=video.returncode
  (OUT/'relay-airwater-proximity.json').write_text(json.dumps(report,indent=2))
  await c.command({'action':'timeReset'})
 print('PASS: Relay and Air + Water first-person approaches, scroll zoom, mouse look, no camera overlaps',flush=True)
asyncio.run(main())
