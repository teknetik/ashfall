"""Real native pointer checks for movable HUD/windows and the ten square slots.

Uses NativeQa's separate QA layout preference namespace; never changes the player's
saved layout. Run with: uv run --with python-xlib python unity/tools/check_draggable_ui.py
For an isolated display, prefix with:
xvfb-run -a -s "-screen 0 3840x2160x24" env ATHEN_UI_XVFB=1 LIBGL_ALWAYS_SOFTWARE=1
"""
import asyncio,json,os,pathlib,subprocess,sys,math,shutil,time
from Xlib import X,display
from Xlib.ext import xtest
from native_client import Client
from desktop_input import focus as desktop_focus,key,click
R=pathlib.Path(__file__).resolve().parents[1]
Q=R/'evidence/ui/20260908/draggable/native'
Q.mkdir(parents=True,exist_ok=True)

def focus():
 if not os.environ.get('ATHEN_UI_XVFB'):return desktop_focus()
 # A private Xvfb display needs no window manager. Publish the player window for
 # the shared keyboard tests, then focus it directly without touching the desktop.
 d=display.Display();root=d.screen().root
 d.change_keyboard_control(auto_repeat_mode=X.AutoRepeatModeOff)
 for w in root.query_tree().children:
  pid=w.get_full_property(d.intern_atom('_NET_WM_PID'),X.AnyPropertyType)
  if pid is not None and int(pid.value[0])==int(os.environ['ATHEN_NATIVE_PID']):
   root.change_property(d.intern_atom('_NET_CLIENT_LIST'),d.intern_atom('WINDOW'),32,[w.id])
   w.configure(stack_mode=X.Above);w.set_input_focus(X.RevertToParent,X.CurrentTime);d.sync();time.sleep(.15)
   return d
 raise RuntimeError('QA player window not found on private display')

