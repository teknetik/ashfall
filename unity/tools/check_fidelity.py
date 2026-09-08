"""Native source-fidelity review at an explicit RTX 3060 quality profile.

Usage: check_fidelity.py baseline|restored [--route]
Uses a private Linux preference directory, never the developer's saved settings.
"""
import asyncio
import base64
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from native_client import Client
from desktop_input import focus, key

ROOT = Path(__file__).resolve().parents[1]
PHASE = sys.argv[1]
assert PHASE in ('baseline', 'restored')
OUT = Path(os.environ.get('ATHEN_FIDELITY_EVIDENCE', ROOT / 'evidence/fidelity/20260908')) / ('native-' + PHASE)
PROJECT = Path(os.environ.get('ATHEN_FIDELITY_PROJECT', ROOT / 'AthenHill'))
BUILD = PROJECT / 'Builds' / ('FidelityBaseline' if PHASE == 'baseline' else 'FidelityReview') / 'AthenHill.x86_64'
if os.environ.get('ATHEN_FIDELITY_BUILD'):
    BUILD = Path(os.environ['ATHEN_FIDELITY_BUILD'])
CAMERAS = ['cam_hill', 'cam_avenue', 'cam_gate', 'cam_terminal', 'cam_fidelity_guard',
           'cam_shop_recovery_close', 'cam_salvage_general', 'cam_fidelity_generator']
PROFILE = dict(width=1920, height=1080, windowMode=0, preset=2, renderPercent=100,
               shadows=3, antiAliasing=4, textureLimit=0, postProcessing=True,
               vSync=False, frameLimit=0)

def metrics(frames):
    values = sorted(f['dt'] * 1000 for f in frames)
    assert values
    return dict(samples=len(values), seconds=sum(values)/1000,
                averageFps=1000/statistics.mean(values),
                p50=values[int((len(values)-1)*.5)], p95=values[int((len(values)-1)*.95)],
                p99=values[int((len(values)-1)*.99)], maximum=max(values),
                framesOver33ms=sum(v > 33.33 for v in values),
                gpuTimingAvailable=any(f['gpuMs'] > 0 for f in frames),
                meanMainThreadMs=statistics.mean(f['mainMs'] for f in frames) if all(f['mainMs']>=0 for f in frames) else None,
                meanCpuFrameMs=statistics.mean(f['cpuMs'] for f in frames) if any(f['cpuMs']>0 for f in frames) else None,
                maxSetPass=max(f['setPass'] for f in frames),
                maxSubmittedTriangles=max(f['tris'] for f in frames),
                drawCounterAvailable=any(f['draws'] > 0 for f in frames))

def memory(pid):
    xml = ET.fromstring(subprocess.check_output(['nvidia-smi', '-q', '-x'], text=True))
    gpu = xml.find('gpu')
    match = [p for p in gpu.findall('./processes/process_info') if p.findtext('pid') == str(pid)]
    return dict(gpu=gpu.findtext('product_name'), total=gpu.findtext('fb_memory_usage/total'),
                totalDeviceUsed=gpu.findtext('fb_memory_usage/used'),
                playerFramebuffer=match[0].findtext('used_memory') if match else None,
                note='Device total includes Editor and other applications. Player framebuffer comes from the matching process PID.')

async def walkthrough(c, snap):
    """Record real movement separately, after all timing samples have stopped."""
    from Xlib import X
    from Xlib.ext import xtest
    from settings_test_input import window
    await c.command({'action':'view','camera':'follow'})
    await c.command({'action':'reset'})
    d=focus(); root=d.screen().root; w=window(d); p=root.translate_coords(w,0,0)
    geometry=w.get_geometry()
    assert (geometry.width,geometry.height)==(1920,1080)
    video=await asyncio.create_subprocess_exec('ffmpeg','-hide_banner','-loglevel','error','-y',
        '-f','x11grab','-framerate','30','-video_size','1920x1080',
        '-i',f'{os.environ["DISPLAY"]}+{p.x},{p.y}', '-t','26',
        '-c:v','libx264','-preset','veryfast','-crf','20','-threads','2',
        '-pix_fmt','yuv420p',str(OUT/'walkthrough.mp4'))
    try:
        await asyncio.sleep(1)
        key(d,'w',True);await asyncio.sleep(9);key(d,'w',False)
        xtest.fake_input(d,X.MotionNotify,x=p.x+960,y=p.y+540);d.sync()
        for _ in range(18):
            xtest.fake_input(d,X.ButtonPress,4);xtest.fake_input(d,X.ButtonRelease,4);d.sync()
            await asyncio.sleep(.06)
        await asyncio.sleep(1)
        assert snap()['camera']['firstPerson'],snap()['camera']
        await c.command({'action':'capture','name':'first-person-stairs'})
        key(d,'w',True);await asyncio.sleep(2);key(d,'w',False)
        await asyncio.sleep(2)
        for _ in range(18):
            xtest.fake_input(d,X.ButtonPress,5);xtest.fake_input(d,X.ButtonRelease,5);d.sync()
            await asyncio.sleep(.06)
        assert await video.wait()==0,'Walkthrough recording failed'
    finally:
        key(d,'w',False)
        if video.returncode is None: video.terminate();await video.wait()

