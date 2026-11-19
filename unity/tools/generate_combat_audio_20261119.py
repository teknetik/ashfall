"""Field rifle and droid identity sounds (19 Nov 2026 combat audio pass) through the cached ElevenLabs pipeline.

python3 unity/tools/generate_combat_audio_20261119.py --generate     # paid generation of missing takes only
python3 unity/tools/generate_combat_audio_20261119.py                # remaster cached takes, no API calls
python3 unity/tools/generate_combat_audio_20261119.py --procedural-only   # procedural layers and fallbacks only

Follows generate_pistol_audio.py: sources and exact requests in unity/staging/elevenlabs-audio/combat-20261119,
mastered 44.1 kHz mono WAVs in Assets/AthenHill/Audio/ElevenLabs/Combat/Rifle and Combat/Droids (new files only;
nothing under Combat/ that existed before is touched). Manifest with levels, recipes and credits:
combat-20261119-manifest.json beside the sources, copied to art/showcase_20261119/combat_audio/manifest.json.

Field rifle: layered like the pistol (mech + body + tail), designed for its 0.18 s fire interval (333 rounds/min,
WardCrafting.asset weapon_field_rifle; the stat floor is 0.08 s). Each layer is cut shorter than the pistol's so a
held burst does not pile up: mech <= 0.15 s, body <= 0.30 s, tail <= 0.75 s with a forced exponential decay and a
high-pass so overlapping tails stay clear instead of smearing into low-mid mud.
Droids: alert / attack tell / attack / death per kind (Reaper, Sentinel, Gunner, Lancer, Foreman) plus Reaper steps,
bolt fly-bys and impacts. The Sentinel's rolling loop is synthesised (seamless circular noise, no API).
Budget guard: a ledger of the response character-cost (credits) refuses any request that would take this pass past
BUDGET; nothing retries automatically.
"""
import argparse, json, shutil, subprocess, sys, wave
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import generate_elevenlabs_audio as city

ROOT = city.ROOT
SOURCE = city.SOURCE / 'combat-20261119'
RIFLE_DEST = city.DEST / 'Combat/Rifle'
DROID_DEST = city.DEST / 'Combat/Droids'
PISTOL_DEST = city.DEST / 'Combat/Pistol'
ART = ROOT / 'art/showcase_20261119/combat_audio'
RATE = city.RATE
BUDGET = 4000
DRY = 'Isolated close game sound effect, one single event only, no music, no voices, no background.'
NOMUSIC = 'No music, no speech.'

# name, seconds, prompt  (one entry per paid take)
RIFLE = {
    'mech': (.5, -21, [
        'A rugged salvaged automatic rifle bolt cycling once: one hard, very short, dense steel bolt clack with a tight spring snap, heavier and lower than a pistol. ' + DRY,
        'One heavy steel rifle bolt slamming home on a scrap-built automatic weapon: short solid metal chunk, very tight. ' + DRY,
        'A machine rifle action cycling once: hard compact steel clack and a brief rattle of a loose receiver plate, extremely short. ' + DRY,
        'A nanite-fed automatic rifle breech snapping shut: one dense mechanical thunk with a bright metal edge, very short. ' + DRY,
        'One sharp steel recoil spring and bolt carrier impact inside a heavy rifle: hard, short, dry clack. ' + DRY,
        'A battle rifle mechanism cycling once: a heavy, crisp metal clack with a tiny electrical tick, very short and tight. ' + DRY]),
    'body': (.6, -15, [
        'One shot of a heavy salvaged automatic nanite rifle: hard cracking electric discharge with a deep chest-thumping low boom, tight and short. ' + DRY,
        'A single shot from a science fiction assault rifle: punchy concussive crack with a heavy sub bass thump and a short electric snap. ' + DRY,
        'One round from an electromagnetic battle rifle: violent sharp crack, thick low punch and a brief metallic ring, short. ' + DRY,
        'A nano-charge rifle firing once: loud snapping discharge with a deep booming thud, dry and powerful, very short. ' + DRY,
        'One shot of a scrap-built heavy rifle: explosive cracking bang with a weighty low-end punch and a quick fizz, short. ' + DRY,
        'A single heavy energy rifle shot: deep punchy boom layered with a hard electric crack, tight with no echo. ' + DRY,
        'One automatic rifle shot fired outdoors close to the microphone: hard crack and a big low thump, extremely short decay. ' + DRY,
        'A salvaged coil rifle shot: sharp magnetic snap and a deep compressed thump, short, aggressive. ' + DRY]),
    'tail': (1.0, -25, [
        'The short outdoor echo of one rifle shot in a dry open desert: a quick tight slapback off a stone wall that dies away fast, no initial bang, no long rumble. ' + NOMUSIC,
        'A brief desert gunshot reflection: one crisp slap off nearby rocks and a fast fading crackle, no attack at the start. ' + NOMUSIC,
        'The tail of one rifle shot outdoors on hard sand: a short bright echo and a quick airy decay, no low rumble, no initial transient. ' + NOMUSIC,
        'Echo of one shot off a fortified concrete wall in an open basin: tight single reflection fading quickly, soft onset. ' + NOMUSIC,
        'A short outdoor gun report tail between rock walls: snappy reflection and fast decay, clean, no thunder. ' + NOMUSIC,
        'The quick reverberation after one rifle shot on a desert plain: dry crackling reflection that fades in under a second, soft start. ' + NOMUSIC]),
}
RIFLE_EXTRA = [
    ('empty', .5, -24, ['A heavy rifle trigger pulled with no charge: one dry steel click and a weak failing electric fizz. ' + DRY,
                        'An empty automatic rifle dry fire: a dull mechanical clack and a short dying whine. ' + DRY]),
    ('draw', .8, -22, ['Shouldering a heavy rifle off a canvas sling: strap rustle, steel rattle, a solid hand slap on the handguard and a short rising charge whine. ' + DRY,
                       'Raising a scrap-built rifle into the hands: fabric sling slide, metal clatter and a low electronic power-up hum. ' + DRY]),
    ('holster', .7, -23, ['Slinging a heavy rifle onto the back: canvas strap rustle, a soft metal knock and a charge powering down. ' + DRY,
                          'Lowering a heavy rifle onto a sling: fabric swish, a muted steel clunk and a short fading hum. ' + DRY]),
]
# Per-layer hard length (s) and decay: the rifle's fire interval is 0.18 s.
RIFLE_SHAPE = {'mech': (.15, .05), 'body': (.30, .11), 'tail': (.75, .22)}
# Gunshot "glue" RMS targets after the peak cap (generate_pistol_audio.GLUE_RMS: mech -22, body -16, tail -24).
RIFLE_GLUE = {'mech': -20, 'body': -15, 'tail': -26, 'empty': -24}
# Event loudness per layer (LUFS, event_lufs), so every variant of a layer sits within about 0.5 dB of the others.
RIFLE_LUFS = {'mech': -22, 'body': -16, 'tail': -23.5, 'empty': -25, 'draw': -21, 'holster': -23}

