#!/usr/bin/env python3
"""Ranged enemies (2 Oct 2026): Meshy Multi-Image to 3D for the feral gunner droid and the feral lancer drone.
Key only from MESHY_API_KEY in the environment; task records (no secrets, no data URIs) go to record.json here.
Usage: python3 gen_model.py <enemy> <attempt> [--pose a-pose|t-pose] [--polycount N] [--geometry standard|2k]
       enemy = gunner | lancer | gun; images are concepts/<enemy>_{front,side,back}.png (front first, as Meshy expects);
       --views picks other concept names (the gunner's forearm gun: --views side,top,quarter).
Outputs: <enemy>/<attempt>/model.glb (remeshed, textured, PBR), pre_remeshed.glb, textures/, thumbnails/, task.json."""
import argparse, base64, json, os, sys, time, urllib.request, urllib.error
from pathlib import Path
KEY = os.environ.get('MESHY_API_KEY') or sys.exit('MESHY_API_KEY is required in the environment')
API = 'https://api.meshy.ai/openapi/v1'
HERE = Path(__file__).parent

TEXTURE_PROMPTS = {
    'gunner': ('Weathered feral security robot: sun-faded olive-drab and slate-grey painted armour plates, dark gunmetal '
               'frame, rust at seams, bolts and edges, chipped paint, sand grime on feet and joints, copper coils on the '
               'forearm gun, one glowing amber-red optic lens in the head. No text, no logos.'),
    'lancer': ('Weathered feral gun drone: faded oxide-red rust-red paint over dull grey steel, heavy rust, dents, chipped '
               'edges, sand grime, dark steel rotor blades, copper coil rings on the cannon barrel, one large glowing '
               'amber-red sensor eye on the front. No text, no logos.'),
    'gun': ('Salvaged forearm-mounted rivet/arc gun: dark gunmetal and slate-grey steel, faded olive-drab painted panels, '
            'worn copper coil rings and capacitor, rust at seams and bolts, chipped edges, sand grime, black rubber cable. '
            'No text, no logos.'),
}


def call(method, path, body=None):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body else None, method=method,
                                 headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=300) as r: return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500: time.sleep(15 * (attempt + 1)); continue
            raise RuntimeError(f'{method} {path} -> {e.code} {e.read().decode()[:500]}')
        except urllib.error.URLError: time.sleep(15 * (attempt + 1))
    raise RuntimeError(f'{method} {path} failed after retries')


def fetch(url, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): dest.write_bytes(urllib.request.urlopen(url, timeout=900).read())


def uri(p: Path):
    return 'data:image/png;base64,' + base64.b64encode(p.read_bytes()).decode()


ap = argparse.ArgumentParser()
ap.add_argument('enemy', choices=['gunner', 'lancer', 'gun']); ap.add_argument('attempt')
ap.add_argument('--pose', default=''); ap.add_argument('--polycount', type=int, default=40000)
ap.add_argument('--geometry', default='standard'); ap.add_argument('--views', default='front,side,back')
a = ap.parse_args()
out = HERE / a.enemy / a.attempt; out.mkdir(parents=True, exist_ok=True)
rec_path = HERE / 'record.json'
rec = json.loads(rec_path.read_text()) if rec_path.exists() else {}
key = f'{a.enemy}_{a.attempt}'
r = rec.setdefault('models', {}).setdefault(key, {})
def save():  # merge: other scripts write other keys of record.json concurrently
    cur = json.loads(rec_path.read_text()) if rec_path.exists() else {}
    cur.setdefault('models', {})[key] = r; rec_path.write_text(json.dumps(cur, indent=2))
views = a.views.split(',')
images = [HERE / 'concepts' / f'{a.enemy}_{v}.png' for v in views]
if 'task' not in r:
    body = dict(image_urls=[uri(p) for p in images], ai_model='latest', geometry_resolution=a.geometry,
                should_texture=True, enable_pbr=True, texture_resolution='2k', texture_prompt=TEXTURE_PROMPTS[a.enemy],
                should_remesh=True, topology='quad', target_polycount=a.polycount, save_pre_remeshed_model=True,
                pose_mode=a.pose, image_enhancement=True, remove_lighting=True, target_formats=['glb'],
                multi_view_thumbnails=True)
    logged = {k: v for k, v in body.items() if k != 'image_urls'}
    logged['images'] = [str(p.relative_to(HERE)) for p in images]
    r.update(endpoint='POST v1/multi-image-to-3d', request=logged, started=time.strftime('%Y-%m-%dT%H:%M:%S'))
    r['task'] = call('POST', '/multi-image-to-3d', body)['result']; save()
    print('task', r['task'], flush=True)
while True:
    t = call('GET', f'/multi-image-to-3d/{r["task"]}')
    print(key, t['status'], t.get('progress'), flush=True)
    if t['status'] == 'SUCCEEDED': break
    if t['status'] in ('FAILED', 'CANCELED', 'EXPIRED'):
        r.update(status=t['status'], task_error=t.get('task_error')); save(); sys.exit(f'{key} {t["status"]}: {t.get("task_error")}')
    time.sleep(15)
mu = t.get('model_urls') or {}
fetch(mu['glb'], out / 'model.glb')
if mu.get('pre_remeshed_glb'): fetch(mu['pre_remeshed_glb'], out / 'pre_remeshed.glb')
for i, tex in enumerate(t.get('texture_urls') or []):
    for k, u in tex.items():
        if isinstance(u, str) and u.startswith('http'): fetch(u, out / 'textures' / f'{i}_{k}.png')
if t.get('thumbnail_url'): fetch(t['thumbnail_url'], out / 'thumbnails' / 'thumbnail.png')
for k, u in (t.get('thumbnail_urls') or {}).items():
    if isinstance(u, str): fetch(u, out / 'thumbnails' / f'{k}.png')
(out / 'task.json').write_text(json.dumps({k: v for k, v in t.items() if not k.endswith('_urls') and k not in ('thumbnail_url',)}, indent=2))
r.update(status='SUCCEEDED', credits=t.get('consumed_credits'), finished=time.strftime('%Y-%m-%dT%H:%M:%S'),
         files=sorted(str(p.relative_to(HERE)) for p in out.rglob('*') if p.is_file()))
save(); print('DONE', key, 'credits', t.get('consumed_credits'), flush=True)
