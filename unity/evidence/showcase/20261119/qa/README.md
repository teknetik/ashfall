# Native QA of the showcase programme (19 November 2026)

First native runs of the seven packages in `art/showcase_20261119/`. Everything was run on the Linux development player
(OpenGL Core, RTX 3060 12 GB, i9-10850K, NVIDIA 615.78.08, 1920×1080, High preset with TAA) on the private QA display
:5, muted, through the shared Unity lock. Real keyboard/mouse input via XTEST for the verbs; the dev bridge for teleports,
camera aim, time, weather and reads. **Nothing was heard**: audio checks assert which clip/source played, not how it sounds.
Captures are git-ignored; this file is the record.

## Builds

| Build | When | Contents |
| --- | --- | --- |
| `Builds/batch-showcase1` | 14:09 | round 2: all seven packages installed, Edit Mode 384/384, no QA fixes, before the night pass |
| `Builds/batch-qa1` … `batch-qa5` | 14:43–15:47 | QA fix rounds (p1 … p5 below) |
| **`Builds/batch-showcase-qa`** (also `LinuxDevelopment`) | **17:32** (earlier finals at 16:31 and 16:56; rebuilt with the NPC facing fix, then with the name-plate fix) | every fix below; Edit Mode r6 **390/390**; the night-readability pass **applied and verified at 16:04** (`art/night_readability_20261119/verify.json`, 0 problems; it had been rolled back and re-applied at 16:03–16:04), conversation shot re-tuned through `ShowcaseCameraInstall20261119 --steps shot` (15:35), map survey render (14:39) |

## Regression (existing loop)

| Check | batch-showcase1 / qa1 | batch-showcase-qa (final) |
| --- | --- | --- |
| City loop (`run_cityloop.py`) | PASS | **PASS** |
| Range tutorial (`check_checkpoint.py`, incl. its city loop) | 10/10 (qa1) | **10/10** |
| Rifle quest | 38/38 | **38/38** |
| Home / journal | 37/37 | **37/37** |
| Field Supply | 26/26 | **26/26** |
| Berms expansion | 8/8 | **8/8** |

No game regression was found. Four failures were stale or broken checks, fixed in the check (no assertion weakened):
`check_checkpoint.py` and `check_berms_expanse.py` moved the XTEST pointer while the game's cursor was locked (always-on
mouse look since 5 Oct: one huge mouse delta threw the camera to pitch 80, "Gate route blocked"); the expansion check drew
the pistol with 7 (2 since the 5 Oct hotbar); `city_loop_check.py` asserted the mute button mutes, but QA-display runs now
start muted, so it asserts the toggle. Tooling: `ATHEN_EXE` pins a private build copy (qa.py, check_checkpoint,
run_cityloop), `ATHEN_OUT` for argv-only scripts, and the checkpoint/expansion/inventory launchers mute the player on the
QA display. Runners: `qa/run_regression.sh BUILD TAG [checks]`, `qa/run_packages.sh BUILD TAG checks`.

## Packages

