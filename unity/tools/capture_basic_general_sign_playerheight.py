"""Two player-height views of the Basic General neon sign (t_196932d9): walk (real keys) to two lane points, aim, capture noon. Bounded, no retries."""
import asyncio, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from native_client import Client
from desktop_input import focus_window
from capture_basic_general_sign import shot, set_hour, aim, OUT, SIGN
from capture_tool_exchange_display import walk_to


async def main():
    d, window = focus_window()
    c = Client(); recs = []
    await c.command({'action': 'view', 'camera': 'follow'})
    await set_hour(c, 12.0)
    for name, pos in [('fp_sign_lane_far', (8.0, 0.0, 24.0)), ('fp_sign_street', (8.0, 0.0, 20.0)), ('fp_sign_close', (8.0, 0.0, 19.0))]:
        res = await asyncio.wait_for(walk_to(c, d, pos, .3, 40), timeout=45)
        await aim(c, res['position'], SIGN)
        await asyncio.sleep(.6)
        r = await shot(c, name + '-noon'); r['reached'] = res['position']; recs.append(r); print(r['path'], flush=True)
    (OUT / 'after-playerheight-report.json').write_text(json.dumps(dict(complete=True, captures=recs), indent=2))
    d.close()

asyncio.run(main())
