"""Supplemental saved native character cameras under the revised noon lighting."""
import asyncio, hashlib, json, os, sys
from pathlib import Path
from PIL import Image
sys.path.insert(0, '/home/teknetik/code/ao2/unity/tools')
from native_client import Client
from desktop_input import focus

async def main():
    out = Path(os.environ['ATHEN_NATIVE_DIR'])
    client = Client()
    focus()
    report = {'complete': False, 'purpose': __doc__, 'views': []}
    await client.command({'action':'timeReset'})
    await client.command({'action':'actorSnapshot'})
    try:
        for name in ['cam_motion_npc_mira_close', 'cam_motion_npc_mira_full',
                     'cam_motion_npc_torr_close', 'cam_motion_npc_torr_full',
                     'cam_motion_npc_vex_close', 'cam_motion_npc_vex_full',
                     'cam_motion_npc_linn_close', 'cam_motion_npc_linn_full']:
            image = out / (name + '.png')
            assert not image.exists()
            await client.command({'action':'view','camera':name})
            await asyncio.sleep(.6)
            await client.command({'action':'capture','name':name})
            for _ in range(60):
                try:
                    with Image.open(image) as im:
                        im.load()
                        assert im.size == (1920,1080)
                    break
                except (OSError,FileNotFoundError):
                    await asyncio.sleep(.1)
            else:
                raise TimeoutError(name)
            report['views'].append({'camera':name,'sha256':hashlib.sha256(image.read_bytes()).hexdigest()})
        report['complete'] = True
    finally:
        (out/'character-lighting-review.json').write_text(json.dumps(report,indent=2))
        await client.command({'action':'view','camera':'follow'})
    print('Captured eight native character lighting views.')

asyncio.run(main())
