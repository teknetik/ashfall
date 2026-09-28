#!/usr/bin/env python3
"""Ward NPC roster (27 Sep 2026, Carl: "more people"). Text-to-3D preview -> refine (PBR) -> rig -> library clips.
Key only from MESHY_API_KEY in the environment. Resumable: task ids go to <name>/record.json (no secrets).
Usage: python3 generate.py [name ...]   (default: all characters below)"""
import json, os, sys, time, urllib.request, urllib.error
from pathlib import Path
KEY = os.environ.get('MESHY_API_KEY') or sys.exit('MESHY_API_KEY is required in the environment')
V1, V2 = 'https://api.meshy.ai/openapi/v1', 'https://api.meshy.ai/openapi/v2'
HERE = Path(__file__).parent
COMMON = ('full body realistic human character, standing in A-pose, arms held away from the body, feet flat and '
          'apart, relaxed neutral face, detailed hands with five separate fingers, practical desert-colony clothing on '
          'a sun-baked frontier mining world, weathered but clean-cut garment construction, no weapons, no text, no logos')
CHARS = {
    'karaveen_trader_m': dict(role='vendor', height=1.78, prompt='middle-aged male nomad caravan trader, layered sun-faded '
        'ochre and rust robes over a quilted vest, wrapped linen head scarf, leather apron with many small pouches, brass '
        'dust goggles pushed up on forehead, fingerless gloves, worn leather boots. ' + COMMON,
        texture='sun-faded ochre, rust and cream cotton, patched and re-stitched, oiled brown leather with scuffed edges, '
        'dull brass buckles, fine desert dust in the folds, natural tanned skin, no strong baked lighting'),
    'karaveen_trader_f': dict(role='vendor', height=1.68, prompt='adult female nomad caravan trader, long patched duster '
        'coat in indigo and sand tones, woven sash belt with beads and trade tokens, loose head wrap with a veil around the '
        'neck, rolled sleeves, cloth wrapped forearms, soft leather boots. ' + COMMON,
        texture='faded indigo and sand dyed cotton, hand-woven patterned sash, bone and copper beads, repaired seams, '
        'dusty hems, natural skin, no strong baked lighting'),
    'hydroponics_worker': dict(role='walker', height=1.74, prompt='hydroponics farm worker, pale green utility coveralls '
        'with rolled sleeves, waterproof bib apron, rubber gloves tucked in a belt, tool belt with pruning shears and a '
        'water tester, short practical haircut, rubber work boots. ' + COMMON,
        texture='washed-out sage green canvas, grey-green rubber, water stains and soil marks at knees and cuffs, '
        'scratched plastic tools, natural skin, no strong baked lighting'),
    'salvage_hauler': dict(role='walker', height=1.84, prompt='burly male scrap salvage hauler, heavy canvas work jacket '
        'with reinforced shoulders, knee pads, respirator mask hanging around the neck, welding gloves, empty back-pack '
        'carry frame straps, cargo trousers, steel-toe boots. ' + COMMON,
        texture='dark khaki canvas with oil stains and grinder burn marks, worn grey rubber knee pads, scratched steel '
        'buckles, scuffed boots, natural skin, no strong baked lighting'),
    'ward_townswoman': dict(role='walker', height=1.65, prompt='adult woman Ward colonist townsperson, loose linen shirt, '
        'light shawl over shoulders, high-waisted desert trousers, satchel bag across the body, hair tied back, simple '
        'sandal boots. ' + COMMON,
        texture='off-white and terracotta linen, soft wool shawl in muted teal, tan leather satchel, light dust, '
        'natural skin, no strong baked lighting'),
}
# Library clips on each rig (3 credits each). Vendors: calm idles + talk; walkers: walks + idle.
CLIPS = {'vendor': {'idle_246': 246, 'idle_252': 252, 'talk_313': 313, 'walk_30': 30},
         'walker': {'walk_30': 30, 'walk_121': 121, 'idle_252': 252}}


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


