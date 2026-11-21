#!/usr/bin/env python3
"""Steady Hands bench sound effects (audio agent, 20 Nov 2026).

  python3 art/steady_hands_bench_20261120/audio/gen_sfx.py                 # dry run: plan, cache state, cost estimate
  python3 art/steady_hands_bench_20261120/audio/gen_sfx.py --generate      # paid takes for missing variants, then master
  python3 art/steady_hands_bench_20261120/audio/gen_sfx.py --master        # master cached takes and synthesis only
  ... [--only seat,screw.camout]                                           # restrict to id prefixes (asm. optional)

Run it under ~/.local/state/ward-programme/heavy.sh (memory cap). Follows unity/tools/generate_combat_audio_20261119.py
and imports its helpers (load, trim, event_lufs, fit_lufs, spectral filters) and generate_elevenlabs_audio.generate
(cached requests with records, no automatic retries). Event table: events.json (make_events.py).

Sources: unity/staging/elevenlabs-audio/bench-20261120/sfx/<group>-<name>-<nn>-<hash>.mp3 (+ .json request record);
the hash is of the exact request, so an edited prompt is a new take and the old one stays on disk.
Output: Assets/AthenHill/Audio/ElevenLabs/Bench/<group>/<group>-<name>-<nn>.wav (44.1 kHz 16-bit, mono; the bed stereo)
with .meta files carrying stable GUIDs (md5 of the asset path), plus folder .meta files.
Manifest: audio/manifest.json (contract section C), seam checks: audio/seam_check.json, balance in the manifest.
Budget: budget.py (cap 5,500 credits across sound effects, voice and speech-to-text, subscription read before and after).
"""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'unity/tools'))
sys.path.insert(0, str(HERE))
import generate_elevenlabs_audio as city            # noqa: E402
import generate_combat_audio_20261119 as cmb        # noqa: E402
import budget                                       # noqa: E402

RATE = 44100
SRC = budget.STAGE / 'sfx'
UNITY = ROOT / 'unity/AthenHill'
DEST = UNITY / 'Assets/AthenHill/Audio/ElevenLabs/Bench'
EVENTS = json.loads((HERE / 'events.json').read_text())
INFLUENCE = EVENTS['prompt_influence']
cmb.SOURCE = SRC                                   # cmb.lufs writes its scratch file there
RATE_GUESS = 10                                    # credits per requested second (19 Nov: 53 takes, 511 credits)

FOLDER_META = """fileFormatVersion: 2
guid: {guid}
folderAsset: yes
DefaultImporter:
  externalObjects: {{}}
  userData:
  assetBundleName:
  assetBundleVariant:
"""
CLIP_META = """fileFormatVersion: 2
guid: {guid}
AudioImporter:
  externalObjects: {{}}
  serializedVersion: 8
  defaultSettings:
    serializedVersion: 2
    loadType: {load}
    sampleRateSetting: 0
    sampleRateOverride: 44100
    compressionFormat: {fmt}
    quality: {quality}
    conversionMode: 0
    preloadAudioData: 1
  platformSettingOverrides: {{}}
  forceToMono: 0
  normalize: 0
  loadInBackground: 0
  ambisonic: 0
  3D: 1
  userData:
  assetBundleName:
  assetBundleVariant:
"""


def guid(rel):
    return hashlib.md5(('ward-steady-hands-bench-20261120/' + rel).encode()).hexdigest()


def write_meta(path, folder=False, bed=False):
    meta = Path(str(path) + '.meta')
    if meta.exists():
        return
    rel = str(path.relative_to(UNITY / 'Assets'))
    if folder:
        meta.write_text(FOLDER_META.format(guid=guid(rel)))
    elif bed:   # ambience: Vorbis compressed in memory (AUDIO.md)
        meta.write_text(CLIP_META.format(guid=guid(rel), load=1, fmt=1, quality=0.8))
    else:       # short effects: PCM, decompress on load, no import normalisation (levels are mastered here)
        meta.write_text(CLIP_META.format(guid=guid(rel), load=0, fmt=0, quality=1))


def ensure_folder(path):
    path.mkdir(parents=True, exist_ok=True)
    p = path
    while p != UNITY / 'Assets/AthenHill/Audio/ElevenLabs':
        write_meta(p, folder=True)
        p = p.parent


