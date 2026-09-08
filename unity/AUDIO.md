# Athen Hill audio

The native Unity scene uses two user-supplied music tracks and twelve original
ElevenLabs effects generated on 8 September 2026. All playback is local and offline. The API key stays in the ignored project
`.env`; it is never needed by Unity or included in a player build.

| Audio | Playback |
| --- | --- |
| Dust of the Giants / Dust of Alshain | Supplied MP3s; alternate with three-second crossfades in the Music group |
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
mute silences the output. Open **Esc → Settings → Sound** for independent Master,
Music, Ambience and Effects volumes. These preserve the authored source balance.
Effects controls both SFX and UI. Settings pauses gameplay while playing audio for
preview; the ordinary Pause menu stops music and ambience. Values are saved locally.

Select **City Audio** to edit cue references, footstep cadence, fade time and
ducking. Select its AudioSources to adjust individual levels. **Audio/City.mixer**
has independent Music, Ambience, SFX and UI groups. The Lattice and Ring sources
are attached to their interaction markers. Market murmur is a normal movable
AudioSource beside the vendor. No runtime city reconstruction is involved.

Music imports as streaming Vorbis; ambient loops use compressed Vorbis in memory;
short effects use PCM with Decompress On Load. The supplied MP3s are preserved
unchanged in `Assets/AthenHill/Audio/Music`; Unity imports stereo streaming clips.
Generated effect masters are 44.1 kHz WAV with level-balanced gain and 150 ms
overlap on ambience loops. CityAudio keeps the playlist on two sources for crossfade.

## Supplied music

The user supplied both tracks on 8 September 2026. No artist or licensing metadata
was inferred. SHA-256 hashes match the supplied files:

- Dust of the Giants: `f764365b2d2bdf63b704dab39236ff6f0f313d86c642b02e61397011ac9ae14d`
- Dust of Alshain: `ca594636d1379d54033cef9d278eb68d990e36ad43357c31d763f45bc2eca043`

Use **Athen Hill → Audio → Apply supplied city music** to restore scene playlist
references. `SettingsAudioPass.ApplyAndBuild` imports the tracks and builds both
Linux players. The former Hill at Dusk source remains as an unused historical
production asset. The old ElevenLabs pass can intentionally restore that soundscape.

## Historical generation and effect provenance

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
