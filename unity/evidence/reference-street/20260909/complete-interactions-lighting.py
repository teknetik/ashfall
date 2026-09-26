"""Run unaffected city interaction and lighting checks after proximity-test retries."""
import asyncio, importlib.util, os
from pathlib import Path
spec=importlib.util.spec_from_file_location('qa','/home/teknetik/code/ao2/art/reference_street_20260909/verify_reference_street.py')
qa=importlib.util.module_from_spec(spec);spec.loader.exec_module(qa)

async def main():
    out=Path(os.environ['ATHEN_NATIVE_DIR'])
    os.environ['ATHEN_EVIDENCE']=str(out)
    from native_client import Client
    c=Client()
    report={'complete':False,'steps':[], 'identityMatchesMeasuredRun':qa.identity()==qa.read(out/'reference-identity-before.json')}
    assert report['identityMatchesMeasuredRun']
    assert not qa.authoring_processes()
    assert not (out/'city-loop.json').exists()
    assert not (out/'reference-lighting.json').exists()
    try:
        await c.command({'action':'profileStart'})
        try:
            entry=await qa.subprocess_check(out,'city_loop_check.py')
            report['steps'].append(entry)
        finally:
            await c.command({'action':'profileStop'})
            frames=qa.read(out/'profile.json')
            qa.write(out/'interaction-frames.json',frames)
            qa.write(out/'interaction-performance.json',{'complete':bool(report['steps']) and report['steps'][-1]['returncode']==0,'scope':'Separate city-loop interaction profile','allFrames':qa.summarize(frames)})
        assert entry['returncode']==0
        await qa.lighting(out)
        report['complete']=True
    finally:
        report['identityAfterMatchesMeasuredRun']=qa.identity()==qa.read(out/'reference-identity-before.json')
        qa.write(out/'interaction-lighting-completion.json',report)
    print('City-loop and lighting complete; source/build identity unchanged.',flush=True)

asyncio.run(main())
