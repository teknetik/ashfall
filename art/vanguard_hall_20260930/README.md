# Vanguard Hall rebuild — 30 September 2026

User direction (Carl, 30 Sep 2026): "this building needs a complete rebuild. it looks terrible." The replaced hall was
the 6,856-triangle Meshy 7 salvage model (`meshy/salvage-20260908/hall`) with the district-retrofit banners.
The new target, `concept/vanguard-hall-concept-a.png`, was shown to Carl and accepted ("yes this!"); see
`concept/ACCEPTED.md`. It supersedes the 8 Sep turnaround and the 9 Sep repair brief/revision 02 for the Hall only.
The concept is a target image, not evidence of the game render.

## What was built

An authored civic hall at the same site (front face on the old front edge, world z −26.55, centred on x −10),
now a real building instead of a 4.25 m facade slab: 10 m walls + battered corner piers (11.6 m at the base),
8.5 m deep, parapet 12.85 m, attic 13.65 m, mast to 19.2 m, on a 0.5 m podium that keeps the original top height,
front step footprint and approach.

| Part | Construction |
| --- | --- |
| Masonry | Individually modelled ashlar blocks in course-aligned running bond (0.43–0.48 m courses), bevelled arrises, subtle face tilt, occasional chipped corners; recessed mortar backing; per-block tint and occlusion in vertex colour (Athen Hill/Masonry Lit). Rough sandstone plinth course. |
| Piers | Four battered corner piers (2.1 m → 1.5 m) built as split course rings, flared rough base course, steel corner wraps on three, a strapped repair on the front-west pier. |
| Portal | 2.9 × 3.8 m opening in a stepped jamb surround, flat-arch lintel with key stone, hood moulding; riveted steel double doors with bronze studs, kick plates and pulls, strap hinges, transom grille, threshold plate. |
| Upper storey | Four barred windows between pilasters with capitals, projecting sills, lintels, steel frames; interior-mapped glazing. Central pilaster carries the woven banner on a rod. |
| Entablature | Frieze projecting 0.5 m over the walls (soffit visible), corner capitals, swept cornice with cyma and corona, iron corbels, steel soffit brackets. |
| Roofline | Parapet with coping, raised corner caps, front attic, steel scuppers, west downpipe with swan neck and hopper, roof deck, hatch, vents, cabinet, comms mast with crossbar, whips, dish, guys and a red beacon. |
| Nameplate | Dark bronze plate with brass border/rivets and raised 3D brass lettering "VANGUARD HALL" (Noto Serif Display Bold, OFL). |
| Sides and rear | Side windows and pilasters, conduit and junction box, security light/camera, power box; rear service door with painted steel leaf, canopy and lamp, riveted repair plate over spalled stone, a bricked-up window with rough infill, air conditioner. |
| Podium | Rough sandstone faces, overhanging edge ring, paving slabs, front step (original footprint/height) and a rear service step. Sheltered sand drifts (LOD0). |

## Sources and scripts (run order)

1. `fetch_polyhaven.py` — CC0 Poly Haven textures to `polyhaven/` (`polyhaven/manifest.json` records authors/licence).
2. `prepare_textures.py` — Unity texture sets (graded albedo for the two sandstones, packed masks) and the generated
   woven banner (original twin-stripe mark) → `unity/AthenHill/Assets/AthenHill/Art/VanguardHall/Textures`.
3. `author_vanguard_hall.py` (Blender 5.2, headless) → `Art/VanguardHall/Models/VanguardHall_LOD0.glb`, `LOD1.glb`,
   `vanguard-hall.json` (colliders, fittings, nameplate, scuppers, beacon, triangle counts) and
   `vanguard-hall-source.blend`. Coordinates are Unity metres local to the hall root.
4. `review_vanguard_hall.py` (Blender, EEVEE) — optional source review renders (`review/`).
5. Unity: **Athen Hill → Vanguard Hall → Build assets** (texture import settings, materials, prefab with LODGroup,
   box colliders, fittings, practical lights, weathering decals), **Install rebuilt hall** (once),
   **Add review cameras**, **Verify saved scene** (`Editor/VanguardHallPass.cs`).

Shader: `Art/VanguardHall/Shaders/MasonryLit.shader` is Athen Hill/Weathered Lit plus per-block vertex tint
(`_BlockTint`, RGB, 0.5 = neutral) and per-block occlusion (`_BlockAO`, alpha).

Heavy media (textures, blend files, renders) stays local per `.gitignore`; scripts, JSON and this README are tracked.
Unity-side textures/models are complete for builds.

## Third-party content

Poly Haven (CC0): worn_rock_natural_01, sandstone_cracks, rust_coarse_01, rusty_metal_sheet, painted_metal_shutter,
dense_sand, rough_linen (texture maps). Fittings reuse the West Gate Poly Haven CC0 props (industrial wall lamp,
security light/camera, air conditioner, power box). Font: Noto Serif Display Bold (SIL OFL 1.1, `fonts/`).
Concept: generated with Codex image_gen (ChatGPT plan), prompt `concept/prompt-a.txt`.
