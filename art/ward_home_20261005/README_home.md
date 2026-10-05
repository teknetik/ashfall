# The player's home: WallHomeP (5 October 2026)

Carl (5 Oct 2026, ~02:40): "we need a place to store our loot" → rent one of the container homes: "a locker and shelf
rack as the stash, a bunk as a rest and save point". This is the art half of that pass (design: [PROGRESS.md](PROGRESS.md)).
Not yet accepted by Carl.

## What was built

**WallHomeP** is variant P of the 3 Oct converted 20 ft container homes (`art/ward_buildings_20261003`, key `homep`). It
replaces `Wall home south 2` (WallHomeA, world (27.5, 0, −41.4), yaw 0, +Z = street). The exterior is A's: rust container
on dressed stone pads, stone step and planter, madder awning, roof solar, drum, AC, laundry line, porch light and
impact scar. The differences from A:

- **Real door opening.** The cut-in door is a real opening (A's door and window were solid slabs). It has a welded
  box-section frame from the lining to the rail plane, door stops, a worn tread-plate threshold (top y 0.502) nosing
  out over the step, a riveted kick plate on the sill rail and the frame halves of three barrel hinges.
- **Door leaf.** The leaf is its own object, `WallHomeP_DoorLeaf_LOD0` and `_LOD1`, with its origin on the hinge axis
  at the leaf's foot, **(0.86, 0.51, 1.277)**. Rotate it about local +Y: **closed yaw 0, open yaw −176** (parks flat against the face west of the door). It swings
  outward over the step, the usual way for a cut-in steel door, and keeps the interior walk path clear.
  - The leaf is an overlay door, 1.01 × 1.95 m, in weathered teal steel (`WB_TankTeal`). It carries A's three
    stiffeners, a rim, rivets, lever handles both sides, a keyhole and a stencilled **S2**.
  - Paint is worn round the handle and along the pull edge. Rust creeps up from the foot and drips under the ribs.
  - The leaf's free edge sweeps a 1.03 m radius. It clears the awning, the porch lamp, the threshold and both steps.
- **Real window.** The glass is `WS_ClearGlass`, so the real interior shows. It has glazing beads and the five bars
  outside; A's shutter and rain hood are unchanged.
- **Two steps.** A lower stone step (top 0.15 m) was added in front of A's step (0.30 m), so the rises are 0.15, 0.15
  and 0.20 to the 0.50 m floor. All are within the player controller's 0.3 m step offset.
- **Awning.** The awning's street edge is 0.15 m higher, so the opening leaf clears it.
- **Colliders.** There is no solid `COL_Container`. Walls with a door gap, the roof, the floor and the furniture have
  their own colliders (below).

**Interior.** The lining faces run x −2.913..2.953 and z −1.103..1.103. The floor is at **0.50**: hardwood boards on the
0.48 steel plate. The ceiling is at **2.763**, giving 5.87 × 2.21 m and 2.26 m clear.

- **Lining.** Salvaged plywood sheets (`WG_Plywood`) are fixed over the corrugation on battens, with screw heads. A
  few dark composite sheets (`WS_PanelDark`) are mixed in. A riveted steel patch plate covers the lower front wall by
  the battery. A timber skirting runs along the walls.
  - **Missing upper sheet, back wall.** The battens and a mineral-wool batt show, with a second batt sagging and
    peeled forward; the peg rail is screwed across this bay.
  - **Kicked-through lower sheet, east end.** The batt is half gone and the end door shows behind it.
  - **Missing ceiling panel over the rack.** The batts sag between the battens and the roof plate shows.
- **Floor.** Longitudinal boards (`SS_Boards`) run in two or three lengths with staggered joints and rows of screw
  heads. One board is a fresh replacement. A steel plate is screwed over the worn spot where you stand at the locker.
  A ribbed rubber mat sits inside the door, sand has blown in over the threshold, and a striped kilim rug (madder,
  bone, indigo, ochre, fringed) lies in the middle.
- **Bunk** (west end, along the back wall, 1.94 × 0.81 m). It has a welded steel frame (`WB_BlackSteel`): legs with
  rubber feet, angle rails and straps, a barred head end and a foot rail, worn bright where hands grab. It carries:
  - a canvas mattress (1.86 × 0.80 × 0.14) with piping, a pillow, and a madder wool blanket. The blanket is rumpled,
    hangs down the open side and has its top edge turned back. A folded indigo blanket sits at the foot.
  - a shelf over the bunk with books, a small radio with an aerial and two tins, and an AC grille above it.
  - a clip-on reading lamp on the head rail, with its cord running under the bunk to a socket past the foot.
  - a slatted crate as the side table, with a book, a bottle and a candle tin.
  - a canvas duffel under the head end and a yellow crate mount under the middle.
- **Stash locker** (on the back wall facing the doorway, x 0.65..1.55, 0.5 deep, 1.9 high). It is a double-door olive
  steel locker (`WG_OlivePaint`) with:
  - pressed door lips, louvres top and bottom, card holders, hinges and a recessed plinth.
  - a handle housing and lever, and a padlock hasp across the meeting edge with a brass padlock.
  - a stencilled **S2**, chipped paint at the edges, wear round the handle and padlock, and rust at the plinth.
  - a rolled sleeping mat strapped on top.
- **Shelf rack** beside the locker (x 1.66..2.86, 0.45 deep, 4 levels, top 2.30). It is galvanised slotted angle
  with slot rows, foot plates rusting at the floor, ply shelves and back cross-bracing. On it:
  - modelled: three small parts bins with fill, cable and copper coils, a small motor and a geared hub.
  - scanned street-dressing mounts: wooden box, green jerrycan, toolbox, red crate, a yellow salvage crate, a carton
    and an oil tin.
  - beside it, an ammo crate with a red crate on top as spillover.
- **Under the window.** A fold-down timber table (top 1.22) on folding steel brackets and butt hinges, with ring stains.
  On it: a hot plate with an enamel kettle, an enamel mug of tea, a galvanised water jug, a food tin and a spoon. A
  three-legged stool with a ring stretcher stands at it. The inside sill holds a tin of succulents, and a bone cloth
  curtain hangs bunched on a wire.
- **Services and life.**
  - A ceiling cable tray carries cables, one sagging out, and a caged bulb hangs from it.
  - A junction box sits behind the exterior one, with conduit to the tray. A solar charge controller with a cyan
    readout and **status LED**, a battery on the floor, a socket strip and a fire extinguisher on a wall bracket by
    the door complete the power and safety kit.
  - A peg rail on the back wall holds a long leather coat, an indigo scarf with fringes and a felt hat.
  - A mirror shard is glued to the front wall with a photo tucked under it. A paper calendar hangs on a nail by the
    locker. A coil of rope hangs on the east wall, and a pair of boots stands by the door.

Lettering and images are authored and in-world: the **S2** stencils, plus the photo and calendar textures, which
contain no lettering or digits.

## Files

| File | What |
| --- | --- |
| `home_interior.py` | Variant P: `shell()` (exterior with real openings), `door_leaf()`, the interior, `record()` (colliders, anchors, lights, mounts, decal hints) and `build(s)`, which wraps `s.finish` so the interior parts and the leaf are exported |
| `art/ward_buildings_20261003/author_buildings.py` | Guarded hooks in `wall_home()`/`wall_home_lod2()` for `"P"` and the `homep` key in `BUILDINGS`; A/B/C paths are unchanged |
| `unity/AthenHill/Assets/AthenHill/Art/WardBuildings/Models/WallHomeP_LOD0/1/2.glb`, `homep.json` | The outputs; `art/ward_buildings_20261003/homep-source.blend` is the source |
| `textures/HP_Insulation.png`, `HP_Photo.png`, `HP_Calendar.png` | Authored textures for the new materials (`make_textures.py`) |
| `verify_variants.py` | Re-authors container variants into `scratch/<tag>/` and compares them with the committed records (never writes to Assets) |
| `review_home.py`, `review/` | Cycles CPU review renders with preview materials built from the Unity `.mat` files, the record's prop mounts and lights, and 1.8 m scale figures with the 0.7 m capsule footprint |
| `concept/home_concept_v1.png`, `concept/prompts.json` | One Codex concept used as an art-direction target (not a render of the asset) |

To rebuild, run `~/.local/state/ward-programme/blender.sh art/ward_buildings_20261003/author_buildings.py -- homep`.
To re-check A/B/C, run `blender.sh art/ward_home_20261005/verify_variants.py -- <tag> homea homeb homec`.

**A/B/C check (5 Oct, after the P edits, `logs/verify-after.log`).** homea/homeb/homec json identical; every LOD
identical in triangles and (sorted) vertex positions, except `WallHomeB_Rubble_LOD1`. That one is nondeterministic in
the untouched script too (bevels iterate Python sets; its hash differs between every run, the baseline included). The
committed A/B/C files are byte-identical before and after authoring P (`logs/abc-md5-before.txt`).

## Triangles

| LOD | Total | Breakdown |
| --- | --- | --- |
| LOD0 | 36,167 | exterior 6,819 (A was 5,676) · lining 1,531 · floor 1,265 · metal 5,221 · cloth 8,848 · props 6,323 · hardware 3,716 (screws, rivets, slots: no shadows) · glow 260 · door leaf 1,596 · locker stencil 588 |
| LOD1 | 10,569 | exterior 2,884 · lining 554 · floor 30 · metal 2,630 · cloth 1,168 · props 1,763 (small props dropped, book block, radio case) · glow 120 · door leaf 832 · stencil 588 |
| LOD2 | 24 | exterior box only (A's LOD2 in rust) |

The street-dressing mounts carry their own LODs.

## Record (`homep.json`, building-local metres)

**Anchors**

| Name | Value |
| --- | --- |
| `door_hinge` | pos (0.86, 0.51, 1.277), axis +Y, `closedYaw` 0, `openYaw` −176 (parks flat against the face west of the door), swing outward, radius 1.03 |
| `door_centre` | (1.375, 0.502, 1.16): floor at the middle of the doorway |
| `door_outside` | (1.375, 0.30, 1.62): upper step, inside the swing |
| `door_clear_outside` | (1.375, 0.15, 2.4): beyond the swing |
| `door_inside` | (1.375, 0.50, 0.62) |
| `locker_use` | (1.1, 1.5, −0.3), yaw 180; 1.0 m above the floor, 0.3 m in front of the doors |
| `bunk_use` | (−1.85, 1.5, 0.05), yaw 180 |
| `wake_point` | (−1.7, 0.5, 0.2), yaw 90 (facing the room and door) |
| `interior_bounds` | centre (0.02, 1.6315, 0.0), size (5.866, 2.263, 2.206) |

**Colliders.**
- Exterior: `COL_AwningPoleW/E`, `COL_Planter`, `COL_Step` (A's), `COL_StepLow`.
- Shell: `COL_Floor` (y 0..0.50), `COL_Roof`, `COL_WallBack`, `COL_WallWest`, `COL_WallEast`, `COL_WallFrontWest`
  (to x 0.90) and `COL_WallFrontEast` (from x 1.85), which leave a 0.95 m door gap, and `COL_DoorHead`.
- Furniture: `COL_Bunk`, `COL_BunkHead`, `COL_Locker`, `COL_Rack`, `COL_Table`, `COL_Stool`, `COL_SideCrate`,
  `COL_Battery`, `COL_CrateStack`.
- **`COL_DoorLeaf`**: the closed position, with `local_center` relative to the hinge so it can live on the leaf.

**Lights.**
- The porch light (A's, on the clock).
- **Home ceiling light**: point (0, 2.56, 0), warm, intensity 2.0, range 5.0, soft shadows.
- **Home reading lamp**: spot from the lamp's bulb at the pillow, 75°/40°, intensity 1.3, range 2.6.
- **Home status LED**: point (−0.07, 1.64, 1.056), cyan, intensity 0.12, range 0.7, no shadows.
- All three home lights are marked `"interior": true, "clock": false`. **InteriorGlow (bulbs, LED, readout) must not
  cast shadows**: the lights sit inside those meshes, and the first review render was black because of exactly this.

**Mounts.** A's (AC, water barrel, bucket) plus ten interior street-dressing prefabs (`SD_*`, flagged
`"interior": true`). Pivots are at the footprint centre on the shelf or floor, with front +Z.

**Decal hints** for the Unity pass (optional): floor scuffs inside the door and at the locker (`WL_DecalMarks`), grime
round the inside handle (`WG_DecalGrime`), a damp stain under the AC grille (`WL_DecalDamp`) and dust on the
threshold (`WG_DecalSandSpill`).

**Walk paths** (checked on the plan render with the 0.7 m capsule footprint):
- Door → locker: straight, 0.95 m wide and 1.7 m deep.
- Door → bunk side: 0.88–0.92 m between the blanket's hang and the stool and table.
- Overhead: nothing below 2.50 m in the paths (cage bottom 2.50, tray 2.69, door head 2.44 at the threshold).

## Materials

**Existing materials, reused by name.**
- Shell and exterior: `WS_ContainerRust`, `WB_BlackSteel`, `WB_TankTeal`, `VH_Steel`, `VH_Dark`, `WS_Deck`,
  `WG_RustSteel`, `WS_PaintOlive`, `WS_ClearGlass`, `VH_Ashlar(Rough)`, `VH_Sand`, `WS_ClothMadder`, `WB_SolarPanel`,
  `WB_PaintBone`, `VH_PaintedSteel`, `NF_WallLampBulb`.
- Interior surfaces: `WG_Plywood`, `WS_PanelDark`, `WG_PlateSteel`, `SS_Timber`, `SS_Boards`, `WG_Rubber`,
  `WG_OlivePaint`, `WG_BonePaint`, `WB_CylRed`, `WB_CylBone`, `WB_StencilPaint`.
- Cloth: `WS_ClothBone/Indigo/Ochre/Madder`, `WS_Hide`, `FS_Canvas`, `FS_Webbing`, `FS_Felt`, `WG_Hessian`,
  `WL_HessianOld`.
- Small props: `SS_Enamel`, `SS_BulbWarm`, `VH_Brass`, `VH_Bronze`, `VH_Rubber`, `WS_PaintRed`, `WS_PaintYellow`,
  `WB_LedCyan`, `WB_ScreenCyan`.

`WardBuildingsPass`'s material search does not cover `SS_*` (Art/SalvageShop/Materials), `FS_*`
(Art/FieldSupply/Materials) or `WL_*` (Art/WardLife/Materials). The install must add those folders.

**New materials the Unity pass must create** (URP Lit):

| Name | Base map | Base colour | Smoothness | Metallic | Notes |
| --- | --- | --- | --- | --- | --- |
| `HP_Insulation` | `textures/HP_Insulation.png` (tiles every 0.5 m: scale 2) | white | 0.05 | 0 | mineral wool |
| `HP_Mirror` | none | (0.86, 0.87, 0.88) | 0.94 | 1 | needs the interior reflection probe |
| `HP_Photo` | `textures/HP_Photo.png` (exact 0–1 UVs, clamp) | white | 0.55 | 0 | |
| `HP_Calendar` | `textures/HP_Calendar.png` (exact 0–1 UVs, clamp) | white | 0.15 | 0 | |
| `HP_Succulent` | none | (0.33, 0.43, 0.30) | 0.45 | 0 | |

The ribbed `VH_Paint` texture (behind `WS_PaintTeal/Olive`, `VH_PaintedSteel`, `WB_PaintBone`) made flat doors and
lockers read as roller shutters in review. The door leaf, locker, bed frame and boxes therefore use flat paints
instead: `WB_TankTeal`, `WG_OlivePaint`, `WB_BlackSteel`, `WG_BonePaint`.

## Review (Blender Cycles on the CPU, 1280 × 720; not the game's render)

**Renders.** In `review/`; `p5_*`/`p4_*` are current, while `p1`–`p3` record the fix rounds.
- `ext_closed`, `ext_open` (door open), `p5_lod1_ext_open_night` (LOD1 at night).
- `doorway_west` (doorway to bunk), `doorway_east` (doorway to locker and rack).
- `locker`, `bunk`, `inside_out` (bunk to door), and `plan` (top-down with figures and capsule footprints).

**Not mirror-imaged.** The renders match the game: from the street the door is on the viewer's left, as in the
game's `cam_wb_home_south` capture.

**Fixed in review.**
- The interior rendered black: the lights were inside opaque bulbs.
- The ribbed paint read as shutters.
- The rust strip on the door looked toothy.
- The insulation read as white boards; it now uses a fibrous texture.
- The mattress poked through the blanket.
- The rug wear patch read as a sheet of paper.
- The scarf read as trousers.
- The coat was flat paper-white; it is now `WS_Hide`.
- The locker handle wear was an oversized blob.

**Compared with the concept** (`concept/home_concept_v1.png`): the layout and furniture vocabulary match, and the
locker and rack read strongly.

**Remaining defects** (honest assessment):
- **Density.** The concept is denser: more items under the bunk and on every shelf, a runner rug the full length, and
  heavier, more varied wear. The home reads tidy and a little sparse at the ceiling and the east end.
- **Wear is geometric only.** It is patches and plates, because URP Lit ignores the kit's vertex tint and occlusion.
  Floor traffic wear relies on the mat, the rug, the plate and the optional decals.
- **Coat** is a simple loft: it reads as a coat at room distance but is stiff, with no collar or lapels. The scarf and
  hat are simple too.
- **Blanket** rumples are gentle procedural folds, not a cloth simulation.
- **Photo and calendar** are stylised and graphic, not photographic.
- **Not judged in-engine.** Colours and brightness are approximations; the real look needs Unity captures.

## Open issues for the Unity pass

- **Door leaf.** Both GLBs contain a leaf. Either swing both LOD leaves or use the LOD0 leaf as one moving child
  outside the LODGroup (recommended). `COL_DoorLeaf` belongs on the leaf, using `local_center`.
- **Open on approach.** The outward swing passes over the step. Open it while the player is still ~2.4 m away, so
  the leaf never sweeps through them.
- **Interior light layer.** Put the interior parts on the interior light layer with an `InteriorLighting` probe and a
  reflection probe, as in the Salvage and Field Supply shops. InteriorGlow and InteriorHardware must not cast shadows.
- **Step height.** Confirm the 0.15/0.15/0.20 m steps with the real `CharacterController` in the native check.

## Unity install (Phase 2, 5 Oct 2026): `Editor/WardHomePass.cs`

Run: `~/.local/state/ward-programme/unity.sh LOG AthenHill.Editor.WardHomePass.RunBatch --steps models,install,verify -nographics`

**Graphics steps:**
- `bake`: interior reflection probe, with the EXR clamped; it drops any light data URP adds outside the pass.
- `capture:HOUR:cam+cam[:open]`: at most 6 cameras per run; never saves.

**Rollback:** `uninstall`, or the scene copy `unity/evidence/ward-home/20261005/rollback/scene-before-first-install.unity`.

### `models`

- **Materials and textures.** `HP_*` materials go in `Art/WardHome/Materials`, textures in `Art/WardHome/Textures`.
  The material search covers `WardBuildings`, `VanguardHall`, `WardShops`, `WestGate`, `TrainingRange`,
  `WestGateArches`, `NightFacade`, `SalvageShop`, `FieldSupply`, `WardLife` and `WardHome`. 0 unmapped.
- **Prefab.** `Prefabs/WardBuildings/WallHomeP.prefab`, with a LODGroup at 14/55/450 m like the other wall homes.
  LOD0/1/2 are 36,167 / 11,333 / 24 triangles; LOD1 uses the LOD0 leaf.
- **Door leaf.** A `Door leaf` child at the hinge carries the LOD0 leaf mesh and `COL_DoorLeaf`. It is not static.
- **Colliders and mounts.** 22 colliders sit under `Colliders`. A's three exterior mounts are under `Fittings`. The ten
  interior street-dressing mounts are under `Interior fittings`, unshadowed on the interior layer.
- **Lights.** The porch light is under `Practical lights`. Three unshadowed interior lights on layer 7 are under
  `Interior lights`.
- **Gameplay children.**
  - `WardHome` on the root: lease 40, 60 slots, feeds the bench.
  - `Door` at `door_centre`: `HomeDoor` (closed 0 / open −176, open distance 2.4, leaf collider) and a
    `WorldInteractable` "E · Locked door" with range 2.0.
  - `Locker` ("E · Open the locker", 1.6) and `Bunk` ("E · Rest on the bunk", 1.6).
  - `Wake point` (yaw 90) and `Camera zone` (`CameraConfineZone` over `interior_bounds`).

### `install`

- **Scene root.** A new root, "Ward home", sits at the transform of `Ward building: wall homes (rust)/Wall home south 2`:
  world (27.5, 0, −41.4), yaw 0, verified in the scene. That WallHomeA instance is set inactive, never deleted.
- **Instance and references.** The instance "Player home (WallHomeP)" gets `GameSession` and `FollowCamera` as
  overrides.
- **Lighting.** `InteriorLighting` gets the 3 lamps and 15 interior renderers, plus the interior fittings. Its portal
  rectangle covers the door and the window together. An interior reflection probe is box-projected over the room.
  The porch light is on the Ward lighting clock, practical and night-only, as A's was.
- **Landmarks** under `AthenDebugBridge.landmarks`:
  - `home_door` (28.875, 0, −38.64): 1.68 m from the door.
  - `home_inside` (28.875, 0.5, −40.78).
  - `home_locker` (28.6, 0.5, −41.65): 1.0 m from the locker interactable.
  - `home_bunk` (25.8, 0.5, −41.2): 1.02 m from the bunk interactable.
- **Review cameras:** `cam_home_street`, `_door`, `_inside_bunk`, `_inside_locker`, `_locker` and `_bunk`.

### `verify`

Output: `unity/evidence/ward-home/20261005/verify.json`. All checks clean:
- installed and prefab-linked, with no missing materials;
- the old instance is inactive and the new one sits exactly at its transform;
- every component field is wired;
- the landmarks are inside or outside as named;
- the leaf collider is enabled and blocks the closed doorway;
- a capsule (r 0.3, h 1.8, ignoring the bottom 0.3 m step offset) is clear on all three routes:
  `home_door` → lower step → step → threshold → `home_inside`, `home_inside` → `home_locker`, and
  `home_inside` → `home_bunk`. The door is open for these runs (leaf collider off).
- the review cameras are not inside colliders;
- no scenery is inside the leaf's swing. Nanofab 2's south-west pier starts 1.9 m in front of the container face; the
  leaf sweeps to 1.1 m.
- **Scene diff:** the saved scene YAML against the pre-install copy has no unexpected documents. Against the
  pre-first-install copy, the only differences are this pass's 56 new documents, the light circuit, the landmarks
  parent, the WallHomeA active flag and the scene roots.

### Unity captures

Taken with the editor at 13:00 with the door open, in `unity/evidence/ward-home/20261005/editor/open/`.
- **Read well:** `cam_home_street`, `_inside_bunk`, `_inside_locker`, `_locker` and `_bunk` all read as intended.
- **Since fixed, not yet re-captured in Unity:**
  - `cam_home_door` was inside Nanofab 2 and has been moved.
  - The floor read as small tiles, because the timber grain crossed the boards; the UVs now follow each board's
    length.
  - The insulation read as a saturated yellow board; it has a new muted texture.
  - The CPU Blender renders `review/final_*` show the fixes. The combined batch's lookbook will show them in Unity.

### Note for the main session: URP light data

The first bake saved URP's auto-added `UniversalAdditionalLightData` onto 13 lights outside this pass: Field Supply
lamps, a Ward night-life street lamp and wall lamp, Watchtower SE, Nanofab 2, WallHomeB's porch light and West Gate
arch B. They were default components URP adds whenever a light renders. `revertlightdata` removed exactly those
(`unity/evidence/ward-home/20261005/revert-light-data.json`), and `bake` now drops any it adds. FieldSupplyShopPass's
bake can do the same thing.
