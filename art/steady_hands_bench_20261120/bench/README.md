# bench: the hands-on assembly system

Steady Hands bench programme, `bench` agent, 20 November 2026. Brief: `../briefs/bench.md`. Design: `../DESIGN.md`.
Contract with the crafting system: `../CONTRACT.md` section B, as built by `craft` (`../craft/README.md`).

Status: **Milestone 2; real-art selftest 17/17 on 21 Nov (install-bench-a6)**. All eight stages have actions and the whole job is playable in greybox by mouse and by
keyboard alone; the stand-ins carry the art's ids, places are bound to the art's seat marks, and `BindFamily` has been
tried on the four real families that are in `Art/Bench`. One native run exists (the coordinator's, on the 18:05 slice
build): it found a mirrored turn, fixed since. Nobody has seen stages 2 to 5 in the player.

Results (20 Nov 2026, evidence in `unity/evidence/steady_hands/20261120/`):

- `install,verify,bindcheck,selftest` (`install-bench-m2e1.log`, 19:37): rc 0, scene file unchanged by a second install.
- `bench/verify.json`: pass. 81 steps (67 design rows + 14 recovery steps), 208 actions in all eight stages; 159 parts,
  96 places, 17 mechanisms, 10 `cam_bench_*` cameras; every reference of every action resolves; 17 fault-to-recovery
  paths played on paper; the 74 sound events the job asks for all have clips.
- `bench/selftest.json`: 17 of 17 scenarios. The bot plays the whole job in 189 actions: 189 s of game time by mouse
  (Fine, 0.98), 280 s by keyboard alone (Fine, 0.96). A person is far slower: DESIGN gives 17 minutes. The other
  scenarios: the slice both ways, leaving and returning (twice), and eleven mistakes with their ways back.
- `bench/bind-servo.json`, `bind-tools.json`, `bind-pistol.json`, `bind-fixtures.json`: each real family binds with
  no unresolved node, empty or clip (see "The seam").
- Edit Mode `editmode-bench-m2.xml` (19:32): 503 of 504. The one failure was a slip in my own test (it tried to reach a
  fault inside a recovery step on a clean run); fixed. **Not rerun since**: the table was then aligned with the
  exported grip and materials families, and the suite is held back while the slice 2 build waits for memory.
- Native: `unity/tools/check_steady_hands_bench.py` was run by the coordinator on `batch-sh-slice1` (mouse, to
  `s0.salvage`). Not run on anything newer. Keyboard mode, `BENCH_REAL=1` and `BENCH_FULL=1` have never run.

## What exists

| Piece | Where |
|---|---|
| Step table (the editable source; 67 design rows + 14 recovery steps, ids as in DESIGN section 7) | `../data/steps.json`; `bench/check_steps.py` checks it against the stand-ins and the layout without Unity |
| Recipe asset generated from it | `Data/Assembly/assembly_grip_stabilised_pistol.asset` (`AssemblyRecipe`, `sourceHash`) |
| Job model, pure C# | `Scripts/Assembly/AssemblyJob.cs` (graph, faults, recoveries, quality, blob v2, `Leave`, `Grant`) |
| Parts, markers, mechanisms | `AssemblyPart.cs`, `AssemblyMarker.cs` (Place, Mark, Path, Zone), `AssemblyParam.cs` |
| The bench as a set of parts | `AssemblyBench.cs` (index, as-found reset, replay of a job onto the scene, picking, clamps, lamps, wipe masks), `AssemblyWipeMask.cs` |
| The seven verbs | `AssemblyVerbs.cs`: `SeatVerb`, `TurnVerb`, `PathVerb`, `WindowVerb`, `WipeVerb`, `PointVerb`, `FlickVerb` |
| The sitting | `AssemblySession.cs` (state machine, hand, focus ring, hints, hand-off), `AssemblyInput.cs` |
| Camera | `AssemblyCameraRig.cs` (take-over with a restore ledger, shots, orbit, zoom, depth of field), `AssemblyCameraBlendOut.cs` (the way back to the follow camera) |
| Feedback without interface | `AssemblyFeedback.cs` (rim, glint, flash, shudder, ghost, path line) |
| Sound and voice | `AssemblyAudio.cs`, `BenchVoice.cs`, `AssemblyAudioTable.cs` -> `Data/Assembly/AssemblyAudioTable.asset` |
| The little UI there is | `AssemblyHud.cs`, `Data/Assembly/AssemblyHud.uss` |
| Tuning | `AssemblySettings.cs` -> `Data/Assembly/AssemblySettings.asset` |
| The one contact point with crafting | `AssemblyCraftLink.cs` |
| QA | `AssemblyQa.cs` (`assembly` block in snapshot.json, `dev.assembly.*`), `AssemblyBot.cs` (plays the job with made-up input) |
| Greybox families and layout | `bench/make_greybox.py` -> `Data/Assembly/Greybox/*.parts.json`, `../data/layout.json` |
| Builder | `Editor/AssemblyKitBuilder.cs` |
| Installer | `Editor/AssemblyBenchInstall20261120.cs` (`recipe`, `audio`, `settings`, `prefab`, `scene`, `install`, `verify`, `selftest [--only TEXT]`, `bindcheck [--family NAME]`, `rollback`) |
| Bench prefab and scene root | `Data/Assembly/SteadyHandsBench.prefab`; scene root **Steady Hands bench** at the Salvage workbench's transform |
| Input map | `bench/apply_input.py` (`--check`, `--remove`) adds the `Bench` map to `Data/Controls.inputactions` |
| Tests | `Tests/Editor/AssemblyJobTests.cs` (10), `Tests/Editor/AssemblyBenchTests.cs` (14) |
| Recorded scene edits | `bench/record.json` (InteriorLighting root, landmark `bench_steady_hands`) |
| Native check | `unity/tools/check_steady_hands_bench.py` (mouse; `BENCH_MODE=keys`, `BENCH_REAL=1`, `BENCH_FULL=1`, `BENCH_STOP=sN`, `BENCH_TURN_SIGN=-1`) |

