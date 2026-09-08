"""Launch the saved Linux player at 1080p and run the same real keyboard checks."""
import asyncio,json,os,pathlib,subprocess,time,sys,statistics,signal,re
def interrupted(*args):raise KeyboardInterrupt("Native QA interrupted")
signal.signal(signal.SIGTERM,interrupted)
R=pathlib.Path(__file__).resolve().parents[1];QA=R/'evidence/U5/native';QA.mkdir(parents=True,exist_ok=True)
async def main():
 original=subprocess.check_output(['xrandr','--current'],text=True)
 # The connected QA display supports 1080p. Restore its prior mode after testing.
 active=next((line.split()[0] for line in original.splitlines() if '*' in line),None)
 mode=active or 'x'.join(re.search(r'current (\d+) x (\d+)',original).groups())
 changed_mode=mode!='1920x1080'
 if changed_mode:subprocess.run(['xrandr','--output','DP-0','--mode','1920x1080'],check=True)
 for name in ['snapshot.json','environment.json','ack.json','qa-error.json','command.json']:(QA/name).unlink(missing_ok=True)
 (QA/'qualification.json').write_text(json.dumps({'complete':False}))
 log=open(QA/'launcher.log','w')
 p=subprocess.Popen([str(R/'AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64'),'-force-glcore','-screen-fullscreen','1','-screen-width','1920','-screen-height','1080','-logFile',str(QA/'Player.log'),'--athen-qa',str(QA)],stdout=log,stderr=subprocess.STDOUT)
 os.environ.update(ATHEN_NATIVE_DIR=str(QA),ATHEN_NATIVE_PID=str(p.pid),ATHEN_EVIDENCE=str(QA));(QA/'pid').write_text(str(p.pid))
 from native_client import Client
 try:
  deadline=time.monotonic()+60
  while time.monotonic()<deadline:
   if p.poll() is not None:raise RuntimeError('Player exited during launch: '+str(p.returncode))
   if (QA/'snapshot.json').exists():break
   await asyncio.sleep(.2)
  else:raise TimeoutError('No player snapshot')
  await asyncio.sleep(5)
  s=json.loads((QA/'snapshot.json').read_text());assert (s['width'],s['height'])==(1920,1080),s
  assert s['triangles']>1000,'Native renderer is not drawing the city'
  startup=(QA/'Player.log').read_text()
  assert 'Exception:' not in startup,'Native startup exception; inspect Player.log'
  async with Client() as c:
   await c.command({'action':'capture','name':'startup'});await asyncio.sleep(.4)
   await c.command({'action':'profileStart'})
   route=await asyncio.create_subprocess_exec(sys.executable,str(R/'tools/walk_route.py'));assert await route.wait()==0,'Native walking route failed'
   await c.command({'action':'profileStop'})
   await c.command({'action':'capture','name':'route-lattice'})
   for name in ['cam_hill','cam_avenue','cam_gate','character','portrait']:
    await c.command({'action':'view','camera':name});await asyncio.sleep(.5);await c.command({'action':'capture','name':name})
   await c.command({'action':'view','camera':'follow'})
   loop=await asyncio.create_subprocess_exec(sys.executable,str(R/'tools/city_loop_check.py'));assert await loop.wait()==0,'Native city loop failed'
   await c.command({'action':'quit'});await asyncio.sleep(2)
  samples=json.loads((QA/'profile.json').read_text());walking=[x for x in samples if x['speed']>1 and x['state']=='Play']
  def stats(xs):
   xs=sorted(xs);return {'min':xs[0],'mean':statistics.mean(xs),'p50':xs[len(xs)//2],'p95':xs[int(len(xs)*.95)],'p99':xs[int(len(xs)*.99)],'max':xs[-1]}
  report={'frames':len(samples),'walkingFrames':len(walking),'environment':json.loads((QA/'environment.json').read_text()),'walking':{key:stats([x[key] for x in walking]) for key in ['dt','draws','tris','batches','setPass','mainMs','renderMs','cpuMs','gpuMs']},'averageWalkingFPS':len(walking)/sum(x['dt'] for x in walking),'complete':True}
  (QA/'qualification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
 finally:
  if p.poll() is None:p.terminate();p.wait(timeout=10)
  log.close()
  if changed_mode:subprocess.run(['xrandr','--output','DP-0','--mode',mode],check=True)
asyncio.run(main())
