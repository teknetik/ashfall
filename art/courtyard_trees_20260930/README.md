# Courtyard tree beds — 30 September 2026

Carl (30 Sep 2026): "i think the other two trees in the courtyard should have similar enclosures to the large tree. move
the trees if need be". Not yet accepted by Carl. Evidence: `unity/evidence/courtyard-trees/20260930` (install, verify,
native captures at 13:00 and 21:00 from `cam_tree_bed_*`).

The two courtyard birches (scene roots `birch 3` by Salvage, `birch 4b` by Air + Water) now stand in stone beds built
like the hero tree's ring (`art/hill_20260930/author_ward_hill.py`, whose helpers `author_tree_beds.py` imports — their
`main()` calls are now guarded so the hill scripts can be imported): one dressed course on the shared masonry kit
(Athen Hill/Masonry Lit), curved coping stones with a seat 0.49 m above the paving, leaf-litter soil, slim surface
roots, an irrigation riser with a drip line round the bed, a ring of curved apron flags on the street paving, sheltered
sand at the wall foot, two bronze uplights per bed (lens and lights on the Ward lighting clock, practical + night-only; 70 / 14 m / 66°, as strong as the hero ring's),
light old damage. Birch 4b's roots have lifted and cracked one coping stone (four iron dog cramps); Birch 3 has one paler
replacement stone. Planting: the hill's CC0 Poly Haven weeds, celandine, ice plant, grass tufts, bark and twigs.

| Tree | Moved | Bed (outer / inner face) | LOD0 / LOD1 tris (bed + planting) |
| --- | --- | --- | --- |
| birch 3 | (−19.75, 24.39) → (−19.60, 25.55): 2.1 m of walkway to the Salvage porch, crown further off its north wall | r 1.62 / 1.22 m | 21.4k + 22.9k / 5.7k + 6.6k |
| birch 4b | (−16.34, −3.64) → (−16.34, −1.85): 1.4 m to the Air + Water porch, the cross street stays 5 m wide | r 1.80 / 1.38 m | 24.4k + 34.6k / 6.6k + 10.8k |

The trees keep their prefab links, LODGroups and trunk capsules; each bed adds an annulus mesh collider (wall and
coping) and a convex soil disc, so the coping can be stepped onto.

## Run order

```sh
env -i HOME=$HOME PATH=/usr/bin:/bin blender -b --factory-startup --python-exit-code 1 -P author_tree_beds.py [-- Birch3 Birch4b]
env -i HOME=$HOME PATH=/usr/bin:/bin blender -b --factory-startup -P review_tree_beds.py -- Birch4b [overview eye seat heave inside top]
```

Unity (`Editor/CourtyardTreesPass.cs`): **Athen Hill → Courtyard trees → Build assets**, **Install tree beds (one
time)** (moves the two trees, instances `Prefabs/CourtyardTrees/TreeBed_<Key>.prefab` under **Courtyard tree beds**,
binds the uplights to the light clock, adds `cam_tree_bed_*`), **Verify saved scene**. Batch:
`-executeMethod AthenHill.Editor.CourtyardTreesPass.RunBatch --steps build,install,verify`. Materials are shared, not
copied (hall stone and fittings, hill litter/root bark/plants). Heavy media stays local per `.gitignore`.
