import asyncio,json,pathlib
from fastmcp import Client
R=pathlib.Path(__file__).resolve().parents[1];C=R/'AthenHill/Captures'
async def main():
 results=[]
 async with Client('http://127.0.0.1:18081/mcp',timeout=60) as c:
  await c.call_tool('set_active_instance',{'instance':'AthenHill@7f7f353bae1a07d0'})
  await c.call_tool('manage_editor',{'action':'play'})
  async def command(j):
   (C/'debug-command.json').write_text(json.dumps(j));await c.call_tool('execute_menu_item',{'menu_path':'Athen Hill/Diagnostics/Apply command'})
  for landmark in ['west_gate','shop_row_w','shop_row_e','hill_tree']:
   await command({'action':'goto','landmark':landmark})
   for yaw in [0,90,180,270]:
    await command({'action':'cameraYaw','yaw':yaw});await asyncio.sleep(.4)
    await c.call_tool('execute_menu_item',{'menu_path':'Athen Hill/Diagnostics/Write snapshot'})
    s=json.loads((C/'snapshot.json').read_text());results.append({'landmark':landmark,'yaw':yaw,'camera':s['camera'],'player':s['player']})
    if s['camera']['overlaps']:raise RuntimeError(str(results[-1]))
  await command({'action':'capture','camera':'cam_hill'})
  await c.call_tool('manage_editor',{'action':'stop'})
 (R/'evidence/U2/camera-check.json').write_text(json.dumps(results,indent=2));print('PASS',len(results),'camera orientations')
asyncio.run(main())
