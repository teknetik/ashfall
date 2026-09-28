"""Player footstep sets per surface through the cached ElevenLabs pipeline (27 Sep 2026 character-feel pass).

python3 unity/tools/generate_footstep_audio.py --generate      (generate missing sources, then slice and master)
python3 unity/tools/generate_footstep_audio.py                 (re-slice / re-master cached sources only)

Each request asks for a short take of several separate boot steps on one surface. The take is sliced at onsets into
single steps; steps that are too quiet, too long or doubled are rejected, the rest are level-matched within the set
(same RMS, ±0 dB) so no step jumps out, then written as 44.1 kHz mono WAV. Variation (pitch/volume) is applied at
runtime by FootstepAudio. Sources and request records: unity/staging/elevenlabs-audio/footsteps. Mastered WAVs:
Assets/AthenHill/Audio/ElevenLabs/Footsteps. Manifest with per-set loudness: footstep-manifest.json beside the sources.
"""
import argparse, json, subprocess, sys, wave
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import generate_elevenlabs_audio as city

SOURCE = city.SOURCE / 'footsteps'
DEST = city.DEST / 'Footsteps'
RATE = city.RATE
STYLE = ('Close dry foley recording, one person only, separate single footsteps with clear short pauses between them, '
         'no music, no voices, no background ambience, no reverb.')
# surface -> (walk description, run description)
SURFACES = {
    'stone': ('Slow relaxed walking footsteps in soft leather desert boots on worn sandstone paving slabs with a light dusting of grit: soft heel-toe tap and faint gritty scuff.',
              'Jogging footsteps in leather desert boots on sandstone paving with fine grit: firmer tap with a short gritty scuff.'),
    'sand': ('Slow walking footsteps in leather boots on dry packed desert sand: soft muffled crunch and gentle sand shift, very soft.',
             'Running footsteps in leather boots on dry desert sand: soft thuds with sand spray and crunch.'),
    'gravel': ('Slow walking footsteps in leather boots on fine loose gravel and grit: small crisp crunch of little stones.',
               'Running footsteps in leather boots on loose fine gravel: quick crunching steps with scattering pebbles.'),
    'concrete': ('Slow walking footsteps in leather boots on a dusty concrete apron outdoors: dull soft heel tap with a light gritty scrape.',
                 'Jogging footsteps in leather boots on dusty concrete outdoors: firm dull taps with light grit scrape.'),
    'metal': ('Slow walking footsteps in leather boots on a thick steel deck plate: dull low metallic thud, heavy plate, not ringing.',
              'Running footsteps in leather boots on a thick steel deck plate: quick dull metallic thumps, heavy solid plate.'),
    'wood': ('Slow walking footsteps in leather boots on thick weathered wooden planks: soft hollow knock with a slight creak.',
             'Running footsteps in leather boots on thick weathered wooden planks: quick hollow knocks.'),
}
TAKES = 2          # requests per set; each yields ~5-8 steps
# sets whose first two takes gave fewer than 8 usable steps get two more takes
EXTRA_TAKES = {('stone', 'walk'), ('concrete', 'walk'), ('metal', 'walk'), ('metal', 'land'), ('sand', 'land'), ('gravel', 'land')}
TARGET_RMS = -26   # dBFS per step (loudness is set in the mix, this keeps sets consistent)
LAND_TARGET = -22


def sets():
    for surface, (walk, run) in SURFACES.items():
        yield surface, 'walk', walk, 4.5, TARGET_RMS
        yield surface, 'run', run, 3.5, TARGET_RMS + 1
    for surface, text in [('stone', 'A person in leather boots landing from a small jump onto sandstone paving: one firm double-foot landing thump with a gritty scuff.'),
                          ('sand', 'A person in leather boots landing from a small jump onto soft desert sand: one soft heavy thud with a sand crunch and spray.'),
                          ('gravel', 'A person in leather boots landing from a small jump onto loose gravel: one heavy crunching landing.'),
                          ('metal', 'A person in leather boots landing from a small jump onto a thick steel plate: one dull heavy metallic thump.'),
                          ('concrete', 'A person in leather boots landing from a small jump onto concrete: one firm dull landing thud with a scuff.')]:
        yield surface, 'land', text + ' Several separate landings with pauses.', 4.0, LAND_TARGET


def load(path):
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'f32le', '-ar', str(RATE), '-ac', '1', '-'])
    x = np.frombuffer(raw, dtype='<f4').copy(); x -= x.mean(); return x


