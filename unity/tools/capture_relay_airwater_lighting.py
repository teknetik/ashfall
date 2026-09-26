"""Fixed native close views under three authored sun positions; no performance claim."""
import asyncio,json,os
from pathlib import Path
from native_client import Client
from desktop_input import focus,key
OUT=Path(os.environ['ATHEN_NATIVE_DIR'])
async def main():
 c=Client();d=focus();report={'complete':False,'views':[]}
 if json.loads((OUT/'snapshot.json').read_text())['session']['state']=='Paused':
  key(d,'Escape',True);await asyncio.sleep(.08);key(d,'Escape',False);await asyncio.sleep(.3)
 try:
  await c.command({'action':'timePause','paused':True})
  for hour in [8,12,16]:
   await c.command({'action':'timeSet','hour':hour});await asyncio.sleep(3)
   await c.command({'action':'timeState'});lighting=json.loads((OUT/'time-state.json').read_text())
   for camera in ['cam_audit_relay_works_door','cam_audit_air_water_door','cam_audit_air_water_side_right']:
    focus();await c.command({'action':'view','camera':camera});await asyncio.sleep(.7)
    name=camera+'-hour-'+str(hour);await c.command({'action':'capture','name':name})
    report['views'].append({'image':name+'.png','camera':camera,'lighting':lighting});print(name,flush=True)
  report['complete']=True
 finally:
  (OUT/'material-lighting.json').write_text(json.dumps(report,indent=2));await c.command({'action':'timeReset'});await c.command({'action':'view','camera':'follow'})
asyncio.run(main())
