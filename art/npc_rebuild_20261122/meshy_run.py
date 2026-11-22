#!/usr/bin/env python3
"""Meshy stages of the NPC rebuild (AGENTS.md section 5 pre-approves the credits). Resumable: a task id on record is
only polled, never created again.

  meshy_run.py rig NAME [--version v1]   Rodin mesh -> Meshy rig with fingers (5) + idle and talk clips (3 each)
  meshy_run.py face NAME                 face/NAME/in_<view>.png -> out_<view>.png, nano-banana-pro (9 a view)
"""
import base64, fcntl, json, mimetypes, re, subprocess, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

H = Path(__file__).resolve().parent
ROOT = H.parents[1]
API = 'https://api.meshy.ai/openapi/v1'
KEY = next(m.group(1).strip('"\'') for m in (re.match(r'MESHY_API_KEY=(.+?)\s*$', l)
                                              for l in (ROOT / '.env').read_text().splitlines()) if m)
# name: (height, idle, talk). The clip ids are the ones each colonist already uses.
PEOPLE = {'linn': (1.63, 252, 310), 'brann': (1.84, 246, 309), 'ossa': (1.75, 243, 313), 'mira': (1.68, 244, 313),
          'torr': (1.76, 246, 309), 'vex': (1.80, 243, 314), 'rell': (1.88, 252, 314), 'tamsin': (1.76, 248, 309),
          'porter': (1.78, None, None, 566), 'nanotech': (1.68, None, None, 566), 'grower': (1.80, None, None, 566)}   # walkers: a walk


def call(method, path, body=None):
    r = urllib.request.Request(f'{API}/{path}', None if body is None else json.dumps(body).encode(),
                               {'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'}, method=method)
    for i in range(6):
        try:
            with urllib.request.urlopen(r, timeout=600) as x:
                return json.load(x)
        except urllib.error.HTTPError as e:
            # only a rate limit is safe to send again; after a 5xx a POST may already have created the task
            if e.code == 429 or (e.code >= 500 and method == 'GET'):
                time.sleep(10 * (i + 1)); continue
            raise SystemExit(f'{method} {path}: {e.code} {e.read().decode()[:300]}')
        except (urllib.error.URLError, TimeoutError):
            if method == 'GET':
                time.sleep(10 * (i + 1)); continue
            raise SystemExit(f'{method} {path}: no answer; check the task list before sending again')
    raise SystemExit(f'{method} {path}: gave up')


def ledger(what, task, cost):
    with open(H / 'meshy_ledger.json', 'a+') as f:
        fcntl.flock(f, fcntl.LOCK_EX); f.seek(0); t = f.read()
        rows = json.loads(t) if t.strip() else []
        rows.append(dict(time=time.strftime('%FT%T'), what=what, task=task, credits=cost))
        f.seek(0); f.truncate(); json.dump(rows, f, indent=1)


def task(rec_path, key, kind, body, cost):
    rec = json.loads(rec_path.read_text()) if rec_path.exists() else {}
    if key not in rec:
        rec[key] = call('POST', kind, body)['result']
        rec_path.write_text(json.dumps(rec, indent=1)); ledger(str(rec_path.parent.relative_to(H)) + ':' + key, rec[key], cost)
    while True:
        t = call('GET', f'{kind}/{rec[key]}')
        if t['status'] == 'SUCCEEDED':
            return t, rec[key]
        if t['status'] in ('FAILED', 'CANCELED', 'EXPIRED'):
            raise SystemExit(f'{key}: {t["status"]} {t.get("task_error")}')
        time.sleep(8)


def fetch(url, path):
    if not path.exists():
        path.write_bytes(urllib.request.urlopen(url, timeout=600).read())


def rig(name, version):
    h, idle, talk, *walk = PEOPLE[name]
    d = H / 'rig' / name / version; d.mkdir(parents=True, exist_ok=True); rp = d / 'record.json'
    url = json.loads((H / f'rodin/{name}/{version}/result.json').read_text())['model_mesh']['url']
    t, rid = task(rp, 'rig', 'rigging', dict(model_url=url, height_meters=h, include_fingers=True), 5)
    fetch(t['result']['rigged_character_glb_url'], d / 'rigged.glb')
    for label, aid in (('idle', idle), ('talk', talk), ('walk', walk[0] if walk else None)):
        if aid is None:
            continue
        c, _ = task(rp, f'{label}_{aid}', 'animations',
                    dict(rig_task_id=rid, action_id=aid, post_process=dict(operation_type='change_fps', fps=30)), 3)
        fetch(c['result']['animation_glb_url'], d / f'{label}_{aid}.glb')
    print('rig done', name)


def aligned(d, v):
    p = subprocess.run(['uv', 'run', '--offline', '--with', 'pillow', '--with', 'numpy', 'python', str(H / 'face/align.py'),
                        str(d / f'view_{v}.png'), str(d / f'out_{v}.png')], capture_output=True, text=True)
    return p.returncode == 0, (p.stdout.strip() or p.stderr.strip()[-200:])


SIDE = ("\nThe head is seen at a three-quarter angle, turned away from the camera, and MUST stay turned at exactly that angle: "
        "this is an edit of Image 1 in place, not a new portrait. The eyes look where the head points, not at the camera.")


def face(name):
    """Front view: the render plus the identity crop. Three-quarter views: the render alone (the front-on crop pulled
    the head round to face the camera). Every result must pass face/align.py; two retries, then the view is left out."""
    d = H / 'face' / name; rp = d / 'record.json'; prompt = (d / 'prompt.txt').read_text()
    solo = prompt.replace('; Image 2 shows their face for identity and colouring only (do not copy its angle or framing)', '').replace(' as in Image 2', '') + SIDE
    uri = lambda p: f'data:{mimetypes.guess_type(str(p))[0]};base64,' + base64.b64encode(p.read_bytes()).decode()
    for v in ('front', 'left45', 'right45'):
        out = d / f'out_{v}.png'
        for attempt in range(4):
            if not out.exists():
                key = v + (f'_r{attempt}' if attempt else '')
                rec = json.loads(rp.read_text()) if rp.exists() else {}
                if (d / f'rejected_{key}.png').exists():
                    continue
                side = v != 'front' or attempt > 1
                refs = [uri(d / f'in_{v}.png')] + ([] if side else [uri(d / 'ref.png')])
                t, _ = task(rp, key, 'image-to-image', dict(ai_model='nano-banana-pro', prompt=solo if side else prompt,
                            reference_image_urls=refs), 9)
                fetch(t['image_urls'][0], out)
            else:
                key = v + (f'_r{attempt}' if attempt else '')
                while (d / f'rejected_{key}.png').exists():
                    attempt += 1; key = f'{v}_r{attempt}'
            good, why = aligned(d, v)
            print(name, v, key, why, flush=True)
            if good:
                break
            out.rename(d / f'rejected_{key}.png')
    print('face done', name)


if __name__ == '__main__':
    cmd, who = sys.argv[1:3]
    ver = sys.argv[sys.argv.index('--version') + 1] if '--version' in sys.argv else 'v1'
    rig(who, ver) if cmd == 'rig' else face(who)
