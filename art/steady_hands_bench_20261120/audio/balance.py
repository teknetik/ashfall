#!/usr/bin/env python3
"""Balance check for the bench audio (run after gen_sfx.py; writes manifest.json "balance").

1. Loudest simultaneous sets the bench can play (the loudest variant of each one-shot placed so all peaks line up, loops at
   their full level, the bed underneath), summed at unity gain: the aligned peak must stay under -1.5 dBFS. If a set
   goes over, the runtime bus gain that brings it back is recommended (the clips are not changed).
2. The test pulse against the game's scrap pistol shot (Combat/Pistol mech + body + tail at PlayerCombat's layer gains):
   the pulse must be at least 6 dB quieter in event loudness.
3. Spread of event loudness inside each one-shot group (variants should sit within about 1.5 dB)."""
import json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_sfx as g  # noqa: E402

UNITY = g.UNITY
MAN = json.loads((HERE / 'manifest.json').read_text())
EV = {e['id']: e for e in MAN['events']}
SETS = {
    'press (s4.press)': ['asm.amb.bed', 'asm.press.knit', 'asm.press.hiss', 'asm.press.pump', 'asm.press.lever'],
    'test card (s7.card_after)': ['asm.amb.bed', 'asm.pulse.shot', 'asm.pulse.hit', 'asm.ui.stage'],
    'fault at the screw (s1.screw_b)': ['asm.amb.bed', 'asm.screw.turn', 'asm.screw.camout', 'asm.ui.glint'],
    'quench and vent (s4.open)': ['asm.amb.bed', 'asm.press.vent', 'asm.quench.sizzle', 'asm.press.hiss'],
    'drill bind (s3.drill)': ['asm.amb.bed', 'asm.drill.turn', 'asm.drill.bind', 'asm.vise.creak'],
    'job done (s6.cell to s7)': ['asm.amb.bed', 'asm.ui.job', 'asm.latch.snap', 'asm.cell.power_up'],
    'shake after (s7.shake)': ['asm.amb.bed', 'asm.damper.settle', 'asm.damper.tick', 'asm.ui.stage'],
    'worst case: bed + three loudest loops + three loudest one-shots': None,
}


def clip(path):
    x = g.load(UNITY / path, 2) if 'amb-bed' in path else g.load(UNITY / path)
    return g.mono(x) if x.ndim == 2 else x


def loudest(eid):
    files = EV[eid]['files']
    return max((clip(f) for f in files), key=lambda x: np.abs(x).max()) if files else None


def aligned_peak(ids):
    loops = [i for i in ids if EV.get(i, {}).get('loop')]
    shots = [i for i in ids if i in EV and not EV[i]['loop']]
    n = int(3 * g.RATE); mix = np.zeros(n)
    for i in loops:
        x = loudest(i)
        if x is None: continue
        mix += np.resize(x, n)
    # put every one-shot's peak on the loop mix's own loudest sample (worst case)
    at = int(np.argmax(np.abs(mix))) if np.abs(mix).max() > 0 else n // 2
    sign = np.sign(mix[at]) or 1.0
    for i in shots:
        x = loudest(i)
        if x is None: continue
        p = int(np.argmax(np.abs(x))); x = x * (sign * np.sign(x[p]) or 1.0)
        s = at - p; a, b = max(0, s), min(n, s + len(x)); mix[a:b] += x[a - s:b - s]
    return g.peak_db(mix)


def main():
    out = {'sets': {}}
    loops = sorted([e for e in MAN['events'] if e['loop'] and e['files'] and e['id'] != 'asm.amb.bed'],
                   key=lambda e: -max(np.abs(clip(f)).max() for f in e['files']))[:3]
    shots = sorted([e for e in MAN['events'] if not e['loop'] and e['files']],
                   key=lambda e: -max(np.abs(clip(f)).max() for f in e['files']))[:3]
    worst_gain = 1.0
    for name, ids in SETS.items():
        ids = ids or ['asm.amb.bed'] + [e['id'] for e in loops] + [e['id'] for e in shots]
        p = aligned_peak(ids)
        out['sets'][name] = {'events': ids, 'aligned_peak_dbfs': round(p, 2), 'under_-1.5': bool(p < -1.5)}
        if p > -1.5: worst_gain = min(worst_gain, 10 ** ((-1.5 - p) / 20))
    out['recommended_bus_gain'] = round(worst_gain, 3)
    # pulse against the pistol
    pistol = g.ROOT / 'unity/AthenHill/Assets/AthenHill/Audio/ElevenLabs/Combat/Pistol'
    gains = {'mech': .548, 'body': .694, 'tail': .365}
    shots_p = []
    for k in range(1, 4):
        parts = [g.load(sorted(pistol.glob(f'pistol-{l}-*.wav'))[(k - 1) % len(sorted(pistol.glob(f'pistol-{l}-*.wav')))]) * gn for l, gn in gains.items()]
        n = max(len(p) for p in parts); shots_p.append(sum(np.pad(p, (0, n - len(p))) for p in parts))
    p_ev = float(np.mean([g.cmb.event_lufs(x) for x in shots_p]))
    q_ev = float(np.mean([g.cmb.event_lufs(clip(f)) for f in EV['asm.pulse.shot']['files']]))
    out['pulse_vs_pistol'] = {'pistol_shot_event_lufs': round(p_ev, 2), 'test_pulse_event_lufs': round(q_ev, 2),
                              'difference_db': round(p_ev - q_ev, 2), 'pulse_at_least_6_db_quieter': bool(p_ev - q_ev >= 6)}
    spread = {}
    for e in MAN['events']:
        if e['loop'] or len(e['files']) < 2: continue
        v = [t.get('measured_lufs') for t in e['takes'] if t.get('measured_lufs') is not None]
        if v: spread[e['id']] = round(max(v) - min(v), 2)
    out['variant_spread_db'] = {k: v for k, v in sorted(spread.items(), key=lambda kv: -kv[1])}
    MAN['balance'] = out
    (HERE / 'manifest.json').write_text(json.dumps(MAN, indent=1) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k != 'variant_spread_db'}, indent=1))
    print('largest variant spreads:', list(out['variant_spread_db'].items())[:8])


if __name__ == '__main__':
    main()
