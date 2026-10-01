# Night facade tune — evidence (1 October 2026)

Art-direction review item 10 plus two section-4 defects, and the orchestrator's batch-2 finding on the West Gate arch
bulkheads. Sources and run order: `art/night_facade_20261001/README.md`. Pass: `Editor/NightFacadePass.cs`. Tested on
the working tree of `ward/next-level` (base 3ebd801b plus the uncommitted batch 1–3 work), 1 Oct 16:30–17:10.
Not reviewed or accepted by Carl. **No player build, native lookbook, A/B or city loop of this pass's own** (revised
definition of done): all images here are **editor** captures (edit-mode clock frame 20:30 / 13:00 through
`DuskStartPass.Preview`; every practical light at its authored intensity, no circuit distance fade). The orchestrator's
combined native lookbook is the judge of the night look.

## What changed in the saved scene and assets

- 34 wall lamps (Relay Works 3, Air + Water 3, Tool Exchange 3, Finery 3, Field Supply 3, Salvage 3, Repairs 4,
  Thread + Hide 3, Basic General 5, Vanguard Hall 4): point → spot, 0.15 m further from the wall and 0.1 m lower, aimed
  down and 10° out, 140° / 95°, cookie `NF_WallLampCookie` (256², generated), intensity ×1.3 (shops 4.2 → 5.46, hall
  4.6 → 5.98, hall recess 3.2 → 4.16), ranges and colour unchanged, unshadowed, still practical + night-only on the
  Ward lighting clock. Bulbs `NF_WallLampBulb` (emission 1.5 / 1.15 / 0.75, was `VH_LampLens` 6 / 4.8 / 3.3), globes
  `NF_WallLampGlass` (68 slots, warm emission 0.45 / 0.33 / 0.2). Edited in the prefab assets; scene instances carry no
  overrides (survey: 0 before, 0 reverted).
- 2 West Gate arch bulkheads (`WGA_GateA/B`): lens slots (3 per gate) `VH_LampLens` → `NF_BulkheadLens` (1.1 / 0.85 /
  0.58); spot 0.3 m away from the leaves and 0.05 m lower, leaning 8° toward the leaves, 125° → 140° / 90°, intensity
  3 → 4.2, range 7.5 → 8.475.
- Window glass: `WS_Glass` (in place), `NF_Glass_HallEast` (Finery, Field Supply), `NF_Glass_North` (Salvage, Repairs,
  Thread + Hide), `VH_Glass` (in place) — values in `verify-saved-scene.json` → `materials`. Shader
  `WardWindowInterior.shader`: `_NeutralLight`, `_NeutralFraction` (third lamp colour; 0 = previous look);
  `shader-check.json`: every pass compiles for OpenGL Core.
- `VH_Ashlar`, `VH_AshlarRough` `_BumpScale` 1.0 → 0.65.
- Deactivated: *Field Supply and Finery weathering/Localized drainage and foundation deposits/Foundation grime 9* and
  *10* (8 Sep wall-foot decals left at the old Finery facade line, x 16.7, hanging over the rebuilt porch;
  `decal-audit.json`).
- *Ward district retrofit/Shop retrofits/Shop retrofits Structure* → `Art/NightFacade/Retrofit/Shop_retrofits_Structure_north_avenue_nf.asset`:
  3 islands / 98 triangles removed (hook block, cable, hook of the old Tool Exchange jib crane floating at
  (−15.9, 6.1–8.2, 10.9); `remnant.json`, `fix-defects.json`).
- Review cameras: root **Night facade review cameras**, `cam_nf_air_water_lamps`, `cam_nf_relay_works`,
  `cam_nf_tool_exchange`, `cam_nf_finery_front`, `cam_nf_field_supply`, `cam_nf_repairs_thread`, `cam_nf_salvage`,
  `cam_nf_hall_portal`.