async def main():
 p=None;checks=[]
 async def launch():
  nonlocal p,d,c
  for n in ['snapshot.json','ack.json','command.json']:(Q/n).unlink(missing_ok=True)
  p=subprocess.Popen([str(R/'AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64'),'-force-glcore','-screen-fullscreen','0','-screen-width','1920','-screen-height','1080','-logFile',str(Q/'Player.log'),'--athen-qa',str(Q)],stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
  os.environ.update(ATHEN_NATIVE_DIR=str(Q),ATHEN_NATIVE_PID=str(p.pid),ATHEN_EVIDENCE=str(Q))
  for _ in range(200):
   if (Q/'snapshot.json').exists():break
   assert p.poll() is None,'Native player exited'
   await asyncio.sleep(.2)
  d=focus();c=Client();await asyncio.sleep(1)
  if snap()['session']['state']=='Paused':await tap('Escape')
 def snap():return json.loads((Q/'snapshot.json').read_text())
 async def tap(k):
  nonlocal d
  d=focus()
  key(d,k,True)
  try:
   if os.environ.get('ATHEN_UI_XVFB'):await c.command({'action':'uiSnapshot'})
   else:await asyncio.sleep(.08)
  finally:key(d,k,False)
  await asyncio.sleep(.2)
 async def layout():
  await c.command({'action':'uiSnapshot'});j=json.loads((Q/'ui-layout.json').read_text())
  return {e['name']:e for e in j['elements'] if e['name']}
 def screen_point(pos,els):
  root=d.screen().root
  for wid in root.get_full_property(d.intern_atom('_NET_CLIENT_LIST'),X.AnyPropertyType).value:
   w=d.create_resource_object('window',wid);pid=w.get_full_property(d.intern_atom('_NET_WM_PID'),X.AnyPropertyType)
   if pid is not None and int(pid.value[0])==p.pid:
    origin=root.translate_coords(w,0,0);s=snap();scale=s['width']/els['hud']['bounds'][2]
    return int(origin.x+pos[0]*scale),int(origin.y+pos[1]*scale)
  raise RuntimeError('QA window not found')
 async def press(name):
  nonlocal d
  d=focus()
  els=await layout();e=els[name];assert e['visible'] and e['enabled'],name
  x,y,w,h=e['bounds'];xx,yy=screen_point((x+w/2,y+h/2),els)
  if os.environ.get('ATHEN_UI_XVFB'):
   xtest.fake_input(d,X.MotionNotify,x=xx,y=yy);xtest.fake_input(d,X.ButtonPress,1);d.sync()
   await c.command({'action':'uiSnapshot'});xtest.fake_input(d,X.ButtonRelease,1);d.sync();await c.command({'action':'uiSnapshot'})
  else:click(d,xx,yy)
  await asyncio.sleep(.3)
 async def reset():
  if snap()['session']['state']!='Play':await tap('Escape')
  await tap('Escape');await press('reset-ui');await tap('Escape')
 async def capture(name):
  await c.command({'action':'capture','name':name});await asyncio.sleep(.3)
  await c.command({'action':'uiSnapshot'});shutil.copy(Q/'ui-layout.json',Q/(name+'-layout.json'))
 async def drag(name,delta=(65,50),handle=None,local=(35,20),ctrl=False):
  nonlocal d
  d=focus()
  els=await layout();e=els[name];assert e['visible'],name
  rect=e['bounds'];grab=els[handle]['bounds'] if handle else rect
  pos=(grab[0]+grab[2]/2,grab[1]+grab[3]/2) if handle else (grab[0]+local[0],grab[1]+local[1])
  start=screen_point(pos,els);end=screen_point((pos[0]+delta[0],pos[1]+delta[1]),els)
  before=snap();xtest.fake_input(d,X.MotionNotify,x=start[0],y=start[1]);d.sync();await asyncio.sleep(.1)
  if ctrl:
   key(d,'Control_L',True);await asyncio.sleep(.15)
   if os.environ.get('ATHEN_UI_XVFB'):await c.command({'action':'uiSnapshot'})
  xtest.fake_input(d,X.ButtonPress,1);d.sync();await asyncio.sleep(.08)
  if os.environ.get('ATHEN_UI_XVFB'):await c.command({'action':'uiSnapshot'})
  try:
   steps=4 if os.environ.get('ATHEN_UI_XVFB') else 12
   for i in range(1,steps+1):
    t=i/steps;xtest.fake_input(d,X.MotionNotify,x=int(start[0]+(end[0]-start[0])*t),y=int(start[1]+(end[1]-start[1])*t));d.sync();await asyncio.sleep(.025)
    if os.environ.get('ATHEN_UI_XVFB'):await c.command({'action':'uiSnapshot'})
  finally:
   xtest.fake_input(d,X.ButtonRelease,1);d.sync()
   if ctrl:key(d,'Control_L',False)
  await asyncio.sleep(.3)
  after=snap();new=(await layout())[name]['bounds']
  moved=math.dist(rect[:2],new[:2]);assert moved>15,(name,'did not move',rect,new)
  assert after['session']['state']==before['session']['state'],(name,'drag activated a button')
  for field in ['yaw','pitch']:assert abs(before['camera'][field]-after['camera'][field])<.2,(name,'camera moved')
  assert math.dist(before['player']['position'],after['player']['position'])<.05,(name,'player moved')
  checks.append({'window':name,'ctrl':ctrl,'before':rect,'after':new,'cameraAndPlayerStable':True})
  (Q/'report.json').write_text(json.dumps({'complete':False,'checks':checks},indent=2))
  print('PASS: drag',name,'with Ctrl' if ctrl else '',flush=True)
  return new
 d=None;c=None
 try:
  await launch();await reset();await capture('default-square-hotbar')
  els=await layout();slots=[els['slot'+str(i)] for i in range(1,11)]
  assert all(abs(s['bounds'][2]/s['bounds'][3]-1)<.05 for s in slots),[s['bounds'] for s in slots]
  assert all(s['enabled'] for s in slots[:6]) and not any(s['enabled'] for s in slots[6:])
  if os.environ.get('ATHEN_UI_CHECK_STAGE')=='finish':
   checks=json.loads((Q/'report.json').read_text())['checks']
  else:
   await drag('quickbar',(-70,-120),handle='slot5',ctrl=True);await reset()
   await press('slot1');assert 'Water Flask' in snap()['session']['notice']
   await drag('notice',(100,160),local=(70,20));await reset()
   for name,delta,local in [('identity',(120,130),(100,42)),('compass',(-120,150),(150,22)),('objective-box',(-140,150),(90,28)),('chat',(100,-180),(100,24))]:
    await drag(name,delta,local=local);await reset()
   for name,delta in [('quickbar',(-100,-180)),('top-actions',(-160,180)),('interaction',(160,-80)),('key-hints',(-140,-130))]:
    await drag(name,delta,handle=name+'-drag-handle');await reset()
   # Ctrl-drag from a live action must move the bar without opening its menu.
   await drag('quickbar',(-70,-120),handle='slot5',ctrl=True);assert snap()['session']['state']=='Play';await reset()
   await drag('nametag-npc_vex',(80,80),local=(60,12));await reset()
   for shortcut,state in [('5','Inventory'),('6','Notes'),('Escape','Paused')]:
    await tap(shortcut);assert snap()['session']['state']==state
    await drag('modal',(-210,-60),local=(160,38));await capture('dragged-'+state.lower());await tap('Escape');await reset()
   # Restoring defaults is reversible, and dropped windows stay fully on screen.
   await tap('5');await drag('modal',(-1300,-800),local=(160,38));els=await layout();b=els['modal']['bounds'];assert b[0]>=7 and b[1]>=7,b
   await tap('Escape');await reset()
  await reset()
  for name,delta,local in [('identity',(220,150),(100,42)),('quickbar',(100,-170),(100,8))]:await drag(name,delta,local=local)
  expected={n:(await layout())[n]['bounds'] for n in ['identity','quickbar']}
  await capture('custom-layout');await c.command({'action':'quit'});await asyncio.to_thread(p.wait,10)
  await launch();els=await layout()
  for name,b in expected.items():assert math.dist(b[:2],els[name]['bounds'][:2])<2,(name,'position did not persist',b,els[name]['bounds'])
  await capture('restored-layout')
  for width,height in [(1280,720),(1024,768)]:
   await c.command({'action':'resize','width':width,'height':height});await asyncio.sleep(.8);d=focus()
   if snap()['session']['state']=='Paused':await tap('Escape')
   els=await layout();root=els['hud']['bounds']
   for name in ['identity','quickbar']:
    x,y,w,h=els[name]['bounds'];assert x>=0 and y>=0 and x+w<=root[2]+1 and y+h<=root[3]+1,(width,name,'offscreen')
   await capture(f'custom-{width}x{height}')
  # Existing complete city loop uses real keyboard controls and modal focus.
  route=await asyncio.create_subprocess_exec(sys.executable,str(R/'tools/city_loop_check.py'))
  assert await route.wait()==0,'Existing city loop failed'
  await reset();await c.command({'action':'quit'});await asyncio.to_thread(p.wait,10)
  log=(Q/'Player.log').read_text();assert 'Exception:' not in log and 'Unknown pseudo' not in log
  report={'complete':True,'squareSlots':10,'checks':checks,'cityLoop':True,'persistenceAcrossRestart':True,'clampedToScreen':True,'resetUi':True,'responsive':[[1920,1080],[1280,720],[1024,768]]}
  (Q/'report.json').write_text(json.dumps(report,indent=2));print('PASS: square slots, every HUD group + NPC labels + modal dragging, no click/camera leaks, persistence, reset and responsive layouts.')
 finally:
  if p and p.poll() is None:p.terminate();p.wait(timeout=10)
asyncio.run(main())
