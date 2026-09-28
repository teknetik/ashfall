"""Real-input checkpoint checks against the native Linux development player."""
import asyncio,json,os,subprocess,time,shutil,base64
from pathlib import Path
from native_client import Client
from settings_test_input import focus,key,click,window
from Xlib import X
from Xlib.ext import xtest
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ATHEN_CHECKPOINT_EVIDENCE',ROOT/'evidence/checkpoint/20260926/native'));OUT.mkdir(parents=True,exist_ok=True)
async def main():
 recording=None
 report={'passed':False,'checks':[]};env=dict(os.environ,XDG_CONFIG_HOME=str(OUT/'config'))
 video=json.loads((ROOT/'evidence/courtyard/20260908/after-native/settings.json').read_text())['video']
 for vendor,product in [('unknown','unknown'),('Free Column','Athen Hill')]:
  prefs=OUT/'config/unity3d'/vendor/product;prefs.mkdir(parents=True,exist_ok=True)
  encoded=base64.b64encode(json.dumps(video).encode()).decode()
  (prefs/'prefs').write_text('<unity_prefs version_major="1" version_minor="1"><pref name="AthenHill.Settings.v1.QA.Video" type="string">'+encoded+'</pref></unity_prefs>')
 p=subprocess.Popen([str(ROOT/'AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64'),'-force-glcore','-screen-fullscreen','0','-screen-width','1920','-screen-height','1080','-logFile',str(OUT/'Player.log'),'--athen-qa',str(OUT),'--athen-qa-background'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
 (OUT/'pid').write_text(str(p.pid))
 os.environ.update(ATHEN_NATIVE_DIR=str(OUT),ATHEN_NATIVE_PID=str(p.pid))
 def focused():
  d=focus();w=window(d);w.set_input_focus(X.RevertToParent,X.CurrentTime);g=w.get_geometry();xy=d.screen().root.translate_coords(w,0,0);xtest.fake_input(d,X.MotionNotify,x=xy.x+g.width//2,y=xy.y+g.height//2);d.sync();return d
 def snap():return json.loads((OUT/'snapshot.json').read_text())
 async def tap(name,seconds=.12):
  d=focused();key(d,name,True);await asyncio.sleep(seconds);key(d,name,False);await asyncio.sleep(.35)
 async with Client() as c:
  async def cmd(**kw):await c.command(kw);await asyncio.sleep(.35)
  async def capture(name):
   await cmd(action='capture',name=name);await cmd(action='uiSnapshot');shutil.copyfile(OUT/'ui-layout.json',OUT/(name+'-ui.json'));shutil.copyfile(OUT/'snapshot.json',OUT/(name+'-state.json'))
  try:
   for _ in range(1800):
    try:
     d=focus();break
    except RuntimeError:await asyncio.sleep(.05)
   if shutil.which('hyprctl'):
    selector=f'pid:{p.pid}';subprocess.run(['hyprctl','-i','0','dispatch',f'hl.dsp.window.float({{action="set",window="{selector}"}})'],capture_output=True)
   for _ in range(1800):
    if (OUT/'snapshot.json').exists() and snap()['session']['state']=='MainMenu':break
    await asyncio.sleep(.1)
   assert (OUT/'snapshot.json').exists() and snap()['session']['state']=='MainMenu','Main menu never ready'
   await tap('Return')
   # A key left pressed by an aborted XTEST run reaches the focused player as held movement; clear them first.
   d0=focused()
   for k in ['d','Right','a','Left','w','s','Up','Down','Shift_L','Shift_R','Control_L','e','f','space']:key(d0,k,False)
   for _ in range(1800):
    if snap()['session']['state']=='Play':break
    await asyncio.sleep(.1)
   assert snap()['session']['state']=='Play'
   await cmd(action='resize',width=1920,height=1080);await asyncio.sleep(2)
   assert (snap()['width'],snap()['height'])==(1920,1080),snap()
   await cmd(action='timeSet',hour=12);await cmd(action='timePause',paused=True)
   if shutil.which('ffmpeg') and os.environ.get('ATHEN_CHECKPOINT_RECORD','1')!='0':
    focused();wid=window(focus()).id
    recording=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','x11grab','-framerate','20','-window_id',str(wid),'-i',os.environ['DISPLAY'],'-c:v','libx264','-preset','ultrafast','-crf','23','-pix_fmt','yuv420p',str(OUT/'walkthrough.mp4')],stdin=subprocess.PIPE,stderr=(OUT/'video.log').open('wb'),stdout=subprocess.DEVNULL)
   await cmd(action='goto',landmark='checkpoint_approach');await cmd(action='view',camera='follow');await cmd(action='cameraYaw',yaw=270)
   await tap('w',1.3);assert snap()['player']['position'][0]<-60,'Gate route blocked';report['checks'].append('Real W movement through west gate')
   for camera,label in [('cam_berms_gate','gate-matched'),('cam_berms_post','post-matched')]:
    await cmd(action='view',camera=camera);await capture(label)
   await cmd(action='view',camera='cam_checkpoint_player');await capture('checkpoint-day')
   await cmd(action='goto',landmark='checkpoint_ossa');assert 'Ossa' in snap()['interaction']['prompt'];await tap('e');assert snap()['interaction']['npc']=='Warden Ossa';assert snap()['session']['spoken']==[];await capture('ossa-dialogue');await tap('Escape');report['checks'].append('Named Ossa dialogue; no city-objective count pollution')
   await cmd(action='goto',landmark='checkpoint_rell');await tap('e');assert snap()['interaction']['npc']=='Warden Rell';await capture('rell-dialogue');await tap('Escape');report['checks'].append('Second armed Warden dialogue')
   await cmd(action='goto',landmark='checkpoint_board');await cmd(action='view',camera='follow');await cmd(action='cameraYaw',yaw=270);await tap('w',.3);assert 'briefing' in snap()['interaction']['prompt'];await tap('e');assert 'friendly' in snap()['session']['notice'];report['checks'].append('Field briefing board responds to real E input')
   await cmd(action='view',camera='follow');await cmd(action='cameraYaw',yaw=270)
   d=focused()
   for _ in range(10):
    xtest.fake_input(d,X.ButtonPress,4);xtest.fake_input(d,X.ButtonRelease,4);d.sync();await asyncio.sleep(.08)
   await asyncio.sleep(.5);assert snap()['camera']['firstPerson'];await capture('checkpoint-first-person');report['checks'].append('Real wheel zoom reaches first person at checkpoint')
   for _ in range(6):
    xtest.fake_input(d,X.ButtonPress,5);xtest.fake_input(d,X.ButtonRelease,5);d.sync();await asyncio.sleep(.08)
   await cmd(action='goto',landmark='checkpoint_locker');await cmd(action='view',camera='cam_checkpoint_locker');assert 'ARMS LOCKER' in snap()['interaction']['prompt'];await capture('locker-before');await tap('e');assert snap()['combat']['hasPistol'];assert snap()['combat']['step']=='Draw';assert not snap()['combat']['lockerEnabled'];await capture('locker-collected');report['checks'].append('Locker issues pistol once; guidance advances and disappears')
   await tap('7');assert snap()['combat']['Armed'];assert snap()['combat']['step']=='Targets'
   await cmd(action='goto',landmark='checkpoint_range_reset');await tap('e');assert snap()['combat']['step']=='Targets';report['checks'].append('Range reset station responds without bypassing tutorial')
   await cmd(action='goto',landmark='checkpoint_firingline');await cmd(action='view',camera='cam_checkpoint_range');await capture('range-overview')
   await cmd(action='view',camera='cam_checkpoint_target_close');await capture('target-close')
   for i in range(1,4):
    await cmd(action='view',camera=f'cam_checkpoint_plate{i}');await tap('f',.65)
   assert snap()['combat']['targets']==3,snap()['combat'];assert snap()['combat']['step']=='FirstContact';await capture('range-knocked-down');report['checks'].append('Real pistol input knocks down all three replacement plates and advances tutorial')
   # Record original robots at runtime and inspect patrol encounter without changing health or progression.
   await cmd(action='goto',landmark='checkpoint_road');await cmd(action='view',camera='cam_berms_road');await capture('service-road-original-drone')
   await cmd(action='goto',landmark='checkpoint_approach');await cmd(action='view',camera='follow');await cmd(action='cameraYaw',yaw=90);await tap('w',1);assert not snap()['combat']['Armed'];report['checks'].append('Returning inside Ward holsters pistol')
   await cmd(action='goto',landmark='checkpoint_locker');await cmd(action='view',camera='cam_checkpoint_player');await cmd(action='timeSet',hour=21);await capture('checkpoint-night')
   await cmd(action='settingsSnapshot');shutil.copyfile(OUT/'settings.json',OUT/'profile-settings.json')
   await cmd(action='timeSet',hour=12);await cmd(action='view',camera='follow');await cmd(action='cameraYaw',yaw=270)
   if recording and recording.poll() is None:recording.communicate(b'q',timeout=10)
   # Warm the same route and camera directions before sampling frame times.
   for yaw in [270,180,90,0]:await cmd(action='cameraYaw',yaw=yaw);await tap('w',1.8)
   await cmd(action='goto',landmark='checkpoint_locker');await asyncio.sleep(3);await cmd(action='profileStart')
   for yaw in [270,180,90,0]:await cmd(action='cameraYaw',yaw=yaw);await tap('w',1.8);await asyncio.sleep(2)
   await cmd(action='profileStop');await cmd(action='memorySnapshot');await capture('route-end')
   subprocess.run([__import__('sys').executable,str(ROOT/'tools/record_phase1_hardware.py'),str(OUT)],stdout=subprocess.DEVNULL,check=True)
   errors=[line for line in (OUT/'Player.log').read_text().splitlines() if 'Exception:' in line or 'NullReference' in line];assert not errors,errors
   cityenv=dict(os.environ,ATHEN_EVIDENCE=str(OUT/'city-loop'))
   city=await asyncio.create_subprocess_exec(__import__('sys').executable,str(ROOT/'tools/city_loop_check.py'),env=cityenv,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.STDOUT)
   result=await city.communicate();(OUT/'city-loop-output.txt').write_bytes(result[0]);assert city.returncode==0,result[0].decode()
   report['checks'].append('Existing city dialogue, trade, travel and modal-input regression')
   report['passed']=True
  except Exception as e:report['error']=repr(e);raise
  finally:
   if recording and recording.poll() is None:
    recording.communicate(b'q',timeout=10)
   (OUT/'report.json').write_text(json.dumps(report,indent=2));
   try:await cmd(action='quit')
   except Exception:pass
   try:p.wait(timeout=5)
   except subprocess.TimeoutExpired:p.terminate()
asyncio.run(main())
