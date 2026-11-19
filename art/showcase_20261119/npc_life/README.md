# NPC life: barks, captions and the missing voices (19 Nov 2026)

Status: code written and compiled (`unity/tools/compile_check.py`: Runtime, Editor and Edit Mode tests OK), audio
generated, **installer not yet run, nothing tested in Unity or natively**. Not yet accepted by Carl.

## What changed

Before this pass nobody in Ward said anything outside the dialogue window. Now:

- **Barks**: short lines outside dialogue from the eight talking colonists (Mira, Torr, Vex, Linn, Brann, Tamsin, Wardens
  Ossa and Rell) and the three ambient walkers (Daro, Sel, Anso). Triggers:
  - **Greeting** when the player walks up (5.5 m; edge-triggered, re-arms after stepping back beyond 8.5 m; 150 s per
    colonist; never within 60 s of a conversation with them). Some greetings depend on the hour or the story.
  - **Acknowledge** replaces the greeting once per save after a milestone: primer complete (`primer`) or the home leased
    (`flag:home_leased`). Recorded as a story flag `bark.<speaker>.<line>`, so it survives save/load (save format unchanged, v4).
  - **OrderDone** replaces the greeting while a completed field order is news (15 min of play; each colonist once per
    order). Runtime only: a reload forgets the news.
  - **Idle** remarks every 70–150 s while the player lingers within 9 m and in sight; some tied to the hour (CityTimeOfDay).
  - **Weapon**: Wardens keep weapons holstered inside the walls (PlayerCombat), so the city reacts at the moment that
    happens: the player comes back through the wall with a weapon out (auto-holster) or presses 1/2 inside the walls with
    a weapon equipped. The nearest speaker with a Weapon line in range (12 m; Wardens 25 m) and in sight answers; 25 s
    per speaker.
  - **Passing**: walkers speak when the player comes within 3.2 m (90 s per walker), and now **glance at the player**
    as they pass (ActorLookAt on each walker's visual: focus within 4.5 m, ±55°, no idle glances or rest levelling, so
    the walk clip's own head motion is untouched otherwise).
  - Rules: one bark at a time; 7 s of silence after any bark ends; nothing during dialogue, windows, pause or Settings,
    and 3 s of grace after one closes; a speaker must be in sight (no wall between heads, e.g. Brann behind the Salvage
    wall); the last three lines of each speaker are not repeated; hour-specific lines are preferred in their hours.
  - A talking colonist plays its talk clip while barking (ActorLookAt then holds eye contact). No lip sync: the Meshy
    rigs have no face bones.
- **Captions**: every bark is subtitled low centre, above the interaction prompt (bottom 252 px, 760 px wide; 640 in the
  compact layout): speaker in small bronze capitals (14 px, `#a48a62`, 20 px in small windows) over the line (21 px warm
  white) on a dark enamel strip. It is apart from the radio panel and notices under the compass and **never written to
  the event log** (DESIGN.md: the log must not read like a chat channel). Hidden in every non-play state.
  Subtitles on/off: `BarkDirector.CaptionsEnabled` (PlayerPrefs `AthenHill.Settings.v1.BarkCaptions`, default on). There
  was no subtitles setting; **a Settings toggle is still needed** (GameSettings/SettingsPanel belong to another agent): it
  only has to read/write that property. With captions off, lines without a take are skipped.
- **Voices** (ElevenLabs, same model, settings and mastering as `unity/tools/generate_npc_voices.py`):
  - Tamsin's five dialogue nodes (new voice: **Evelyn**, British, "resourceful and ironic", `XEoBW4iDmiawQP72xnAF`).
  - Ossa's `locker`, `range` and (follow-up) `long_arm` nodes (Victoria, as before). The old takes (pre-hotbar key numbers) are kept in
    `unity/staging/elevenlabs-audio/npc-voices/previous_20261119/`; the new takes reuse the canonical paths and GUIDs that
    `NpcVoiceAudit` expects.
  - 80 barks (68 talking colonists in their 2 Oct voices; walkers Daro = **Paul** `49TtX0KZLnuzDrAizTkN`, Sel = **Alice**
    `Xb7hH8MSUJpSbSDYk0k2`, Anso = **Will** `bIHbv24MWmeRgasZH58o`).
  - Tamsin's `supplies` node said "press 2" / "press 9" (the hotbar is configurable since 5 Oct: medkit 3, nano 4 by
    default). Its text is now key-free and voiced as such: "Medkits patch you up mid-fight; keep a few on your hotbar. The
    trauma kit closes worse wounds. A nano cell refills your weapon and overclocks the regulator, so the charge keeps coming
    back while you fire. The surge pack runs hotter and longer." The installer changes it only while it still reads the old text.