New checks: `unity/tools/check_showcase_{combat_feel,combat_audio,npc_life,camera,interface,world_map,weather}.py` (shared
helpers `unity/tools/showcase_qa.py`: private config, save folder and HOME per run, so photo-mode PNGs and saves never touch
Carl's folders), `check_showcase_perf.py`, `check_showcase_perf_bisect.py`. Reports in `qa/<round>/<name>/report.json`.

| Package | Verdict | Last run | Notes |
| --- | --- | --- | --- |
| combat_feel | **PASS** | 23/23 (qa5) | plate and droid markers + ticks, kill markers = kills, shake (pistol 0.02°, damage 0.16–0.8°), suppressed under Reduced Motion, low-vitality edge below 35 % and cleared by a medkit, optic weak point (4 of 12 aimed rifle shots registered; optic 43.4 vs body 28.9 = ×1.45), brass critical marker, critical flash, FX light cap never above 2, gunner bolts. Not seen: criticalStaggers stayed 0 |
| combat_audio | **PASS (machine-checkable part)** | 14/14 (qa5) | pistol keeps its arrays, rifle uses `weapon_field_rifle` (single and a 12-shot burst), Sentinel/Reaper/Gunner/Lancer play their own clips (aim, fire, tell, strike, steps, death), Sentinel roll loop on near and off from the city, bolt fly-bys/impacts, no droid voice left on UI. Alerts were not caught in the sampled "last clip" (sampled every 0.5 s). **Not heard by anyone.** |
| npc_life | **PASS** | 27/27 (final) | greetings + captions, once-only ack_primer (flag saved), night/morning lines, cooldown, Esc hides the caption, captions off, walker Passing line with glance, idle remark (68 s), Tamsin's four nodes and Ossa's locker play their own takes. The two qa5 failures were check bugs (Torr's arrival greeting held the bark slot; Ossa's route), fixed for the final run |
| showcase_camera | **PASS after fixes** | 99/99 (final) | all eight colonists framed (captures judged by eye, see below), camera restored exactly (relative to the colonist), first person keeps the view with depth of field, switch off, Reduced Motion cuts, photo mode open/fly/15 m/ground/rows/F12 (1920×1080 + 3840×2160, opaque, upright, not black)/P and Esc exit/refusals/F8/container home |
| weather | **PASS** | 13/13 (qa1) | see `art/showcase_20261119/weather/README.md` "Native QA fixes"; contact sheets `qa/p1/weather/weather-sheet-1300.jpg`, `-2030.jpg` |
| interface | **PASS** | 22/22 (qa5) | Settings rows and defaults, persistence over a restart, Reset controls, Adaptive fade/Alt/prompt/window hold, Reduced Motion cut, photo HUD row, top centre ≤ 2. Not tested: Ctrl-drag of a moved window (step 5) |
| world_map | **PASS** | 29/29 (qa5) | on a COPY of Carl's save (original untouched, mtime 5 Oct 08:47): the old save continues, M/Esc, drag/wheel/keys, discovery + autosave, waystation respawn ring, knock-down cross, QA commands, Continue keeps discoveries, survey shown, declutter, new game no longer discovers the depot |

## Fixes made (game code)

| Symptom | Cause | Fix (file) |
| --- | --- | --- |
| Mira's shoulder shot showed only the player's back; Torr half hidden | sweep pulled the lens to ~1/3 of the shot but fallback only under 0.35 m | `minShotFraction` 0.75 → eye line (`Camera/ConversationCamera.cs`, `ConversationFraming.TooTight`) + test |
| NPC kept its back to the camera when spoken to from behind | NPCs never turned | `NpcAgent.faceSpeaker`: the visual turns to the player during the dialogue and back after (`NpcAgent.cs`) |
| Player's face/profile in the foreground of conversations | colonist kept his walking heading | `PlayerMotor.TalkYaw` (motor facing, eased ~0.3 s, cut under Reduced Motion), set by `ConversationCamera` while the dialogue is open + test |
| Player's back filled ~half the frame | shot 0.7 m behind the head | `Shot.Default` back 1.25 m, shoulder 0.75, player x 0.27; installer step `shot` |
| At Mira's counter the NPC hid behind the player's head; eye line 0.3 m from her face | no minimum separation | `minSeparation` 1.2 m → eye line; eye line stepped back to `eyeLineDistance` 1.3 m + test |
| Identity, Field Notes and compass crowded the lower-third dialogue | only log/hints/hotbar gave way | every panel incl. new `HudPanel.Compass` fades in the lower third (`HudPresentation.cs`, `CityHud.cs`) + test |
| Photo mode from first person (home) showed the inside of the colonist's face | Colonist row defaulted to Shown | starts hidden when opened from first person (`Camera/PhotoMode.cs`) |
| New game: "Machine depot marked on your map" walking out of the gate | radius rule for every site | `WorldMapDiscovery.PrimerAllows`: depot only from the primer's Depot step (`Map/WorldMapData.cs`, `WorldMap.cs`) + test |
| "Node 07 goods dock" on top of "Lattice Jack" | no declutter | `WorldMapMath.Declutter` (priority, selected place wins) + test |
| "Show on the sheet · T" with no target | always shown | hidden without a target (`WorldMapPanel.cs`) |
| Black void beyond the survey picture | viewport background #101717 | sand #7f6245 (`Resources/WorldMap/WorldMap.uss`) |
| NullReferenceException on quit | `WeatherDirector.OnDisable` refreshed a clock whose key light was gone | refresh only a live clock (`Weather/WeatherDirector.cs`) |
| Lower-third name plate printed the role twice ("Basic General · Basic General") on every opening line | opening nodes are titled with the colonist's role | `DialogueLayoutRule.NamePlateSubtitle` drops a topic that repeats the role (`HudPresentation.cs`, `CityHud.cs`) + test. Found by eye in the final captures, not by a check |

QA-only additions: `CombatFeelQa` (weak-point centres, last shot set, cone, droid audio, bolt counters), `FeralDroid`
voice counters, `DroidBolt.Flybys/Impacts`, `ShowcaseQa` `shotFraction`. Each package README has a "Native QA fixes" note.

## Conversation frames (judged by eye, final build)

`qa/final2/camera/run/conversation-*.png`: Mira (real walk-up), Vex (also walked up from his east and south sides),
Linn, Brann (20:30, Salvage), Tamsin (Field Supply), Ossa and Rell frame the NPC's face on its third, lit, with the
colonist's back and helmet about a third of the width; nothing clips the lens; the lower third sits below the faces and
the rest of the HUD is gone. Torr (1 m away at the mission slab) uses the eye line and now turns to face the player: a
centred close-up. Before/after sheets: `qa/previews/conv1.jpg`, `conv2.jpg` (first run) → `final2-a.jpg`, `final2-b.jpg`,
`final2-c.jpg` (odd-angle walk-ups).

## Performance (indicative)

`check_showcase_perf.py` on batch-qa5, two fresh runs, 8 s each after 3 s warm-up, uncapped, breezy unless stated.
Private display :5, the desktop shares the GPU.

| View | avg FPS (run 1 / 2) | p50 ms | p95 ms | p99 ms |
| --- | --- | --- | --- | --- |
| cam_hill 13:00 | 56.9 (57.1 / 56.7) | 17.33 | 19.42 | 21.08 |
| cam_hill 20:30 | 57.3 | 17.29 | 19.50 | 20.86 |
| cam_avenue 13:00 | 53.6 | 18.64 | 20.51 | 21.44 |
| cam_avenue 20:30 | 53.6 | 18.52 | 20.95 | 22.75 |
| cam_gate 13:00 | 84.0 | 11.90 | 13.58 | 14.59 |
| cam_gate 20:30 | 70.9 (62.4 / 79.3) | 12.95 | 24.83 | 34.08 |
| cam_bx_relay_knoll 13:00 (Berms review camera) | 305 | 3.01 | 4.72 | 7.67 |
| cam_bx_relay_knoll 20:30 | 278 | 3.34 | 5.38 | 8.12 |
| cam_hill 13:00, dust-front peak | 59.8 | 16.63 | 18.06 | 19.45 |
| cam_gate 13:00, peak | 86.9 | 11.44 | 13.01 | 14.62 |
| Berms follow view (caravan), peak / breezy | 77.0 / 68.3 | 12.80 / 14.54 | 15.32 / 17.53 | 17.99 / 20.24 |
| Follow at Vex → conversation (depth of field) | 49.8 → 74.3 | 19.84 → 13.40 | 22.74 → 15.08 | 24.51 → 16.13 |
| Follow at Tamsin → conversation (depth of field) | 70.5 → 62.1 | 14.10 → 16.02 | 15.62 → 17.75 | 16.84 → 19.01 |

Reading: the city views sit at 54–60 FPS, below the 60 FPS target, as they did on 5 October (A/B of that day: cam_hill
63, cam_avenue 59, cam_gate 96; AGENTS.md's 88–97 refers to gate-type views). A cost bisection
(`check_showcase_perf_bisect.py`, cam_hill/cam_avenue, toggling the `Ward weather` and `Night readability` roots) on
batch-qa5 and batch-showcase1 found no measurable cost from either (all variants 57–65 FPS, run-to-run spread ±4 FPS,
~12–13.6 M submitted triangles). The gate view is ~10 FPS below 5 October and was not bisected; the 20:30 gate run had
hitches up to 106 ms in run 1 only. The dust front does not cost frame time (the veil hides distance). The conversation
depth of field costs ~2 ms at Tamsin; at Vex the conversation shot is cheaper than the follow view it replaces. The
Berms review camera numbers (≈300 FPS) look at the knoll against the sky and say little about play there; use the follow
view. **Retracted:** the 254 FPS bowl walk from the first expansion run (camera thrown to pitch 80 by the pointer-lock
bug, looking at the sky). The 163–169 FPS from the fixed run is a real bowl walk but with 4× MSAA (that script's video
settings), not the TAA preset used here.

### Before/after against the last commit (the batch A/B)

`Builds/batch-baseline-head` is the game at commit f39dfa4b (no showcase work), built at 17:58 from a copy-on-write copy
of the project (`~/.local/state/ward-programme/showcase-20261119/baseline.sh`: Assets put back to HEAD, same Library,
same packages). `unity/tools/check_showcase_ab.py` then ran three fresh launches of each build, alternating (base,
showcase, showcase, base, base, showcase), 8 s per view after 3 s warm-up, uncapped, 1920×1080 High with TAA, the
showcase build pinned to its default weather. Report: `qa/ab-head/ab-table.json`.

| View | Before: avg FPS, p50 / p95 / p99 ms | After: avg FPS, p50 / p95 / p99 ms | p50 change |
| --- | --- | --- | --- |
| cam_hill 13:00 | 59.4, 16.69 / 17.97 / 19.01 | 59.6, 16.67 / 17.87 / 19.08 | −0.02 ms |
| cam_avenue 13:00 | 56.0, 17.85 / 19.33 / 20.31 | 56.1, 17.84 / 19.29 / 20.29 | −0.01 ms |
| cam_gate 13:00 | 88.0, 11.46 / 12.57 / 13.39 | 88.0, 11.40 / 12.68 / 13.64 | −0.06 ms |
| cam_hill 20:30 | 58.8, 16.83 / 18.31 / 19.30 | 58.4, 16.96 / 18.59 / 19.45 | +0.13 ms |
| cam_avenue 20:30 | 58.7, 16.86 / 18.23 / 19.77 | 58.6, 16.93 / 18.30 / 19.25 | +0.07 ms |
| cam_gate 20:30 | 86.2, 11.72 / 12.92 / 13.80 | 87.0, 11.62 / 12.78 / 13.68 | −0.10 ms |

Reading: the programme costs nothing measurable at these views (largest change +0.13 ms; the three runs of one build
spread by up to 0.35 ms). Submitted triangles are equal; SetPass calls rise at night (hill 525 → 581, gate 244 → 294)
without a frame-time effect. The hill and avenue views are at 56–60 FPS on **both** builds, so the shortfall against the
60 FPS target is not from today's work; it is where the 5 October build stood on this desktop today (5 October's own
runs: hill 63, avenue 59, gate 96). The gate view at 86–88 FPS on both builds is likewise unchanged by the programme.
The lower numbers in the table above (hill 57, avenue 54, gate 84) are the same build an hour earlier: desktop load
moves these views by more than the programme does. Not covered by this A/B: the Berms, a dust front, an open
conversation (see the table above for those on the showcase build alone).

## Open defects and limits (most serious first)

1. City views (hill, avenue) at 54–60 FPS, under the 60 FPS target. The A/B above shows the build of the last commit
   is the same on this desktop today, so this is not from the programme; it is still a gap against the target.
2. Nothing audible was verified: rifle character, droid identities, bolt fly-bys, wind/front beds, bark and dialogue
   voices need a listening pass (combat_audio README "Listening test").
3. Optic weak point: only a third of carefully aimed rifle shots at a stationary worker registered; it may feel small.
   No critical stagger was seen. Needs a human with a mouse.
4. Torr's conversation from the mission slab uses the eye line (a centred close-up rather than a shoulder shot).
5. Vex's ActorLookAt was not focused at the sampled moments of his barks (walkers' glance does work).
6. Night conversations depend on the night-readability pass; Brann at 20:30 reads well in the captures.
7. Not tested: Ctrl-drag of a moved window vs the lower third; the uinput real-mouse path; the schematic map fallback
   on the new sand background.

