import asyncio,json,pathlib,math
from fastmcp import Client
from desktop_input import focus,key
R=pathlib.Path(__file__).resolve().parents[1];C=R/'AthenHill/Captures';O=R/'evidence/U3'
async def main():
 d=focus();checks=[]
 async with Client('http://127.0.0.1:18081/mcp',timeout=60) as c:
  await c.call_tool('set_active_instance',{'instance':'AthenHill@7f7f353bae1a07d0'})
  async def snap():
   await c.call_tool('execute_menu_item',{'menu_path':'Athen Hill/Diagnostics/Write snapshot'});return json.loads((C/'snapshot.json').read_text())
  async def tap(name,seconds=.08):
   key(d,name,True)
   try:await asyncio.sleep(seconds)
   finally:key(d,name,False)
   await asyncio.sleep(.15)
  async def goto(name):
   (C/'debug-command.json').write_text(json.dumps({'action':'goto','landmark':name}));await c.call_tool('execute_menu_item',{'menu_path':'Athen Hill/Diagnostics/Apply command'});await asyncio.sleep(.3)
  async def click(name):
   for _ in range(30):
    s=await snap()
    if s['session']['focused']==name:await tap('Return');return
    await tap('Tab')
   raise RuntimeError('Could not keyboard-focus '+name)
  async def expect(state):
   s=await snap();assert s['session']['state']==state,s['session'];checks.append(s);(O/"city-loop.json").write_text(json.dumps({"complete":False,"checks":checks},indent=2));return s
  if (await snap())['session']['state']=='Paused':await tap('Escape')
  await expect('Play')
  for landmark,npc in [('west_gate','npc_vex'),('mission_slab','npc_torr'),('oa_hill','npc_linn')]:
   await goto(landmark);await tap('e');s=await expect('Dialogue');assert npc in s['session']['spoken']
   before=s['player']['position'];await tap('w',.4);s=await snap();assert math.dist(before,s['player']['position'])<.04,'Modal movement leak'
   await click('choice0');await expect('Dialogue')
   if npc=='npc_vex':await c.call_tool('manage_camera',{'action':'screenshot','output_folder':'Captures/U3','screenshot_file_name':'dialogue'})
   await tap('Escape');await expect('Play')
  await goto('basic_general');await tap('e');await expect('Dialogue');await click('choice0');await expect('Shop')
  await click('buy0');s=await expect('Shop');assert s['session']['credits']==21 and s['session']['quantities']['water_flask']==1,s['session']
  await click('sell2');s=await expect('Shop');assert s['session']['credits']==22 and s['session']['quantities']['scrap_coil']==0,s['session']
  await c.call_tool('manage_camera',{'action':'screenshot','output_folder':'Captures/U3','screenshot_file_name':'shop'})
  await tap('Escape');await goto('lattice_jack');await tap('e');await expect('Grid');await asyncio.sleep(1.4);await click('node0');s=await expect('Grid');assert s['session']['linked'];assert s['session']['selectedDestination']=='crosswind_reach'
  await c.call_tool('manage_camera',{'action':'screenshot','output_folder':'Captures/U3','screenshot_file_name':'lattice'})
  assert s['session']['visitedHill'] and len(s['session']['spoken'])==4 and s['session']['boughtFlask'] and s['session']['soldScrap']
  await tap('Escape');await tap('Escape');s=await expect('Paused');before=s['player']['position'];await tap('w',.4);assert math.dist(before,(await snap())['player']['position'])<.01
  await tap('Escape');await expect('Play')
  for keyname,state in [('5','Inventory'),('6','Notes')]:await tap(keyname);await expect(state);await tap('Escape')
  await goto('ring_gate');s=await expect('Play');assert 'offline' in s['session']['notice']
  await tap('Escape');await expect('Paused');await click('mute');s=await expect('Paused');assert s['session']['muted'];await click('mute')
  await click('reduced-motion');s=await expect('Paused');assert s['session']['reducedMotion']
  await click('credits-button');await expect('Credits');await tap('Escape')
  await goto('lattice_jack');await tap('e');await expect('Grid');await asyncio.sleep(1.4);await click('node1');s=await expect('Grid');assert s['session']['selectedDestination']=='drywater_works';await tap('Escape')
  await tap('r');s=await expect('Play');assert abs(s['player']['position'][0]-43)<.1
  (O/'city-loop.json').write_text(json.dumps({'complete':True,'checks':checks},indent=2));print('PASS: four dialogues, modal input, buy/sell, lattice, all objectives, pause, pack/notes, reset')
asyncio.run(main())
