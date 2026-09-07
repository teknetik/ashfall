import asyncio,json,pathlib
from fastmcp import Client
from desktop_input import focus,key
R=pathlib.Path(__file__).resolve().parents[1]; C=R/'AthenHill/Captures'; O=R/'evidence/U2'
async def main():
 d=focus()
 async with Client('http://127.0.0.1:18081/mcp',timeout=60) as c:
  await c.call_tool('set_active_instance',{'instance':'AthenHill@7f7f353bae1a07d0'})
  (C/'debug-command.json').write_text(json.dumps({'action':'reset'}));await c.call_tool('execute_menu_item',{'menu_path':'Athen Hill/Diagnostics/Apply command'})
  result=[]
  for name in ['walk','run']:
   key(d,'w',True)
   if name=='run':key(d,'Shift_L',True)
   try:
    await asyncio.sleep(.5)
    await c.call_tool('execute_menu_item',{'menu_path':'Athen Hill/Diagnostics/Write snapshot'})
    s=json.loads((C/'snapshot.json').read_text());result.append({'motion':name,'snapshot':s})
    await c.call_tool('manage_camera',{'action':'screenshot','output_folder':'Captures/U2','screenshot_file_name':name})
   finally:key(d,'w',False);key(d,'Shift_L',False)
   await asyncio.sleep(.3)
  (O/'locomotion.json').write_text(json.dumps(result,indent=2))
  for r in result:
   a=next(a for a in r['snapshot']['actors'] if a['name']=='PlayerCandidate');print(r['motion'],r['snapshot']['player'],a['clip'],a['clips'])
asyncio.run(main())
