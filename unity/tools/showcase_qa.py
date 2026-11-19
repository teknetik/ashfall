"""Shared helpers for the 19 Nov 2026 showcase native checks (unity/tools/check_showcase_*.py).

Wraps the real-input harness (unity/evidence/gameplay-v2/20260930-reqa2/qa.py): launches a private build copy
(ATHEN_EXE) on the QA display with its own config folder, HOME (so photo-mode PNGs land in the run folder, not in
~/Pictures) and save folder, records PASS/FAIL checks and captures, and writes report.json.

Output folder: argv[1] or ATHEN_OUT (default unity/evidence/showcase/20261119/qa/<script name>).
Run through ~/.local/state/ward-programme/showcase-20261119/native_check.sh NAME SCRIPT ATHEN_EXE=... (lock, cap, :5).
"""
import json, math, os, shutil, sys, time, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'unity/evidence/gameplay-v2/20260930-reqa2'))
import qa  # noqa: E402

if os.environ.get('ATHEN_EXE'):
    qa.EXE = Path(os.environ['ATHEN_EXE'])
NAME = Path(sys.argv[0]).stem.replace('check_showcase_', '')
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get('ATHEN_OUT', ROOT / 'unity/evidence/showcase/20261119/qa' / NAME)).resolve()
OUT.mkdir(parents=True, exist_ok=True)
report = {'name': NAME, 'exe': str(qa.EXE), 'exeMtime': time.ctime(qa.EXE.stat().st_mtime) if qa.EXE.exists() else None,
          'started': time.strftime('%Y-%m-%d %H:%M:%S'), 'checks': [], 'captures': [], 'notes': []}
CARL_SAVE = Path.home() / '.config/unity3d/Free Column/Athen Hill/ward-save.json'


def ok(cond, what, detail=None):
    report['checks'].append({'check': what, 'passed': bool(cond), 'detail': detail})
    print(('PASS ' if cond else 'FAIL ') + what + ('' if detail is None else ' :: ' + json.dumps(detail, default=str)[:400]), flush=True)
    save_report()
    return bool(cond)


def note(text, detail=None):
    report['notes'].append({'note': text, 'detail': detail})
    print('NOTE ' + text + ('' if detail is None else ' :: ' + json.dumps(detail, default=str)[:400]), flush=True)


def save_report():
    (OUT / 'report.json').write_text(json.dumps(report, indent=1, default=str))


def cap(name, layout=True):
    try:
        c = qa.capture(name, layout=layout)
        report['captures'].append(str(qa.RUN / (name + '.png')))
        return c
    except Exception as e:  # noqa: BLE001
        note('capture failed: ' + name, str(e))


def launch(run='run', save=None, extra=()):
    """Start the player with a private config, HOME and (optional) save folder."""
    run_dir = OUT / run
    if run_dir.exists():
        shutil.rmtree(run_dir)
    home = run_dir / 'home'
    home.mkdir(parents=True)
    old = os.environ.get('HOME')
    os.environ['HOME'] = str(home)
    try:
        qa.launch(run_dir, save_dir=save, extra=extra)
    finally:
        os.environ['HOME'] = old
    return run_dir


def start(continue_game=True, timeout=60):
    """Main menu -> Return (Continue when a save exists, otherwise New game) -> Play."""
    qa.wait_menu()
    qa.focus()
    qa.tap('Return')
    qa.wait(lambda: qa.state() == 'Play', timeout, what='Play')
    qa.release_all()
    time.sleep(1.0)


def stop():
    try:
        return qa.stop()
    except Exception as e:  # noqa: BLE001
        note('stop failed', str(e))


def errors(run=None):
    """Runtime exceptions in Player.log (ignores the known noise)."""
    out = []
    for e in qa.log_errors():
        t = e['text']
        if any(s in t for s in ('Licensing', 'memorysetup', 'Shader warning', 'ALSA', 'FMOD', 'pulse')):
            continue
        out.append(e)
    return out


def finish():
    try:
        errs = errors()
        ok(not [e for e in errs if 'Exception' in e['text'] or 'NullReference' in e['text']], 'no runtime exceptions in Player.log',
           [e['text'][:200] for e in errs][:8])
    except Exception as e:  # noqa: BLE001
        note('log scan failed', str(e))
    stop()
    failed = [c for c in report['checks'] if not c['passed']]
    report['passed'] = not failed
    report['summary'] = '%d/%d passed' % (len(report['checks']) - len(failed), len(report['checks']))
    report['finished'] = time.strftime('%Y-%m-%d %H:%M:%S')
    save_report()
    print(('PASS ' if not failed else 'FAIL ') + NAME + ' ' + report['summary'], flush=True)
    return 0 if not failed else 1


def run(body):
    """Run body(); record an uncaught error as a failed check; always finish."""
    try:
        body()
    except Exception as e:  # noqa: BLE001
        report['error'] = traceback.format_exc()
        ok(False, 'script completed without error', repr(e)[:400])
        try:
            cap('error-state', layout=True)
        except Exception:  # noqa: BLE001
            pass
    sys.exit(finish())


# ---------------------------------------------------------------- state helpers
def snap():
    return qa.snap()


def dev():
    qa.cmd('dev.state')
    time.sleep(.15)
    return qa.dev()


def feel():
    return (snap().get('combat') or {}).get('feel') or {}


def show():
    return snap().get('showcase') or {}


def hud():
    return snap().get('hud') or {}


def barks():
    return snap().get('barks') or {}


def mapstate():
    return snap().get('map') or {}


