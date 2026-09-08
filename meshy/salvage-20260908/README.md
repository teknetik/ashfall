# Post-war city asset pass — 8 September 2026

Eight original static assets were generated with Meshy 7 multi-image-to-3D from
front, side and back reference panels. The reference sheets, source prompts and
panels are retained in [refs/salvage_20260908](../../refs/salvage_20260908/).
The Relay Works sheet reuses the project's accepted original reference; the other
seven sheets were made with built-in ImageGen for this pass.

| Asset | Triangles | Use in the saved Unity scene |
|---|---:|---|
| Relay Works shop module | 6,208 | Eight repaired shop facades, retaining individual shop names |
| Basic General | 4,277 | Patched cloth awning, reclaimed counter and stocked porch |
| Vanguard Hall | 6,856 | Scarred stone base, bolted repairs, antenna and faded banner |
| Community billboard | 1,368 | Repaired frame, old notices and utility boxes |
| Salvage crate | 679 | Five replaced crates plus sixteen extra yard crates |
| Field generator | 1,619 | Six power units around working yards |
| Trash cluster | 432 | Fifty small deposits around edges and yards |
| Industrial scrap | 896 | Ten stacks of damaged sheet metal and pipe |

There are 16 replaced scene instances and 82 additional props. Lattice Jack was
excluded. The tree, west gate and damaged east wall were retained as landmarks;
the new salvage supports them. The separate Ring Gate replacement is preserved.

[manifest.json](manifest.json) records Meshy task IDs, reference panels, triangle
counts, GLB/FBX hashes and the **240 credits** spent on these eight jobs. Each asset
folder retains the downloaded FBX, GLB and PBR maps. These are generated original
assets; no extracted game content or marketplace mesh was used.

The editable Unity prefabs are under
`unity/AthenHill/Assets/AthenHill/Prefabs/Salvage`. Runtime materials share a 4096²
PBR atlas; original textures remain beside the imported models. Asset scales and
bottom-centred pivots were fitted to the existing city. Basic General uses the
authored doorway/porch collision after a native walking test exposed a false
obstruction in its generated collision mesh. NPC roots and routes are unchanged.

See [native screenshots and verification](../../unity/evidence/salvage/20260908/acceptance.md)
and [Unity editing instructions](../../unity/EDITING.md#post-war-salvage).
