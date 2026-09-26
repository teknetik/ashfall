import asyncio,importlib.util,json,time,uuid,os,subprocess
from pathlib import Path
ROOT=Path('/home/teknetik/code/ao2')
OUT=Path(__file__).resolve().parent
NATIVE=ROOT/'unity/evidence/quality/20260926/candidate-native-04-windowed'
SPEC=importlib.util.spec_from_file_location('coverage',ROOT/'unity/evidence/quality/20260926/tree-shadow-protocol/runner-coverage.py');module=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(module)
def read(p):return json.loads(p.read_text())
def write(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2)
def telemetry(name):
 vals={}
 for label,cmd in [('gpu',['nvidia-smi','--query-gpu=name,memory.total,memory.used,utilization.gpu,pstate,clocks.gr,temperature.gpu','--format=csv']),('processes',['nvidia-smi','pmon','-c','1'])]:
  r=subprocess.run(cmd,text=True,capture_output=True,timeout=8);vals[label]={'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
 for label,path in [('memoryPressure',Path('/proc/pressure/memory')),('meminfo',Path('/proc/meminfo')),('playerStatus',Path('/proc/1103618/status'))]:vals[label]=path.read_text()
 write(OUT/(name+'-telemetry.json'),vals)
async def main():
 receipts=OUT/'commands';receipts.mkdir();client=module.NativeClient(NATIVE,1103618,receipts)
 report={'complete':False,'purpose':'Two bounded original-caster hill controls comparing leaf ambient .15 vs0; diagnostic only','desktopState':'Parent observed unlocked desktop and user movement before this run','intervals':[],'qualification':False}
 owner=NATIVE/'.tree-shadow-command-owner.json';token=uuid.uuid4().hex;write(owner,{'runnerPid':os.getpid(),'playerPid':1103618,'output':str(OUT),'token':token})
 profiling=False;initial=None
 try:
  # Reconcile the prior interrupted runner's own outstanding command, without overwriting it.
  deadline=time.monotonic()+10
  while (NATIVE/'command.json').exists() and time.monotonic()<deadline:await asyncio.sleep(.05)
  if (NATIVE/'command.json').exists():raise RuntimeError('Prior owned command remains unconsumed; no overwrite')
  report['priorAck']=read(NATIVE/'ack.json')
  report['recoveryReview']=await client.command({'action':'reviewReset'},cleanup=True)
  previous=read(ROOT/'unity/evidence/quality/20260926/tree-shadow-coverage-04b/report.json')['initialTime']
  await client.command({'action':'timeSet','hour':previous['hour']},cleanup=True)
  await client.command({'action':'timeSpeed','speed':previous['speed']},cleanup=True)
  await client.command({'action':'timePause','paused':previous['paused']},cleanup=True)
  initial=await client.command({'action':'timeState'})
  report['recoveredSettings']=await client.command({'action':'settingsSnapshot'},cleanup=True)
  write(ROOT/'unity/evidence/quality/20260926/tree-shadow-coverage-04b/cleanup-recovery.json',{'priorFailurePreserved':True,'review':report['recoveryReview'],'settings':report['recoveredSettings'],'time':initial,'playerNotMoved':True})
  await client.command({'action':'timePause','paused':True});await client.command({'action':'timeSet','hour':12})
  await client.command({'action':'view','camera':'cam_hill'})
  for index,value in enumerate([.15,0],1):
   name=f'{index:02}-ambient-{value}'
   review=await client.command({'action':'reviewTree','shadowDistance':18,'shadowCascades':1,'ambientTransmission':value})
   assert review['ambientTransmission'] and all(abs(r['current']-value)<.0001 for r in review['ambientTransmission'])
   assert not review['treeShadow']['enabled']
   await asyncio.sleep(3)
   settings=await client.command({'action':'settingsSnapshot'});before=read(NATIVE/'snapshot.json');module.validate_state(settings,before)
   telemetry(name+'-before')
   await client.command({'action':'profileStart'});profiling=True;await asyncio.sleep(10)
   frames=await client.command({'action':'profileStop'});profiling=False;write(OUT/(name+'-frames.json'),frames)
   after=read(NATIVE/'snapshot.json');module.validate_state(settings,after)
   row={'name':name,'ambient':value,'settings':settings,'review':review,'before':before,'after':after,'rawFrames':len(frames),'summary':module.summarize(frames[1:]),'interactionObserved':any(f['speed']>.01 or f['state']!='Play' for f in frames),'memory':await module.memory_snapshot(client,NATIVE)}
   write(OUT/(name+'-metadata.json'),row);report['intervals'].append(row)
   print(json.dumps({'interval':name,'fps':row['summary']['averageFps'],'p99':row['summary']['p99Ms'],'interactionObserved':row['interactionObserved']}),flush=True)
  report['complete']=True
 except BaseException as error:report['error']=repr(error)
 finally:
  try:
   if profiling:write(OUT/'interrupted-frames.json',await client.command({'action':'profileStop'},cleanup=True))
   report['restoredReview']=await client.command({'action':'reviewReset'},cleanup=True)
   if initial:
    await client.command({'action':'timeSet','hour':initial['hour']},cleanup=True);await client.command({'action':'timeSpeed','speed':initial['speed']},cleanup=True);await client.command({'action':'timePause','paused':initial['paused']},cleanup=True)
   report['restoredSettings']=await client.command({'action':'settingsSnapshot'},cleanup=True)
   report['restoredTime']=await client.command({'action':'timeState'},cleanup=True)
   report['cleanup']='Original leaf/shadows/casters/time restored; camera follow; player position not changed by runner'
  except BaseException as error:report['cleanupError']=repr(error);report['complete']=False
  write(OUT/'report.json',report)
  if owner.exists() and read(owner).get('token')==token:owner.unlink()
 print(json.dumps({'complete':report['complete'],'cleanup':report.get('cleanup'),'error':report.get('error'),'cleanupError':report.get('cleanupError')}),flush=True)
 if not report['complete']:raise SystemExit(2)
asyncio.run(main())
