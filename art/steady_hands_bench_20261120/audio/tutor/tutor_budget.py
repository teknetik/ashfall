"""ElevenLabs budget guard for the tutor lines (tutor agent, 21 Nov 2026). Carl allowed all remaining credits; the guard
keeps RESERVE credits on the account. Spend is the sum of the response `character-cost` header of every take under
unity/staging/elevenlabs-audio/bench-tutor-20261121/ plus speech-to-text logged in stt_spend.json. Key from the
repository .env, never printed. Separate from ../budget.py (the audio agent's 5,500 cap) so neither counts the other."""
import datetime as dt, json, re, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
STAGE = ROOT / 'unity/staging/elevenlabs-audio/bench-tutor-20261121'
RESERVE = 200
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
            total += int(json.loads(rec.read_text()).get('response', {}).get('character-cost', 0) or 0)
        except Exception:
            continue
    stt = HERE / 'stt_spend.json'
    if stt.exists():
        total += sum(int(x.get('credits', 0)) for x in json.loads(stt.read_text()))
    return total


def log_run(kind, before, after, spent_run, note=''):
    p = HERE / 'ledger.json'
    rows = json.loads(p.read_text()) if p.exists() else []
    rows.append({'utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'kind': kind, 'reserve': RESERVE, 'spent_this_run_by_header': spent_run,
                 'spent_total_by_header': spent(), 'subscription_left_before': before and before['left'],
                 'subscription_left_after': after and after['left'],
                 'subscription_delta': (before['left'] - after['left']) if before and after else None, 'note': note})
    p.write_text(json.dumps(rows, indent=1) + '\n')
