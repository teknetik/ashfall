# Night facade tune — sources (1 October 2026)

Art-direction review item 10 ("Night facade tune: lamp hot spots, pillowed masonry, flat orange glass") and two defects
from the review's section 4 (the Finery frontage orange smear, the floating shadow at `cam_sd_hill_benches`).
Material and light edits only. Unity pass: `unity/AthenHill/Assets/AthenHill/Editor/NightFacadePass.cs`. Evidence:
`unity/evidence/night-facade/20261001/`. Not reviewed or accepted by Carl.

## What changes

| Area | Before | After |
| --- | --- | --- |
| Shop and hall wall lamps (34: nine Ward shops, 30; Vanguard Hall, 4) | warm **point** light 0.2 m in front of the caged lamp (0.265 m from the stone), 4.2 / 7.5 m (hall 4.6 / 8 m, recess 3.2 / 5.5 m): a burnt, clipped disc on the wall round every fixture | **spot** 0.15 m further out and 0.1 m lower, aimed down and 10° out from the wall, 140° outer / 95° inner, soft cookie `NF_WallLampCookie` (plateau, soft rim, faint cage-bar shadows), intensity ×1.3, same range and colour, still unshadowed, still on the Ward lighting clock (practical + night-only). It washes the wall below the lamp and the porch; the fixture reads instead of a white disc |
| Lamp bulbs | `VH_LampLens`, emission 6 (shared with the tree-bed and hill uplight lenses and the West Gate bulkheads) | `NF_WallLampBulb`, emission (1.5, 1.15, 0.75): one to two stops over the lit wall. `VH_LampLens` is unchanged |
| Lamp glass | `PH_industrial_wall_lamp_glass` (clear, unlit; shared with the West Gate outpost lamps) | `NF_WallLampGlass`: the same glass with a soft warm emission (0.45, 0.33, 0.2) so the globe glows round the bulb. Both new materials are on the clock's emissive list (dim by day) |
| Shop windows (`Athen Hill/Ward Window Interior`) | one `WS_Glass` for all eight glazed shops: room lamps 3.0, 55 % lit, 50 % blinds, one warm tint (1, .62, .32) + 30 % cool | room lamps 1.2–1.45, blinds 60–75 %, a third lamp colour (neutral 3500–4000 K, new shader property `_NeutralFraction`), softer cool tint, fewer cool rooms, per street: **WS_Glass** (Relay Works, Air + Water, Tool Exchange; 45 % lit), **NF_Glass_HallEast** (Finery, Field Supply; 60 % lit, warmest), **NF_Glass_North** (Salvage, Repairs, Thread + Hide; 68 % lit, most neutral and cool workshop light) |
| Vanguard Hall windows (`VH_Glass`) | room lamps 3.0, 60 % lit | 1.25, 50 % lit, 70 % blinds, the third colour |
| Ward masonry (`VH_Ashlar`, `VH_AshlarRough`) | normal strength 1.0: the worn-rock normal reads as puffy pillows under grazing lamp light | 0.65 (shared by every building on the masonry kit: shops, hall, hill, tree beds, perimeter walls, West Gate arches) |
| West Gate arch bulkheads (2, `WGA_GateA/B`; added after the batch-2 lookbook) | lens `VH_LampLens` (clipped white box); spot 125°, 3 / 7.5 m mounted 0.19 m in front of the leaves (grazing, the wicket black) | lens slots → `NF_BulkheadLens` (1.1, 0.85, 0.58); spot 0.3 m further from the leaves, 0.05 m lower, leaning 8° toward them, 140° / 90°, intensity 4.2, range 8.475 |
| Finery porch smear | two 8 Sep wall-foot grime decals (`Field Supply and Finery weathering/.../Foundation grime 9`, `10`) still placed for the OLD Finery facade line (x 16.7), hanging in the air 1.4 m in front of the rebuilt wall and projecting onto the porch | deactivated (kept for rollback) |
| Floating 13:00 shadow at the hill benches (−9.5, 0, 1.9) | caster: the hoist (hook block, cable, hook; 98 triangles, Retro_Hazard/Retro_Steel) of the old Tool Exchange jib crane, left floating 6.1–8.2 m up at (−15.9, 10.9) when the north-avenue parcel filter removed the jib and mast from `Shop_retrofits_Structure_north_avenue` | the three islands stripped into a new mesh `Art/NightFacade/Retrofit/Shop_retrofits_Structure_north_avenue_nf.asset`, assigned to *Ward district retrofit/Shop retrofits/Shop retrofits Structure*; the original asset is untouched |

