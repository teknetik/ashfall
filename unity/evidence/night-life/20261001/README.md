# Night lighting and ambient life — evidence (1 October 2026)

Art-direction review items 3 ("Night: light the dark pockets and the dead screens") and 9 ("Smoke, steam and fire"),
plus the perimeter-walls follow-up (wall feet and both collapses nearly black at 20:30). Sources and run order:
`art/night_life_20261001/README.md`. Unity pass: `Assets/AthenHill/Editor/NightLifePass.cs`; runtime
`Assets/AthenHill/Scripts/AmbientLife.cs`. Not reviewed or accepted by Carl.

## What changed in the scene

New scene root **Ward night life** (not a render-chunk source; nothing retired):

| Group | Content |
| --- | --- |
| Street lamps (8) | `Prefabs/NightLife/NL_StreetLampPost` instances: Lamp courtyard terminals (8, −16.8), Lamp hall corner (−2.5, −31.2), Lamp Lattice court (5.1, −39.4), Lamp hill benches (−8, 0.2), Lamp apron south (44, −14), Lamp apron north (44.6, 18.5), Lamp south collapse (14.3, −41.4), Lamp north collapse (−44, 39.6). Each has a scene-added *Lamp warm street light*: spot straight down, 150° outer / 100° inner, intensity 6.0, range 15 m, colour (1, 0.76, 0.48), no shadows. |
| Wall lamps (3) | `NL_StreetLampWall` instances snapped onto the real masonry by a ray against the LOD0 meshes: Wall lamp south lane (−22, 3.4, −43.99) and Wall lamp south lane west (−10, 3.4, −43.98) on the south perimeter wall, Wall lamp rampart south (46.49, 3.6, −26) on the east rampart. *Lamp warm wall light*: spot tilted 25° out from the wall, 130° / 75°, intensity 4.0, range 10 m, no shadows. A fourth bracket (rampart north) first landed on the processing-hall ruin's pale wall and was removed. |
| Mission terminal glow (3) | Cool point fill per Meshy mission terminal (0.45, 0.86, 1.0), intensity 0.75, range 3 m, 0.95 m in front of each screen. |
| Ambient life (5) | *Barrel fire* (flames + embers on `NL_BarrelFlame` (HDR additive), smoke on the cookfire smoke material, *Barrel fire light* point 1.7 / 6.5 m flickering, off by day), *Repairs flue smoke* (forge flue rain cap (19.85, 8.65, 4.92)), *Salvage stovepipe smoke* (roof-shed stovepipe (−20.3, 11.24, 20.65)), *Air + Water relief steam* (filter header (−17.67, 2.66, −8.17), 1.4 s puffs every 3–6.5 s), *Generator exhaust haze* (east-yard generator (30.3, 0.94, −14.9)). Max particles 156 / 70 / 70 / 80 / 24. All on `AmbientLife` (Reduced Motion stops and clears them; day/night tint from the clock). |

Other scene edits:
- **Ward lighting clock** (CityLightCircuit): the 11 lamp lights and 3 terminal fills added to `practicalLights` and
  `nightOnlyLights` (+14 each; 120 → 135 / 66 → 81 at the install, minus the removed rampart-north bracket). The barrel fire light is not on the circuit (AmbientLife drives it).
- The three `Mission Terminal Upgrade/Mission Terminal 0x/Meshy Mission Terminal` renderers use
  `Art/NightLife/Terminal/MissionTerminal_Lit.mat` (prefab-instance override). The Meshy `MissionTerminal.mat` and the
  MissionTerminal prefab are unchanged. Emission strength 1.5, constant (the hill RECLAIM kiosks are constant too).
- New root **Night life review cameras** (16 cameras, below).
- Rollback: `rollback/before-night-life.unity` (scene before the install). To revert in place: deactivate *Ward night
  life*, put `MissionTerminal.mat` back on the three terminal renderers, and remove the 14 lights from the circuit lists.

`verify-saved-scene.json` (final, `-nographics`, after `fxmats,lodcuts,rebuildfx`): installed and active, 11/11 fixtures
prefab-linked, uniform scale, 0 missing materials, all 14 lamp/fill lights practical + night-only, effects bound to the
session and clock, terminals on the lit material, chunk fingerprint matches, root not a chunk source, 16 review cameras.

