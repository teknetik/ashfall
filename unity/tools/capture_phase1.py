"""Capture the Phase 1 native audit from an explicitly launched QA player.

Pass its evidence directory (containing pid and snapshot.json). Debug teleports
are used only to compose review images; they do not qualify traversal.
"""
import asyncio
import json
import os
from pathlib import Path
import sys

from native_client import Client
from desktop_input import focus, key

OUT = Path(sys.argv[1]).resolve()
os.environ.update(ATHEN_NATIVE_DIR=str(OUT), ATHEN_NATIVE_PID=(OUT / 'pid').read_text().strip())
VIEWS = ['cam_hill', 'cam_avenue', 'cam_gate', 'cam_grid', 'cam_whompah',
         'cam_hero', 'cam_terminal', 'cam_courtyard_facade', 'cam_shop_recovery_close',
         'cam_grounding_shop_back', 'cam_grounding_shop_side', 'cam_salvage_general',
         'cam_p1_hall_front', 'cam_p1_hall_door', 'cam_grounding_hall_back',
         'cam_p1_tree_roots', 'cam_fidelity_guard', 'cam_p1_vex_face']
if os.environ.get('ATHEN_PHASE1_AFTER'):
    VIEWS += ['cam_p1_finery_front', 'cam_p1_finery_door', 'cam_p1_finery_roof']


async def main():
    d = focus()
    c = Client()
    report = dict(complete=False, views=[], purpose='Native visual audit; debug positioning is not a route test')
    try:
        snapshot = json.loads((OUT / 'snapshot.json').read_text())
        if snapshot['session']['state'] == 'Paused':
            key(d, 'Escape', True)
            await asyncio.sleep(.1)
            key(d, 'Escape', False)
            await asyncio.sleep(.3)
        if (snapshot['width'], snapshot['height']) != (1920, 1080):
            await c.command({'action':'resize','width':1920,'height':1080})
            await asyncio.sleep(1.2)
            snapshot = json.loads((OUT / 'snapshot.json').read_text())
        assert (snapshot['width'], snapshot['height']) == (1920, 1080)
        report['measuredViewport'] = [snapshot['width'], snapshot['height']]
        await c.command({'action': 'settingsSnapshot'})
        report['settings'] = json.loads((OUT / 'settings.json').read_text())
        assert report['settings']['renderScale'] == 1
        report['environment'] = json.loads((OUT / 'environment.json').read_text())
        assert report['environment']['actorCount'] == 9
        # Keep the player away from the reviewed Vex, hall and tree cameras.
        await c.command({'action': 'goto', 'landmark': 'basic_general'})
        for name in VIEWS:
            await c.command({'action': 'view', 'camera': name})
            await asyncio.sleep(.65)
            await c.command({'action': 'capture', 'name': name})
            await asyncio.sleep(.2)
            report['views'].append(name)
        await c.command({'action': 'actorSnapshot'})
        report['complete'] = True
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        key(d, 'w', False)
        (OUT / 'capture-report.json').write_text(json.dumps(report, indent=2))
        await c.command({'action': 'quit'})
    print(json.dumps(dict(complete=True, views=len(VIEWS), output=str(OUT))))


if __name__ == '__main__':
    asyncio.run(main())
