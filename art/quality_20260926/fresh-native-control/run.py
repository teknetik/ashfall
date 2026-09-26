import asyncio,base64,hashlib,importlib.util,json,os,re,signal,struct,subprocess,time,uuid
from pathlib import Path
ROOT=Path('/home/teknetik/code/ao2')
OUT=ROOT/'unity/evidence/quality/20260926/fresh-control-04'
EXE=ROOT/'unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64'
SIG='efb50993780079460b0cbed1363e2166a2de1d9f_1790318179_484952352'
spec=importlib.util.spec_from_file_location('coverage',ROOT/'unity/evidence/quality/20260926/tree-shadow-protocol/runner-coverage.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def write(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2)
def read(p):return json.loads(p.read_text())
def hypr(args,env):return subprocess.check_output(['hyprctl',*args],env=env,text=True,timeout=8)
def telemetry(name,pid):
 r=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,memory.used,utilization.gpu,pstate,clocks.gr,temperature.gpu','--format=csv'],text=True,capture_output=True,timeout=8)
 write(OUT/(name+'-telemetry.json'),{'gpu':r.stdout,'gpuErrors':r.stderr,'memoryPressure':Path('/proc/pressure/memory').read_text(),'meminfo':Path('/proc/meminfo').read_text(),'playerStatus':Path(f'/proc/{pid}/status').read_text()})
async def main():
 OUT.mkdir();(OUT/'commands').mkdir();config=OUT/'config';config.mkdir()
 report={'complete':False,'qualification':False,'purpose':'Fresh build04 native process control; no input or settings qualification','desktopState':'Parent observed unlocked; no input injected','oldPid':1103618,'viewportHistory':[]}
 old=Path('/proc/1103618')
 if old.exists():
  assert (old/'exe').resolve()==EXE.resolve()
  assert 'candidate-native-04-windowed' in (old/'cmdline').read_bytes().decode()
  os.kill(1103618,signal.SIGTERM)
  for _ in range(100):
   if not old.exists():break
   await asyncio.sleep(.1)
  if old.exists():raise RuntimeError('Old owned process did not exit; no second launch')
 report['oldProcessStopped']=True
 video=dict(width=1920,height=1080,windowMode=0,preset=2,renderPercent=100,shadows=3,antiAliasing=4,textureLimit=0,postProcessing=True,vSync=False,frameLimit=0)
 encoded=base64.b64encode(json.dumps(video).encode()).decode()
 prefs='<?xml version="1.0" encoding="utf-8"?><unity_prefs version_major="1" version_minor="1"><pref name="AthenHill.Settings.v1.QA.Video" type="string">'+encoded+'</pref></unity_prefs>'
 for company,product in [('unknown','unknown'),('Free Column','Athen Hill')]:
  folder=config/'unity3d'/company/product;folder.mkdir(parents=True);(folder/'prefs').write_text(prefs)
 scoped=dict(DISPLAY=':0',WAYLAND_DISPLAY='wayland-1',HYPRLAND_INSTANCE_SIGNATURE=SIG,__GLX_VENDOR_LIBRARY_NAME='nvidia',XDG_CONFIG_HOME=str(config))
 env=dict(os.environ,**scoped)
 for key in ['LIBGL_ALWAYS_SOFTWARE','GALLIUM_DRIVER','MESA_LOADER_DRIVER_OVERRIDE','LIBGL_KOPPER_DRI2','VK_ICD_FILENAMES','VK_DRIVER_FILES','ATHEN_UI_XVFB']:env.pop(key,None)
 command=[str(EXE),'-force-glcore','-screen-fullscreen','0','-screen-width','1920','-screen-height','1080','-logFile',str(OUT/'Player.log'),'--athen-qa',str(OUT),'--athen-qa-background']
 report.update(command=command,scopedEnvironment=scoped,videoRequested=video,buildFiles=[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [EXE,EXE.parent/'AthenHill_Data/Managed/AthenHill.Runtime.dll',EXE.parent/'AthenHill_Data/level0']])
 write(OUT/'launch.json',report)
 child=subprocess.Popen(command,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT,start_new_session=True);pid=child.pid;report['pid']=pid;(OUT/'pid').write_text(str(pid));os.environ['ATHEN_NATIVE_PID']=str(pid)
 client=m.NativeClient(OUT,pid,OUT/'commands');owner=OUT/'.tree-shadow-command-owner.json';token=uuid.uuid4().hex;write(owner,{'playerPid':pid,'runnerPid':os.getpid(),'token':token,'purpose':report['purpose']})
 profiling=False;changed=False;initial_time=None
 try:
  deadline=time.monotonic()+90;window=None;started=time.monotonic()
  while time.monotonic()<deadline:
   if child.poll() is not None:raise RuntimeError('Fresh player exited before window')
   windows=[c for c in json.loads(hypr(['-j','clients'],env)) if c.get('pid')==pid]
   if windows:window=windows[0];break
   await asyncio.sleep(.02)
  if not window:raise RuntimeError('Fresh owned window unavailable')
  report['firstClient']=window;report['windowFoundSeconds']=time.monotonic()-started
  address=window['address'];assert re.fullmatch(r'0x[0-9a-fA-F]+',address)
  report['floatResult']=hypr(['dispatch',f'hl.dsp.window.float({{window="address:{address}",action="set"}})'],env)
  report['resizeResult']=hypr(['dispatch',f'hl.dsp.window.resize({{window="address:{address}",x=1536,y=864,relative=false}})'],env)
  stable=0;lastframe=-1
  while time.monotonic()<deadline:
   if child.poll() is not None:raise RuntimeError('Fresh player exited in initialization')
   if (OUT/'snapshot.json').exists():
    s=read(OUT/'snapshot.json')
    if s['frame']!=lastframe:
     lastframe=s['frame'];row={k:s[k] for k in ['frame','width','height','fps']};report['viewportHistory'].append(row)
     stable=stable+1 if (s['width'],s['height'])==(1920,1080) else 0
    if stable>=8 and (OUT/'environment.json').exists():break
   await asyncio.sleep(.05)
  if stable<8:raise RuntimeError('Fresh viewport did not establish eight observed1080p frames')
  report['environment']=read(OUT/'environment.json');assert 'NVIDIA' in report['environment']['gpu'] and report['environment']['api']=='OpenGLCore'
  initial_time=await client.command({'action':'timeState'});report['initialTime']=initial_time
  changed=True;await client.command({'action':'timePause','paused':True});await client.command({'action':'timeSet','hour':12});await client.command({'action':'view','camera':'cam_hill'})
  report['actors']=await client.command({'action':'actorSnapshot'});assert len(report['actors'])==9
  await asyncio.sleep(3)
  settings=await client.command({'action':'settingsSnapshot'});before=read(OUT/'snapshot.json');m.validate_state(settings,before);assert settings['shadowDistance']==18 and settings['shadowCascades']==1
  report['settings']=settings;report['before']=before;telemetry('before',pid)
  await client.command({'action':'profileStart'});profiling=True;await asyncio.sleep(10)
  frames=await client.command({'action':'profileStop'});profiling=False;write(OUT/'hill-control-frames.json',frames)
  report['after']=read(OUT/'snapshot.json');m.validate_state(settings,report['after']);report['summary']=m.summarize(frames[1:]);report['interactionObserved']=any(f['speed']>.01 or f['state']!='Play' for f in frames);report['memory']=await m.memory_snapshot(client,OUT);telemetry('after',pid)
  await client.command({'action':'capture','name':'hill-control-after'})
  report['complete']=not report['interactionObserved']
 except BaseException as error:report['error']=repr(error)
 finally:
  try:
   if profiling:write(OUT/'interrupted-frames.json',await client.command({'action':'profileStop'},cleanup=True))
   if changed:
    report['restoredReview']=await client.command({'action':'reviewReset'},cleanup=True)
    await client.command({'action':'timeSet','hour':initial_time['hour']},cleanup=True);await client.command({'action':'timeSpeed','speed':initial_time['speed']},cleanup=True);await client.command({'action':'timePause','paused':initial_time['paused']},cleanup=True)
    report['cleanup']='Initial clock and camera follow restored; no player input/reset; new process retained for owner'
  except BaseException as error:report['cleanupError']=repr(error);report['complete']=False
  report['playerAlive']=child.poll() is None;write(OUT/'report.json',report)
  if owner.exists() and read(owner).get('token')==token:owner.unlink()
 print(json.dumps({k:report.get(k) for k in ['complete','pid','summary','error','cleanupError','playerAlive']}),flush=True)
asyncio.run(main())
