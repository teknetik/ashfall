# Hill and hero-tree base rebuild — 30 September 2026

Carl (30 Sep 2026): "having rebuild the vanguard building and ones close by I would like to do a similar pass on the
hero tree and hill. note the image how its circled in stone, stone like the walls of the other buildings so it matches.
I have also attached a new flood light asset for the vanguards hall to replace the box looking ones and replacement
terminals for the 'hill'." His reference was an edited in-game screenshot: the tree ringed by a low masonry wall, grass
beds and paved paths. The ring here uses the Vanguard Hall / hall-district stone (shared kit `art/ward_masonry_kit`,
Athen Hill/Masonry Lit), not the orange brick in the edit.

## What was built

| Part | Construction |
| --- | --- |
| Retaining walls | All four sides of the existing 14 × 14 m plinth: rough foot course, two dressed ashlar courses, alternating quoins at the corners, a 0.42 m coping band flush with the hilltop (runoff under it, old battle damage, heavier on the +X side that faced the West Gate). |
| Stairs | The three 4 m flights (6 × 0.25 m risers, 0.6 m treads) sit exactly on the saved `COL_ENV_hill_stair_*` boxes: two or three stones per step, worn nosings, treads dished where feet land. Raking-coped cheek walls (raking-cut courses under 0.16 m sloped copings) end in capstones at the stair heads; sheltered sand in the tread corners. |
| Tree ring | One dressed course (outer face r 3.30 m) authored on a straight frame and bent round the centre so every block keeps the kit's margins, chips and eroded arrises; inner face r 2.85 m; curved coping stones 0.49 m above the paving (a seat). One coping stone has been lifted by a root and cracked, repaired with four iron dog cramps (rust runoff below). Three bronze uplights in the coping light the crown at night. |
| Hilltop | Curved apron flags round the ring, three flagged paths with full-width landings, kerbed beds, stone pads and stepping stones for the terminals, a stone under Linn's standing point, an irrigation standpipe with valve wheel inside the ring. |
| Soil and roots | Grass-bed soil (Poly Haven `sparse_grass`) and a leaf-litter dome inside the ring (`dry_decay_leaves`), both shaped by `hill_layout.bed_y` / `ring_soil_y`. Eight surface roots with side roots rise from the trunk flare, lie half-buried and dive under the litter; the long one runs to the heaved coping. |
| Planting | `scatter_hill_plants.py`: Poly Haven medium grasses (most of the bed), Cheiridopsis succulent drifts, ice plant, celandine and weeds at the kerbs, Othonna shrubs as accents, Namaqualand stones and two feature boulders; bark litter, twigs and stones inside the ring. Seeded Poisson disc, drift-shaped density, clear of pads, stones, Linn and the board. |
| Terminals | Carl's Meshy "Reclaim & Save Point" kiosk on the three existing terminal slots, now facing the tree, 1.85 m tall, three LODs (46k / 15k / 4k), full 2k source maps, cyan emission mask from the albedo, a night screen glow. Decimation smeared the baked screen UI, so both screens carry an authored overlay following his layout (`screen/make_terminal_screen.py`), with an honest LINK OFFLINE status line. Decorative, as before: no save or reclaim interaction exists. |
| Hall floodlights | Carl's Meshy tripod floodlight (1.0 m, three LODs) replaces the modelled box uplights on the Vanguard Hall podium; its head was turned up 15° about the yoke pivot (continuous weight, no tearing) and the existing spot lights moved to its lens, aimed at the nameplate. |

## Sources and scripts (run order)

1. `fetch_polyhaven.py` — CC0 Poly Haven models and textures to `polyhaven/` (`polyhaven/manifest.json`: authors, licence, URLs).
2. `author_ward_hill.py` (Blender 5.2, headless) → `Art/WardHill/Models/WardHill_LOD0.glb` (~122k triangles), `LOD1` (~25k),
   `ward-hill.json` (cheek colliders, terminal mounts, uplights, ring/soil collider specs, bed polygons, exclusions) and
   `hill-source.blend`. In Unity the walls, stairs and ring cast shadows through their LOD1 meshes (shadow proxies). Layout constants and ground-height functions live in `hill_layout.py`.
3. `scatter_hill_plants.py` (Blender) → `HillPlants_LOD0.glb` (~241k) / `LOD1` (~74k), `hill-plants.json`. One object per
   zone (five zones, each its own LOD group in Unity) and group (ground cover casts no shadow; boulders, shrubs and
   twigs do); each object's origin is its soil level.
4. `prepare_hill_textures.py` (uv, Pillow, NumPy) → plant and soil texture sets (base + alpha, URP masks, normals).
5. `prepare_meshy_props.py` (Blender) → `Art/HillProps/{Terminal,Floodlight}` LOD glbs, source maps byte-for-byte, `props.json`;
   `prepare_prop_maps.py` → `*_Mask.png`, `*_Emission.png`; `screen/make_terminal_screen.py` → `Terminal_Screen.png`.
   Carl's GLBs are kept unchanged in `meshy_source/` (and his originals in ~/Downloads).
6. `art/vanguard_hall_20260930/author_vanguard_hall.py` → hall GLBs without the box uplights, floodlight mounts and aims.
7. Unity: **Athen Hill → Ward hill → Build assets**, **Install rebuilt hill** (once), **Install Vanguard Hall floodlights**,
   **Add review cameras**, **Verify saved scene** (`Editor/WardHillPass.cs`).

Review renders: `review_hill.py`, `review_props.py`, `review_polyhaven.py` (Blender, Cycles CPU) → `review/`.

Shader: `Shaders/WardGroundCover` is a copy of the Ward Tree (URP 17.6 Lit) shader whose wind bends each vertex by its
height above the object origin (`_WardBendHeight`), driven by the reduced-motion-aware `_AthenAtmosphereTime`.

Heavy media (Poly Haven downloads, blend files, review renders) stays local per `.gitignore`; scripts, JSON and this
README are tracked. Unity-side textures and models are complete for builds.

## Third-party content

Poly Haven (CC0): grass_medium_01, grass_medium_02, cheiridopsis_succulent, crystalline_iceplant, celandine_01,
weed_plant_02, othonna_cerarioides, namaqualand_stones_01, namaqualand_boulder_05, bark_debris_01,
dry_branches_medium_01 (models); sparse_grass, dry_decay_leaves (textures). Authors in `polyhaven/manifest.json`.
Meshy: the terminal and floodlight GLBs were generated by Carl in Meshy and supplied as files (no task ids recorded here).
