# Steady Hands bench audio (20 Nov 2026)

The bench job's sound package: contact, tool and mechanism effects, a bench ambience bed, and Brann's and Ossa's lines.
**Nobody has listened to any of it.** Every check below is a measurement.

## Files

| What | Where |
| --- | --- |
| Event table (source of truth for effects) | `make_events.py` writes `events.json` |
| Voice lines | `lines.json` (`{id, speaker, text, trigger, file}`) |
| Generators | `gen_sfx.py` (effects and synthesis), `gen_voice.py` (voice, STT check), `balance.py`, `budget.py` (cap) |
| Manifest (contract section C) | `manifest.json`: `events` (files, loop, lufs, pitch_range, note, takes with measurements), `contact_matrix`, `voice`, `balance` |
| Loop seam checks | `seam_check.json` |
| Spend | `ledger.json` (runs, subscription before and after), `stt_spend.json` |
| Transcripts | `stt.json` |
| Game clips | `unity/AthenHill/Assets/AthenHill/Audio/ElevenLabs/Bench/<group>/<group>-<name>-<nn>.wav`, `Bench/Voice/<speaker>-<id>.wav` |
| Paid sources and request records | `unity/staging/elevenlabs-audio/bench-20261120/{sfx,voice}/` |

Re-run (no API calls): `heavy.sh python3 .../gen_sfx.py --master`, then `balance.py`, then `gen_voice.py --master`
(in that order: each writes its part of `manifest.json`). `--generate` pays only for takes whose exact request is not
cached; an edited prompt is a new take (the source name carries a hash of the request), old takes stay on disk.

## Counts

- 113 events in 37 groups, 239 effect clips: 217 ElevenLabs takes (`eleven_text_to_sound_v2`, influence 0.55) and 22
  synthesised in numpy. 23 loops (22 effect loops plus the stereo bed).
- 36 voice lines: 32 Brann (Callum), 4 Ossa (Victoria); `eleven_multilingual_v2`, stability 0.55, similarity 0.78,
  style 0.12, speaker boost (the existing colonist settings); mastered with the Linn master (edge trim, two-pass
  loudnorm -20 LUFS / -2 dBTP, 40 ms lead).
- 275 WAVs with `.meta` files, 38 folder `.meta` files; GUIDs are md5 of `ward-steady-hands-bench-20261120/<path under
  Assets>`, all unique. Effects import as PCM, decompress on load, `normalize: 0` (levels are mastered here); the bed as
  Vorbis compressed in memory; voice as the crafting voice generator writes it.

## Mastering

One-shots: trim, 40 Hz high-pass, fitted to an event loudness target (four repeats with 0.5 s gaps, as the 19 Nov
combat pass) with a soft peak cap, then the variants of each event levelled to within 1.5 dB of each other.
Loops: 35 Hz high-pass, cut and cross-faded here (never trusting the generated loop): the steadiest section is chosen,
the loop length searched within ±12 % for the best overlap correlation, linear fade when the overlap is correlated
and equal-power otherwise, twelve candidates (four fade lengths × three starts) seam-checked and the best kept.
Seven sources were gappy (strokes and swirls with silence between): their active stretches were spliced into a
continuous stream of 160 ms grains first (`densify`). Bed: 17.4 s stereo, one 1.5 s equal-power fade, plus faint
synthesised lamp-housing ticks placed circularly.

Levels: targets are in `events.json` (-29 to -36 event LUFS for contacts after the balance shift of -4 dB, faults
loudest; loops -31 to -36 LUFS; bed -38 LUFS). Voice -20 LUFS.

## Checks (measured)

- **Seams: 23 of 23 loops pass** at pitch 0.8, 1.0 and 1.3 (tiled three times and resampled): sample step at the seam
  under the loop's own 99.9th percentile step, energy above 6 kHz at the seam under 1.5× the loop's own 99th
  percentile window, and the 20 ms level step across the seam no bigger than the loop's own 99th percentile step.
  The first cut failed four (spin.true, wind.crank, solder.hiss, seam.trace); the candidate search fixed them.