# droid sounds: asset, seconds, prompt, target event loudness (LUFS, event_lufs). Targets sit on the shared clip of the
# same role (droid-alert -15.7, droid-windup -15.6, gunner-aim -16.1, droid-strike -19.8, droid-death -15.2, droid-step-1
# -21.1, bolt-flyby -18.4, bolt-impact -30.7): heavies 0.5-3 dB above, tells never below -16.5 so they cut through a fight.
DROIDS = [
    # Scrap Reaper: level-3 heavy melee walker with a blade arm
    ('reaper-alert', 1.0, 'A huge heavy salvaged war robot spots its prey: a deep distorted mechanical growl through a broken loudspeaker, grinding hydraulic servos and a low metallic shriek, menacing and brief. ' + DRY, -15),
    ('reaper-windup', .8, 'A massive robot raising a long steel blade arm: slow heavy hydraulic groan rising into a sharp metallic scrape and a ringing blade, it stops before the swing, no impact. ' + DRY, -15.5),
    ('reaper-strike-1', .6, 'A massive robot swinging a heavy steel blade: deep fast whoosh into a brutal metal blade chop impact with a grinding scrape. ' + DRY, -17),
    ('reaper-strike-2', .6, 'A huge war robot slashing with a heavy cleaver arm: low whoosh and a hard metallic slicing clang. ' + DRY, -17),
    ('reaper-death', 2.0, 'A huge armoured war robot collapsing: deep failing hydraulic groan, servo motors winding down, a heavy grinding crash of thick steel plates onto rocky sand, last sparks. ' + NOMUSIC, -15),
    ('reaper-step-1', .5, 'One very heavy armoured robot foot slamming down on rocky desert ground: deep thud with a metallic clank and gravel crunch. One step only. ' + DRY, -20),
    ('reaper-step-2', .5, 'A single huge steel robot footfall on dusty gravel: low heavy boom, a hydraulic hiss and grit scatter. One step only. ' + DRY, -20),
    # Post Sentinel: wheeled, rolls on a split wheel, fires bolt bursts
    ('sentinel-alert', 1.0, 'A wheeled security robot sentry detects an intruder: a loud two-tone electronic warble alarm and a turret servo whirr, short and urgent. ' + DRY, -15.5),
    ('sentinel-aim', .9, 'A robot sentry gun acquiring a target: rapid rising targeting beeps accelerating, a turret servo and a hard lock click at the end, no shot. ' + DRY, -16),
    ('sentinel-fire-1', .5, 'One shot from a robot sentry bolt cannon: a sharp high electric snap with a metallic chug and a hissing discharge. ' + DRY, -18),
    ('sentinel-fire-2', .5, 'A sentry turret firing one energy bolt: crisp zapping crack and a mechanical cycling thunk. ' + DRY, -18),
    ('sentinel-death', 2.0, 'A wheeled robot sentry breaks down: its electric motor whines down, a wheel grinds and scrapes to a stop, the body topples over with a heavy metal crash and sputtering sparks. ' + NOMUSIC, -15.5),
    # Feral Gunner: salvaged walker with an arm cannon
    ('gunner-alert', .9, 'A rusty salvaged gunner robot spots a target: a harsh glitchy radio static burst and a mechanical gun-arm rack clack. ' + DRY, -16),
    ('gunner-tell', .9, 'A salvaged robot arm cannon charging: a quick stuttering capacitor whine with crackling, rising, ending in a sharp lock click, no shot. ' + DRY, -16),
    ('gunner-shot-1', .5, 'One shot from a salvaged robot rivet cannon firing a glowing bolt: hard metallic thunk with a short hissing electric crack. ' + DRY, -18.5),
    ('gunner-shot-2', .5, 'A scrap robot arm gun firing one hot bolt: compressed air punch, a clank and a fizzing crack. ' + DRY, -18.5),
    ('gunner-death', 1.8, 'A salvaged gunner robot shot down: an electric short pop, a stuttering power-down whine and a clattering metal fall onto sand. ' + NOMUSIC, -15.5),
    # Feral Lancer: hover drone with an arc cannon
    ('lancer-alert', .9, 'A flying gun drone spots a target: rotor pitch rising, a sharp electronic double chirp and a crackle of arcing electricity. ' + DRY, -16),
    ('lancer-tell', 1.4, 'A drone arc cannon charging: deep electric hum rising steeply in pitch with fizzing arcs, tense, ending at a high whine, no shot. ' + DRY, -16.5),
    ('lancer-launch-1', .8, 'A heavy arc cannon on a drone discharging one bolt: deep punchy electric thump with a snapping crackle and a fast descending zap. ' + DRY, -17),
    ('lancer-launch-2', .8, 'A drone lightning cannon firing one heavy bolt: booming electric crack and a sizzling falling whine. ' + DRY, -17),
    ('lancer-death', 1.8, 'A flying drone shot down: rotors sputtering and failing, an electric burst, a falling spinning whine and a metal crash onto sand. ' + NOMUSIC, -15.5),
    # Depot Foreman: elite industrial walker (slams)
    ('foreman-alert', 1.2, 'A huge industrial foreman robot detects intruders: a loud distorted factory klaxon blast and a heavy hydraulic hiss. ' + DRY, -15),
    ('foreman-windup', .9, 'A huge industrial robot drawing back a heavy hydraulic fist: deep pneumatic pressure build and groaning steel, stops before any impact. ' + DRY, -15.5),
    ('foreman-strike', .7, 'A huge industrial robot hydraulic fist punch: heavy whoosh into a deep metal slam impact. ' + DRY, -16.5),
    # first slam take (foreman-slam, 14 credits) was 98 % below 150 Hz, a sub boom with no clang: rejected, source kept
    ('foreman-slam-b', 1.4, 'A giant robot smashing both steel fists into rocky ground: a sharp heavy metal clang on impact, a deep boom underneath, then gravel and stones scattering and rattling down. ' + NOMUSIC, -14.5),
    ('foreman-death', 2.5, 'A giant industrial foreman robot dying: a klaxon distorting and dying, pressure venting hiss, heavy machinery seizing and a huge metal crash. ' + NOMUSIC, -14.5),
    # bolts
    ('bolt-flyby-1', .5, 'A glowing energy bolt zipping past close to the listener: short electric hiss doppler whoosh with crackle, no impact. ' + DRY, -18.5),
    ('bolt-flyby-2', .5, 'A plasma bolt snapping past very close: fast sizzling whizz from left to right, no impact. ' + DRY, -18.5),
    # bolt-flyby-3 (5 credits) came back as a low whoosh (87 % below 150 Hz): rejected, source kept
    ('bolt-flyby-4', .5, 'A small bright energy bolt whizzing past the ear: high sizzling electric zip with a quick pitch drop, airy and thin, no impact, no low rumble. ' + DRY, -18.5),
    ('bolt-impact-1', .6, 'A glowing energy bolt hitting rocky sand: sharp sizzling electric crack with a burst of grit. Outdoor, no echo. ' + DRY, -24),
    ('bolt-impact-2', .6, 'An energy bolt striking stone: hard zap, spark crackle and pebbles scattering. Outdoor, no echo. ' + DRY, -24),
    ('lancer-impact', .8, 'A heavy arc cannon bolt exploding on rock: deep electric thump, crackling arc discharge and scattering grit. Outdoor. ' + DRY, -21),
]


