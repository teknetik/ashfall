"""Shared ElevenLabs budget guard for the Steady Hands bench audio (sound effects and voice).

The cap covers everything this brief spends: the sum of the response `character-cost` header of every take recorded
under unity/staging/elevenlabs-audio/bench-20261120/ (sfx/*.json and voice/*.json), plus speech-to-text checks logged in
stt_spend.json. The key is read from the repository .env and never printed."""
import json, re, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STAGE = ROOT / 'unity/staging/elevenlabs-audio/bench-20261120'
CAP = 5500
API = 'https://api.elevenlabs.io/v1'


def credential():
    m = re.search(r'^\s*(?:export\s+)?ELEVENLABS_API_KEY\s*=\s*(.+)$', (ROOT / '.env').read_text(), re.M)
    if not m:
        raise SystemExit('ELEVENLABS_API_KEY is absent from the project .env')
    return m.group(1).strip().strip('"\'')


def subscription(key):
    req = urllib.request.Request(API + '/user/subscription', headers={'xi-api-key': key})
    with urllib.request.urlopen(req, timeout=60) as r:
        s = json.load(r)
    s = {k: s.get(k) for k in ('tier', 'character_count', 'character_limit', 'next_character_count_reset_unix')}
    s['left'] = s['character_limit'] - s['character_count']
    return s


def spent():
    total = 0
    for rec in STAGE.glob('*/*.json'):
        try:
            r = json.loads(rec.read_text()).get('response', {})
        except Exception:
            continue
        total += int(r.get('character-cost', 0) or 0)
    stt = HERE / 'stt_spend.json'
    if stt.exists():
        total += sum(int(x.get('credits', 0)) for x in json.loads(stt.read_text()))
    return total


def log_run(kind, before, after, spent_run, note=''):
    p = HERE / 'ledger.json'
    rows = json.loads(p.read_text()) if p.exists() else []
    import datetime as dt
    rows.append({'utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'kind': kind, 'cap': CAP, 'spent_this_run_by_header': spent_run,
                 'spent_total_by_header': spent(), 'subscription_left_before': before and before['left'],
                 'subscription_left_after': after and after['left'],
                 'subscription_delta': (before['left'] - after['left']) if before and after else None, 'note': note})
    p.write_text(json.dumps(rows, indent=1) + '\n')
