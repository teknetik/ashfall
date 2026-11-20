# Linn's voice (20 November 2026)

Carl's playtest note: "Linns voice does not match, should be more older and rough". Linn (`npc_linn`, the elder on
the hill by the tree; she also leases the container home) spoke in **Amelia** (`ZF6FPAbjXT4488VcRRnw`, British,
assigned 2 Oct 2026), a bright younger voice (median pitch about 215 Hz on her takes).

**Now:** every line Linn speaks is in **Seer Morganna** (`7NsaqHdLuKNFvEfjpUno`), Carl's choice of three candidates
("B is the best I think", 20 Nov). Library entry: female, old, no accent given, "wise", characters and animation, "The
voice of an old wise seer woman telling people of their fortunes." Carl has heard only the two candidate lines
(`candidates/B-SeerMorganna-*.mp3`); those two takes (greet_shade, hill) are the ones installed. **Nobody else has
listened to anything here, and nobody has heard the other eleven takes.**

Cached alternatives (switching back is free, no API calls): Empress (`MHPwHxLx0nmGIb5Jnbly`, the first default,
candidate A) and Maria Moody (`wGcFBfKz5yUQqhqr0mVy`, candidate C, background hiss). All 13 lines are cached for both
under `takes/<voice id>/`.

## What changed

- 13 takes: her 4 dialogue nodes (`greeting`, `hill`, and the housing nodes `housing` and `housing_leased`, which had
  no take before and played silent) and her 9 barks. The 11 existing WAVs were replaced in place (same paths, `.meta`
  files and GUIDs); no scene, prefab, BarkSet or dialogue reference changed.
- The two new housing WAVs are bound to their nodes in `Data/npc_linn.asset` by the Editor pass
  `AthenHill.Editor.LinnVoicePass20261120` (`install`, `verify`, `rollback`). Unity re-serialised that asset with default
  empty fields (`entries: []`, empty `requires`/`setFlag`). The pass touches no scene object.
- Words are exactly as written. For the generator only: `Nanofab` is spoken from "nano-fab"; `Karaveen` from
  "Kah-rah-veen" for Seer Morganna (`voice.json`, per voice; "Carra-veen" for the others, which came back as "Caravan").
  Captions and dialogue text are unchanged.
- Records naming the voice: `unity/tools/devui/npc_roster.json` (Seer Morganna, 4 takes), `unity/tools/devui/test_devui.py`
  (voiced node total 36 to 38; passes), `unity/AUDIO.md` row, `art/showcase_20261119/npc_life/barks.json` (Linn's speaker
  voice), `Editor/NpcVoiceAudit.cs` (Linn 2 to 4 nodes: the audit had failed on Linn since the housing nodes came on
  5 Oct). The two older generators skip Linn (one-line guard each) so they cannot re-make her lines in Amelia:
  `unity/tools/generate_npc_voices.py`, `art/showcase_20261119/npc_life/generate_voices.py`.
- Native check for the orchestrator's batch: `unity/tools/check_linn_voice_native.py` (not run here).

## Settings

Model `eleven_multilingual_v2` (as every other colonist), output `mp3_44100_128`, stability 0.5, similarity_boost 0.8,
style 0.1, use_speaker_boost true, speed 0.92: the same settings that made the two candidate lines Carl approved (those
two takes are reused unchanged). Settings live in `voice.json`.

