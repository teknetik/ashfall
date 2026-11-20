# Outer Berms ground variety (20 November 2026, showcase phase 2)

The Outer Berms bowl (about 495 x 425 m west of the West Gate) read as one flat sand look between the sites. This pass is
**additive**. It doesn't move or change sites, encounters, spawns, loot, the road, the range, the waystation, landmarks
or any existing collider, and it doesn't change the walkable ground mesh or its collider. It adds three things:

1. **Ground regions in the material.** The 54 expansion ground tiles (`Outer Berms/Berms expanse/Ground`, 108 LOD
   renderers) now use `Art/BermsVariety/Ground/BermsVarietyGround.mat`, shader *Athen Hill/Berms Ground V3*. That is
   Berms Ground V2 plus a region mask over the whole bowl (`BermsVarietySplatA/B.png`, 2048², 0.25 m per texel over
   x −572…−60, z −256…256). The regions are:
   - clay pans: closed, flat hollows with crisp edges and a sand fringe;
   - dried silt in the wash channels, and braided gravel bars;
   - hardpan: packed flats at a 60–150 m scale;
   - wind-laid sand in the lee (ENE side) of the mesa, knoll, butte, ridges, dunes and berm lines, plus sand sheets
     and hollows;
   - gravel fans below rock and along the mountain foot, with desert varnish on the old, far parts of each fan and on
     pavement lag;
   - wheel and track marks, in the relief channel: two-rut Warden trails along the five `sites.json` routes, the
     braided Karaveen trail past the caravan ambush and out to the north-west, half-buried haul-droid treads from the
     depot side, and the Post sentinel wheel loops;
   - crater bowls with blast scorch and radial rays, glassed centres on about 30 % of craters, and burn scars under the
     battle wrecks.

   Every region reuses the V2 texture layers, recoloured, so the bowl still matches the basin and the old Berms
   ground. All weights fade to zero 4–18 m from the playable edge and 12–30 m from the old ground, which keeps V2 and
   its road splat.
2. **Scene root `Outer Berms/Berms variety`.** It holds these groups:
   - *Earthworks*: 10 segments, 289 m of old Warden berm lines and three redoubts, 1.3–1.6 m high and walkable, with
     breaches where trails, washes and sites are;
   - *Dunes*: 7 dunes across the wind;
   - *Craters*: 13 raised rims. The bowls are painted, because the ground may not be dug;
   - *Outcrops*: 15 sandstone ledges, tors and tilted slabs on the basin's `SandstoneBasinV3.mat`, so they have the
     same strata as the mountains;
   - *Wreckage*: 34 half-buried kit pieces. These are a drone-bay wreck, a processing-hall ruin, a conveyor spine, a
     yard fence line, a toppled crane, dead workers and drones in front of the lines, and spent cells and slumped
     sandbags on and behind them;
   - *Clusters*: 258 kit pieces placed for a reason. These are talus and shade scrub at the ledges, scrub and dead wood
     in the washes, five rockfalls below the mountain foot, Karaveen litter along the trail, and dead shrubs at the pan
     margins;
   - *Berms variety review cameras*: 14 `cam_bv_*` cameras.
3. **Footsteps.** `FootstepAudio` gained an additive *Berms variety map*: 256² cells at 2 m, giving sand, gravel or
   stone. Before this pass, the expansion tiles matched no collider rule and always played *Stone*. Now the tiles,
   earthworks, craters and dunes read the map. Counts are 6.5k stone (clay, hardpan, glass), 10.3k sand and 48.8k
   gravel cells (fans, tracks, natural scree). The old Berms ground map is unchanged.

Lore basis (`lore.md`): the Wardens' "hard-fought stands at the outer berms" and "night actions against
self-replicating machine swarms", and the Outer Berms' "half-buried ruins … collapsed processing halls, rusted conveyor
spines, shattered drone bays". The lines, craters and wrecks are unnamed remains of those stands. No new history is
added.

## Files (this folder)

- `bv_common.py`: heightfield access, sites, routes and the survey.
- `cameras.py` → `review_cameras.json`.
- `layout.py` → `features.json` (earthworks, ledges, dunes, craters, tracks), `placements.json` (prefabs; chunks are
  filled in by `meshes.py`) and **`layout-check.json`** (every trimmed, nudged or rejected item and why, and the final
  clearances).
