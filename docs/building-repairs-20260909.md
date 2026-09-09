# Phase 1 building repairs — 9 September 2026

This is the current per-building continuation of [the audit](mesh-audit.md).
The saved scene now contains replacements for **all nine store buildings**. The Hall is a separate landmark. Replacement count describes installed geometry; visual acceptance and completion of Phase 1 remain separate checks.

The six-store installation and its own before/after build are recorded in [the rollout evidence](../unity/evidence/phase1/20260909-store-rollout/README.md).
The [current baseline](../unity/evidence/phase1/20260909-buildings/baseline-identity.json)
preserves the starting working tree and saved scene. The initial capture operation
attempted seven overview/landmark views and six views of each of ten buildings;
[per-image validity](../unity/evidence/phase1/20260909-buildings/baseline-native/capture-validity.json)
records frames obscured by focus-pause UI. Those frames do not qualify as clear before views.

| Building | Current work | Remaining gate |
| --- | --- | --- |
| Basic General | Original frontage source v3 installed with separate sign, supported cloth roof, masonry, stock and threshold. Corrected native lettering and all six matched audit views captured, with mesh GUIDs preserved. Real porch approach, atomic trading and corrected-build route checks pass. | Improve plain shaded surfaces/stock detail; each placement still needs final visual review. No final visual acceptance. |
| Relay Works | Editable revision 02 plus the revision 04 door seal installed uniformly at the original parcel. Six native views captured; original porch/steps retained and warped shell collider replaced by nine explicit proxies. The corrected build passes the full route at native 1080p; materials remain unaccepted. | Shaded metal/window readability, plain rear wall; construction/material standard remains unaccepted for district rollout. |
| Air + Water | Original source revision 04: offset entry, broad upper window, connected roof tanks and filter bank, green shade. Installed uniformly at the existing parcel; native front/door/sides/back/roof reviewed, old shell retained inactive and porch/steps preserved. | Filters need convincing mounts, valves and service labels. Dark finishes, blank walls and water-service props remain open. |
| Field Supply | Original source revision 04: low pitched roof, loading shutter, staff entry and supported metal loading canopy. Installed uniformly at the existing parcel; native front/door/sides/back/roof reviewed, old shell retained inactive and porch/steps preserved. | Shaded shutter, sign and staff entry need better material/light separation; storage props and rear-wall detail remain open. |
| Repairs | Original source revision 04: workshop shutter, side entry, raised roof ventilation and exhaust. Installed uniformly at the existing parcel; native front/door/sides/back/roof reviewed, old shell retained inactive and porch/steps preserved. | Dark shutter/ventilation, blank walls and workshop/service props remain open. |
| Salvage | Original source revision 04: pitched loft, unequal windows, reclaimed panels and lifting fittings. Installed uniformly at the existing parcel; native front/door/sides/back/roof reviewed, old shell retained inactive and porch/steps preserved. | Hoist working context, broad panel ageing, blank rear wall and dark windows need further work. |
| Thread + Hide | Original source revision 04: narrow upper windows, plum canopy and folded cloth on a roof drying frame. Installed uniformly at the existing parcel; native front/door/sides/back/roof reviewed, old shell retained inactive and porch/steps preserved. | Roof cloth remains sparse/stiff; textile-work props, plain walls and dark entrance need further work. |
| Tool Exchange | Original source revision 04: broad shutter, recessed display, clerestory and offset roof monitor. Installed uniformly at the existing parcel; native front/door/sides/back/roof reviewed, old shell retained inactive and porch/steps preserved. | Empty/dark display, missing tool-work props and plain wall fields remain open. |
| Vanguard Hall | Existing uniform fit confirmed. Editable source revision 02 clears the nameplate and banner intersections; four corrected source views supplement nine initial views. | Audition the new source in Unity, preserve foundations/collision, check materials, route and individual native views. |
| Finery | Prior frontage/courtyard retained, including later uncommitted surface work. | Inspect current materials, canopy attachments and entrance; repair remaining repeated marks/blank regions and qualify this placement individually. |

The rollout build passes both real-input traversals through all nine store porches and the separate Hall approach. Trading, dialogue, travel and the release smoke checks pass; detailed results and remaining hitches are in the rollout evidence.

All six current replacement sources are installed. Seven old `District rebuild` shop candidates remain inactive. Their source defects
are retained in [the rejection record](../meshy/district-20260908/README.md).
New architectural sources are replacements for those failed construction ideas;
uniform scaling alone is not a reason to enable the rejected meshes. Existing
active gate arches, actor roots/routes, the courtyard, mission terminals and shop
data remain outside the visual replacements.

## Coordinate-conversion finding

The initial Basic General import preserved a proper axis rotation but not the
front-view handedness between Blender and Unity. This mirrored all separate
lettering. A previous symmetric-cube winding check could not detect the error.
The corrected mapping is Blender `(x,y,z)` to Unity `(-x,z,-y)`, with reversed
triangle winding, corresponding transformed normals and recalculated tangents.
Transforms remain uniformly scaled. The first native frame is retained as failed
evidence; it does not accept the frontage.

See the [individual source review](../unity/evidence/phase1/20260909-buildings/source-review.md) and [revised store manifest](../art/quality_20260909/relay-family/store-variants-04/manifest.json). New source renders are not native evidence.


The earlier [Basic General and Relay native evidence](../unity/evidence/phase1/20260909-buildings/README.md) preserves their build checks and the six stores' preparation history. Its gallery is Blender source evidence. The subsequent [six-store native rollout](../unity/evidence/phase1/20260909-store-rollout/README.md) contains the installed revision 04 buildings, matched native captures and a separate tested build identity.
