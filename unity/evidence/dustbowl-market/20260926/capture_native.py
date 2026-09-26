"""Native development-build stills for the dust-bowl/market pass (static views, not performance qualification)."""
import asyncio, json, os, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'unity/tools'))
NATIVE = Path(__file__).parent / 'native'
os.environ['ATHEN_NATIVE_DIR'] = str(NATIVE)
from native_client import Client
OUT = Path(__file__).parent / 'native-captures'; OUT.mkdir(exist_ok=True)
async def main():
    c = Client()
    await c.command({'action': 'timeReset'}); await c.command({'action': 'timePause', 'paused': True})
    for hour in (16, 20.5):
        await c.command({'action': 'timeSet', 'hour': hour})
        for cam in ['cam_market', 'cam_market_lane', 'cam_market_produce', 'cam_market_cookfire', 'cam_avenue', 'cam_gate', 'cam_hero']:
            await c.command({'action': 'view', 'camera': cam}); await asyncio.sleep(3.0)
            name = f'{cam}-h{int(hour)}'
            await c.command({'action': 'capture', 'name': name})
            for _ in range(100):
                p = NATIVE / (name + '.png')
                if p.exists() and p.stat().st_size > 0: time.sleep(.3); (OUT / p.name).write_bytes(p.read_bytes()); break
                await asyncio.sleep(.1)
            print('captured', name, flush=True)
    await c.command({'action': 'timeReset'})
asyncio.run(main())
