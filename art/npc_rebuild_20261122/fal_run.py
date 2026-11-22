#!/usr/bin/env python3
"""fal runner for the NPC rebuild (Carl, 22 Nov 2026: "we have $13 in fal credit, use as much of it as needed").

Uses FAL_KEY from the project .env (the account with the credit), never printed or written. Every job is booked in
fal_ledger.json under a lock before it is sent, at listed prices, and refused if the total would pass CAP. A job that
was submitted is only ever polled again, never sent twice.

  fal_run.py sheet NAME [--res 2K|4K] [--version v1] [--ref IMG ...]
        prompt concept/p_NAME_VERSION.txt -> concept/NAME_sheet_VERSION.png      $0.15 (4K: $0.30)
  fal_run.py model NAME [--version v1] [--std]
        concept/NAME/panel_{front,side,back}.png -> rodin/NAME/VERSION/model.glb $1.20 HighPack, $0.40 --std
  fal_run.py total
"""
import argparse, base64, fcntl, json, mimetypes, re, sys, time, urllib.error, urllib.request
from pathlib import Path

H = Path(__file__).resolve().parent
ROOT = H.parents[1]
CAP = 13.00
LEDGER = H / 'fal_ledger.json'


def key():
    for l in (ROOT / '.env').read_text().splitlines():
        m = re.match(r'\s*FAL_KEY\s*=\s*(.+?)\s*$', l)
        if m:
            return m.group(1).strip('"\'')
    sys.exit('FAL_KEY is not in .env')


def rows_update(fn):
    with open(LEDGER, 'a+') as f:
        fcntl.flock(f, fcntl.LOCK_EX); f.seek(0); t = f.read()
        rows = json.loads(t) if t.strip() else []
        res = fn(rows)
        f.seek(0); f.truncate(); json.dump(rows, f, indent=1)
        return res


def uri(p):
    return f"data:{mimetypes.guess_type(p)[0]};base64," + base64.b64encode(Path(p).read_bytes()).decode()


def api(url, body=None, k=None):
    r = urllib.request.Request(url, None if body is None else json.dumps(body).encode(),
                               {'Authorization': 'Key ' + k, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(r, timeout=300) as x:
        return json.load(x)


def job(id, endpoint, body, usd):
    k = key()

    def book(rows):
        for r in rows:
            if r['id'] == id and r['state'] != 'rejected':
                return dict(r), False
        total = sum(r['usd'] for r in rows)
        if total + usd > CAP + 1e-9:
            sys.exit(f'cap: ${total:.2f} booked, ${usd:.2f} more would pass ${CAP:.2f}')
        rows.append(dict(id=id, endpoint=endpoint, usd=usd, state='booked', time=time.strftime('%FT%T')))
        return dict(rows[-1]), True

    def put(**kw):
        rows_update(lambda rows: [r for r in rows if r['id'] == id][-1].update(kw))

    r, new = rows_update(book)
    if new:
        try:
            q = api('https://queue.fal.run/' + endpoint, body, k)
        except urllib.error.HTTPError as e:
            text = e.read().decode('utf8', 'replace').replace(k, '[REDACTED]')[:400]
            if e.code in (400, 401, 402, 403, 413, 422):
                put(state='rejected', usd=0.0, note=f'{e.code} {text}')
            else:
                put(state='uncertain', note=f'{e.code} {text}')
            sys.exit(f'{id}: fal answered {e.code} {text}')
        except Exception as e:
            put(state='uncertain', note=type(e).__name__); sys.exit(f'{id}: no answer ({type(e).__name__}); not resending')
        put(state='submitted', request_id=q['request_id'], status_url=q['status_url'], response_url=q['response_url']); r.update(q)
    elif 'status_url' not in r:
        sys.exit(f'{id}: booked without a request id ({r["state"]}); not resending')
    end = time.time() + 1500
    while time.time() < end:
        try:
            if api(r['status_url'], k=k).get('status') == 'COMPLETED':
                break
        except urllib.error.URLError:
            pass
        time.sleep(6)
    else:
        sys.exit(f'{id}: still running; run again to keep polling')
    try:
        res = api(r['response_url'], k=k)
    except urllib.error.HTTPError as e:
        text = e.read().decode('utf8', 'replace').replace(k, '[REDACTED]')[:400]
        put(state='failed', note=text); sys.exit(f'{id}: failed {text}')
    put(state='done')
    return res


def main():
    a = argparse.ArgumentParser()
    a.add_argument('cmd', choices=['sheet', 'model', 'total']); a.add_argument('name', nargs='?')
    a.add_argument('--res', default='2K', choices=['2K', '4K']); a.add_argument('--version', default='v1')
    a.add_argument('--std', action='store_true'); a.add_argument('--ref', nargs='*', default=[])
    o = a.parse_args(); n, v = o.name, o.version
    if o.cmd == 'sheet':
        out = H / f'concept/{n}_sheet_{v}.png'
        if out.exists():
            return print('exists', out)
        body = dict(prompt=(H / f'concept/p_{n}_{v}.txt').read_text(), aspect_ratio='16:9', resolution=o.res,
                    output_format='png', num_images=1)
        ep = 'fal-ai/nano-banana-pro'
        if o.ref:
            ep += '/edit'; body['image_urls'] = [uri(x) for x in o.ref]
        res = job(f'sheet:{n}:{v}', ep, body, .30 if o.res == '4K' else .15)
        urllib.request.urlretrieve(res['images'][0]['url'], out); print('wrote', out)
    elif o.cmd == 'model':
        d = H / f'rodin/{n}/{v}'; d.mkdir(parents=True, exist_ok=True)
        if (d / 'model.glb').exists():
            return print('exists', d)
        body = dict(image_urls=[uri(H / f'concept/{n}/panel_{p}.png') for p in ('front', 'side', 'back')],
                    tier='Gen-2.5-High', quality_mesh_option='150K Triangle', material='PBR', TAPose=True,
                    geometry_file_format='glb', seed=20261)
        if not o.std:
            body['addons'] = dict(high_pack=True)
        res = job(f'model:{n}:{v}', 'fal-ai/hyper3d/rodin/v2.5', body, .40 if o.std else 1.20)
        (d / 'result.json').write_text(json.dumps(res, indent=1))
        urllib.request.urlretrieve(res['model_mesh']['url'], d / 'model.glb'); print('wrote', d / 'model.glb')
    rows = json.loads(LEDGER.read_text()) if LEDGER.exists() and LEDGER.read_text().strip() else []
    print(f'fal booked at list prices: ${sum(r["usd"] for r in rows):.2f} of ${CAP:.2f}')


if __name__ == '__main__':
    main()
