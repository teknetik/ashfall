"""Current saved native build04 static views; not motion/performance qualification."""
import asyncio,hashlib,json,os,sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'unity/tools'))
from native_client import Client
BASE=Path(__file__).parent
NATIVE=BASE/'candidate-native-04-windowed'
OUT=BASE/'native-current-build04'
OUT.mkdir(exist_ok=False)
os.environ['ATHEN_NATIVE_DIR']=str(NATIVE)
report={'complete':False,'buildIdentity':'candidate-build-04-identity.json','scope':__doc__,'views':[]}
async def main():
 c=Client()
 async def cmd(value):
  await c.command(value)
  if (NATIVE/'qa-error.json').exists():raise RuntimeError('Native command failed')
 def read(name):return json.loads((NATIVE/name).read_text())
 try:
  assert 'Selected window backend: x11' in (NATIVE/'Player.log').read_text()
  await cmd({'action':'reviewReset'});await cmd({'action':'timeReset'});await cmd({'action':'timePause','paused':True})
  await cmd({'action':'settingsSnapshot'});report['settings']=read('settings.json')
  assert report['settings']['renderScale']==1 and report['settings']['msaa']==4
  assert report['settings']['shadowDistance']==18 and report['settings']['shadowCascades']==1
  await cmd({'action':'actorSnapshot'});report['actors']=read('actors.json');assert len(report['actors'])==9
  await cmd({'action':'reviewTree','ambientTransmission':.15});review=read('visual-review-state.json')
  assert abs(review['ambientTransmission'][0]['original']-.15)<.0001
  report['savedLeafCheck']=review
  await cmd({'action':'reviewReset'})
  for camera in ['cam_hill','cam_avenue','cam_gate','cam_grid','cam_whompah','cam_hero','cam_terminal','cam_tree_canopy_below','cam_tree_root_south','character','portrait','cam_fidelity_guard']:
   await cmd({'action':'view','camera':camera});await asyncio.sleep(2.7)
   state=read('snapshot.json');assert [state['width'],state['height']]==[1920,1080]
   name='current04-'+camera;source=NATIVE/(name+'.png');assert not source.exists()
   await cmd({'action':'capture','name':name})
   for _ in range(100):
    try:
     with Image.open(source) as pic:
      pic.load();assert pic.size==(1920,1080)
      rgb=pic.convert('RGB');assert rgb.crop((0,0,1920,8)).getbbox() and rgb.crop((1912,0,1920,1080)).getbbox(),'Clipped backbuffer'
     break
    except (FileNotFoundError,OSError):await asyncio.sleep(.1)
   else:raise TimeoutError(name)
   dest=OUT/(camera+'.png');dest.write_bytes(source.read_bytes())
   report['views'].append({'camera':camera,'file':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'snapshot':state})
   (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Captured '+camera,flush=True)
  report['complete']=True
 except BaseException as error:
  report['error']=str(error);raise
 finally:
  report['restoreErrors']=[]
  for action in ['reviewReset','timeReset']:
   try:await cmd({'action':action})
   except Exception as error:report['restoreErrors'].append(str(error))
  if report['restoreErrors']:report['complete']=False
  (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
asyncio.run(main())
