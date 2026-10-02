#!/usr/bin/env python3
"""Salvage shop interior hero props (1 Oct 2026). Carl: "make the salvage shop walkable ... the salvage shop should be open
to trade and have the equipment in there ... get to upgrade my pistol". The pistol fabrication station moves from the
field tool cart into the shop; these are its workbench and the shop's stock racks.

Static props: Meshy text-to-3D meshy-7.1 preview (remesh, triangles) -> refine (PBR, 2k). No rigging.
Key only from MESHY_API_KEY in the environment (never written to disk or logs). Resumable: task ids go to
<name>/record.json. A regeneration of a rejected result is requested with `--retry <name>`: the current record is moved to
<name>/attempt<N>/ (task ids kept) and a fresh preview is started; at most two regenerations per prop.
Usage: python3 generate.py [--retry] [name ...]"""
import json, os, sys, time, shutil, urllib.request, urllib.error, threading
from pathlib import Path
KEY = os.environ.get('MESHY_API_KEY') or sys.exit('MESHY_API_KEY is required in the environment')
V2 = 'https://api.meshy.ai/openapi/v2'
HERE = Path(__file__).parent
STYLE = ('desert frontier colony salvage hardware, realistic hard-surface detail, bolted and welded steel, worn edges, '
         'no text, no logos, no people, single object')
