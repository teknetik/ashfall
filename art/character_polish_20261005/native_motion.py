"""Matched real-input motion captures; recording is separate from the timing sample."""
import asyncio,json,os,sys,subprocess,time
from pathlib import Path
ROOT=Path('/home/teknetik/code/ao2');sys.path.insert(0,str(ROOT/'unity/tools'))
from lookbook import Run,launch,start_play,summarize
from desktop_input import focus,focus_window,key
async def main():
 out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=False);exe=Path(sys.argv[2]).resolve()
 p=launch(out,exe);run=Run(out);rec=None;report={'exe':str(exe),'clips':[]}
 try:
  await start_play(run,p);await run.command({'action':'timeSet','hour':13});await run.command({'action':'timePause','paused':True})
  report['environment']=run.read('environment.json');await run.command({'action':'settingsSnapshot'});report['settings']=run.read('settings.json');report['resolution']=[run.read('snapshot.json')[k] for k in ['width','height']]
  for side,yaw,button in ([] if '--profile-only' in sys.argv else [('rear',270,'w'),('front',90,'s')]):
   await run.command({'action':'reset'});await run.command({'action':'view','camera':'follow'})
   await run.command({'action':'cameraYaw','yaw':yaw});await run.command({'action':'cameraPitch','pitch':9});await run.command({'action':'cameraBoom','boom':3.6});await asyncio.sleep(1)
   d,w=focus_window()
   rec=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','x11grab','-framerate','30','-window_id',str(w.id),'-i',os.environ.get('DISPLAY',':0'),'-an','-c:v','libx264','-preset','ultrafast','-crf','20','-pix_fmt','yuv420p',str(out/(side+'.mp4'))],stdin=subprocess.PIPE,stderr=(out/(side+'-ffmpeg.log')).open('w'))
   await run.command({'action':'motionStart'});await asyncio.sleep(.6)
   key(d,button,True)
   for i in range(4):
    await asyncio.sleep(.39);await run.capture(side+'-walk-'+str(i))
   key(d,button,False);await asyncio.sleep(.7)
   key(d,button,True);key(d,'Shift_L',True);await asyncio.sleep(1.4);await run.capture(side+'-run')
   key(d,'space',True);await asyncio.sleep(.12);key(d,'space',False);await asyncio.sleep(1.2)
   key(d,button,False);key(d,'Shift_L',False);await asyncio.sleep(.8)
   await run.command({'action':'motionStop'});(out/(side+'-motion.json')).write_text(json.dumps(run.read('motion.json'),indent=1))
   rec.communicate(b'q',timeout=15);rec=None;report['clips'].append(side)
  # Unrecorded, uncapped frame times at the same route/pose in both builds.
  await run.command({'action':'reset'});await run.command({'action':'view','camera':'follow'});await run.command({'action':'cameraYaw','yaw':270});await run.command({'action':'cameraBoom','boom':3.6});await run.command({'action':'cameraPitch','pitch':9});await asyncio.sleep(2)
  await run.command({'action':'profileStart'});d=focus();key(d,'w',True);await asyncio.sleep(4);key(d,'w',False);await run.command({'action':'profileStop'})
  report['walk_profile']=summarize(run.read('profile.json'));report['snapshot']=run.read('snapshot.json');report['passed']=True
 finally:
  if rec and rec.poll() is None:rec.communicate(b'q',timeout=15)
  try:
   d=focus()
   for k in ['w','s','Shift_L','space']:key(d,k,False)
   await run.command({'action':'quit'});p.wait(timeout=20)
  except Exception:
   if p.poll() is None:os.killpg(p.pid,15)
  (out/'motion-report.json').write_text(json.dumps(report,indent=2))
 print(json.dumps({k:v for k,v in report.items() if k not in ['environment','snapshot']},indent=2))
asyncio.run(main())
