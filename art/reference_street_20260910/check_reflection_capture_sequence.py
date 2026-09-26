"""Native diagnostic: settled afternoon/night/noon capture allocations and transition cost.

Run only after the sole native review runner finishes. Preserves its evidence.
This does not qualify full-route performance or artistic quality.
"""
import asyncio,json,os,sys,time
from pathlib import Path
import capture_native_iteration as base
sys.path.insert(0,str(base.ROOT/'unity/tools'))
from native_client import Client
from desktop_input import focus

async def run(out):
    assert base.read(out/'review-runner-status.json')['complete']
    dest=out/'reflection-sequence.json';assert not dest.exists()
    pid=int((out/'pid').read_text());assert Path(os.readlink('/proc/'+str(pid)+'/exe')).name=='AthenHill.x86_64'
    os.environ.update(ATHEN_NATIVE_DIR=str(out),ATHEN_NATIVE_PID=str(pid));focus()
    client=Client();identity=base.identity();assert identity==base.read(out/'asset-passes-identity-after.json')
    report={'complete':False,'startedUtc':base.utc(),'steps':[],'scope':__doc__,'pid':pid,'buildIdentityUnchanged':None}
    def save():base.write(dest,report)
    async def clock():
        await client.command({'action':'timeState'});return base.read(out/'time-state.json')
    async def settle(hour,old):
        quiet=None;start=time.monotonic();obs=[]
        while time.monotonic()-start<30:
            s=await clock();obs.append({'elapsedSeconds':time.monotonic()-start,'state':s});r=s['reflections']
            assert s['paused'] and abs(s['hour']-hour)<.01 and r['failed']==0,s
            valid=not r['pending'] and r['completed']>=old+2
            if valid:
                assert s['realtimeReflectionsEnabled']
                assert all(p['mode']=='Realtime' and p['texturePresent'] and p['realtimeTextureCreated'] and p['textureWidth']==p['resolution'] for p in r['probes']),s
                quiet=quiet or time.monotonic()
                if time.monotonic()-quiet>=1.2:return obs
            else:quiet=None
            await asyncio.sleep(.15)
        raise TimeoutError(json.dumps(obs[-1]))
    try:
        await client.command({'action':'view','camera':'cam_reference_street'})
        await client.command({'action':'timePause','paused':True})
        for hour in [16,0,12]:
            before=await clock();assert abs(before['hour']-hour)>.3
            entry={'hour':hour,'before':before,'startedUtc':base.utc()};report['steps'].append(entry);save()
            await client.command({'action':'profileStart'})
            await client.command({'action':'timeSet','hour':hour})
            entry['observations']=await settle(hour,before['reflections']['completed'])
            await client.command({'action':'profileStop'})
            frames=base.read(out/'profile.json');base.write(out/('reflection-transition-hour-'+str(hour)+'-frames.json'),frames)
            entry['frameSamples']=len(frames);entry['complete']=True
            await client.command({'action':'capture','name':'reflection-sequence-hour-'+str(hour)})
            entry['capture']='reflection-sequence-hour-'+str(hour)+'.png';save()
        report['complete']=len(report['steps'])==3 and all(s['complete'] for s in report['steps'])
    except Exception as e:
        report['error']=repr(e);raise
    finally:
        for payload in [{'action':'profileStop'},{'action':'view','camera':'follow'},{'action':'timeReset'}]:
            try:await client.command(payload)
            except Exception as e:report.setdefault('cleanupErrors',[]).append(repr(e))
        report['buildIdentityUnchanged']=identity==base.identity();report['finishedUtc']=base.utc();report['runtimeErrors']=base.errors(out)
        report['complete']=bool(report['complete'] and report['buildIdentityUnchanged'] and not report.get('cleanupErrors') and not report['runtimeErrors']['matchingLines'] and not report['runtimeErrors']['qaError']);save()
    assert report['complete'],report
    print('Native afternoon/night/noon sequence completed with two new probe captures per transition, valid textures and zero failures.')
if __name__=='__main__':asyncio.run(run(Path(sys.argv[1]).resolve()))
