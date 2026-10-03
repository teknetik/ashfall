#!/usr/bin/env python3
"""player_face_20261003 (copied from art/tutorial_set_20261002/meshy_job.py): resumable Meshy jobs. Key only from MESHY_API_KEY (project .env); task records without
secrets go to meshy/player-face-20261003/<name>/manifest.json. Run again to poll and download.
Usage:
  meshy_job.py image3d  NAME IMAGE.png [polycount]            # Image-to-3D with PBR textures
  meshy_job.py retex    NAME MODEL.glb STYLE.png|mv:A.png,B.png|"text prompt"  # Retexture keeping the model's UVs (4k PBR)
"""
import base64, json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

def env_key():
    k = os.environ.get('MESHY_API_KEY')
    if k: return k
    for line in Path('/home/teknetik/code/ao2/.env').read_text().splitlines():
        if line.startswith('MESHY_API_KEY='): return line.split('=', 1)[1].strip().strip('"\'')
    sys.exit('MESHY_API_KEY missing')
KEY = env_key()
ROOT = Path('/home/teknetik/code/ao2/meshy/player-face-20261003')

def api(method, url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, method=method,
                                 headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'})
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=600) as r: return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500: time.sleep(15 * (attempt + 1)); continue
            raise RuntimeError(f'{method} {url} -> {e.code} {e.read().decode()[:600]}')
        except (urllib.error.URLError, TimeoutError): time.sleep(15 * (attempt + 1))
    raise RuntimeError('failed after retries')

def data_uri(p):
    p = Path(p); mime = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.glb': 'application/octet-stream'}[p.suffix.lower()]
    return f'data:{mime};base64,' + base64.b64encode(p.read_bytes()).decode()

def main():
    kind, name = sys.argv[1], sys.argv[2]
    d = ROOT / name; d.mkdir(parents=True, exist_ok=True)
    mf = d / 'manifest.json'
    m = json.loads(mf.read_text()) if mf.exists() else {'name': name, 'kind': kind}
    save = lambda: mf.write_text(json.dumps(m, indent=2) + '\n')
    if kind == 'image3d':
        url = 'https://api.meshy.ai/openapi/v1/image-to-3d'
        if 'task' not in m:
            img = sys.argv[3]; poly = int(sys.argv[4]) if len(sys.argv) > 4 else 30000
            opts = {'ai_model': 'latest', 'should_remesh': True, 'topology': 'triangle', 'target_polycount': poly,
                    'should_texture': True, 'enable_pbr': True, 'texture_resolution': '2k', 'target_formats': ['glb']}
            m['source_image'] = str(img); m['options'] = opts; save()
            m['task'] = api('POST', url, dict(opts, image_url=data_uri(img)))['result']; save()
    elif kind == 'retex':
        url = 'https://api.meshy.ai/openapi/v1/retexture'
        if 'task' not in m:
            model, style = sys.argv[3], sys.argv[4]
            opts = {'ai_model': 'latest', 'enable_original_uv': True, 'enable_pbr': True, 'texture_resolution': '4k',
                    'target_formats': ['glb']}
            body = dict(opts, model_url=data_uri(model))
            if style.startswith('mv:'):
                imgs = style[3:].split(','); body['multiview_image_urls'] = [data_uri(i) for i in imgs]; body['ai_model'] = 'meshy-7'
                opts['ai_model'] = 'meshy-7'; m['style_images'] = imgs
            elif Path(style).exists(): body['image_style_url'] = data_uri(style); m['style_image'] = style
            else: body['text_style_prompt'] = style; m['style_prompt'] = style
            m['source_model'] = model; m['options'] = opts; save()
            m['task'] = api('POST', url, body)['result']; save()
    else: sys.exit('unknown kind')
    while True:
        r = api('GET', f'{url}/{m["task"]}')
        print(name, r['status'], r.get('progress'), flush=True)
        if r['status'] == 'SUCCEEDED':
            m['credits'] = r.get('consumed_credits'); save()
            glb = r.get('model_urls', {}).get('glb')
            if glb and not (d / 'model.glb').exists(): (d / 'model.glb').write_bytes(urllib.request.urlopen(glb, timeout=600).read())
            if r.get('thumbnail_url') and not (d / 'thumb.png').exists():
                (d / 'thumb.png').write_bytes(urllib.request.urlopen(r['thumbnail_url'], timeout=300).read())
            for i, tex in enumerate(r.get('texture_urls') or []):
                for k, u in tex.items():
                    f = d / f'tex{i}_{k}.png'
                    if u and not f.exists(): f.write_bytes(urllib.request.urlopen(u, timeout=600).read())
            (d / 'status.json').write_text(json.dumps({k: v for k, v in r.items() if 'url' not in k}, indent=2))
            print(name, 'DONE', flush=True); return
        if r['status'] in ('FAILED', 'CANCELED', 'EXPIRED'):
            m['error'] = r.get('task_error'); save(); sys.exit(f'{name} {r["status"]}: {r.get("task_error")}')
        time.sleep(20)

main()