## Final run on batch-showcase-qa (16:56 build)

Regression: city loop PASS, range tutorial 10/10, rifle quest 38/38, home/journal 37/37, Field Supply 26/26, Berms
expansion 8/8. Packages re-run on it: camera 99/99, npc_life (see table), interface (see table). Edit Mode r5 389/389
(tree as built, before the NpcAgent facing change, which has no pure logic to test). Packages last run on batch-qa5
(combat_feel, combat_audio, weather on qa1, world_map) contain the same code for their areas apart from the WeatherDirector
quit fix and the NPC facing. Display :5 is left up if the night-readability agent is still running (see the final report).

## Re-run on the 17:32 build (name-plate fix)

A first rebuild at 17:26 was stopped by `ward-watchdog` after 88 s (256 MB of memory available, swap 27.3 GB: the desktop
had less headroom than earlier). `Builds/LinuxDevelopment` and `batch-showcase-qa` were checked untouched; Unity's
leftover shared-memory segment (1.6 GB) was freed and the second attempt built in 172 s. On that build: camera 99/99
(`qa/final3/camera`; name plates read "Basic General", "Salvage dealer · Salvage", "West Gate watch"), interface 22/22,
city loop PASS. The other checks were last run on the 16:56 build, which differs only by this one text rule.

## Gate names build (18:50, `Builds/batch-gates`, also `LinuxDevelopment`)