- `masks.py` → the two splat PNGs, `footsteps.json`, `work/regions_preview.png` and `work/regions_stats.json`.
- `meshes.py` → `Art/BermsVariety/Meshes/BermsVarietyRelief.glb` (`<Group>_NN_LOD0/_LOD1/_COL`; written straight from
  numpy) and `mesh.json`.
- `material.json`: the V3 values on top of a property-by-property copy of `BermsGroundV2.mat`.
- `plot_plan.py` → `work/plan.png` (plan of sites, markers, features and cameras).
- `survey.json`: the saved scene's gameplay markers and colliders, written by the installer's `survey` step.

Python steps run in order through `~/.local/state/ward-programme/heavy.sh uv run --with numpy --with scipy --with pillow
--with matplotlib python <script>`: `layout.py` → `masks.py` → `meshes.py`. `layout.py` must run before `masks.py`
because the masks read the berms, dunes and wreck positions.

**Layout check.** Clearances in metres, by class:

| Class | Spawn | Loot / interactable | Landmark | Site centre | Route / trail | Existing collider | Playable edge | Old ground |
|---|---|---|---|---|---|---|---|---|
| Ledge | 25 | 10 | 8 | 30 | 6 | 3 | 8 | 14 |
| Berm | 15 | 8 | 6 | 24 | 5 | 3 | 7 | 14 |
| Dune | 12 | 8 | 6 | 22 | 5 | 3 | 6 | 14 |
| Rim | 8 | 6 | 4 | 16 | 2.5 | 2 | 6 | 14 |
| Wreck | 20 | 8 | 6 | 26 | 5 | 3 | 8 | 14 |
| Boulder | 14 | 5 | 4 | 22 | 3.5 | 2 | 5 | 12 |
| Small | 5 | 3 | 3 | 18 | 1.5 | 1 | 4 | 10 |

The Karaveen trail and haul treads count as routes for blocking objects. Berm lines are cut where they would cross a
route, a wash, a site or an existing collider. Report: 0 problems among kept items. Rejected and nudged items are listed
with their reasons.

## Unity

`Editor/BermsVarietyPass20261120.cs`, run as `RunBatch --steps …`:

| Step | What it does |
|---|---|
| `survey` | Read-only. Writes `survey.json`. |
| `material` | Mask importer settings: BC7, linear, mips, clamp. Builds the V3 material. |
| `install` | Re-runnable: deletes its own root first. Swaps the tile material, builds the chunks with LODGroups and MeshColliders, places the prefabs, applies the footstep map and adds the cameras. |
| `verify` | → `unity/evidence/showcase_phase2/20261120/berms_variety/verify.json`. See below. |
| `toggle:on` / `toggle:off` | The A/B switch: root active, tile material V3 or V2, footstep map. |
| `rollback` | Same as `toggle:off`. The root stays inactive so it can be recovered. |
| `uninstall` | Deletes the root after rollback. |
| `cost:cam+cam` | Draws and triangles per view → `cost.json`. |
| `capture:HOUR:cam+cam[:before\|after\|both]` | Graphics run, at most six cameras. Poses come from `review_cameras.json`. `before` and `after` switch the pass in memory only; the scene is never saved. |
| `shaderinfo` | Diagnostic. |

`verify` checks the root and the tiles on V3, the mask textures, missing materials and scripts, broken prefab links,
LOD triangles, that every surveyed gameplay marker is still at its surveyed position, that no collider of this pass is
within 2–3 m of a spawn, loot node or landmark (overlap capsule), the footstep map, and a droid's-eye check (below).

Commands, from the repository root:

```
P2=~/.local/state/ward-programme/showcase-phase2-20261120
$P2/seq.sh install berms_variety-N AthenHill.Editor.BermsVarietyPass20261120.RunBatch material,install,verify
$P2/seq.sh install berms_variety-N AthenHill.Editor.BermsVarietyPass20261120.RunBatch toggle:off   # A/B "off" and rollback
$P2/seq.sh install berms_variety-N AthenHill.Editor.BermsVarietyPass20261120.RunBatch toggle:on
```

The pre-install scene is `~/.local/state/ward-programme/showcase-phase2-20261120/scenes/before-berms_variety-2.unity`.

