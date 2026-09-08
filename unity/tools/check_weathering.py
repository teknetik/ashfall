"""Native 1080p weathering captures and real-input traversal, with honest timing.

Attach to an explicitly launched development player with ATHEN_NATIVE_PID and
ATHEN_NATIVE_DIR. No scene state, player preferences or release bridges are changed.
"""
import asyncio, json, os, pathlib, sys, subprocess, math, time
from native_client import Client
from desktop_input import focus, key

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=pathlib.Path(os.environ['ATHEN_NATIVE_DIR'])
VIEWS=['cam_hill','cam_avenue','cam_gate','cam_grid','cam_whompah','cam_hero','cam_terminal','cam_wear_terminal','cam_wear_steps','cam_wear_wall']

def stats(frames):
    values=sorted(f['dt']*1000 for f in frames)
    def pct(p):return values[min(len(values)-1,int((len(values)-1)*p))]
    return dict(frames=len(frames),seconds=sum(values)/1000,averageFps=1000*len(values)/sum(values),p50Ms=pct(.5),p95Ms=pct(.95),p99Ms=pct(.99),maxMs=max(values),hitchesOver33ms=sum(v>33.33 for v in values),meets60fpsAndP99=1000*len(values)/sum(values)>=60 and pct(.99)<=16.67)

async def main():
    report={'phase':sys.argv[1],'complete':False,'views':[]}
    d=focus(); c=Client()
    def snap():return json.loads((OUT/'snapshot.json').read_text())
    async def tap(k):
        key(d,k,True);await asyncio.sleep(.12);key(d,k,False);await asyncio.sleep(.25)
    try:
        if snap()['session']['state']=='Paused':await tap('Escape')
        assert (snap()['width'],snap()['height'])==(1920,1080)
        report['environment']=json.loads((OUT/'environment.json').read_text())
        await c.command({'action':'settingsSnapshot'});report['settings']=json.loads((OUT/'settings.json').read_text())
        assert report['environment']['actorCount']==9
        assert report['settings']['renderScale']==1
        for view in VIEWS:
            await c.command({'action':'view','camera':view});await asyncio.sleep(.65)
            await c.command({'action':'capture','name':view});await asyncio.sleep(.3)
            report['views'].append(view)
        await c.command({'action':'profileStart'});await asyncio.sleep(10);await c.command({'action':'profileStop'})
        frames=json.loads((OUT/'profile.json').read_text());report['fixedViewTiming']=stats(frames)
        (OUT/'fixed-profile.json').write_text(json.dumps(frames))
        if sys.argv[1]=='after':
            await c.command({'action':'view','camera':'follow'});await c.command({'action':'reset'})
            route=[['west_stair_approach',[12,0,0]],['hill_tree',[4,1.5,0]],['north_stair_top',[0,1.5,-4]],['north_stair_bottom',[0,0,-12]],['mission_slab',[8,.25,-12.4]],['terminal_stand_1',[10,.25,-12.6]],['terminal_stand_3',[6,.25,-12.6]],['slab_departure',[8,0,-10.8]],['clear_lane',[12,0,-10.8]],['north_lane',[12,0,-23]],['service_lane',[33,0,-23]],['wall_approach',[44.5,0,-15]],['notices',[44.5,0,-10.5]],['leak_corner',[44.5,0,-7.4]]]
            routepath=OUT/'route.json';routepath.write_text(json.dumps(route));os.environ['ATHEN_EVIDENCE']=str(OUT)
            await c.command({'action':'profileStart'})
            process=await asyncio.create_subprocess_exec(sys.executable,str(ROOT/'tools/walk_route.py'),str(routepath),'walking.json')
            assert await process.wait()==0,'Affected route failed'
            await c.command({'action':'profileStop'})
            frames=json.loads((OUT/'profile.json').read_text());(OUT/'traversal-profile.json').write_text(json.dumps(frames));report['traversalTiming']=stats(frames)
            process=await asyncio.create_subprocess_exec(sys.executable,str(ROOT/'tools/city_loop_check.py'))
            assert await process.wait()==0,'City verbs failed'
            report['routeAndVerbs']=True
        report['complete']=True
    except Exception as e:report['error']=str(e);raise
    finally:
        (OUT/'report.json').write_text(json.dumps(report,indent=2));key(d,'w',False)
        await c.command({'action':'quit'})
    print(json.dumps(report,indent=2))

if __name__=='__main__':asyncio.run(main())
