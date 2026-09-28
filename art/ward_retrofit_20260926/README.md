# Ward district retrofit v1 — 26 September 2026

User request: the shop buildings all look alike and read as plain geometric boxes on a
barren plaza. Make them feel modern/sci-fi yet worn from years of war and neglect, and
make the small level feel full. Inspiration: the Tir/Ward lore (company world, the Fall,
hydroponics, one working nanofab, repurposed mining droids, Quantum Tube goods network,
Wardens, Outer Berms).

Approach: keep every existing shell, porch, collider, route and gameplay root. Add a
Blender-authored retrofit layer that changes each shop's silhouette and material identity,
and fill the empty quadrants inside the walls with lore-grounded infrastructure.
Installed as one prefab instance (`Ward district retrofit`) by
`AthenHill.Editor.WardRetrofitPass`.

## What was added

| Group | Content |
| --- | --- |
| Shop retrofits (8 shops) | Front: corner armour guards, parapet cyan light strip, cable tray, conduits, camera, **lit projecting blade sign** per shop. Rear: service spine (pipes, conduits, AC units, electrical boxes), bolted patches, scorch/pock/grime decals, wall lamp. Roofs: HVAC units, vent stacks, masts, solar/radiator banks — seated on the surveyed roof decks. Per-shop character: Relay rooftop cabin + mast + teal cladding; Air+Water moisture-condenser tower + bone cladding; Tool Exchange rooftop workshop + hoist jib; Salvage Warden lookout (HESCO, turret, banner) + scaffold; Finery rooftop cabin + bone cladding; Field Supply teal cladding; Repairs container cabin + olive cladding; Thread+Hide upper balcony + olive cladding. Cross-street pipe bridges, alley cable swags, Warden banners. |
| Service lanes | Steel utility poles (transformers, insulators, junction boxes) down both rear lanes, line runs and service drops to the roofs. |
| Processing hall ruin (NE) | Pre-Fall precast frame: broken columns with rebar, surviving trusses and holed corrugated roof, collapsed bay with fallen truss/sheets, rubble, crane rails with stranded bridge, faded company sigil and "PROCESSING 11", rusted conveyor spine toward the east wall. |
| Hydroponics bays (NW) | Two quonset greenhouses (polycarbonate skin, tarp patches, tiered grow racks under LED bars), feed tanks, pump/filter skid, planters. |
| Nanofab workshop (SE) | "NANOFAB 2" chamfered teal composite block, hazard-framed loading door, lit access panel, roof fans, ducting, exhaust stack, process-gas cylinders, scrap lean-to, container stack. |
| Aquifer pump station (SW) | "AQUIFER 3" pump house, three storage tanks with headers, well head with rising main, HESCO guard post and scrap turret. |
| Walking mining droid | Meshy hero asset ([record](../../meshy/mining-droid-20260926/README.md)) rigged in Blender by `rig_droid.py`: rigid skinning (body; swing + foot bone per leg), `walk` diagonal-pair trot (1.2 s, foot lift, body drop keeps stance feet planted, stride ≈1.51 m/s) and `idle`. Unity: `WardMiningDroidPass` — legacy clips, `ActorAnimation` + `AmbientWalker` (same components as the ambient colonists), kinematic box collider, 40 m patrol loop (−46,−28)→(−32,−28)→(−32,−22)→(−46,−22) at 1.1 m/s, checked against the obstacle survey. |
| Watchtowers 1–4 | Wall-corner Warden towers: braced legs, armoured cabin, searchlight, antenna, banner, ladder, HESCO base. |
| Quantum Tube conduit | Ribbed goods conduit on pylons along the north wall, terminating in two node housings either side of the Ring Gate axis ("NODE 07 · GOODS ONLY"). It does not connect to the Ring Gate and implies no passenger transport. |
| Perimeter dwellings | Five container homes (one stacked with stair) with awnings, AC, solar panels, planters. |
| Gate defences / street clusters / hall banners | HESCO lines and turrets flanking (not blocking) the West Gate approach; utility clutter in the cross-streets and lanes; two Warden banners on the Hall. |

Totals (`geometry-report.json`): ~500k source triangles, 88 box colliders, 36 practical
lights (added to the existing `CityLightCircuit`, so they follow day/night and distance
culling). "Detail" meshes (props, bracing, fittings) cull below 3 % screen height; decals
and glow meshes cast no shadows. **No native performance qualification has been run.**

## Rebuild

```sh
python3 download_textures.py && python3 download_polyhaven.py   # CC0 sources (MD5-checked)
./make_textures.sh                                             # tints, stencils, decals, blade signs
blender -b --factory-startup -P build_retrofit.py              # WardRetrofit.glb + ward-retrofit-v1.blend
blender -b --factory-startup -P rig_droid.py                   # MiningDroid.glb (rigged, idle/walk)
blender -b ward-retrofit-v1.blend -P review_retrofit.py -- name:ex,ez,ey,tx,tz,ty   # optional Eevee stills
```
`build_retrofit.py -- "<group substring>"` builds one group into `partial.blend` without exporting.
Then Unity: **Athen Hill → District → Install district retrofit** and **Install walking mining droid** (refuses if installed) or
`AthenHill.Editor.WardRetrofitPass.RunAll` in batch mode (replaces only its own install).

Placement uses `survey/` (heightmap + collider map of the saved scene, see its README):
roof pieces search for flat, unoccupied roof deck; ground pieces are nudged to free ground.
Regenerate the survey (`AthenHill.Editor.DistrictRetrofitSurvey.Heightmap`) after layout changes.

## Sources and licences

- 18 Poly Haven texture sets and 52 Poly Haven models, **CC0** (`sources/texture-manifest.json`,
  `sources/polyhaven-manifest.json`, official API downloads with MD5 checks).
- Market canvas/hessian/linen textures reused from `art/karaveen_market_20260926` (CC0-derived).
- Stencil/sign lettering: Nimbus Sans Narrow Bold (URW base35), rasterised into textures only.
- All structures, the droid, sigil, Warden banner and decals are original to this project.

## Known gaps

- The shells themselves are unchanged: the retrofit layers over them. Facade massing,
  window/door design and the broad central paving still need a dedicated pass.
- The droid's walk is procedural keyframing on a rigid rig: no foot IK, so feet can slide slightly
  at speed changes/turns, and the patrol ignores the player (it collides but doesn't path around them).
- Meshy ignored the requested kneeling pose and drill boom; the model is a standing walker.
- Air+Water's extra roof tank was skipped (its roof already carries tanks).