def load(path):
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'f32le', '-ar', str(RATE), '-ac', '1', '-'])
    x = np.frombuffer(raw, dtype='<f4').copy(); x -= x.mean(); return x


def write(path, s):
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes((np.clip(s, -1, 1) * 32767).astype('<i2').tobytes())


def rms_db(s): return 20 * np.log10(max(1e-9, float(np.sqrt(np.mean(s ** 2)))))
def peak_db(s): return 20 * np.log10(max(1e-9, float(np.abs(s).max())))


def lufs(samples):
    """EBU R128 integrated loudness and true peak through ffmpeg's ebur128 (needs >= 0.4 s of audio)."""
    tmp = SOURCE / '_measure.wav'; write(tmp, samples)
    try:
        out = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(tmp), '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    finally:
        tmp.unlink()
    summary = out[out.rfind('Summary:'):]
    val = lambda key: float(summary.split(key)[1].split()[0]) if key in summary else None
    return val('I:'), val('Peak:')


def event_lufs(x):
    """Loudness of a short one-shot as heard: four repeats with 0.5 s gaps (a lone 0.2 s click is below the R128
    400 ms gate). Comparable between files, which is what the balance needs."""
    gap = np.zeros(int(.5 * RATE))
    return lufs(np.concatenate([np.concatenate([x, gap]) for _ in range(4)]))[0]


