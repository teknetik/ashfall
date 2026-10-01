# Courtyard tree beds — evidence, 30 September 2026

Source: [art/courtyard_trees_20260930](../../../../art/courtyard_trees_20260930/README.md). Not yet accepted by Carl.

| Path | What |
| --- | --- |
| `install.json` | Trees moved: birch 3 (−19.75, 24.39) → (−19.60, 25.55); birch 4b (−16.34, −3.64) → (−16.34, −1.85). Four uplights bound to the Ward lighting clock. |
| `verify-saved-scene.json` | Both beds prefab-linked and centred on their trees, 0 missing materials, ring + soil colliders, trunk capsules moved with the trees, 5 review cameras. |
| `native-1/` | Native lookbook at 13:00 and 21:00 (`cam_tree_bed_*`, `cam_district_water`, `cam_district_salvage`, `cam_hill`). |
| `rollback/before-tree-beds.unity` | Scene before the install. |

Night: the first install's uplights (30 intensity, 12 m, 50°, aimed at the crown) left the trunks dark at 20:30 — the
light clock was not culling them (full strength to 90 m). Retuned in place to the hero ring's strength (70, 14 m, 66°,
grazing the trunk into the lower crown) with **Athen Hill → Courtyard trees → Retune uplights** (keeps the clock
bindings); after: `../../street-dressing/20260930/native-fix/cam_tree_bed_birch*-h20.50.png` (trunks and lower crowns lit).
The lens discs share the hero ring's VH_LampLens and clip to white like it (a facade/lamp tune item, not changed here).

Street-dressing litter, grime decals and the city-loop regression run on the combined build are in
`../../street-dressing/20260930`.