## ElevenLabs usage

| | character_count / limit | left |
| --- | --- | --- |
| Before (19 Nov, first call) | 32,630 / 46,736 | 14,106 |
| After first session | 34,627 / 46,736 | 12,109 |
| Follow-up before (control-hint fixes) | 34,657 / 46,736 | 12,079 |
| Follow-up after (final) | 34,791 / 46,736 | 11,945 |

Total for the pass: **2,161 credits** (32,630 → 34,791). The follow-up spent 134 (Ossa's `long_arm` re-take; budget
1,500). First session: 2,027 credits by the per-request `character-cost` headers (1,997 + 30 for the two Warden weapon lines added
last; the subscription counter showed 1,997 of them at the final check). 5,062 characters of text were voiced: this
account bills about 0.4 credits per character for `eleven_multilingual_v2`. Budget was 10,000; nothing was refused.
`voice_manifest.json` has every line (text, voice, characters, request id, history item id, cost, hashes, seconds) and
both runs with before/after counts. The API key was read from `.env` by the script and never printed or stored.

| Priority | Lines | Characters |
| --- | ---: | ---: |
| (a) Tamsin's dialogue | 5 | 1,124 |
| (b) Ossa locker + range | 2 | 529 |
| follow-up: Ossa long_arm | 1 | 335 |
| (c) talking colonists' barks | 68 | 2,962 |
| (d) walkers' barks | 12 | 447 |

## Files

New (mine):
- `unity/AthenHill/Assets/AthenHill/Scripts/Npc/BarkSet.cs` (BarkTrigger, BarkLine, BarkSet asset)
- `.../Scripts/Npc/BarkLogic.cs` (pure: BarkRules line choice/hours/caption time, BarkMemory cooldowns and no-repeat, ApproachGate)
- `.../Scripts/Npc/NpcBarker.cs` (per speaker: lines, radii, voice emitter)
- `.../Scripts/Npc/BarkDirector.cs` (triggers, gating, audio, captions, QA state)
- `.../Scripts/Npc/BarkCaptionView.cs`
- `.../Editor/NpcLifeInstall20261119.cs` (installer)
- `.../Tests/Editor/NpcBarkTests.cs` (11 Edit Mode tests)
- `.../Audio/ElevenLabs/NpcBarks/*.wav` (80), `.../Audio/ElevenLabs/NpcVoices/npc_tamsin-*.wav` (5); metas come from Unity's import
- `unity/staging/elevenlabs-audio/npc-barks-20261119/` (source MP3s + request records), `.../npc-voices/npc_tamsin-*`, `npc_ossa-locker|range.*` (replaced; old in `previous_20261119/`)
- `art/showcase_20261119/npc_life/`: `barks.json` (source of truth), `generate_voices.py`, `voice_manifest.json`,
  `subscription_before.json`, `subscription_after.json`, this README; the installer writes `assets|dialogue|scene|verify|rollback.json` and `install_record.json` here.

