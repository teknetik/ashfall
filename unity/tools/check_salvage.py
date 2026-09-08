"""Native Linux render, real-keyboard route and city-loop verification for the saved salvage pass."""
import asyncio,json,os,subprocess,sys,time,statistics
from pathlib import Path
R=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ATHEN_SALVAGE_EVIDENCE',R/'evidence/salvage/20260908/native'));OUT.mkdir(parents=True,exist_ok=True)
CAMERAS=['cam_hill','cam_avenue','cam_gate','cam_salvage_shop','cam_salvage_general','cam_salvage_hall','cam_salvage_yard','cam_salvage_board','cam_salvage_wreck','cam_terminal','cam_whompah']
ROUTE=[('west_stair_approach',[12,0,0]),('hill_tree',[4,1.5,0]),('hill_southwest',[4,1.5,4]),('south_stair_top',[0,1.5,4]),('south_stair_bottom',[0,0,12]),('general_clear_lane',[0,0,21]),('general_front_lane',[8,0,21]),('general_approach',[8,0,19]),('general_porch',[8,.5,16.8]),('general_departure',[8,0,19.5]),('west_shop_4_approach',[12,0,18]),('west_shop_4',[16,.5,18]),('west_lane_south',[12,0,18]),('west_shop_3_approach',[12,0,9]),('west_shop_3',[16,.5,9]),('west_shop_3_exit',[12,0,9]),('west_shop_2_approach',[12,0,-9]),('west_shop_2',[16,.5,-9]),('west_shop_2_exit',[12,0,-9]),('mission_slab',[8,.25,-12.5]),('west_shop_1_approach',[12,0,-18]),('west_shop_1',[16,.5,-18]),('west_shop_1_exit',[12,0,-18]),('north_lane_west',[12,0,-22.8]),('hall_approach',[-10,0,-22.8]),('hall_porch',[-10,.5,-25.5]),('hall_departure',[-10,0,-22.8]),('east_shop_1_approach',[-12,0,-18]),('east_shop_1',[-16,.5,-18]),('east_shop_1_exit',[-12,0,-18]),('east_shop_2_approach',[-12,0,-9]),('east_shop_2',[-16,.5,-9]),('east_shop_2_exit',[-12,0,-9]),('east_shop_3_approach',[-12,0,9]),('east_shop_3',[-16,.5,9]),('east_shop_3_exit',[-12,0,9]),('east_shop_4_approach',[-12,0,18]),('east_shop_4',[-16,.5,18]),('east_shop_4_exit',[-12,0,18]),('east_lane',[-12,0,0]),('east_wreck',[-51,0,0])]
async def main():
 report={'complete':False,'scope':'route and interactions only' if os.environ.get('ATHEN_SALVAGE_ROUTE_ONLY') else 'views, route and interactions','views':[]};process=None;mode=None
 try:
  screen=subprocess.check_output(['xrandr','--current'],text=True);mode=next(line.split()[0] for line in screen.splitlines() if '*' in line)
  if mode!='1920x1080':subprocess.run(['xrandr','--output','DP-0','--mode','1920x1080'],check=True)
  for name in ('snapshot.json','environment.json','ack.json','command.json','qa-error.json'):(OUT/name).unlink(missing_ok=True)
  process=subprocess.Popen([str(R/'AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64'),'-force-glcore','-screen-fullscreen','1','-screen-width','1920','-screen-height','1080','-logFile',str(OUT/'Player.log'),'--athen-qa',str(OUT)],stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
  os.environ.update(ATHEN_NATIVE_DIR=str(OUT),ATHEN_NATIVE_PID=str(process.pid),ATHEN_EVIDENCE=str(OUT))
  from native_client import Client
  from desktop_input import focus,key
  for _ in range(300):
   if (OUT/'snapshot.json').exists():break
   if process.poll() is not None:raise RuntimeError('Native player exited')
   await asyncio.sleep(.2)
  else:raise TimeoutError('Native snapshot missing')
  await asyncio.sleep(2);d=focus();await asyncio.sleep(.5)
  def snapshot():return json.loads((OUT/'snapshot.json').read_text())
  if snapshot()['session']['state']=='Paused':
   key(d,'Escape',True);await asyncio.sleep(.08);key(d,'Escape',False);await asyncio.sleep(.3)
  assert (snapshot()['width'],snapshot()['height'])==(1920,1080)
  report['environment']=json.loads((OUT/'environment.json').read_text());assert report['environment']['actorCount']==int(os.environ.get('ATHEN_EXPECT_ACTORS','8'))
  async with Client() as c:
   for cam in ([] if os.environ.get('ATHEN_SALVAGE_ROUTE_ONLY') else json.loads(os.environ.get('ATHEN_ASSET_CAMERAS',json.dumps(CAMERAS)))):
    await c.command({'action':'view','camera':cam});await asyncio.sleep(1)
    await c.command({'action':'profileStart'});await asyncio.sleep(3);await c.command({'action':'profileStop'})
    frames=json.loads((OUT/'profile.json').read_text());(OUT/(cam+'-profile.json')).write_text(json.dumps(frames))
    fps=len(frames)/sum(f['dt'] for f in frames);v={'camera':cam,'averageFps':fps,'frames':len(frames),'p99FrameMs':sorted(f['dt']*1000 for f in frames)[int(len(frames)*.99)],'maxTrianglesAllPasses':max(f['tris'] for f in frames),'maxDrawCounter':max(f['draws'] for f in frames)}
    report['views'].append(v);assert fps>=58,v;await c.command({'action':'capture','name':cam});print(v,flush=True)
   await c.command({'action':'view','camera':'follow'})
   if os.environ.get('ATHEN_ACTOR_CHECK'):
    check=await asyncio.create_subprocess_exec(sys.executable,str(R/'tools/check_district_actor.py'));assert await check.wait()==0,'Yard mechanic animation failed'
   if not os.environ.get('ATHEN_SKIP_ROUTE'):
    route=json.loads(Path(os.environ['ATHEN_ASSET_ROUTE']).read_text()) if os.environ.get('ATHEN_ASSET_ROUTE') else ROUTE
    (OUT/'route.json').write_text(json.dumps(route));await c.command({'action':'profileStart'})
    check=await asyncio.create_subprocess_exec(sys.executable,str(R/'tools/walk_route.py'),str(OUT/'route.json'),'walking.json');assert await check.wait()==0,'Salvage route failed'
    await c.command({'action':'profileStop'});frames=json.loads((OUT/'profile.json').read_text());moving=[f for f in frames if f['speed']>1 and f['state']=='Play'];report['walkingFps']=len(moving)/sum(f['dt'] for f in moving);assert report['walkingFps']>=58
   check=await asyncio.create_subprocess_exec(sys.executable,str(R/'tools/city_loop_check.py'));assert await check.wait()==0,'City interactions failed'
   await c.command({'action':'quit'})
  await asyncio.to_thread(process.wait,timeout=15)
  log=(OUT/'Player.log').read_text();assert 'Exception:' not in log and 'NullReferenceException' not in log
  report['complete']=True;print('PASS: saved salvage models, native 1080p rendering, walking and interactions',flush=True)
 except Exception as e:report['error']=str(e);raise
 finally:
  if process and process.poll() is None:process.terminate();process.wait(timeout=10)
  if mode and mode!='1920x1080':subprocess.run(['xrandr','--output','DP-0','--mode',mode],check=True)
  (OUT/'report.json').write_text(json.dumps(report,indent=2))
asyncio.run(main())
