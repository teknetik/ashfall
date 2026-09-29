"""Bounded after-integration stills for the Basic General neon sign (t_196932d9): fixed audit cameras only, noon/dusk/night. No walking.
Run: ATHEN_NATIVE_DIR=<dir> ATHEN_NATIVE_PID=<pid> DISPLAY=:0 uv run --offline --with python-xlib --with pillow python capture_basic_general_sign_stills.py
"""
import asyncio, json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from native_client import Client
from desktop_input import focus_window
from capture_basic_general_sign import shot, start, set_hour, OUT, FIXED, HOURS


async def main():
    d, window = focus_window()
    c = Client(); records = []
    await start(c, d)
    for cam in FIXED:
        await c.command({'action': 'view', 'camera': cam.replace('cam_audit_', 'cam_audit_')})
        await asyncio.sleep(1.0)
        for hour_name, hour in HOURS:
            await set_hour(c, hour)
            rec = await shot(c, cam + '-' + hour_name)
            rec['hour'] = hour_name; records.append(rec)
            print(rec['path'], flush=True)
    (OUT / 'after-stills-report.json').write_text(json.dumps(dict(complete=True, captures=records), indent=2))
    d.close()

asyncio.run(main())