Edited (owned): `Scripts/NpcAgent.cs` (non-serialized `barking` flag: talk clip while barking).
Replaced in place: `Audio/ElevenLabs/NpcVoices/npc_ossa-locker.wav`, `npc_ossa-range.wav` (same GUIDs).
Shared, additive only: `UI/CityHUD.uxml` (one `bark-caption` element after `nametags`), `UI/CityHUD.uss` (rules appended
at the end), `Scripts/NativeQa.cs` (snapshot key `barks`; commands `barkSnapshot`, `barkReset`, `barkCaptions {on}`).
Data assets (`npc_tamsin.asset`, `npc_ossa.asset`, `Data/Barks/*.asset`) and the scene change only through the installer.
Not touched: GameSession, CityHud, CityAudio, AmbientWalker, ActorLookAt, GameSettings, SettingsPanel, FollowCamera, Combat.

## Install (when Unity may run)

```sh
# from unity/AthenHill, Editor closed, one Unity job at a time, inside the usual memory-capped scope
unity.sh LOG -executeMethod AthenHill.Editor.NpcLifeInstall20261119.RunBatch -nographics --steps assets,dialogue,text,scene,verify
```

Steps are idempotent. `assets` creates `Data/Barks/barks_<speaker>.asset`, adds missing lines and binds each take by
path only while the line's text matches `barks.json` (Inspector-edited text stays, caption-only); `--force` resets the
JSON lines and NpcBarker overrides. `dialogue` binds Tamsin's and Ossa's takes the same way. `text` corrects three CityCatalog descriptions. `scene` adds BarkDirector
to the GameSession object, NpcBarker to every active NpcAgent root and the three walkers, and ActorLookAt to each
walker's visual; existing components are kept. `verify` throws on any missing set, line, take, barker, walker head bone
or UXML element. Menu: **Athen Hill → NPC life → Install barks and voices (19 Nov 2026)**.

Re-generate audio (never re-spends for cached takes; refuses a stale bark take): `python3 art/showcase_20261119/npc_life/generate_voices.py --generate --budget N`.

## Rollback

`--steps rollback` removes every NpcBarker and the BarkDirector, the walker ActorLookAt components this pass added
(`install_record.json`), clears the takes it bound on Tamsin's and Ossa's nodes and restores the old texts (Tamsin supplies, Ossa long_arm, three catalog descriptions; long_arm is then unvoiced, its old take is in `previous_20261119/`).
`Data/Barks/`, the WAVs and staging files stay on disk. The previous Ossa takes are in `previous_20261119/` (they speak
the old key numbers, which is why they had been unbound). The UXML element and USS rules are inert without the director.

## Native test plan (real input, after the installer and a development build)

Use `barkReset` before each scripted walk-up, `barkSnapshot` (or `snapshot.json` → `barks`) to assert, and the lookbook
display for captures. `barks.last` has speaker, speakerId, line, text, trigger, voiced, time; `caption` is the text on screen.

1. **Greeting**: new game at the spawn, walk to Vex (scene ≈ 41.7, 0, −1.5). Expect within ~5.5 m: caption `VEX` + a
   greeting, voice audible from Vex, `last.trigger = Greeting`, `voiced = true`, Vex in his talk clip, head on the player.
   Step back < 8 m and return: nothing. Step beyond 8.5 m and return within 150 s: nothing (cooldown).
2. **No overlap / global gap**: walk straight from Vex to Daro's lane: the second line waits ≥ 7 s after the first ends.
3. **Windows**: during a bark press Esc: caption gone, voice paused; resume: caption back. Press E on the speaker: bark
   voice stops at once, dialogue voice plays; close: no bark for 3 s, no greeting from that colonist for 60 s.
4. **Idle**: stand 3–8 m from Mira 3 minutes: 1–2 idle lines, never the same twice in a row.
5. **Hour**: `timeSet 23`, walk up to Vex: `greet_night`; `timeSet 8`: `greet_morning`.
6. **Captions off**: `barkCaptions {on:false}`: voiced barks play with no caption; on again restores.
7. **Weapon** (save with the pistol): inside the walls near Torr press 2: notice "Wardens keep weapons holstered…" and
   Torr's Weapon line within 1.5 s. In the Berms draw, walk back through the wall by Rell: auto-holster notice and a
   Warden Weapon line if Rell or Ossa is within 25 m and in sight (record the distance if silent).
