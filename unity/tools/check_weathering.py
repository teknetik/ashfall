"""Native 1080p weathering captures and real-input traversal, with honest timing.

Attach to an explicitly launched development player with ATHEN_NATIVE_PID and
ATHEN_NATIVE_DIR. No scene state, player preferences or release bridges are changed.
"""
import asyncio, json, os, pathlib, sys, subprocess, math, time
from native_client import Client
from desktop_input import focus, key
from Xlib import X
from Xlib.ext import xtest

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
            # Moving proximity review is separate from the timing samples.
            await c.command({'action':'view','camera':'follow'})
            await c.command({'action':'goto','landmark':'mission_slab'})
            await c.command({'action':'cameraYaw','yaw':180})
            d=focus();root=d.screen().root
            for wid in root.get_full_property(d.intern_atom('_NET_CLIENT_LIST'),X.AnyPropertyType).value:
                w=d.create_resource_object('window',wid);pid=w.get_full_property(d.intern_atom('_NET_WM_PID'),X.AnyPropertyType)
                if pid is not None and int(pid.value[0])==int(os.environ['ATHEN_NATIVE_PID']):
                    origin=root.translate_coords(w,0,0);break
            video=await asyncio.create_subprocess_exec('ffmpeg','-hide_banner','-loglevel','error','-y','-f','x11grab','-framerate','30','-video_size','1920x1080','-i',os.environ.get('DISPLAY',':0')+f'+{origin.x},{origin.y}','-t','15','-c:v','libx264','-preset','ultrafast','-crf','22','-pix_fmt','yuv420p',str(OUT/'terminal-walkthrough.mp4'))
            await asyncio.sleep(3)
            xtest.fake_input(d,X.MotionNotify,x=origin.x+960,y=origin.y+540);d.sync()
            for _ in range(18):
                xtest.fake_input(d,X.ButtonPress,4);xtest.fake_input(d,X.ButtonRelease,4);d.sync();await asyncio.sleep(.08)
            await asyncio.sleep(2)
            assert snap()['camera']['firstPerson'],'Real wheel zoom did not enter first person'
            await c.command({'action':'capture','name':'first-person-terminal'})
            for k,seconds in [('a',.4),('s',.6),('d',.4)]:
                key(d,k,True)
                try:await asyncio.sleep(seconds)
                finally:key(d,k,False)
                await asyncio.sleep(1)
            assert await video.wait()==0,'Walkthrough capture failed'
            report['walkthrough']='15 seconds, 1920x1080 at 30 FPS video; real strafe and wheel zoom; separate from timing'
        report['complete']=True
    except Exception as e:report['error']=str(e);raise
    finally:
        (OUT/'report.json').write_text(json.dumps(report,indent=2));key(d,'w',False)
        await c.command({'action':'quit'})
    print(json.dumps(report,indent=2))

if __name__=='__main__':asyncio.run(main())
