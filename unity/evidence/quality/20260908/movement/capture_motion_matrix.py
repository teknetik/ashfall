"""Native movement visual evidence matrix. Creates actual clips/manifests only when run.
Requires root-installed MotionReviewSetup cameras and an opted-in native development player.
Run with ATHEN_NATIVE_PID and ATHEN_NATIVE_DIR; --section narrows a revision run.
No build, Editor, source asset or scene mutation. No animation-quality auto-acceptance.
"""
import argparse,asyncio,datetime,hashlib,json,math,os,pathlib,re,sys,time
HERE=pathlib.Path(__file__).resolve().parent;UNITY=HERE.parents[3]
sys.path.insert(0,str(UNITY/'tools'))
from native_client import Client
from desktop_input import focus,key
from Xlib import X
from Xlib.ext import xtest
PLAN=json.loads((HERE/'capture-plan.json').read_text());QA=pathlib.Path(os.environ['ATHEN_NATIVE_DIR'])

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb')as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def length(v):return math.sqrt(sum(x*x for x in v))
def sub(a,b):return [x-y for x,y in zip(a,b)]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def segment_distance(p,a,b):
 v=sub(b,a);t=max(0,min(1,dot(sub(p,a),v)/max(1e-6,dot(v,v))));return length(sub(p,[x+t*y for x,y in zip(a,v)]))

