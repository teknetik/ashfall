# Brief: `audio` — the bench's sound and the voices

You make the audio package for the Steady Hands bench job: every contact, tool and mechanism sound, a bench ambience,
and Brann's and Ossa's lines. At the bench, sound is how the player feels resistance, so it matters as much as the
models.

Read first: `../AGENT-RULES.md`, `../DESIGN.md` sections 6, 7, 10 and 11 (the step tables say what each sound must
tell the player), `../CONTRACT.md` section C (binding), `../FACTS.md` (Tooling: the existing generators),
`unity/AUDIO.md`, `unity/tools/generate_combat_audio_20261119.py` and `art/showcase_20261119/combat_audio/README.md`
(the pattern to follow: one prompt per variant, the dry suffix, trim, shape, loudness fit, ledger, manifest),
`art/crafting_assembly_20261120/generate_voices.py` and `lines.json` (Brann and Ossa, with stable `.meta` GUIDs),
`art/linn_voice_20261120/linn_voice.py` (the better master and the pronunciation map).

## What you own

`art/steady_hands_bench_20261120/audio/**` (generator scripts, `events.json`, `lines.json`, `manifest.json`, ledger,
README) and `unity/AthenHill/Assets/AthenHill/Audio/ElevenLabs/Bench/**`. Sources stay in
`unity/staging/elevenlabs-audio/bench-20261120/`. No Unity runs, no C#.

## Budget

ElevenLabs has about 8,000 credits until 5 December and nothing else may run out because of you. Hard cap for this
brief: **5,500 credits** (about 3,300 for sound effects at roughly 10 credits a second, 2,000 for voice at one credit
a character, the rest for retakes), enforced in the generator with a ledger from the `character-cost` header and a
subscription read before and after. Dry-run first and print the plan and its estimated cost. Stop at the cap and
report what is missing.

## 1. Sound effects

Write `events.json` first: every `asm.<group>.<name>` event from `DESIGN.md` section 11, with for each: what the
player must learn from it, one-shot or loop, number of variants, length, loudness target, and the prompt. Then
generate. Requirements:

- **Loops that carry resistance** (screw turn, vise thread, drill, bobbin crank, press pump, knit, tester whirr,
  spin true and spin grind): they must loop without a click and survive pitch from 0.8 to 1.3; cut and cross-fade
  them yourself, do not trust a generated loop. One to three seconds each.
- **Repeated one-shots** (seat, snip, tap, click, drop in dish, screw seat): at least three variants, short, dry,
  with a consistent level.
- **A contact matrix** by material pair for seats and drops: steel, alloy, wood, rubber, plastic, copper, glass,
  canvas, paper on the mat (rubber), the dish (steel) and each other where the job needs it. Prune to pairs the step
  tables use.
- **Paired good and bad sounds** that are unmistakable: cam-out against a clean turn, a stripped head, a cold joint
  against solder flowing, the grinding spin against the true spin, the buzzer against the lamp click, the rattle of
  the bare pistol against the damper's single tick.
- **Synthesise what is better synthesised** (pure clicks, ticks, the buzzer, the tester lamp relay): numpy, as
  `art/next_level_20261002/combat/make_trade_click.py` does, costs nothing.
- **Bench ambience** `asm.amb.bed`: a 20 to 30 second seamless bed of the shop from the bench (lamp tick, faint
  compressor, distant avenue), quiet, mono or stereo as `unity/AUDIO.md` treats ambience.
- **Test pulses** `asm.pulse.*`: the low-power test shot, clearly weaker than the game's pistol shot
  (`Audio/ElevenLabs/Combat/Pistol`), and the paper hit.
- Mastering as the combat pass does (trim, fades, per-event loudness, soft limit, 16-bit mono 44.1 kHz WAV), plus a
  `balance` check that the loudest simultaneous set stays under -1.5 dBFS.
- `.meta` files with stable GUIDs as `generate_voices.py` writes them, so data can reference clips before Unity
  imports them.

## 2. Voice

Write `lines.json` (`{id, speaker, text, trigger, file}`) and get the text right before spending: Brann is a gruff,
dry salvage dealer who respects careful work and says little; Ossa is a Warden, direct, a little wry. Existing lines
to match are in `U/Data/npc_brann.asset`, `npc_ossa.asset` and the 20 Nov `lines.json`. Lore words are in `lore.md`;
keep to them and invent no history. Lines are short (most under 70 characters) because they play over work.

- **Brann, about 28 lines**: taking the bench ("Bench is yours. Lay it out."), one per stage start (8), the stuck
  screw, the cracked tang, the first fault of each kind (cam-out, stripped head, short lead, cold joint, over-bend,
  a part flying off: 6), three idle hints that point without solving, the spin test good and bad, the press ("Keep it
  in the green."), the damper test, his verdict on the before card and on the after card for each quality (Rough,
  Standard, Fine), the hand-over ("Range. Go and feel the difference."), stepping away mid-job and coming back,
  abandoning.
- **Ossa, 4 lines** at the range for the test fire: before the first shot, after a tight group, after a poor one, on
  completion of the order. `craft` binds them.
- Use the existing voices and settings (`FACTS.md`), the Linn master, and a pronunciation map for lore words
  ("Berms", "Karaveen" went wrong before: check by transcript if you can, list doubtful takes for Carl's ear).
- Deliver WAVs to `U/Audio/ElevenLabs/Bench/Voice/` named `<speaker>-<id>.wav` with stable `.meta` GUIDs.

## Report

After the dry run, append the plan and its cost to `PROGRESS.md` and go on. Final report: counts of events, clips and
lines; credits spent against the cap and what is left on the account; what was synthesised; the loops' seam check;
which takes you rejected and why; every sound you could not make convincing; lines you doubt. Nobody has listened to
any of it: say so, and give Carl a short listening list (the ten clips that matter most, with paths).
