#!/usr/bin/env python3
"""Brann, salvage dealer (1 Oct 2026): rig the unused roster model meshy/npc-roster-20260927/salvage_hauler and fetch
calm shopkeeper idles and conversational talk clips from the Meshy animation library.
Key only from MESHY_API_KEY in the environment; task records (no secrets) go to record.json beside this script.
Rig order: reuse the 27 Sep rig task if it is still retrievable and succeeded; otherwise rig again from the refine task,
or (if Meshy refuses the task input) from the stored textured.glb as a data URI.
Usage: python3 rig_dealer.py [clip_name=action_id ...]   (default: the CLIPS below)"""
import base64, json, os, sys, time, urllib.request, urllib.error
from pathlib import Path
KEY = os.environ.get('MESHY_API_KEY') or sys.exit('MESHY_API_KEY is required in the environment')
API = 'https://api.meshy.ai/openapi/v1'
HERE = Path(__file__).parent
SOURCE = HERE.parent / 'npc-roster-20260927/salvage_hauler'
OLD_RIG = '01a0e30c-8256-72b3-b5fc-403481bc6b6d'
REFINE = '01a0e30a-5208-7521-afd7-37a730a8537e'
HEIGHT = 1.82
# Shopkeeper behind a counter: weight-shifting / relaxed idles (no scanning guard idles) and conversational talk.
CLIPS = dict(a.split('=') for a in sys.argv[1:]) if sys.argv[1:] else {
    'idle_246': 246, 'idle_252': 252, 'talk_313': 313, 'talk_309': 309, 'talk_314': 314}
CLIPS = {k: int(v) for k, v in CLIPS.items()}


def call(method, url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, method=method,
                                 headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=300) as r: return json.loads(r.read())
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
    p = HERE / name
    if not p.exists(): p.write_bytes(urllib.request.urlopen(url, timeout=600).read())


rec_path = HERE / 'record.json'
rec = json.loads(rec_path.read_text()) if rec_path.exists() else {}
save = lambda: rec_path.write_text(json.dumps(rec, indent=2))
rec.update(name='Brann (salvage dealer)', source_model=str(SOURCE.relative_to(HERE.parents[1])), refine_task=REFINE)
rec.setdefault('credits', {})
if 'rig_task' not in rec:
    try:
        old = call('GET', f'{API}/rigging/{OLD_RIG}')
        rec['old_rig_lookup'] = dict(task=OLD_RIG, status=old.get('status'), task_error=old.get('task_error'))
        if old.get('status') == 'SUCCEEDED':
            rec['rig_task'] = OLD_RIG; rec['rig_input'] = 'existing 27 Sep rig task (input_task_id refine)'
            rec['height_meters'] = old.get('height_meters') or 1.84
    except RuntimeError as e:
        rec['old_rig_lookup'] = dict(task=OLD_RIG, error=str(e)[:200])
    save()
if 'rig_task' not in rec:
    try:
        rec['rig_task'] = call('POST', f'{API}/rigging', dict(input_task_id=REFINE, height_meters=HEIGHT))['result']
        rec['rig_input'] = f'input_task_id {REFINE}'
    except RuntimeError as e:
        print('task input refused:', e)
        uri = 'data:application/octet-stream;base64,' + base64.b64encode((SOURCE / 'textured.glb').read_bytes()).decode()
        rec['rig_task'] = call('POST', f'{API}/rigging', dict(model_url=uri, height_meters=HEIGHT))['result']
        rec['rig_input'] = 'model_url data URI of salvage_hauler/textured.glb'
    rec['height_meters'] = HEIGHT; save()
rig = wait('rigging', rec['rig_task'])
rec['credits']['rig'] = rig.get('consumed_credits')
fetch(rig['result']['rigged_character_glb_url'], 'rigged.glb')
ba = rig['result'].get('basic_animations') or {}
if ba.get('walking_glb_url'): fetch(ba['walking_glb_url'], 'basic_walk.glb')
save()
rec.setdefault('animation_tasks', {}); rec.setdefault('actions', {})
for name, aid in CLIPS.items():
    if name not in rec['animation_tasks']:
        rec['animation_tasks'][name] = call('POST', f'{API}/animations', dict(
            rig_task_id=rec['rig_task'], action_id=aid, post_process=dict(operation_type='change_fps', fps=30)))['result']
        rec['actions'][name] = aid; save()
for name, tid in rec['animation_tasks'].items():
    if (HERE / f'{name}.glb').exists() and name in rec['credits']: continue
    a = wait('animations', tid)
    rec['credits'][name] = a.get('consumed_credits')
    fetch(a['result']['animation_glb_url'], f'{name}.glb'); save()
rec['finished'] = time.strftime('%Y-%m-%dT%H:%M:%S'); save()
print('DONE credits', sum(v or 0 for v in rec['credits'].values()), flush=True)
