#!/usr/bin/env python3
"""Ward talking NPCs and Wardens (3 Oct 2026): resumable Meshy pipeline per character.
  concept sheet (front/side/back) -> multi-image-to-3D (PBR) -> rigging (24 Meshy bones) -> library idle/talk clips.
Key only from MESHY_API_KEY (environment or the project .env); records without secrets go to <name>/record.json.
Usage: npc_meshy.py NAME [--stop-after model|rig]   (re-run to poll and download; nothing is re-submitted)
Pre-approved Meshy use (AGENTS.md section 5). Budget for this pass: ~350 credits."""
import base64, json, os, subprocess, sys, time, urllib.request, urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONCEPT = Path('/home/teknetik/code/ao2/art/ward_npcs_20261003/concept')
API = 'https://api.meshy.ai/openapi/v1'
# Per NPC: rig height (m) and the library clips fetched on its own rig (ids from
# meshy/character-feel-20260927/animation-library.json; the six guard-model characters used these same calm idles/talks).
NPCS = {
    'mira': dict(height=1.68, clips={'idle_244': 244, 'talk_313': 313}),
    'torr': dict(height=1.76, clips={'idle_246': 246, 'talk_309': 309}),
    'vex':  dict(height=1.80, clips={'idle_243': 243, 'talk_314': 314}),
    'linn': dict(height=1.62, clips={'idle_252': 252, 'talk_310': 310}),
    'ossa': dict(height=1.74, clips={'idle_243': 243, 'talk_313': 313}),
    'rell': dict(height=1.88, clips={'idle_252': 252, 'talk_314': 314}),
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


def panels(name, d, sheet):
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
    sheet = Path(rec.get('sheet') or CONCEPT / f'{name}_sheet_v1.png')
    # 1. model
    if 'model_task' not in rec:
        imgs = panels(name, d, sheet)
        opts = {'ai_model': 'latest', 'topology': 'triangle', 'target_polycount': 60000, 'should_remesh': True,
                'should_texture': True, 'enable_pbr': True, 'symmetry_mode': 'auto', 'pose_mode': 'a-pose'}
        rec['sheet'] = str(sheet); rec['panels'] = [p.name for p in imgs]; rec['model_options'] = opts; save()
        try:
            rec['model_task'] = call('POST', f'{API}/multi-image-to-3d', dict(opts, image_urls=[data_uri(p) for p in imgs]))['result']
        except RuntimeError as e:
            if 'pose_mode' not in str(e): raise
            opts.pop('pose_mode'); rec['model_options'] = opts; rec['note_pose_mode'] = str(e)[:300]
            rec['model_task'] = call('POST', f'{API}/multi-image-to-3d', dict(opts, image_urls=[data_uri(p) for p in imgs]))['result']
        rec['model_submitted'] = time.strftime('%Y-%m-%dT%H:%M:%S'); save()
    t = wait('multi-image-to-3d', rec['model_task'])
    rec['credits']['model'] = t.get('consumed_credits'); save()
    fetch(t['model_urls']['glb'], d / 'model.glb')
    if t.get('thumbnail_url'): fetch(t['thumbnail_url'], d / 'thumb.png')
    if stop == 'model': return
    # 2. rig
    if 'rig_task' not in rec:
        rec['rig_task'] = call('POST', f'{API}/rigging', dict(input_task_id=rec['model_task'], height_meters=cfg['height']))['result']
        rec['rig_height_meters'] = cfg['height']; save()
    r = wait('rigging', rec['rig_task'])
    rec['credits']['rig'] = r.get('consumed_credits'); save()
    fetch(r['result']['rigged_character_glb_url'], d / 'rigged.glb')
    for key, url in (r['result'].get('basic_animations') or {}).items():
        if key.endswith('_glb_url') and 'armature' not in key: fetch(url, d / ('basic_' + key.replace('_glb_url', '') + '.glb'))
    if stop == 'rig': return
    # 3. clips
    rec.setdefault('animation_tasks', {}); rec.setdefault('actions', {})
    for clip, aid in cfg['clips'].items():
        if clip not in rec['animation_tasks']:
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
