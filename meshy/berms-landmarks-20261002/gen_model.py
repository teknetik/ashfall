#!/usr/bin/env python3
"""Berms landmarks (2 Oct 2026): Meshy Multi-Image to 3D for the three Outer Berms landmarks.
Key only from MESHY_API_KEY in the environment; task records (no secrets, no data URIs) go to record.json here.
Usage: python3 gen_model.py <subject> <attempt> [--polycount N] [--geometry standard|2k] [--texres 2k|4k]
                            [--topology triangle|quad] [--views a,b,c]
  subject = hauler | derrick | pylon | tube; images are concepts/<subject>_<view>.png (first image = the main view).
  The pylon landmark is two models (pylon + fallen tube) so each can be fitted to its own true size.
Outputs: <subject>/<attempt>/model.glb (remeshed, textured, PBR), pre_remeshed.glb, textures/, thumbnails/, task.json."""
import argparse, base64, json, os, sys, time, urllib.request, urllib.error
from pathlib import Path
KEY = os.environ.get('MESHY_API_KEY') or sys.exit('MESHY_API_KEY is required in the environment')
API = 'https://api.meshy.ai/openapi/v1'
HERE = Path(__file__).parent

VIEWS = {'hauler': 'hero,side,back', 'derrick': 'front,side,back', 'pylon': 'front,side,back', 'tube': 'front,side,back'}
POLY = {'hauler': 80000, 'derrick': 90000, 'pylon': 50000, 'tube': 50000}
TEXTURE_PROMPTS = {
    'hauler': ('Wrecked desert caravan cargo truck: sun-bleached chalky ochre and faded sky-blue painted steel, chipped to '
               'bare grey steel at edges, steps and handles, orange-brown rust bleeding from seams, bolts and drain points, '
               'blackened scorch patches, black cracked rubber tyres, sand-coloured canvas with faded madder-red and indigo '
               'cloth patches, dull blue water drums, weathered timber crates with steel bands, pale desert sand. No text, '
               'no logos, no baked shadows or highlights.'),
    'derrick': ('Derelict aquifer pump derrick: riveted steel lattice in faded oxide-red primer with orange-brown rust '
                'concentrated at joints, rivets and drip edges, dull galvanised grey pipework and valves with rust at flanges, '
                'dark iron hand-wheels, weathered grey concrete footings with rust drip streaks, dented grey steel control '
                'hut, dark blue cracked solar cells in aluminium frames, one small dull teal indicator lens, pale desert sand '
                'and dust. No text, no logos, no baked shadows or highlights.'),
    'pylon': ('Damaged freight-tube support pylon: sun-bleached pale grey concrete with vertical weathering streaks, rust '
              'stains under exposed rusted rebar, blackened scorch around blast craters, sand-scoured lower steps, brushed '
              'gunmetal and pale grey alloy cradle with oxidation and dents, thin dull dark-teal inlay lines (unlit), pale '
              'desert sand and broken concrete rubble. No text, no logos, no baked shadows or highlights.'),
    'tube': ('Fallen freight transport tube section: ribbed brushed gunmetal and pale grey alloy casing rings with dark '
             'recessed seams, oxidation, dents and scorch marks, thin dull dark-teal inlay lines (unlit), dark grey inner '
             'liner, black rubber conduits with copper cable cores, pale drifted desert sand, grey rocks and concrete '
             'fragments. No text, no logos, no baked shadows or highlights.'),
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
ap.add_argument('subject', choices=list(VIEWS)); ap.add_argument('attempt')
ap.add_argument('--polycount', type=int, default=0); ap.add_argument('--geometry', default='2k')
ap.add_argument('--texres', default='4k'); ap.add_argument('--topology', default='triangle')
ap.add_argument('--views', default='')
a = ap.parse_args()
out = HERE / a.subject / a.attempt; out.mkdir(parents=True, exist_ok=True)
rec_path = HERE / 'record.json'
key = f'{a.subject}_{a.attempt}'
r = (json.loads(rec_path.read_text()) if rec_path.exists() else {}).get('models', {}).get(key, {})


def save():  # merge: several generations run at once and write other keys of record.json
    cur = json.loads(rec_path.read_text()) if rec_path.exists() else {}
    cur.setdefault('models', {})[key] = r; rec_path.write_text(json.dumps(cur, indent=2))


views = (a.views or VIEWS[a.subject]).split(',')
images = [HERE / 'concepts' / f'{a.subject}_{v}.png' for v in views]
if 'task' not in r:
    body = dict(image_urls=[uri(p) for p in images], ai_model='latest', geometry_resolution=a.geometry,
                should_texture=True, enable_pbr=True, texture_resolution=a.texres, texture_prompt=TEXTURE_PROMPTS[a.subject],
                should_remesh=True, topology=a.topology, target_polycount=a.polycount or POLY[a.subject],
                save_pre_remeshed_model=True, image_enhancement=True, remove_lighting=True, target_formats=['glb'],
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
        r.update(status=t['status'], task_error=t.get('task_error'), credits=t.get('consumed_credits')); save()
        sys.exit(f'{key} {t["status"]}: {t.get("task_error")}')
    time.sleep(20)
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
