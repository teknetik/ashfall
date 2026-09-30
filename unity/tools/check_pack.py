"""Native check of the Ark-style field pack (30 Sep 2026): continue a copied save (with a few extra items added so the
grid, filters and loadout have something to show), then drive the pack with real X11 keyboard and mouse input and
capture each state at 1920x1080 plus one small-window view at 1280x720.

  uv run --offline --with python-xlib --with pillow python unity/tools/check_pack.py OUT --save SAVE_DIR

The original save is never touched. Writes OUT/report.json with focus/visibility checks, frame times with the pack
open and closed, and Player.log errors.
"""
import argparse, json, shutil, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'unity/evidence/gameplay-v2/20260930-reqa2'))
import qa  # noqa: E402

EXTRA = {'medkit': 2, 'scrap_coil': 1, 'micro_capacitor': 3, 'optic_lens_cracked': 1, 'alloy_plate': 2, 'wound_coil': 1,
         'charge_cell_core': 1, 'grip_stabilised_pistol': 1, 'barrel_bored_alloy': 1}

p = argparse.ArgumentParser(); p.add_argument('out', type=Path); p.add_argument('--save', type=Path, required=True)
a = p.parse_args()
out = a.out.resolve(); out.mkdir(parents=True, exist_ok=False)
save = out / 'save'; shutil.copytree(a.save, save)
f = save / 'ward-save.json'; s = json.loads(f.read_text())
have = {i['itemId']: i for i in s['items']}
for item, n in EXTRA.items():
    if item in have: have[item]['quantity'] += n
    else: s['items'].append({'itemId': item, 'quantity': n})
f.write_text(json.dumps(s))
report = {'extraItems': EXTRA, 'checks': {}}
checks = report['checks']


def layout_tiles(layout):
    return [e['name'] for e in layout['elements'] if e['visible'] and (e['name'] or '').startswith(('inv-', 'sch-'))]


def bounds(layout, name):
    e = qa.el(layout, name)
    return e['bounds'] if e else None


def centre(b):
    return b[0] + b[2] / 2, b[1] + b[3] / 2


def move(px, py):
    from Xlib import X
    from Xlib.ext import xtest
    d = qa.focus(center=False); w = qa.window()
    o = d.screen().root.translate_coords(w, 0, 0)
    xtest.fake_input(d, X.MotionNotify, x=o.x + int(px), y=o.y + int(py)); d.sync(); time.sleep(.15)


def drag(x0, y0, x1, y1, steps=12):
    move(x0, y0); qa.button(1, True); time.sleep(.08)
    for i in range(1, steps + 1):
        move(x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps)
    qa.button(1, False); time.sleep(.3)


def typed(text):
    for ch in text:
        qa.tap(ch, secs=.04, settle=.08)


def frame_times(name, seconds=6):
    prof = qa.profile_for(seconds, name)
    return prof


