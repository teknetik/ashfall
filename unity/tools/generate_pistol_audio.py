"""Layered scrap/nano pistol sounds through the cached ElevenLabs pipeline (27 Sep 2026 character-feel pass).

python3 unity/tools/generate_pistol_audio.py --generate
Three layers, six variants each, combined at random at runtime by WeaponAudio (PlayerCombat):
  mech  - the actuator snap / slide: sharp close mechanical transient
  body  - the nano-charge discharge crack with a low thump (the "weight" of the shot)
  tail  - the outdoor desert slapback off the wall and berms (distant, no transient)
plus empty clicks, draw and holster foley. Sources/requests: unity/staging/elevenlabs-audio/pistol. Mastered WAVs:
Assets/AthenHill/Audio/ElevenLabs/Combat/Pistol. Manifest with levels: pistol-manifest.json beside the sources.
Levels: each layer is trimmed so the three sum to a punchy shot that peaks below -1 dBFS (checked in the manifest
with a worst-case sum of the loudest variants).
"""
import argparse, json, sys, wave
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import generate_elevenlabs_audio as city
import generate_footstep_audio as steps

SOURCE = city.SOURCE / 'pistol'
DEST = city.DEST / 'Combat/Pistol'
RATE = city.RATE
DRY = 'Isolated close game weapon sound effect, one single event only, no music, no voices, no background.'
LAYERS = {
    'mech': (.5, -18, [
        'A compact handmade pistol firing mechanism: one very sharp crisp metallic actuator snap and slide clack, extremely short and tight. ' + DRY,
        'One sharp steel slide cycling on a scrap-built pistol: tight bright metal click-clack, very short. ' + DRY,
        'A heavy spring-loaded firing pin and bolt snapping forward in a small metal pistol: one hard crisp mechanical clack. ' + DRY,
        'A rugged salvaged pistol hammer and actuator striking: one short sharp metallic snap with a tiny rattle. ' + DRY,
        'A small industrial energy pistol mechanism cycling: one crisp dense metal clack, short and punchy. ' + DRY,
        'One tight mechanical snap of a sci-fi pistol breech closing: hard, bright, very short. ' + DRY]),
    'body': (.7, -14, [
        'One powerful shot from a handmade science fiction nano-charge pistol: violent sharp electric crack with a deep low thump punch, short. ' + DRY,
        'A compact energy pistol discharging once: loud snapping plasma crack with a heavy low-frequency boom, very punchy and short. ' + DRY,
        'One shot of a scrap-built electromagnetic pistol: hard cracking discharge, sub bass thump and a brief electrical sizzle. ' + DRY,
        'A single nanite pulse pistol shot: sharp crackling bang with a chesty low thud, dry and powerful. ' + DRY,
        'One heavy sci-fi handgun shot: explosive electric snap layered with a deep punchy gunshot boom, no echo. ' + DRY,
        'A salvaged energy revolver firing one round: cracking arc discharge and a thick low punch, short. ' + DRY]),
    'tail': (1.6, -24, [
        'The distant echo tail of one gunshot in a wide open desert canyon: soft slapback reflection off a stone wall rolling away, no initial shot transient. No music.',
        'The outdoor reverb tail after a single pistol shot on a dry desert plain: low rumbling echo decaying across dunes, starts soft, no attack. No music.',
        'Slapback echo of one gunshot bouncing off a concrete wall and sandy berms outdoors: short double reflection and fading rumble, no initial bang. No music.',
        'A single faraway gunshot echo in a quiet desert outpost: soft rolling thunder-like decay, no sharp attack. No music.',
        'Desert outdoor gun report tail: gentle low echo rolling between rock walls and fading out, no transient at the start. No music.',
        'The fading reverberation of one shot in an open sandy basin with a fortified wall nearby: diffuse low echo, soft onset. No music.']),
}
EXTRA = [
    ('empty', .5, -24, ['One dry mechanical trigger click on a handmade pistol with no charge, tiny electrical fizzle. ' + DRY,
                         'A small metal pistol dry-fire click with a weak failing charge whine. ' + DRY,
                         'One empty trigger pull on a scrap pistol: light plastic and metal click. ' + DRY]),
    ('draw', .8, -22, ['A metal pistol drawn quickly from a leather holster: leather slide, a grip rattle and a small rising charge-up whine. ' + DRY,
                       'Drawing a compact handgun from a stiff canvas holster: fabric scrape, metal clack and a quiet electronic power-up hum. ' + DRY]),
    ('holster', .7, -23, ['A metal pistol pushed back into a leather holster: leather slide and soft thud, a small charge powering down. ' + DRY,
                          'Holstering a compact handgun in a canvas holster: fabric rustle and a soft snap button click. ' + DRY]),
]


