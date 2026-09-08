# Athen Hill audio

The native Unity scene uses 13 original ElevenLabs assets generated on 8 September
2026. All playback is local and offline. The API key stays in the ignored project
`.env`; it is never needed by Unity or included in a player build.

| Audio | Playback |
| --- | --- |
| Hill at Dusk | 40-second instrumental, edited to a 37.03-second loop; Music group |
| Desert wind | Stereo continuous ambience |
| Market murmur | Positional ambience beside Basic General |
| Lattice hum / Ring hum | Separate positional loops at the travel devices |
| Stone steps 01–03 | Alternating clips at walk/run distance cadence, slight pitch variation |
| Terminal click | Opening/closing panels |
| Trade confirmation | Each successful buy or sell |
| Access denied | Offline Ring Gate, failed interaction/trade |
| Lattice open / link | Opening the tunnel and selecting a destination |

Music fades in over three seconds, softens to 65% during dialogue/shopping and
40% during Lattice travel, then returns smoothly. Pause stops the audio timeline;
mute silences the output. The existing pause UI controls both. UI feedback can
sound while paused; environmental audio and music remain paused.

Select **City Audio** to edit cue references, footstep cadence, fade time and
ducking. Select its AudioSources to adjust individual levels. **Audio/City.mixer**
has independent Music, Ambience, SFX and UI groups. The Lattice and Ring sources
are attached to their interaction markers. Market murmur is a normal movable
AudioSource beside the vendor. No runtime city reconstruction is involved.

Music imports as streaming Vorbis; ambient loops use compressed Vorbis in memory;
short effects use PCM with Decompress On Load. All masters are 44.1 kHz WAV, with
stereo music/wind and mono positional sounds. Clips are gain-balanced with at
least 3 dB peak headroom before source volume mixing. Loop tails overlap their
heads (three seconds for music, 150 ms for ambience) to avoid a silent restart.

## Generation and provenance

[ElevenLabs Music API](https://elevenlabs.io/docs/api-reference/music/compose)
generated the instrumental using `music_v2` with `force_instrumental: true`.
[ElevenLabs Sound Effects API](https://elevenlabs.io/docs/api-reference/text-to-sound-effects/convert)
generated the effects using `eleven_text_to_sound_v2`, with looping enabled for
ambient beds. No existing song, artist or game soundtrack was used as a reference.

`staging/elevenlabs-audio/` retains the original API audio, exact requests,
available response IDs, timestamps, hashes and the mastered-file measurements in
`manifest.json`. These files contain no credentials. The generated WAVs and their
Unity import settings live in `AthenHill/Assets/AthenHill/Audio/ElevenLabs/`.

From the repository root:

```sh
# Uses paid API generation only for missing source files; cached requests must match.
python3 unity/tools/generate_elevenlabs_audio.py --generate

# Re-edit cached audio without making API requests (requires numpy and ffmpeg).
python3 unity/tools/generate_elevenlabs_audio.py
```

To explicitly reapply these source assignments and defaults, use **Athen Hill →
Audio → Apply ElevenLabs soundscape** outside Play mode. This changes audio
components in the existing scene and preserves gameplay roots and geometry.
Normal tuning in the Inspector does not require reapplying this command.

## Native verification

```sh
uv run --with python-xlib python unity/tools/check_elevenlabs_audio.py
```

This launches the Linux development player with its audio routed into a temporary
dedicated PulseAudio sink (moving only its own FMOD stream), records the actual
game output, and checks music
wrapping, footsteps, market/device ambience, trade and travel cues, pause, mute
and restoration. It restores audio resources and exits its player afterwards.
Evidence is saved to `evidence/audio/20260908/`; the native `report.json` records
pass/fail, source state and captured RMS/peak levels.