def wait(url):
    while True:
        t = call('GET', url)
        print(url.split('/openapi/')[-1][:60], t['status'], t.get('progress'), flush=True)
        if t['status'] == 'SUCCEEDED': return t
        if t['status'] in ('FAILED', 'CANCELED', 'EXPIRED'): raise RuntimeError(f'{url} {t["status"]}: {t.get("task_error")}')
        time.sleep(15)


def fetch(url, path):
    if not path.exists(): path.write_bytes(urllib.request.urlopen(url, timeout=600).read())


def run(name):
    c = CHARS[name]; out = HERE / name; out.mkdir(exist_ok=True)
    rp = out / 'record.json'; rec = json.loads(rp.read_text()) if rp.exists() else {}
    save = lambda: rp.write_text(json.dumps(rec, indent=2))
    rec.update(name=name, role=c['role'], height_meters=c['height']); rec.setdefault('credits', {})
    if 'preview_task' not in rec:
        rec['preview_request'] = dict(mode='preview', prompt=c['prompt'][:800], ai_model='meshy-7.1', pose_mode='a-pose',
                                      should_remesh=True, topology='triangle', target_polycount=40000, target_formats=['glb'])
        rec['preview_task'] = call('POST', f'{V2}/text-to-3d', rec['preview_request'])['result']; save()
    p = wait(f'{V2}/text-to-3d/{rec["preview_task"]}'); rec['credits']['preview'] = p.get('consumed_credits')
    fetch(p['thumbnail_url'], out / 'preview.png'); save()
    if 'refine_task' not in rec:
        rec['refine_request'] = dict(mode='refine', preview_task_id=rec['preview_task'], enable_pbr=True,
                                     texture_resolution='2k', texture_prompt=c['texture'][:800], target_formats=['glb'])
        rec['refine_task'] = call('POST', f'{V2}/text-to-3d', rec['refine_request'])['result']; save()
    r = wait(f'{V2}/text-to-3d/{rec["refine_task"]}'); rec['credits']['refine'] = r.get('consumed_credits')
    fetch(r['model_urls']['glb'], out / 'textured.glb'); fetch(r['thumbnail_url'], out / 'refined.png'); save()
    if 'rig_task' not in rec:
        rec['rig_task'] = call('POST', f'{V1}/rigging', dict(input_task_id=rec['refine_task'], height_meters=c['height']))['result']; save()
    g = wait(f'{V1}/rigging/{rec["rig_task"]}'); rec['credits']['rig'] = g.get('consumed_credits')
    fetch(g['result']['rigged_character_glb_url'], out / 'rigged.glb')
    ba = g['result'].get('basic_animations') or {}
    if ba.get('walking_glb_url'): fetch(ba['walking_glb_url'], out / 'basic_walk.glb')
    save()
    rec.setdefault('animation_tasks', {})
    for clip, aid in CLIPS[c['role']].items():
        if clip not in rec['animation_tasks']:
            rec['animation_tasks'][clip] = call('POST', f'{V1}/animations', dict(rig_task_id=rec['rig_task'], action_id=aid,
                                                post_process=dict(operation_type='change_fps', fps=30)))['result']; save()
    for clip, tid in rec['animation_tasks'].items():
        a = wait(f'{V1}/animations/{tid}'); rec['credits'][clip] = a.get('consumed_credits')
        fetch(a['result']['animation_glb_url'], out / f'{clip}.glb'); save()
    rec['finished'] = time.strftime('%Y-%m-%dT%H:%M:%S'); save()
    print(name, 'DONE credits', sum(v or 0 for v in rec['credits'].values()), flush=True)


if __name__ == '__main__':
    import threading
    names = sys.argv[1:] or list(CHARS)
    errs = []
    def go(n):
        try: run(n)
        except Exception as e: errs.append((n, str(e))); print('ERROR', n, e, flush=True)
    ts = [threading.Thread(target=go, args=(n,)) for n in names]
    for t in ts: t.start(); time.sleep(2)
    for t in ts: t.join()
    print('ALL DONE', 'errors:', errs, flush=True)
