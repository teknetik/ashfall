#!/usr/bin/env python3
"""Warden plate carrier (2 Oct 2026): Meshy Text-to-3D v2 preview + PBR refine. Key only from MESHY_API_KEY in the
environment; task records (no secrets) go to manifest.json here. Resumable: run it again to poll and download.
Usage: python3 generate.py            # start preview if needed, poll, refine when the preview succeeds, download all"""
import json, os, sys, time, urllib.request, urllib.error
from pathlib import Path
KEY = os.environ.get('MESHY_API_KEY') or sys.exit('MESHY_API_KEY is required in the environment')
API = 'https://api.meshy.ai/openapi/v2/text-to-3d'
HERE = Path(__file__).parent
PROMPT = ('One realistic military plate carrier vest for a desert colony militia, worn over armour: sand-tan and faded '
          'olive cordura canvas carrier with a front and a back hard steel plate pocket, two padded shoulder straps with '
          'metal buckles, a side cummerbund with laser-cut webbing, two rifle magazine pouches and one small radio pouch '
          'on the chest, a grab handle on the back, a single orange stencilled stripe across the chest plate, worn '
          'edges and sand dust. Hollow open vest shape with open neck and open arm holes, as if hung on an invisible '
          'torso, about 0.55 m tall and 0.45 m wide. Single isolated object, no body, no mannequin, no hands, no base, '
          'no text, no logos.')
TEXTURE = ('Worn desert militia plate carrier: sand-tan and faded olive cordura weave, scuffed black nylon webbing and '
           'straps, dull steel buckles, matte dark plate edges, one orange stencil stripe, fine sand in seams. Matte, '
           'no baked light, no logos or text.')
def api(method, path='', body=None):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body else None, method=method,
                                 headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=300) as r: return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500: time.sleep(15 * (attempt + 1)); continue
            raise RuntimeError(f'{method} {path} -> {e.code} {e.read().decode()[:500]}')
        except urllib.error.URLError: time.sleep(15 * (attempt + 1))
    raise RuntimeError('failed after retries')
mf = HERE / 'manifest.json'
m = json.loads(mf.read_text()) if mf.exists() else {'asset': 'Warden plate carrier', 'dimensions_m': {'height': .55, 'width': .45},
     'purpose': 'Visible chest armour on the player colonist (armour_chest quest reward)', 'prompt': PROMPT, 'tasks': {}, 'credits': {}}
save = lambda: mf.write_text(json.dumps(m, indent=2) + '\n')
def wait(stage):
    while True:
        r = api('GET', '/' + m['tasks'][stage]); (HERE / f'{stage}-status.json').write_text(json.dumps(r, indent=2))
        print(stage, r['status'], r.get('progress'), flush=True)
        if r['status'] == 'SUCCEEDED':
            m['credits'][stage] = r.get('consumed_credits')
            for name, url in [(f'{stage}.glb', r.get('model_urls', {}).get('glb')), (f'{stage}.png', r.get('thumbnail_url')),
                              (f'{stage}-alpha.png', r.get('alpha_thumbnail_url'))]:
                if url and not (HERE / name).exists(): (HERE / name).write_bytes(urllib.request.urlopen(url, timeout=300).read())
            save(); return r
        if r['status'] in ('FAILED', 'CANCELED', 'EXPIRED'): sys.exit(f'{stage} {r["status"]}: {r.get("task_error")}')
        time.sleep(15)
if 'preview' not in m['tasks']:
    opts = {'mode': 'preview', 'prompt': PROMPT, 'ai_model': 'latest', 'should_remesh': True, 'target_polycount': 24000,
            'topology': 'triangle', 'target_formats': ['glb'], 'alpha_thumbnail': True}
    m['tasks']['preview'] = api('POST', body=opts)['result']; m['preview_options'] = opts; save()
wait('preview')
if 'refine' not in m['tasks']:
    opts = {'mode': 'refine', 'preview_task_id': m['tasks']['preview'], 'ai_model': 'latest', 'enable_pbr': True,
            'texture_prompt': TEXTURE, 'target_formats': ['glb'], 'alpha_thumbnail': True}
    m['tasks']['refine'] = api('POST', body=opts)['result']; m['refine_options'] = opts; save()
wait('refine'); print('DONE', flush=True)
