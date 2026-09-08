"""Native UI acceptance: real keyboard/mouse, screenshots, responsive geometry and gameplay."""
import asyncio, json, os, pathlib, re, subprocess, sys, time, shutil
from Xlib import X
from Xlib.ext import xtest
from native_client import Client
from desktop_input import focus, key, click

R=pathlib.Path(__file__).resolve().parents[1]
QA=pathlib.Path(os.environ.get('ATHEN_UI_EVIDENCE',R/'evidence/ui/20260908/native'))
QA.mkdir(parents=True,exist_ok=True)

async def main():
 original=subprocess.check_output(['xrandr','--current'],text=True)
 mode=next(line.split()[0] for line in original.splitlines() if '*' in line)
 subprocess.run(['xrandr','--output','DP-0','--mode','1920x1080'],check=True)
 for name in ['snapshot.json','environment.json','ack.json','qa-error.json','command.json']:(QA/name).unlink(missing_ok=True)
 p=subprocess.Popen([str(R/'AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64'),'-force-glcore','-screen-fullscreen','1','-screen-width','1920','-screen-height','1080','-logFile',str(QA/'Player.log'),'--athen-qa',str(QA)],stdout=open(QA/'launcher.log','w'),stderr=subprocess.STDOUT)
 os.environ.update(ATHEN_NATIVE_DIR=str(QA),ATHEN_NATIVE_PID=str(p.pid),ATHEN_EVIDENCE=str(QA))
 (QA/'pid').write_text(str(p.pid))
 try:
  for _ in range(300):
   if (QA/'snapshot.json').exists():break
   if p.poll() is not None:raise RuntimeError('Player exited')
   await asyncio.sleep(.2)
  else:raise TimeoutError('No native snapshot')
  d=focus()
  async def tap(k,t=.08):
   key(d,k,True)
   try:await asyncio.sleep(t)
   finally:key(d,k,False)
   await asyncio.sleep(.17)
  def snapshot():return json.loads((QA/'snapshot.json').read_text())
  async with Client() as c:
   async def capture(name):
    await c.command({'action':'uiSnapshot'});shutil.copy(QA/'ui-layout.json',QA/(name+'-layout.json'))
    await c.command({'action':'capture','name':name});await asyncio.sleep(.35)
    print('Captured',name,flush=True)
   async def activate(name):
    for _ in range(45):
     if snapshot()['session']['focused']==name:await tap('Return');return
     await tap('Tab')
    raise AssertionError('Could not focus '+name)
   async def expect(state):
    await asyncio.sleep(.2)
    assert snapshot()['session']['state']==state,snapshot()['session']
   await asyncio.sleep(2)
   if snapshot()['session']['state']=='Paused':await tap('Escape')
   await capture('hud-follow')
   await c.command({'action':'view','camera':'cam_avenue'});await capture('hud-1080p')
   await c.command({'action':'profileStart'});await asyncio.sleep(3);await c.command({'action':'profileStop'});shutil.copy(QA/'profile.json',QA/'avenue-profile.json')
   # Pointer clicks must still reach nested illustrated buttons and block camera drags.
   d=focus()
   if snapshot()['session']['state']=='Paused':await tap('Escape')
   layout=json.loads((QA/'ui-layout.json').read_text());bounds=next(e['bounds'] for e in layout['elements'] if e['name']=='slot1')
   x,y,w,h=bounds;click(d,int(x+w/2),int(y+h/2));await asyncio.sleep(.3)
   assert 'Water Flask' in snapshot()['session']['notice'],snapshot()['session']
   pointer=json.loads((QA/'pointer.json').read_text());assert pointer['overUi'],pointer
   await capture('hotbar-click')
   await c.command({'action':'view','camera':'follow'})
   loop=await asyncio.create_subprocess_exec(sys.executable,str(R/'tools/city_loop_check.py'))
   assert await loop.wait()==0,'Existing city loop failed'
   # All menus are visited with real keys, including the long credits scroll.
   for k,state,name in [('5','Inventory','inventory'),('6','Notes','notes'),('Escape','Paused','pause')]:
    await tap(k);await expect(state);await capture(name);await tap('Escape')
   await tap('Escape');await activate('credits-button');await expect('Credits');await capture('credits')
   await c.command({'action':'uiSnapshot'});assert not any(e['enabled'] for e in json.loads((QA/'ui-layout.json').read_text())['elements'] if e['name'] in ['slot1','inventory-button','hint-pause'])
   await tap('Escape');await c.command({'action':'goto','landmark':'basic_general'});await tap('e');await activate('choice0');await expect('Shop');await capture('shop-final');await tap('Escape')
   for camera in ['cam_hill','cam_gate']:
    await c.command({'action':'view','camera':camera});await capture(camera)
   await c.command({'action':'view','camera':'cam_avenue'})
   for width,height in [(1280,720),(1024,768)]:
    await c.command({'action':'resize','width':width,'height':height});await asyncio.sleep(1);d=focus()
    if snapshot()['session']['state']=='Paused':await tap('Escape')
    await capture(f'hud-{width}x{height}')
    await tap('5');await expect('Inventory');await capture(f'inventory-{width}x{height}');await tap('Escape')
   await c.command({'action':'quit'});await asyncio.sleep(1)
  log=(QA/'Player.log').read_text()
  issues=[l for l in log.splitlines() if any(x in l for x in ['Exception:','Unknown pseudo','warning: Expected','Could not load','No font asset'])]
  assert not issues,issues
  samples=json.loads((QA/'avenue-profile.json').read_text());frames=[s for s in samples if s['dt']>0]
  layout_checks=[]
  for path in QA.glob('hud-*-layout.json'):
   layout=json.loads(path.read_text());els={e['name']:e for e in layout['elements'] if e['name']}
   heading=els['chat-heading']['bounds'];scroll=els['log-scroll']['bounds'];footer=els['chat-footer']['bounds']
   assert heading[1]+heading[3]<=scroll[1]+1,(path,'log header overlap')
   assert scroll[1]+scroll[3]<=footer[1]+1,(path,'log footer overlap')
   root=els['hud']['bounds']
   if layout['width']<1500 or layout['height']<900:assert els['log']['fontSize']>=20 and els['credits']['fontSize']>=20,(path,'small-window type')
   for name in ['identity','compass','objective-box','top-actions','chat','hotbar','key-hints']:
    x,y,w,h=els[name]['bounds'];assert x>=0 and y>=0 and x+w<=root[2]+1 and y+h<=root[3]+1,(path,name,'outside window')
   for a,b in [('chat','hotbar'),('hotbar','key-hints'),('identity','compass'),('compass','objective-box'),('objective-box','top-actions')]:
    x,y,w,h=els[a]['bounds'];xx,yy,ww,hh=els[b]['bounds'];assert x+w<=xx+1 or xx+ww<=x+1 or y+h<=yy+1 or yy+hh<=y+1,(path,a,b,'overlap')
   layout_checks.append(path.name)
  report={'complete':True,'cityLoop':json.loads((QA/'city-loop.json').read_text())['complete'],'screenshots':sorted(x.name for x in QA.glob('*.png')),'layoutChecks':layout_checks,'avenueFps':len(frames)/sum(s['dt'] for s in frames),'drawsMax':max(s['draws'] for s in frames) or None,'renderPassTrianglesMax':max(s['tris'] for s in frames),'counterNote':'Unity draw-call recorder returns zero on this runtime; triangle count includes repeated render passes, not unique visible geometry.','runtimeIssues':issues}
  (QA/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
 finally:
  if p.poll() is None:p.terminate();p.wait(timeout=10)
  subprocess.run(['xrandr','--output','DP-0','--mode',mode],check=True)

asyncio.run(main())
