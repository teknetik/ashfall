#!/usr/bin/env python3
"""Reference images through fal (Nano Banana Pro), with a shared spending ledger.

Carl put a key for the Teknetik fal account in 1Password on 20 Nov 2026 (the account had $14.53); it is FAL_KEY in the
repository's .env. The fal MCP tools are connected to a different account that has no credit: do not use them to
generate. This script is the only route to fal for this programme.

Usage:
  fal_image.py OUT.png PROMPT.txt --tag AGENT [--aspect 3:2] [--resolution 2K] [--ref IMG ...]

  --tag         who is spending (model-pistol, model-servo, model-bench, orchestrator, ...). Each tag is capped.
  --aspect      auto, 21:9, 16:9, 3:2, 4:3, 5:4, 1:1, 4:5, 3:4, 2:3, 9:16 (default 3:2)
  --resolution  1K, 2K (default) or 4K. The price is the same per image; 4K is slower.
  --ref         reference images (up to 8). With references the /edit endpoint is used and they are sent at full
                size, so fine detail in a reference does carry (unlike the Grok route, which shrinks them).

Each image costs $0.15. Caps: $3.00 per tag, $9.00 in total (edit CAPS below only if the orchestrator says so).
Writes OUT, OUT.prompt.txt and a line in imagegen/fal_ledger.json. Refuses to overwrite OUT. The prompt is sent as
written; if the service refuses it, stop and say so, do not reword to get round a refusal.
"""
import argparse, base64, fcntl, json, mimetypes, os, re, sys, time, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fal_ledger.json')
PRICE = 0.15
CAPS = {'per_tag': 3.00, 'total': 9.00}
ENDPOINT = 'fal-ai/nano-banana-pro'


def key():
    for line in open(os.path.join(ROOT, '.env')):
        m = re.match(r'\s*FAL_KEY\s*=\s*(.+?)\s*$', line)
        if m:
            return m.group(1).strip('"\'')
    sys.exit('FAL_KEY is not in .env')


def reserve(tag, out):
    """Book the spend before the call, under a lock, so parallel agents cannot pass the cap together."""
    with open(LEDGER, 'a+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        text = f.read()
        rows = json.loads(text) if text.strip() else []
        total = sum(r['usd'] for r in rows)
        mine = sum(r['usd'] for r in rows if r['tag'] == tag)
        if total + PRICE > CAPS['total'] + 1e-9:
            sys.exit('fal total cap reached ($%.2f of $%.2f): ask the orchestrator' % (total, CAPS['total']))
        if mine + PRICE > CAPS['per_tag'] + 1e-9:
            sys.exit('fal cap for %s reached ($%.2f of $%.2f): ask the orchestrator' % (tag, mine, CAPS['per_tag']))
        rows.append({'time': time.strftime('%Y-%m-%dT%H:%M:%S'), 'tag': tag, 'usd': PRICE, 'out': out, 'state': 'sent'})
        f.seek(0); f.truncate(); json.dump(rows, f, indent=1)
        return len(rows) - 1, total + PRICE, mine + PRICE


def settle(index, state, note=''):
    with open(LEDGER, 'r+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        rows = json.load(f)
        rows[index]['state'] = state
        if note:
            rows[index]['note'] = note[:300]
        if state == 'rejected':        # validation error or refusal before generation: fal does not bill it
            rows[index]['usd'] = 0.0
        f.seek(0); f.truncate(); json.dump(rows, f, indent=1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('out'); p.add_argument('prompt')
    p.add_argument('--tag', required=True)
    p.add_argument('--aspect', default='3:2')
    p.add_argument('--resolution', default='2K', choices=['1K', '2K', '4K'])
    p.add_argument('--ref', nargs='*', default=[])
    a = p.parse_args()
    out = os.path.abspath(a.out)
    if os.path.exists(out):
        sys.exit('refusing to overwrite ' + out)
    if len(a.ref) > 8:
        sys.exit('at most 8 references')
    prompt = open(a.prompt).read().strip()
    fmt = 'jpeg' if out.lower().endswith(('.jpg', '.jpeg')) else 'png'
    body = {'prompt': prompt, 'aspect_ratio': a.aspect, 'resolution': a.resolution, 'output_format': fmt, 'num_images': 1}
    endpoint = ENDPOINT
    if a.ref:
        endpoint += '/edit'
        urls = []
        for r in a.ref:
            data = open(r, 'rb').read()
            if len(data) > 8 * 1024 * 1024:
                sys.exit('%s is over 8 MB: shrink it first' % r)
            mime = mimetypes.guess_type(r)[0] or 'image/png'
            urls.append('data:%s;base64,%s' % (mime, base64.b64encode(data).decode()))
        body['image_urls'] = urls
    k = key()
    index, total, mine = reserve(a.tag, out)
    req = urllib.request.Request('https://fal.run/' + endpoint, data=json.dumps(body).encode(),
                                 headers={'Authorization': 'Key ' + k, 'Content-Type': 'application/json'})
    try:
        res = json.load(urllib.request.urlopen(req, timeout=300))
    except urllib.error.HTTPError as e:
        text = e.read().decode('utf8', 'replace').replace(k, '[REDACTED]')
        settle(index, 'rejected' if e.code in (400, 401, 403, 422) else 'uncertain', '%s %s' % (e.code, text))
        sys.exit('fal answered %s: %s' % (e.code, text[:600]))
    except Exception as e:                      # timeout or network: the job may have run and been billed
        settle(index, 'uncertain', type(e).__name__)
        sys.exit('no answer from fal (%s); counted as spent, do not simply retry: tell the orchestrator' % type(e).__name__)
    images = res.get('images') or []
    if not images:
        settle(index, 'uncertain', json.dumps(res)[:300])
        sys.exit('fal returned no image: ' + json.dumps(res)[:400])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    urllib.request.urlretrieve(images[0]['url'], out)
    open(out + '.prompt.txt', 'w').write(prompt + '\n\n# fal %s, aspect %s, %s, refs: %s\n' % (
        endpoint, a.aspect, a.resolution, ', '.join(os.path.basename(r) for r in a.ref) or 'none'))
    settle(index, 'done')
    print('wrote %s  (fal spend: %s $%.2f of $%.2f, total $%.2f of $%.2f)' % (out, a.tag, mine, CAPS['per_tag'], total, CAPS['total']))


if __name__ == '__main__':
    main()