**Edit.** Change `layout.py` (anchors, clearances), `masks.py` (region rules) or `material.json` (colours,
`_VarStrength`), then re-run the Python chain and `material,install,verify`. Inspector edits to the V3 material are
overwritten by `material`. Prefab instances can be moved in the scene, but `install` rebuilds them from
`placements.json`. Don't edit the GLB.

## Results (saved scene, 20:3x)

**verify: PASS.** 0 problems, 0 gameplay markers moved, 0 crowded. 108/108 tile renderers are on V3. 292 prefab
instances with no broken links, 0 missing materials, 0 missing scripts.

**Droid's-eye check.** Rays go from each of the 59 spawns' eyes (1.4 m) to a player's chest on rings at 18 m and 30 m:
12 of 4,194 rays (0.3 %) are blocked first by this pass's geometry, and no spawn is over 15 %. New cover is in the
approaches between sites, not in the fight rings.

**Relief chunks:** 45 chunks, 60.7k triangles at LOD0 and 12.6k at LOD1:

| Group | LOD0 tris | LOD1 tris |
|---|---|---|
| Earthworks | 9.9k | 1.4k |
| Dunes | 6.8k | 1.0k |
| Craters | 11.2k | 2.1k |
| Outcrops | 32.6k | 8.2k |

**Cost estimate** (`cost` step, `cost.json`): this pass's renderers in each view, with LODGroups at PC lodBias 2 and
frustum culling. It is an estimate, not a GPU measurement.

| View | Colour draws | Colour triangles | Shadow casters within 150 m (triangles) |
|---|---|---|---|
| `cam_bv_bx_gate_west` (out of the West Gate) | 181 | 206k | 10 (66k) |
| `cam_bv_long_gate` (across the bowl) | 165 | 202k | 17 (73k) |
| `cam_bv_long_far` (back across the bowl) | 145 | 212k | 46 (91k) |
| `cam_bv_relay_scrapyard` (between sites) | 48 | 65k | 43 (197k) |

Most of these draws are the kit prefabs: each Poly Haven boulder or scrub piece is up to 18k triangles at LOD0, with
its own LODGroup. The relief meshes are about 45 draws at most. The tile material adds no draws but costs more per
pixel (two more texture samples and a relief normal). Only the orchestrator's native A/B can price that.

## Evidence and what was looked at

**Looked at with my own eyes:**
- `work/plan.png` and `work/regions_preview.png`.
- Matplotlib previews of one ledge, one berm and one crater rim (`work/mesh_preview.png`).
- One graphics run (20:23, before the memory rule change) of six cameras at 13:00 and 17:00, before and after.
  - Files: `unity/evidence/showcase_phase2/20261120/berms_variety/editor/{before,after}/<cam>_<13.0|17.0>.png`.
  - Stacked pairs (before on top): `…/berms_variety/pairs/<cam>_<hour>.jpg`.
  - Cameras: `cam_bv_northgate_caravan`, `cam_bv_scrapper_waystation`, `cam_bv_waystation_relay`,
    `cam_bv_caravan_derrick`, `cam_bv_relay_scrapyard` and `cam_bv_long_gate`.

**Honest reading of those captures.** They show the first mask and material version:
- **Better.** Clay pans, wash silt, ripple fields, dunes and berm forms now break the floor into distinct grounds
  (`waystation_relay`, `scrapper_waystation`, `long_gate`).
- **Too much wind sand.** Ripples were too strong and corrugated.
- **Karaveen trail.** Its packed band read as a broad, flat, featureless strip (`northgate_caravan` after looks
  *flatter* than before).
- **V2 lag patches.** The old pale lag patches that gave V2 some breakup disappeared under the regions.

After that I made these changes (masks.py, material.json):
- less sand (lee and sheets);
- ripples at ×1.0 instead of ×1.6;
- more and darker hardpan;
- greyer fan gravel;
- track compaction 0.8 → 0.5 and a much weaker packed band.

Those changes are **installed and verified but not seen**. Graphics captures were stopped by the orchestrator's memory
rule.

**Not looked at:**
- 8 of the 14 cameras.
- Any view of the outcrops, earthworks or wreck fields close up.
- Night.
- The droid's-eye view as pictures (only the ray statistics above).

