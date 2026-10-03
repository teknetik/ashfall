#!/usr/bin/env python3
"""Rig Carl's main_char_OK (decimated LOD0, 1k textures: blender/player_rig_input.glb) with Meshy and fetch the clips the
player needs on that rig. Resumable: task ids go to rig.json (no secrets); re-run to poll and download.
Key only from MESHY_API_KEY in the environment. Pre-approved Meshy use (AGENTS.md section 5).
Usage: rig_main_char.py [name_actionId ...]   default: the library clips below.
Outputs (this folder): rigged.glb (+ basic walking/running GLBs from the rig result), <name>.glb per clip."""
import base64, json, os, sys, time, urllib.request, urllib.error
from pathlib import Path
KEY = os.environ.get('MESHY_API_KEY') or sys.exit('MESHY_API_KEY is required in the environment')
API = 'https://api.meshy.ai/openapi/v1'
HERE = Path(__file__).parent
OUT = HERE
SOURCE_GLB = HERE / 'blender/player_rig_input.glb'
HEIGHT = 1.8
# Library ids from meshy/character-feel-20260927/animation-library.json: 252 Idle 13 (the accepted calm breathing idle),
# 95 Gun Hold Left Turn (pistol hold source), 573 Rifle Turn Left (rifle hold), 334 Lower Weapon Look Raise (rifle carry),
# 585 Aim Turn, 528 Strafe Left, 233 Walk Back, 234 Walk Forward While Shooting (the other retarget sources).
DEFAULT = {'idle_252': 252, 'aim_95': 95, 'rifleturn_573': 573, 'lower_334': 334, 'aimturn_585': 585, 'left_528': 528, 'back_233': 233, 'fwd_234': 234}
ACTIONS = {a: int(a.split('_')[1]) for a in sys.argv[1:]} or DEFAULT


def call(method, url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, method=method,
                                 headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=600) as r: return json.loads(r.read())
        except urllib.error.HTTPError as e:
            text = e.read().decode()[:400]
            if e.code in (429, 500, 502, 503, 504) and attempt < 4: time.sleep(15 * (attempt + 1)); continue
            raise RuntimeError(f'{method} {url.split("/v1/")[-1]} -> {e.code} {text}')
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < 4: time.sleep(15 * (attempt + 1)); continue
            raise


def wait(kind, tid):
    while True:
        t = call('GET', f'{API}/{kind}/{tid}')
        print(kind, tid[:8], t['status'], t.get('progress'), flush=True)
        if t['status'] == 'SUCCEEDED': return t
        if t['status'] in ('FAILED', 'CANCELED', 'EXPIRED'): sys.exit(f'{kind} {t["status"]}: {t.get("task_error")}')
        time.sleep(10)


def fetch(url, name):
    for attempt in range(4):
        try:
            (OUT / name).write_bytes(urllib.request.urlopen(url, timeout=600).read()); return
        except Exception as e:
            if attempt == 3: raise
            time.sleep(10)


rec_path = OUT / 'rig.json'
rec = json.loads(rec_path.read_text()) if rec_path.exists() else {}
save = lambda: rec_path.write_text(json.dumps(rec, indent=2))
if 'rig_task' not in rec:
    uri = 'data:application/octet-stream;base64,' + base64.b64encode(SOURCE_GLB.read_bytes()).decode()
    rec['rig_task'] = call('POST', f'{API}/rigging', dict(model_url=uri, height_meters=HEIGHT))['result']
    rec['rig_input'] = f'model_url data URI of {SOURCE_GLB.name} ({SOURCE_GLB.stat().st_size} bytes)'
    rec['height_meters'] = HEIGHT; rec['submitted'] = time.strftime('%Y-%m-%dT%H:%M:%S'); save()
rig = wait('rigging', rec['rig_task'])
rec['rig_credits'] = rig.get('consumed_credits'); rec['rig_result_keys'] = sorted(rig['result'].keys()); save()
if not (OUT / 'rigged.glb').exists(): fetch(rig['result']['rigged_character_glb_url'], 'rigged.glb')
basic = rig['result'].get('basic_animations') or {}
rec['basic_animation_keys'] = sorted(basic.keys())
for key, url in basic.items():
    if key.endswith('_glb_url') and 'armature' not in key:
        name = 'basic_' + key.replace('_glb_url', '') + '.glb'
        if not (OUT / name).exists(): fetch(url, name); print('fetched', name, flush=True)
save()
rec.setdefault('animation_tasks', {}); rec.setdefault('actions', {})
for name, aid in ACTIONS.items():
    if name not in rec['animation_tasks']:
        rec['animation_tasks'][name] = call('POST', f'{API}/animations', dict(rig_task_id=rec['rig_task'], action_id=aid, post_process=dict(operation_type='change_fps', fps=30)))['result']
        rec['actions'][name] = aid; save()
for name, tid in rec['animation_tasks'].items():
    if (OUT / f'{name}.glb').exists(): continue
    a = wait('animations', tid)
    rec.setdefault('animation_credits', {})[name] = a.get('consumed_credits')
    fetch(a['result']['animation_glb_url'], f'{name}.glb'); save()
rec['finished'] = time.strftime('%Y-%m-%dT%H:%M:%S'); save(); print('DONE')