# Per-layer loudness after the peak cap: transient-heavy takes come back up to 12 dB quieter in RMS than dense ones,
# which would make shots jump in level. A tanh soft-saturation drive (the usual gunshot "glue") is searched per file
# so every variant of a layer lands within 1 dB of its RMS target with the peak held at -3 dBFS.
GLUE_RMS = {'mech': -22, 'body': -16, 'tail': -24, 'empty': -24}


def glue(path, target):
    x = steps.load(path)
    peak = 10 ** (-3 / 20)
    def shaped(g):
        y = np.tanh(g * x / max(1e-9, np.abs(x).max()))
        return y / np.abs(y).max() * peak
    lo, hi = .5, 12.0
    plain = x / max(1e-9, np.abs(x).max()) * peak
    if steps.rms_db(plain) >= target:
        y = plain * 10 ** ((target - steps.rms_db(plain)) / 20)   # already dense: just level it, no saturation
    elif steps.rms_db(shaped(lo)) >= target:
        y = shaped(lo)
    else:
        for _ in range(30):
            mid = (lo + hi) / 2; y = shaped(mid)
            if steps.rms_db(y) < target: lo = mid
            else: hi = mid
        y = shaped(hi)
    steps.write(path, y)
    return round(steps.rms_db(y), 2), round(20 * np.log10(float(np.abs(y).max())), 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate', action='store_true')
    args = parser.parse_args()
    SOURCE.mkdir(parents=True, exist_ok=True); DEST.mkdir(parents=True, exist_ok=True)
    keep_src, keep_dest = city.SOURCE, city.DEST
    city.SOURCE, city.DEST = SOURCE, DEST
    manifest = {'provider': 'ElevenLabs', 'model': 'eleven_text_to_sound_v2', 'assets': []}
    try:
        groups = [(n, s, db, prompts) for n, (s, db, prompts) in LAYERS.items()] + EXTRA
        for name, seconds, db, prompts in groups:
            for i, text in enumerate(prompts):
                body = {'text': text, 'duration_seconds': seconds, 'loop': False, 'prompt_influence': .55, 'model_id': 'eleven_text_to_sound_v2'}
                asset = f'pistol-{name}-{i + 1:02d}'
                src = city.generate(asset, body, False, args.generate)
                result = city.master(src, False, db, 1, False, asset)
                if name in GLUE_RMS:
                    result['rms_dbfs'], result['peak_dbfs'] = glue(DEST / result['file'], GLUE_RMS[name])
                    result['sha256'] = city.sha(DEST / result['file']); result['glue_target_rms_dbfs'] = GLUE_RMS[name]
                result.update(layer=name, request=body); manifest['assets'].append(result)
                print(f"{asset:22s} {result['seconds']:.2f}s rms {result['rms_dbfs']:.1f} peak {result['peak_dbfs']:.1f}", flush=True)
                (SOURCE / 'pistol-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        # worst case: loudest mech + body + tail summed at the runtime default layer gains
        ratio = {'mech': .75, 'body': .95, 'tail': .5}
        def loud(layer):
            files = [a['file'] for a in manifest['assets'] if a['layer'] == layer]
            return max((steps.load(DEST / f) for f in files), key=lambda x: np.abs(x).max())
        parts = [loud(l) * g for l, g in ratio.items()]
        n = max(len(p) for p in parts); total = sum(np.pad(p, (0, n - len(p))) for p in parts)
        worst = 20 * np.log10(float(np.abs(total).max()))
        # scale the layer ratios so the worst-case aligned sum peaks at -1.5 dBFS (FP close mech x1.15 included)
        k = 10 ** ((-1.5 - worst - 20 * np.log10(1.15) * .5) / 20)
        gains = {l: round(g * k, 3) for l, g in ratio.items()}
        manifest['worst_case_sum_peak_dbfs_at_ratio'] = round(worst, 2)
        manifest['runtime_layer_gains'] = gains
        (SOURCE / 'pistol-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        print('worst-case summed peak at ratio', manifest['worst_case_sum_peak_dbfs_at_ratio'], 'dBFS; runtime gains', gains)
    finally:
        city.SOURCE, city.DEST = keep_src, keep_dest


if __name__ == '__main__':
    main()
