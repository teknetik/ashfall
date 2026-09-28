#!/usr/bin/env python3
"""Meshy text-to-3D (preview -> PBR refine) for the retrofit hero pieces.
Key comes only from MESHY_API_KEY in the environment; task records (no secrets) go to --out/task.json."""
import argparse, json, os, sys, time, urllib.request
from pathlib import Path
BASE = 'https://api.meshy.ai/openapi/v2/text-to-3d'
KEY = os.environ.get('MESHY_API_KEY') or sys.exit('MESHY_API_KEY is required in the environment')


def call(method, url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, method=method,
                                 headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as r: return json.loads(r.read())


def wait(tid, label):
    while True:
        t = call('GET', f'{BASE}/{tid}')
        print(label, t['status'], t.get('progress'), flush=True)
        if t['status'] == 'SUCCEEDED': return t
        if t['status'] in ('FAILED', 'CANCELED', 'EXPIRED'): sys.exit(f'{label} {t["status"]}: {t.get("task_error")}')
        time.sleep(15)


ap = argparse.ArgumentParser()
ap.add_argument('--out', required=True); ap.add_argument('--prompt', required=True)
ap.add_argument('--negative', default=''); ap.add_argument('--polycount', type=int, default=60000)
a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
rec = dict(prompt=a.prompt, negative_prompt=a.negative, art_style='realistic', target_polycount=a.polycount, started=time.strftime('%Y-%m-%dT%H:%M:%S'))
pre = call('POST', BASE, dict(mode='preview', prompt=a.prompt, negative_prompt=a.negative, art_style='realistic',
                              should_remesh=True, topology='triangle', target_polycount=a.polycount))['result']
rec['preview_task'] = pre; (out / 'task.json').write_text(json.dumps(rec, indent=2))
p = wait(pre, 'preview')
rec['preview_thumbnail'] = p.get('thumbnail_url')
ref = call('POST', BASE, dict(mode='refine', preview_task_id=pre, enable_pbr=True))['result']
rec['refine_task'] = ref; (out / 'task.json').write_text(json.dumps(rec, indent=2))
r = wait(ref, 'refine')
for kind in ('glb',):
    url = r['model_urls'][kind]
    (out / f'model.{kind}').write_bytes(urllib.request.urlopen(url, timeout=300).read())
if r.get('thumbnail_url'): (out / 'thumbnail.png').write_bytes(urllib.request.urlopen(r['thumbnail_url'], timeout=120).read())
rec.update(finished=time.strftime('%Y-%m-%dT%H:%M:%S'), texture_urls_present=bool(r.get('texture_urls')), status='SUCCEEDED')
(out / 'task.json').write_text(json.dumps(rec, indent=2)); print('DONE', out)