def spectral(x, gain_fn):
    """Zero-phase FFT filter: gain_fn(freqs) -> linear gain."""
    n = 1 << int(np.ceil(np.log2(len(x) * 2)))
    spec = np.fft.rfft(x, n); f = np.fft.rfftfreq(n, 1 / RATE)
    return np.fft.irfft(spec * gain_fn(f), n)[:len(x)]


def highpass(f, cut, order=2): return 1 / np.sqrt(1 + (cut / np.maximum(f, 1e-3)) ** (2 * order))
def lowpass(f, cut, order=2): return 1 / np.sqrt(1 + (f / cut) ** (2 * order))
def low_shelf(f, cut, db): return 1 + (10 ** (db / 20) - 1) * lowpass(f, cut, 2)


def shape(x, limit, tau, fade_in=.002):
    """Hard length with an exponential decay past the first 15 ms, so the layer cannot ring into the next shot."""
    x = x[:int(limit * RATE)].copy()
    t = np.arange(len(x)) / RATE
    x *= np.where(t < .015, 1, np.exp(-(t - .015) / tau))
    n = max(1, int(fade_in * RATE)); x[:n] *= np.linspace(0, 1, n)
    n = min(int(.012 * RATE), len(x) // 4); x[-n:] *= np.linspace(1, 0, n)
    return x


def glue(x, target):
    """generate_pistol_audio.glue: tanh soft saturation searched per file so every variant of a layer lands on its RMS
    target with the peak at -3 dBFS."""
    peak = 10 ** (-3 / 20)
    def shaped(g):
        y = np.tanh(g * x / max(1e-9, np.abs(x).max())); return y / np.abs(y).max() * peak
    plain = x / max(1e-9, np.abs(x).max()) * peak
    if rms_db(plain) >= target: return plain * 10 ** ((target - rms_db(plain)) / 20)
    lo, hi = .5, 12.0
    if rms_db(shaped(lo)) >= target: return shaped(lo)
    for _ in range(30):
        mid = (lo + hi) / 2
        if rms_db(shaped(mid)) < target: lo = mid
        else: hi = mid
    return shaped(hi)


def trim(x, floor=.015):
    env = np.abs(x); act = np.flatnonzero(env > max(float(env.max()) * floor, .0002))
    if len(act): x = x[max(0, act[0] - int(.003 * RATE)):min(len(x), act[-1] + int(.04 * RATE))]
    n = min(int(.003 * RATE), len(x) // 4); x[:n] *= np.linspace(0, 1, n)
    n = min(int(.025 * RATE), len(x) // 4); x[-n:] *= np.linspace(1, 0, n)
    return x


def level(x, target_rms, peak_cap=-3):
    g = min(10 ** (target_rms / 20) / max(1e-9, float(np.sqrt(np.mean(x ** 2)))), 10 ** (peak_cap / 20) / max(1e-9, float(np.abs(x).max())))
    return x * g


def fit_lufs(x, target, cap=-3):
    """Gain to an event loudness target; where that pushes the peak past the cap, a tanh limiter takes the excess
    (transient takes come back up to 12 dB apart in loudness at the same peak, so plain peak normalising cannot
    level them)."""
    c = 10 ** (cap / 20)
    # at most 6 dB into the limiter in total: a bass-heavy take (K-weighting discounts it) would otherwise be squashed
    # into a square wave; it then lands under its target, which the manifest shows
    most = 2 * c / max(1e-9, float(np.abs(x).max()))
    limit = lambda g: (lambda y: c * np.tanh(y / c) if np.abs(y).max() > c else y)(x * g)
    g = 1.0
    for _ in range(5):
        g = min(most, g * 10 ** ((target - event_lufs(limit(g))) / 20))
    x = limit(g)
    return x


# ------------------------------------------------------------------ procedural
def roll_loop(seconds=4.0, seed=7):
    """Post Sentinel rolling loop: wheel rumble (band-limited circular noise with a rotation bump), gravel crunch
    (sparse filtered grains) and a faint drive-motor whine. Every component is periodic in the loop length, so the
    seam is continuous; Unity scales pitch and volume with ground speed."""
    rng = np.random.default_rng(seed); n = int(seconds * RATE); t = np.arange(n) / RATE
    def circular_noise(lo, hi):
        spec = rng.normal(size=n // 2 + 1) + 1j * rng.normal(size=n // 2 + 1)
        f = np.fft.rfftfreq(n, 1 / RATE); spec *= highpass(f, lo, 2) * lowpass(f, hi, 2) / np.sqrt(np.maximum(f, 20))
        y = np.fft.irfft(spec, n); return y / np.abs(y).max()
    rumble = circular_noise(35, 220)
    bump = 1 + .35 * np.sin(2 * np.pi * 3 * t / seconds * 4)            # 3 wheel turns per second, integer cycles
    rumble *= bump
    grit = np.zeros(n)
    for _ in range(int(seconds * 55)):
        at = rng.integers(0, n); length = int(rng.uniform(.002, .009) * RATE)
        g = rng.normal(size=length) * np.exp(-np.arange(length) / (length / 3)) * rng.uniform(.2, 1)
        idx = (at + np.arange(length)) % n; grit[idx] += g
    grit = np.real(np.fft.irfft(np.fft.rfft(grit) * highpass(np.fft.rfftfreq(n, 1 / RATE), 900, 2) * lowpass(np.fft.rfftfreq(n, 1 / RATE), 5000, 2), n))
    grit /= max(1e-9, np.abs(grit).max())
    f0 = round(118 * seconds) / seconds                                     # whole cycles in the loop
    whine = sum(np.sin(2 * np.pi * f0 * k * t + .3 * np.sin(2 * np.pi * t / seconds * 2)) / k ** 1.4 for k in (1, 2, 3, 5))
    whine /= np.abs(whine).max()
    y = rumble * .85 + grit * .28 + whine * .07
    y = level(y - y.mean(), -20, -4)
    # -20 LUFS, 2.4 dB over the scrap drone's rotor loop (-22.4): the runtime roll volume (0.34 idle to 0.85 at full
    # speed) takes it back down, and it has to carry 40-60 m across the bowl
    return y * 10 ** ((-20 - lufs(y)[0]) / 20)


def synth_click(seed, f=2600, decay=.012, body=.0, length=.12):
    """Procedural mechanical clack fallback: a noise transient through two resonances plus an optional low knock."""
    rng = np.random.default_rng(seed); n = int(length * RATE); t = np.arange(n) / RATE
    hit = rng.normal(size=n) * np.exp(-t / .0015)
    ring = np.sin(2 * np.pi * f * t) * np.exp(-t / decay) + .6 * np.sin(2 * np.pi * f * 1.73 * t) * np.exp(-t / (decay * .6))
    knock = body * np.sin(2 * np.pi * 140 * t) * np.exp(-t / .02)
    return level(hit * .5 + ring + knock, -20)


# ------------------------------------------------------------------ ledger and generation
def ledger():
    """Credits charged to this pass, from the response character-cost of every take recorded in SOURCE."""
    total = 0
    for rec in SOURCE.glob('*.json'):
        if rec.name.endswith('manifest.json'): continue
        r = json.loads(rec.read_text()).get('response', {})
        total += int(r.get('character-cost', 0) or 0)
    return total


def take(asset, seconds, prompt, allowed, influence=.55):
    body = {'text': prompt, 'duration_seconds': seconds, 'loop': False, 'prompt_influence': influence, 'model_id': 'eleven_text_to_sound_v2'}
    if not (SOURCE / (asset + '.mp3')).exists() and allowed:
        spent = ledger()
        # character-cost per take has been 10 per requested second for this model; refuse before crossing the budget
        if spent + seconds * 10 * 1.5 > BUDGET:
            raise RuntimeError(f'budget: {spent} credits spent, {asset} would pass {BUDGET}')
    keep = city.SOURCE
    city.SOURCE = SOURCE
    try:
        return city.generate(asset, body, False, allowed), body
    finally:
        city.SOURCE = keep


def credits_of(asset):
    p = SOURCE / (asset + '.json')
    return int(json.loads(p.read_text()).get('response', {}).get('character-cost', 0) or 0) if p.exists() else 0


def describe(path, x, extra):
    d = {'file': str(path.relative_to(ROOT / 'unity/AthenHill')), 'seconds': round(len(x) / RATE, 3),
         'peak_dbfs': round(peak_db(x), 2), 'rms_dbfs': round(rms_db(x), 2), 'event_lufs': round(event_lufs(x), 2), 'sha256': city.sha(path)}
    d.update(extra); return d


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate', action='store_true')
    parser.add_argument('--procedural-only', action='store_true')
    parser.add_argument('--only', help='comma separated asset name prefixes (e.g. rifle,sentinel)')
    args = parser.parse_args()
    for d in (SOURCE, RIFLE_DEST, DROID_DEST, ART): d.mkdir(parents=True, exist_ok=True)
    only = args.only.split(',') if args.only else None
    want = lambda name: not only or any(name.startswith(o) for o in only)
    manifest = {'pass': 'combat audio 19 Nov 2026', 'provider': 'ElevenLabs', 'model': 'eleven_text_to_sound_v2',
                'sfx_reference': 'https://elevenlabs.io/docs/api-reference/text-to-sound-effects/convert', 'assets': [], 'missing': []}
    old = SOURCE / 'combat-20261119-manifest.json'
    if old.exists() and only:   # keep entries of groups not regenerated this run
        prev = json.loads(old.read_text()); manifest['assets'] = [a for a in prev['assets'] if not want(Path(a['file']).stem)]

    def paid(asset, seconds, prompt):
        if args.procedural_only: raise RuntimeError('procedural only')
        return take(asset, seconds, prompt, args.generate)

    # ---- rifle
    groups = [(n, s, db, p) for n, (s, db, p) in RIFLE.items()] + RIFLE_EXTRA
    for layer, seconds, db, prompts in groups:
        for i, prompt in enumerate(prompts):
            asset = f'rifle-{layer}-{i + 1:02d}'
            if not want(asset): continue
            out = RIFLE_DEST / (asset + '.wav')
            try:
                src, body = paid(asset, seconds, prompt)
                x = trim(load(src))
                recipe = 'ElevenLabs take, trimmed'
                if layer in RIFLE_SHAPE:
                    limit, tau = RIFLE_SHAPE[layer]
                    if layer == 'body': x = spectral(x, lambda f: low_shelf(f, 140, 4) * highpass(f, 32, 2)); recipe += ', +4 dB low shelf at 140 Hz, HPF 32 Hz'
                    if layer == 'tail': x = spectral(x, lambda f: highpass(f, 180, 2) * lowpass(f, 9000, 1)); recipe += ', HPF 180 Hz (no low-mid build-up), LPF 9 kHz'
                    if layer == 'mech': x = spectral(x, lambda f: highpass(f, 400, 2)); recipe += ', HPF 400 Hz (the body carries the low end)'
                    x = shape(x, limit, tau, .008 if layer == 'tail' else .001); recipe += f', cut at {limit} s with exp decay tau {tau} s'
                x = glue(x, RIFLE_GLUE[layer]) if layer in RIFLE_GLUE else level(x, db)
                recipe += f", glue to {RIFLE_GLUE[layer]} dBFS RMS / -3 dBFS peak" if layer in RIFLE_GLUE else f', levelled to {db} dBFS RMS'
                # glue evens RMS, not loudness: variants still came out 5 dB apart, so finish on the layer's event loudness
                x = fit_lufs(x, RIFLE_LUFS[layer]); recipe += f', fitted to {RIFLE_LUFS[layer]} LUFS event loudness'
                write(out, x)
                manifest['assets'].append(describe(out, x, {'group': 'rifle', 'layer': layer, 'source': 'elevenlabs', 'request': body, 'recipe': recipe, 'credits': credits_of(asset)}))
            except RuntimeError as e:
                if layer == 'mech':   # the mechanical layer has a procedural fallback
                    x = synth_click(i + 11, f=2300 + 180 * i, decay=.008 + .002 * i, body=.35, length=.13); x = shape(x, .13, .04)
                    write(out, x)
                    manifest['assets'].append(describe(out, x, {'group': 'rifle', 'layer': layer, 'source': 'procedural', 'recipe': f'synth_click(seed {i + 11}) fallback: {e}', 'credits': 0}))
                else:
                    manifest['missing'].append({'asset': asset, 'reason': str(e)})
            print(f'{asset:22s} done', flush=True)
            old.write_text(json.dumps(manifest, indent=2) + '\n')

    # ---- droids and bolts
    for asset, seconds, prompt, db in DROIDS:
        if not want(asset): continue
        out = DROID_DEST / (asset + '.wav')
        try:
            src, body = paid(asset, seconds, prompt)
            x = fit_lufs(trim(load(src)), db)
            write(out, x)
            manifest['assets'].append(describe(out, x, {'group': asset.split('-')[0], 'source': 'elevenlabs', 'request': body, 'recipe': f'ElevenLabs take, trimmed, fitted to {db} LUFS event loudness, -3 dBFS soft peak cap', 'credits': credits_of(asset)}))
        except RuntimeError as e:
            manifest['missing'].append({'asset': asset, 'reason': str(e)})
        print(f'{asset:22s} done', flush=True)
        old.write_text(json.dumps(manifest, indent=2) + '\n')

    if want('foreman-slam') and (DROID_DEST / 'foreman-slam-b.wav').exists() and (DROID_DEST / 'foreman-strike.wav').exists():
        # Both slam takes were almost all sub (96-98 % below 150 Hz) and vanish on small speakers: the slam is built from
        # the second take's boom, the Foreman's own strike clang high-passed above 300 Hz on top, and a procedural
        # gravel scatter falling away over 0.7 s.
        boom = load(DROID_DEST / 'foreman-slam-b.wav')
        clang = spectral(load(DROID_DEST / 'foreman-strike.wav'), lambda f: highpass(f, 300, 2))
        rng = np.random.default_rng(23); n = len(boom); grit = np.zeros(n + int(.8 * RATE))
        for _ in range(140):
            at = int(abs(rng.normal(.12, .22)) * RATE); length = int(rng.uniform(.002, .012) * RATE)
            if at + length >= len(grit): continue
            grit[at:at + length] += rng.normal(size=length) * np.exp(-np.arange(length) / (length / 3)) * rng.uniform(.1, 1) * np.exp(-at / RATE / .35)
        grit = spectral(grit, lambda f: highpass(f, 1000, 2) * lowpass(f, 6500, 2)); grit /= max(1e-9, np.abs(grit).max())
        n = max(len(boom), len(clang), len(grit)); pad = lambda y: np.pad(y, (0, n - len(y)))
        x = .6 * pad(boom / np.abs(boom).max()) + pad(clang / np.abs(clang).max()) + .25 * pad(grit)
        x = fit_lufs(trim(x), -14.5); out = DROID_DEST / 'foreman-slam.wav'; write(out, x)
        manifest['assets'] = [a for a in manifest['assets'] if Path(a['file']).name != out.name]
        manifest['assets'].append(describe(out, x, {'group': 'foreman', 'source': 'layered', 'credits': 0,
            'recipe': '0.6 x foreman-slam-b (boom) + foreman-strike HPF 300 Hz (clang) + 0.25 x procedural gravel (140 grains, 1-6.5 kHz, seed 23, tau 0.35 s), fitted to -14.5 LUFS'}))

    if want('sentinel-roll'):
        out = DROID_DEST / 'sentinel-roll-loop.wav'; x = roll_loop(); write(out, x)
        manifest['assets'].append(describe(out, x, {'group': 'sentinel', 'source': 'procedural', 'loop': True, 'seam_delta': float(abs(x[0] - x[-1])),
            'recipe': 'roll_loop(4 s, seed 7): circular noise 35-220 Hz with a 3 Hz wheel bump, 55 gravel grains/s band 0.9-5 kHz, 118 Hz drive whine (1,2,3,5 harmonics) at -23 dB; all periodic in 4 s', 'credits': 0}))

    manifest['balance'] = balance(manifest)
    manifest['credits_this_pass'] = ledger()
    old.write_text(json.dumps(manifest, indent=2) + '\n')
    shutil.copy(old, ART / 'manifest.json')
    print(json.dumps(manifest['balance'], indent=1))
    print('credits charged to this pass (response character-cost):', manifest['credits_this_pass'], '| missing:', len(manifest['missing']))


# ------------------------------------------------------------------ balance
PISTOL_GAINS = {'mech': .548, 'body': .694, 'tail': .365}      # PlayerCombat defaults (WeaponFeelPass)
RIFLE_INTERVAL = .18


def mixed_shot(files, gains, rng):
    parts = [load(f) * gains[l] for l, f in files]
    n = max(len(p) for p in parts); return sum(np.pad(p, (0, n - len(p))) for p in parts)


def burst(dest, prefix, gains, interval, shots, seed=3):
    """A burst as the game plays it: one random mech/body/tail per shot (no immediate repeat) at the fire interval."""
    rng = np.random.default_rng(seed)
    layers = {l: sorted(dest.glob(f'{prefix}-{l}-*.wav')) for l in gains}
    if not all(layers.values()): return None
    step = int(interval * RATE); out = np.zeros(step * shots + int(2 * RATE)); last = {}
    for s in range(shots):
        for l, g in gains.items():
            i = rng.integers(len(layers[l]))
            if len(layers[l]) > 1 and i == last.get(l): i = (i + 1) % len(layers[l])
            last[l] = i; x = load(layers[l][i]) * g; out[s * step:s * step + len(x)] += x
    return out


def balance(manifest):
    """Rifle runtime layer gains: a single rifle shot about 1.5 dB above a single pistol shot (event loudness), the
    held burst's short-term loudness reported against a pistol volley at its own fire rate, and the worst-case
    aligned peak of the loudest variants held under -1.5 dBFS (the same rule the pistol generator used)."""
    out = {}
    ps = burst(PISTOL_DEST, 'pistol', PISTOL_GAINS, .28, 1)
    rifle_ratio = {'mech': .55, 'body': .75, 'tail': .38}
    rs = burst(RIFLE_DEST, 'rifle', rifle_ratio, RIFLE_INTERVAL, 1)
    if ps is None or rs is None: return {'note': 'layers missing'}
    # average over several random single shots
    def avg_event(dest, prefix, gains):
        return float(np.mean([event_lufs(burst(dest, prefix, gains, 1, 1, seed=s)[:int(1.8 * RATE)]) for s in range(6)]))
    p_ev = avg_event(PISTOL_DEST, 'pistol', PISTOL_GAINS)
    r_ev = avg_event(RIFLE_DEST, 'rifle', rifle_ratio)
    k = 10 ** ((p_ev + 1.5 - r_ev) / 20)
    gains = {l: round(g * k, 3) for l, g in rifle_ratio.items()}
    # worst case: loudest variant of each layer summed, aligned
    worst = 0
    loud = {l: max(sorted(RIFLE_DEST.glob(f'rifle-{l}-*.wav')), key=lambda f: np.abs(load(f)).max()) for l in gains}
    worst = peak_db(mixed_shot([(l, loud[l]) for l in gains], gains, None))
    if worst > -1.5:
        s = 10 ** ((-1.5 - worst) / 20); gains = {l: round(g * s, 3) for l, g in gains.items()}; worst = -1.5
    pistol_volley = burst(PISTOL_DEST, 'pistol', PISTOL_GAINS, .28, 8)
    rifle_burst = burst(RIFLE_DEST, 'rifle', gains, RIFLE_INTERVAL, 12)
    out['pistol_single_shot_event_lufs'] = round(p_ev, 2)
    out['rifle_single_shot_event_lufs'] = round(avg_event(RIFLE_DEST, 'rifle', gains), 2)
    pv, pp = lufs(pistol_volley); rv, rp = lufs(rifle_burst)
    out['pistol_volley_8_at_0.28s'] = {'lufs': pv, 'true_peak_dbfs': pp}
    out['rifle_burst_12_at_0.18s'] = {'lufs': rv, 'true_peak_dbfs': rp}
    out['rifle_worst_case_aligned_peak_dbfs'] = round(worst, 2)
    out['rifle_runtime_layer_gains'] = gains
    out['pistol_runtime_layer_gains'] = PISTOL_GAINS
    # tail overlap at the fire rate: how many tails ring at once
    tails = sorted(RIFLE_DEST.glob('rifle-tail-*.wav'))
    if tails: out['rifle_tail_max_seconds'] = round(max(len(load(t)) for t in tails) / RATE, 3); out['rifle_tails_overlapping_at_0.18s'] = int(np.ceil(out['rifle_tail_max_seconds'] / RIFLE_INTERVAL))
    # droid roles against the shared set they replace (event loudness)
    shared = {f.stem: f for f in (city.DEST / 'Combat').glob('*.wav')}
    def ev(path): return round(event_lufs(load(path)), 2)
    roles = {'alert': 'droid-alert', 'windup': 'droid-windup', 'tell': 'gunner-aim', 'aim': 'gunner-aim', 'strike': 'droid-strike', 'slam': 'droid-strike',
             'death': 'droid-death', 'step': 'droid-step-1', 'fire': 'gunner-fire', 'shot': 'gunner-fire', 'launch': 'lancer-fire', 'flyby': 'bolt-flyby', 'impact': 'bolt-impact'}
    rows = {}
    for a in manifest['assets']:
        stem = Path(a['file']).stem
        if stem.startswith('rifle') or 'roll' in stem: continue
        role = next((r for r in roles if f'-{r}' in stem), None)
        ref = 'lancer-charge' if stem.startswith('lancer') and role == 'tell' else roles.get(role)
        if role and ref in shared: rows[stem] = {'event_lufs': a['event_lufs'], 'replaces_or_sits_beside': ref, 'shared_event_lufs': ev(shared[ref])}
    rows['sentinel-roll-loop (continuous)'] = {'lufs': lufs(load(DROID_DEST / 'sentinel-roll-loop.wav'))[0], 'replaces_or_sits_beside': 'drone-rotor', 'shared_lufs': lufs(load(shared['drone-rotor']))[0]} if 'drone-rotor' in shared and (DROID_DEST / 'sentinel-roll-loop.wav').exists() else None
    out['droids_vs_shared'] = rows
    return out


if __name__ == '__main__':
    main()
