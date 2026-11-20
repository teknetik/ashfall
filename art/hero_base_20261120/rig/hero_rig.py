#!/usr/bin/env python3
"""Hero base (20 Nov 2026): rig the Rodin mesh with Meshy and fetch test clips. Resumable; nothing is re-submitted.
Rodin GLB (public fal URL, or a local file sent as a data URI) -> Meshy rigging (height, finger bones) -> the free
walk/run clips that come with the rig, plus any library clips listed in CLIPS.
Key only from MESHY_API_KEY (environment or the project .env); never printed or written. Records: record.json, ledger.json.
Usage: hero_rig.py <model_url | path/to/model.glb> [--height 1.88] [--stop-after rig]
Meshy use is pre-approved (AGENTS.md section 5). Rigging 5 credits, 3 per library clip."""
import base64, json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
API = 'https://api.meshy.ai/openapi/v1'
COST = {'rig': 5, 'clip': 3}
# name -> Meshy library action id (ids: meshy/character-feel-20260927/animation-library.json). The three the game
# already uses on the player: rifle hold source, lowered carry source, idle.
CLIPS = {'rifle_573': 573, 'carry_334': 334, 'idle_248': 248,
         # the rest of the player's source set (Art/CharacterMotion/Source/Player/Player_<name>.glb), fetched natively
         'aim_95': 95, 'draw_222': 222, 'back_233': 233, 'fwd_234': 234, 'left_528': 528, 'aimturn_585': 585,
         'idle_243': 243, 'idle_252': 252, 'turnl_576': 576, 'turnr_586': 586}


def env_key():
    k = os.environ.get('MESHY_API_KEY')
    if k: return k
    for line in Path('/home/teknetik/code/ao2/.env').read_text().splitlines():
        if line.startswith('MESHY_API_KEY='): return line.split('=', 1)[1].strip().strip('"\'')
    sys.exit('MESHY_API_KEY missing')
KEY = env_key()


def call(method, url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, method=method,
                                 headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'})
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=900) as r: return json.loads(r.read())
        except urllib.error.HTTPError as e:
            text = e.read().decode()[:600]
            if e.code == 429 or e.code >= 500: time.sleep(15 * (attempt + 1)); continue
            raise RuntimeError(f'{method} {url.split("/v1/")[-1]} -> {e.code} {text}')
        except (urllib.error.URLError, TimeoutError): time.sleep(15 * (attempt + 1))
    raise RuntimeError('failed after retries')


def spend(rec, what, cost):
    bal = call('GET', f'{API}/balance')['balance']
    if bal - cost < 0: raise SystemExit(f'refused {what}: balance {bal}, cost {cost}')
    led = HERE / 'ledger.json'; rows = json.loads(led.read_text()) if led.exists() else []
    rows.append({'time': time.strftime('%Y-%m-%dT%H:%M:%S'), 'call': what, 'expected_cost': cost, 'balance_before': bal})
    led.write_text(json.dumps(rows, indent=1) + '\n')


def wait(kind, tid):
    while True:
        t = call('GET', f'{API}/{kind}/{tid}')
        print(kind, tid[:8], t['status'], t.get('progress'), flush=True)
        if t['status'] == 'SUCCEEDED': return t
        if t['status'] in ('FAILED', 'CANCELED', 'EXPIRED'): raise SystemExit(f'{kind} {t["status"]}: {t.get("task_error")}')
        time.sleep(15)


def fetch(url, path):
    if path.exists(): return
    for attempt in range(4):
        try: path.write_bytes(urllib.request.urlopen(url, timeout=900).read()); return
        except Exception:
            if attempt == 3: raise
            time.sleep(10)


def main():
    src = sys.argv[1]
    height = float(sys.argv[sys.argv.index('--height') + 1]) if '--height' in sys.argv else 1.88
    stop = sys.argv[sys.argv.index('--stop-after') + 1] if '--stop-after' in sys.argv else ''
    rp = HERE / 'record.json'
    rec = json.loads(rp.read_text()) if rp.exists() else {}
    save = lambda: rp.write_text(json.dumps(rec, indent=2) + '\n')
    rec.setdefault('credits', {})
    if 'rig_task' not in rec:
        if src.startswith('http'):
            model_url = src; rec['model_source'] = src
        else:
            model_url = 'data:model/gltf-binary;base64,' + base64.b64encode(Path(src).read_bytes()).decode()
            rec['model_source'] = str(Path(src).resolve())
        rec['rig_options'] = dict(height_meters=height, include_fingers=True); save()
        spend(rec, 'rigging', COST['rig'])
        rec['rig_task'] = call('POST', f'{API}/rigging', dict(model_url=model_url, **rec['rig_options']))['result']
        rec['rig_submitted'] = time.strftime('%Y-%m-%dT%H:%M:%S'); save()
    r = wait('rigging', rec['rig_task'])
    rec['credits']['rig'] = r.get('consumed_credits'); save()
    fetch(r['result']['rigged_character_glb_url'], HERE / 'rigged.glb')
    for key, url in (r['result'].get('basic_animations') or {}).items():
        if url and key.endswith('_glb_url') and 'armature' not in key:
            fetch(url, HERE / ('basic_' + key.replace('_glb_url', '') + '.glb'))
    if stop == 'rig': print('RIG DONE', flush=True); return
    rec.setdefault('animation_tasks', {}); rec.setdefault('actions', {})
    for clip, aid in CLIPS.items():
        if clip not in rec['animation_tasks']:
            spend(rec, 'animation ' + clip, COST['clip'])
            rec['animation_tasks'][clip] = call('POST', f'{API}/animations', dict(
                rig_task_id=rec['rig_task'], action_id=aid, post_process=dict(operation_type='change_fps', fps=30)))['result']
            rec['actions'][clip] = aid; save()
    for clip, tid in rec['animation_tasks'].items():
        a = wait('animations', tid)
        rec['credits'][clip] = a.get('consumed_credits'); save()
        fetch(a['result']['animation_glb_url'], HERE / f'{clip}.glb')
    rec['finished'] = time.strftime('%Y-%m-%dT%H:%M:%S'); save()
    print('DONE credits', sum(v or 0 for v in rec['credits'].values()), flush=True)


if __name__ == '__main__':
    main()
