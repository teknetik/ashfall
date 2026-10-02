#!/usr/bin/env python3
"""Ranged enemies (2 Oct 2026): rig the chosen feral gunner model with Meshy auto-rigging and fetch library clips.
Key only from MESHY_API_KEY in the environment; task records (no secrets) go to record.json (key 'gunner_rig').
The model goes in as a data URI of its textured GLB (keeps the PBR maps, as for Brann on 1 Oct 2026).
Usage: python3 rig_gunner.py <model.glb> [name=action_id ...]   (default: CLIPS below). Re-runnable; finished
downloads are skipped. Clips land in gunner/rig/<name>.glb."""
import base64, json, os, sys, time, urllib.request, urllib.error
from pathlib import Path
KEY = os.environ.get('MESHY_API_KEY') or sys.exit('MESHY_API_KEY is required in the environment')
API = 'https://api.meshy.ai/openapi/v1'
HERE = Path(__file__).parent
OUT = HERE / 'gunner' / 'rig'; OUT.mkdir(parents=True, exist_ok=True)
MODEL = Path(sys.argv[1])
HEIGHT = 2.0
# Candidates chosen from the library preview GIFs (previews/sheet_*.png); final picks are made from Blender renders
# of these clips on the gunner itself.
CLIPS = dict(a.split('=') for a in sys.argv[2:]) if sys.argv[2:] else {
    'idle_alert_2': 2, 'idle_combat_89': 89, 'idle_1_11': 11,
    'walk_casual_30': 30, 'walk_fight_21': 21, 'walk_shoot_234': 234,
    'run_2_14': 14, 'run_rifle_511': 511,
    'aim_gunhold_95': 95, 'shoot_run_98': 98, 'jab_right_192': 192,
    'strafe_left_gun_528': 528, 'strafe_left_crouch_525': 525, 'strafe_right_crouch_526': 526,
    'hit_178': 178, 'hit_electro_172': 172, 'hit_gunshot_177': 177,
    'death_electro_181': 181, 'death_back_183': 183, 'death_forward_184': 184}
CLIPS = {k: int(v) for k, v in CLIPS.items()}


def call(method, url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, method=method,
                                 headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=600) as r: return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500: time.sleep(15 * (attempt + 1)); continue
            raise RuntimeError(f'{method} {url.split("/openapi/")[-1]} -> {e.code} {e.read().decode()[:400]}')
        except urllib.error.URLError: time.sleep(15 * (attempt + 1))
    raise RuntimeError(f'{method} {url} failed after retries')


def wait(kind, tid):
    while True:
        t = call('GET', f'{API}/{kind}/{tid}')
        print(kind, tid[:8], t['status'], t.get('progress'), flush=True)
        if t['status'] == 'SUCCEEDED': return t
        if t['status'] in ('FAILED', 'CANCELED', 'EXPIRED'): raise RuntimeError(f'{kind} {tid} {t["status"]}: {t.get("task_error")}')
        time.sleep(10)


def fetch(url, name):
    p = OUT / name
    if not p.exists(): p.write_bytes(urllib.request.urlopen(url, timeout=900).read())


rec_path = HERE / 'record.json'
rec = json.loads(rec_path.read_text()) if rec_path.exists() else {}
r = rec.setdefault('gunner_rig', {})
def save():  # merge: other scripts write other keys of record.json concurrently
    cur = json.loads(rec_path.read_text()) if rec_path.exists() else {}
    cur['gunner_rig'] = r; rec_path.write_text(json.dumps(cur, indent=2))
r.setdefault('credits', {})
if 'rig_task' not in r:
    uri = 'data:application/octet-stream;base64,' + base64.b64encode(MODEL.read_bytes()).decode()
    r['rig_task'] = call('POST', f'{API}/rigging', dict(model_url=uri, height_meters=HEIGHT))['result']
    r.update(rig_input=f'model_url data URI of {MODEL.relative_to(HERE)}', height_meters=HEIGHT); save()
rig = wait('rigging', r['rig_task'])
r['credits']['rig'] = rig.get('consumed_credits')
fetch(rig['result']['rigged_character_glb_url'], 'rigged.glb')
for k, u in (rig['result'].get('basic_animations') or {}).items():
    if isinstance(u, str) and k.endswith('glb_url'): fetch(u, 'basic_' + k.replace('_glb_url', '') + '.glb')
save()
r.setdefault('animation_tasks', {}); r.setdefault('actions', {})
for name, aid in CLIPS.items():
    if name not in r['animation_tasks']:
        r['animation_tasks'][name] = call('POST', f'{API}/animations', dict(
            rig_task_id=r['rig_task'], action_id=aid, post_process=dict(operation_type='change_fps', fps=30)))['result']
        r['actions'][name] = aid; save()
for name, tid in r['animation_tasks'].items():
    if (OUT / f'{name}.glb').exists() and name in r['credits']: continue
    a = wait('animations', tid)
    r['credits'][name] = a.get('consumed_credits')
    fetch(a['result']['animation_glb_url'], f'{name}.glb'); save()
r['finished'] = time.strftime('%Y-%m-%dT%H:%M:%S'); save()
print('DONE credits', sum(v or 0 for v in r['credits'].values()), flush=True)
