"""Launch the dev player (lookbook.launch/start_play) and run check_hall_district_city_loop.py against it."""
import asyncio, os, runpy, sys, json
from pathlib import Path
TOOLS = Path('/home/teknetik/code/ao2/unity/tools'); sys.path.insert(0, str(TOOLS))
from lookbook import launch, start_play, Run, ROOT
out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=False)
player = launch(out, ROOT / 'unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64')
(out / 'pid').write_text(str(player.pid))
run = Run(out)
asyncio.run(start_play(run, player))
os.environ['ATHEN_NATIVE_DIR'] = str(out); os.environ['ATHEN_NATIVE_PID'] = str(player.pid)
try:
    os.chdir(TOOLS)
    runpy.run_path(str(TOOLS / 'check_hall_district_city_loop.py'), run_name='__main__')
finally:
    try: asyncio.run(run.command({'action': 'quit'}, timeout=5))
    except Exception: pass
    try: player.wait(timeout=15)
    except Exception: os.killpg(player.pid, 15)