# ------------------------------------------------------------------ helpers
def load(path, channels=1):
    import subprocess
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'f32le', '-ar', str(RATE), '-ac', str(channels), '-'])
    x = np.frombuffer(raw, dtype='<f4').reshape(-1, channels).copy()
    x -= x.mean(axis=0)
    return x[:, 0] if channels == 1 else x


def write(path, s):
    import wave
    s = np.asarray(s)
    ch = 1 if s.ndim == 1 else s.shape[1]
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes((np.clip(s, -1, 1) * 32767).astype('<i2').tobytes())


def db(v): return 20 * np.log10(max(1e-9, float(v)))
def peak_db(x): return db(np.abs(x).max())
def mono(x): return x if x.ndim == 1 else x.mean(axis=1)


def loop_lufs(x):
    y = np.concatenate([x, x, x]) if len(x) < 3 * RATE else x
    if y.ndim == 1:
        return cmb.lufs(y)[0]
    import subprocess
    tmp = SRC / '_measure_st.wav'; write(tmp, y)
    try:
        out = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(tmp), '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    finally:
        tmp.unlink()
    s = out[out.rfind('Summary:'):]
    return float(s.split('I:')[1].split()[0])


def fit_loop(x, target, cap):
    """Plain gain to the integrated loudness target; never past the peak cap (a loop is not limited)."""
    for _ in range(3):
        g = 10 ** ((target - loop_lufs(x)) / 20)
        g = min(g, 10 ** (cap / 20) / max(1e-9, float(np.abs(x).max())))
        x = x * g
    return x


def low_fraction(x, cut=150):
    spec = np.abs(np.fft.rfft(mono(x))) ** 2; f = np.fft.rfftfreq(len(mono(x)), 1 / RATE)
    return float(spec[f < cut].sum() / max(1e-12, spec.sum()))


def centroid(x):
    spec = np.abs(np.fft.rfft(mono(x))); f = np.fft.rfftfreq(len(mono(x)), 1 / RATE)
    return float((spec * f).sum() / max(1e-12, spec.sum()))


def onsets(x):
    """Separate loud events in a one-shot: peaks of the 10 ms envelope above half the maximum, 120 ms apart."""
    w = int(.01 * RATE); n = len(x) // w
    if n < 2: return 1
    env = np.sqrt((x[:n * w].reshape(n, w) ** 2).mean(axis=1)); thr = env.max() * .5
    count, last = 0, -99
    for i in range(1, n - 1):
        if env[i] >= thr and env[i] >= env[i - 1] and env[i] >= env[i + 1] and i - last > 12:
            count += 1; last = i
    return max(1, count)