def sources(name_part=None, playing=None):
    a = (snap().get('audio') or {}).get('sources') or []
    return [s for s in a if (name_part is None or name_part.lower() in (s['name'] or '').lower() or name_part.lower() in (s['clip'] or '').lower())
            and (playing is None or s['playing'] == playing)]


def actors():
    qa.cmd('actorSnapshot')
    time.sleep(.4)
    return {a['name']: a for a in qa.read('actors.json')}


def time_set(hour, pause=True):
    qa.cmd('timeSet', hour=float(hour))
    qa.cmd('timePause', paused=pause)


def png_stats(path):
    """Size, mean luminance, alpha range and top/bottom brightness of a PNG (to tell upright, black, transparent)."""
    from PIL import Image, ImageStat
    with Image.open(path) as im:
        im.load()
        size, mode = im.size, im.mode
        rgba = im.convert('RGBA')
        a = rgba.getchannel('A')
        lum = rgba.convert('L')
        w, h = size
        top = ImageStat.Stat(lum.crop((0, 0, w, h // 3))).mean[0]
        bottom = ImageStat.Stat(lum.crop((0, 2 * h // 3, w, h))).mean[0]
        return dict(size=size, mode=mode, mean=round(ImageStat.Stat(lum).mean[0], 1), stddev=round(ImageStat.Stat(lum).stddev[0], 1),
                    alphaMin=a.getextrema()[0], alphaMax=a.getextrema()[1], top=round(top, 1), bottom=round(bottom, 1))


def wait_for(pred, timeout=10, step=.1, what='condition'):
    try:
        return qa.wait(pred, timeout, step, what)
    except TimeoutError:
        return None


def dist(a, b):
    return math.hypot(a[0] - b[0], a[-1] - b[-1])


# ---------------------------------------------------------------- fixture saves
SKILLS = ['armourcraft', 'armourHandling', 'awareness', 'blades', 'blunt', 'chemistry', 'dodging', 'electronics', 'energyWeapons', 'engineering', 'pistol', 'rifle']


def kit_save(folder, flags=(), orders_index=7, hour_note=None, extra_items=()):
    """Primer complete, Warden kit orders done, field rifle (precision barrel) primary + scrap pistol secondary, basic armour,
    Rifle 20 (the next-level enemies fixture, version 2)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    s = {'version': 2, 'savedUtc': '2026-11-19T12:00:00.0000000Z', 'build': 'qa', 'credits': 200, 'purchases': 0, 'sales': 0,
         'items': [{'itemId': 'medkit', 'quantity': 3}] + [{'itemId': i, 'quantity': q} for i, q in extra_items],
         'crafting': {'known': ['recipe_charge_cell_core', 'recipe_field_rifle', 'recipe_rifle_precision_barrel', 'recipe_grip_stabilised_pistol'],
                      'crafted': [{'id': 'recipe_grip_stabilised_pistol', 'count': 1}, {'id': 'recipe_field_rifle', 'count': 1}, {'id': 'recipe_rifle_precision_barrel', 'count': 1}], 'crafts': 3,
                      'fitted': [{'slot': 'grip', 'itemId': 'grip_stabilised_pistol'}],
                      'weapons': [{'weaponId': 'weapon_scrap_pistol', 'fitted': [{'slot': 'grip', 'itemId': 'grip_stabilised_pistol'}]},
                                  {'weaponId': 'weapon_field_rifle', 'fitted': [{'slot': 'barrel', 'itemId': 'rifle_precision_barrel'}]}]},
         'loot': {'rng': 'bc1721a626f0570d', 'rolls': 20, 'misses': [], 'collected': ['scrap_alloy', 'copper_filament', 'nanite_residue', 'droid_servo_damaged', 'rifle_receiver', 'warden_plate_carrier']},
         'bermsStep': 'Complete', 'hasPistol': True,
         'orders': {'index': orders_index, 'id': 'order_keep_charge', 'testFired': ['order_steady_hands'], 'reported': ['order_steady_hands', 'order_kit_helmet', 'order_long_arm', 'order_plate_carrier']},
         'city': {'visitedHill': True, 'boughtFlask': True, 'soldScrap': True, 'linked': True, 'spoken': ['npc_linn', 'npc_mira', 'npc_torr', 'npc_vex'],
                  'selectedDestination': '', 'flags': ['brann_met', 'tamsin_met'] + list(flags)},
         'character': {'version': 1, 'level': 2, 'experience': 0, 'attributePoints': 2, 'skillPoints': 6,
                       'attributes': [{'id': a, 'count': 10} for a in ['agility', 'endurance', 'intellect', 'perception', 'resolve', 'strength']],
                       'skills': [{'id': k, 'count': 20 if k in ('rifle', 'engineering') else 0} for k in SKILLS],
                       'equipped': [{'slot': 'primary', 'itemId': 'field_rifle'}, {'slot': 'secondary', 'itemId': 'scrap_pistol'}, {'slot': 'armour_chest', 'itemId': 'warden_plate_carrier'},
                                    {'slot': 'armour_head', 'itemId': 'field_helmet'}, {'slot': 'armour_arms', 'itemId': 'field_armguards'}, {'slot': 'armour_hands', 'itemId': 'field_gloves'},
                                    {'slot': 'armour_legs', 'itemId': 'field_leggings'}, {'slot': 'armour_feet', 'itemId': 'field_boots'}, {'slot': 'storage', 'itemId': 'field_backpack'}]}}
    (folder / 'ward-save.json').write_text(json.dumps(s, indent=1))
    return folder


def carl_save_copy(folder):
    """A copy of Carl's real save in a private folder (the original is only read)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CARL_SAVE, folder / 'ward-save.json')
    return folder
