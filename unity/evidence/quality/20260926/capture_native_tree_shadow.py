"""Separate-frame native shadow geometry audition, not temporal/performance acceptance."""
import asyncio, hashlib, json, os, sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'unity/tools'))
from native_client import Client
FOLDER=Path(__file__).parent/'candidate-native-03'
OUT=Path(__file__).parent/'native-tree-shadow-v2'
OUT.mkdir(exist_ok=True)
REPORT=OUT/'report.json'
assert not REPORT.exists(), 'Preserve existing evidence.'
os.environ['ATHEN_NATIVE_DIR']=str(FOLDER)
report={'complete':False,'purpose':__doc__,'views':[],'limitations':'Daylight frozen; actors, wind and particles animate. Static stills do not qualify movement or temporal stability.'}
async def main():
 c=Client()
 async def cmd(j):
  await c.command(j)
  if (FOLDER/'qa-error.json').exists():raise RuntimeError((FOLDER/'qa-error.json').read_text())
 def read(name):return json.loads((FOLDER/name).read_text())
 try:
  await cmd({'action':'timeReset'});await cmd({'action':'timePause','paused':True})
  await cmd({'action':'reviewTree','shadowDistance':48,'shadowCascades':2})
  await cmd({'action':'settingsSnapshot'});report['settings']=read('settings.json')
  report['environment']=read('environment.json')
  await cmd({'action':'memorySnapshot'});report['memory']=read('memory.json')
  streaming=report['memory']['streamingMipmapsActive']
  assert report['settings']['renderScale']==1 and report['settings']['msaa']==4
  for camera in ['cam_hill','cam_hero','cam_tree_canopy_below','cam_tree_root_south','cam_whompah']:
   await cmd({'action':'view','camera':camera});await asyncio.sleep(3)
   for enabled in [False,True]:
    await cmd({'action':'reviewTreeShadow','enabled':enabled});await asyncio.sleep(3)
    review=read('visual-review-state.json')
    assert review['treeShadow']['enabled']==enabled
    if enabled:assert review['treeShadow']['shadowRendererCount']==3
    state=read('snapshot.json');assert [state['width'],state['height']]==[1920,1080]
    name=f'{camera}-shadow-lod1-{int(enabled)}';source=FOLDER/f'tree-shadow-v2-{name}.png'
    assert not source.exists() and not (OUT/(name+'.png')).exists()
    await cmd({'action':'capture','name':source.stem})
    for _ in range(100):
     try:
      with Image.open(source) as image:
       image.load();assert image.size==(1920,1080)
       assert image.convert('RGB').crop((0,0,1920,8)).getbbox(),'Clipped top strip'
      break
     except (FileNotFoundError,OSError):await asyncio.sleep(.1)
    else:raise TimeoutError(name)
    dest=OUT/(name+'.png');dest.write_bytes(source.read_bytes())
    report['views'].append({'camera':camera,'shadowLod1':enabled,'image':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'review':review,'snapshot':state})
    REPORT.write_text(json.dumps(report,indent=2)+'\n');print('Captured '+name,flush=True)
  report['complete']=True
 except Exception as error:
  report['error']=str(error);raise
 finally:
  errors=[]
  for action in ['reviewReset','timeReset']:
   try:await cmd({'action':action})
   except Exception as error:errors.append({'action':action,'error':str(error)})
  report['restoreErrors']=errors
  if errors:report['complete']=False
  REPORT.write_text(json.dumps(report,indent=2)+'\n')
asyncio.run(main())