## Pending (needs Unity and the GPU to myself)

1. **Graphics captures (before and after), both at 13:00 and 17:00, three runs (6 + 6 + 2 cameras).** The pass is installed,
   so "before" is produced in memory by the capture step's `before` mode (root off, tiles on V2, footstep map off). The
   scene is not saved.
   - Run A: `cam_bv_northgate_caravan`, `cam_bv_waystation_relay`, `cam_bv_mesa_dunes`, `cam_bv_scrapyard_pylon`,
     `cam_bv_pylon_westfans`, `cam_bv_southridge_scrapyard`.
   - Run B: `cam_bv_relay_postrelay`, `cam_bv_long_far`, `cam_bv_bx_gate_west`, `cam_bv_bx_scrapyard`,
     `cam_bv_long_gate`, `cam_bv_scrapper_waystation`.
   - Run C (two cameras, 14 in all): `cam_bv_caravan_derrick`, `cam_bv_relay_scrapyard`.
   - The command, per run, is the one below with `CAMS` replaced by the `+`-joined names:
     `DISPLAY=:0 WAYLAND_DISPLAY=wayland-1 ~/.local/state/ward-programme/unity.sh $PWD/unity/evidence/showcase_phase2/20261120/berms_variety/capture-2.log AthenHill.Editor.BermsVarietyPass20261120.RunBatch --steps capture:13:CAMS:both,capture:17:CAMS:both`
2. **A fix round from those captures.** Likely items: sand amount and colour, how the trail reads, hardpan contrast,
   and how the outcrops look against the mountains.
3. **Edit Mode suite** (`$P2/seq.sh tests berms_variety`). It was not run. `FootstepAudio.cs` changed (additive fields
   and one branch), so it should be run.

## Proposed text for unity/EDITING.md

> ## Outer Berms ground variety (20 November 2026)
> The bowl's ground tiles (`Outer Berms/Berms expanse/Ground`) use `Art/BermsVariety/Ground/BermsVarietyGround.mat`
> (shader *Athen Hill/Berms Ground V3*: V2 plus a region mask over x −572…−60, z −256…256: clay pans, hardpan, wind sand,
> gravel fans with desert varnish, wash bars and silt, wheel and track marks, scorch, glass and crater bowls). The masks
> and region rules come from `art/berms_variety_20261120` (`masks.py`); colours and strengths are in `material.json`
> (`_VarStrength` 0 = V2 look). Scene root **Outer Berms/Berms variety**: Earthworks, Dunes, Craters (generated meshes on
> the same ground material, MeshColliders, walkable), Outcrops (sandstone ledges on SandstoneBasinV3, colliders), Wreckage
> and Clusters (kit prefabs), review cameras `cam_bv_*`. `FootstepAudio`'s *Berms variety map* gives sand, gravel or
> stone on the tiles and earthworks. Re-run `layout.py` → `masks.py` → `meshes.py`, then
> `BermsVarietyPass20261120.RunBatch --steps material,install,verify` (install is re-runnable and rebuilds the root);
> A/B and rollback: `--steps toggle:off|on`. Don't edit the GLB or the root's children by hand: `install` rebuilds them.
> Never move an object onto a spawn, loot node, trail or site: `layout.py`'s clearances and `verify`'s marker and
> droid's-eye checks guard that.

## Proposed AGENTS.md section 3 row

