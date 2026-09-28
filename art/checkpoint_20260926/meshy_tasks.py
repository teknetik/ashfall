"""Use installed Meshy MCP; credentials supplied only through the environment."""
import asyncio,json,os,sys
from pathlib import Path
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
ROOT=Path('/home/teknetik/code/ao2/meshy/checkpoint-robots-20260926')
BRIEFS={
'range-target':dict(height=1.05,closest_view_m=1,prompt='Single heavy steel shooting range target plate, rectangular torso-shaped silhouette with chamfered upper corners and small square head tab, thick flat vertical steel armour plate with beveled perimeter and two bottom hinge lugs, industrial training equipment. Broad flat clean front face for painted target rings, scuffed steel edges, realistic welded construction. Only the target plate, no stand or base or legs, no bags, no pillows, no circular lamp shapes, no emissive lights, no text. Full object upright, neutral studio lighting.',polygons=28000),
'mining-droid':dict(height=2.3,closest_view_m=1,prompt='Heavy quadruped aquifer service robot, four clearly separated articulated steel legs with visible hydraulic knees and small angular steel cleated feet, broad low rectangular armoured engine chassis, compact recessed front sensor cluster, side-mounted articulated drill boom with auger bit, rear hose spool and water pump, industrial diesel machinery proportions, realistic sci-fi salvage construction, bolted panels, exposed pistons. No giant circular eye, no padded feet, no lamp shapes, no base, no text. Full object, legs spread in neutral stance.',polygons=65000),
'worker-droid':dict(height=2.1,closest_view_m=1,prompt='Heavy biped industrial cargo-loader robot, full body T pose for rigging, two separate legs with articulated hydraulic knees and small angular steel cleated feet, wide boxy armoured torso with bolted lifting frame, compact rectangular recessed sensor head, two separate arms with piston forearms and three-prong clamp hands. Believable functional machinery, thick mechanical joints, exposed cables, salvaged steel. No giant circular lamp head, no soft shoes, no pillow feet, no cloth, no ground or base, no text, realistic sci-fi.',polygons=60000),
'scrap-drone':dict(width=1.3,closest_view_m=1,prompt='Industrial inspection hover drone, compact armoured rectangular central chassis with recessed twin amber sensor lenses, two large ducted rotors on short side struts with visible fan blades inside protective rings, folded three-prong mechanical salvage claw underneath, exposed battery pack and cable connectors, bolted replaceable steel panels. Clear functional machinery, asymmetrical repair plates, realistic desert sci-fi. No legs, no lamp shapes, no soft forms, no pedestal or base, no text. Entire single object.',polygons=45000)}
def payload(r):
 for c in r.content:
  if c.type=='text':
   try:return json.loads(c.text)
   except ValueError:pass
 return {'raw': '\n'.join(c.text for c in r.content if c.type=='text')}

async def main():
 async with Client(StdioTransport(command='npx',args=['-y','@meshy-ai/meshy-mcp-server'],env={'MESHY_API_KEY':os.environ['MESHY_API_KEY']}),timeout=360) as c:
  if sys.argv[1]=='preview':
   tasks=payload(await c.call_tool('meshy_list_tasks',dict(task_type='text-to-3d',limit=12,response_format='json')))
   print('Recent task list inspected',flush=True)
   (ROOT/'prior-tasks.json').write_text(json.dumps(tasks,indent=2))
   for name,b in BRIEFS.items():
    if name!='range-target':continue
    d=ROOT/name;d.mkdir(exist_ok=True);f=d/'task.json'
    if f.exists():continue
    opts=dict(prompt=b['prompt'],ai_model='latest',model_type='standard',topology='triangle',target_polycount=b['polygons'],should_remesh=True,target_formats=['glb'],response_format='json')
    if name=='worker-droid':opts['pose_mode']='t-pose'
    r=payload(await c.call_tool('meshy_text_to_3d',opts));rec=dict(brief=b,preview=r,options=opts,usage='unknown');f.write_text(json.dumps(rec,indent=2));print(name,r,flush=True)
  elif sys.argv[1]=='finish':
   async def finish(name):
    d=ROOT/name;f=d/'task.json';rec=json.loads(f.read_text());tid=rec['preview']['task_id']
    r=payload(await c.call_tool('meshy_get_task_status',dict(task_id=tid,wait=True,timeout_seconds=300,response_format='json')))
    rec['preview_status']=r;f.write_text(json.dumps(rec,indent=2))
    opts=dict(preview_task_id=tid,enable_pbr=True,texture_resolution='4k',remove_lighting=True,texture_prompt='Sun-faded olive and worn ochre painted steel panels, bare steel at moving joints and localized edge wear, matte black rubber hoses, restrained amber sensor glass. Distinct mechanical materials, no directional highlights in base colour, no text.',target_formats=['glb'],response_format='json')
    if 'refine' not in rec:
     rec['refine']=payload(await c.call_tool('meshy_text_to_3d_refine',opts));rec['refine_options']=opts;f.write_text(json.dumps(rec,indent=2))
    tid=rec['refine']['task_id'];print(name,'refine',tid,flush=True)
    r=payload(await c.call_tool('meshy_get_task_status',dict(task_id=tid,wait=True,timeout_seconds=300,response_format='json')));rec['refine_status']=r;f.write_text(json.dumps(rec,indent=2))
    result=await c.call_tool('meshy_download_model',dict(task_id=tid,format='glb',save_to=str(d/'model.glb'),response_format='json')) if False else await c.call_tool('meshy_download_model',dict(task_id=tid,format='glb',save_to=str(d/'model.glb')))
    rec['download']=str(result.content);f.write_text(json.dumps(rec,indent=2));print(name,'downloaded',flush=True)
   await asyncio.gather(*(finish(n) for n in BRIEFS if n=='range-target'))
asyncio.run(main())
