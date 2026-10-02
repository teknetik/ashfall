"""Outer Berms combat one-shots through the same cached ElevenLabs pipeline as the city audio.

python3 unity/tools/generate_berms_combat_audio.py --generate
Sources and request records: unity/staging/elevenlabs-audio (reused on later runs).
Mastered WAVs: Assets/AthenHill/Audio/ElevenLabs/Combat. Manifest: combat-manifest.json beside the sources.
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import generate_elevenlabs_audio as city

city.DEST = city.DEST / 'Combat'
# name, seconds, prompt, target RMS dBFS
SOUNDS = [
    ('scrap-pistol-shot', .6, 'One single shot from a compact handmade science fiction energy pistol: sharp punchy electric crack with a short metallic mechanical clack and a brief fizzing discharge tail. Dry close game weapon sound, one shot only, no echo, no music.', -14),
    ('scrap-pistol-empty', .5, 'One dry mechanical trigger click on an empty handmade pistol with a tiny fading electrical fizzle. Short isolated game foley, no background.', -22),
    ('scrap-pistol-draw', .7, 'A metal pistol drawn from a leather holster: quick leather slide and a small mechanical charge-up whine settling. Short close foley, no background.', -22),
    ('droid-alert', .9, 'A rusty industrial robot detects an intruder: two harsh distorted electronic chirps with a servo whirr, menacing but brief. Isolated game sound, no music, no voice.', -18),
    ('droid-strike', .6, 'A heavy metal robot fist swings and slams: fast servo whoosh into a dull metallic impact thud. Single close game impact, no background.', -16),
    ('droid-hit', .5, 'An energy bolt hits scrap metal armour: sharp metallic clang with crackling sparks. Single short game impact, no echo.', -17),
    ('droid-death', 1.8, 'A damaged industrial robot shuts down and collapses: descending electronic power-down whine, sputtering sparks and a heavy clattering metal crash on sandy ground. Single event, no music.', -17),
    ('player-hurt', .5, 'A heavy dull body blow impact on a padded jacket with a short muffled thud and cloth rustle, no voice. Close game foley, single hit.', -18),
    ('target-clang', .7, 'A bullet hitting a hanging steel target plate: bright resonant metallic ping with a short ringing decay. Single hit, outdoor, no echo.', -17),
    # 27 Sep 2026 depot / robot pass (optional fifth field: seamless loop)
    ('cradle-hum', 6, 'Low steady electrical transformer hum from an old damaged industrial charging station outdoors: deep mains buzz with a faint unstable crackle. No music, no voices, no beeps. Seamless continuous loop.', -24, True),
    ('arc-crackle-1', .9, 'One short violent electrical arc from a broken power cell: sharp crackling zap with a sizzling spark burst. Single event, dry, no music.', -18),
    ('arc-crackle-2', 1.0, 'A shorting industrial lamp: brief buzzing electrical spark crackle ending with a small pop. Single event, dry, no music.', -20),
    ('droid-windup', .7, 'A heavy industrial robot winding up a punch: fast rising servo whine with a hydraulic hiss building tension, stops abruptly before any impact. Close game sound, no impact, no music.', -17),
    ('drone-windup', .6, 'A small hovering scrap drone revving to dive at a target: rotor buzz pitch rising quickly into a harsh electric whine. No impact, no music.', -17),
    ('droid-step-1', .5, 'One heavy metal robot foot stepping onto gravelly desert sand: dull metallic clank with a gritty crunch. Single step only, close dry foley, no background.', -20),
    ('droid-step-2', .5, 'A single heavy steel robot footfall on dusty rocky ground: low thud, small servo tick and a sandy scrape. One step only, dry, no background.', -20),
    ('drone-rotor', 3, 'A small rusty hovering drone with two rotors: steady buzzing propeller hum with a slight mechanical rattle, constant pitch. No music, no voices. Seamless continuous loop.', -22, True),
    # 2 Oct 2026 Outer Berms expansion: ranged droids (gunner, lancer) and their bolts
    ('gunner-aim', .9, 'A salvaged robot arm cannon charging to fire: quick rising electric whine with a crackling capacitor buzz and a short mechanical lock click at the end, no shot. Close game sound, no music.', -18),
    ('gunner-fire', .5, 'One shot from a heavy salvaged robot rivet gun firing a glowing energy bolt: sharp metallic thunk with a hissing electric crack and a brief fizz. Single shot, dry, no echo, no music.', -15),
    ('lancer-charge', 1.4, 'A flying gun drone charging a heavy arc cannon: deep electric hum rising steadily in pitch with crackling arcs, ending at a tense high whine, no shot. Game sound, no music.', -18),
    ('lancer-fire', .9, 'A heavy arc cannon on a drone discharging one bolt: deep punchy electric boom with a snapping crackle and a short descending zap tail. Single shot, no echo, no music.', -14),
    ('bolt-impact', .6, 'A glowing energy bolt hitting sand and rock: sharp sizzling crack with a small burst of grit and a short electric fizz. Single impact, outdoor, no echo, no music.', -17),
    ('bolt-flyby', .5, 'A fast energy bolt whizzing past the listener: brief electric hiss doppler whoosh from left to right with a crackle. Single flyby, no impact, no music.', -19),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate', action='store_true')
    args = parser.parse_args()
    city.SOURCE.mkdir(parents=True, exist_ok=True); city.DEST.mkdir(parents=True, exist_ok=True)
    manifest = {'provider': 'ElevenLabs', 'sfx_reference': 'https://elevenlabs.io/docs/api-reference/text-to-sound-effects/convert', 'assets': []}
    for name, seconds, prompt, db, *opt in SOUNDS:
        loop = bool(opt and opt[0])
        body = {'text': prompt, 'duration_seconds': seconds, 'loop': loop, 'prompt_influence': .5, 'model_id': 'eleven_text_to_sound_v2'}
        source = city.generate(name, body, False, args.generate)
        result = city.master(source, loop, db, 1, False, name)
        result.update(request=body); manifest['assets'].append(result)
        (city.SOURCE / 'combat-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        print('Mastered', name, round(result['seconds'], 2), flush=True)


if __name__ == '__main__':
    main()
