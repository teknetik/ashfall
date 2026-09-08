"""Exercise native Sound/Video settings through real keyboard and mouse input."""
import asyncio, json, os, pathlib, subprocess, time, shutil
from Xlib import X
from Xlib.ext import xtest
from native_client import Client
from settings_test_input import focus, key, click, window

ROOT=pathlib.Path(__file__).resolve().parents[1]
QA=ROOT/'evidence/settings/20260908/options'
QA.mkdir(parents=True,exist_ok=True)

async def main():
 p=None
 # Isolate Linux preferences, including Unity's own remembered window size.
 config=QA/'config'
 if config.exists():shutil.rmtree(config)
 config.mkdir()
 async def launch(restart=False):
  nonlocal p
  for name in ['snapshot.json','ack.json','command.json','qa-error.json']:(QA/name).unlink(missing_ok=True)
  args=[os.environ.get('ATHEN_SETTINGS_PLAYER',str(ROOT/'AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64')),'-force-glcore','-logFile',str(QA/('restart.log' if restart else 'Player.log')),'--athen-qa',str(QA)]
  if not restart:args+=['-screen-fullscreen','0','-screen-width','1920','-screen-height','1080']
  p=subprocess.Popen(args,env=dict(os.environ,XDG_CONFIG_HOME=str(config)),stdout=open(QA/'launcher.log','w'),stderr=subprocess.STDOUT)
  os.environ.update(ATHEN_NATIVE_DIR=str(QA),ATHEN_NATIVE_PID=str(p.pid))
  (QA/'pid').write_text(str(p.pid))
  for _ in range(300):
   if (QA/'snapshot.json').exists():break
   if p.poll() is not None:raise RuntimeError('Player exited')
   await asyncio.sleep(.2)
  else:raise TimeoutError('No native snapshot')
  d=focus();await asyncio.sleep(1)
  return d
 def snap():return json.loads((QA/'snapshot.json').read_text())
 try:
  d=await launch()
  async def tap(k):
   key(d,k,True);await asyncio.sleep(.06);key(d,k,False);await asyncio.sleep(.15)
  async with Client() as c:
   async def state():
    await c.command({'action':'settingsSnapshot'});return json.loads((QA/'settings.json').read_text())
   async def capture(name):
    await c.command({'action':'uiSnapshot'});shutil.copy(QA/'ui-layout.json',QA/(name+'-layout.json'))
    await c.command({'action':'capture','name':name});await asyncio.sleep(.3)
    print('Captured '+name,flush=True)
   async def activate(name):
    focus()
    for _ in range(90):
     if snap()['session']['focused']==name:await tap('Return');return
     await tap('Tab')
    raise AssertionError('Cannot focus '+name+'; focus='+str(snap()['session']['focused']))
   async def focus_control(name):
    focus()
    for _ in range(90):
     if snap()['session']['focused']==name:return
     await tap('Tab')
    raise AssertionError('Cannot focus '+name)
   async def choose(name,label):
    await focus_control(name);await tap('Return');await tap('Home')
    # Read the actual control choices, then select with real keys.
    await c.command({'action':'uiSnapshot'})
    layout=json.loads((QA/'ui-layout.json').read_text())
    field=next(e for e in layout['elements'] if e['name']==name)
    values={name:field['choices']}
    idx=values[name].index(label)
    for _ in range(idx):await tap('Down')
    await tap('Return');await asyncio.sleep(.3)
   async def slider(name,value):
    await focus_control(name);await tap('Home')
    for _ in range(value):await tap('Right')
   if snap()['session']['state']=='Paused':await tap('Escape')
   await tap('Escape');await activate('settings-button')
   # Mouse input reaches the sliders, not the movable modal behind them.
   await c.command({'action':'uiSnapshot'})
   layout=json.loads((QA/'ui-layout.json').read_text())
   bounds=next(e['bounds'] for e in layout['elements'] if e['name']=='master-volume')
   hud=next(e['bounds'] for e in layout['elements'] if e['name']=='hud')
   scale=snap()['width']/hud[2]
   root=d.screen().root
   w=window(d)
   pos=root.translate_coords(w,0,0)
   x,y,width,height=bounds
   focus();click(d,int(pos.x+(x+217+(width-217)*.5)*scale),int(pos.y+(y+height/2)*scale))
   await asyncio.sleep(.3)
   st=await state();assert .2<st['sound']['master']<.8,st
   assert abs(snap()['audio']['volume']-st['sound']['master'])<.01
   await focus_control('master-volume');await tap('End')
   await focus_control('ambience-volume');await tap('Home')
   sources=snap()['audio']['sources']
   assert all(a['volume']==0 for a in sources if a['group']=='Ambience'),sources
   assert all(a['volume']>0 for a in sources if a['group'] in ['SFX','UI']),sources
   await focus_control('ambience-volume');await tap('End')
   await focus_control('effects-volume');await tap('Home')
   sources=snap()['audio']['sources']
   assert all(a['volume']==0 for a in sources if a['group'] in ['SFX','UI']),sources
   assert all(a['volume']>0 for a in sources if a['group']=='Ambience'),sources
   await focus_control('effects-volume');await tap('End')
   await capture('sound-mouse-and-channels')
   await activate('video-tab')
   await choose('shadow-quality','Off')
   await choose('anti-aliasing','8× MSAA')
   await choose('texture-quality','Half resolution')
   await activate('post-processing')
   await activate('v-sync')
   await capture('video-custom-options')
   await activate('apply-video')
   st=await state()
   assert st['draft']['preset']==3 and st['shadowDistance']==0 and st['msaa']==8 and st['textureLimit']==1 and st['vSync']==1 and not st['postProcessing'],st
   await activate('revert-video')
   await focus_control('frame-limit');await tap('Return');await tap('Home');await tap('Down');await tap('Return')
   await activate('apply-video');st=await state();assert st['frameLimit']==30,st
   await activate('revert-video')
   await choose('window-mode','Fullscreen (borderless)')
   await choose('resolution','1280 × 720')
   await activate('apply-video');await asyncio.sleep(1);focus()
   assert (snap()['width'],snap()['height'])==(1280,720),snap()
   await capture('fullscreen-preview')
   await activate('revert-video')
   # Keep 1024x768 for a 4:3 layout check, then restore defaults for this QA profile.
   await choose('resolution','1024 × 768');await activate('apply-video');await asyncio.sleep(1);await activate('keep-video')
   await capture('video-1024x768')
   await activate('sound-tab');await capture('sound-1024x768')
   await c.command({'action':'settingsSnapshot'})
   st=await state()
   deadline=time.monotonic()+65
   while st['transitions']<1:
    assert time.monotonic()<deadline,'Playlist did not advance'
    await asyncio.sleep(1);focus();st=await state()
   await asyncio.sleep(3.3);st=await state();assert st['track']=='Dust of Alshain',st
   await c.command({'action':'quit'});p.wait(timeout=10)

  issues=[line for file in ['Player.log'] for line in (QA/file).read_text().splitlines() if any(s in line for s in ['Exception:','NullReference','Unknown pseudo','warning: Expected','Could not load'])]
  assert not issues,issues
  report={'complete':True,'mouseSlider':True,'independentAudioChannels':True,'customGraphicsApplied':True,'vSync':True,'frameLimit':True,'borderlessResolutionPreview':True,'layout1024x768':True,'automaticPlaylistAdvance':True,'runtimeIssues':issues}
  (QA/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
 finally:
  if p and p.poll() is None:p.terminate();p.wait(timeout=10)

asyncio.run(main())