- Rollback: `rollback/before-night-facade.unity` (scene before install), `originals.json` (every value changed;
  `NightFacadePass --steps rollback`).

Counts: lights 0 added (34 converted, 2 retuned; the circuit's practical/night-only lists unchanged); triangles −98;
5 new materials, 1 cookie texture (256², RGBA32 + mips, ~350 kB), 1 mesh copy. The URP cookie atlas (2048², set in
`PC_RPAsset`) is first used by this pass.

## Verify (saved scene, `verify-saved-scene.json`)

34/34 lamps: spot, cookie, NF bulb and globe, on the clock practical + night-only list; bulkheads on the clock with the
NF lens; 0 missing materials on the tuned prefabs; chunk fingerprint matches (no chunk source touched); 8 review cameras.

## Images

| File | What |
| --- | --- |
| `compare-night-h20.jpg` | 20:30, five views: before / round 1 / round 2 |
| `compare-night-h20-final.jpg` | 20:30, Tool Exchange, Finery, hall portal: before / round 2 / final (round 3) |
| `compare-hill-benches-h13.jpg` | 13:00 cam_sd_hill_benches: floating shadow before / gone after; plinth masonry at normal 0.65 by day |
| `compare-wicket-h20.jpg` | West Gate wicket: batch-2 native (before) beside the editor after — not like for like |
| `debug-finery-band.jpg` | Finery porch band with decals / reflections / porch specular off: unchanged in all |
| `editor-before/`, `editor-after1..3/` | the editor captures |

Rounds: (1) spots 120°/75°, tilt 15°, out 0.2 m, ×1.0, cookie falloff from half radius: discs gone but walls too dark;
(2) cookie plateau, 130°/90°, tilt 10°, out 0.15 m, ×1.1, glowing globes, fewer cool rooms, bulkheads; (3) 140°/95°,
×1.3 (final).

## Findings

- Wall-lamp disc: the point light sat 0.265 m from the stone (≈60× the illuminance of a lamp-lit wall at 1 m) behind a
  bulb at emission 6 (bloom threshold 1.1). Both fixed.
- Finery glazing is `WS_Glass` on the window-interior shader (not `WardGlass`, which has no active renderer).
- **The Finery "orange streak" is not a decal.** `moonscan-finery.json` (10 cm grid, night key-light rays) shows it is the
  moonlight shadow of *Avenue utility lamp 02*'s mast and head (render chunks WardLampPaint/Steel/Enamel/Bronze) lying
  diagonally across the porch; inside it only the warm lamps remain, so it reads as an orange smear. It is unchanged
  with all decals, reflection probes or the porch specular switched off (`debug-finery-band.jpg`). Physically
  consistent; softening it means changing the night key light (shadow strength or intensity) — a district-wide
  decision left to Carl / the orchestrator. The two orphaned decals were removed anyway.
- Floating 13:00 shadow: caster found (above); gone in the editor 13:00 view.

## Known remaining defects / not verified

- Native look not seen: night exposure, bloom and the circuit's distance fade differ from the editor; the combined
  lookbook decides. Upper facades between lamps are darker than before (by design: downlights).
- The hall portal recess lamp now throws a visible pool on the right door leaf.
- Cookie keyword: the first frame with a cookie light visible enables `_LIGHT_COOKIES` in every lit shader; on OpenGL a
  one-off shader-variant hitch at dusk is possible. Cost not measured (no own A/B); expected small (spots are tighter
  than the old points). If the combined test shows a cost, set `lamps.cookie` false and re-run `apply`.
- Window interiors are still procedural rooms with flat backlit blinds; tone is calmer but not photographic.
- `VH_LampLens` (tree-bed and hill uplight lenses) unchanged: owned by the birch-canopy pass.
- Masonry normal 0.65 applies to every masonry-kit building (by day as well); check the walls and hall by day.
- A shop rebuild or *Refresh models and materials* reverts lamps/glass; re-run `apply` after one.
