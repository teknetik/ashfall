#!/usr/bin/env python3
"""Tool Exchange sci-fi workshop props (30 Sep 2026). Carl: "if you rebuild the tool shop remember sci-fi not woodworking
shop from the 90s as it looks now". Static props: Meshy text-to-3D preview -> refine (PBR, 2k). No rigging.
Key only from MESHY_API_KEY in the environment. Resumable: task ids go to <name>/record.json (no secrets).
Usage: python3 generate.py [name ...]"""
import json, os, sys, time, urllib.request, urllib.error, threading
from pathlib import Path
KEY = os.environ.get('MESHY_API_KEY') or sys.exit('MESHY_API_KEY is required in the environment')
V2 = 'https://api.meshy.ai/openapi/v2'
HERE = Path(__file__).parent
STYLE = ('grounded near-future frontier colony technology on a desert world, salvaged and repaired industrial hardware, '
         'hard-surface detail, bolted panels, worn edges, no text, no logos, no people, single object centred')
TEX = ('worn industrial paint in graphite, warm grey and muted safety yellow, bare brushed steel at edges, scratched '
       'composite, rubber cable sheaths, small restrained cyan indicator lights, fine desert dust in recesses, '
       'no strong baked lighting, no text')
PROPS = {
    'nanofab_bench': dict(size=[1.7, 1.5, 0.8], polycount=60000, prompt='sci-fi nanofabrication workbench: heavy steel '
        'workbench with an enclosed glass-fronted fabrication chamber on top, glowing cyan print bed and a small robotic '
        'deposition nozzle on a gantry inside, control panel with physical buttons, tool drawers below, cable conduits. ' + STYLE),
    'tool_wall': dict(size=[1.6, 1.1, 0.22], polycount=50000, prompt='wall-mounted sci-fi power tool rack panel: dark '
        'steel backboard with charging cradles holding futuristic hand tools - a plasma cutter, a nano-welding torch, a '
        'servo driver, a magnetic clamp, spare energy cells - each cradle with a small status light, cable looms. ' + STYLE),
    'servo_arm': dict(size=[0.7, 1.3, 0.7], polycount=45000, prompt='sci-fi workshop robotic manipulator arm on a '
        'bolted steel base, three heavy servo joints, exposed hydraulic lines, two-finger clamp gripper, arm raised in a '
        'resting pose. ' + STYLE),
    'plasma_cutter': dict(size=[0.5, 0.25, 0.14], polycount=25000, prompt='sci-fi handheld plasma cutter power tool '
        'with a clip-on energy cell pack, rugged steel and composite housing, finned emitter nozzle with a cyan coil. ' + STYLE),
    'drone_chassis': dict(size=[0.75, 0.3, 0.75], polycount=35000, prompt='small quad-rotor utility drone partly '
        'disassembled for repair, exposed rotor motors and circuit boards, one arm removed and lying beside it, sitting '
        'on a low steel service stand. ' + STYLE),
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
                                     texture_resolution='2k', texture_prompt=TEX[:800], target_formats=['glb'])
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
