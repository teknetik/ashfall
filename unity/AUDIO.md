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

## Next-level pass, 2 October 2026 (music default and trade click)

- **Oasis of Ruins** (`Assets/AthenHill/Audio/Music/Oasis of Ruins.mp3`, 4:00, 48 kHz stereo, −14.5 LUFS integrated,
  supplied by the user in `meshy/incoming-20261002/`, SHA-256
  `4be69277940897315696d22d6fff6c3467ac39879972c5d2ae6bd08b83385dfc`, same streaming Vorbis import as the 8 Sep tracks)
  is the **first** entry of `CityAudio.musicPlaylist`, followed by Dust of the Giants and Dust of Alshain. `CityAudio`
  starts `musicPlaylist[0]` on every scene load (new game and Continue alike; the track index is not saved) and
  advances in playlist order with the three-second crossfade, so the new track always plays first.
- **Trade click**: `CityAudio.tradeConfirm` now plays `Assets/AthenHill/Audio/UI/trade-click.wav` on
  `CitySoundCue.Trade` (buy and sell). Carl found the ElevenLabs confirmation "like a bell or hitting an empty can";
  the replacement is a 34 ms synthesized digital click (`art/next_level_20261002/combat/make_trade_click.py`, numpy,
  deterministic: a 1.2 ms transient through a 2.6 kHz resonance plus a soft 1.9 kHz blip at −14 dB), peak −14 dBFS,
  imported without normalization so it stays quiet. The old `ElevenLabs/trade-confirm.wav` stays in the project for
  rollback (`CombatNextLevelPass.Trade()` re-points the scene field; the Unavailable, Lattice and confirmation cues are
  unchanged).

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

## NPC dialogue voices (2 October 2026)

Seven named NPCs have 30 offline ElevenLabs dialogue takes. Each `NpcDefinition`
node keeps its original text and choices and now references its own AudioClip.
Opening or changing a node starts its clip at the NPC; leaving dialogue stops it.
The dialogue text remains visible if a clip is absent. Voice playback uses the
Effects mixer group and Effects volume; Master mute still applies. These clips do
not use the API at runtime.

| NPC | Area | Voice | Accent | ElevenLabs voice ID | Takes |
| --- | --- | --- | --- | --- | ---: |
| Mira | Ward / Basic General | Clara | British | `aj0fZfXTBc7E3By4X8L2` | 1 |
| Torr | Ward / Terminal court | Chris | American | `iP95p4xoKVk53GoZ742B` | 2 |
| Vex | Ward / West Gate | Charlie | Australian | `IKne3meq5aSn9XLyUdCD` | 2 |
| Linn | Ward / Hill | Amelia | British | `ZF6FPAbjXT4488VcRRnw` | 2 |
| Brann | Ward / Salvage shop | Callum | American | `N2lVS1w4EtoT3dr4eOWO` | 15 |
| Warden Ossa | Outer Berms / West Gate post | Victoria | British | `N8SmJJ4vvs5Mz9VaT6u5` | 6 |
| Warden Rell | Outer Berms / Checkpoint | Roger | American | `CwhRBWXzGAHq8TQ4Fs17` | 2 |

The source MP3s, exact requests, response IDs and checksums are in
`staging/elevenlabs-audio/npc-voices/`. The 44.1 kHz mono WAVs and Unity `.meta`
files are in `AthenHill/Assets/AthenHill/Audio/ElevenLabs/NpcVoices/`.
`unity/tools/generate_npc_voices.py --install` verifies cached takes and restores
references without API calls; `--generate` creates only missing takes. It refuses
to reuse a take after its text or voice assignment changes. The developer
console's NPC page reads the same roster from a local SQLite database seeded by
`unity/tools/devui/npc_roster.json`. New voice assignments require generating
new clips and updating the Unity node references before they affect the game.
Credit the generated performances as AI voices in the shipped game credits.

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
