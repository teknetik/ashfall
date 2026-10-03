import asyncio,json,pathlib,math
import os
from native_client import Client, select_merchant_item
from desktop_input import focus,focus_window,key
from Xlib import X
R=pathlib.Path(__file__).resolve().parents[1];C=pathlib.Path(os.environ.get('ATHEN_NATIVE_DIR',R/'AthenHill/Captures'));O=pathlib.Path(os.environ.get('ATHEN_EVIDENCE',R/'evidence/U3'));O.mkdir(parents=True,exist_ok=True)
async def main():
 d=focus();checks=[]
 async with Client('http://127.0.0.1:18081/mcp',timeout=60) as c:
  await c.call_tool('set_active_instance',{'instance':'AthenHill@7f7f353bae1a07d0'})
  async def snap():return await c.snapshot()
  async def tap(name,seconds=.08):
   nonlocal d
   d,window=focus_window();window.set_input_focus(X.RevertToParent,X.CurrentTime);d.sync()
   key(d,name,True)
   try:
    await asyncio.sleep(seconds)
    if os.environ.get('ATHEN_UI_XVFB'):await c.command({'action':'uiSnapshot'})
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
  async def grid_ready():
   for _ in range(100):
    if (await snap())['session']['gridProgress']>=.999:return
    await asyncio.sleep(.1)
   raise RuntimeError('Lattice did not become ready')
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
  before=(await snap())['session']
  await click('merchant-tab-buy');await click('merchant-filter-supplies');await select_merchant_item(c,'water_flask',tap)
  await click('merchant-trade');s=await expect('Shop');after_buy=s['session']
  assert after_buy['credits']==before['credits']-4 and after_buy['quantities']==dict(before['quantities'],water_flask=before['quantities']['water_flask']+1),after_buy
  await click('merchant-tab-sell');await click('merchant-filter-all');await select_merchant_item(c,'scrap_coil',tap)
  await click('merchant-trade');s=await expect('Shop')
  assert s['session']['credits']==after_buy['credits']+1 and s['session']['quantities']==dict(after_buy['quantities'],scrap_coil=after_buy['quantities']['scrap_coil']-1),s['session']
  await c.call_tool('manage_camera',{'action':'screenshot','output_folder':'Captures/U3','screenshot_file_name':'shop'})
  await tap('Escape');await goto('lattice_jack');await tap('e');await expect('Grid');await grid_ready();await click('node0');s=await expect('Grid');assert s['session']['linked'];assert s['session']['selectedDestination']=='crosswind_reach'
  await c.call_tool('manage_camera',{'action':'screenshot','output_folder':'Captures/U3','screenshot_file_name':'lattice'})
  assert s['session']['visitedHill'] and len(s['session']['spoken'])==4 and s['session']['boughtFlask'] and s['session']['soldScrap']
  await tap('Escape');await tap('Escape');s=await expect('Paused');before=s['player']['position'];await tap('w',.4);assert math.dist(before,(await snap())['player']['position'])<.01
  await tap('Escape');await expect('Play')
  for keyname,state in [('5','Inventory'),('6','Notes')]:await tap(keyname);await expect(state);await tap('Escape')
  await goto('ring_gate');s=await expect('Play');assert 'offline' not in (s['session'].get('notice') or ''),'3 Oct 2026: the Meshy ring is the Lattice Jack, no offline response'
  await tap('Escape');await expect('Paused');await click('mute');s=await expect('Paused');assert s['session']['muted'];await click('mute')
  await click('reduced-motion');s=await expect('Paused');assert s['session']['reducedMotion']
  await click('reduced-motion');s=await expect('Paused');assert not s['session']['reducedMotion']
  await click('credits-button');await expect('Credits');await tap('Escape')
  await goto('lattice_jack');await tap('e');await expect('Grid');await grid_ready();await click('node1');s=await expect('Grid');assert s['session']['selectedDestination']=='drywater_works';await tap('Escape')
  await tap('r');s=await expect('Play');assert abs(s['player']['position'][0]-43)<.1
  (O/'city-loop.json').write_text(json.dumps({'complete':True,'checks':checks},indent=2));print('PASS: four dialogues, modal input, buy/sell, lattice, all objectives, pause, pack/notes, reset')
if __name__=='__main__':
 if not os.environ.get('ATHEN_NATIVE_PID') or not os.environ.get('ATHEN_NATIVE_DIR'):raise SystemExit('Run through unity/tools/run_native.sh with the existing QA run directory.')
 asyncio.run(main())