PROPS = {
    'workbench': dict(unity='SS_Workbench', size=[2.2, 2.1, 0.9], polycount=120000, prompt=(
        "heavy salvager's steel fabrication workbench: thick scarred steel plate worktop at waist height "
        'on welded steel legs, cast iron bench vice at the left end, steel parts drawers under the right end, open '
        'lower shelf with a metal crate, rear upright steel frame carrying a compact nano-fabricator print head on a small '
        'overhead gantry above the right half, a dark rectangular screen panel on the frame, a tool rail with hand tools, '
        'bundled cables. ' + STYLE),
        texture=('oil-stained scarred bare steel worktop with a dark timber edge, worn graphite and faded olive painted '
                 'steel frame, muted safety yellow vice, brushed steel drawer fronts with worn handles, black rubber cable '
                 'sheaths, dark glass screen panel, a few small restrained cyan indicator lights on the print head, fine '
                 'desert dust in recesses, wear concentrated at handles and edges, no strong baked lighting, no text')),
    # attempt 2 (same prefab): the first preview had no rear frame or gantry and read as a machinist's bench, not a nanofab
    'workbench_b': dict(unity='SS_Workbench', size=[2.2, 2.1, 0.9], polycount=120000, prompt=(
        'fabrication workstation: heavy steel workbench with a thick scarred steel top and a tall welded '
        'steel back frame rising to twice the bench height; on the frame a compact nano-fabricator print head hangs from '
        'an overhead gantry rail above the right half of the worktop, a dark rectangular screen panel beside it, a rail of '
        'hanging hand tools, cables; cast iron vice at the left end, parts drawers under the right '
        'end, lower shelf with a crate. ' + STYLE),
        texture=None),
    # the accepted attempt 2 mesh re-textured at 4k (same preview task): the hero interaction prop is seen at 0.8 m
    'workbench_b4k': dict(unity='SS_Workbench', size=[2.2, 2.1, 0.9], reuse_preview='workbench_b', texres='4k',
                          prompt=None, texture=None),
    'parts_rack': dict(unity='SS_PartsRack', size=[2.0, 2.2, 0.6], polycount=120000, prompt=(
        'tall heavy-duty industrial steel shelving unit, four sturdy steel shelves on bolted angle-iron uprights, every '
        'shelf neatly stocked with salvaged robot parts: servo motors, hydraulic actuators, coils of copper wire, power '
        'cells, drone rotors, grey plastic parts bins, small crates of bolts, two disassembled robot arms. ' + STYLE),
        texture=('worn blue-grey painted steel shelving with chipped edges and bare steel at the shelf lips, oily '
                 'machined steel and aluminium parts, copper wire, faded orange and grey plastic bins, black rubber, '
                 'dull composite robot casings, fine desert dust on the shelves, grimy but organised, no strong baked '
                 'lighting, no text, no labels')),
    # attempt 2: the first came back as an empty orange stand with one motor underneath (no torso shell, no drum)
    'parts_rack_heavy': dict(unity='SS_PartsRackHeavy', size=[2.0, 1.4, 0.9], polycount=90000, prompt=(
        'low heavy steel rack loaded with big salvaged machinery: on the top level a large dented robot chest shell '
        'lying on its back beside a round electric motor housing; on the bottom level a wooden cable drum wound with '
        'thick black cable and a few big steel gears. ' + STYLE),
        texture=('worn graphite grey painted steel rack beams with chipped faded yellow edges and bare steel at the '
                 'corners, faded off-white composite robot shell with grime and scratches, cast grey motor housing, '
                 'weathered timber drum, black rubber cable, fine desert dust, no strong baked lighting, no text, no labels')),
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


def retire(name):
    """Move the current attempt aside (kept for the record) so the next run starts a fresh preview."""
    out = HERE / name
    n = 1
    while (out / f'attempt{n}').exists(): n += 1
    if n > 2: sys.exit(f'{name}: two regenerations already used')
    dst = out / f'attempt{n}'; dst.mkdir()
    for f in out.iterdir():
        if f.is_file() or (f.is_dir() and not f.name.startswith('attempt')): shutil.move(str(f), dst / f.name)
    print(name, 'retired to', dst, flush=True)


def run(name):
    c = PROPS[name]; out = HERE / name; out.mkdir(exist_ok=True)
    rp = out / 'record.json'; rec = json.loads(rp.read_text()) if rp.exists() else {}
    save = lambda: rp.write_text(json.dumps(rec, indent=2))
    rec.update(name=name, unity_prefab=c['unity'], target_size_m=c['size']); rec.setdefault('credits', {})
    if c.get('reuse_preview') and 'preview_task' not in rec:
        src = json.loads((HERE / c['reuse_preview'] / 'record.json').read_text())
        rec['preview_task'] = src['preview_task']; rec['preview_reused_from'] = c['reuse_preview']; save()
    if 'preview_task' not in rec:
        rec['preview_request'] = dict(mode='preview', prompt=c['prompt'][:600], ai_model='meshy-7.1', should_remesh=True,
                                      topology='triangle', target_polycount=c['polycount'], target_formats=['glb'])
        rec['preview_task'] = call('POST', f'{V2}/text-to-3d', rec['preview_request'])['result']; save()
    p = wait(f'{V2}/text-to-3d/{rec["preview_task"]}')
    if not c.get('reuse_preview'): rec['credits']['preview'] = p.get('consumed_credits')
    fetch(p['thumbnail_url'], out / 'preview.png'); save()
    if 'refine_task' not in rec:
        rec['refine_request'] = dict(mode='refine', preview_task_id=rec['preview_task'], enable_pbr=True,
                                     texture_resolution=c.get('texres', '2k'), texture_prompt=(c['texture'] or PROPS[name.split('_b')[0]]['texture'])[:800], target_formats=['glb'])
        rec['refine_task'] = call('POST', f'{V2}/text-to-3d', rec['refine_request'])['result']; save()
    r = wait(f'{V2}/text-to-3d/{rec["refine_task"]}'); rec['credits']['refine'] = r.get('consumed_credits')
    fetch(r['model_urls']['glb'], out / 'textured.glb'); fetch(r['thumbnail_url'], out / 'refined.png')
    rec['finished'] = time.strftime('%Y-%m-%dT%H:%M:%S'); save()
    print(name, 'DONE credits', sum(v or 0 for v in rec['credits'].values()), flush=True)


if __name__ == '__main__':
    args = sys.argv[1:]
    retry = '--retry' in args
    names = [a for a in args if not a.startswith('--')] or ['workbench', 'parts_rack']
    if retry:
        for n in names: retire(n)
    errs = []
    def go(n):
        try: run(n)
        except Exception as e: errs.append((n, str(e))); print('ERROR', n, e, flush=True)
    ts = [threading.Thread(target=go, args=(n,)) for n in names]
    for t in ts: t.start(); time.sleep(2)
    for t in ts: t.join()
    print('ALL DONE', 'errors:', errs, flush=True)
