#!/usr/bin/env python3
"""(2 Oct 2026 rifle clips: the same script with its record in player-rifle/.) Re-rig the player colonist (meshy/mpc model, rig stripped, 1k textures) and fetch library weapon/idle clips.
Key only from MESHY_API_KEY in the environment; task records (no secrets) go to ward-guard/rig.json.
The Sep 2026 rig task 01a07c81 is no longer retrievable (404), so a new rig is made from the same model; its clips
are retargeted onto the installed guard skeleton in Unity (world-space rotation deltas)."""
import base64, json, os, sys, time, urllib.request, urllib.error
from pathlib import Path
KEY = os.environ.get('MESHY_API_KEY') or sys.exit('MESHY_API_KEY is required in the environment')
API = 'https://api.meshy.ai/openapi/v1'
HERE = Path(__file__).parent
OUT = HERE / 'player-rifle'; OUT.mkdir(exist_ok=True)  # 2 Oct 2026: the 27 Sep rig task expired (404); new rig record here, rifle clips
MODEL_TASK = 'none-player-uses-upload'
SOURCE_GLB = HERE / 'player/colonist-unrigged-1k.glb'
# Library idles judged calm from the preview GIFs (previews/sheet_*.png): relaxed stance, no scanning.
ACTIONS = {a: int(a.split('_')[1]) for a in sys.argv[1:]} or {'idle_243': 243, 'idle_244': 244, 'idle_246': 246, 'idle_249': 249, 'idle_251': 251, 'idle_252': 252}


def call(method, url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, method=method,
                                 headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=300) as r: return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'{method} {url.split("/v1/")[-1]} -> {e.code} {e.read().decode()[:400]}')


def wait(kind, tid):
    while True:
        t = call('GET', f'{API}/{kind}/{tid}')
        print(kind, tid[:8], t['status'], t.get('progress'), flush=True)
        if t['status'] == 'SUCCEEDED': return t
        if t['status'] in ('FAILED', 'CANCELED', 'EXPIRED'): sys.exit(f'{kind} {t["status"]}: {t.get("task_error")}')
        time.sleep(10)


def fetch(url, name): (OUT / name).write_bytes(urllib.request.urlopen(url, timeout=300).read())


rec_path = OUT / 'rig.json'
rec = json.loads(rec_path.read_text()) if rec_path.exists() else {}
save = lambda: rec_path.write_text(json.dumps(rec, indent=2))
if 'rig_task' not in rec:
    try:
        rec['rig_task'] = call('POST', f'{API}/rigging', dict(input_task_id=MODEL_TASK, height_meters=1.78))['result']
        rec['rig_input'] = f'input_task_id {MODEL_TASK}'
    except RuntimeError as e:
        print('task input refused:', e)
        uri = 'data:application/octet-stream;base64,' + base64.b64encode(SOURCE_GLB.read_bytes()).decode()
        rec['rig_task'] = call('POST', f'{API}/rigging', dict(model_url=uri, height_meters=1.78))['result']
        rec['rig_input'] = f'model_url data URI of {SOURCE_GLB.name}'
    rec['height_meters'] = 1.78; save()
rig = wait('rigging', rec['rig_task'])
rec['rig_credits'] = rig.get('consumed_credits')
if not (OUT / 'rigged.glb').exists(): fetch(rig['result']['rigged_character_glb_url'], 'rigged.glb')
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