## Kit, triangles, lights

| Prefab | LOD0 | LOD1 | LOD2 | cuts (screen height) |
| --- | --- | --- | --- | --- |
| NL_StreetLampPost (103 authored parts merged per material) | 35,699 tris / 9 renderers | 19,572 / 8 | 4,144 / 5 | 0.30 / 0.15 / 0.012 (≈ 33 m / 66 m at 60°, LOD bias 2) |
| NL_StreetLampWall (73 parts) | 26,997 / 8 | 9,944 / 6 | 2,176 / 2 | 0.12 / 0.06 / 0.006 |

Totals over the 11 fixtures: LOD0 366,583, LOD1 186,408, LOD2 39,680 triangles (never all at LOD0). LOD0/LOD1 cast sun
shadows only through a ShadowsOnly copy of the LOD2 masses. New lights: 11 spots + 3 points on the circuit (night only,
unshadowed) + 1 flickering point (night only). Particle systems: 7, ≤ 400 particles in total.

## Frame time (A/B) — measured on an earlier state; final numbers pending the orchestrator's combined test

Alternating runs of two development builds made from ONE snapshot of the saved scene (night life on / off: root inactive
and terminals on their original material in the off copy), 1920×1080, High preset, OpenGL, RTX 3060 12 GB, render scale
100 %, VSync off in QA, 8 s profile per hour, two rounds each (`ab/3-*`, `ab/summary-3.json`). GPU time unavailable
(null). This snapshot (14:03/14:07) predates the final `fxmats/lodcuts/rebuildfx` step (HDR barrel flame material,
denser smoke/steam, post LOD1→LOD2 moved from 0.08 to 0.15, i.e. fewer triangles beyond 66 m).

| Camera | Hour | On: avg fps / p50 / p95 / p99 / max (ms) | Off: avg fps / p50 / p95 / p99 / max | Δ mean frame | Δ tris |
| --- | --- | --- | --- | --- | --- |
| cam_hill (wide) | 13:00 | 66.9 / 14.85 / 16.01 / 17.36 / 18.71 | 66.8 / 14.90 / 16.26 / 17.94 / 28.02 | −0.02 ms | +303k |
| cam_hill (wide) | 20:30 | 72.5 / 13.74 / 14.70 / 15.80 / 19.61 | 74.4 / 13.42 / 14.23 / 14.94 / 17.16 | +0.35 ms | +282k |
| cam_nl_courtyard (close) | 13:00 | 94.2 / 9.27 / 23.69 / 26.48 / 29.41 | 104.6 / 9.63 / 10.76 / 11.22 / 12.94 | +1.06 ms | +252k |
| cam_nl_courtyard (close) | 20:30 | 108.4 / 9.23 / 10.27 / 10.91 / 12.06 | 113.3 / 8.81 / 9.90 / 10.43 / 12.38 | +0.40 ms | +234k |

Per-run fps: cam_hill 13:00 on 66.2, 67.5 / off 66.5, 67.1; 20:30 on 72.1, 72.9 / off 74.5, 74.2; courtyard 13:00 on 94.9,
93.5 / off 106.3, 103.0; 20:30 on 108.8, 108.0 / off 114.2, 112.5.

The courtyard 13:00 "on" figure is a **first-view artefact**: it is the first profile after the player loads, and every
other frame took ~19 ms (main thread waiting, alternating with ~5 ms frames). Profiling the same view after a warm-up
(`ab/dbg-courtyard-late13-*`, hours 20.5 then 13, one run per arm) gives on 103.3 fps / p95 11.07 / p99 12.54 vs off
110.3 / 10.05 / 10.93 at 13:00 (**+0.61 ms**), and 105.2 / 10.51 vs 114.7 / 9.74 at 20:30 (**+0.79 ms**, single runs,
desktop drift ±1–1.5 ms). Likely first-use shader/texture warm-up of the new materials; the combined test should check
whether it recurs. So: wide view ~0 ms by day and +0.35 ms at night (within the < 0.5 ms guide); close courtyard view
+0.4–0.8 ms (above the wide-view guide, in a view with three LOD0 lamps, three lit terminals and their fills).