Mastering, matched to the other colonists' clips (PCM 16-bit, 44.1 kHz, mono, about -20 LUFS, peaks -2 dBFS or lower):
edges trimmed below -50 dB, two-pass `loudnorm` I=-20 TP=-2 LRA=7 (linear), one gain step towards -20 LUFS that never
lifts the peak over -2 dBFS, 8 ms fade-in, 30 ms fade-out, then 40 ms of digital silence in front. Seer Morganna's takes
start on breath and room tone (her noise floor is about 45 to 50 dB below peak, near Amelia's), which the -50 dB trim
does not remove, so the pad keeps the first syllable off the first sample. Dialogue clips import as Vorbis 0.85,
decompress on load; barks keep the NpcLife import (compressed in memory).

## Every line

Paths under `unity/AthenHill/Assets/AthenHill/Audio/ElevenLabs/`. Request ids, costs and checksums per take are in
`installed.json` and `takes/7NsaqHdLuKNFvEfjpUno/*.json`.

| Line | File | Words (caption) | Chars | Before: Amelia, LUFS / peak, s | Now: LUFS / peak, s | Words/s | Transcript |
| --- | --- | --- | ---: | --- | --- | ---: | --- |
| greeting | `NpcVoices/npc_linn-greeting.wav` | Looking for someone? Try the shade. Sooner or later everyone comes up here, even the people who swear they are too busy. | 120 | -19.4 / -2.2, 7.755 | -20.0 / -2.0, 11.515 | 1.91 | match |
| hill | `NpcVoices/npc_linn-hill.wav` | You can see the gate, hear the market, and get out of the dust. No terminal needs to explain that. If we get separated, meet me on the hill. | 140 | -20.8 / -2.0, 10.217 | -20.0 / -2.0, 11.133 | 2.6 | match |
| housing | `NpcVoices/npc_linn-housing.wav` | There is a rust-red container against the south wall, behind the Nanofab yard. The family who fitted it out went with a Karaveen caravan last season. Bunk, a steel locker, shelves, a window that shuts. Forty credits takes the lease off the roll and the key is yours. Keep the locker for your salvage; the Berms will fill your pack faster than you think. (spoken as: nano-fab, Kah-rah-veen) | 358 | no take | -20.0 / -2.0, 28.233 | 2.3 | heard: nanofab -> nano fab; karaveen -> caravene |
| housing_leased | `NpcVoices/npc_linn-housing_leased.wav` | Then it is yours. The door knows you now. Rest on the bunk when the Berms wear you down, and come back up the hill when you need someone to talk to. | 148 | no take | -19.9 / -2.0, 12.348 | 2.59 | match |
| greet_shade | `NpcBarks/npc_linn-greet_shade.wav` | Sit a while. The shade's free. | 30 | -20.8 / -2.0, 1.997 | -20.0 / -2.7, 3.02 | 1.99 | match |
| greet_evening | `NpcBarks/npc_linn-greet_evening.wav` | Evening. Best light on the hill, this. | 38 | -20.0 / -3.6, 2.554 | -19.9 / -2.9, 3.234 | 2.16 | match |
| idle_market | `NpcBarks/npc_linn-idle_market.wav` | You can hear the whole market from up here. | 43 | -20.0 / -4.8, 2.183 | -19.9 / -4.5, 2.342 | 3.84 | match |
| idle_tree | `NpcBarks/npc_linn-idle_tree.wav` | This tree was old when I was young. | 35 | -20.0 / -4.8, 1.95 | -19.9 / -7.2, 2.64 | 3.03 | match |
| idle_pumps | `NpcBarks/npc_linn-idle_pumps.wav` | Listen. You can hear the aquifer pumps at night. | 48 | -20.0 / -2.5, 2.879 | -20.0 / -2.0, 4.279 | 2.1 | match |
| weapon | `NpcBarks/npc_linn-weapon.wav` | Not on the hill, please. Put it away. | 37 | -20.0 / -4.7, 2.229 | -20.0 / -3.7, 3.218 | 2.49 | match |
| ack_primer | `NpcBarks/npc_linn-ack_primer.wav` | You came back from the Berms. I'm glad. | 39 | -20.0 / -2.3, 2.322 | -19.9 / -2.5, 3.225 | 2.48 | heard: berms -> bums |
| ack_home | `NpcBarks/npc_linn-ack_home.wav` | How's the container? Keep the window shut against the dust. | 59 | -19.5 / -3.8, 3.158 | -20.0 / -2.7, 3.704 | 2.7 | match |
| order_done | `NpcBarks/npc_linn-order_done.wav` | The Wardens talk about you now. Don't let it go to your head. | 61 | -19.9 / -2.0, 3.483 | -20.8 / -2.0, 4.505 | 2.89 | match |

**Transcripts** (ElevenLabs Scribe, `--stt`, no character cost; `unity/evidence/showcase_phase2/20261120/linn_voice/stt.json`):
11 of 13 match word for word; "nano fab" counts as a difference only because of the hyphen.
- `housing`: Karaveen is heard as "Caravene" (ending in "-veen") with the spelling "Kah-rah-veen". Earlier spellings came
  back as "Caravan", "camping", "Caribbean" and "Carabine"; the probes are in `probe/pron/`.
- `ack_primer`, "You came back from the Berms. I'm glad.": **still wrong**. Every take and probe in this voice is heard
  as "bums" or "bombs": two full takes and eight probes with Berms, Burms, Bermz, Burrms, Behrms, berms, BERMS and a
  comma. "Bermes" gave "Bermas" and "Berrrms" gave "Barrens". The original spelling is kept. In `housing_leased` the
  same voice's "Berms" was heard correctly. Carl should listen to this one; if it is wrong, the line can be voiced in
  Empress alone, or the text changed.
- Retaken: `greeting` (first take said "they're"; now "they are"), `housing` (Karaveen), `ack_home` (heard "windows";
  now matches), `ack_primer` (still as above). Rejected takes are in `probe/retryB1/` and `probe/retryB2/`.

**Pace** (words per second, `pace.json`): Linn's median is 2.49 against the other speakers' medians of 2.53 (Brann) to
3.59 (Torr). Her slowest takes are `greeting` at 1.87 (11.5 s for 22 words; retaken once, the retake was the same
length, so this is how this voice reads that line), `greet_shade` at 2.01 (one of the two lines Carl approved),
`idle_pumps` at 2.12 and `greet_evening` at 2.19. **`housing` is 28.2 s** (Empress 28.8 s); the conversation waits for it.
Pauses inside the long takes are short (greeting 1.2 s in all, housing 2.8 s in five pauses), so the slowness is drawn-out
speech, not gaps.

**Voice measures** (Praat, median over her takes): pitch 123 Hz (Amelia 215), HNR 10.8 dB (11.6), jitter 1.8 %
(1.8), shimmer 7.1 % (7.3). Deeper and a little breathier than Amelia, and not rougher on jitter and shimmer.

## Characters spent

| | Credits left |
| --- | ---: |
| Start of the item | 11,095 |
| After screening, candidates and the Empress set (first hand-back) | 9,604 |
| Before generating the Seer Morganna set | 9,553 |
| Now | 8,318 |

The Seer Morganna round (full set, pronunciation probes, retakes) took about 1,235 credits; the account bills about
0.4 credit per character of text. 2,777 credits used by this item in all.

## Commands

From the repository root (`P2` = `~/.local/state/ward-programme/showcase-phase2-20261120`):

    python3 art/linn_voice_20261120/linn_voice.py                          # dry run: lines, characters, cache state
    python3 art/linn_voice_20261120/linn_voice.py --generate               # default voice (voice.json), idempotent
    P2/seq.sh install linn_voice-N AthenHill.Editor.LinnVoicePass20261120.RunBatch install,verify

Switch voice (cached ones cost nothing), then the same Unity run so the clips re-import and verify compares their
imported lengths with the new WAVs:

    python3 art/linn_voice_20261120/linn_voice.py --generate --voice MHPwHxLx0nmGIb5Jnbly   # Empress (cached)
    python3 art/linn_voice_20261120/linn_voice.py --generate --voice wGcFBfKz5yUQqhqr0mVy   # Maria Moody (cached)

Set `default_voice` in `voice.json` to make a switch stick. Other options: `--master`, `--stt`,
`--candidate NAME --voice ID --lines a,b`, `--budget N` (default 6,000). `probe_pron.py 'phrase' ...` makes a short
TTS probe in the default voice and transcribes it (a few credits each).

Rollback to Amelia (Editor pass first, then the audio files from `previous/`), one command:

    art/linn_voice_20261120/rollback.sh

The record edits above are not reverted by it. Not exercised.

## Verified and not verified

- Verified: `LinnVoicePass20261120` install and verify via `P2/seq.sh` (runs `linn_voice-1` to `-4`; logs in
  `unity/evidence/showcase_phase2/20261120/linn_voice/`). The latest run, `linn_voice-4` (Seer Morganna), passed verify:
  13 clips at their usual paths, mono, 44.1 kHz, each imported length equal to the mastered WAV. A repeated install
  left the asset byte-identical. `test_devui` passes; `compile_check.py` passes for all three assemblies.
- Not verified: nobody but Carl has heard any take, and he has heard only two. No player build and no native run here:
  `check_linn_voice_native.py` is written for the orchestrator's combined build and has not been run.
  `NpcVoiceAudit.VerifyAndBuild` not run (it builds the player).

## Open

- "Berms" in `ack_primer` (see above), and "Karaveen" in `housing`, need Carl's ear.
- The `greeting` take is slow (11.5 s), and `housing` takes 28.2 s.
- Seer Morganna was made as a fortune-teller character voice; whether she sounds theatrical across all 13 lines cannot be
  measured.
