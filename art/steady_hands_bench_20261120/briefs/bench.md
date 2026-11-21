# Brief: `bench` — the hands-on assembly system

You build the interaction system for the Steady Hands bench job: the thing that makes picking up, turning, seating,
fastening and working parts with tools feel like real work. This is the centre of the programme.

Read first, in this order: `../AGENT-RULES.md`, `../DESIGN.md` (all of it), `../CONTRACT.md` (sections A parts.json,
B and C), `../FACTS.md` (Runtime hooks, Brann's bench), `../ANYMACHINE.md` section 2.

## What you own

`Scripts/Assembly/**`, `Editor/Assembly*.cs`, `Tests/Editor/Assembly*Tests.cs`, `Data/Assembly/**`, and small additive
edits to `GameSession.cs`, `GameInput.cs`, `Data/Controls.inputactions`, `FollowCamera.cs`,
`Camera/CinematicCamera.cs`, `CityHud.cs`, `DevBridgeCommands.cs`, `NativeQa.cs`. Another agent (`craft`) owns
`Scripts/Crafting/**`, orders, journal, save and combat feel, and is writing `Scripts/Crafting/AssemblyHost.cs` to the
surface in `CONTRACT.md` section B at the same time as you. Code against that surface. Until its file exists, keep
your calls to it behind one small adapter class of your own (`Scripts/Assembly/AssemblyCraftLink.cs`) so the tree
always compiles; check for the real file before each compile and switch over when it lands.

## What to build

1. **Data**: `AssemblyRecipe` (ScriptableObject) holding stages, steps (id, archetype, tool, target part, numbers,
   prerequisites, recovery step, audio and voice ids, weight in quality), built by an Editor method from a JSON step
   table that you write from `DESIGN.md` section 7 (`art/steady_hands_bench_20261120/data/steps.json`; keep the step
   ids exactly). The JSON is the editable source; the asset is generated from it.
2. **Job model** (`AssemblyJob`, pure C#, no scene): step graph, step states, faults and recoveries, precision scores,
   quality, elapsed time, serialise to and from the blob the crafting system saves. Edit Mode tests cover: the graph
   (nothing available before its prerequisites, every step reachable, the job completable), every fault and its
   recovery, leaving and resuming at any point, quality thresholds, the blob round trip, and a blob from an older
   layout loading safely.
3. **Parts, sockets, fasteners, tools, parameters** as components, built from `parts.json` by an Editor builder
   (`AssemblyKitBuilder`) that turns a family GLB plus its `parts.json` into prefabs. The same builder must accept a
   **greybox family**: you write greybox `parts.json` files and generate primitive meshes for them, so the whole job is
   playable before any art exists and the art drops in through the same path.
4. **The seven verb archetypes** of `DESIGN.md` section 6, each with a mouse form and a keyboard form, each reporting
   progress, faults and precision. Feel rules in that section are requirements: the carry spring with weight classes,
   the pull-in, resistance carried by sound pitch and tool motion and travel per unit of input.
5. **The session** (`AssemblySession`): enters and leaves `CityState.Assembly`, owns the bench camera (take-over with
   a restore ledger like `PhotoMode`, or an overlay like `ConversationCamera`: choose and say why), focus and
   affordance light, the three-step idle hints, stage shots, depth of field through `TransientVolume`, Reduced Motion
   forms of all of it, the Field Notes line, Brann's lines with captions (`BenchVoice`: plays a clip on Brann's voice
   source, shows `BarkCaptionView`, sets `NpcAgent.barking`), and `AssemblyAudio` (pooled sources on the SFX group,
   own voice limit, pitch-following loops, material-pair contact sounds) driven by event ids. Missing clips must be
   silent, not errors: audio arrives later.
6. **Input**: a `Bench` action map in `Controls.inputactions` per `DESIGN.md` section 5, with a `verify` step in your
   installer that checks ids and bindings are unique, as the P and M keys did. The cursor is free and visible at the
   bench.
7. **Interface**: no panels for the core work. The shade must be transparent in `Assembly` state and the modal frame
   hidden; build what little UI there is (stage line, captions, a hold-to-abandon affordance, the key legend on first
   use) in code with your own stylesheet, the way `WorldMapPanel` does.
8. **QA**: `dev.assembly.*` bridge commands (state, list available steps, complete a step with a given precision,
   raise a fault, finish with a quality, abandon, move the camera to a stage shot) and an `assembly` block in
   `snapshot.json` with enough to drive a real-input check: screen positions of the active targets, the held object,
   the current verb and its progress.
9. **Installer** `Editor/AssemblyBenchInstall20261120.cs` (`install`, `verify`, `rollback`): creates the scene root
   **Steady Hands bench** placed from the workbench's transform (not under `Salvage shop interior`, whose installer
   rebuilds its root), with the greybox set laid out per `DESIGN.md` section 4 on the worktop (0.864 m, 2.2 x 1.15 m),
   registers the root with `InteriorLighting`, adds a QA landmark and `cam_bench_*` review cameras, and generates the
   recipe asset. A later `integration` agent swaps the greybox for the real families and does lighting and shaders;
   leave it a clean seam (one method that binds a family) and say where it is.

## Order of work

**Milestone 1, the slice** (report when it is done, then continue): stages 0, 1, 6 and 7 fully playable in greybox
with the Seat, Turn, Window, Point and Flick archetypes, the camera, input, hints, audio hooks, save and resume, the
hand-off to `craft`, the installer and its verify, tests green through `SH/seq.sh tests bench-m1`. In the slice the
grip that is fitted in stage 6 is given complete by a dev command.

**Milestone 2**: the Path and Wipe archetypes and stages 2 to 5, so the full 17 minutes is playable in greybox, with
every fault and recovery in the design. Then the first-person arms in stage 7 if a bench driver for the view model is
clean (`DESIGN.md` decision 8; `FACTS.md` Hands), otherwise say why not.

You may run Edit Mode tests and your installer through the wrappers. You may not build the player or run native
checks; the orchestrator does that and sends you captures and defects. Write a native check script early
(`unity/tools/check_steady_hands_bench.py`, on `showcase_qa.py`) that plays the slice with real keyboard and mouse
through your snapshot block and saves a capture per step, so the orchestrator can run it; a second mode plays it
keyboard-only.

## Judged on

Whether it feels like handling objects. A step that is "click the highlighted thing" is a failure of this brief even
if every test passes. Where a number decides feel (spring stiffness, pull-in distance and time, turn gain, window
widths, hint timings), put it in the recipe or a settings asset and list it in your README with what it does, so it
can be tuned from play without code.

Folder for your notes and data: `art/steady_hands_bench_20261120/bench/` (`README.md`, departures, tuning table).