async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT/'report.json').exists():
        raise RuntimeError('This evidence folder already has a report; preserve it before rerunning.')
    config = OUT/'config'
    encoded = base64.b64encode(json.dumps(PROFILE).encode()).decode()
    # Installed Unity writes unknown/unknown on this host; also seed the named
    # project directory so the profile survives a product-name metadata repair.
    for company, product in [('unknown','unknown'), ('Free Column','Athen Hill')]:
        directory = config/'unity3d'/company/product
        directory.mkdir(parents=True, exist_ok=True)
        (directory/'prefs').write_text('<unity_prefs version_major="1" version_minor="1">\n'
            f'<pref name="AthenHill.Settings.v1.QA.Video" type="string">{encoded}</pref>\n</unity_prefs>\n')
    for name in ('snapshot.json','ack.json','command.json','qa-error.json'):
        (OUT/name).unlink(missing_ok=True)
    report = dict(phase=PHASE, complete=False, requestedProfile=PROFILE, build=str(BUILD), views=[])
    process = None
    try:
        process = subprocess.Popen([str(BUILD), '-force-glcore', '-screen-fullscreen', '0',
            '-screen-width','1920','-screen-height','1080', '-logFile',str(OUT/'Player.log'),
            '--athen-qa',str(OUT)], env=dict(os.environ, XDG_CONFIG_HOME=str(config)),
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        os.environ.update(ATHEN_NATIVE_DIR=str(OUT), ATHEN_NATIVE_PID=str(process.pid), ATHEN_EVIDENCE=str(OUT))
        (OUT/'pid').write_text(str(process.pid))
        deadline=time.monotonic()+60
        while not (OUT/'snapshot.json').exists():
            if process.poll() is not None: raise RuntimeError('Native player exited')
            if time.monotonic()>deadline: raise TimeoutError('No native QA snapshot')
            await asyncio.sleep(.2)
        d=focus()
        await asyncio.sleep(2)
        def snap(): return json.loads((OUT/'snapshot.json').read_text())
        if snap()['session']['state']=='Paused':
            key(d,'Escape',True); await asyncio.sleep(.08); key(d,'Escape',False); await asyncio.sleep(.4)
        async with Client() as c:
            if (snap()['width'], snap()['height']) != (1920, 1080):
                await c.command({'action':'resize', 'width':1920, 'height':1080})
                await asyncio.sleep(2)
            await c.command({'action':'settingsSnapshot'})
            settings=json.loads((OUT/'settings.json').read_text())
            report['effectiveSettings']=settings
            assert (snap()['width'],snap()['height'])==(1920,1080),snap()
            assert settings['frameLimit']==-1 and settings['vSync']==0,settings
            assert settings['renderScale']==1 and settings['textureLimit']==0 and settings['msaa']==4,settings
            report['environment']=json.loads((OUT/'environment.json').read_text())
            assert report['environment']['actorCount']==9,report['environment']
            await c.command({'action':'actorSnapshot'})
            report['actors']=json.loads((OUT/'actors.json').read_text())
            if PHASE=='restored':
                guards=[a for a in report['actors'] if a['name']=='WardGuard']
                assert len(guards)==4 and all(a['triangles']==38071 for a in guards),report['actors']
                assert all(abs(a['meshLow'])<.05 and 1.76<a['meshHigh']<1.84 for a in guards),guards
            for camera in CAMERAS:
                focus()
                await c.command({'action':'view','camera':camera}); await asyncio.sleep(1.2)
                await c.command({'action':'capture','name':camera}); await asyncio.sleep(.3)
                await c.command({'action':'profileStart'}); await asyncio.sleep(5)
                await c.command({'action':'profileStop'})
                frames=json.loads((OUT/'profile.json').read_text())
                (OUT/(camera+'-frames.json')).write_text(json.dumps(frames))
                result=dict(camera=camera,**metrics(frames))
                report['views'].append(result)
                print(json.dumps(result),flush=True)
            report['memory']=memory(process.pid)
            await c.command({'action':'view','camera':'follow'})
            if '--route' in sys.argv:
                await c.command({'action':'reset'}); await asyncio.sleep(1)
                await c.command({'action':'profileStart'})
                for script in ['walk_route.py','city_loop_check.py']:
                    child=await asyncio.create_subprocess_exec(sys.executable,str(ROOT/'tools'/script),
                        stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.STDOUT)
                    output,_=await child.communicate()
                    (OUT/(script+'.log')).write_bytes(output)
                    if child.returncode: raise RuntimeError(f'{script} failed; inspect its saved log')
                    print(script+' passed',flush=True)
                    if script=='walk_route.py':
                        await c.command({'action':'profileStop'})
                        frames=json.loads((OUT/'profile.json').read_text())
                        shutil.copy2(OUT/'profile.json',OUT/'walking-frames.json')
                        report['walking']=metrics([f for f in frames if f['state']=='Play' and f['speed']>1])
                report['cityLoop']=snap()['session']
            report['performancePass']=all(v['averageFps']>=60 and v['p99']<=16.67 for v in report['views'])
            if 'walking' in report: report['performancePass'] &= report['walking']['averageFps']>=60 and report['walking']['p99']<=16.67
            if '--video' in sys.argv:
                await walkthrough(c,snap)
                report['walkthrough']='26 seconds at 30 FPS capture; separate from performance samples; includes real wheel zoom into first person.'
            await c.command({'action':'quit'})
            process.wait(timeout=15)
        log=(OUT/'Player.log').read_text()
        report['runtimeErrors']=[line for line in log.splitlines() if any(t in line for t in ('Exception:','NullReferenceException','Shader error','is not supported on this GPU'))]
        assert not report['runtimeErrors'],report['runtimeErrors']
        assert report['performancePass'],'RTX 3060 frame-time qualification failed; inspect raw samples'
        report['complete']=True
    except Exception as error:
        report['error']=repr(error)
        raise
    finally:
        if process and process.poll() is None:
            process.terminate();process.wait(timeout=10)
        (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')

asyncio.run(main())