8. **Walkers**: stand on Daro's lane (≈ 38, 0, −3.5): as he passes within 3.2 m, a Passing line; `guards` in the snapshot
   lists his ActorLookAt with `Focused = true` while near, and his head visibly turns (judge at player height).
9. **Milestones**: with a save just after the primer, walk up to Mira: `ack_primer` (`once`), flag
   `bark.npc_mira.ack_primer` in `interaction.flags`; `barkReset`, walk up again: an ordinary greeting; save, Continue,
   walk up: still no repeat. Lease the home from Linn, walk away > 8.5 m and back: `ack_home`. Complete a field order,
   return, walk up to Brann: `order_done`.
10. **Dialogue takes**: open Tamsin (first visit, greeting, magazines, packs, supplies) and Ossa (locker, range): each
    node plays its take; the supplies text has no key numbers.
11. **Regression**: city loop and range tutorial checks; A/B frame time at hill/avenue/gate (expected within drift:
    11 speakers scanned at 5 Hz with at most a few raycasts, one AudioSource per speaker created on first bark).

## Known risks and open points

- Nothing here has run in Unity. Most likely to need tuning in play: radii, cooldowns, caption position against
  user-moved HUD windows, and the talk clip switching in for 2–3 s barks (0.15 s blend).
- Walker glance assumes the walkers' Meshy rigs have `Head`/`neck` bones like the colonists' (verify checks `Head`;
  ActorLookAt disables itself without it).
- Weapon reactions near the Berms wall depend on where Rell and Ossa stand relative to the crossing (not measured).
- `art/field_supply_20261005/apply_data.py` rewrites `npc_tamsin.asset` and the Field Supply catalog items from its own
  constants; those constants now carry the key-free texts (follow-up), so re-running it no longer brings the stale lines back.
- `NpcVoiceAudit` (Tamsin 5 nodes; every bark take), `unity/tools/devui/npc_roster.json` (Tamsin; Ossa 7; walkers under
  `ambientVoices`, which the devui seed and generate_npc_voices.py ignore) and `unity/AUDIO.md` now list the new voices
  (follow-up, with the coordinator's go-ahead). `test_devui.py` roster counts follow (8 NPCs, 36 takes; the test passes).
  NpcVoiceAudit's other node counts (e.g. Linn, Mira since their later nodes) were not re-checked; it has not been run.
- OrderDone news is not saved; once-only lines add `bark.*` story flags to the save.

## Control-hint sweep (follow-up, 19 Nov 2026)

Current controls (unity/README.md, since 5 Oct 2026): 1 primary weapon (rifle), 2 sidearm (pistol), 3–0 items the player
assigned (medkit 3 and nano cell 4 by default), left mouse or F fires (F is still bound to Fire in Controls.inputactions),
always-on mouse look. Swept: every `Data/*.asset` (NPC dialogue, CityCatalog, field orders, crafting), `Resources/*.asset`,
prefabs, the saved scene's serialized strings (BermsTutorial radio lines and steps), runtime string literals (notices,
journal steps, HUD hints and tooltips, PackPanel, Settings controls list), CityHUD.uxml and unity/README.md.

Changed (key-free where the HUD already shows the key):