- **Balance** (loudest variant of each one-shot with all peaks aligned on the loop mix's loudest sample, unity gain):
  press -3.4, test card -1.8, screw fault -7.2, quench and vent -4.1, drill bind -2.1, job done -2.3, shake after
  -2.1 dBFS: all under -1.5. A synthetic worst case (bed + three loudest loops + three loudest one-shots, all aligned)
  reaches +1.1 dBFS; `balance.recommended_bus_gain` 0.74 covers it if `AssemblyAudio` ever lets that happen.
- **Test pulse vs the pistol:** pulse -31.0 event LUFS against the scrap pistol's three-layer shot at its runtime
  gains -18.4: 12.6 dB weaker.
- **Voice transcripts** (ElevenLabs Scribe): 35 of 36 matched apart from spelling ("mold", "gray", "Bran", apostrophes
  dropped); `fault_stripped` came back "Plyos" for "Pliers" and was retaken (t2 transcribes correctly).

## Spend

2,691 credits charged to this brief by the response headers (effects 2,054 including 94 for retakes; voice 603 including one
retake; speech-to-text 34) against the 5,500 cap. The account read 8,021 before the first take and 5,340 after the
last (the subscription figure lags a few credits).

## Takes rejected (retaken with new prompts; the old takes stay in staging)

- `tap.strike` v4: 82 % of its energy under 150 Hz (a thud, not a ringing tap).
- `pulse.shot` v3: 76 % under 150 Hz (a boom; the pulse must be thin).
- `seat.canvas_rubber` v1: 98 % under 150 Hz.
- `seat.glass_rubber` v2: 71 % under 150 Hz.
- `vise.creak` v1: five separate groans in a one-shot.
- `oil.wipe` v1: four separate wipes.
- `peel.tape` and `screw.turn` v1: level swinging 30-40 dB inside the loop (gaps).
- Voice `fault_stripped` t1: "Pliers" heard as "Plyos".

## Doubts (for Carl's ear)

- Loops built from gappy sources still pulse: `screw.turn` v1 (level std 12 dB in the loop; v2 is steady at 0.6 dB,
  prefer it if v1 sounds like ticking), `solvent.swirl` (10 dB), `bend.yield` (10 dB), `wind.crank` (8 dB),
  `peel.tape` (7 dB), `brush.dust` (6 dB). Swirls and creaks pulse naturally; the wire on the bobbin should sing
  evenly and may not.
- `press.knit` is the one sound with no real-world reference ("nanites knitting"): whether it reads as anything is
  unknown.
- `seat.canvas_rubber` v2 is still 74 % low end (a cloth thump; may vanish on small speakers).
- Synthesised: damper tick and settle, tester probe, lamp relay and buzzer, cure lamp hum and switch, cell power down
  and up, the three UI cues. The UI cues are soft digital blips, kept away from bells (Carl's trade-click note).
- Spin `true` against `grind` and `solder.flow` against `solder.cold` were prompted as pairs and measure differently
  (grind is broadband and gritty), but whether they are unmistakable is a listening question.
- Lines: Ossa's `range_ready` names "three on the plate", assuming the range plates; the range set-up is `craft`'s.
  A few short lines landed 1.5-2.5 dB under -20 LUFS because the -2 dBTP peak limit held them (stage7,
  hint_schematic, card_after_standard).

## Departures

- Event groups beyond `DESIGN.md` section 11, for steps the tables need: `wind` (bobbin crank and snap), `pry` (case
  clips), `part` (circlip, gears, spring, connector, scrap bin, floor), `kit` (tool roll), `wire` (lead sliding),
  `seat.blocked`, `seat.spring_click`, `seat.dovetail`, `seat.slide`. `brush` covers the wipe verb; `strip` the
  strippers.
- `asm.amb.bed` is stereo (the contract says mono WAVs; the brief allowed stereo as `unity/AUDIO.md` treats ambience).
- Contact matrix: no `ceramic` or `paper`-on-mat seats were made; they map to `seat.tiny_steel` and `card.clip`.
- Brann has 32 lines, not about 28 (stage 0 is his "Bench is yours" line; a `damper_bad` line was added).
- All effect targets were lowered 4 dB after the first balance check (`SHIFT` in `make_events.py`).

Status: delivered, not installed in a scene (the bench system binds the clips), not listened to, not accepted by Carl.
