# West Gate exit and Warden outpost — 26 September 2026

User direction: tidy up the exit from Ward to the Outer Berms; the first-pass Warden outpost "looks amateur at
best" and should reach AAA quality. This pass replaces the first-pass booth, box barriers, floating TextMesh
signs, crate locker and basin-shader floor. It keeps every gameplay object, ID and tutorial connection.

## What was built

| Area | Content |
| --- | --- |
| Gate | Steel-armoured concrete piers covering the cut wall ends (hazard-wrapped bases, riveted plate, rusted corner angles), knee-braced lintel carrying stencilled WEST GATE / WARD signs, walk-on gantry with railings, four floodlights, CCTV, amber beacon, Warden banners on both faces, junction box and conduit. Parked-open sliding gate leaf on a rail plinth with wall-top guide rollers. Concrete ramp apron from the threshold down to the basin floor. |
| Warden post | 20 ft ISO container (modelled trapezoidal corrugation, corner castings, cargo doors with one leaf open onto a lit desk and radio) on footings; issue window with bars, counter and propped awning shutter; shade canopy (cloth-simulated) on poles; roof sandbags, antenna, solar panel, searchlight; rear AC unit; generator, fuel and water drums. |
| Arms issue | Steel arms locker with one door open (pistol cradles, cyan charge strip and beacon, ARMS plate) under the canopy, beside crates and a chair. It uses the same interaction root and prompt. |
| Lane | Raised boom barrier at the foot of the ramp, scanned jersey barriers (lane edge and chicane), sandbag sentry nest by the south pier, field briefing board with a pinned map, notice and roster. |
| Range | Firing bench with FIRING LINE plate and a sandbag firing point, range sign, LIVE FIRE sign, range flag, range control post with a power box. Trailer light tower between the lane and the range. |
| Ground | New `Athen Hill/Berms Ground` shader: four height-blended scanned layers (pebbly dry ground, drift sand, compacted gravel, cracked crust) with a painted splat. The splat includes a tyre-rutted track, sand drifts at the wall and in the lee of objects, and trodden areas. Full URP lighting: SSAO, decals and local lights. Distance haze matches the backdrop. Also 190 scattered rocks and stones, five boulders, 18 scanned desert shrubs, and decals for tyre tracks, oil, sand spill and grime. |
| Inside approach | The collapsed gantry framing the gate from inside Ward was replaced with riveted, rust-textured I-sections at the same transforms. The flat-coloured originals remain in AuthoredWorld, inactive; colliders are unchanged. |
| Wardens | Ossa and Rell use a Warden kit variant of the guard material. The supplied material re-used its albedo as a full-strength emissive map and was fully metallic, so the guards glowed white. The variant is non-emissive, dielectric, field khaki. The four city guards keep the original material. |

## Sources and scripts (run order)

1. `fetch_polyhaven.py` — CC0 Poly Haven models/textures (`polyhaven/`, `polyhaven/manifest.json`).
2. `convert_polyhaven.py` (Blender 5.2) — decimated LOD GLBs without images → `Assets/AthenHill/Art/WestGate/Props` (`polyhaven-conversion.json`).
3. `pack_polyhaven_textures.py` — URP texture sets for the props (and sandstone recolour of the pink granite scans).
4. `make_textures.py` — tinted tiling paints, stencilled signs (OFL fonts, `fonts/`), Warden banner, pinned papers.
5. `pack_ground_layers.py`, `make_ground_splat.py` — ground layer arrays and splat (from `layout.json` and `berms-ground-grid.json`).
6. `make_decals.py` — decal textures.
7. `author_west_gate.py` (Blender 5.2) — authored structures → `Art/WestGate/Structures` (`authored-assets.json`).
8. `layout.py` → `layout.json` — every placement, gameplay anchor, landmark, the road line, apron and decals.
9. Unity: **Athen Hill → Outer Berms → West Gate: build assets**, then **West Gate: install outpost**, then
   **West Gate: upgrade wreck gantry** (`Editor/WestGateOutpostPass.cs`). Install refuses to overwrite an
   installed outpost; authoring iteration used `WestGateOutpostPass.Reinstall()`, which rebuilds only its own root.

`concept/gate_exit_from_ward.png` is a generated reference (OpenAI gpt-image-1, prompt in `concept/prompts.json`).
It guided the lintel sign, knee braces and pier hazard wraps. It is not a target render or shipped art.

Heavy media (downloads, per-layer PNGs, concept image) stays local per `.gitignore`; scripts, JSON and this
README are tracked. Licence entries are appended to `Assets/AthenHill/Art/THIRD_PARTY_LICENSES.txt`.
