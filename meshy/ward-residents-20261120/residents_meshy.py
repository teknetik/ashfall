#!/usr/bin/env python3
"""Ward residents (showcase phase 2, 20 Nov 2026, art/ward_residents_20261120): resumable Meshy pipeline per character,
copied from meshy/ward-walkers-20261003/walker_meshy.py with three changes:
  * texture_resolution 4k (same 30 credits as 2k on 19 Nov 2026 pricing) for faces that hold up at conversation distance;
  * include_fingers on the rig (finger bones, no extra cost);
  * the account balance is read before every paid call and the call is refused if it would overspend the phase budget.
concept sheet (front/side/back) -> multi-image-to-3D (PBR, 4k) -> rigging -> library clips (walk + work).
Key only from MESHY_API_KEY (environment or the project .env); records without secrets go to <name>/record.json.
Usage: residents_meshy.py NAME [--stop-after model|rig]   (re-run to poll and download; nothing is re-submitted)
Pre-approved Meshy use (AGENTS.md section 5). Budget for this item: 126 credits in total (all three)."""
import base64, json, os, subprocess, sys, time, urllib.request, urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONCEPT = Path('/home/teknetik/code/ao2/art/ward_residents_20261120/concept')
API = 'https://api.meshy.ai/openapi/v1'
COST = {'model': 30, 'rig': 5, 'clip': 3}
FLOOR = 0   # never let the balance drop below this
NPCS = {   # rig height (m), concept sheet, library clips fetched on its own rig (ids: meshy/character-feel-20260927/animation-library.json)
    'trader':  dict(height=1.74, sheet='trader_sheet_v2.png',  clips={'walk_566': 566, 'inspect_281': 281}),  # Walking 2, Female Bend Over Pick Up Inspect
    'clerk':   dict(height=1.86, sheet='clerk_sheet_v1.png',   clips={'walk_566': 566, 'checkout_34': 34}),   # Walking 2, Checkout Gesture
    'carrier': dict(height=1.66, sheet='carrier_sheet_v1.png', clips={'walk_553': 553, 'drink_342': 342}),   # Elderly Shaky Walk, Stand and Drink
}


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
            with urllib.request.urlopen(req, timeout=600) as r: return json.loads(r.read())
        except urllib.error.HTTPError as e:
            text = e.read().decode()[:600]
            if e.code == 429 or e.code >= 500: time.sleep(15 * (attempt + 1)); continue
            raise RuntimeError(f'{method} {url.split("/v1/")[-1]} -> {e.code} {text}')
        except (urllib.error.URLError, TimeoutError): time.sleep(15 * (attempt + 1))
    raise RuntimeError('failed after retries')


def spend(rec, what, cost):
    """Balance check before a paid call; logged in the record and in ledger.json."""
    bal = call('GET', f'{API}/balance')['balance']
    if bal - cost < FLOOR: raise SystemExit(f'refused {what}: balance {bal}, cost {cost}')
    led = HERE / 'ledger.json'; rows = json.loads(led.read_text()) if led.exists() else []
    rows.append({'time': time.strftime('%Y-%m-%dT%H:%M:%S'), 'character': rec['name'], 'call': what, 'expected_cost': cost, 'balance_before': bal})
    led.write_text(json.dumps(rows, indent=1) + '\n')
    rec.setdefault('balance_checks', []).append({'call': what, 'balance_before': bal})


def wait(kind, tid):
    while True:
        t = call('GET', f'{API}/{kind}/{tid}')
        print(kind, tid[:8], t['status'], t.get('progress'), flush=True)
        if t['status'] == 'SUCCEEDED': return t
        if t['status'] in ('FAILED', 'CANCELED', 'EXPIRED'): raise SystemExit(f'{kind} {t["status"]}: {t.get("task_error")}')
        time.sleep(20)


def fetch(url, path):
    if path.exists(): return
    for attempt in range(4):
        try: path.write_bytes(urllib.request.urlopen(url, timeout=600).read()); return
        except Exception:
            if attempt == 3: raise
            time.sleep(10)