| File | Old | New | Voiced |
| --- | --- | --- | --- |
| `Data/npc_ossa.asset` `long_arm` (installer `dialogue`) | …equip it in your loadout, and 8 draws it out here. | …equip it in your loadout, and draw it from your hotbar out here. | re-take, Victoria |
| `Data/npc_tamsin.asset` `supplies` (installer `dialogue`) | Medkits patch you up mid-fight, press 2. The trauma kit closes worse. … while you fire, press 9. … | Medkits patch you up mid-fight; keep a few on your hotbar. The trauma kit closes worse wounds. … while you fire. … | new take, Evelyn |
| `Data/CityCatalog.asset` `trauma_kit` (installer `text`) | …Closes what a medkit can't. Use with 2. | …Closes what a medkit can't. Use it from your hotbar. | no |
| `Data/CityCatalog.asset` `nano_cell` (installer `text`) | …keeps refilling while you fire. Use with 9. | …keeps refilling while you fire. Use it from your hotbar. | no |
| `Data/CityCatalog.asset` `nano_surge_pack` (installer `text`) | …firing or not. Use with 9. | …firing or not. Use it from your hotbar. | no |
| `UI/CityHUD.uxml` pause-panel controls label (edited directly) | Left-drag · Look … 1–6 · Hotbar | Mouse · Look (hold Left Alt for a pointer) … 1 / 2 · Weapons     3–0 · Hotbar items | no |
| `art/field_supply_20261005/apply_data.py` constants | the four old texts above (Tamsin supplies, three item descriptions) | the new texts | n/a (`--check` passes, nothing written) |

Checked and already current (no change): BermsTutorial `lineDraw` "Press 2 to draw it." and `lineTargets` "Left mouse
fires, and so does F; …" (code defaults and the saved scene; the October captures saying "Press 7" / "F fires from the
hip" predate the 5 Oct patch), the Draw step "Press 2 to draw the scrap pistol.", journal step "Draw the pistol (2)",
Ossa `locker` "Press 2 to draw the pistol…" and `range` "Draw with 2…" (re-voiced in the first session), the Long Arm
completion line "press 1 out here to draw it" (weapon keys are fixed, so naming 1 is correct; unvoiced radio text),
hotbar tooltips and the empty-slot notice (built from the live key), CityCatalog notes, Settings → Controls list,
"Press J" notices, and unity/README.md's controls table.

The two data assets change only when the installer runs; until then the game still shows the old texts.

## Every line of new writing

**Mira** (`npc_mira`) · Clara, British (`aj0fZfXTBc7E3By4X8L2`)

| id | trigger | when | line |
| --- | --- | --- | --- |
| greet_morning | Greeting | 5–11 h | Morning! Flasks are fresh sealed today. |
| greet_day | Greeting | 11–18 h | Afternoon. Counter's open if you need anything. |
| greet_evening | Greeting | 18–2 h | Evening, love. Still open, just about. |
| greet_any | Greeting | any | There you are. Need a top-up? |
| idle_seals | Idle | any | Now, where did I put the spare seals? |
| idle_greens | Idle | 6–20 h | Hydroponics still owes me two crates of greens. |
| idle_quiet | Idle | 20–5 h | Quiet tonight. I like it quiet. |
| weapon | Weapon | any | Not near my counter, please. Holster it. |
| ack_primer | Acknowledge | `primer`, once | Heard you came back from the Berms in one piece. Good. |
| ack_home | Acknowledge | `flag:home_leased`, once | Linn says you've taken the container on the south wall. Welcome home. |
| order_done | OrderDone | any | Word is Ossa's pleased with you. That's rare. |

**Torr** (`npc_torr`) · Chris, American (`iP95p4xoKVk53GoZ742B`)

| id | trigger | when | line |
| --- | --- | --- | --- |
| greet_part | Greeting | any | Hey. Got a spare part for me? No? Worth asking. |
| greet_again | Greeting | any | You again. Good. Something's always broken. |
| idle_boards | Idle | any | Three terminals, two spare boards. Somebody's waiting. |
| idle_slab | Idle | any | If the slab says nothing, ask a person. |
| idle_night | Idle | 20–5 h | Screens act up after dark. Always have. |
| weapon | Weapon | any | Whoa. Wardens see that in here, you'll lose it. |
| ack_primer | Acknowledge | `primer`, once | Back from the Berms? Bring me anything with a circuit board. |
| ack_home | Acknowledge | `flag:home_leased`, once | Got yourself a roof, I hear. Keep that locker shut. |
| order_done | OrderDone | any | Another one of Ossa's orders done? Not bad. |

**Vex** (`npc_vex`) · Charlie, Australian (`IKne3meq5aSn9XLyUdCD`)