Carl decided on 19 Nov that the West Gate is the gate near the market (the Berms portal). The +X spawn arches became the
East Gate (`art/gate_names_20261119`; evidence `unity/evidence/gate-names/20261119/`). Every project file changed
between the 17:32 build and this one belongs to that pass (checked by modification time), so this build is the 17:32
showcase tree plus the rename. Run on it: `check_showcase_gate_names.py` 12/12, world map 29/29, interface 22/22, city
loop PASS, range tutorial 10/10; Edit Mode 393/393. Not re-run on it: camera, NPC life, combat feel, combat audio,
weather, rifle quest, home/journal, Field Supply, Berms expansion (last run on the 16:56 and 17:32 builds; the pass
adds four static plates and changes text only). Captures judged by eye: `lookbook-r2/sheet-h13.00.jpg` and
`sheet-h20.50.jpg` (no old lettering from any player view, plates readable at 20:30), `qa/gates/gate_names/run/`.
After the last test run Unity dropped `SENTIS_ANALYTICS_ENABLED` from the Standalone scripting defines in
`ProjectSettings.asset`; it was put back so the tree matches what was built.

## Playtest build (19:15, `Builds/batch-playtest1119`, also `LinuxDevelopment`)

Built from the tree committed as 982db591 (the same tree as the 18:50 build, rebuilt at Carl's request). Run on it:
gate names 12/12, camera 99/99, city loop PASS, rifle quest 38/38 (`qa/playtest/`, `qa/regression-playtest/`). The
other checks were last run on the 16:56, 17:32 and 18:50 builds.
