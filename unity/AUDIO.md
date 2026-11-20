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
| Linn (re-voiced 20 Nov 2026, Carl's pick) | Ward / Hill | Seer Morganna | not stated | `7NsaqHdLuKNFvEfjpUno` | 4 |
| Brann | Ward / Salvage shop | Callum | American | `N2lVS1w4EtoT3dr4eOWO` | 15 |
| Warden Ossa | Outer Berms / West Gate post | Victoria | British | `N8SmJJ4vvs5Mz9VaT6u5` | 6 |
| Warden Rell | Outer Berms / Checkpoint | Roger | American | `CwhRBWXzGAHq8TQ4Fs17` | 2 |
| Tamsin (19 Nov 2026) | Ward / Field Supply | Evelyn | British | `XEoBW4iDmiawQP72xnAF` | 5 |

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

## NPC life: barks and the missing voices (19 November 2026)

Recorded by `art/showcase_20261119/npc_life/generate_voices.py` (same model `eleven_multilingual_v2`, voice settings,
request records and loudness mastering as `generate_npc_voices.py`; source of truth `barks.json` in that folder; full
take list with request ids and costs in `voice_manifest.json` there). Bound by the Editor installer
`NpcLifeInstall20261119` by asset path, never by hand-written references.

- **Dialogue takes:** Tamsin's five Field Supply nodes (new voice above); Warden Ossa's `locker`, `range` and `long_arm`
  nodes re-recorded in her existing voice with the current controls (the earlier takes named the pre-hotbar keys; they are
  kept in `staging/elevenlabs-audio/npc-voices/previous_20261119/`). Paths stay `NpcVoices/<npc>-<node>.wav`.
- **Barks:** 80 short lines outside dialogue, one `BarkSet` per speaker in `Assets/AthenHill/Data/Barks/`, clips in
  `Assets/AthenHill/Audio/ElevenLabs/NpcBarks/<speaker>-<line>.wav` (sources in `staging/elevenlabs-audio/npc-barks-20261119/`).
  The eight talking NPCs use the voices in the table above. Ambient walkers:

| Walker | Route | Voice | Accent | ElevenLabs voice ID | Barks |
| --- | --- | --- | --- | --- | ---: |
| Daro (Karaveen porter) | `npc_walker_01`, east avenue lane | Paul | British (subtle Northern) | `49TtX0KZLnuzDrAizTkN` | 4 |
| Sel (nanofab technician) | `npc_walker_02`, Quantum Tube goods node | Alice | British | `Xb7hH8MSUJpSbSDYk0k2` | 4 |
| Anso (hydroponics grower) | `npc_walker_03`, hall district | Will | American | `bIHbv24MWmeRgasZH58o` | 4 |

Bark playback: `BarkDirector` (on the GameSession object) plays one bark at a time through each speaker's own
positional `Bark voice` AudioSource on the Effects mixer group (Effects volume, Master mute), only during play; pause
freezes it and dialogue or any window stops it. Barks are captioned (Settings › Sound › Bark captions; PlayerPrefs
`AthenHill.Settings.v1.BarkCaptions`). Imports: mono Vorbis 0.85, compressed in memory (barks) or decompressed on load
(dialogue takes, as before).


## Combat audio: field rifle and droid identity (19 November 2026)

Not yet installed or heard; details, listening plan and rollback in
[art/showcase_20261119/combat_audio/README.md](../art/showcase_20261119/combat_audio/README.md).
`unity/tools/generate_combat_audio_20261119.py` (cached ElevenLabs `eleven_text_to_sound_v2` takes, numpy mastering,
`--generate` buys only missing takes; 511 credits) writes `Combat/Rifle/` and `Combat/Droids/`; sources and requests in
`staging/elevenlabs-audio/combat-20261119/`. Installer: `CombatAudioPass20261119.RunBatch --steps audio,weapon,droids,bolts,verify`.

| Set | Clips | Playback |
| --- | --- | --- |
| Field rifle (`PlayerCombat.weaponSounds`, `weapon_field_rifle`) | mech ×6 (≤0.15 s), body ×8 (≤0.30 s, +4 dB below 140 Hz), tail ×6 (≤0.75 s, HPF 180 Hz), empty/draw/holster ×2 | Layered like the pistol for a 0.18 s fire interval; tail ×0.75 inside a held burst; the pistol keeps its arrays |
| Scrap Reaper | alert, blade tell, chop ×2, death, heavy steps ×2 | Voice 3–70 m |
| Post Sentinel | alarm, targeting-beep tell, sentry shot ×2, death; procedural 4 s roll loop | Voice 3–90 m; roll loop 12–120 m, volume/pitch from ground speed |
| Feral Gunner | static alert, capacitor tell, rivet shot ×2, death | Voice 2.5–75 m |
| Feral Lancer | chirp alert, arc charge tell, launch ×2, death | Voice 2.5–80 m |
| Depot Foreman | klaxon, pneumatic tell, fist strike, layered ground slam, death, Reaper steps | Voice 4–90 m |
| Bolts | fly-by ×3, impact ×2, heavy lancer impact | 1.5–50 m |

All on the SFX group (the droid and bolt prefabs were on UI), custom desert rolloff silent at Max Distance, doppler
off. `VoiceLimiter.Droids` keeps alerts, tells, attacks and deaths and drops footsteps, clangs and impacts beyond 10
droid one-shots at once. Empty `FeralDroid.*Variants` arrays fall back to the shared clips (worker, scrap drone).
