"""Separate-frame native material audition, not temporal/performance acceptance."""
import asyncio, hashlib, json, os, sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'unity/tools'))
from native_client import Client
FOLDER=Path(__file__).parent/'candidate-native-03'
OUT=Path(__file__).parent/'native-leaf-shade-v1'
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
  assert report['settings']['renderScale']==1 and report['settings']['msaa']==4
  for camera in ['cam_hill','cam_hero','cam_tree_canopy_below','cam_tree_canopy_edge']:
   await cmd({'action':'view','camera':camera});await asyncio.sleep(3)
   for amount in [0,.15,.25]:
    await cmd({'action':'reviewTree','ambientTransmission':amount});await asyncio.sleep(3)
    last=None;stable=0
    for _ in range(20):
     await cmd({'action':'reviewTree','ambientTransmission':amount})
     review=read('visual-review-state.json');entry=review['ambientTransmission'][0];tex=entry['leafTexture']
     assert abs(entry['current']-amount)<.0001 and tex['name']=='leaves-edge-padded-v1',entry
     key=(tex['loadedMipmapLevel'],tex['desiredMipmapLevel'])
     stable=stable+1 if key==last else 0;last=key
     if stable>=2 and key[0]==key[1]:break
     await asyncio.sleep(.4)
    else:raise RuntimeError('Leaf mip selection did not settle: '+str(tex))
    state=read('snapshot.json');assert [state['width'],state['height']]==[1920,1080]
    name=f'{camera}-ambient-{round(amount*100)}';source=FOLDER/f'leaf-shade-v1-{name}.png'
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
    report['views'].append({'camera':camera,'ambientTransmission':amount,'image':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'review':review,'snapshot':state})
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