> | Outer Berms ground variety | 20 Nov 2026 (`art/berms_variety_20261120`, `Editor/BermsVarietyPass20261120.cs`, scene root **Outer Berms/Berms variety**): the 54 expansion ground tiles on *Berms Ground V3* (bowl-wide region mask: clay pans, hardpan, lee sand, gravel fans with varnish, wash bars and silt, Warden/Karaveen/haul/sentinel tracks, scorch, glass and crater bowls; old Berms ground keeps V2); 289 m of old Warden berm lines and redoubts, 7 dunes, 13 crater rims, 15 sandstone ledges/tors/slabs (60.7k/12.6k tris LOD0/1, colliders), 34 half-buried wrecks (drone bay, processing hall, conveyor spine, crane, battle remains) and 258 purposeful kit pieces; footstep map sand/gravel/stone over the bowl. Additive: no site, spawn, loot, route or existing collider moved (verify PASS, droid's-eye 0.3 % of rays blocked by the pass). One root plus `toggle:off` for A/B. Editor captures of 6 views only (first version); not natively tested; not yet accepted by Carl. |

## World map

The world map's survey picture (`WorldMapInstall20261119` `survey`) is a top-down render of this ground. It now
**needs re-rendering**, because the regions, berms, ledges and wreck fields change the bowl as seen from above. This
pass didn't run that installer.

## Sources and licences

- Terrain shapes, masks and relief meshes are procedural and original (this folder).
- Textures are the existing V2 layer arrays: Poly Haven CC0, as recorded in `art/berms_road_20261001`.
- Prefabs are existing kit pieces: Poly Haven CC0 scans, Blender-authored kits and earlier Meshy pieces (see their
  records).
- No new downloads, no Meshy credits, no OpenAI images.

## Open defects and limits

- Craters are painted bowls with a raised rim, not real depressions, because the ground mesh is locked. A true dig
  would need a ground-mesh change (not made).
- No bones: there is no CC0 bone asset in the project.
- Prefab draw count at long views (~145–180) is the main cost risk. If the A/B shows it, the fix is to merge cluster
  pieces into per-zone chunks or cull them earlier.
- The ledges are low-poly strata cakes (2.2k triangles each) and have not been judged in-game close up.

## Fix round 1 (20 Nov 2026, 21:30–22:00, from the orchestrator's native lookbook of build `batch-p2-b1`)

**What the native frames showed.** I looked at them myself: `unity/evidence/showcase_phase2/20261120/qa/b1/lookbook-*`,
14 cameras at 13:00 and 20:50.
- **Ledges.** On `SandstoneBasinV3` they showed barcode streaks: the basin shader's side projection stretched at close
  range. Their shapes were stepped boxes.
- **Ripples.** A regular 2–4 m corduroy covered most of the sand.
- **Middle distance.** From 50 to 200 m it was mostly one sand tone.
- **20:50 frames.** The regions read under the moon: pans and washes are pale, berm lines are visible. Glassed and
  scorched patches went near-black, like holes, because a smooth dark surface reflects the night sky
  (`cam_bv_long_gate`, `cam_bv_mesa_dunes`). Outcrops are dark silhouettes at night; that is acceptable.

**Changes** (installed by run `berms_variety-9`; verify PASS, 0 problems, droid's-eye 9 of 4,194 rays):

1. **Outcrops, rebuilt.**
   - *Material:* a new `Art/BermsVariety/Rock/BermsVarietyRock.mat` (URP Lit) on Poly Haven **Cliff Side** (CC0,
     1.83 m scan, fetched by `fetch_polyhaven.py` into `polyhaven/`, provenance in `polyhaven/manifest.json`). The walls
     carry cylindrical UVs at 2.3 m per tile with v = world height, so the bedding in the scan runs level.
     `SandstoneBasinV3` is no longer used.
   - *Walls:* about 0.45 m × 0.3 m grids. They have a foot flare, a rounded top chamfer instead of steps, recessed soft
     beds that follow world height, vertical joints, and two octaves of noise.
   - *Outlines:* rounder, with lobes (superellipse 2.1–2.8 instead of 4).
   - *Cap and foot apron:* a second mesh on the ground material. The apron is drifted sand against the wall, higher and
     longer on the lee side, so each outcrop sits in the floor.
   - *Fallen blocks:* 8 tilted blocks broken off the long ledges (23 outcrop objects now).
   - *Talus:* 8 boulders per ledge, smaller, allowed to lie on the apron.
2. **Ripples** (shader V3, the ripple block only).
   - Direction turns by up to about ±40° over 100 m and ±17° over 11 m.
   - Wavelength and amplitude vary with low-frequency noise, and the crest warp is stronger, which adds forks and
     dislocations.
   - Large ripples (1.2–3 m) appear only in patches of wind-laid sand: lee, dunes and sheets, times a patch noise.
   - New fine ripples (6–20 cm) appear only within about 35 m.
   - Both fade out over hardpan, gravel and tracks.
3. **Middle distance.**
   - Varnished lag sheets at 100–250 m: dark brown gravel.
   - Wind sand cut from 23 % to 19 % of the bowl.
   - Clay pans: more of them, paler (0.80 / 0.74 / 0.64).
   - Hardpan darker (0.44 / 0.33 / 0.25); fan gravel greyer.
   - Bowl shares now: gravel 36 % (varnished share 31 %), sand 19 %, hardpan 12 %, clay 6 %.
   - Earthworks are 0.25 m higher and 1 m wider, and three more lines were tried. 364 m survive the layout check, up
     from 289 m, in 11 segments.
4. **Glass and scorch.** Glass smoothness 0.78 → 0.5, glass colour 0.11 → 0.17, scorch multiplier lighter, so night
   frames should no longer show black holes.

**New counts.**
- 55 relief chunks: 73.6k triangles at LOD0, 20.6k at LOD1.
- 349 prefab instances.
- 23 outcrops, each with two renderers (rock and ground) plus a shadow proxy.

**Cost after the fix round** (`cost.json`):

| View | Colour draws | Colour triangles | Shadow casters within 150 m (triangles) |
|---|---|---|---|
| `cam_bv_long_gate` | 227 | 249k | 18 (102k) |
| `cam_bv_bx_gate_west` | 222 | 167k | 10 (5k) |
| `cam_bv_long_far` | 198 | 289k | 41 (136k) |
| `cam_bv_relay_scrapyard` | 51 | 83k | 41 (99k) |

The draw count rose with the extra talus and the two-part outcrops. Merging the cluster prefabs into zone chunks is the
next lever if the A/B asks for it.

**Not seen.** None of this has been seen yet: there are no graphics captures under the current rule. The orchestrator
will rebuild and re-shoot the 14 cameras.

**Known risks.**
- The UV seam on each outcrop: one column where u wraps.
- The rock-to-cap seam at the chamfer top, where two materials meet.
- Cliff Side is saturated orange, tinted to 0.92 / 0.86 / 0.80; check it against the boulders.

## Fix round 2 (20 Nov 2026, 23:00, outcrops only, from build `batch-p2-b2`)

The orchestrator's verdict on b2: the ground is good, so the ripples and masks were left as they were. Three changes, all
to the outcrops and the cameras:

1. **Rock colour.** `recolour_rock.py` rewrites `Rock/BV_CliffSide_BaseMap.jpg` (same GUID):
   - In linear light every pixel keeps its luminance relative to the scan's mean (the bedding, with contrast ×1.15).
   - It takes the mean colour of the basin's own `Art/Terrain/SandstoneAlbedo.png`, keeping 20 % of the scan's chroma.
   - Mean colour went from 0.49 / 0.32 / 0.19 to 0.62 / 0.51 / 0.41; the basin's mean is 0.62 / 0.53 / 0.44.
   - The material base colour is now white.
   - In-frame, the b2 rock read 0.30 / 0.19 / 0.13 on its lit face, against 0.65 / 0.59 / 0.51 for the basin wall in
     `cam_bv_southridge_scrapyard`.
2. **Sand cap and apron.**
   - The rock part now has its own domed **rock top**, with planar UVs and noise.
   - The sand cap follows that rock top plus a noisy offset (two octaves, 1.6 m and 0.6 m) that sinks below the rock
     toward the rim. Sand therefore shows only in irregular patches and hollows: thin, with ragged intersecting
     edges. The hard-edged slab is gone.
   - The apron's height and reach get two noise octaves (2.5 m and 0.9 m along the wall) plus a 0.8 m height noise, so
     its line against the wall is irregular.
   - Outcrop triangles: 84k at LOD0, 21k at LOD1.
3. **Review cameras.**
   - `cameras.py` now refuses a camera spot with an outcrop (outline plus a 5 m apron) or a kit piece near the lens or
     in the first 14 m of the view. When that happens it searches nearby spots that still look from the same site
     toward the other.
   - Moved: `cam_bv_caravan_derrick` (t 0.47, 11 m to the side), `cam_bv_southridge_scrapyard` (t 0.17, 6 m side) and
     `cam_bv_scrapyard_pylon` (t 0.26, 6 m side; also blocked by new talus).
   - `layout.py` drops kit pieces on a camera's lens or in its first 10 m of view. Two wash-scrub pieces on
     `cam_bv_bx_scrapyard` were dropped; that camera keeps the old `cam_bx` pose.
   - `features.json` is unchanged, and all 14 cameras are clear by that rule.
