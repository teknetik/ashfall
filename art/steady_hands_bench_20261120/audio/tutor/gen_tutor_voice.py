#!/usr/bin/env python3
"""Brann's guided first job (tutor agent, 21 Nov 2026): a copy of ../gen_voice.py (the audio agent's, frozen) pointed at
tutor/lines.json, its own staging folder, ledger and budget. Same voice, model, settings, spelling map and master.

  python3 art/steady_hands_bench_20261120/audio/gen_voice.py               # dry run: lines, characters, cache state
  python3 art/steady_hands_bench_20261120/audio/gen_voice.py --generate    # paid takes for missing lines, master, install
  python3 art/steady_hands_bench_20261120/audio/gen_voice.py --master      # master cached takes only
  python3 art/steady_hands_bench_20261120/audio/gen_voice.py --stt         # transcribe the installed takes, compare words
  ... --retake ID[,ID]   a further take of a line (take index +1); the newest take is installed, older ones kept

Same model and voice settings as the existing colonist takes (art/showcase_20261119/npc_life/barks.json:
eleven_multilingual_v2, stability 0.55, similarity 0.78, style 0.12, speaker boost), and the Linn master
(art/linn_voice_20261120/linn_voice.py: edge trim, two-pass loudnorm to -20 LUFS / -2 dBTP, 40 ms lead). Spoken spelling
map for lore words (the caption keeps the written word). Takes: unity/staging/elevenlabs-audio/bench-20261120/voice/.
WAVs: Assets/AthenHill/Audio/ElevenLabs/Bench/Voice/<speaker>-<id>.wav with stable .meta GUIDs (md5 of the path).
Budget: tutor_budget.py (whatever the account has left above a 200 credit reserve, Carl 21 Nov). The key is never printed."""
import argparse, datetime as dt, difflib, hashlib, importlib.util, json, re, subprocess, sys, urllib.error, urllib.request, uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
import tutor_budget as budget  # noqa: E402

spec = importlib.util.spec_from_file_location('linn', ROOT / 'art/linn_voice_20261120/linn_voice.py')
linn = importlib.util.module_from_spec(spec); spec.loader.exec_module(linn)
BARKS = json.loads((ROOT / 'art/showcase_20261119/npc_life/barks.json').read_text())
MODEL, SETTINGS = BARKS['model_id'], BARKS['voice_settings']
OUTPUT = 'mp3_44100_128'
DOC = json.loads((HERE / 'lines.json').read_text())
VOICES = DOC['voices']
STAGE = budget.STAGE / 'voice'
UNITY = ROOT / 'unity/AthenHill'
# Spoken spelling only (captions keep the written word). Berms went wrong as "bums"/"bombs" for Linn, Karaveen as "Caravene".
SAY = {'Karaveen': 'Carra-veen', 'Nanofab': 'nano-fab', 'Berms': 'Burrms'}
META = """fileFormatVersion: 2
guid: {guid}
AudioImporter:
  externalObjects: {{}}
  serializedVersion: 8
  defaultSettings:
    serializedVersion: 2
    loadType: 0
    sampleRateSetting: 0
    sampleRateOverride: 44100
    compressionFormat: 1
    quality: 0.85
    conversionMode: 0
    preloadAudioData: 1
  platformSettingOverrides: {{}}
  forceToMono: 1
  normalize: 0
  loadInBackground: 0
  ambisonic: 0
  3D: 1
  userData:
  assetBundleName:
  assetBundleVariant:
"""


def spoken(t):
    for w, s in SAY.items():
        t = re.sub(r'\b' + w + r'\b', s, t)
    return t


def body(line):
    return {'text': spoken(line['text']), 'model_id': MODEL, 'voice_settings': SETTINGS}


def takes(line):
    return sorted(STAGE.glob(f"{line['speaker']}-{line['id']}-t*.mp3"))


def valid(mp3, line):
    rec = mp3.with_suffix('.json')
    if not rec.exists(): return False
    r = json.loads(rec.read_text())
    return r.get('request') == body(line) and r.get('voice_id') == VOICES[line['speaker']]['id'] and r.get('sha256') == linn.sha(mp3)