class Capture:
 def __init__(self,args):
  self.args=args;self.c=Client();self.d=focus();self.shot=None;self.video=None
  self.out=QA/('motion-matrix-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));self.out.mkdir()
  self.manifest={'complete':False,'visualAcceptance':'Unreviewed; automated recording is not an animation-quality decision','startedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'section':args.section,'actorFilter':args.actor,'talkCompanion':args.talk_companion,'shots':[],'plan':PLAN}
 def require_focus(self):
  root=self.d.screen().root;active=root.get_full_property(self.d.intern_atom('_NET_ACTIVE_WINDOW'),X.AnyPropertyType)
  if active is None or not active.value[0]:raise RuntimeError('Native capture lost window focus')
  window=self.d.create_resource_object('window',int(active.value[0]));pid=window.get_full_property(self.d.intern_atom('_NET_WM_PID'),X.AnyPropertyType)
  if pid is None or int(pid.value[0])!=int(os.environ['ATHEN_NATIVE_PID']):raise RuntimeError('Native capture lost window focus; no further input sent')
 def snap(self):return json.loads((QA/'snapshot.json').read_text())
 def event(self,name,**data):
  if self.shot is not None:self.shot['events'].append({'event':name,'monotonic':time.monotonic(),'videoOffsetEstimate':time.monotonic()-self.shot['captureStartMonotonic'],**data})
 async def command(self,action,**data):await self.c.command({'action':action,**data})
 async def observe(self,seconds,actors=True):
  end=time.monotonic()+seconds
  while time.monotonic()<end:
   self.require_focus()
   s=self.snap()
   if self.shot is not None:self.shot['snapshots'].append({'videoOffsetEstimate':time.monotonic()-self.shot['captureStartMonotonic'],'snapshot':s})
   if actors:
    await self.command('actorSnapshot');a=json.loads((QA/'actors.json').read_text())
    if self.shot is not None:self.shot['actorSamples'].append({'videoOffsetEstimate':time.monotonic()-self.shot['captureStartMonotonic'],'actors':a})
   await asyncio.sleep(max(0,min(.24,end-time.monotonic())))
 async def tap(self,name,duration=.085):
  self.require_focus()
  self.event('keyDown',key=name);key(self.d,name,True)
  try:await asyncio.sleep(duration)
  finally:key(self.d,name,False);self.event('keyUp',key=name)
 async def hold(self,keys,seconds):
  self.require_focus()
  for k in keys:key(self.d,k,True);self.event('keyDown',key=k)
  try:await self.observe(seconds)
  finally:
   for k in keys:key(self.d,k,False);self.event('keyUp',key=k)
 async def jump(self,keys=(),run=False):
  self.require_focus()
  held=list(keys)+(['Shift_L']if run else [])
  for k in held:key(self.d,k,True);self.event('keyDown',key=k)
  try:
   if held:await self.observe(.22)
   await self.tap('space');await self.observe(.92)
  finally:
   for k in held:key(self.d,k,False);self.event('keyUp',key=k)
  await self.observe(.65)
 async def grounded(self,timeout=3):
  end=time.monotonic()+timeout
  while time.monotonic()<end:
   if self.snap()['player']['grounded']:return
   await asyncio.sleep(.025)
  raise AssertionError('Ground contact did not return')
 async def normal(self):
  if self.snap()['session']['state']!='Play':await self.tap('Escape');await self.observe(.25,False)
  assert self.snap()['session']['state']=='Play',self.snap()['session']
 async def setup(self,landmark='west_gate',camera='follow',yaw=None):
  await self.normal();await self.command('goto',landmark=landmark)
  if landmark=='west_gate'and camera!='follow':
   await self.command('view',camera='follow');await self.command('cameraYaw',yaw=-90)
   key(self.d,'w',True)
   try:await asyncio.sleep(.4)
   finally:key(self.d,'w',False)
   await self.command('goto',landmark=landmark)
  await self.command('view',camera=camera)
  if yaw is not None:await self.command('cameraYaw',yaw=yaw)
  await self.observe(.4,False)
 async def start(self,name,**meta):
  self.shot={'name':name,'events':[],'snapshots':[],'actorSamples':[],'complete':False,'qualityDecision':'Unreviewed','captureStartMonotonic':time.monotonic(),'captureStartUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),**meta}
  path=self.out/(name+'.mp4');self.shot['file']=path.name
  self.video=await asyncio.create_subprocess_exec('ffmpeg','-hide_banner','-loglevel','error','-y','-f','x11grab','-framerate','60','-video_size','1920x1080','-i',os.environ.get('DISPLAY',':0')+f'+{self.origin.x},{self.origin.y}','-c:v','libx264','-preset','ultrafast','-crf','20','-pix_fmt','yuv420p',str(path),stdin=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
  await self.command('motionStart');await self.observe(.6)
 async def finish(self,success=True,error=None):
  if self.shot is None:return
  for k in ['w','a','s','d','space','Shift_L']:key(self.d,k,False)
  self.event('captureEnding');motion=[]
  try:
   await self.command('motionStop')
   motion=json.loads((QA/'motion.json').read_text());(self.out/(self.shot['name']+'-physics.json')).write_text(json.dumps(motion,indent=2))
  except Exception as cleanup_error:
   success=False;self.shot['motionCleanupError']=str(cleanup_error)
  if self.video.returncode is None:
   try:self.video.stdin.write(b'q');await self.video.stdin.drain()
   except (BrokenPipeError,ConnectionResetError):pass
  try:_,stderr=await asyncio.wait_for(self.video.communicate(),15)
  except asyncio.TimeoutError:
   self.video.kill();_,stderr=await self.video.communicate();success=False;self.shot['encoderCleanupError']='Encoder required termination after 15 seconds'
  self.shot['encoderExit']=self.video.returncode
  if stderr:self.shot['encoderLog']=stderr.decode(errors='replace')
  path=self.out/self.shot['file']
  probe=await asyncio.create_subprocess_exec('ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path),stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
  stdout,err=await probe.communicate();self.shot['ffprobeExit']=probe.returncode
  if probe.returncode==0:
   self.shot['ffprobe']=json.loads(stdout);self.shot['sha256']=sha(path);self.shot['bytes']=path.stat().st_size
   self.shot['durationSeconds']=float(self.shot['ffprobe']['format']['duration'])
   self.shot['durationSufficient']=self.shot['durationSeconds']>=self.shot.get('minimumVideoSeconds',1.8)
   pts=await asyncio.create_subprocess_exec('ffprobe','-v','error','-select_streams','v:0','-show_entries','frame=best_effort_timestamp_time,pkt_duration_time,key_frame','-of','json',str(path),stdout=asyncio.subprocess.PIPE)
   encoded_times,_=await pts.communicate();encoded_frames=json.loads(encoded_times).get('frames',[]);index=self.out/(self.shot['name']+'-frame-times.csv')
   index.write_text('frame_index,pts_seconds,duration_seconds,key_frame\n'+''.join(str(i)+','+f.get('best_effort_timestamp_time','')+','+f.get('pkt_duration_time','')+','+str(f.get('key_frame',''))+'\n'for i,f in enumerate(encoded_frames)));self.shot['frameTimestampIndex']=index.name;self.shot['encodedFrameCount']=len(encoded_frames)
  else:self.shot['ffprobeError']=err.decode()
  self.shot['physicsFile']=self.shot['name']+'-physics.json';self.shot['physicsFrames']=len(motion);self.shot['acceptedJumps']=sum(r['JumpStarted']for r in motion);self.shot['phases']=list(dict.fromkeys(r['phase']for r in motion))
  self.shot['behaviorEvidenceComplete']=all(p in self.shot['phases']for p in self.shot.get('requiredPhases',[])) and ('expectedJumps'not in self.shot or self.shot['acceptedJumps']==self.shot['expectedJumps']) and (not self.shot.get('expectedGroundedFinal')or bool(motion and motion[-1]['Grounded']))
  self.shot['complete']=success and self.video.returncode==0 and probe.returncode==0 and self.shot.get('durationSufficient',False) and self.shot['behaviorEvidenceComplete']
  if error:self.shot['error']=str(error)
  self.shot['timingNote']='Events contain actual monotonic key/command times. videoOffsetEstimate is relative to ffmpeg process launch, not a claimed frame-exact actuation time. Use named clip and ffprobe PTS for exact defect frame/time citations.'
  detail=self.out/(self.shot['name']+'.json');detail.write_text(json.dumps(self.shot,indent=2))
  self.manifest['shots'].append({k:v for k,v in self.shot.items()if k not in ['actorSamples','snapshots','ffprobe']});self.manifest['shots'][-1]['details']=detail.name
  self.shot=None;self.video=None;self.save()
 def save(self):
  (self.out/'manifest.json').write_text(json.dumps(self.manifest,indent=2))
  lines=['# Native movement clip index','','These files were recorded in this run. Visual quality remains unreviewed. Exact encoded frame times are in the linked CSVs; input-event offsets in each JSON are approximate relative to process launch.','','| Clip | Duration | Recording complete | Timestamp/details |','| --- | ---: | --- | --- |']
  for s in self.manifest['shots']:
   lines.append('| ['+s['name']+']('+str(self.out/s['file'])+') | '+str(round(s.get('durationSeconds',0),3))+' s | '+str(s['complete'])+' | [Details]('+str(self.out/s['details'])+') · [Frame PTS]('+str(self.out/s.get('frameTimestampIndex',''))+') |')
  (self.out/'review-index.md').write_text('\n'.join(lines)+'\n')
 async def shot_action(self,name,fn,**meta):
  await self.start(name,**meta)
  try:await fn();await self.finish()
  except Exception as e:await self.finish(False,e);raise
 async def jumps(self):
  for view,keys in PLAN['jumpInputs'].items():
   for kind in ['standing','running','repeat']:
    await self.setup(camera=('cam_motion_jump_'if kind=='running'else'cam_motion_stand_')+view)
    async def action(kind=kind,keys=keys):
     if kind=='running':await self.jump(keys,True)
     elif kind=='standing':await self.jump()
     else:
      await self.tap('space');await asyncio.sleep(.25);await self.grounded();await self.tap('space');await self.observe(1.5)
    await self.shot_action('jump-'+view+'-'+kind,action,view=view,scenario=kind,landmark='west_gate',requiredPhases=['Takeoff','Rising','Falling','Landing','Grounded'],expectedJumps=2 if kind=='repeat'else 1,expectedGroundedFinal=True)
  for view in ['front','side']:
   await self.setup('hill_tree','cam_motion_edge_'+view)
   # Camera-projected keys are recorded explicitly. These are capture paths to validate, never collider edits.
   async def edge():
    await self.hold(['s']if view=='front'else['d'],2.5);await self.observe(.8)
   await self.shot_action('edge-'+view,edge,view=view,scenario='walk-off-edge',landmark='hill_tree',requiredPhases=['Falling','Landing','Grounded'],expectedJumps=0,expectedGroundedFinal=True)
 async def guards(self):
  for guard in PLAN['guards']:
   if self.args.actor and guard['actor']not in self.args.actor:continue
   for view in ['full','close']:
    await self.setup(guard['landmark'],guard[view+'Camera'])
    async def action(guard=guard):
     self.event('idleLoopsStart',expectedClip=self.assigned_guard_clip(guard,'idle'),minimumLoops=3)
     await self.observe(guard['idleSeconds']*3+.8)
     self.check_guard_window(guard,'idle',guard['idleSeconds']*3)
     await self.tap('e');await self.observe(.45);assert self.snap()['session']['state']=='Dialogue',self.snap()['session']
     assert guard['actor']in self.snap()['session']['spoken'],self.snap()['session']
     if self.args.talk_companion:
      await self.command('reviewHud',hidden=True)
      self.event('hudHiddenVisualCompanion',state=json.loads((QA/'visual-review-state.json').read_text()),note='Actual E-key dialogue continues with normal modal blocking; HUD opacity hidden solely to expose animation. Normal-UI playback evidence is separate.')
     self.event('talkLoopsStart',expectedClip=self.assigned_guard_clip(guard,'talk'),minimumLoops=3)
     await self.observe(guard['talkSeconds']*3+.8)
     self.check_guard_window(guard,'talk',guard['talkSeconds']*3)
     if self.args.talk_companion:
      await self.command('reviewHud',hidden=False);self.event('hudRestored')
     await self.tap('Escape');await self.observe(.3);assert self.snap()['session']['state']=='Play'
     self.event('idleReturn');await self.observe(guard['idleSeconds']+1)
    await self.shot_action(guard['actor']+'-'+view+'-loops'+('-hud-hidden-companion'if self.args.talk_companion else''),action,actor=guard['actor'],view=view,minimumCompleteLoops=3,minimumVideoSeconds=guard['idleSeconds']*4+guard['talkSeconds']*3+.8,landmark=guard['landmark'],diagnosticCompanion=self.args.talk_companion)
 def assigned_guard_clip(self,guard,slot):
  actors=self.manifest['savedClipAssignments']['actors']
  assignment=next(a for a in actors if a.get('parent')==guard['actor'])[slot]
  asset=UNITY/'AthenHill'/assignment['path']
  # Read the actual serialized clip name; installed Meshy clips are idle_meshy/talk_meshy.
  match=re.search(r'^  m_Name: (.+)$',asset.read_text(),re.MULTILINE)
  assert match, 'Missing serialized clip name: '+str(asset)
  return match.group(1)
 def check_guard_window(self,guard,clip,minimum):
  expected=self.assigned_guard_clip(guard,clip);times=[];clip_times=[]
  for sample in self.shot['actorSamples']:
   matches=[a for a in sample['actors']if math.dist(a['position'],guard['position'])<.08]
   if len(matches)==1 and matches[0]['CurrentClip']==expected:
    times.append(sample['videoOffsetEstimate']);clip_times.append(matches[0]['clipTime'])
  span=max(times)-min(times)if times else 0
  playback=max(clip_times)-min(clip_times)if clip_times else 0
  self.shot.setdefault('guardPlaybackChecks',[]).append({'actor':guard['actor'],'slot':clip,'clip':expected,'observedSpanSeconds':span,'actualClipProgressSeconds':playback,'requiredSeconds':minimum,'samples':len(times)})
  assert span>=minimum,{'actor':guard['actor'],'clip':clip,'observedSeconds':span,'requiredSeconds':minimum}
  assert playback>=minimum,{'actor':guard['actor'],'clip':expected,'actualClipProgressSeconds':playback,'requiredSeconds':minimum}
 async def player(self):
  for view in ['side','rear']:
   await self.setup(camera='cam_motion_jump_'+view)
   keys=PLAN['jumpInputs'][view]
   async def action():
    self.event('playerIdleStart');await self.observe(15)
    await self.hold(keys,.7);await self.observe(.6)
    reverse=[{'w':'s','s':'w','a':'d','d':'a'}[k]for k in keys];await self.hold(reverse,.7);await self.observe(.4)
    await self.hold(keys,.4);await self.hold(keys+['Shift_L'],.5);await self.hold(keys,.4);await self.observe(.65)
    await self.hold(reverse+['Shift_L'],.8);await self.observe(.45)
    await self.hold(['a']if view=='rear'else['w'],.5);await self.hold(['d']if view=='rear'else['s'],.5);await self.observe(.5)
    await self.jump(keys,True);await self.hold(['a']if view=='rear'else['w'],.45);await self.observe(.6)
   await self.shot_action('player-transitions-'+view,action,view=view,checks=['idle loops','start/stop','walk-run-walk','90/180 moving turns','move after landing'])
  await self.setup(camera='follow',yaw=-90)
  async def orbit():
   self.event('stationaryCameraOrbit',note='Current controls rotate the camera at rest; they do not provide a separate character turn-in-place command.')
   xtest.fake_input(self.d,X.ButtonPress,1);self.d.sync()
   try:
    for i in range(16):xtest.fake_input(self.d,X.MotionNotify,x=self.origin.x+800+i*20,y=self.origin.y+520);self.d.sync();await asyncio.sleep(.035)
   finally:xtest.fake_input(self.d,X.ButtonRelease,1);self.d.sync()
   await self.observe(2)
  await self.shot_action('stationary-orbit-control',orbit,knownLimitation='Stationary character turn-in-place is not a current input verb; camera orbit is captured explicitly rather than mislabeled.')
 def walker_sample(self,walker,actors):
  candidates=[]
  for a in actors:
   p=a['position'];dist=min(segment_distance(p,walker['points'][i],walker['points'][(i+1)%4])for i in range(4))
   if dist<.08:candidates.append(a)
  assert len(candidates)==1,{'actor':walker['actor'],'candidates':[a['name']for a in candidates]}
  return candidates[0]
 async def walkers(self):
  for walker in PLAN['walkers']:
   if self.args.actor and walker['actor']not in self.args.actor:continue
   for corner in walker['corners']:
    await self.setup(camera=corner['camera']);deadline=time.monotonic()+walker['routeSeconds']+10;approach=sub(corner['previous'],corner['position']);approach=[x/length(approach)for x in approach]
    while True:
     await self.command('actorSnapshot');a=self.walker_sample(walker,json.loads((QA/'actors.json').read_text()));delta=sub(a['position'],corner['position']);along=dot(delta,approach);lateral=length(sub(delta,[along*x for x in approach]))
     if .25<along<2.1 and lateral<.1:break
     if time.monotonic()>deadline:raise AssertionError('No approach observed for '+walker['actor']+' corner '+str(corner['index']))
     await asyncio.sleep(.1)
    async def action():await self.observe(6)
    await self.shot_action(walker['actor']+'-corner-'+str(corner['index']),action,actor=walker['actor'],corner=corner,route=walker['points'],routeSpeed=walker['speed'])
 async def wheel(self,button,count):
  for _ in range(count):xtest.fake_input(self.d,X.ButtonPress,button);xtest.fake_input(self.d,X.ButtonRelease,button);self.d.sync();await asyncio.sleep(.055)
 async def first_person(self):
  for name,landmark,yaw in [('stairs','hill_tree',90),('edge','hill_tree',45),('wall','qa_motion_wall',90),('door','qa_motion_door',90)]:
   await self.setup(landmark,'follow',yaw);await self.wheel(4,18);await self.observe(.3,False);assert self.snap()['camera']['firstPerson']
   async def action(name=name):
    if name in ['stairs','edge']:
     await self.hold(['w'],.7 if name=='stairs'else 2.5)
     if name=='stairs':await self.jump(['w'])
    else:
     await self.hold(['w'],.55);await self.jump(['w']);await self.hold(['a'],.35);await self.hold(['d'],.35)
    await self.observe(.8);self.event('zoomOutWhileSettling');await self.wheel(5,6);await self.observe(.5);self.event('zoomInAgain');await self.wheel(4,6);await self.observe(.6)
    assert self.snap()['player']['grounded'],self.snap()['player']
    assert not self.snap()['camera']['overlaps'],self.snap()['camera']
   await self.shot_action('first-person-'+name,action,scenario=name,landmark=landmark,requiredPhases=['Falling','Landing','Grounded']if name=='edge'else['Takeoff','Falling','Landing','Grounded'],expectedJumps=0 if name=='edge'else 1,expectedGroundedFinal=True,checks=['grounding','camera overlap','near clipping','body/shadow transition','zoom while settling'])
 async def run(self):
  try:
   await self.normal();assert [self.snap()['width'],self.snap()['height']]==[1920,1080]
   root=self.d.screen().root
   for wid in root.get_full_property(self.d.intern_atom('_NET_CLIENT_LIST'),X.AnyPropertyType).value:
    window=self.d.create_resource_object('window',wid);pid=window.get_full_property(self.d.intern_atom('_NET_WM_PID'),X.AnyPropertyType)
    if pid is not None and int(pid.value[0])==int(os.environ['ATHEN_NATIVE_PID']):self.origin=root.translate_coords(window,0,0);break
   xtest.fake_input(self.d,X.MotionNotify,x=self.origin.x+960,y=self.origin.y+540);self.d.sync()
   await self.command('settingsSnapshot');self.manifest['settings']=json.loads((QA/'settings.json').read_text());self.manifest['environment']=json.loads((QA/'environment.json').read_text())
   exe=pathlib.Path(os.readlink('/proc/'+os.environ['ATHEN_NATIVE_PID']+'/exe'));self.manifest['executable']={'path':str(exe),'sha256':sha(exe)}
   self.manifest['buildFiles']=[{'path':str(p.relative_to(exe.parent)),'sha256':sha(p),'bytes':p.stat().st_size}for p in sorted(exe.parent.glob('AthenHill_Data/*'))if p.is_file()and p.name in ['globalgamemanagers','level0','resources.assets','sharedassets0.assets']]
   scene=UNITY/'AthenHill/Assets/AthenHill/Scenes/AthenHill.unity';self.manifest['savedSceneAtCaptureSha256']=sha(scene);self.manifest['capturePlanSha256']=sha(HERE/'capture-plan.json')
   layout=HERE/'capture-layout.json'
   if layout.exists():self.manifest['savedClipAssignments']=json.loads(layout.read_text())
   for section in ['jumps','guards','player','walkers','first-person']:
    if self.args.section in ['all',section]:await getattr(self,section.replace('-','_'))()
   self.manifest['complete']=all(s['complete']for s in self.manifest['shots']);self.manifest['completedUtc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
   if not self.manifest['complete']:raise AssertionError('One or more clip duration/encoder/behavior evidence checks failed; inspect manifest and retain failed captures.')
  except Exception as e:self.manifest['error']=str(e);raise
  finally:
   for k in ['w','a','s','d','space','Shift_L']:key(self.d,k,False)
   if self.shot is not None:await self.finish(False,'Capture interrupted before normal completion')
   if self.args.talk_companion:
    try:await self.command('reviewHud',hidden=False)
    except Exception as e:self.manifest['hudRestoreError']=str(e)
   self.save();print('Evidence manifest:',self.out/'manifest.json',flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--section',choices=['all','jumps','guards','player','walkers','first-person'],default='all');p.add_argument('--actor',action='append');p.add_argument('--talk-companion',action='store_true',help='Development-only HUD-hidden companion to expose actual E-key dialogue animation');asyncio.run(Capture(p.parse_args()).run())
