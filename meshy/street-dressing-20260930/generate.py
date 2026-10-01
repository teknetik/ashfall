#!/usr/bin/env python3
"""Ward street dressing: Meshy hero props (30 Sep 2026). Carl: "A lot of the street trash and props looks very low
quality can we rebuild them in blender and or meshy? I want the area to have a lived in look but not be too messy."
Single static objects (the 10 Sep ground-detail jobs showed whole clutter piles fuse and puncture), composed into street
vignettes in Blender/Unity: a field generator (replaces the six 1,619-triangle salvage generators), a street water point, a
salvage handcart and a communal refuse bin. Meshy text-to-3D preview -> refine (PBR, 2k). No rigging.
Key only from MESHY_API_KEY in the environment. Resumable: task ids go to <name>/record.json (no secrets).
Usage: python3 generate.py [name ...]"""
import json, os, sys, time, urllib.request, urllib.error, threading
from pathlib import Path
KEY = os.environ.get('MESHY_API_KEY') or sys.exit('MESHY_API_KEY is required in the environment')
V2 = 'https://api.meshy.ai/openapi/v2'
HERE = Path(__file__).parent
STYLE = ('grounded near-future frontier colony on a desert world, salvaged and repaired civilian hardware, hard-surface '
         'detail, bolted and welded construction, worn edges, believable real-world scale, no text, no logos, no people, '
         'single object centred on a plain ground, nothing else in the scene')
TEX = ('sun-faded paint over steel, chipped to bare metal on edges and handles, fine desert dust settled in recesses, '
       'light rust at welds and bolts, matte surfaces, no strong baked lighting or shadows, no text, no logos')
PROPS = {
    'field_generator': dict(size=[1.3, 1.0, 0.8], polycount=60000, tex='faded olive drab and sand painted steel frame, '
        'dark grey engine block, black rubber cable and feet, oil stains at the base, one small amber indicator lamp. ' + TEX,
        prompt='compact salvaged field power generator: welded steel tube roll-cage frame around a boxy engine block and a '
        'horizontal cylindrical fuel cell tank, finned heat exchanger on one side, control panel with toggle switches and a '
        'round analogue gauge, heavy power cable coiled on a side reel, lifting eyes on top, rubber feet. ' + STYLE),
    'water_point': dict(size=[0.9, 1.7, 0.9], polycount=50000, tex='weathered pale green painted steel tank, brass tap and '
        'valve, white mineral lime-scale streaks below the tap, damp darker patch on the drip tray. ' + TEX,
        prompt='public street water point: upright cylindrical ribbed steel water tank on a welded four-leg stand, a brass '
        'tap with a short spout at waist height, a filter canister and red valve wheel on the side, a small pressure gauge, '
        'a steel drip tray on the ground below the tap, a supply pipe rising from the ground into the tank. ' + STYLE),
    'handcart': dict(size=[1.6, 0.9, 0.8], polycount=45000, tex='sun-bleached grey wooden planks, rusty painted steel '
        'frame, worn black rubber tyres, faded khaki canvas and hemp rope. ' + TEX,
        prompt='two-wheeled salvage handcart parked level on its front prop leg: wooden plank bed with low steel side rails, '
        'long twin pull handles, two rubber-tyred spoked wheels on a steel axle, a folded canvas tarp and a coil of rope '
        'lashed in the bed. ' + STYLE),
    'refuse_bin': dict(size=[1.5, 1.25, 1.0], polycount=40000, tex='dull green painted steel, darker grime around the lid '
        'edges and handles, scuffed bare metal on the corners, dusty rubber wheels. ' + TEX,
        prompt='communal street refuse bin: large rectangular steel waste container with two hinged flat lids closed, '
        'vertical reinforcing ribs, side lifting pockets, a push handle bar, four small rubber castor wheels, a blank '
        'riveted number plate on the front. ' + STYLE),
}


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
    c = PROPS[name]; out = HERE / name; out.mkdir(exist_ok=True)
    rp = out / 'record.json'; rec = json.loads(rp.read_text()) if rp.exists() else {}
    save = lambda: rp.write_text(json.dumps(rec, indent=2))
    rec.update(name=name, target_size_m=c['size']); rec.setdefault('credits', {})
    if 'preview_task' not in rec:
        rec['preview_request'] = dict(mode='preview', prompt=c['prompt'][:800], ai_model='meshy-7.1', should_remesh=True,
                                      topology='triangle', target_polycount=c['polycount'], target_formats=['glb'])
        rec['preview_task'] = call('POST', f'{V2}/text-to-3d', rec['preview_request'])['result']; save()
    p = wait(f'{V2}/text-to-3d/{rec["preview_task"]}'); rec['credits']['preview'] = p.get('consumed_credits')
    fetch(p['thumbnail_url'], out / 'preview.png'); save()
    if 'refine_task' not in rec:
        rec['refine_request'] = dict(mode='refine', preview_task_id=rec['preview_task'], enable_pbr=True,
                                     texture_resolution='2k', texture_prompt=c['tex'][:800], target_formats=['glb'])
        rec['refine_task'] = call('POST', f'{V2}/text-to-3d', rec['refine_request'])['result']; save()
    r = wait(f'{V2}/text-to-3d/{rec["refine_task"]}'); rec['credits']['refine'] = r.get('consumed_credits')
    fetch(r['model_urls']['glb'], out / 'textured.glb'); fetch(r['thumbnail_url'], out / 'refined.png')
    rec['finished'] = time.strftime('%Y-%m-%dT%H:%M:%S'); save()
    print(name, 'DONE credits', sum(v or 0 for v in rec['credits'].values()), flush=True)


if __name__ == '__main__':
    names = sys.argv[1:] or list(PROPS)
    errs = []
    def go(n):
        try: run(n)
        except Exception as e: errs.append((n, str(e))); print('ERROR', n, e, flush=True)
    ts = [threading.Thread(target=go, args=(n,)) for n in names]
    for t in ts: t.start(); time.sleep(2)
    for t in ts: t.join()
    print('ALL DONE', 'errors:', errs, flush=True)