| id | trigger | when | line |
| --- | --- | --- | --- |
| greet_carts | Greeting | any | Through you go. Mind the carts. |
| greet_morning | Greeting | 5–11 h | Gate's open. Caravans have the morning. |
| greet_night | Greeting | 21–5 h | Late to be coming through. Stay where I can see you. |
| idle_stone | Idle | any | Three generations of patches on this stone. |
| idle_everyone | Idle | any | Everyone gets through. Everyone helps hold the gate. |
| weapon | Weapon | any | Weapons away inside the gate. Wardens' rule, and the Column agrees. |
| ack_primer | Acknowledge | `primer`, once | Made it back through the Berms. Plenty don't, first time. |
| ack_home | Acknowledge | `flag:home_leased`, once | Heard you've got a key now. Near enough one of us. |
| order_done | OrderDone | any | Saw you come in on Warden business. Good on you. |

**Linn** (`npc_linn`) · Amelia, British (`ZF6FPAbjXT4488VcRRnw`)

| id | trigger | when | line |
| --- | --- | --- | --- |
| greet_shade | Greeting | any | Sit a while. The shade's free. |
| greet_evening | Greeting | 17–21 h | Evening. Best light on the hill, this. |
| idle_market | Idle | any | You can hear the whole market from up here. |
| idle_tree | Idle | any | This tree was old when I was young. |
| idle_pumps | Idle | 21–5 h | Listen. You can hear the aquifer pumps at night. |
| weapon | Weapon | any | Not on the hill, please. Put it away. |
| ack_primer | Acknowledge | `primer`, once | You came back from the Berms. I'm glad. |
| ack_home | Acknowledge | `flag:home_leased`, once | How's the container? Keep the window shut against the dust. |
| order_done | OrderDone | any | The Wardens talk about you now. Don't let it go to your head. |

**Brann** (`npc_brann`) · Callum, American (`N2lVS1w4EtoT3dr4eOWO`)

| id | trigger | when | line |
| --- | --- | --- | --- |
| greet_heavy | Greeting | any | Door's open. Bring me something heavy. |
| greet_bench | Greeting | `primer` | Back again? Bench is free. |
| idle_drone | Idle | any | Half of this was a drone last week. |
| idle_hoist | Idle | any | Hoist sticks. Always the hoist. |
| weapon | Weapon | any | Easy. Holster that in my shop. |
| ack_primer | Acknowledge | `primer`, once | Survived Ossa's primer, huh? Now you're useful. |
| ack_home | Acknowledge | `flag:home_leased`, once | Got a locker now? Fill it with scrap. Sell me the rest. |
| order_done | OrderDone | any | Another order closed. Ossa will run you ragged. |

**Tamsin** (`npc_tamsin`) · Evelyn, British (`XEoBW4iDmiawQP72xnAF`)

| id | trigger | when | line |
| --- | --- | --- | --- |
| greet_step | Greeting | any | Mind the step. Always mind the step. |
| greet_pack | Greeting | any | Back again. Pack holding up? |
| idle_straps | Idle | any | Twenty years of caravan straps. My shoulders remember every one. |
| idle_issue | Idle | any | New issue on the shelf. The fab co-op's been busy. |
| weapon | Weapon | any | Not in here, dear. Holster it. |
| ack_primer | Acknowledge | `primer`, once | First run in the Berms done? Your pack will want upgrading. |
| ack_home | Acknowledge | `flag:home_leased`, once | A home of your own. Don't fill the locker with junk. |
| order_done | OrderDone | any | Ossa's work again? I'll restock the medkits. |

**Warden Ossa** (`npc_ossa`) · Victoria, British (`N8SmJJ4vvs5Mz9VaT6u5`) · NpcBarker {'weaponRadius': 25}

