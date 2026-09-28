# Outer Berms far end — machine depot and robots (overnight brief, 27 Sep 2026)

User request (verbatim, 00:05 27 Sep): "continue work on the berm. the robots at the far end and that whole area
could use work. … we will review in the morning." Quality bar from the same user earlier: **AAA quality**; "if you
need assets we have plenty of credits in meshy and the api key is in .env". An OpenAI image key (OPENAI_API_KEY)
is also in the project-root `.env` for concept/reference images. Never print or log keys.

Work in `/home/teknetik/code/ao2`, native Unity project `unity/AthenHill`. Follow `AGENTS.md` (read it first),
`unity/EDITING.md` and `lore.md` (Outer Berms: "collapsed processing halls, rusted conveyor spines, shattered drone
bays, skeletal frames of long-dead fabrication yards"). Preserve unrelated dirty work. Do not commit. Do not touch
the retired browser game. Keep a running log in `art/outer_berms_depot_20260927/PROGRESS.md` (append after every
milestone: what changed, where, what is verified, what is next). Another session may resume from that file.

## Current state (what exists)

- Outer Berms installed by `Editor/OuterBermsInstaller.cs` (read it): ground mesh x −104..−60, z −54..48; machine
  depot centred (−80, −41) r ≈ 8.5 m: `Depot foundation` + five `Depot wall` slabs (plain concrete **boxes**),
  two salvage generators, stripped scrap, crates, litter, a carcass. Encounters under `Outer Berms/Encounters`:
  *First contact · service road* (one scrap drone at (−83, −13)) and *Machine depot nest* (two worker droids at
  (−81, −40.5), (−77, −37) and a drone at (−84, −36)); the depot re-forms 120 s after clearing. Tutorial:
  `BermsTutorial`; combat: `PlayerCombat`, `Health`, `DroidEncounter`, prefabs in `Prefabs/OuterBerms`.
- Robots: Meshy worker droid (rigged: idle/walk/run/attack/hit/death), scrap drone, plus the Ward mining droid
  inside the city. Sources/tasks: `meshy/outer-berms-20260926`, `meshy/checkpoint-robots-20260926`,
  `meshy/mining-droid-20260926`, merge script `art/outer_berms_20260926/merge_worker_droid.py`. Earlier sessions
  noted these were accepted, but the user's latest instruction says the robots at the far end "could use work": improve
  them (fidelity, materials, scale/grounding, animation, readable telegraphs, VFX/SFX) while keeping the gameplay
  contracts (components, Health, encounter spawns, tutorial steps).
- The West Gate outpost (done 26/27 Sep, see `unity/evidence/west-gate/20260926/README.md`) set the quality bar and
  the toolchain to reuse. **Do not break it**: its layout, landmarks and tests must keep passing.
- The walkable floor now uses `Athen Hill/Berms Ground` (layered scanned PBR, splat
  `Art/WestGate/Ground/BermsGroundSplat.png` from `art/west_gate_20260926/make_ground_splat.py`). The splat already
  runs the tyre-rutted track to the depot; extend it (e.g. oil-soaked depot apron, spill fans, rubble) by editing
  that generator and re-running it, not by hand-painting.

## Reusable toolchain (all in the repo)

- `unity/tools/unity_exec.py` — run a C# method body in the live Editor (MCP at http://127.0.0.1:18081/mcp,
  instance `AthenHill@7f7f353bae1a07d0`). `uv run --offline --with fastmcp python unity/tools/unity_exec.py body.cs`.
  CodeDom compiler (C# 6): write `UnityEngine.Object` explicitly. Long operations can drop the MCP socket; poll
  afterwards instead of re-issuing. Launch the Editor with
  `DISPLAY=:0 /home/teknetik/Unity/Hub/Editor/6000.6.0f1/Editor/Unity -projectPath /home/teknetik/code/ao2/unity/AthenHill &`.
- `unity/tools/editor_capture.py` — renders named cameras or `name:x,y,z:tx,ty,tz:fov` views to PNG through the
  Editor (post-processing on). Use it for every iteration; look at the images; judge honestly at player height.
- `art/west_gate_20260926/author_west_gate.py` — Blender 5.2 headless kit (`U()` Unity→Blender axes, `box`, `cyl`,
  `tube`, `ibeam`, `quad` signs with correct UVs, `hinge`, sandbags, `export`). Copy its helpers; note the glTF import
  mirrors X (see its docstring; quads flip U; open surfaces must orient normals explicitly).
- `art/west_gate_20260926/make_textures.py` (tinted scanned paints, stencil signs), `fetch_polyhaven.py`,
  `convert_polyhaven.py`, `pack_polyhaven_textures.py` (CC0 Poly Haven: e.g. `modular_industrial_pipes_01`,
  `overhead_crane`, `rusted_wheel_rim_01/02`, `modular_electricity_poles`, `metal_grate_rusty`, `rusty_metal_grid`,
  concrete/debris textures), `gen_concept.py` (OpenAI gpt-image-1 references), `unity/tools/create_meshy_prop.py`
  (Meshy API; record every task id/options/credits in a manifest under `meshy/<name>-20260927/`).
- `Editor/WestGateOutpostPass.cs` — the pattern for an Editor pass: layout JSON → prefab instances, URP Lit
  materials built from texture sets, LODGroups from `_LOD#` meshes, COL_ proxies → BoxColliders, retired visuals kept
  inactive, install guard + authoring `Reinstall()` that only rebuilds its own root.

## Hard-won pitfalls

- 12 GB GPU: **close the Unity Editor before native player runs** (Editor ≈ 6 GB; with both open the player stalls
  and QA commands time out). Save the scene first. The `pkill -f` of a player can kill your own shell if the pattern
  matches the command line — kill by PID.
- Native real-input checks: `DISPLAY=:0 ATHEN_CHECKPOINT_EVIDENCE=<dir> uv run --offline --with python-xlib python
  unity/tools/check_checkpoint.py` (it now releases stuck keys first). Add a depot-focused check if you change the
  encounter area (goto `checkpoint_road`/new landmarks, fight or inspect, assert no exceptions).
- Editor Play-mode captures come back blank when the window is unfocused; review lighting in the native build.
- CityLightCircuit: register new practicals in `practicalLights`, and daytime-invisible floods in `nightOnlyLights`.
- Performance: the checkpoint route is at p99 16.50 ms against a 16.67 ms target — almost no headroom. Profile the
  depot route too (`profileStart/Stop` like `check_checkpoint.py`), report p50/p95/p99/max honestly, use LODs, avoid
  daytime shadowed practicals, keep scanned-foliage LOD0 ≤ 16k tris.
- Build: menu `Athen Hill/Build/Linux development player` (and release) via `EditorApplication.delayCall`; result
  lands in `unity/AthenHill/Captures/linux-build.json`.
- Edit Mode tests: `uv run --offline --with fastmcp python unity/tools/unity_client.py run_tests '{"mode":"EditMode"}'`
  then poll `get_test_job` (57 tests currently pass).

## Suggested plan (adapt as evidence dictates)

1. Baseline captures of the depot and the robots (wide, player height, close-ups, native in-game) → evidence folder
   `unity/evidence/outer-berms-depot/20260927/`. Write down the concrete defects.
2. Concept reference(s) with `gen_concept.py` for a ruined machine depot / drone nest on Tir (sandstone, salvaged
   industrial steel, restrained cyan tech), and for the robots if a redesign is warranted.
3. Depot environment: replace the box walls with authored/scanned structure (collapsed hall frame, conveyor spine,
   drone charging cradles as the "power source the cluster guards", cable runs, scrap heaps, oil and scorch decals,
   rubble, grounding), keeping the playable space, spawn points, sightlines and cover readable for combat.
4. Robots: inspect the Meshy sources and in-game renders; improve materials (URP Lit texture sets, correct metal/
   roughness, emissive eyes/tells), fix scale/pivots/foot contact, animation quality; regenerate or retexture with
   Meshy (preapproved) when source quality is the limit. Keep prefabs, Health, DroidEncounter wiring and tells.
5. Verify: Edit Mode tests, dev + release builds, native checkpoint check (must still pass), a depot combat check,
   performance on both routes, captures (day and night). Evidence README with honest remaining defects.

Stop condition: when the depot and robots are clearly improved, verified, documented and the builds pass, finish
with a short summary in PROGRESS.md for the morning review. If usage runs out, leave PROGRESS.md accurate so the
next run can resume.