Paths without a prefix are under `unity/AthenHill/Assets/AthenHill/`.

Small additive edits in shared files: `GameSession.cs` (`CityState.Assembly`, `OpenAssembly`, `ActiveAssemblyRecipe`, the
`UseStation` hook for craft), `GameInput.cs` (`Bench` map: `BenchEnabled`, `BenchAction`, `SetBench`), `FollowCamera.cs`
(writes nothing while the bench camera is on; the colonist is drawn as a shadow only), `Camera/CinematicCamera.cs`
(`BenchActive`), `CityHud.cs` (no shade or modal in Assembly, HUD stays enabled, keys never press HUD buttons),
`DevBridgeCommands.cs` (`dev.assembly.*`, `dev.craft.*`), `NativeQa.cs` (`assembly` block, craft's `bench` block),
`Data/Controls.inputactions` (the `Bench` map).

## How it works

- **The scene is a function of the job.** Every action leaves effects (where its part ends up, the mechanism it drove,
  listed effects such as `pistol.wrap>fixtures.partsmat/seat_pistol_wrap` or `tools.roll_unroll=1`). `AssemblyBench.Rebuild(job)` puts the bench
  as found and replays every finished action in table order, so the saved blob holds no part positions and a layout
  or art change cannot break a save.
- **A step is a row of the design; an action is one thing the hands do.** A step holds one or more actions
  (`s1.screw_b` = oil, tap, turn, dish). Actions run in order unless the step is `free` (the two scales, the two
  screws) or gives `after`.
- **What the pointer is on decides what happens**, not a highlighted target: nothing held and a press on a part picks
  it up (off its parent along its own axis first, and not at all while something holds it); a press on a tool takes
  it; with a tool in hand a press on a part or mark starts the open action for that tool there; a press on a seated
  part whose turn has not come refuses with a shudder and a glint on what holds it; a press on a part of the pistol
  when the job wants the pistol handled picks the pistol up.
- **Seat**: the part rides a critically damped spring whose frequency is its mass class, leans into its motion, turns
  with the wheel or Q / E, and is drawn in when the pointer is over the socket or the way into it, it is within
  tolerance and it is square to its key (`symmetry`, `tol_deg`). The non-yaw part of the socket's orientation blends in
  by itself near the socket; the player supplies the heading.
- **Turn**: a circle round where the turn began, the wheel, or a held key. `gain` is part turns per input turn; pitch
  and tool vibration follow resistance. `stop` turns end inside a band (the vise: snug, not over-tight).
- **Window**: `strike` raises the tool while held and lands it on release, height being force; `hold` raises a value
  while held and judges the release. **Point**: one click on a mark; the `aim` form is the test card, with the muzzle
  wandering by the weapon's handling numbers from the crafting system. **Flick**: reversals of the hand while
  carrying, or a held key. **Path**: the furthest point of the line the pointer is on; too fast tears where the action
  says so (the line is judged by how far the pointer strays from it). **Wipe**: below.
- **Faults never end the job.** They cost quality (`penalty`), may start a recovery step (`recovery`, `after`), and
  may change the bench (`effects`: the spring lands on the mat). A recovery can stand in for actions of the step it
  recovers (`replaces`).
- **Camera: a take-over with a restore ledger, as photo mode does**, not an overlay like the conversation camera. The
  bench needs the whole pose, the lens and its own depth of field for minutes; an overlay would have to be recomposed
  each frame over a follow pose that means nothing at the bench. `FollowCamera` returns early while
  `CinematicCamera.BenchActive`. Shots are the `cam_bench_*` cameras under the bench root.
- **Hints** (DESIGN section 8): 10 s the next useful thing glints, 25 s Brann says a short line, 45 s or H a ghost of
  the part at its socket or the tool's path for 2 s. They never cost quality. The next action follows the hand: with a
  part picked up, what that part can do is what is hinted, shot and played.
- **Ids are the art's** (SEAM.md). A place is `<part>/<mark>` when the art has a seat mark for it
  (`fixtures.vise/seat_work`), `...#variant` for a second pose at the same mark (the servo, the sheets, the strap and
  the core in the vise), and `place.*` when the art has none. The stand-ins are generated with the same ids, marks,
  paths, zones and params, so a family is swapped for its GLB without touching the step table.
- **Shots are what they frame.** Each `cam_bench_*` is worked out at install from ids (`"frames"`), a pitch, a yaw
  and a lens, so it holds when the fixtures move; `wide` is the whole worktop with its front edge at the bottom of the
  picture, `work` the rubber work surface, the rest are close. The job asks for a shot per stage, step or action, and
  the session widens it (`work`, then `wide`) when it would not show the tool still to be taken, the part still to
  be picked up, or the place the work is done.
- **Fitted parts go with what carries them.** A part seated on another, or put on a place another part owns (the
  gimbal pressed into the core, a screw started in a plate, the sheets stacked), is handled with that part unless the
  stage still has work for it; a press over a held part and its holder takes the holder.
- **Wipe** writes a 16 x 16 mask per zone that the bench keeps (`AssemblyBench.Wipe(zoneId)`: cells, coverage, a
  texture, `WipeChanged`). The wipe shader is the integration pass's. A wipe finishes by itself at 97 %; let go
  earlier with enough done and it counts, and the step's precision remembers what was missed.
- **Window** has two more forms: `sustain` (the press: pump to the band and keep it there while the work goes on) and
  `wait` (the cure: time passes by itself; lifting the part early is a fault and starts it again).
- **Faults that show later.** `when: "poor:STEP"` raises a fault in place of finishing when an earlier step was done
  below 0.8 (the rotor grinds after a careless brush, the tester stays dark over a cold joint, the damper keeps
  swinging over a pinched lead, a proud pin stops the screws); `blocks` holds the action until its recovery is done.
  Others: `under` (a hold let go short), `fast` (a turn driven too fast), `misaligned` (offered the wrong way up),
  `wrong:PART` (the press landed on that part instead: the lead pulled by its wire).

## The seam for the integration pass

`AssemblyKitBuilder.BindFamily(GameObject familyRoot, JObject partsFile, ...)` binds a family to components and runs
the same on an unpacked GLB instance and on a stand-in. `BuildBench(BenchSpec)` takes `sources[family] = "greybox"` or
a GLB path; the installer's `prefab` step takes `--real pistol,servo,...` and looks in
`Assets/AthenHill/Art/Bench/<Family>/<family>.glb` with `<family>.parts.json` beside it. `bindcheck` does that for one
family at a time on a scratch object, saves nothing, and writes `bench/bind-<family>.json`.

**Tried on the real fixtures, tools, pistol and servo (19:37).** All four bind: every node, clear pose, mark, path and
zone the files name is in the model, and every `*_param` clip moves its rig. What the real models needed that the
stand-ins did not, all handled in the builder:

1. The models are nested (a part is a child of its parent part, or of a bone of that part's rig) and the stand-ins are
   flat. A part is only re-parented when the model does not already have it under its parent.
2. A family's clips are bound from the model's root, and parts are moved about the bench. Each clip is re-bound from
   its rig node (`params[].node`) and kept as `Data/Assembly/Clips/<family>__<clip>.anim` (in memory for `bindcheck`).
   Several rigs per family work (`servo_rig`, `servo_gimbal_rig`). The importer's `Animation` component is removed so
   nothing plays by itself.
3. `tools.roll` is a skinned mesh whose node does not move its bones: the part is bound to its rig node
   `tools_roll_rig`, and its pick box is baked from the shape it has as found (rolled).
4. The roll's tools do not ride its bones, so they are hidden while it is rolled (layout `params`, any source).
5. A param starts at its `rest` (`params[].rest` or `param_rest`): the gimbal's tilts at 0.5.
6. Parts flagged `fixed`, and "fixed sub-part" notes, bind as fixtures. `absent_at_start` parts start gone.
7. A zone is a box whose empty's scale is its half extents; the wipe runs across its thinnest side. The kit's marks
   carry no size, so a mark is picked within 6 mm.
8. Seat marks: a point gives the position and `layout.json` the rotation in the owner's space; `"pose": true` gives
   both. With the real fixtures 39 places sit on marks, 7 of them pose marks (`fixtures.workmat/seat_pistol`,
   `seat_grip`, `fixtures.vise/seat_work`, `fixtures.cradle/seat_frame`, `fixtures.pad/seat_cell`, the two card
   seats). A `clear_<x>` mark beside `seat_<x>` gives the way in (the grip core has them).

**Not yet in `Art/Bench`**: grip and materials (both exported to `../grip/export`, `../materials/export` after 18:48;
the stand-ins and the step table were aligned with their parts.json at 19:35: same ids, parents, marks and paths).

**What the step table uses that the art does not have yet.** A real family is filled with the stand-in parts of the
same ids for whatever its model lacks (`BenchSpec.fill`, on by default; laid out in bench space as the stand-in
family is; `bind-<family>.json` -> `standInsForWhatTheModelLacks`), so fixtures and tools can go to their GLBs now and
the job stays playable. With that, `bindcheck` at 19:44 leaves no id of the table unresolved on any of the four
families. The stand-ins still in use:

- fixtures: `fixtures.tray` (seats `seat_servo`, `seat_alloy`, `seat_vial`), `fixtures.bin` (`seat_scrap`),
  `fixtures.jar` (`seat_swirl`), `fixtures.press` (`seat_mould`) with `fixtures.press_lever` (part and param) and
  `fixtures.press_vents` (a lamp), `fixtures.mouldrack`, `fixtures.mould_tang` (zone `cavity`), `fixtures.lamp` with
  `fixtures.lamp_head` (a lamp) and param `fixtures.lamp_arm`, `fixtures.tester` with `fixtures.tester_probes`
  (tag `tool:probe`) and `fixtures.tester_lamp`, `fixtures.schematic` with params `fixtures.schematic_s0..s7`,
  `fixtures.holster`.
- tools: `tools.strippers`, `tools.wirebrush` (tag `tool:brush`), `tools.pick`, `tools.scribe` (in the roll, seats
  `tools.roll/seat_<name>`), `tools.file_flat` (`tool:file`), `tools.file_round`, `tools.snips`, `tools.drill`,
  `tools.iron` (`tool:solder`), `tools.applicator`, `tools.thirdhand`.
- materials: nothing (the five `swarf_*` parts are not used by the table). The raw core, flash and sprue of
  `materials/PARTS.md` section 5 were not exported; the table uses `grip.core` from the press on.

**Places with no mark** (their numbers are in `layout.json`, in the owner's space, and want measuring against the
art): `place.entry.pistol`, `.roll`, `.servo`, `.sheet_a`, `.sheet_b`, `.vial` (where things lie when the bench is
taken); `place.roll` and `place.rest.<tool>` (these take the part's own rest pose in its model, so they need
nothing); `place.holster`; `place.bench.stray`; `place.thirdhand`; on the work mat `place.mat.sheet`, `.plate_l`,
`.plate_r`, `.strap`, `.spare`, `.retainer`; on parts `place.sheet.stack`, `place.sheet.template`,
`place.plate.stack`, `place.plate.template`, `place.servo.bobbin`, `place.mould.charge`, `place.mould.core`,
`place.press.pour`. `verify.json` lists them (`placesWithNoMark`).

**Numbers that belong to the stand-ins** and want setting from the art: the vise closing values in `steps.json`
(`to`: 0.6 on the pistol, 0.22 on the servo, 0.94 on the sheets, 0.97 on the strap, 0.69 pressing the gimbal home;
the jaw gap is 90 x (1 - value) mm) and each vise place's `hold_above`; the rotation of every place a real part lies
on that is not a pose mark; `fixtures.vise_screw` turns about its `__clear` direction when it has one, else its
local up (the real one has no clip: the bench spins it).

**Step cross-check.** `verify.json` -> `stepCrossCheck` lists where the table and a part's own `steps` list disagree
(warnings only). Most are the table using a part in more steps than its modeller listed.

## Running it

    python3 art/steady_hands_bench_20261120/bench/make_greybox.py [--check | --report]   # stand-ins + layout; --report compares ids with the exports
    python3 art/steady_hands_bench_20261120/bench/check_steps.py                         # the step table against them, no Unity
    python3 art/steady_hands_bench_20261120/bench/apply_input.py                         # the Bench input map
    SH/seq.sh install bench AthenHill.Editor.AssemblyBenchInstall20261120.RunBatch install,verify,selftest
    SH/seq.sh install bench AthenHill.Editor.AssemblyBenchInstall20261120.RunBatch selftest --only "stage 5"
    SH/seq.sh install bench AthenHill.Editor.AssemblyBenchInstall20261120.RunBatch bindcheck [--family servo]
    SH/native_check.sh bench_slice unity/tools/check_steady_hands_bench.py ATHEN_EXE=<build>/AthenHill.x86_64 [BENCH_MODE=keys] [BENCH_FULL=1] [BENCH_REAL=1] [BENCH_STOP=s1]

`selftest` plays the job with `AssemblyBot` on a plain copy of the prefab: the whole job by mouse and by keyboard,
the slice (stages 2 to 5 granted) both ways, leaving and returning, and the mistakes. About three and a half minutes
of Unity time for all 17; `--only` runs the scenarios whose name contains the text and writes
`selftest-partial.json`. The bot's mouse form makes its circles in screen pixels through the shot's camera.

Dev bridge: `dev.assembly.open {force?, fresh?}`, `close`, `complete {step, key?, precision?}`, `fault {step, kind}`,
`grant {stages[], precision?}`, `finish {score? | quality?}`, `abandon`, `shot {shot}` (holds that shot until an
action is finished; `auto` lets go), `hint {level?}`. `force: true` opens a detached QA job when the crafting system
would refuse. The `assembly` block of snapshot.json gives, per open action, where on the screen it is done, the
path or zone corners, what is held and whether it is the wrong way up, the shots, and each wipe's coverage.

Rollback: `--steps rollback` removes the scene root, its InteriorLighting entry and the landmark;
`apply_input.py --remove` takes the input map out. Assets under `Data/Assembly` and the code stay. Never exercised.

## Tuning table (`Data/Assembly/AssemblySettings.asset`; per-action numbers are in `steps.json`)

| Setting | Start | What it does |
|---|---|---|
| `springTiny / Light / Medium / Heavy` | 34 / 26 / 17 / 10 rad/s | Carry spring frequency by mass class. 90 % of a move takes 0.11 / 0.15 / 0.23 / 0.39 s. Lower = heavier feel |
| `carryLift` | 0.085 m | Height a carried object rides above the work surface |
| `tiltPerSpeed`, `tiltMax` | 10 deg per m/s, 14 deg | Lean into the motion |
| `yawPerNotch`, `yawPerSecond`, `yawFollow` | 15 deg, 150 deg/s, 16 /s | Turning a held part: wheel, Q / E, and how fast it settles |
| `tapSeconds`, `tapPixels` | 0.22 s, 9 px | A press shorter and stiller than this leaves the object in the hand; longer is a drag that places on release |
| `pullInSeconds`, `approachSeconds` | 0.075 s, 0.09 s | The seat: reach the way in, then go home (DESIGN: 60 to 90 ms) |
| `cameraNudgeMm`, `rimFlashSeconds` | 2.5 mm, 0.22 s | Seat feedback (no nudge under Reduced Motion) |
| `fumbleSpeed` | 0.9 m/s | Hand speed at a seat above which the action's `rolled_off` fault fires |
| `shudderMm`, `shudderSeconds` | 1.6 mm, 0.28 s | A part that refuses |
| `turnsPerNotch`, `keyTurnsPerSecond` | 0.125, 1.15 | Turn input by wheel and by held key (before the action's `gain`) |
| `circleMinRadiusMm` | 7 mm | The mouse circle only counts beyond this from the centre |
| `stopSettleSeconds` | 0.3 s | Rest inside the band for a `stop` turn to count |
| `pitchLoose`, `pitchTight` | 0.86, 1.28 | (reserved; loops use each event's own pitch range from the audio manifest) |
| `camOutSpeed` | 4.5 turns/s | A stiff screw (gain under 0.6) turned faster throws the bit out |
| `buzzMm` | 0.5 mm | Tool vibration at full resistance |
| `strikeRaiseSeconds`, `strikeLift` | 0.85 s, 0.11 m | Strike: time to full height, and the height |
| `overMargin` | 0.06 | Hold: how far past the window is a fault while still held |
| `pointTolMm` | 6 mm | Point tolerance when the action gives none (ignored beyond three times this) |
| `aimSwayScale`, `aimSwayPeriod` | 1, 2.6 s | Test card: handling degrees to wander, and the figure of eight's period |
| `flickSpeed`, `flickReversals`, `flickWindow`, `flickHoldSeconds` | 0.45 m/s, 4, 1.5 s, 0.7 s | The shake, mouse and keyboard forms |
| `pathTolMm`, `pathKeyPace` | 9 mm, 0.05 m/s | Following a line |
| `wipeRadiusMm`, `wipeDone`, `wipeFull` | 14 mm, 0.9, 0.97 | Brush radius (at least 0.3 of a small zone); the share that counts when the action gives no `lo`; the share at which a wipe finishes by itself |
| `poorPrecision` | 0.8 | A step done below this is "done badly" where a later step checks it |
| `sustainDrift`, `sustainVoidSeconds` | 0.55, 2 s | The press: how fast the value falls when let go (share of the pump rate), and time out of the band that leaves a void |
| `hintGlint`, `hintVoice`, `hintGhost`, `ghostSeconds` | 10, 25, 45, 2 s | Idle hints |
| `enterSeconds`, `shotSeconds` | 0.8, 0.6 s | Camera blends (cuts under Reduced Motion) |
| `orbitYaw`, `orbitPitch`, `orbitPerPixel`, `orbitPerSecond` | 25, 12 deg, 0.14 deg/px, 45 deg/s | Looking round |
| `zoomPerNotch`, `zoomPerSecond`, `zoomFollow`, `closeDistance` | 0.14, 0.9, 9, 0.34 m | Moving in on the work |
| `aperture`, `depthOfField` | f/4.5, on | Depth of field (off under Reduced Motion) |
| `abandonHoldSeconds` | 2 s | Hold Backspace (or the on-screen control) to pack the job in |
| `maxVoices`, `sameEventWindow`, `volume` | 8, 0.04 s, 0.74 | Sound: voice limit, repeat guard, bus gain (0.74 keeps the audio package's worst pile-up under full scale) |

Per action in `steps.json`: `turns`, `gain` (resistance), `lo` / `hi` (window, stop band, pace), `rate`, `count`,
`tolMm` / `tolDeg`, `weight` (in quality), fault `penalty` and `after`. Quality thresholds: `quality.rough` 0.55,
`quality.fine` 0.85, `faultPenalty` 0.02, `maxPenalty` 0.5, `replacedPrecision` 0.35.

## Voice triggers bound

`BenchVoice` looks a line up by trigger in `audio/lines.json` (the audio agent's trigger names are used as they are).
Raised by the session: `session.enter.first`, `session.enter.resume`, `session.leave.unfinished`, `session.abandon`,
`stage.start:N`, `step.start:ID` (when a step becomes available), `step.done:ID` and `step.done:ID:Quality`,
`step.fault_first:ID`, `fault.first:KIND`, `step.fault:ID`, `hint.idle25:a|b|c`.

All 32 of Brann's lines now have a trigger the job raises: take_bench, come_back, step_away, abandon, stage1 to
stage7, stuck_screw, cracked_tang, fault_camout, fault_stripped (over-torque in `s5.torque` and `s6.screws`),
fault_short_lead (`s2.leads`, `s3.trim`), fault_cold_joint (a joint let go cold in `s3.tin` or `s3.loop`, and the
tester in `s3.test`), fault_overbend (`s3.strap`), fault_flew_off (`s1.housing`, `s2.circlip`, `s5.rotor`),
the three hints, spin_good and spin_bad (`s3.spin`), press (`s4.press` becoming available), damper_good and
damper_bad (`s5.damp`), card_before, card_after_rough / standard / fine, hand_over. The selftest asserts the
triggers; nobody has heard the lines in the game. Ossa's four range lines belong to `craft`.

## Departures from the brief, DESIGN.md and CONTRACT.md

1. **Steps hold actions.** DESIGN's rows name several archetypes ("Seat, Turn (vise)"); a row is a step and each
   archetype in it an action with its own key. Save, QA and audio use `step:key`.
2. **Carry is press-and-hold or click-and-carry.** DESIGN section 5 says "hold to carry, release to place". A short
   still press leaves the object in the hand (the next press places it); a drag places on release. Both are needed:
   aiming the pistol at the card and shaking it are done while carrying.
3. **Space: tap or hold.** Tap picks up, puts down or uses; hold is the tool action (and the keyboard shake).
4. **Flip changes the screwdriver's bit** (middle button / R with it in the hand): the bit in it changes places with the
   one in the bit block (SEAM.md section 3: the bit seated in the screwdriver is its setting).
5. **Esc in the last stage.** `s7.leave` has `onLeave`: stepping back when it is the only step left finishes the job.
6. **No pause from the bench.** Esc steps back (job kept), so the Paused branch of DESIGN's state chart is not reachable
   from the bench.
7. **Optional steps lapse with their stage** (`s0.shake_before` is not offered in stage 1).
8. **`s6.slide` starts by clamping the frame again** (two extra actions): DESIGN has no row for getting the frame from
   the cradle stand back into the vise, and `s6.cell` says "open the vise".
9. **`s1.inspect` turns the vise on its swivel** until the crack faces the player (the frame is clamped; DESIGN says
   "turn the bare frame over").
10. **`s1.screw_b` tap uses the screwdriver's handle** as a strike on the screw; `s1.pin` stands the punch on the pin
    first (a Seat of the tool), then strikes with the mallet.
11. **The backstrap housing does not go back on in stage 6** (the grip takes its place); it is binned in `s6.cell`.
12. **A rolled-off part lands on the bench**, not in a floor tray (the floor is not in the bench camera's view).
13. **Abandon** passes the crafting system one entry per reserved unit of every item a finished step `spends`
    (`s2.pry` the servo, `s3.cut` the alloy, `s4.charge` the nanites); see 26.
14. **A detached QA job** (`dev.assembly.open force`) exists so the slice can be played whatever the crafting state is.
15. **Leaving the bench blends back** to the follow camera over the time the way in takes (a cut under Reduced
    Motion). Written, never seen.
16. **Brann's caption uses the existing bark strip**; the stage line of AssemblyHud shows only for a detached job (a real
    job's stage is in Field Notes through `ReportAssemblyStage`, which is why Field Notes stays on screen).

Milestone 2:

17. **The grip is turned over on the mat** four times in stage 5 (`over` and `back` actions): it lies on a side, the
    plates and their screws go on from above, and DESIGN's rows do not say how the far side is reached.
18. **The rotor and its retaining ring come out in `s4.pressfit`**, before the gimbal is pressed in. DESIGN puts them
    back in `s5.rotor` without a row that takes them out.
19. **`s2.board` follows `s2.leads`** (the leads run to the board's plug), and `s2.winding` ends by opening the vise and
    binning the carcass, so the vise is free for the sheets.
20. **One row, simpler hands**: `s3.punch` is a click of the punch on each mark (no mallet); `s3.trim` cuts at marks on
    the leads (the bench rule is not used); `s2.dust` brushes the lid and the near side; `s5.loop` is the tuck alone,
    ending with the clips' snap; `s5.torque` drives and torques each side's two screws in turn (no cross pattern
    across the grip).
21. **The core is `grip.core` from the press on.** The exported materials family has no raw core, flash or sprue;
    `s4.flash` knocks and eases the core itself.
22. **The plates and strap are the materials family's parts all the way** (`materials.sheet_a_plate`,
    `sheet_b_plate`, `strap_bent_1`, `strap_bent`), seated on `grip.core`'s seat marks, as the grip family was built.
23. **The two new grip screws lie in the magnetic dish** (slots 10 and 11), not in a jar of Brann's, and take the
    cross bit: the old grip screws are slotted, the servo's and the new ones cross, so the bit is changed twice.
24. **`s6.cell` has a `clear` action**: the old housing goes in the scrap bin and its spring, the scales, the wrap, the
    spare strip, the case lid and the circlip go with it (the coordinator's ruling: nothing left on the mat).
25. **The wide shot looks down 54 degrees**, not DESIGN's 40, so the worktop fills the picture with its front edge at
    the bottom (the coordinator's ruling from the first native frames).
26. **Abandon reports spent units by tag** against what the ticket reserved (`component:servo`, `scrap_alloy`,
    `nanite:tier1`).
27. **The first-use legend goes when the first action is done** (it had stayed 30 seconds). H brings it back for 6.

21 November (real art, by the agent that took over):

28. **A real part whose parent is in another family stands in that parent's own frame** (`Settle`): the materials family's
    leads and loop ("in the cradle frame D, identity transform") and the core's flash and sprue ("in the frame of
    grip.core") had been kept where their family root put them, so the gimbal's leads hung 20 mm through the work mat.
29. **The pistol lies on the work mat turned 180 degrees about the mat's up from the art's pose mark** (`layout.json` place
    `fixtures.workmat/seat_pistol`, `turn: 180`, applied by the builder to the pose): as modelled its cell and latch face
    the back of the bench, out of every shot (s0.cell, s6.cell). Asked of model-bench; drop the turn when the mark changes.
30. **The gimbal lies on the mat turned half round** (`fixtures.workmat/seat_small` rot 0, 180, 0) so its leads, which leave
    frame D towards -Z, lie towards the player for the stage 3 lead work. It is a point mark of symmetry 0, so in play the
    part keeps the heading the hand gave it; the rotation holds on replay and for the sight check.
31. **Picking**: a hold point's 12 mm catch no longer takes a press off another part whose own surface is under the pointer
    (such a hit scores 3 cm further away), and a part fitted in the one under the pointer that the job wants now, while the
    job has nothing for the carrier (the rotor in the cradle), is taken instead within 3 cm of depth.
32. **`s2.pry:clip_3` uses the `over` shot and `s6.plug:plug` a new side shot `vise_r`** (layout shots `vise_l`, `vise_r`).
    Putting `s1.bind`, `s6.plug:route` and `s6.pin` on `vise_r` was tried and taken back: on the stand-in bench the cutters
    and the pin could then not be taken from that shot, and the route was still behind the core.
33. **The lead pulled by its wire cannot be done by hand on the real pistol**: at `s1.lead` the wire lies under the housing
    and the pin and no point of it comes under the pointer (61 surface points tried). The selftest scenario raises the
    fault by the dev path there and says so (`note` in selftest.json). Not a model defect: the design's order puts s1.lead
    before the housing comes off.

34. **The test card says what to do** (Carl lost at s0.card_before, 21 Nov): printed rings on both cards, the pistol and aim
    dot come up within 30 cm of the card (was about 5), what stands between the card shot's eye and the card is not drawn
    while the pistol is up, and an **action line** (AssemblyHud, top left) shows the action's `line` from `steps.json`, or
    the tutor's text through `AssemblySession.LineFor`, with what is left of a counted action. One line on screen.
35. **`s1.bind` is two actions** (`snip_a` in the vise shot, `snip_b` in the side shot `vise_r`), so each wire twist is
    in sight; `s6.pin` start and taps use the `work` shot.
36. **A Path may look further ahead** (`ahead` in metres; the peel 0.12): a stretch of line round the back of its part is
    stepped over where the line shows again, and such a step is not counted as speed (no tear). The sight check passes a
    line that starts and ends in sight with every hidden stretch under its look-ahead (`paths[].followable`).
37. **The hand drill turns its crank** (continuous params with no clip turn their bone about its +Z; the spindle follows
    at -ratio). `AssemblySession.Refused` (kind, part, other) and `LineFor` are the tutor's hooks; `BenchVoice.Busy` and
    `SayLine` too.

38. **Lines round the back turn the work**: a Path with `swivel` (the peel, the lead route) turns the vise on its swivel to
    keep the stretch being followed facing the eye, finishes by itself in its last 3 cm, and swings the vise back square.
39. **A tool to be taken from the open roll is taken in the `roll` shot** (over the toolkit), whatever the work shot shows;
    the camera goes back to the work once it is in hand.
40. **The servo is turned 180 degrees in the vise** from the art's `seat_servo` (layout `turn`), so its seam clips face the
    player; `s3.bath` uses the `tester` shot; the sight check sees through glass fixtures (the solvent jar).
41. **The core is cleaned by the job**: the file bares the parting line (`~grip.core/flash`), the round file the pocket
    (`~grip.core/pocket`), the quench washes off the release powder (`~grip.core/skin`).

Sight on the installed (real) bench, 21 Nov 08:47: 14 of 201 actions have a point hidden in their shot (30 at the start of
the day). Left: the peel (`s1.tape`, the wrap's far side, 15 of 36 points; a single stretch round the back is 94 mm, past
the Path verb's 6 cm look-ahead), `s1.bind` wire b's twist (only `vise_r` sees it), `s1.pin:taps` and `s6.pin.r`, `s2.dust:side`,
`s2.pry` clips 1 and 2 (no shot sees them), the two strip pulls' clear poses (13 mm into the mat), `s4.pressfit.r` (the pocket
shoulder under the cradle), `s6.plug:route` and `s6.pin` (behind the left plate), `s6.cell:clear` (the stand-in bin's floor).
`sight.json` now gives `seenFrom` (the shots that would show a hidden point) and `paths` (hidden stretches along each line).

## Mistakes of DESIGN section 7: what is built

Built with a way back: wrong bit; seized screw forced (pliers); bent pin (anvil); spring jumps; lead pulled by its
wire (re-strip in stage 3); vial rolls off; circlip flies; lead cut short (splice); careless brush grinds (brush
again); cold joint at the tester (reflow); strip cracks on the second over-bend (the spare); gimbal pressed past
flush (mend the lug); retaining ring flies; pinched lead at the damper; grip lifted from under the lamp (the wait
starts again); proud pin; plug upside down. Blocked by what holds them, no fault: scales under screws, gears out of
order, the lid under clips and screws, the cell under its latch, hot core and bare hand.

Cost quality only (no way back built): over-tight vise, torn tape, a miss with the mallet, snapped clip, short
resistor leg, nicked strands, scorched joint, spilled oil, off-centre punch, drill bound or wire snapped (mouse
only: they are speed), over-pour, voids in the press, loose pocket, stripped head, past the line with the file.
Wandering lines (scribe, cut, seam) only lower the step's precision.

Not built: the wrong mould (there is one mould), cross-threading a plate screw, rocking a plate by torquing one side
first, the rag for spilled oil, re-stripping nicked strands, the spare screw for a stripped head.

## Known gaps (Milestone 2)

- **Nobody has seen stages 2 to 5 in the player**, and nobody has played any of it with a real hand. The greybox is
  boxes and cylinders; whether a shot shows the work well, and whether a verb feels like handling a thing, is unjudged.
- **Stage 7 first-person arms** (DESIGN decision 8): judged not clean on 21 Nov and not built (PROGRESS 21 Nov): the view model, its arms rig and both hand solvers are gated on a drawn weapon in Play state, and it carries the hand pistol, not the bench one. It needs an opt-in external-hold hook in `FirstPersonViewModel` (not a bench file) and integration's Part 2 grip in the view model. `s7.inspect` turns the pistol in the bench camera.
- **The Edit Mode suite has not been rerun** since the 19:35 alignment with the exported grip and materials.
- **The real crafting ticket route** (`BENCH_REAL=1`), the keyboard native mode and `BENCH_FULL=1`: never run.
- **The blend back to the follow camera**, the per-shot framing, the HUD changes: written, not seen.
- **Clips re-bound from their rigs** are sampled with `AnimationClip.SampleAnimation` on non-legacy clips: it moves
  the bones in the Editor (`bindcheck`); not tried in a player.
- **A whole bench built from the art has never been made or played**: `bindcheck` binds one family at a time. The
  places with no mark and the vise numbers (see "The seam") will be wrong for the real parts until measured.
- The `rolled_off` fault needs a fast hand (over 0.9 m/s at the seat); `fast` faults need a fast mouse. Only the dev
  fault path tests them.
- Rollback has never been run.
