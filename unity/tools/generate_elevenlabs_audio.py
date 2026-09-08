"""Generate the city audio once with ElevenLabs; cache originals outside Unity.

python3 unity/tools/generate_elevenlabs_audio.py --generate
Subsequent runs reuse paid generations. Omit --generate to only remaster cached audio.
Requires ffmpeg, ffprobe and numpy. The credential is read without sourcing .env.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request
import wave

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'unity/staging/elevenlabs-audio'
DEST = ROOT / 'unity/AthenHill/Assets/AthenHill/Audio/ElevenLabs'
RATE = 44100

# name, seconds, looping, prompt, target RMS dBFS, channels
SOUNDS = [
    ('desert-wind', 20, True, 'Steady gentle dry desert wind flowing through an open sandstone courtyard, fine sand brushing stone, distant airy gusts, quiet warm afternoon. Natural spacious ambience, no storms, no whistles, no voices, no music. Seamless continuous background loop.', -24, 2),
    ('market-murmur', 16, True, 'Distant sparse outdoor market on a quiet dusty science fiction colony, softly indistinct human conversation behind stalls, occasional subtle cloth and metal handling, calm open air, no understandable words, no close voices, no music, no footsteps in foreground. Seamless ambient loop.', -25, 1),
    ('lattice-hum', 8, True, 'Quiet futuristic data terminal idling: smooth airy electrical hum, delicate glassy digital shimmer, subtle pulsing resonance, calm cyan energy field. Continuous stable texture with no activation or ending, no alarms, no music, seamless loop.', -22, 1),
    ('ring-hum', 8, True, 'Large dormant stone science fiction portal with a deep soft resonant power hum, gently wavering low mechanical energy and faint dusty air. Stable continuous bass thrum, no impact, no melody, no alarm, no activation or ending. Seamless loop.', -22, 1),
    ('stone-step-01', .5, False, 'One single close dry boot footstep landing on sandstone paving, short firm heel impact and a tiny gritty scuff. Isolated game foley, one impact only, no ambience or echo.', -17, 1),
    ('stone-step-02', .5, False, 'A single worn leather boot stepping on pale stone tile, one muted compact footfall with a little sand grit, dry close foley, no repeated steps, no background.', -17, 1),
    ('stone-step-03', .5, False, 'One single firm rubber boot footfall on rough stone pavement, short low thud with a light gritty toe scrape. Dry isolated game foley, one step only, no background.', -17, 1),
    ('terminal-click', .5, False, 'One short subtle retro science fiction interface confirmation click: soft tactile tick with a tiny rounded electronic chirp. Crisp immediate attack, very short decay, unobtrusive, no reverb or background.', -20, 1),
    ('trade-confirm', .9, False, 'One brief warm science fiction trade accepted sound: soft mechanical token clink followed by two gentle ascending electronic notes, compact and satisfying, old computer terminal, no cash register, no background.', -20, 1),
    ('access-denied', .7, False, 'One short soft science fiction terminal unavailable indicator: two muted descending electronic blips and a dull relay tick. Gentle restrained error cue, not a loud alarm, dry isolated sound.', -22, 1),
    ('lattice-open', 2.5, False, 'A science fiction travel terminal opening a data tunnel: soft energy intake rises into an airy crystalline sweep and settles with a delicate electrical shimmer. Single compact activation, no explosion, no music, no voice.', -20, 1),
    ('lattice-link', 1.2, False, 'A science fiction data link established: one clear delicate crystalline ping with a warm low electronic pulse and a short shimmering tail. Pleasant restrained success cue, no voices, no background.', -20, 1),
]
MUSIC_PROMPT = ('Original instrumental ambient exploration music for a quiet dusty desert science fiction colony city at golden hour. '
    'An early 2000s computer role playing game atmosphere: warm analogue synth pads, sparse plucked oud-like strings, '
    'distant breathy flute textures, occasional very soft frame drum accents, spacious weathered sound. '
    'Unhurried, contemplative, a little mysterious but welcoming. Low intensity, no strong beat or big swells, '
    'no cinematic climax. A restrained repeating modal motif over a steady tonal drone, harmonious beginning and ending '
    'suitable for a looping background bed. Exactly 40 seconds. Instrumental only, no singing, no speech, no choir.')

# First-pass sources are retained. These revisions replace excessively bright takes.
REVISIONS = {
    'stone-step-02': 'One heavy boot footstep on a stone floor. A single low thud with a short gravelly scrape. Close dry foley, no background or electronic sounds.',
    'lattice-hum': 'Continuous low-pitched transformer hum with gentle mechanical vibration. Soft warm pulsing resonance at an idle futuristic terminal. No high-pitched whine, hiss or beeps. No music. Seamless loop.',
    'lattice-open': 'Soft low-pitched science fiction energy whoosh. One warm swelling bass pulse and a brief soft airy tail. Quiet teleport activation. No high-pitched tones, hiss or alarms. No music.',
}


def credential():
    # This project explicitly owns the credential; an inherited shell key may be stale.
    text = (ROOT / '.env').read_text() if (ROOT / '.env').exists() else ''
    entries = re.findall(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z_0-9]*)\s*=\s*(.+)$', text, re.M)
    for name, value in entries:
        if 'ELEVEN' in name.upper():
            return value.strip().strip('\"\'')
    if os.environ.get('ELEVENLABS_API_KEY'):
        return os.environ['ELEVENLABS_API_KEY']
    raise RuntimeError('No ElevenLabs credential found in project .env')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(name, body, music, allowed):
    source = SOURCE / (name + '.mp3')
    record_path = SOURCE / (name + '.json')
    if source.exists():
        if not record_path.exists() or json.loads(record_path.read_text())['request'] != body:
            raise RuntimeError(f'{name}: cached request differs; choose a new asset name')
        print('Reusing', name, flush=True)
        return source
    if not allowed:
        raise RuntimeError(f'{name}: no cached source; pass --generate to use ElevenLabs')
    key = credential()
    endpoint = '/v1/music' if music else '/v1/sound-generation'
    output_format = 'mp3_48000_128' if music else 'mp3_44100_128'
    req = urllib.request.Request('https://api.elevenlabs.io' + endpoint + '?output_format=' + output_format,
        data=json.dumps(body).encode(), headers={'xi-api-key': key, 'Content-Type': 'application/json'})
    print('Generating', name, flush=True)
    try:
        # No automatic retries: a timed-out paid request needs inspection before resubmission.
        with urllib.request.urlopen(req, timeout=300) as response:
            data = response.read()
            metadata = {k: response.headers.get(k) for k in ('request-id', 'history-item-id', 'song-id', 'character-cost') if response.headers.get(k)}
            content_type = response.headers.get('Content-Type', '')
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f'{name}: HTTP {exc.code}: ' + exc.read().decode()[:1200].replace(key, '[REDACTED]')) from None
    if len(data) < 1000 or 'json' in content_type:
        raise RuntimeError(f'{name}: API did not return audio')
    temp = source.with_suffix('.tmp.mp3')
    temp.write_bytes(data)
    subprocess.run(['ffprobe', '-v', 'error', str(temp)], check=True)
    temp.replace(source)
    record_path.write_text(json.dumps({'provider': 'ElevenLabs', 'endpoint': endpoint,
        'generated_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'request': body,
        'output_format': output_format, 'response': metadata, 'sha256': sha(source)}, indent=2) + '\n')
    return source


def master(source, loop, db, channels, music=False, output_name=None):
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(source), '-f', 'f32le',
        '-ar', str(RATE), '-ac', str(channels), '-'])
    samples = np.frombuffer(raw, dtype='<f4').reshape(-1, channels).copy()
    samples -= samples.mean(axis=0)
    if loop:
        # Overlap the tail into the head, then rotate the seam into continuous audio.
        # Linear complementary gains avoid a volume bump on correlated ambience.
        n = int((3.0 if music else .15) * RATE)
        ramp = np.linspace(0, 1, n, endpoint=False)[:, None]
        blend = samples[-n:] * (1-ramp) + samples[:n] * ramp
        samples = np.concatenate((samples[n:-n], blend))
    else:
        envelope = np.max(np.abs(samples), axis=1)
        active = np.flatnonzero(envelope > max(float(envelope.max()) * .015, .0002))
        if len(active):
            samples = samples[max(0, active[0]-int(.004*RATE)):min(len(samples), active[-1]+int(.05*RATE))]
        n = min(int(.004*RATE), len(samples)//4)
        samples[:n] *= np.linspace(0, 1, n)[:, None]
        n = min(int(.025*RATE), len(samples)//4)
        samples[-n:] *= np.linspace(1, 0, n)[:, None]
    rms = float(np.sqrt(np.mean(samples**2)))
    if rms < .00001:
        raise RuntimeError(f'{source.name}: silent generation')
    gain = min(10**(db/20)/rms, 10**(-3/20)/float(np.abs(samples).max()))
    samples *= gain
    output = DEST / ((output_name or source.stem) + '.wav')
    with wave.open(str(output), 'wb') as wav:
        wav.setnchannels(channels); wav.setsampwidth(2); wav.setframerate(RATE)
        wav.writeframes((np.clip(samples, -1, 1)*32767).astype('<i2').tobytes())
    return {'file': output.name, 'source': str(source.relative_to(ROOT)), 'source_sha256': sha(source),
        'sha256': sha(output), 'seconds': len(samples)/RATE, 'channels': channels, 'loop': loop,
        'rms_dbfs': 20*np.log10(float(np.sqrt(np.mean(samples**2)))),
        'peak_dbfs': 20*np.log10(float(np.abs(samples).max())),
        'seam_delta': float(np.max(np.abs(samples[0]-samples[-1]))) if loop else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate', action='store_true')
    args = parser.parse_args()
    SOURCE.mkdir(parents=True, exist_ok=True); DEST.mkdir(parents=True, exist_ok=True)
    manifest = {'provider': 'ElevenLabs', 'music_reference': 'https://elevenlabs.io/docs/api-reference/music/compose',
        'sfx_reference': 'https://elevenlabs.io/docs/api-reference/text-to-sound-effects/convert', 'assets': []}
    entries = [('hill-at-dusk', 40, True, MUSIC_PROMPT, -23, 2)] + SOUNDS
    for name, duration, loop, prompt, db, channels in entries:
        music = name == 'hill-at-dusk'
        prompt = REVISIONS.get(name, prompt)
        body = {'prompt': prompt, 'music_length_ms': int(duration*1000), 'force_instrumental': True, 'model_id': 'music_v2'} if music else {
            'text': prompt, 'duration_seconds': duration, 'loop': loop, 'prompt_influence': .45, 'model_id': 'eleven_text_to_sound_v2'}
        source = generate(name + '-warm-v2' if name in REVISIONS else name, body, music, args.generate)
        result = master(source, loop, db, channels, music, name)
        result.update(request=body)
        manifest['assets'].append(result)
        (SOURCE / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        print('Mastered', name, round(result['seconds'], 2), 'seconds', flush=True)
    print('Ready:', len(manifest['assets']), 'Unity audio assets', flush=True)


if __name__ == '__main__':
    main()
