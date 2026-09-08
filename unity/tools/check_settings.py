"""Exercise native Sound/Video settings through real keyboard and mouse input."""
import asyncio, json, os, pathlib, subprocess, time, shutil
from Xlib import X
from Xlib.ext import xtest
from native_client import Client
from settings_test_input import focus, key, click, window

ROOT=pathlib.Path(__file__).resolve().parents[1]
QA=ROOT/'evidence/settings/20260908/native'
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
   assert snap()['session']['state']=='Settings',snap()
   await capture('sound-initial')
   await activate('reset-sound')
   # Arrow keys adjust a focused volume slider while the character stays still.
   before=snap()['player']['position']
   await focus_control('music-volume');await tap('Home')
   assert (await state())['sound']['music']==0,await state()
   await tap('End');await tap('Left')
   assert abs((await state())['sound']['music']-.99)<.001
   await activate('mute-all');assert snap()['audio']['volume']==0
   await activate('mute-all')
   await activate('test-effect');await activate('next-track');await asyncio.sleep(3.4)
   assert (await state())['track']=='Dust of Alshain',await state()
   assert snap()['player']['position']==before
   assert (await state())['timeScale']==0
   await capture('sound')
   await activate('video-tab');await capture('video-initial')
   await focus_control('resolution');await tap('Return');await tap('Escape')
   assert snap()['session']['state']=='Settings','Escape on dropdown must stay in Settings'
   await c.command({'action':'uiSnapshot'})
   resolution_field=next(e for e in json.loads((QA/'ui-layout.json').read_text())['elements'] if e['name']=='resolution')
   assert '3840 × 2160' in resolution_field['choices'],resolution_field

   await choose('graphics-preset','Low')
   assert (await state())['draft']['preset']==0,await state()
   await activate('apply-video');await capture('video-confirm')
   st=await state();assert st['previewing'] and st['msaa']==1 and st['renderScale']==.75,st
   await tap('Escape');st=await state();assert not st['previewing'] and st['video']['preset']==2,st
   # Use resolution dropdown to request 1280x720, confirm, then verify persistence.
   await choose('resolution','1280 × 720')
   await choose('graphics-preset','Medium')
   await activate('apply-video');await asyncio.sleep(1);d=focus()
   await activate('keep-video');await asyncio.sleep(.5)
   st=await state();assert (snap()['width'],snap()['height'])==(1280,720),snap()
   assert st['video']['preset']==1 and st['msaa']==2,st
   await capture('video-1280x720')
   # Timeout works while gameplay time is stopped.
   await choose('graphics-preset','Low');await activate('apply-video')
   for _ in range(17):await asyncio.sleep(1)
   focus()
   st=await state();assert not st['previewing'] and st['video']['preset']==1 and st['msaa']==2,st
   await capture('video-timeout')
   await tap('Escape');assert snap()['session']['state']=='Paused'
   await tap('Escape');assert snap()['session']['state']=='Play'
   key(d,'w',True);await asyncio.sleep(.4);key(d,'w',False);await asyncio.sleep(.2)
   assert snap()['player']['position']!=before
   await c.command({'action':'quit'});p.wait(timeout=10)
  d=await launch(True)
  async with Client() as c:
   await c.command({'action':'settingsSnapshot'});st=json.loads((QA/'settings.json').read_text())
   assert st['video']['preset']==1 and (snap()['width'],snap()['height'])==(1280,720),st
   assert abs(st['sound']['music']-.99)<.001,st
   await c.command({'action':'capture','name':'restarted-1280x720'});await asyncio.sleep(.3)
   await c.command({'action':'quit'});p.wait(timeout=10)
  issues=[line for file in ['Player.log','restart.log'] for line in (QA/file).read_text().splitlines() if any(s in line for s in ['Exception:','NullReference','Unknown pseudo','warning: Expected','Could not load'])]
  assert not issues,issues
  report={'complete':True,'soundChannels':True,'playlistCrossfade':True,'keyboardNavigation':True,'movementBlockedInSettings':True,'lowAndMediumPresetsApplied':True,'escapeRevert':True,'timeoutRevertWhilePaused':True,'resolutionChanged':[1280,720],'settingsPersistAcrossRestart':True,'gameplayResumes':True,'runtimeIssues':issues}
  (QA/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
 finally:
  if p and p.poll() is None:p.terminate();p.wait(timeout=10)

asyncio.run(main())
