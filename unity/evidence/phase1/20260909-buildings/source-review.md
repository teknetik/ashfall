# Individual source review — 9 September 2026

These are authored Blender sources, not native-game acceptance. The first six-view
sets under `art/quality_20260909/relay-family/store-variants-01` are retained.
Revision 02 repairs the connections found in that inspection. Each store keeps its
own source scene, mesh export, material regions, collision plan and revision entry.
The source geometry is in metres; whole-building nonuniform fitting is not used.

| Store | Distinct construction | Source findings and revision | Remaining review |
| --- | --- | --- | --- |
| Air + Water | Offset entry, broad upper filter gallery, twin roof vessels, filter bank and green cloth shade | Seat tank saddles; connect vessel cross feed, exterior downfeed and filter inlets; attach lower awning arms and add side/rear base courses | Native pipe contact, shade response, ground transition, parcel and controller clearance |
| Field Supply | Low pitched metal roof, loading shutter, narrow staff entry and supported loading canopy | Preserve roof/gable thickness; add rear canopy attachment plates and collision proxies for both posts; side/rear base courses | Native post clearance, staff-door scale, materials and loading props |
| Repairs | Low workshop bay, side entry, raised louvred roof monitor and exhaust | Attach lower awning arms; complete side/rear base courses | Native workshop frontage, exhaust/roof contact and purposeful repair props |
| Salvage | Taller pitched loft, unequal upper windows, reclaimed lower panels and lifting bracket | Terminate lifting cable in an attached eye; fasten lower canopy arms; base courses | Native loft silhouette, hoist clearance, panel ageing and salvage work area |
| Thread + Hide | Three narrow upper windows, broad plum shade and roof drying frame | Pin folded cloth to the drying rail; fasten lower awning arms; base courses | Native fabric thickness, motion, textile props and ground transition |
| Tool Exchange | Broad shutter, recessed display, clerestory and offset utility monitor | Fasten lower awning arms and finish side/rear base courses | Native display depth/content, shutter fittings, service access and ground transition |

All six retain relatively plain sides/rears and a shared mineral construction
language. Structural variations improve identification; they do not yet establish
sufficient lived-in detail or contemporary close-range material quality. These
sources stay outside the active scene until the representative material/construction
standard is reviewed. The seven rejected `District rebuild` shop candidates remain
inactive; these source revisions never re-enable those meshes.

Relay Works revision 02 has readable separate lettering, a closed double doorway
with actual reveals, upper windows, cloth supports, side/rear services and roof
plant. Its source front/back/door/awning and native front/door/roof/back were
inspected independently. Native shade is substantially darker than the Blender
studio. The rear wall is still plain, and the fixed rear audit camera crops the
footing; a wider supplemental native view is captured in the corrected final set. The native first-person route and
frame-time report belong to the new build, not the source studio renders.

Hall revision 02 clears the nameplate from the cornice and moves the banner away
from its intersecting horizontal wall rib. The emblem is tessellated and conformed
to the banner, with its original two-stripe identity retained. Full-front, doorway,
banner and pedestrian source views verify this revision. The Hall retains its
already-corrected uniform native fit while this new source remains staged. Further
native integration, foundation/collision matching and material review remain open.

The corrected sources have all six angles each, 36 images in total. The labeled
[front](store-sources-front.jpg), [door](store-sources-door.jpg),
[left](store-sources-left.jpg), [right](store-sources-right.jpg),
[rear](store-sources-rear.jpg) and [roof](store-sources-roof.jpg) contact sheets
provide a quick cross-store comparison; original PNGs remain beside each Blender
source. Rear elevations visibly retain repetition and limited storytelling. That
is an open defect, not a reason to mark all buildings accepted.

## Door meeting correction — revision 03

The first-person native view exposed a 45 mm meeting gap between the closed Relay leaves. Revision 03 adds a continuous opaque seal behind the leaves and an overlapping metal meeting strip. The same authored repair is included in the five staged variants with double doors; Tool Exchange has only a shutter and receives no added parts. Earlier images and revision 02 sources remain unchanged. The six contact sheets show revision 02, before these small meeting strips; the exact correction has its own [Blender close-up](../../../../art/quality_20260909/relay-family/revision-03/source-meeting-seal.png) and [part record](../../../../art/quality_20260909/relay-family/door-meeting-revision.json).

Relay gains two source objects / 376 triangles without changing any actor, collider, material or placement. Its prefab GUID and previous meshes are retained. The 135-second traversal in `relay-native` predates these two visual parts and is not relabelled as a measurement of the final correction.


## Export-position correction — revision 04

The final first-person recheck showed that revision 03’s seal was exported near the origin. Its loaded Blender scene had not evaluated world transforms before deriving door bounds. Revision 04 explicitly evaluates the dependency graph, validates doorway bounds and preserves all original vertex positions. The two existing native mesh GUIDs are retained while their vertex positions are corrected. [Buffer comparison](source-export-v4-verification.json) verifies all original parts are unchanged in Relay and the six staged store exports. [Corrected source close-up](../../../../art/quality_20260909/relay-family/revision-04/source-meeting-seal.png) and [revision record](../../../../art/quality_20260909/relay-family/door-meeting-revision-v4.json) identify the current sources. Earlier revision 03 files remain as failed export evidence.
