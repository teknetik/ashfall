"""Attach to an opted-in development player and exercise movement with real X11 input.
ATHEN_NATIVE_PID + ATHEN_NATIVE_DIR are mandatory. Does not build, quit or mutate scenes.
Run after CharacterMotionPass.Install and native build. Optional ATHEN_MOTION_VIDEO=1.
"""
import asyncio, json, math, os, pathlib, sys, time
ROOT=pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'tools'))
from native_client import Client
from desktop_input import focus,key
from Xlib import X
from Xlib.ext import xtest
OUT=pathlib.Path(os.environ['ATHEN_NATIVE_DIR'])

async def main():
 d=focus();c=Client();report={'complete':False,'input':'Real X11 keyboard and wheel; QA only resets/views/records','scenarios':[]};video=None
 def snap():return json.loads((OUT/'snapshot.json').read_text())
 async def tap(k,seconds=.08):
  key(d,k,True)
  try:await asyncio.sleep(seconds)
  finally:key(d,k,False)
 async def grounded(timeout=3):
  deadline=time.monotonic()+timeout
  while time.monotonic()<deadline:
   if snap()['player']['grounded']:return
   await asyncio.sleep(.04)
  raise AssertionError('Player did not ground')
 async def begin(name):
  await c.command({'action':'motionStart'});report['activeScenario']=name;return time.monotonic()
 async def end(name,started):
  await c.command({'action':'motionStop'});rows=json.loads((OUT/'motion.json').read_text());(OUT/(name+'-motion.json')).write_text(json.dumps(rows,indent=2))
  row={'name':name,'seconds':time.monotonic()-started,'frames':len(rows),'phases':list(dict.fromkeys(r['phase']for r in rows)),'acceptedJumps':sum(r['JumpStarted']for r in rows),'maxY':max(r['position'][1]for r in rows),'minY':min(r['position'][1]for r in rows),'final':rows[-1]}
  report['scenarios'].append(row);return rows,row
 def assert_jump(rows,row,count=1):
  assert row['acceptedJumps']==count,row
  for phase in ['Takeoff','Rising','Falling','Landing','Grounded']:assert phase in row['phases'],row
  assert rows[-1]['Grounded']and rows[-1]['phase']=='Grounded',row
  assert 1.16<=row['maxY']-row['minY']<=1.31,row
  assert abs(rows[-1]['position'][1]-rows[0]['position'][1])<.07,row
 try:
  await c.command({'action':'view','camera':'follow'});await c.command({'action':'reset'});await asyncio.sleep(.6)
  if snap()['session']['state']=='Paused':await tap('Escape');await asyncio.sleep(.3)
  assert snap()['session']['state']=='Play',snap()['session']
  root=d.screen().root
  for wid in root.get_full_property(d.intern_atom('_NET_CLIENT_LIST'),X.AnyPropertyType).value:
   window=d.create_resource_object('window',wid);pid=window.get_full_property(d.intern_atom('_NET_WM_PID'),X.AnyPropertyType)
   if pid is not None and int(pid.value[0])==int(os.environ['ATHEN_NATIVE_PID']):origin=root.translate_coords(window,0,0);break
  xtest.fake_input(d,X.MotionNotify,x=origin.x+960,y=origin.y+540);d.sync()
  if os.environ.get('ATHEN_MOTION_VIDEO')=='1':
   video=await asyncio.create_subprocess_exec('ffmpeg','-hide_banner','-loglevel','error','-y','-f','x11grab','-framerate','60','-video_size','1920x1080','-i',os.environ.get('DISPLAY',':0')+f'+{origin.x},{origin.y}','-c:v','libx264','-preset','ultrafast','-crf','20','-pix_fmt','yuv420p',str(OUT/'character-motion.mp4'),stdin=asyncio.subprocess.PIPE)
   report['videoStartedMonotonic']=time.monotonic()
  started=await begin('standing-jump');await asyncio.sleep(.2);await tap('space');await asyncio.sleep(1.3);rows,row=await end('standing-jump',started);assert_jump(rows,row)
  await c.command({'action':'reset'});await asyncio.sleep(.35)
  started=await begin('running-jump');key(d,'w',True);key(d,'Shift_L',True);await asyncio.sleep(.4);await tap('space');await asyncio.sleep(1.2);key(d,'w',False);key(d,'Shift_L',False);await asyncio.sleep(.4);rows,row=await end('running-jump',started);assert_jump(rows,row)
  assert max(r['Speed']for r in rows)>5.9,row
  assert any(r['clip']=='jump_landing_moving'for r in rows),row
  await c.command({'action':'reset'});await asyncio.sleep(.35)
  started=await begin('held-jump');await tap('space',1.6);await asyncio.sleep(.35);rows,row=await end('held-jump',started);assert_jump(rows,row)
  started=await begin('repeated-jump');await tap('space');await asyncio.sleep(.24);await grounded();await tap('space');await asyncio.sleep(1.3);rows,row=await end('repeated-jump',started);assert_jump(rows,row,2)
  started=await begin('modal-block');await tap('5');await asyncio.sleep(.25);assert snap()['session']['state']=='Inventory',snap()['session'];before=snap()['player']['position'];key(d,'w',True);await tap('space');await asyncio.sleep(.35);key(d,'w',False);after=snap()['player']['position'];assert math.dist(before,after)<.03;await tap('Escape');await asyncio.sleep(.35);rows,row=await end('modal-block',started);assert row['acceptedJumps']==0,row
  await c.command({'action':'goto','landmark':'hill_tree'});await c.command({'action':'cameraYaw','yaw':45});await asyncio.sleep(.4)
  started=await begin('walk-off-hill');key(d,'w',True);await asyncio.sleep(2.4);key(d,'w',False);await asyncio.sleep(.7);rows,row=await end('walk-off-hill',started)
  assert row['acceptedJumps']==0 and 'Takeoff'not in row['phases'],row
  assert 'Falling'in row['phases']and'Landing'in row['phases'],row
  assert row['maxY']-row['minY']>1 and rows[-1]['Grounded'],row
  await c.command({'action':'goto','landmark':'hill_tree'});await c.command({'action':'cameraYaw','yaw':90});await asyncio.sleep(.4)
  started=await begin('stairs-jump');key(d,'w',True);await asyncio.sleep(.65);await tap('space');await asyncio.sleep(1.3);key(d,'w',False);await asyncio.sleep(.5);rows,row=await end('stairs-jump',started)
  assert row['acceptedJumps']==1 and'Landing'in row['phases']and rows[-1]['Grounded'],row
  await c.command({'action':'reset'});await asyncio.sleep(.4)
  for _ in range(18):xtest.fake_input(d,X.ButtonPress,4);xtest.fake_input(d,X.ButtonRelease,4);d.sync();await asyncio.sleep(.05)
  await asyncio.sleep(.25);assert snap()['camera']['firstPerson']and snap()['camera']['playerHidden'],snap()['camera']
  started=await begin('first-person-jump');await tap('space');await asyncio.sleep(1.3);rows,row=await end('first-person-jump',started);assert_jump(rows,row)
  assert not snap()['camera']['overlaps'],snap()['camera']
  await c.command({'action':'capture','name':'first-person-landing'})
  for _ in range(6):xtest.fake_input(d,X.ButtonPress,5);xtest.fake_input(d,X.ButtonRelease,5);d.sync();await asyncio.sleep(.06)
  await asyncio.sleep(.3);await c.command({'action':'actorSnapshot'});report['actors']=json.loads((OUT/'actors.json').read_text())
  report['complete']=True
 finally:
  for k in ['space','w','a','s','d','Shift_L']:key(d,k,False)
  if video:
   video.stdin.write(b'q');await video.stdin.drain();await video.wait()
   report['video']='character-motion.mp4, real-input 1080p/60 capture; review at normal speed and frame by frame'
  (OUT/'character-motion-report.json').write_text(json.dumps(report,indent=2))
 print(json.dumps(report,indent=2))

if __name__=='__main__':asyncio.run(main())
