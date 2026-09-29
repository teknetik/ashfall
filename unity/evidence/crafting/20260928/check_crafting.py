"""Native development-player crafting smoke: QA only positions the player/camera; real keyboard drives verbs."""
import asyncio, json, math, os, shutil, subprocess, sys, time
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[3] / 'tools'
sys.path.insert(0, str(TOOLS))
from native_client import Client
from settings_test_input import focus, key, window
from Xlib import X
from Xlib.ext import xtest

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent / 'native-smoke'
OUT.mkdir(parents=True, exist_ok=True)

async def main():
    env = dict(os.environ, DISPLAY=os.environ.get('DISPLAY', ':0'), XDG_CONFIG_HOME=str(OUT / 'config'))
    p = subprocess.Popen([str(ROOT / 'AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64'), '-force-glcore', '-screen-fullscreen', '0', '-screen-width', '1280', '-screen-height', '720', '-logFile', str(OUT / 'Player.log'), '--athen-qa', str(OUT), '--athen-qa-background'], env=env, stdout=(OUT / 'launcher.log').open('wb'), stderr=subprocess.STDOUT)
    os.environ.update(DISPLAY=env['DISPLAY'], ATHEN_NATIVE_DIR=str(OUT), ATHEN_NATIVE_PID=str(p.pid))
    report = {'passed': False, 'checks': [], 'pid': p.pid}
    def snap(): return json.loads((OUT / 'snapshot.json').read_text())
    def craft(): return json.loads((OUT / 'crafting.json').read_text())
    def focused():
        d = focus(); w = window(d); w.set_input_focus(X.RevertToParent, X.CurrentTime)
        g = w.get_geometry(); xy = d.screen().root.translate_coords(w, 0, 0)
        xtest.fake_input(d, X.MotionNotify, x=xy.x + g.width // 2, y=xy.y + g.height // 2)
        d.sync(); return d
    async def tap(name, seconds=.08, settle=.24):
        d=focused(); key(d,name,True); await asyncio.sleep(seconds); key(d,name,False); await asyncio.sleep(settle)
    try:
        async with Client() as c:
            async def cmd(**kw): await c.command(kw); await asyncio.sleep(.2)
            for _ in range(900):
                if p.poll() is not None: raise RuntimeError('Player exited before startup: '+str(p.returncode))
                if (OUT / 'snapshot.json').exists() and snap()['session']['state']=='MainMenu': break
                await asyncio.sleep(.1)
            else: raise TimeoutError('Player main menu unavailable')
            if shutil.which('hyprctl'):
                subprocess.run(['hyprctl','-i','0','dispatch',f'hl.dsp.window.float({{action="set",window="pid:{p.pid}"}})'],capture_output=True)
            await tap('Return')
            for _ in range(200):
                if snap()['session']['state']=='Play': break
                await asyncio.sleep(.1)
            assert snap()['session']['state']=='Play', snap()['session']['state']
            await cmd(action='goto',landmark='checkpoint_approach'); await cmd(action='view',camera='follow'); await cmd(action='cameraYaw',yaw=270); await tap('w',1.3)
            assert snap()['combat']['step']=='TakePistol',snap()['combat']['step']
            await cmd(action='goto',landmark='checkpoint_locker'); await tap('e')
            assert snap()['combat']['hasPistol'], 'Locker E did not grant pistol'
            report['checks'].append('Real E acquired scrap pistol at locker')
            await tap('7'); assert snap()['combat']['Armed']
            await cmd(action='goto',landmark='checkpoint_firingline')
            for i in range(1,4):
                await cmd(action='view',camera=f'cam_checkpoint_plate{i}'); await tap('f',.6)
            assert snap()['combat']['step']=='FirstContact',snap()['combat']['step']
            await cmd(action='goto',landmark='checkpoint_road'); await cmd(action='view',camera='follow')
            async def fight(until, seconds):
                end=time.monotonic()+seconds; shots=0; last_sample=0
                while time.monotonic()<end:
                    s=snap(); live=[x for x in s['combat']['enemies'] if x['alive']]
                    if s['combat']['step']==until: return shots
                    if not s['combat']['Armed']:
                        await tap('7')
                    if not live:
                        await asyncio.sleep(.15); continue
                    pos=s['player']['position']; e=min(live,key=lambda x:math.hypot(x['position'][0]-pos[0],x['position'][2]-pos[2]))
                    dx=e['position'][0]-pos[0]; dz=e['position'][2]-pos[2]
                    if time.monotonic()-last_sample>5:
                        report.setdefault('fight_samples',[]).append({'until':until,'player':pos,'enemy':e['position'],'health':e['health'],'shots':s['combat']['ShotsFired'],'yaw':s['camera']['yaw']})
                        last_sample=time.monotonic()
                    if until=='Complete' and math.hypot(dx,dz)>18:
                        # A knock-down returns to the checkpoint; use the QA landmark for the walk back.
                        await cmd(action='goto',landmark='depot_yard'); await cmd(action='view',camera='follow')
                        continue
                    await cmd(action='cameraYaw',yaw=math.degrees(math.atan2(dx,dz))%360)
                    if math.hypot(dx,dz)<6.5: await tap('f',.06,.22); shots+=1
                    else: await tap('w',.4,.1)
                raise TimeoutError(f'Did not reach {until}; step={snap()["combat"]["step"]}; crafting={craft()}')
            shots=await fight('Depot',120)
            first=snap()['session']['quantities']
            assert first['droid_servo_damaged']==0 and first['scrap_alloy']>=1 and first['nanite_residue']>=2,first
            report['checks'].append(f'First-contact drone real-fire clear ({shots} shots); no servo, alloy/residue credited')
            await cmd(action='goto',landmark='depot_approach'); await cmd(action='view',camera='follow')
            shots=await fight('Complete',210)
            s=snap(); q=s['session']['quantities']; c0=craft()
            report['pre_craft']={'quantities':q,'crafting':c0}
            assert q['droid_servo_damaged']>=1 and q['scrap_alloy']>=2 and q['nanite_residue']>=5,(q,c0)
            assert 'recipe_grip_stabilised_pistol' in c0['knownRecipes'],c0
            report['checks'].append(f'Depot workers real-fire clear ({shots} shots); guaranteed ingredients and servo unlock before completion')
            await cmd(action='goto',landmark='checkpoint_fabricator'); await cmd(action='view',camera='follow'); await tap('e')
            assert snap()['session']['state']=='Fabricator', (snap()['session']['state'],snap()['session']['notice'])
            await cmd(action='uiSnapshot'); assert craft()['fabricatorOpen']
            report['checks'].append('Real E opens field fabricator native modal')
            await tap('Return')
            for _ in range(30):
                if craft()['crafts']==1: break
                await asyncio.sleep(.1)
            assert craft()['crafts']==1,craft()
            q1=snap()['session']['quantities']
            report['post_craft']={'quantities':q1,'crafting':craft()}
            assert q1['droid_servo_damaged']==q['droid_servo_damaged']-1 and q1['scrap_alloy']==q['scrap_alloy']-2 and q1['nanite_residue']==q['nanite_residue']-5,q1
            assert q1['grip_stabilised_pistol']==1,q1
            report['checks'].append('Real Enter crafts: exactly 1 servo, 2 alloy, 5 residue spent; one grip carried')
            # Successful crafting moves keyboard focus to Fit; Enter is the second distinct verb.
            await tap('Return')
            for _ in range(30):
                if craft()['gripSlot']=='grip_stabilised_pistol': break
                await asyncio.sleep(.1)
            assert craft()['gripSlot']=='grip_stabilised_pistol',(craft(),snap()['session']['focused'])
            assert craft()['recoilFinal']==31 and snap()['session']['quantities']['grip_stabilised_pistol']==0,craft()
            report['post_fit']={'quantities':snap()['session']['quantities'],'crafting':craft()}
            report['checks'].append('Real keyboard fits grip; recoil 38→31 and carried grip consumed')
            await tap('Escape'); assert snap()['session']['state']=='Play'
            await cmd(action='goto',landmark='depot_approach'); await cmd(action='view',camera='follow')
            if not snap()['combat']['Armed']: await tap('7')
            await tap('f',.08,.25)
            assert abs(craft()['lastKickDegrees']-1.55)<.001,craft()
            report['checks'].append('Real F shot applies 1.55° kick with fitted grip')
            report['final']={'crafting':craft(),'quantities':snap()['session']['quantities']}
            report['passed']=True
            await cmd(action='quit')
    except Exception as e:
        report['error']=repr(e)
        raise
    finally:
        report['runtime_errors']=[x for x in (OUT/'Player.log').read_text(errors='replace').splitlines() if 'Exception:' in x or 'NullReference' in x] if (OUT/'Player.log').exists() else []
        (OUT/'report.json').write_text(json.dumps(report,indent=2))
        if p.poll() is None:
            p.terminate()
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill()

asyncio.run(main())