`WardGlass` (the review's guess) has no active renderer; the Finery display glazing is `WS_Glass` (now `NF_Glass_HallEast`).

**The visible Finery streak was not the decals.** A night key-light ray scan of the porch (`moonscan` step) shows the
orange band is the moonlight shadow of *Avenue utility lamp 02*'s mast and head lying across the porch; inside it only
the warm lamps remain. It survives with decals, reflections or the porch specular off (`debug-finery-band.jpg` in the
evidence). Softening it needs a district-wide night key-light change (shadow strength/intensity), left to Carl. The
two decals were orphans anyway and stay retired.

## Run order

All Unity steps through `$O/unity.sh <log> AthenHill.Editor.NightFacadePass.RunBatch --steps <steps> [--out dir]`
(`$O` = `/home/teknetik/.local/state/ward-programme`); add `-nographics` except for `capture`.

1. Before copying C# into `Assets/`: `python3 ../night_life_20261001/check_compile.py editor staging/NightFacadePass.cs`.
2. `survey` (lamps, bulbs, lights, prefab-instance overrides, window-shader users, Finery decals, camera-pixel → surface →
   13:00 sun ray caster tests) → `survey.json`; `remnant` (triangle islands near the caster) → `remnant.json`;
   `decalaudit` (sideways decals with no wall inside their box) → `decal-audit.json`; `lightprobe` → per-light
   contribution and shadow occluders on the Finery porch → `lightprobe-finery.json`; `moonscan` (night key-light
   caster per 10 cm on the Finery porch) → `moonscan-finery.json`; `bandprobe` (graphics; the Finery view with decals,
   reflections or porch specular off, nothing saved).
3. `shadercheck` (OpenGL Core compile of every pass of the window shader in two keyword sets).
4. `build`: the cookie PNG (generated in C#), `NF_WallLampBulb`, `NF_WallLampGlass`, `NF_BulkheadLens`,
   `NF_Glass_HallEast`, `NF_Glass_North` (created once; safe to re-run, it only regenerates the cookie).
5. `install` (one time): rollback scene copy, `originals.json` (every light, bulb, glass slot and material value the
   pass touches, recorded before any change), then `apply`.
6. `apply` (idempotent): reads `facade-tune.json`, recomputes every light from its ORIGINAL transform, sets the
   materials, assigns bulbs/lamp glass/street glass/bulkhead lenses in the prefab assets (`Prefabs/WardShops/*.prefab`,
   `Prefabs/VanguardHall/VanguardHall.prefab`, `Prefabs/WestGateArches/WGA_GateA/B.prefab`), adds the new materials to the clock's emissive list, recreates the
   review cameras. Values added to the tune file later are recorded into `originals.json` before their first write.
7. `fixdefects`: the `defects` block of the tune file (decals to deactivate, islands to strip by box).
8. `verify` → `verify-saved-scene.json` (34 spots with cookie, bulbs/glass, clock membership, glass users, 0 missing
   materials, chunk fingerprint).
9. `capture:HOUR:cam+cam` (graphics, at most 6 cameras per run, close views only): edit-mode clock frame via
   `DuskStartPass.Preview`, one warm-up render first.
10. `rollback`: restores every recorded light, bulb, glass slot and material value, the decals and the retrofit mesh,
    and removes the new materials from the clock. The shader property defaults to 0 (previous look); the original
    shader is `rollback/WardWindowInterior.shader.orig`.

A shop rebuild (`WardShopsPass` *Build assets*) re-creates the lamps as points with `VH_LampLens`; *Refresh models and
materials* re-maps the glass slots to `WS_Glass` by name; a West Gate arch prefab rebuild puts `VH_LampLens` and the
125° spot back on the bulkheads. Re-run `apply` after any of them.

## Review cameras (scene root "Night facade review cameras", player height)

cam_nf_air_water_lamps, cam_nf_relay_works, cam_nf_tool_exchange, cam_nf_finery_front, cam_nf_field_supply,
cam_nf_repairs_thread, cam_nf_salvage, cam_nf_hall_portal (20:30 for the look; 13:00 for the masonry relief). The
floating shadow is checked at the existing cam_sd_hill_benches / cam_nl_hill_benches at 13:00.

## Sources and licences

No new third-party content. The cookie is generated procedurally in `NightFacadePass.MakeCookie`. New materials are
copies of project materials (`VH_LampLens`, the Poly Haven CC0 `industrial_wall_lamp` glass already in the project,
`WS_Glass`). Applied 1 Oct: build,install (runB) → fixdefects (runC) → apply ×2 (round 2 with bulkheads, round 3).

## Files

| File | Purpose |
| --- | --- |
| `facade-tune.json` | every value the pass sets (lamps, bulb, lamp glass, glass per street, masonry, defects) |
| `originals.json` | the recorded original values (written by install/apply; used by apply and rollback) |
| `staging/NightFacadePass.cs` | the C# as compile-checked before copying into Assets |
| `rollback/WardWindowInterior.shader.orig` | the window shader before `_NeutralLight` / `_NeutralFraction` |
| `logs/` | Unity batch logs (git-ignored) |