def chosen(line):
    """The installed take: the one named in picks.json, else the newest valid take."""
    picks = json.loads((HERE / 'picks.json').read_text()) if (HERE / 'picks.json').exists() else {}
    ok = [t for t in takes(line) if valid(t, line)]
    want = picks.get(f"{line['speaker']}-{line['id']}")
    for t in ok:
        if want and t.stem.endswith(want): return t
    return ok[-1] if ok else None


def request(line, key, index):
    vid = VOICES[line['speaker']]['id']; b = body(line)
    mp3 = STAGE / f"{line['speaker']}-{line['id']}-t{index}.mp3"
    req = urllib.request.Request(f'{budget.API}/text-to-speech/{vid}?output_format={OUTPUT}', data=json.dumps(b).encode(),
                                 headers={'xi-api-key': key, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=180) as r:
        audio = r.read(); headers = {k: r.headers[k] for k in ('request-id', 'history-item-id', 'character-cost') if k in r.headers}
        ctype = r.headers.get('Content-Type', '')
    if len(audio) < 1000 or 'audio' not in ctype:
        raise RuntimeError('ElevenLabs did not return audio')
    STAGE.mkdir(parents=True, exist_ok=True)
    tmp = mp3.with_suffix('.tmp.mp3'); tmp.write_bytes(audio)
    subprocess.run(['ffprobe', '-v', 'error', str(tmp)], check=True); tmp.replace(mp3)
    mp3.with_suffix('.json').write_text(json.dumps({'voice_id': vid, 'voice_name': VOICES[line['speaker']]['name'], 'model_id': MODEL,
        'output_format': OUTPUT, 'request': b, 'caption_text': line['text'], 'generated_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'response': headers, 'sha256': linn.sha(mp3)}, indent=2) + '\n')
    return int(headers.get('character-cost') or len(b['text']))


def stt(path, key):
    boundary = uuid.uuid4().hex
    data = (f'--{boundary}\r\nContent-Disposition: form-data; name="model_id"\r\n\r\nscribe_v1\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="language_code"\r\n\r\neng\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
            f'Content-Type: audio/wav\r\n\r\n').encode() + path.read_bytes() + f'\r\n--{boundary}--\r\n'.encode()
    req = urllib.request.Request(budget.API + '/speech-to-text', data=data,
                                 headers={'xi-api-key': key, 'Content-Type': f'multipart/form-data; boundary={boundary}'})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r).get('text', '')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--generate', action='store_true'); ap.add_argument('--master', action='store_true')
    ap.add_argument('--stt', action='store_true'); ap.add_argument('--only', help='comma separated line ids for --stt'); ap.add_argument('--retake', help='comma separated line ids')
    args = ap.parse_args()
    lines = DOC['lines']
    key = budget.credential() if (args.generate or args.stt or args.retake) else None
    before = budget.subscription(key) if key else None
    spent0 = budget.spent(); spent_run = 0; stopped = None
    if before: print(f"subscription before: {before['left']} left; tutor spent {spent0} so far; reserve {budget.RESERVE}")
    retake = set(args.retake.split(',')) if args.retake else set()
    for l in lines:
        n = len(body(l)['text']); have = chosen(l)
        need = (have is None and args.generate) or l['id'] in retake
        if need and not stopped:
            if n > before['left'] - spent_run - budget.RESERVE: stopped = f"reserve of {budget.RESERVE} reached at {l['id']}"
            else:
                try:
                    spent_run += request(l, key, len(takes(l)) + 1); have = chosen(l)
                except urllib.error.HTTPError as e:
                    stopped = f"HTTP {e.code} {e.read().decode(errors='replace')[:200].replace(key, '[REDACTED]')}"
                except Exception as e:
                    stopped = str(e).replace(key, '[REDACTED]')[:200]
        if have and (args.generate or args.master or l['id'] in retake):
            wav = UNITY / l['file']; wav.parent.mkdir(parents=True, exist_ok=True)
            for folder in (wav.parent, wav.parent.parent):
                m = Path(str(folder) + '.meta')
                if not m.exists():
                    rel = str(folder.relative_to(UNITY / 'Assets'))
                    m.write_text(f'fileFormatVersion: 2\nguid: {hashlib.md5(("ward-steady-hands-bench-tutor-20261121/" + rel).encode()).hexdigest()}\n'
                                 'folderAsset: yes\nDefaultImporter:\n  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n')
            linn.master(have, wav)
            meta = Path(str(wav) + '.meta')
            if not meta.exists():
                meta.write_text(META.format(guid=hashlib.md5(('ward-steady-hands-bench-tutor-20261121/' + l['file'][len('Assets/'):]).encode()).hexdigest()))
        print(f"{'ok  ' if have else '----'} {l['speaker']:9s} {l['id']:20s} {n:3d}  {l['text']}", flush=True)
    if args.stt:
        rows = []
        old = {r['id']: r for r in json.loads((HERE / 'stt.json').read_text())} if (HERE / 'stt.json').exists() else {}
        only = set(args.only.split(',')) if args.only else None
        for l in lines:
            wav = UNITY / l['file']
            if not wav.exists(): continue
            if only is not None and l['id'] not in only:
                if l['id'] in old: rows.append(old[l['id']])
                continue
            text = stt(wav, key)
            a = linn.words(l['text']); b = linn.words(text)
            sm = difflib.SequenceMatcher(None, a, b)
            rows.append({'id': l['id'], 'speaker': l['speaker'], 'line': l['text'], 'transcript': text, 'word_match': round(sm.ratio(), 3),
                         'differences': [f"{op}: {' '.join(a[i1:i2])} -> {' '.join(b[j1:j2])}" for op, i1, i2, j1, j2 in sm.get_opcodes() if op != 'equal'],
                         'take': chosen(l).name if chosen(l) else None})
            print(f"{sm.ratio():.3f} {l['id']}: {text}", flush=True)
        (HERE / 'stt.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False) + '\n')
    after = budget.subscription(key) if key else None
    if key:
        if args.stt and before and after and before['left'] - after['left'] - spent_run > 0:
            # speech-to-text is not reported by a cost header: charge whatever the subscription lost beyond the takes
            p = HERE / 'stt_spend.json'; rows = json.loads(p.read_text()) if p.exists() else []
            rows.append({'utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'credits': before['left'] - after['left'] - spent_run}); p.write_text(json.dumps(rows, indent=1) + '\n')
        budget.log_run('voice' + (' stt' if args.stt else ''), before, after, spent_run, stopped or '')
    # voice rows in the manifest
    mp = HERE / 'manifest.json'; man = json.loads(mp.read_text()) if mp.exists() else {}
    rows = []
    for l in lines:
        t = chosen(l); wav = UNITY / l['file']
        rows.append({**l, 'spoken_text': body(l)['text'], 'voice': VOICES[l['speaker']], 'take': t.name if t else None,
                     'takes_on_disk': len(takes(l)), 'installed': wav.exists(),
                     **({'after': {**linn.loudness(wav), **linn.probe(wav)}} if wav.exists() else {})})
    man['voice'] = {'model_id': MODEL, 'voice_settings': SETTINGS, 'mastering': 'art/linn_voice_20261120/linn_voice.py master()', 'lines': rows}
    man['credits_spent_by_header'] = budget.spent(); mp.write_text(json.dumps(man, indent=1) + '\n')
    total = sum(len(body(l)['text']) for l in lines); missing = sum(len(body(l)['text']) for l in lines if not chosen(l))
    print(f'{len(lines)} lines, {total} characters, missing {missing}; spent this run {spent_run}; tutor total {budget.spent()}')
    if after: print(f"subscription after: {after['left']} left")
    if stopped: print('STOPPED:', stopped)


if __name__ == '__main__':
    main()
