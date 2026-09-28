"""Diagnostic: native player position/camera after goto checkpoint_approach and a real W walk."""
import asyncio,json,os,subprocess,shutil,base64,sys
from pathlib import Path
from native_client import Client
from settings_test_input import focus,key,window
from Xlib import X
from Xlib.ext import xtest
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(sys.argv[1]);OUT.mkdir(parents=True,exist_ok=True)
async def main():
 env=dict(os.environ,XDG_CONFIG_HOME=str(OUT/'config'))
 video=json.loads((ROOT/'evidence/courtyard/20260908/after-native/settings.json').read_text())['video']
 for vendor,product in [('unknown','unknown'),('Free Column','Athen Hill')]:
  prefs=OUT/'config/unity3d'/vendor/product;prefs.mkdir(parents=True,exist_ok=True)
  (prefs/'prefs').write_text('<unity_prefs version_major="1" version_minor="1"><pref name="AthenHill.Settings.v1.QA.Video" type="string">'+base64.b64encode(json.dumps(video).encode()).decode()+'</pref></unity_prefs>')
 p=subprocess.Popen([str(ROOT/'AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64'),'-force-glcore','-screen-fullscreen','0','-screen-width','1920','-screen-height','1080','-logFile',str(OUT/'Player.log'),'--athen-qa',str(OUT),'--athen-qa-background'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
 os.environ.update(ATHEN_NATIVE_DIR=str(OUT),ATHEN_NATIVE_PID=str(p.pid))
 def focused():
  d=focus();w=window(d);w.set_input_focus(X.RevertToParent,X.CurrentTime);g=w.get_geometry();xy=d.screen().root.translate_coords(w,0,0);xtest.fake_input(d,X.MotionNotify,x=xy.x+g.width//2,y=xy.y+g.height//2);d.sync();return d
 def snap():return json.loads((OUT/'snapshot.json').read_text())
 async def tap(name,seconds=.12):
  d=focused();key(d,name,True);await asyncio.sleep(seconds);key(d,name,False);await asyncio.sleep(.35)
 log=[]
 async with Client() as c:
  async def cmd(**kw):await c.command(kw);await asyncio.sleep(.35)
  try:
   for _ in range(1800):
    try:focus();break
    except RuntimeError:await asyncio.sleep(.05)
   for _ in range(1800):
    if (OUT/'snapshot.json').exists() and snap()['session']['state']=='MainMenu':break
    await asyncio.sleep(.1)
   await tap('Return')
   for _ in range(1800):
    if snap()['session']['state']=='Play':break
    await asyncio.sleep(.1)
   await cmd(action='resize',width=1920,height=1080);await asyncio.sleep(2)
   await cmd(action='timeSet',hour=12);await cmd(action='timePause',paused=True)
   d=focused()
   for k in ['d','Right','a','Left','w','s','Up','Down','Shift_L','Shift_R','Control_L','e','f','space','Return']:key(d,k,False)
   await asyncio.sleep(.5)
   for lm in ['checkpoint_road','checkpoint_approach']:
    await cmd(action='goto',landmark=lm)
    for i in range(6):
     await asyncio.sleep(.25);s_=snap();log.append((lm+' idle %d'%i,s_['player'],s_['camera'],s_['session'].get('focused')))
   log.append(('after goto',snap()['player'],snap()['camera'],snap()['session'].get('focused')))
   await cmd(action='view',camera='follow');await cmd(action='cameraYaw',yaw=270);await asyncio.sleep(.5)
   log.append(('after yaw',snap()['player'],snap()['camera'],snap()['session'].get('focused')))
   await tap('w',.4);log.append(('w .4',snap()['player'],snap()['camera'],snap()['session'].get('focused')))
   await tap('w',.9);log.append(('w .9',snap()['player'],snap()['camera'],snap()['session'].get('focused')))
   await cmd(action='capture',name='probe-end')
  finally:
   (OUT/'probe.json').write_text(json.dumps(log,indent=1))
   try:await cmd(action='quit')
   except Exception:pass
   try:p.wait(timeout=5)
   except subprocess.TimeoutExpired:p.terminate()
asyncio.run(main())
