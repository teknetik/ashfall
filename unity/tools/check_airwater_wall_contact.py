"""Real-key contact test at the Air + Water filter bank (t_3041b425): walk from the porch straight into the wall between vessel 1 and 2 and hold W.
The fittings carry no collider (by design: 10 mm beyond the retained collars, inside the porch zone), so the controller stops at the unchanged wall proxy.
Records the stop position, first-person camera position and the camera overlap list. Run via run_native.sh <native-dir> check_airwater_wall_contact.py <out.json>."""
import asyncio, json, math, os, sys
from pathlib import Path
from native_client import Client
from desktop_input import focus, key
from capture_tool_exchange_display import walk_to, snap, OUT


async def main():
    out = sys.argv[1]
    d = focus(); c = Client()
    await c.command({'action': 'cameraBoom', 'boom': 0})
    rec = {}
    await walk_to(c, d, (-13, 0, -7.7), .3, 60)  # lane first: a direct diagonal would hit the porch edge
    await walk_to(c, d, (-16.4, .5, -7.7), .3, 60)  # porch, between vessels 1 and 2 (world z -8.1 / -7.3)
    await c.command({'action': 'cameraYaw', 'yaw': -90}); await c.command({'action': 'cameraPitch', 'pitch': 5}); await asyncio.sleep(.4)
    key(d, 'w', True)
    try:
        await asyncio.sleep(2.0); a = snap(); await asyncio.sleep(1.5); b = snap()
    finally: key(d, 'w', False)
    rec['first'] = a['player']['position']; rec['second'] = b['player']['position']; rec['displacementM'] = math.dist(a['player']['position'], b['player']['position'])
    rec['camera'] = b['camera']; rec['grounded'] = b['player']['grounded']
    await c.command({'action': 'capture', 'name': 'wall_contact_firstperson'})
    (OUT / out).write_text(json.dumps(rec, indent=2)); print(json.dumps(rec)[:500])

asyncio.run(main())