qa.launch(out / 'run', save_dir=save)
try:
    qa.wait_menu(); qa.focus(); qa.tap('Return'); qa.wait(lambda: qa.state() == 'Play', 30, what='Play after Continue')
    qa.cmd('resize', width=1920, height=1080); time.sleep(2)
    qa.cmd('timeSet', hour=17.0); qa.cmd('timePause', paused=True)
    qa.PARK = (1880, 60)
    report['closedFrames'] = frame_times('frames-closed')
    # Open with the real Tab key.
    qa.tap('Tab', settle=.8); qa.wait(lambda: qa.state() == 'Inventory', 5, what='pack open')
    time.sleep(1.0)
    lay = qa.ui()
    tiles = layout_tiles(lay)
    checks['open'] = dict(state=qa.state(), focused=qa.focused(), tiles=tiles, cols=[bounds(lay, n) for n in ('pack-col', 'you-col', 'preview-col', 'modal')])
    report['01'] = qa.capture('01-pack-1080')
    report['openFrames'] = frame_times('frames-open')
    # Keyboard: two cells right, then up to the chips and the tabs.
    qa.tap('Right'); qa.tap('Right'); checks['right2'] = qa.focused()
    qa.tap('Down'); checks['down'] = qa.focused()
    qa.tap('Up'); qa.tap('Up'); checks['upToChip'] = qa.focused()
    qa.tap('Up'); checks['upToTab'] = qa.focused()
    qa.tap('Right'); checks['rightTab'] = qa.focused(); qa.tap('Return', settle=.6)
    lay = qa.ui(); checks['schematics'] = layout_tiles(lay)
    report['02'] = qa.capture('02-schematics')
    qa.tap('Left'); qa.tap('Return', settle=.5); checks['backToPack'] = (qa.focused(), len(layout_tiles(qa.ui())))
    qa.tap('Down'); checks['chipAll'] = qa.focused()
    for _ in range(4): qa.tap('Right')
    checks['chipMods'] = qa.focused(); qa.tap('Return', settle=.5)
    lay = qa.ui(); checks['mods'] = layout_tiles(lay)
    report['03'] = qa.capture('03-filter-mods')
    for _ in range(4): qa.tap('Left')
    qa.tap('Return', settle=.4); checks['chipAllAgain'] = (qa.focused(), len(layout_tiles(qa.ui())))
    # Search: WASD letters type (they must not move focus); Down leaves the box for the grid.
    qa.tap('Left'); checks['search'] = qa.focused()
    typed('alloy'); time.sleep(.4)
    lay = qa.ui(); checks['searchTyped'] = dict(focused=qa.focused(), tiles=layout_tiles(lay), value=(qa.el(lay, 'pack-search') or {}).get('text'))
    report['04'] = qa.capture('04-search-alloy')
    qa.tap('Down'); checks['searchDown'] = qa.focused()
    qa.tap('Up'); qa.tap('Left'); checks['backToSearch'] = qa.focused()
    for _ in range(5): qa.tap('BackSpace', settle=.1)
    time.sleep(.3); checks['searchCleared'] = len(layout_tiles(qa.ui()))
    qa.tap('Down', settle=.4)
    # Mouse: hover the barrel slot (fitted Mark II mod), then turn the colonist by dragging.
    lay = qa.ui()
    b = bounds(lay, 'pack-slot-barrel')
    if b:
        move(*centre(b)); time.sleep(.4)
        lay = qa.ui(); checks['hoverBarrel'] = (qa.el(lay, 'inventory-overview-name') or {}).get('text')
        report['05'] = qa.capture('05-hover-barrel-slot')
    pv = bounds(lay, 'preview-view')
    if pv:
        cx, cy = centre(pv)
        drag(cx - 60, cy, cx + 140, cy)
        move(1880, 60); time.sleep(.4)
        report['06'] = qa.capture('06-colonist-turned')
    # Details on the lattice shard: click it, Enter, then Esc returns to the pack.
    lay = qa.ui(); sb = bounds(lay, 'inv-lattice_shard')
    if sb:
        qa.click_at(*centre(sb)); move(1880, 60); qa.tap('Return', settle=.6)
        lay = qa.ui()
        checks['details'] = dict(focused=qa.focused(), title=(qa.el(lay, 'details-title') or {}).get('text'),
                                 detailsVisible=(qa.el(lay, 'inventory-details') or {}).get('visible'),
                                 previewVisible=(qa.el(lay, 'preview-col') or {}).get('visible'))
        report['07'] = qa.capture('07-details-shard')
        qa.tap('Escape', settle=.5); checks['afterEsc'] = dict(state=qa.state(), focused=qa.focused())
    # Close with Tab; the colonist view camera must stop.
    qa.tap('Tab', settle=.6); checks['closed'] = qa.state()
    # Small window.
    qa.cmd('resize', width=1280, height=720); time.sleep(2.5)
    qa.tap('Tab', settle=1.0); lay = qa.ui()
    checks['small'] = dict(state=qa.state(), tiles=len(layout_tiles(lay)), cols=[bounds(lay, n) for n in ('pack-col', 'you-col', 'preview-col', 'modal')])
    report['08'] = qa.capture('08-pack-1280x720')
    qa.tap('Tab', settle=.5)
    qa.cmd('resize', width=1920, height=1080); time.sleep(1.5)
    report['errors'] = qa.log_errors()
finally:
    qa.stop()
(out / 'report.json').write_text(json.dumps(report, indent=1, default=str)); print(json.dumps(checks, default=str)[:4000])