## City loop

**Pending the orchestrator's combined test** (per Carl's 14:50 process change no city loop was run by this pass). The
pass changes no gameplay object: lamps have colliders only on the mast/footing, placed clear of routes, doors, stairs and
NPC/interaction points (`art/night_life_20261001/night_layout.py`: 0 problems); the mission terminals keep their prefab
links, BoxColliders and the `mission_slab` landmark.

## Captures

Native lookbooks of both arms (snapshot 3), all review views plus cam_hill/avenue/gate/courtyard/grid at 13:00 and 20:30:
- before `native-off-3/` (sheets `sheet-h13.00.jpg`, `sheet-h20.50.jpg`), after `native-on-3/`.
- Matched pairs: `compare-night-h20.jpg` (courtyard, terminals, Lattice court (cam_grid), hall corner, hill benches, south
  collapse) and `compare-night-h20-walls.jpg` (south lane, north collapse, rampart, apron north, market fire, cam_hill);
  `compare-day-h13.jpg` (nothing wrong by day: lamps unlit, terminals readable, badges lit).
- Earlier iterations: `native-off-1/`, `native-on-1/` (lamps at 2.6, too weak), `native-on-2/` (on arm only, tuned
  lamps); editor geometry checks `editor-1/`, effect probes `editor-fxprobe-1/`, `fxstats.json` (particle counts).
- `native-on-3` predates the final effects retune: the barrel flames there are still the faint cookfire material, and
  `cam_nl_market_fire` was later moved south of the barrel (the bunting mast stood in front of it).

Best before/after (20:30): `native-off-3/cam_nl_south_collapse-h20.50.png` → `native-on-3/…`; `cam_nl_courtyard`;
`cam_grid`; `cam_nl_south_lane`; `cam_nl_terminals`.

## Review cameras (Night life review cameras, player height 1.65 m)

cam_nl_courtyard, cam_nl_terminals, cam_nl_lattice, cam_nl_hall_corner, cam_nl_hill_benches, cam_nl_apron_south,
cam_nl_apron_north, cam_nl_south_collapse, cam_nl_south_lane, cam_nl_north_collapse, cam_nl_rampart_south,
cam_nl_market_fire, cam_nl_air_water_steam, cam_nl_generator, cam_nl_repairs_flue, cam_nl_salvage_stack.
Use 13:00 and 20:30. Also relevant: cam_courtyard, cam_grid, cam_gate, cam_hill.

## Remaining defects (honest)

- The final effects retune (HDR barrel flames, denser barrel smoke, steam, haze) and the moved market-fire camera have
  **not been seen in the native player**; earlier native captures showed faint flames, smoke that was invisible near the
  barrel and steam that did not appear at capture time. Pending the combined lookbook.
- Flue and barrel smoke are dark lit puffs: readable against the day sky, nearly invisible at night (no light reaches
  them). Generator haze is very faint by design and may read as nothing.
- Lamps are unshadowed: light passes through the plinth, containers and walls (e.g. the south-collapse lamp lights the
  red container and the wall evenly); the lamp lenses render as clipped white discs (next-wins item 10, shared with the
  existing lamps).
- The apron lamps add little from the apron cameras (the avenue lamps at (35, ±5) already light the spawn area; the new
  pools are at the rampart foot).
- The north wall foot is still dark apart from the north collapse: the Quantum Tube runs along the wall face, so no
  bracket was placed there. The night ambient/moon balance was judged and left unchanged (pools now carry the pockets;
  lifting the shared WardDustbowl night ambient would flatten the whole night for every pass).
- Mission-terminal badges glow by day too (constant emission, as the hill kiosks); the screen fill tints the slab cyan.
- Close courtyard cost +0.4–0.8 ms (see above) and the first-view frame alternation at 13:00 need the combined test.
- Fixture LOD transitions and moving smoke/steam not reviewed in motion; no Reduced Motion toggle was exercised natively.
