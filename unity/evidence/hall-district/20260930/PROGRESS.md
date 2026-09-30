# Hall district pass — progress log (30 Sep 2026)

Carl's request (30 Sep 2026, after reviewing the rebuilt Vanguard Hall):
1. Fix the Hall's weak spots: walls in full shade look flat, stone edges too clean close up, rain stains too faint.
2. Rebuild the neighbouring buildings to the same standard (modelled stone, proper doorways, lamps on the city
   day/night timing) so the Hall doesn't stand alone.
3. Re-check the rest of the city loop: Mira, Torr, Linn, trading at Basic General, Lattice travel (only Vex was re-checked).
4. Signs: "I don't like the signs so much. I designed one I like a little more in Meshy for General. See if you can do better."

Session: "Hall and city visuals polish". Baseline: HEAD fe7f350d (hall rebuild) on ward/next-level, clean tree at start.

## Targets (not yet shown to Carl)
- `art/hall_district_20260930/concept/street-concept-a.png` — stone shops beside the hall (Relay Works, Air + Water,
  Field Supply) with deep doorways, roller shutter, filter canisters, awnings, bracket signs, wall lamps.
- `art/hall_district_20260930/concept/sign-family-concept-a.png` — fabricated sign family derived from Carl's Meshy
  Basic General sign (dark steel, amber raised letters, cyan accent, lit OPEN plate), made physical.

## Hall weathering (step 1)
- New shared kit `art/ward_masonry_kit/ward_masonry.py` (the hall script now imports it):
  dressed blocks get a 1–4.5 cm margin, pillowed face, real bevels on all four arrises (bed faces kept at LOD0),
  arrises split every 15 cm (<2.4 m), 30 cm (<4.2 m) and eroded with 3D noise; chips/spalls dig out corners without
  crossing the mortar plane (mortar recessed to 2.6 cm); ray-traced per-vertex sky occlusion (AOBaker);
  vertex RGB = block tint × broad drift × wall-foot splash; UV1 = (runoff, worn arris), UV2 = (rust, 0) from DripSet
  sources (entablature, soffit, string course, coping, sills, scuppers, iron corbels, brackets, lamps, nameplate).
- Bugs found and fixed on the way: bmesh bevel "faces" output includes reshaped neighbours (bevel faces now tagged via a
  temporary material index); inset_individual needs an updated face normal (otherwise zero inset); open top/bottom
  edges cannot be bevelled (the committed hall never had bevelled bed arrises); chips tilting whole faces behind
  the mortar plane (blotches).
- Shader `Athen Hill/Masonry Lit`: runoff streaks (world-space streak map `WardRunoff_Streaks.png`,
  `make_streak_texture.py`), mineral deposits, rust trails, worn-arris breakup, dust on upward faces, cavity albedo.
- Unity: `VanguardHallPass.ApplyWeathering()` (menu Apply weathering pass): streak map import, GLB reimport,
  material properties, LOD0 cut 0.40, probe-only GI (UV1 carries wear data, never lightmap UVs).
- Hall LOD0 85,094 → 149,908 triangles (masonry 24.5k → 69.8k); LOD1 41,976.
- Editor captures: `hall-weather-editor-v3/`. Native tuning pending.

## Final (30 Sep, afternoon)
All five requests done and natively verified; see README.md in this folder for results, scores, defects and rollback.
