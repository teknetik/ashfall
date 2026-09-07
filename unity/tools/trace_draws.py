"""Count real OpenGL draw submissions independently of Unity's empty counters."""
import asyncio,json,os,pathlib,subprocess,time,sys,signal
R=pathlib.Path(__file__).resolve().parents[1];Q=R/'evidence/U4/gl-trace';Q.mkdir(parents=True,exist_ok=True)
TRACE=pathlib.Path('/tmp/athen-apitrace/athen.trace');WRAPPER='/tmp/athen-apitrace/usr/lib/x86_64-linux-gnu/apitrace/wrappers/glxtrace.so'
async def main():
 original=subprocess.check_output(['xrandr','--current'],text=True)
 mode=next(line.split()[0] for line in original.splitlines() if '*' in line)
 subprocess.run(['xrandr','--output','DP-0','--mode','1920x1080'],check=True)
 for name in ['snapshot.json','ack.json','command.json']:(Q/name).unlink(missing_ok=True)
 env=dict(os.environ,LD_PRELOAD=WRAPPER,TRACE_FILE=str(TRACE));log=open(Q/'player.log','w')
 p=subprocess.Popen([str(R/'AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64'),'-force-glcore','-screen-fullscreen','1','-screen-width','1920','-screen-height','1080','-logFile',str(Q/'Player.log'),'--athen-qa',str(Q)],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 os.environ['ATHEN_NATIVE_DIR']=str(Q);os.environ['ATHEN_NATIVE_PID']=str(p.pid)
 from native_client import Client
 from desktop_input import focus,key
 try:
  deadline=time.monotonic()+60
  while not (Q/'snapshot.json').exists():
   if p.poll() is not None:raise RuntimeError('Traced player exited')
   if time.monotonic()>deadline:raise TimeoutError('No traced player snapshot')
   await asyncio.sleep(.1)
  d=focus();s=json.loads((Q/'snapshot.json').read_text())
  if s['session']['state']=='Paused':key(d,'Escape',True);await asyncio.sleep(.08);key(d,'Escape',False)
  phases=[]
  async with Client() as c:
   for name in ['follow','cam_hill','cam_avenue','cam_gate']:
    await c.command({'action':'view','camera':name});await asyncio.sleep(.5);phases.append({'view':name,'snapshot':json.loads((Q/'snapshot.json').read_text())})
   async def tap(name):
    key(d,name,True);await asyncio.sleep(.06);key(d,name,False);await asyncio.sleep(.15)
   async def sample(name):
    await asyncio.sleep(.5);phases.append({'view':name,'snapshot':json.loads((Q/'snapshot.json').read_text())})
   await c.command({'action':'view','camera':'follow'})
   await c.command({'action':'goto','landmark':'basic_general'});await tap('e');await tap('Return');await sample('shop')
   await tap('Escape');await c.command({'action':'goto','landmark':'lattice_jack'});await tap('e');await sample('grid-transition');await asyncio.sleep(1);await sample('grid')
   await tap('Escape');await tap('Escape');await sample('pause')
   await c.command({'action':'quit'})
  p.wait(timeout=10);(Q/'phases.json').write_text(json.dumps(phases,indent=2))
 finally:
  if p.poll() is None:p.terminate();p.wait(timeout=10)
  log.close();subprocess.run(['xrandr','--output','DP-0','--mode',mode],check=True)
 dump=subprocess.check_output(['/tmp/athen-apitrace/usr/bin/apitrace','dump','--color=never','--grep=^(gl(Draw(Arrays|Elements|RangeElements)|MultiDraw).*|glXSwapBuffers|eglSwapBuffers)$',str(TRACE)],text=True);(Q/'draw-calls.txt').write_text(dump)
 import re,collections
 frames=[];count=0;logical=0
 for line in dump.splitlines():
  if 'SwapBuffers(' in line:frames.append({'apiDrawSubmissions':count,'logicalDraws':logical});count=logical=0
  else:
   count+=1;match=re.search(r'drawcount = (\d+)',line,re.I);logical+=int(match.group(1)) if match else 1
 useful=[f for f in frames if f['apiDrawSubmissions']>10]
 report={'tool':'Ubuntu apitrace 11.1','api':'OpenGL 4.5','resolution':[1920,1080],'frames':len(frames),'cityFrames':len(useful),'drawSubmissionHistogram':dict(collections.Counter(f['apiDrawSubmissions'] for f in useful)),'maxApiDrawSubmissions':max(f['apiDrawSubmissions'] for f in useful),'maxLogicalDraws':max(f['logicalDraws'] for f in useful),'traceFile':str(TRACE),'note':'Separate instrumented run for draw counting only; not FPS evidence. Includes world, actors, shadows and native HUD.'}
 triangles=[];triangle_count=0;unclassified=[]
 for line in dump.splitlines():
  if 'SwapBuffers(' in line:triangles.append(triangle_count);triangle_count=0
  elif 'glDraw' in line:
   count_match=re.search(r'count = (\d+)',line)
   if count_match and 'mode = GL_TRIANGLES' in line:triangle_count+=int(count_match[1])//3
   else:unclassified.append(line)
 report.update(maxSubmittedTriangles=max(triangles),unclassifiedDrawCalls=unclassified)
 (Q/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
asyncio.run(main())