# ------------------------------------------------------------------ loops
def make_loop(x, seconds, fade=.12, rank=0):
    """Cut a seamless loop of about `seconds` from the steadiest part of x (mono or stereo) and cross-fade it into itself.

    Segment s = x[a:a+N+F]; loop = s[:N] with its first F samples replaced by s[:F]*in + s[N:N+F]*out, so the last
    sample of the loop (s[N-1]) runs into s[N] at the wrap: the waveform is continuous by construction. N is searched
    within +-12 % for the best normalised correlation of the two overlapped regions; correlated (tonal) overlaps get a
    linear fade, uncorrelated (noisy) ones an equal-power fade."""
    m = mono(x); F = int(fade * RATE)
    N0 = min(int(seconds * RATE), len(m) - F - int(.1 * RATE))
    w = int(.05 * RATE); nw = len(m) // w
    env = 20 * np.log10(np.sqrt((m[:nw * w].reshape(nw, w) ** 2).mean(axis=1)) + 1e-9)
    span = (N0 + F) // w + 1
    lo, hi = int(nw * .08), max(int(nw * .08) + 1, nw - span - int(nw * .05))
    scored = []
    for i in range(lo, max(lo + 1, hi)):
        seg = env[i:i + span]
        if len(seg) < span: break
        scored.append((seg.std() + max(0, env.max() - 6 - seg.mean()) * .5, i, seg.std()))   # steady, not a quiet gap
    scored.sort(); picks = []
    for sc_ in scored:                       # distinct starting points, at least a quarter loop apart
        if all(abs(sc_[1] - p[1]) > span // 4 for p in picks): picks.append(sc_)
    best, a_w, sd = picks[min(rank, len(picks) - 1)] if picks else (0, lo, 0)
    a = a_w * w
    best_c, N = -2, N0
    for n in range(int(N0 * .88), int(N0 * 1.12), max(1, int(.002 * RATE))):
        if a + n + F > len(m): break
        p, q = m[a:a + F], m[a + n:a + n + F]
        c = float(np.dot(p, q) / (np.linalg.norm(p) * np.linalg.norm(q) + 1e-12))
        if c > best_c: best_c, N = c, n
    s = x[a:a + N + F].copy()
    t = np.linspace(0, 1, F, endpoint=False)
    if best_c > .5: fin, fout = t, 1 - t
    else: fin, fout = np.sin(t * np.pi / 2), np.cos(t * np.pi / 2)
    if s.ndim == 2: fin, fout = fin[:, None], fout[:, None]
    loop = s[:N].copy()
    loop[:F] = s[:F] * fin + s[N:N + F] * fout
    return loop, {'start_s': round(a / RATE, 3), 'seconds': round(N / RATE, 3), 'crossfade_s': fade,
                  'overlap_correlation': round(best_c, 3), 'fade': 'linear' if best_c > .5 else 'equal-power',
                  'section_level_std_db': round(float(sd), 2), 'start_rank': rank}


def densify(m, seconds=7.0, grain=.16, xf=.03, seed=3):
    """For a gappy source (strokes, ticks or swirls with silences between): splice its active stretches (20 ms windows
    within 12 dB of the loud 90th percentile) into a continuous stream of 160 ms grains joined by 30 ms equal-power
    cross-fades, in source order, so the loop has no holes and still carries the source's own texture."""
    w = int(.02 * RATE); nw = len(m) // w
    env = 20 * np.log10(np.sqrt((m[:nw * w].reshape(nw, w) ** 2).mean(axis=1)) + 1e-9)
    act = np.flatnonzero(env > np.percentile(env, 90) - 12)
    G, X = int(grain * RATE), int(xf * RATE)
    starts = [i * w for i in act if i * w + G + X < len(m)]
    if not starts: return m
    rng = np.random.default_rng(seed); out = np.zeros(0); k = 0
    t = np.linspace(0, 1, X, endpoint=False); fin, fout = np.sin(t * np.pi / 2), np.cos(t * np.pi / 2)
    while len(out) < seconds * RATE:
        a = starts[k % len(starts)]; g = m[a:a + G + X].copy()
        if len(out): out[-X:] = out[-X:] * fout + g[:X] * fin; out = np.concatenate([out, g[X:]])
        else: out = g
        k += max(1, int(rng.integers(1, 4)))
    return out


def best_loop(x, seconds):
    """Try three cross-fade lengths at the three best starting points and keep the cut whose seam check passes with
    the most margin (the first passing candidate at equal margin)."""
    best = None
    for fade in (.12, .2, .3, .06):
        for rank in range(3):
            loop, cut = make_loop(x, seconds, fade, rank)
            ok, sc = seam_check(loop)
            margin = min(min(1 - v['jump_ratio'], 1.5 - v['hf_ratio'], max(1.0, v['level_step_p99_db']) - v['level_step_db']) for v in sc.values())
            if best is None or (ok, margin) > (best[2], best[3]): best = (loop, cut, ok, margin, sc)
    return best


def resample(x, factor):
    """Pitch by resampling (what an AudioSource does): factor 1.3 plays faster/higher."""
    n = int(len(x) / factor); idx = np.arange(n) * factor
    return np.interp(idx, np.arange(len(x)), x)


def seam_check(loop):
    """Tile the loop three times and compare the seams with the rest of the loop, at pitch 0.8, 1.0 and 1.3:
    - jump: |y[n]-y[n-1]| at the seam over the 99.9th percentile of the loop's own sample steps (<= 1 means no click);
    - hf: energy above 6 kHz in a 4 ms window at the seam over the loop's own 99th percentile window (<= 1.5 passes);
    - level: 20 ms RMS change across the seam against the loop's 99th percentile change (dB)."""
    m = mono(loop); res = {}
    for pitch in (.8, 1.0, 1.3):
        y = resample(np.concatenate([m, m, m]), pitch)
        L = len(m) / pitch; seams = [int(round(L)), int(round(2 * L))]
        d = np.abs(np.diff(y)); p999 = np.percentile(d[int(L):int(2 * L)], 99.9)
        jump = max(d[s - 2:s + 2].max() for s in seams) / max(1e-9, p999)
        hp = cmb.spectral(y, lambda f: cmb.highpass(f, 6000, 4))
        w = int(.004 * RATE); nwin = len(hp) // w
        e = (hp[:nwin * w].reshape(nwin, w) ** 2).mean(axis=1)
        inner = e[int(L / w) + 2:int(2 * L / w) - 2]
        ref = np.percentile(inner, 99) if len(inner) else 1e-12
        hf = max(e[max(0, s // w - 1):s // w + 2].max() for s in seams) / max(1e-15, ref)
        w2 = int(.02 * RATE); n2 = len(y) // w2
        r = 20 * np.log10(np.sqrt((y[:n2 * w2].reshape(n2, w2) ** 2).mean(axis=1)) + 1e-9)
        dr = np.abs(np.diff(r)); inner_dr = dr[int(L / w2) + 2:int(2 * L / w2) - 2]
        lv = max(dr[max(0, s // w2 - 1):s // w2 + 1].max() for s in seams)
        res[str(pitch)] = {'jump_ratio': round(float(jump), 2), 'hf_ratio': round(float(hf), 2),
                           'level_step_db': round(float(lv), 2), 'level_step_p99_db': round(float(np.percentile(inner_dr, 99)), 2)}
    ok = all(v['jump_ratio'] <= 1.0 and v['hf_ratio'] <= 1.5 and v['level_step_db'] <= max(1.0, v['level_step_p99_db']) for v in res.values())
    return ok, res


# ------------------------------------------------------------------ synthesis (no API)
def env_exp(n, tau): return np.exp(-np.arange(n) / RATE / tau)


def res_noise(rng, n, f, q_tau):
    """A noise burst through a damped resonance at f (convolution with a decaying sine)."""
    t = np.arange(int(q_tau * 6 * RATE)) / RATE
    k = np.sin(2 * np.pi * f * t) * np.exp(-t / q_tau)
    burst = rng.normal(size=n)
    return np.convolve(burst, k)[:n]


def fade_out(x, ms=4):
    n = min(len(x) // 3, int(ms / 1000 * RATE)); x[-n:] *= np.linspace(1, 0, n); return x


def synth(recipe, i):
    rng = np.random.default_rng(int(hashlib.md5(recipe.encode()).hexdigest()[:6], 16) + i)
    if recipe == 'damper_tick':     # padded mass against a damped stop: low-mid thock, soft, no ring
        n = int(.09 * RATE); t = np.arange(n) / RATE
        f = 340 + 60 * i
        body = np.sin(2 * np.pi * f * t + 3 * np.exp(-t / .004)) * np.exp(-t / .012)
        pad = cmb.spectral(rng.normal(size=n) * np.exp(-t / .0025), lambda fr: cmb.lowpass(fr, 2800, 2) * cmb.highpass(fr, 300, 1))
        x = body + .6 * pad / max(1e-9, np.abs(pad).max())
        a = int(.0015 * RATE); x[:a] *= np.linspace(0, 1, a)
        return fade_out(x)
    if recipe == 'damper_settle':   # one swing of the mass: a short airy swish, then the tick
        n = int(.32 * RATE); t = np.arange(n) / RATE
        sw = cmb.spectral(rng.normal(size=n), lambda fr: cmb.highpass(fr, 900, 2) * cmb.lowpass(fr, 4500, 2))
        sw *= np.sin(np.pi * np.clip(t / .24, 0, 1)) ** 2 * .25
        tick = synth('damper_tick', i); x = sw.copy(); at = int(.22 * RATE)
        x[at:at + len(tick)] += tick[:n - at] * 1.4
        return fade_out(x)
    if recipe == 'probe':           # a probe tip touching a terminal: tiny bright tick
        n = int(.03 * RATE)
        x = res_noise(rng, n, 4800 + 500 * i, .0018) * env_exp(n, .004) + .4 * res_noise(rng, n, 7300, .001) * env_exp(n, .002)
        return fade_out(x)
    if recipe == 'switch':          # a rocker switch: two close transients
        n = int(.05 * RATE); x = np.zeros(n)
        for at, f, g in ((0, 2900 + 200 * i, 1), (int(.007 * RATE), 1900, .6)):
            m = n - at; x[at:] += g * res_noise(rng, m, f, .0015) * env_exp(m, .005)
        return fade_out(x)
    if recipe == 'lamp':            # relay pull-in + contact + the lamp's faint filament buzz
        n = int(.22 * RATE); t = np.arange(n) / RATE; x = np.zeros(n)
        for at, f, g in ((0, 1500 + 150 * i, 1), (int(.006 * RATE), 3400, .7), (int(.011 * RATE), 2600, .35)):
            m = n - at; x[at:] += g * res_noise(rng, m, f, .002) * env_exp(m, .006)
        buzz = sum(np.sin(2 * np.pi * 100 * k * t) / k for k in (1, 2, 3, 4)) * .05
        x += buzz * np.clip((t - .012) / .02, 0, 1) * np.exp(-np.maximum(0, t - .03) / .08)
        return fade_out(x, 15)
    if recipe == 'buzzer':          # electromechanical buzzer: a rasping 110 Hz pulse train with jitter
        dur = (.38, .62)[i % 2]; n = int(dur * RATE); t = np.arange(n) / RATE
        f0 = 110 + 4 * i; ph = np.cumsum(2 * np.pi * (f0 + 2 * rng.normal(size=n).cumsum() / n) / RATE)
        x = np.sign(np.sin(ph)) * (np.abs(np.sin(ph)) ** .3)
        x = cmb.spectral(x, lambda fr: cmb.highpass(fr, 180, 2) * cmb.lowpass(fr, 3800, 2))
        x *= np.clip(t / .008, 0, 1) * np.clip((dur - t) / .03, 0, 1)
        return x
    if recipe == 'cure_hum':        # ballast hum + faint high whine, whole cycles in 2 s so the loop is seamless
        n = int(2.0 * RATE); t = np.arange(n) / RATE
        hum = sum(np.sin(2 * np.pi * 100 * k * t + k) / k ** 1.2 for k in (1, 2, 3, 4, 6))
        whine = .04 * np.sin(2 * np.pi * 9600 * t) * (1 + .3 * np.sin(2 * np.pi * 1.5 * t))
        spec = np.fft.rfft(rng.normal(size=n)); fr = np.fft.rfftfreq(n, 1 / RATE)
        air = np.fft.irfft(spec * cmb.highpass(fr, 2000, 2) * cmb.lowpass(fr, 7000, 2), n); air /= np.abs(air).max()
        return hum / np.abs(hum).max() * .7 + whine + .06 * air
    if recipe in ('power_down', 'power_up', 'glint', 'stage', 'job'):
        def blip(f0, f1, dur, g=1.0, bright=.25):
            n = int(dur * RATE); t = np.arange(n) / RATE
            f = f0 + (f1 - f0) * t / dur; ph = 2 * np.pi * np.cumsum(f) / RATE
            y = np.sin(ph) + bright * np.sin(2 * ph) + bright * .5 * np.sin(3 * ph)
            return g * y * np.minimum(1, t / .004) * np.exp(-t / (dur * .35))
        def place(parts, total):
            x = np.zeros(int(total * RATE))
            for at, y in parts:
                s = int(at * RATE); x[s:s + len(y)] += y[:len(x) - s]
            return fade_out(x, 10)
        if recipe == 'power_down':
            return place([(0, synth('switch', 0) * 3), (.01, blip(1200, 380, .22, .8, .1))], .26)
        if recipe == 'power_up':    # amber (lower), then cyan (higher, brighter)
            return place([(0, blip(620, 700, .09, .7, .15)), (.14, blip(1150, 1200, .14, 1, .3))], .32)
        if recipe == 'glint':
            f = (2400, 2700)[i % 2]
            return place([(0, blip(f, f * 1.02, .18, .6, .05)), (.035, blip(f * 1.5, f * 1.5, .16, .35, .05))], .24)
        if recipe == 'stage':       # two soft digital notes, a fifth apart
            return place([(0, blip(660, 660, .16, .8, .3)), (.11, blip(990, 990, .26, .9, .3))], .42)
        if recipe == 'job':         # three notes up, warm
            return place([(0, blip(523, 523, .16, .8, .35)), (.12, blip(659, 659, .16, .85, .35)), (.24, blip(784, 784, .5, 1, .35))], .8)
    raise ValueError(recipe)


def lamp_ticks(n, seed=5):
    """Faint lamp-housing ticks for the bed, placed circularly so the loop stays seamless."""
    rng = np.random.default_rng(seed); x = np.zeros(n)
    for _ in range(max(3, int(n / RATE / 3.5))):
        at = int(rng.integers(0, n)); m = int(.03 * RATE)
        y = res_noise(rng, m, rng.uniform(2500, 4200), .0015) * env_exp(m, .004) * rng.uniform(.4, 1)
        idx = (at + np.arange(m)) % n; x[idx] += y
    return x / max(1e-9, np.abs(x).max())


# ------------------------------------------------------------------ requests
def body_for(e, prompt):
    return {'text': prompt, 'duration_seconds': e['request_seconds'], 'loop': e['kind'] == 'loop',
            'prompt_influence': INFLUENCE, 'model_id': 'eleven_text_to_sound_v2'}


def asset_name(e, i, body):
    g, n = e['id'].split('.')[1:]
    h = hashlib.sha1(json.dumps(body, sort_keys=True).encode()).hexdigest()[:6]
    return f'{g}-{n}-{i + 1:02d}-{h}'


def observed_rate():
    rates = []
    for rec in SRC.glob('*.json'):
        r = json.loads(rec.read_text())
        c = int(r.get('response', {}).get('character-cost', 0) or 0)
        if c: rates.append(c / r['request']['duration_seconds'])
    return max(rates) if rates else RATE_GUESS


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--generate', action='store_true'); ap.add_argument('--master', action='store_true')
    ap.add_argument('--only', help='comma separated id prefixes, e.g. seat,screw.camout')
    ap.add_argument('--max-takes', type=int, default=10000, help='stop after this many paid takes this run')
    args = ap.parse_args()
    SRC.mkdir(parents=True, exist_ok=True)
    only = [o if o.startswith('asm.') else 'asm.' + o for o in args.only.split(',')] if args.only else None
    events = [e for e in EVENTS['events'] if not only or any(e['id'].startswith(o) for o in only)]
    key = budget.credential() if args.generate else None
    before = budget.subscription(key) if key else None
    spent0 = budget.spent(); rate = observed_rate()
    plan, est_missing, paid = [], 0.0, 0
    if before:
        print(f"subscription before: {before['left']} credits left; this brief has spent {spent0} of {budget.CAP}")
    manifest_path = HERE / 'manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    by_id = {x['id']: x for x in manifest.get('events', [])}
    seams = json.loads((HERE / 'seam_check.json').read_text()) if (HERE / 'seam_check.json').exists() else {}
    stopped = None
    for e in events:
        g, n = e['id'].split('.')[1:]
        files, takes, flags = [], [], []
        for i in range(e['variants']):
            out = DEST / g / f'{g}-{n}-{i + 1:02d}.wav'
            if e['source'] == 'syn':
                takes.append({'variant': i + 1, 'source': 'synth', 'recipe': e['synth']['recipe']})
                if args.master or args.generate:
                    ensure_folder(out.parent)
                    x = synth(e['synth']['recipe'], i)
                    if e['kind'] == 'loop':
                        x = fit_loop(x, e['lufs'], e['peak_cap_dbfs'])
                        ok, sc = seam_check(x); seams[e['id']] = {'ok': ok, 'pitch': sc, 'cut': 'synthesised with whole cycles'}
                    else:
                        x = cmb.fit_lufs(x, e['lufs'], e['peak_cap_dbfs'])
                    write(out, x); write_meta(out); files.append(out)
                    takes[-1].update(seconds=round(len(x) / RATE, 3), peak_dbfs=round(peak_db(x), 2),
                                     measured_lufs=round(loop_lufs(x) if e['kind'] == 'loop' else cmb.event_lufs(x), 2))
                continue
            body = body_for(e, e['prompts'][i]); name = asset_name(e, i, body)
            mp3 = SRC / (name + '.mp3')
            cost = e['request_seconds'] * rate
            row = {'variant': i + 1, 'source': 'elevenlabs', 'take': name, 'cached': mp3.exists(), 'est_credits': round(cost)}
            if not mp3.exists():
                est_missing += cost
                if args.generate and not stopped:
                    left = before['left'] - (budget.spent() - spent0)
                    if budget.spent() + cost * 1.2 > budget.CAP: stopped = f'cap {budget.CAP}: {budget.spent()} spent, {name} would pass it'
                    elif cost * 1.2 > left: stopped = f'subscription has {left} left'
                    elif paid >= args.max_takes: stopped = f'--max-takes {args.max_takes} reached'
                    else:
                        try:
                            city.SOURCE = SRC
                            city.generate(name, body, False, True); paid += 1; row['cached'] = True
                            rate = observed_rate()
                        except RuntimeError as exc:
                            stopped = str(exc).replace(key, '[REDACTED]')[:300]
            takes.append(row)
            if row['cached'] and (args.master or args.generate):
                ensure_folder(out.parent)
                rec = json.loads((SRC / (name + '.json')).read_text())
                row['credits'] = int(rec.get('response', {}).get('character-cost', 0) or 0)
                if e['id'] == 'asm.amb.bed':
                    x = load(mp3, 2)
                    x, cut = make_loop(x, 18.0, fade=1.5)   # bed: one long equal-power fade
                    x = x + lamp_ticks(len(x))[:, None] * 10 ** (-30 / 20) * np.array([.8, 1.0])
                    x = fit_loop(x, e['lufs'], e['peak_cap_dbfs'])
                    ok, sc = seam_check(x); seams[e['id']] = {'ok': ok, 'pitch': sc, 'cut': cut}
                elif e['kind'] == 'loop':
                    x = load(mp3); x = cmb.spectral(x, lambda f: cmb.highpass(f, 35, 2))
                    _, cut0 = make_loop(x, min(2.4, e['request_seconds'] * .8))
                    dense = cut0['section_level_std_db'] > 4
                    if dense: x = densify(x)
                    x, cut, ok, margin, sc = best_loop(x, min(2.4, e['request_seconds'] * .8))
                    cut['densified'] = dense; cut['source_level_std_db'] = cut0['section_level_std_db']
                    x = fit_loop(x, e['lufs'], e['peak_cap_dbfs'])
                    ok, sc = seam_check(x); seams[f"{e['id']}#{i + 1}"] = {'ok': ok, 'pitch': sc, 'cut': cut}
                    lvl = cut['section_level_std_db']
                    if lvl > 4: flags.append(f'v{i + 1}: unsteady section (level std {lvl} dB)')
                    if not ok: flags.append(f'v{i + 1}: seam check failed')
                else:
                    x = cmb.trim(load(mp3)); x = cmb.spectral(x, lambda f: cmb.highpass(f, 40, 2))
                    x = cmb.trim(x)
                    x = cmb.fit_lufs(x, e['lufs'], e['peak_cap_dbfs'])
                    lf, on = low_fraction(x), onsets(x)
                    row.update(low_fraction=round(lf, 2), onsets=on, centroid_hz=round(centroid(x)))
                    if lf > .6: flags.append(f'v{i + 1}: {int(lf * 100)} % of energy below 150 Hz')
                    if len(x) < .03 * RATE: flags.append(f'v{i + 1}: shorter than 30 ms')
                    if on > 3: flags.append(f'v{i + 1}: {on} separate loud events')
                write(out, x); write_meta(out, bed=e['id'] == 'asm.amb.bed'); files.append(out)
                row.update(seconds=round(len(x) / RATE, 3), peak_dbfs=round(peak_db(x), 2),
                           measured_lufs=round(loop_lufs(x) if e['kind'] == 'loop' else cmb.event_lufs(x), 2))
        meas = [(t, f) for t, f in zip([t for t in takes if t.get('measured_lufs') is not None], files)]
        if e['kind'] != 'loop' and len(meas) > 1:
            # level the variants: anything more than 1.5 dB over the quietest variant comes down (plain gain), so a
            # repeated one-shot does not jump in level (takes that hit the limiter can land a few dB under target)
            floor = min(t['measured_lufs'] for t, _ in meas) + 1.5
            for t, f in meas:
                if t['measured_lufs'] > floor:
                    y = load(f) * 10 ** ((floor - t['measured_lufs']) / 20); write(f, y)
                    t['levelled_db'] = round(floor - t['measured_lufs'], 2); t['measured_lufs'] = round(cmb.event_lufs(y), 2)
                    t['peak_dbfs'] = round(peak_db(y), 2)
        plan.append((e['id'], e['source'], e['variants'], sum(1 for t in takes if t.get('cached')), round(sum(t.get('est_credits', 0) for t in takes if not t.get('cached')))))
        if files or e['id'] not in by_id:
            by_id[e['id']] = {'id': e['id'], 'files': [str(f.relative_to(UNITY)) for f in files] or by_id.get(e['id'], {}).get('files', []),
                              'loop': e['kind'] == 'loop', 'lufs': e['lufs'], 'pitch_range': e['pitch_range'], 'note': e['note'],
                              'learn': e['learn'], 'source': e['source'], 'channels': 2 if e['id'] == 'asm.amb.bed' else 1,
                              'takes': takes, 'flags': flags}
        print(f"{e['id']:28s} {e['source']:3s} x{e['variants']}  {'; '.join(flags)}", flush=True)
    after = budget.subscription(key) if key else None
    if key:
        budget.log_run('sfx', before, after, budget.spent() - spent0, stopped or '')
    manifest = {'pass': EVENTS['pass'], 'contract': 'CONTRACT.md section C', 'model': EVENTS['model'],
                'loudness': EVENTS['loudness'], 'paths_relative_to': 'unity/AthenHill',
                'events': [by_id[e['id']] for e in EVENTS['events'] if e['id'] in by_id],
                'contact_matrix': CONTACT, 'voice': manifest.get('voice'), 'balance': manifest.get('balance'),
                'credits_spent_by_header': budget.spent(), 'cap': budget.CAP}
    manifest_path.write_text(json.dumps(manifest, indent=1) + '\n')
    (HERE / 'seam_check.json').write_text(json.dumps(seams, indent=1) + '\n')
    total = sum(p[4] for p in plan)
    print(f'\nplan: {len(plan)} events, {sum(p[2] for p in plan)} clips, {sum(p[2] for p in plan if p[1] == "el")} paid variants; '
          f'missing takes cost about {total} credits at {rate:.1f}/s; spent so far {budget.spent()} of cap {budget.CAP}')
    if after: print(f"subscription after: {after['left']} left (delta {before['left'] - after['left']})")
    if stopped: print('STOPPED:', stopped)


# material pair -> seat event (CONTRACT.md material classes; surfaces: the rubber mat, the steel dish/fixtures)
CONTACT = {
    'note': 'key is "<part material>|<surface material>"; order-free lookup: try a|b then b|a then "<a>|*". Drops into the '
            'parts dish use asm.screw.dish; parts on the floor asm.part.floor; into the scrap bin asm.part.bin.',
    'steel|rubber': 'asm.seat.steel_rubber', 'steel|steel': 'asm.seat.steel_steel', 'steel|alloy': 'asm.seat.steel_steel',
    'alloy|rubber': 'asm.seat.alloy_rubber', 'alloy|alloy': 'asm.seat.alloy_alloy', 'alloy|steel': 'asm.seat.alloy_alloy',
    'wood|rubber': 'asm.seat.wood_rubber', 'wood|steel': 'asm.seat.wood_steel', 'wood|alloy': 'asm.seat.wood_steel',
    'plastic|rubber': 'asm.seat.plastic_rubber', 'plastic|plastic': 'asm.part.connector', 'plastic|steel': 'asm.seat.plastic_rubber',
    'glass|rubber': 'asm.seat.glass_rubber', 'glass|*': 'asm.seat.glass_rubber',
    'copper|rubber': 'asm.seat.copper_rubber', 'copper|*': 'asm.seat.copper_rubber',
    'canvas|*': 'asm.seat.canvas_rubber', 'paper|*': 'asm.card.clip', 'ceramic|*': 'asm.seat.tiny_steel',
    'rubber|*': 'asm.seat.plastic_rubber', 'steel|*': 'asm.seat.steel_rubber', 'alloy|*': 'asm.seat.alloy_rubber',
    'wood|*': 'asm.seat.wood_rubber', 'plastic|*': 'asm.seat.plastic_rubber',
    'mass:tiny': 'asm.seat.tiny_steel (any material when the part mass class is tiny, except glass and copper)',
}

if __name__ == '__main__':
    main()