def data_uri(p):
    return 'data:image/png;base64,' + base64.b64encode(Path(p).read_bytes()).decode()


def panels(d, sheet):
    """Front, side and back crops of the 3-up sheet, trimmed to the figure and padded on the sheet's grey."""
    out = []
    for i, view in enumerate(('front', 'side', 'back')):
        p = d / f'panel_{view}.png'
        if not p.exists():
            subprocess.run(['magick', str(sheet), '-crop', '3x1@', '+repage', '-delete', ','.join(str(k) for k in range(3) if k != i),
                            '-fuzz', '6%', '-trim', '+repage', '-gravity', 'center', '-background', '#808080',
                            '-bordercolor', '#808080', '-border', '48', str(p)], check=True)
        out.append(p)
    return out


def main():
    name = sys.argv[1]; cfg = NPCS[name]
    stop = sys.argv[sys.argv.index('--stop-after') + 1] if '--stop-after' in sys.argv else ''
    d = HERE / name; d.mkdir(parents=True, exist_ok=True)
    rp = d / 'record.json'
    rec = json.loads(rp.read_text()) if rp.exists() else {'name': name}
    save = lambda: rp.write_text(json.dumps(rec, indent=2) + '\n')
    rec.setdefault('credits', {})
    sheet = CONCEPT / cfg['sheet']
    if 'model_task' not in rec:
        imgs = panels(d, sheet)
        opts = {'ai_model': 'latest', 'topology': 'triangle', 'target_polycount': 60000, 'should_remesh': True,
                'should_texture': True, 'enable_pbr': True, 'texture_resolution': '4k', 'pose_mode': 'a-pose'}
        rec['sheet'] = str(sheet); rec['panels'] = [p.name for p in imgs]; rec['model_options'] = opts; save()
        spend(rec, 'multi-image-to-3d', COST['model']); save()
        rec['model_task'] = call('POST', f'{API}/multi-image-to-3d', dict(opts, image_urls=[data_uri(p) for p in imgs]))['result']
        rec['model_submitted'] = time.strftime('%Y-%m-%dT%H:%M:%S'); save()
    t = wait('multi-image-to-3d', rec['model_task'])
    rec['credits']['model'] = t.get('consumed_credits'); save()
    fetch(t['model_urls']['glb'], d / 'model.glb')
    if t.get('thumbnail_url'): fetch(t['thumbnail_url'], d / 'thumb.png')
    if stop == 'model': return
    if 'rig_task' not in rec:
        spend(rec, 'rigging', COST['rig'])
        rec['rig_options'] = dict(height_meters=cfg['height'], include_fingers=True)
        rec['rig_task'] = call('POST', f'{API}/rigging', dict(input_task_id=rec['model_task'], **rec['rig_options']))['result']; save()
    r = wait('rigging', rec['rig_task'])
    rec['credits']['rig'] = r.get('consumed_credits'); save()
    fetch(r['result']['rigged_character_glb_url'], d / 'rigged.glb')
    for key, url in (r['result'].get('basic_animations') or {}).items():
        if url and key.endswith('_glb_url') and 'armature' not in key: fetch(url, d / ('basic_' + key.replace('_glb_url', '') + '.glb'))
    if stop == 'rig': return
    rec.setdefault('animation_tasks', {}); rec.setdefault('actions', {})
    for clip, aid in cfg['clips'].items():
        if clip not in rec['animation_tasks']:
            spend(rec, 'animation ' + clip, COST['clip'])
            rec['animation_tasks'][clip] = call('POST', f'{API}/animations', dict(
                rig_task_id=rec['rig_task'], action_id=aid, post_process=dict(operation_type='change_fps', fps=30)))['result']
            rec['actions'][clip] = aid; save()
    for clip, tid in rec['animation_tasks'].items():
        a = wait('animations', tid)
        rec['credits'][clip] = a.get('consumed_credits'); save()
        fetch(a['result']['animation_glb_url'], d / f'{clip}.glb')
    rec['finished'] = time.strftime('%Y-%m-%dT%H:%M:%S'); save()
    print(name, 'DONE credits', sum(v or 0 for v in rec['credits'].values()), flush=True)


main()
