# Relay and Air + Water surface revision — 9 September 2026

This extends the user's accepted surface direction after the Field Supply/Finery
revision: varied plaster, physically scaled fine normal relief, flaking painted
metal and natural local edge losses. It changes the two active authored shops
under `Ward shop architecture`, preserving their envelopes, doors, canopies,
service fittings, lettering, prefab links and all collision proxies.

`unity-source.json` and `unity-placement.json` freeze the actual saved Unity
sources before authoring. The two shops are at unit scale, facing world +X.
`author_surfaces.py` and `finish_surfaces.py` ran through the live Blender MCP
addon in Blender 4.5.13. The final editable source is
`relay-airwater-surfaces-v2.blend`; the earlier source is retained.
`facade-meshes-v2.json` is the final Unity-world-space export. The conversion
`B=(x,-z,y)` preserves orientation; export retains triangle winding. Source
camera lettering appears mirrored under this convention. Lettering is reference
geometry only and is not exported or replaced; native Unity captures confirm
the original readable signs.

## Materials and damage

The three full-resolution 4096×4096 colour, tangent normal, roughness and metallic
bakes from [the first material revision](../facade_materials_20260909/README.md)
are reused at four metres per tile. Their original photographic inputs, CC0
provenance and editable Blender material graphs remain in that source record.
Unity reuses the exact installed URP materials, including BC7 imports, linear
normal/packed maps, sRGB colour, streaming mips and anisotropic filtering.
This extension adds no texture allocations or new external art.

Plaster uses faded limewash, exposed mineral variation, fine hairlines and pores.
Stone retains mineral detail with small worn edges. Painted service hardware,
doors, vents, the roof tanks and filter canisters receive uneven coating loss
and oxide roughness. Brass, gaskets, glass, cloth, lettering and unselected bare
steel retain their original materials. Cylinders have continuous physical-scale
UV wraps and independent offsets to avoid identical wear on all three filters.

Sixteen localized plaster spalls use irregular 128-point outlines, shallow
43 mm recesses and small edge bevels. Eight stone corners have irregular curved
losses. Large planes keep flat normals after Boolean work; original custom
normals remain on unmodified construction and curved parts. Fine surface
failures are texture relief, not thousands of separate polygon flakes.

Fourteen editable projectors reuse the existing runoff/foundation atlas. Relay
wear follows window sills, the utility box and entrance. Air + Water deposits
follow filter drainage, the downfeed and sheltered wall bases. These are visual
storytelling, without new gameplay systems or invented setting history.

## Installation, cost and recovery

`RelayAirWaterSurfacePass.Apply` is a guarded, one-time Editor operation. It
assigns new mesh assets on the 479 existing source objects, adds 16 substrate
meshes and the localized projectors in a saved `SurfaceWear.prefab`, explicitly
rebuilds render chunks and saves the scene. The installer verifies unchanged
gameplay and collision signatures and rejects discarded lightmap UV data.
No affected source mesh had an existing UV1 set.

Revised source meshes total 192,138 triangles versus 93,060 for their original
targets: a net increase of 99,078. These are source counts, not frame submission
counts. Texture use is shared with Field Supply/Finery. Native measurement and
visual results are in [the evidence record](../../unity/evidence/relay-airwater-surfaces/20260909/README.md).

`installation.json` records every prior mesh/material reference. To undo only
this pass, show render sources, restore those references on the recorded objects,
remove this pass's `Relay and Air Water surface wear` root from the chunk source
list, then rebuild chunks and save. Keep original asset GUIDs and unrelated
edits. `before-scene.unity` is a historical recovery comparison, not permission
to overwrite subsequent user work. The original Relay/variant Blender sources,
first material revision, rejected district candidates and prior evidence remain.

This revision supersedes the surface appearance of these two active shops only.
It does not infer user acceptance of the new result or certify whole-game fidelity.
