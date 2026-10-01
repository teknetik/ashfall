# Night lighting and ambient life — sources (1 October 2026)

Art-direction review items 3 ("Night: light the dark pockets and the dead screens") and 9 ("Smoke, steam and fire"),
plus the perimeter-walls follow-up (the wall feet and both collapses were nearly black at 20:30). Unity pass:
`unity/AthenHill/Assets/AthenHill/Editor/NightLifePass.cs`, runtime `Scripts/AmbientLife.cs`. Evidence:
`unity/evidence/night-life/20261001/`. Not reviewed or accepted by Carl.

## Run order

1. Scene audit (read-only, `-nographics`):
   `$O/unity.sh <log> AthenHill.Editor.StreetDressingAudit.DumpBatch --out unity/evidence/night-life/20261001/audit-before.json -nographics`
   and `NightLifePass.RunBatch --steps survey` (all lights, the circuit, cameras → `survey.json`).
2. Layout: `python3 night_layout.py` (reads the audit, executes `night_layout_fixtures.py`, validates every post against
   active colliders, shop door/shutter/stair/terminal keep-clear zones, walker/mechanic/droid routes, NPC and landmark
   points, the Lattice/Ring interaction areas and street-dressing props; writes `night-layout.json`; exits 1 on any
   problem). `python3 night_layout.py --candidates` lists valid spots per pocket. Map: `uv run --with matplotlib python
   map_scene.py review/layout-map.png -50 50 -46 46`.
3. Terminal emission: `$O/heavy.sh uv run --with pillow --with numpy python prepare_terminal_emission.py` →
   `Assets/AthenHill/Art/NightLife/Terminal/MissionTerminal_Emission.png` (display, badge, status button found in the
   Meshy albedo; preview `review/terminal_emission_preview.png`).
4. Before copying any C# into `Assets/`, `python3 check_compile.py editor staging/NightLifePass.cs` (Roslyn against the
   current ScriptAssemblies; a compile error in Assets would stop every other agent's Unity job).
5. Unity (`-nographics`): `NightLifePass.RunBatch --steps build,install,verify`. Later edits (never re-run `build`
   after the install: it re-saves the lamp prefabs under the installed instances): `relayout` (fixtures to the layout:
   add/move/remove, same light objects so clock bindings survive), `retune` (light values, terminal emission),
   `rebuildfx` (recreates the Ambient life group and the review cameras), `fxmats` (particle materials), `lodcuts`
   (lamp LOD heights in place), `cameras`; debug `fxstats` (particle counts, -nographics), `fxprobe` (editor close-ups).
   Final state on 1 Oct: `build,install,verify` → `relayout,rebuildfx,verify` (×2) → `fxmats,lodcuts,rebuildfx,verify`.
6. Editor geometry check (graphics, ≤ 6 cameras): `--steps capture:cam_nl_a+cam_nl_b --out <dir>` (saved afternoon
   lighting, particles simulated 4 s; night is judged natively).
7. (Before Carl's 14:50 process change) A/B builds from one snapshot: `--steps abbuild:on -nographics`, then
   `--steps abbuild:off -nographics` (`abclean` removes leftover scene copies); `native_runs.sh captures <tag>`,
   `native_runs.sh ab <tag> <cam> 2`, `ab_summary.py <tag>`. Builds deleted. Further native tests are the
   orchestrator's combined test.

## Review cameras (scene root "Night life review cameras", player height)

cam_nl_courtyard, cam_nl_terminals, cam_nl_lattice, cam_nl_hall_corner, cam_nl_hill_benches, cam_nl_apron_south,
cam_nl_apron_north, cam_nl_south_collapse, cam_nl_south_lane, cam_nl_north_collapse, cam_nl_rampart_south,
cam_nl_market_fire, cam_nl_air_water_steam, cam_nl_generator, cam_nl_repairs_flue, cam_nl_salvage_stack
(13:00 and 20:30; also cam_courtyard, cam_grid, cam_gate, cam_hill).

## Sources and licences

- Street lamps: the project's own authored Ward utility post / wall fixtures (`Art/Quality/Lamps`, 8 Sep, from
  `art/quality_20260908/lamps`), merged per material into `Prefabs/NightLife/NL_StreetLampPost/Wall.prefab` (meshes in
  `Art/NightLife/Lamps`). No new third-party content.
- Terminal emission: derived from the Meshy mission-terminal albedo (task records in `meshy/mission-terminal-v1`).
- Particles: the Karaveen cookfire materials (`Art/Atmosphere/Dustbowl/CookfireSmoke`, `CookfireFlame`, `SoftPuff.png`,
  project-original) and two new materials on the same texture (`Art/NightLife/FX/NL_Steam`, `NL_ExhaustHaze`).
- Barrel: the Poly Haven `barrel_stove` (CC0) already in the street-dressing kit; its open rim (checked in the glTF:
  no lid, floor at y 0) holds the fire.

## Files

| File | Purpose |
| --- | --- |
| `night_layout.py`, `night_layout_fixtures.py`, `night-layout.json` | fixture/terminal-fill/effect layout and validation |
| `map_scene.py` | top-down review map (colliders, routes, NPC points, existing lights, new fixtures) |
| `prepare_terminal_emission.py`, `terminal-emission.json` | terminal emission mask |
| `check_compile.py` | offline C# compile check |
| `native_runs.sh`, `ab_summary.py`, `compare_pairs.py`, `sheet.py` | native lookbooks / A/B profiles of both arms, summary, before/after sheets |
| `staging/` | the C# as compiled/checked before copying into Assets |
| `review/` | maps, previews, contact sheets (git-ignored media) |