def slice_steps(x, gait):
    """Split a take into single steps. Loose surfaces (sand, gravel) never fall silent between steps, so onsets are
    rises of >= 8 dB within 60 ms on a 5 ms RMS envelope (local maxima, within 30 dB of the take's peak), at least
    0.3 s apart for walk/land and 0.22 s for run. Each step runs to the next onset (max 0.45 s walk / 0.35 s run /
    0.6 s land)."""
    hop = int(.005 * RATE)
    env = 20 * np.log10(np.sqrt(np.convolve(x**2, np.ones(hop) / hop, mode='same'))[::hop] + 1e-7)
    rise = np.array([env[i] - env[max(0, i - 12):i].min() if i else 0 for i in range(len(env))])
    spacing = .22 if gait == 'run' else .3
    onsets, last = [], -10**9
    for i in range(1, len(env) - 1):
        if rise[i] >= 8 and rise[i] >= rise[i - 1] and rise[i] >= rise[i + 1] and env[i] > env.max() - 30 and (i - last) * hop / RATE > spacing:
            onsets.append(i * hop); last = i
    limit = {'walk': .45, 'run': .35, 'land': .6}[gait]
    steps = []
    for k, s in enumerate(onsets):
        start = max(0, s - int(.006 * RATE))
        end = min(len(x), onsets[k + 1] - int(.01 * RATE) if k + 1 < len(onsets) else len(x), start + int(limit * RATE))
        seg = x[start:end].copy()
        # trim trailing silence, short fades
        e2 = np.abs(seg); act = np.flatnonzero(e2 > e2.max() * .02)
        if len(act): seg = seg[:min(len(seg), act[-1] + int(.03 * RATE))]
        if len(seg) < int(.06 * RATE): continue
        n = int(.003 * RATE); seg[:n] *= np.linspace(0, 1, n)
        n = min(int(.03 * RATE), len(seg) // 3); seg[-n:] *= np.linspace(1, 0, n)
        steps.append(seg)
    return steps


# Loudness of each set as heard (steps with 0.4 s gaps). Walk sits under run and landings; the surfaces keep a
# natural order (soft sand quietest, steel plate loudest) instead of whatever level each generation came back at.
SET_LUFS = {'walk': -30, 'run': -28, 'land': -26}
SURFACE_OFFSET = {'sand': -2.5, 'gravel': -.5, 'stone': 0, 'concrete': 0, 'wood': .5, 'metal': 1.5}


def write(path, s):
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes((np.clip(s, -1, 1) * 32767).astype('<i2').tobytes())


def set_loudness(steps):
    gap = np.zeros(int(.4 * RATE)); tmp = SOURCE / '_set.wav'
    write(tmp, np.concatenate([np.concatenate([s, gap]) for s in steps]))
    try: return lufs(tmp)
    finally: tmp.unlink()


def rms_db(s): return 20 * np.log10(max(1e-9, float(np.sqrt(np.mean(s**2)))))


def lufs(path):
    out = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    summary = out[out.rfind('Summary:'):]
    val = lambda key: float(summary.split(key)[1].split()[0]) if key in summary else None
    return val('I:'), val('Peak:')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate', action='store_true')
    args = parser.parse_args()
    SOURCE.mkdir(parents=True, exist_ok=True); DEST.mkdir(parents=True, exist_ok=True)
    city.SOURCE, keep = SOURCE, city.SOURCE
    manifest = {'provider': 'ElevenLabs', 'model': 'eleven_text_to_sound_v2', 'method': __doc__.strip().splitlines()[2], 'sets': []}
    try:
        for surface, gait, text, seconds, target in sets():
            steps = []
            requests = []
            for take in range(TAKES + (2 if (surface, gait) in EXTRA_TAKES else 0)):
                body = {'text': text + ' ' + STYLE, 'duration_seconds': seconds, 'loop': False, 'prompt_influence': .6, 'model_id': 'eleven_text_to_sound_v2'}
                name = f'{surface}-{gait}-take{take + 1}'
                if take: body['text'] += f' Take {take + 1}.'
                src = city.generate(name, body, False, args.generate)
                requests.append({'source': str(src.relative_to(city.ROOT)), 'request': body})
                steps += slice_steps(load(src), gait)
            levels = np.array([rms_db(s) for s in steps])
            # reject outliers: much quieter (tails picked up as steps) or much louder (doubled / clatter)
            med = np.median(levels) if len(levels) else 0
            keep_idx = [i for i, l in enumerate(levels) if med - 8 <= l <= med + 6]
            chosen = [steps[i] for i in keep_idx][:12]
            for old in DEST.glob(f'{surface}-{gait}-*.wav'): old.unlink()
            # 1) level-match steps within the set, 2) scale the set to its loudness target (LUFS of the steps
            # heard with 0.4 s gaps), keeping every step's peak at or below -3 dBFS.
            chosen = [s * 10 ** ((target - rms_db(s)) / 20) for s in chosen]
            want = SET_LUFS[gait] + SURFACE_OFFSET.get(surface, 0)
            i_lufs = peak = None
            if chosen:
                i_lufs, _ = set_loudness(chosen)
                g = min(10 ** ((want - i_lufs) / 20), min(10 ** (-3 / 20) / float(np.abs(s).max()) for s in chosen))
                chosen = [s * g for s in chosen]
                i_lufs, peak = set_loudness(chosen)
            files = []
            for i, s in enumerate(chosen):
                out = DEST / f'{surface}-{gait}-{i + 1:02d}.wav'
                write(out, s)
                files.append({'file': out.name, 'seconds': round(len(s) / RATE, 3), 'rms_dbfs': round(rms_db(s), 2), 'peak_dbfs': round(20 * np.log10(float(np.abs(s).max())), 2), 'sha256': city.sha(out)})
            manifest['sets'].append({'surface': surface, 'gait': gait, 'sliced': len(steps), 'kept': len(files), 'target_rms_dbfs': target, 'target_set_lufs': want,
                                     'set_integrated_lufs_with_0.4s_gaps': i_lufs, 'set_true_peak_dbtp': peak, 'requests': requests, 'files': files})
            print(f'{surface:8s} {gait:4s} sliced {len(steps):2d} kept {len(files):2d}  LUFS {i_lufs}', flush=True)
            (SOURCE / 'footstep-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    finally:
        city.SOURCE = keep


if __name__ == '__main__':
    main()
