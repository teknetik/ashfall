# District rebuilding pass · 8 September 2026

Eight Meshy building candidates and one new ambient NPC type were produced for the
native Unity city. **The seven shop replacements were rejected after the user's
close-up review and have been disabled. The previous seven shop instances are
restored in both Linux builds.** The gate and mechanic remain active. The art direction is a settlement rebuilding after civil war:
salvaged metal, chipped stone, mismatched repairs, faded cloth and dusty workshops.

| Source name | Placement / design | Triangles |
| --- | --- | ---: |
| water | Air + Water, rooftop tanks and patched pipes | 3,293 |
| tools | Tool Exchange, sawtooth workshop roof | 3,260 |
| salvage | Salvage, stacked containers and sheet-metal awning | 3,075 |
| finery | Finery, worn art-deco facade | 3,301 |
| field | Field Supply, surplus depot with barrel roof and tower | 3,122 |
| repairs | Repairs, corrugated garage with chimney | 3,222 |
| thread | Thread + Hide, stacked housing and cloth sunshades | 3,153 |
| gate | West Gate arch, two instances at existing openings | 4,530 each |
| mechanic | Adult yard mechanic; separate four-point patrol | 5,587 |

The gate module replaces the old west gate arches. The seven new shop candidates
remain inactive under `District rebuild`; the previous Relay-based shops are
active under `Post-war salvage`. Relay Works itself, the previous civic/salvage props and
clutter, Lattice Jack, the four speaking characters and three traveler routes
are retained. The mechanic adds a fourth ambient walker.

## Production records

Front/side/back concept sheets and extracted input views are in
`../../refs/district_20260908`. Before, after and native screenshots are in
`../../unity/evidence/district/20260908`. `manifest.json` records every task,
original model digest, import bounds, rig checks and credit accounting.

Meshy 7 produced each textured model from three original reference views. All
nine model generations cost 30 credits each. Rigging the mechanic, including
supplied walk/run FBXs, cost 5 credits. **275 credits used; 2,393 remaining** from
the supplied starting balance of 2,668. No additional animation jobs were needed.

The mechanic uses a valid Unity Humanoid Avatar with 24 skin bones, a looping
walk/run Animator controller and one PBR material. Original FBX/GLB files and
2k source texture sets are retained here. Runtime buildings share a padded
6144 × 4096 material atlas with the previous salvage set; every new building
has a 1k tile. The original salvage atlas's pixels are preserved in that atlas.

Editable Unity assets and reimport instructions are documented in
`../../unity/EDITING.md`. Refer to the dated evidence report for final native
verification and known limitations.

## Shop rejection and recovery

The original importer scaled X/Y/Z independently to fill old bounding boxes.
Field Supply's relative height was stretched approximately 2.6 times. Its source
was a wide low depot, not a tower. The 3,500-triangle generation target also lost
roof and facade detail, and 2k textures were reduced to 1k runtime tiles. Distant
screenshots did not adequately validate these candidates at player height.

`DistrictShopRecovery.RestoreAndBuild` restores only the seven previous shop
instances, keeping unrelated scene and HUD edits. The importer now preserves
aspect ratio on future imports. This alone does not repair the rejected source
geometry: those candidates are **not accepted or re-enabled**. They need better
geometry, door-scale checks, full-resolution textures, and close native review
before another installation. No further Meshy credits were spent on recovery.

Recovery evidence: `../../unity/evidence/district/20260908/recovery`. Both Linux
builds succeeded. Five native 1080p views, including Field Supply and Finery at
pedestrian height, rendered without runtime exceptions. Earlier district route
and visual reports describe the rejected shop configuration, not the recovered
shop geometry.