| id | trigger | when | line |
| --- | --- | --- | --- |
| greet_locker | Greeting | `!primer` | The arms locker's under the canopy. Start there. |
| greet_quiet | Greeting | `primer` | Colonist. The Berms are quiet. Don't trust it. |
| idle_ridge | Idle | any | Eyes on the ridge. Always the ridge. |
| idle_night | Idle | 20–5 h | Machines don't sleep. Neither does the watch. |
| weapon | Weapon | any | Weapon away inside the walls, colonist. |
| ack_primer | Acknowledge | `primer`, once | Primer done. You'll do. |
| order_done | OrderDone | any | Order logged. Good work out there. |

**Warden Rell** (`npc_rell`) · Roger, American (`CwhRBWXzGAHq8TQ4Fs17`) · NpcBarker {'weaponRadius': 25}

| id | trigger | when | line |
| --- | --- | --- | --- |
| greet_lane | Greeting | any | Return lane's clear. Keep it that way. |
| greet_back | Greeting | `primer` | Welcome back. Anything following you? |
| idle_dust | Idle | any | Dust on the wind. Could be weather. Could be drones. |
| idle_gap | Idle | any | Keep the gap clear. It's somebody's way home. |
| weapon | Weapon | any | Holster it at the wall. Ward rules. |
| ack_primer | Acknowledge | `primer`, once | You made it through. Plates, drone, depot. Not bad. |
| order_done | OrderDone | any | Heard it on the radio. Nice work. |

**Daro** (`walker_daro`, walker `npc_walker_01`) · Paul, British (subtle Northern) (`49TtX0KZLnuzDrAizTkN`)

| id | trigger | when | line |
| --- | --- | --- | --- |
| pass_load | Passing | any | Coming through. Heavy load. |
| pass_caravan | Passing | any | Caravan's in at noon, if you're buying. |
| pass_road | Passing | any | The Tubes took the trade. Never took the road. |
| weapon | Weapon | any | Easy, friend. I'm only carrying rope. |

**Sel** (`walker_sel`, walker `npc_walker_02`) · Alice, British (`Xb7hH8MSUJpSbSDYk0k2`)

| id | trigger | when | line |
| --- | --- | --- | --- |
| pass_vents | Passing | any | Fab's running warm today. Keep clear of the vents. |
| pass_wand | Passing | any | Mind the wand. It's calibrated. |
| pass_node | Passing | any | Goods node's humming. Shipment due. |
| weapon | Weapon | any | Put that away before a Warden sees it. |

**Anso** (`walker_anso`, walker `npc_walker_03`) · Will, American (`bIHbv24MWmeRgasZH58o`)

| id | trigger | when | line |
| --- | --- | --- | --- |
| pass_greens | Passing | any | Fresh greens at the market. Tell them Anso sent you. |
| pass_satchel | Passing | any | Mind the satchel. Lettuce bruises. |
| pass_beans | Passing | 10–17 h | Hot one. The beans love it. |
| weapon | Weapon | any | Whoa. Not near the greenhouses. |

**Dialogue text changed**: `npc_tamsin` / `supplies` (quoted in What changed). Tamsin's other four nodes and Ossa's locker/range nodes were voiced unchanged.

## Native QA (19 Nov 2026)

- No game defect found; no code changed in this package. `check_showcase_npc_life.py` (batch-qa5 24/26, the two failures
  were check bugs, re-run on batch-showcase-qa: see unity/evidence/showcase/20261119/qa/README.md): Vex's once-only
  `ack_primer` then an ordinary greeting, no repeat inside the cooldown, `greet_night` at 23:00 and `greet_morning` at
  08:00, Esc hides the caption and pauses, captions off still plays the voiced line, Daro's Passing line with his
  ActorLookAt focused, Mira's `ack_primer` saved as `bark.npc_mira.ack_primer`, an idle remark after 68 s, Tamsin's
  greeting/packs/supplies/magazines and Ossa's locker (and range) nodes play their own takes.
- Open: Vex's ActorLookAt was not focused at the sampled moments of his barks (the walkers' glance works). Nothing was
  heard: voices, levels and the 7 s gap need a listening pass. Captions sit at y ≈ 779–828 of 1080, over the colonist's
  legs in the default third-person view; readable on sand and at night.
