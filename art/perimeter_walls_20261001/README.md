# Ward perimeter walls (1 October 2026)

Carl (30 Sep 2026): "walls look too clean, maybe some parts of the wall have fallen." The Ward's perimeter walls were
44-triangle boxes with a tiled ashlar texture. This folder builds them as old, battle-scarred, repaired stone defences
on the shared Ward masonry kit (`art/ward_masonry_kit`, the stone of Vanguard Hall, the hall-district and north-avenue
shops, the hill and the tree beds). Unity side: `Assets/AthenHill/Editor/PerimeterWallsPass.cs`. Evidence:
`unity/evidence/perimeter-walls/20261001/`.

## What is built

Three wall kinds (`pw_layout.KINDS`), each a run of modules (local +X along the wall, city face +Z, y 0 = paving):

| Kind | Walls | Section |
| --- | --- | --- |
| NS | north and south curtain walls, x -60..60 at z ±44.5 | 1 m thick; rough footing, dressed courses, drip string course, parapet course, crenel sill, merlons with saddle caps (top 5.53 m, was 5.0 + 0.26 coping), piers every 7 m on both faces with pyramid caps (old pier rhythm kept) |
| EX | the +X rampart either side of the District gate arches, and the slot between the arches | 3 m thick, 7.4 m to the wall walk; stepped buttresses on the city face at the old positions (z = -43.7 + 5k, 22-37; none at 42 where Watchtower 3 stands), shallow outer pilasters, wall walk, plain coped inner parapet, crenellated outer parapet, stone spouts |
| BW | the -X Outer Berms walls either side of the West Gate portal, and the strip wall beyond the rampart (x 59) | 2 m thick, 3 m; saddleback coping, pilasters on both faces every 5 m, foundation courses showing where the Berms ground falls away |

Variants: `intact_a/b/c` (weathered, chipped, runoff, scattered old scarring, one small shell scar on b, pale
replacement stones on c), `repair` (a patch of small pale stones, a crack stitched with steel staples, cast pattress
plates on a tie rod through both faces), `merlons`/`coping` (parapet partly broken: one gone, one sheared, stones at the
foot), `impact` (shell craters: knocked-out face blocks with the rubble core behind, broken rim blocks, soot, scars),
`siege` (the District gate flanks: impact + broken merlons + stitched crack + soot plume), `collapse` (upper wall fallen
in a stepped break, rubble cones both sides, sandbags on the broken top, welded scrap screen behind; `collapse_n` on the
north wall spills mostly outwards because the Quantum Tube pylons stand 1.3 m off the city face), `breach` (the old siege
breach south of the West Gate portal: wall down to the footing, closed with six HESCO baskets two deep, a second tier,
sandbags and a welded sheet screen on posts outside), `fill` (end and corner pieces with quoins), `gate` (the 1.6 m slot
between the two arches).

Every module is built at LOD0 (bevelled, eroded, chipped ashlar, ~30-40k triangles per 5-7 m, weeds), LOD1 (single
bevels, ~3.5-5k), LOD2 (flat blocks, ~0.8-1.8k) and LOD3 (shadow massing, ~100-340 triangles, inset 9 cm behind every
lit face). Masonry carries the kit's vertex tint/sky occlusion, runoff (UV1.x), worn arrises (UV1.y), rust (UV2.x) and
battle damage (UV2.y) for Athen Hill/Masonry Lit.

Story beats: the siege flanks of the District gate (shell craters, soot, a broken merlon, stitched cracks); the south
wall collapse at x 7-14 (seen from the Lattice and the hill); the north wall collapse at x -42..-49 behind the Quantum
Tube; the West Gate portal flank on the Berms wall (shell damage, a collapse, then the HESCO breach).

## Run order

```
python3 pw_layout.py                                  # layout.json (placements, retire list, kept colliders)
$O/blender.sh author_perimeter_walls.py               # all kinds, LOD0-3 -> Art/PerimeterWalls/Models/PW_<kind>_LOD<n>.glb
                                                      #   + perimeter-walls-<kind>.json (triangles, footprints); ~1 min
$O/blender.sh review_walls.py -- NS run --views wide,eye_*   # optional Cycles review renders -> review/<run>/
python3 pw_validate.py <audit.json> [out.json]        # module footprints vs the scene (StreetDressingAudit.DumpBatch)
$O/unity.sh <log> AthenHill.Editor.PerimeterWallsPass.RunBatch --steps build,install,verify,capture --out <dir>
```

`install` is one time (refuses when "Ward perimeter walls" exists; `reinstall` replaces the root during authoring).
`abbuild:on` / `abbuild:off` build the A/B timing players (`Builds/pw-ab-on`, `Builds/pw-ab-off`; the off arm builds a
temporary scene copy, the saved scene is never toggled) and `ab_runs.sh` alternates native profiles between them.
`$O` = `/home/teknetik/.local/state/ward-programme` (the programme wrappers: capped scopes, shared Unity lock).

## Sources and licences

- Geometry: authored procedurally in Blender 5.2 on `art/ward_masonry_kit/ward_masonry.py` (this repository).
- Dry grass and weeds at the wall feet: Poly Haven `grass_medium_01`, `weed_plant_02` (CC0), the hill pass's downloads
  in `art/hill_20260930/polyhaven/models`, decimated per tuft; Unity materials are the hill's (Ward Ground Cover wind).
- Materials reused in Unity: Vanguard Hall masonry and fittings (`Art/VanguardHall/Materials/VH_*`), street-dressing
  sacks and scrap sheet (`SD_Sack`, `SD_ScrapSheet`), the retrofit's HESCO, rusted sheet and worn corrugated iron
  (`WardRetrofit.glb`), and `PW_Rubble` (a warm copy of the retrofit's Poly Haven concrete-debris rubble, CC0).
- No Meshy generation was used for this pass.

Heavy outputs (`*.blend`, `review/`, logs) are git-ignored.
