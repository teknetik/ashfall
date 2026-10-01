"""Frame-timing A/B walk past the north avenue buildings (30 Sep 2026).

  uv run --offline --with python-xlib --with pillow python unity/tools/profile_north_walk.py OUT [--exe PATH]

Lane-only route (valid in the builds before and after the north avenue rebuild): West Gate -> east lane past Repairs and
Thread + Hide -> round Basic General's front -> across the north end -> west lane past Salvage and the Tool Exchange.
Walked with real W presses at 12:00 (profiled), then back the same way at 20:30 (profiled, lamps on). Run baseline and
new builds alternately (this desktop drifts +-1-1.5 ms between runs). Writes walk-profile.json into OUT.
"""
import argparse, asyncio, json, math, os, sys, time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from lookbook import launch, start_play, Run, summarize, ROOT  # noqa: E402

ROUTE = [('avenue', (12, 0, 0)), ('cross_south', (12.6, 0, 4.0)), ('east_lane_mid', (12.6, 0, 13.0)), ('lane_east_south', (11.0, 0, 18.6)),
         ('general_front', (8, 0, 20.8)), ('north_end', (0, 0, 22)), ('west_north', (-6, 0, 20.5)), ('salvage_lane', (-12.6, 0, 20.8)),
         ('west_lane', (-12.8, 0, 13.5)), ('west_lane_south', (-12.8, 0, 4.0))]


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out', type=Path)
    ap.add_argument('--exe', type=Path, default=ROOT / 'unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64')
    a = ap.parse_args()
    out = a.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    player = launch(out, a.exe); run = Run(out)
    rec = dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), exe=str(a.exe), load=open('/proc/loadavg').read().split()[:3])
    from desktop_input import focus, key
    try:
        await start_play(run, player)
        d = focus()

        def snap():
            for _ in range(20):
                try: return run.read('snapshot.json')
                except (json.JSONDecodeError, FileNotFoundError): time.sleep(.05)
            raise RuntimeError('snapshot unreadable')

        async def walk_to(name, target, tol=.3, limit=70):
            started = time.monotonic(); last = 999; stalls = 0
            while True:
                p = snap()['player']['position']; dx = target[0] - p[0]; dz = target[2] - p[2]; dist = math.hypot(dx, dz)
                if dist < tol: return
                if time.monotonic() - started > limit: raise RuntimeError('timeout walking to %s %s at %s' % (name, target, p))
                stalls = stalls + 1 if abs(last - dist) < .01 else 0
                if stalls >= 6: raise RuntimeError('BLOCKED before %s %s at %s' % (name, target, p))
                last = dist
                await run.command({'action': 'cameraYaw', 'yaw': math.degrees(math.atan2(dx, dz))}); await asyncio.sleep(.06)
                key(d, 'w', True)
                try: await asyncio.sleep(min(1.6, max(.025, (dist - .1) / 3.4)))
                finally: key(d, 'w', False)
                await asyncio.sleep(.08)

        async def profiled(label, route):
            await run.command({'action': 'profileStart'})
            for name, target in route:
                await walk_to(name, target)
            await run.command({'action': 'profileStop'}); await asyncio.sleep(.3)
            rec[label] = summarize(run.read('profile.json')); print(label, json.dumps(rec[label]), flush=True)

        await run.command({'action': 'timeSet', 'hour': 12}); await run.command({'action': 'timePause', 'paused': True})
        await run.command({'action': 'view', 'camera': 'follow'}); await run.command({'action': 'cameraBoom', 'boom': 4})
        await run.command({'action': 'reset'}); await asyncio.sleep(2)
        await profiled('noon', ROUTE)
        await run.command({'action': 'timeSet', 'hour': 20.5}); await run.command({'action': 'timePause', 'paused': True}); await asyncio.sleep(2)
        await profiled('night', list(reversed(ROUTE[:-1])))
        await run.command({'action': 'quit'}, timeout=5)
    finally:
        try: player.wait(timeout=10)
        except Exception:
            try: os.killpg(player.pid, 15)
            except Exception: pass
        try:
            d = focus()
            for k in ['w', 'a', 's', 'd']: key(d, k, False)
        except Exception: pass
        (out / 'walk-profile.json').write_text(json.dumps(rec, indent=1))


if __name__ == '__main__':
    asyncio.run(main())
