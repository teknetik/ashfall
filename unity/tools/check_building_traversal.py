"""Native building-pass route timing, including an unmeasured warm-up traversal.

Run with the authoring apps closed. Real input follows the retained district route;
profile data is not a visual acceptance decision or a whole-phase qualification.
"""
import asyncio,ast,json,os,statistics,sys,time
from pathlib import Path
from native_client import Client
from desktop_input import focus
ROOT=Path(__file__).resolve().parent
OUT=Path(os.environ['ATHEN_NATIVE_DIR'])
def percentile(values,p):
 v=sorted(values);i=(len(v)-1)*p;a=int(i);b=min(a+1,len(v)-1);return v[a]+(v[b]-v[a])*(i-a)
def summarize(frames):
 dt=[v['dt']*1000 for v in frames]
 result=dict(frames=len(dt),seconds=sum(dt)/1000,averageFps=len(dt)*1000/sum(dt),p50Ms=percentile(dt,.5),p95Ms=percentile(dt,.95),p99Ms=percentile(dt,.99),maxMs=max(dt),hitchesOver33ms=sum(x>33.33 for x in dt),hitchesOver50ms=sum(x>50 for x in dt))
 for key in ['mainMs','renderMs','cpuMs','gpuMs','draws','tris','batches','setPass']:
  values=[v[key] for v in frames if v.get(key,-1)>0]
  result[key]=dict(samples=len(values),mean=statistics.mean(values),p95=percentile(values,.95),max=max(values))if values else None
 return result
async def main():
 # Existing routes have been exercised with the current collision layout.
 tree=ast.parse((ROOT/'check_salvage.py').read_text());route=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='ROUTE'for t in n.targets))
 (OUT/'all-building-route.json').write_text(json.dumps(route,indent=2))
 c=Client();focus();await c.command({'action':'settingsSnapshot'})
 settings=json.loads((OUT/'settings.json').read_text());assert settings['renderScale']==1
 video=settings.get('video',{})
 assert video.get('vSync')is False and video.get('frameLimit')==0,settings
 report=dict(complete=False,scope=__doc__,settings=settings,utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
 async def traverse(name):
  focus();p=await asyncio.create_subprocess_exec(sys.executable,str(ROOT/'walk_route.py'),str(OUT/'all-building-route.json'),name);assert await p.wait()==0,name+' failed'
 try:
  await c.command({'action':'view','camera':'follow'});await c.command({'action':'timeReset'});await c.command({'action':'timePause','paused':True});await c.command({'action':'timeState'})
  report['lighting']=json.loads((OUT/'time-state.json').read_text())
  video=None
  if '--record-warmup' in sys.argv:
   from Xlib import X
   d=focus();root=d.screen().root;window=None
   for wid in root.get_full_property(d.intern_atom('_NET_CLIENT_LIST'),X.AnyPropertyType).value:
    w=d.create_resource_object('window',wid);pid=w.get_full_property(d.intern_atom('_NET_WM_PID'),X.AnyPropertyType)
    if pid is not None and int(pid.value[0])==int(os.environ['ATHEN_NATIVE_PID']):window=w;break
   assert window is not None,'Native player window missing'
   origin=root.translate_coords(window,0,0);geometry=window.get_geometry();assert (geometry.width,geometry.height)==(1920,1080)
   path=OUT/'store-walkthrough.mp4';assert not path.exists(),'Preserve prior walkthrough evidence'
   video=await asyncio.create_subprocess_exec('ffmpeg','-hide_banner','-loglevel','error','-f','x11grab','-framerate','30','-video_size','1920x1080','-i',os.environ.get('DISPLAY',':0')+f'+{origin.x},{origin.y}','-t','240','-c:v','libx264','-preset','ultrafast','-crf','22','-pix_fmt','yuv420p',str(path),stdin=asyncio.subprocess.PIPE)
  try:
   print('Unmeasured route warm-up',flush=True);await traverse('warmup-route.json')
  finally:
   if video:
    await video.communicate(b'q');assert video.returncode==0,'Walkthrough encoder failed'
  if video:
   report['warmupVideo']='store-walkthrough.mp4'
   report['videoNote']='Only the unmeasured warm-up was recorded; ffmpeg exited before the measured traversal.'
   await asyncio.sleep(2)
  report['settingsBeforeWarmup']=report.pop('settings')
  await c.command({'action':'settingsSnapshot'});report['settings']=json.loads((OUT/'settings.json').read_text());assert report['settings']['timeScale']==1
  print('Measured route begins',flush=True);focus();await c.command({'action':'profileStart'})
  await traverse('measured-route.json');await c.command({'action':'profileStop'})
  data=json.loads((OUT/'profile.json').read_text());(OUT/'traversal-frames.json').write_text(json.dumps(data))
  report['allFrames']=summarize(data);moving=[v for v in data if v['state']=='Play' and v['speed']>1];report['movingFrames']=summarize(moving)
  s=report['allFrames'];report['meetsCurrentFrameTimeTarget']=s['averageFps']>=60 and s['p99Ms']<=16.67
  report['counterNotes']='Nonpositive timing counters are unavailable and reported as null. Main-thread time includes waits. Resident textures are unavailable. Draw and triangle counters include renderer passes and are not visible geometry.'
  report['complete']=True;print(json.dumps(report['allFrames']),flush=True)
 finally:
  (OUT/'traversal-performance.json').write_text(json.dumps(report,indent=2))
  await c.command({'action':'timeReset'})
asyncio.run(main())
