# Reference street metal and lettering source — 9 September 2026

These scripts are candidates for the new user-supplied Field Supply/Finery
reference. They retain previous facade source and Unity assets. They do not
install anything in Unity or establish visual acceptance.

## Current source revision: V3

The first native candidate in
`unity/evidence/reference-street/20260909/after-native` is rejected as the final
metal treatment: `cam_reference_street.png` and
`cam_audit_field_supply_door.png` show coating that reads too clean and grey,
with insufficient connected paint loss at player distance. The thin lettering
also reads more like a marker than the supplied reference's brushwork. Those
captures, V2 maps, V1 brush source and previous Unity assets remain available.

`author_metal_v3.py` creates a separate source scene and copies the retained V2
photographic material graph, adding darker charcoal coating, clustered nominal
2–10 cm coating losses, irregular margins, local horizontal scuffs and broken
3–23 mm shutter-lip oxidation. The macro field controls weather exposure; the
smaller loss field controls the actual oxide patches. The photographic colour
and normal inputs remain connected, and paint, oxide and abrasion have distinct
roughness. Physical scale and the existing Unity UV contracts are unchanged.

V2's final saved studio had only its last actively used `AgedSteel` graph as a
saved material user; the unreferenced `ShutterSteel` graph was not retained in
that blend. The original authoring script and all V2 bakes survive. V3 loads the
common graph from `AgedSteel` and explicitly recreates the registered shutter
lip field. Both new graphs set `use_fake_user = True`, so
`metal-studio-v3.blend` retains both families across saves regardless of the
currently selected bake material. V2 is untouched.

Both V3 families were authored and baked successfully through live Blender MCP.
`textures-v3/ShutterSteel` and `textures-v3/AgedSteel` each contain 4096²
`BaseColor.png`, `Normal.png`, `Roughness.png` and `Metallic.png`, plus diagnostic
`WearMask.png` and `bake.json`. Their manifests record timings, output hashes,
GPU use and verified unchanged original input hashes. There was one completion
per channel and no circular dependency warning. `metal-v3-manifest.json` records
the source blend hash and changes. Wear-mask coverage above 0.5 is 22.66% for
the shutter, including its lip corrosion, and 4.71% for general coated steel;
these are source-mask measurements, not runtime appearance scores.

`author_brush_v3.py` regenerates the same original glyph paths and placements
with stroke radii multiplied by 1.7 around their unchanged centerlines. It
preserves the phrase, per-letter lean, slat clipping and world-space plane.
`brush-graffiti-v3.blend`, `brush-graffiti-meshes-v3.json` and
`brush-graffiti-manifest-v3.json` are the retained outputs. The export has 4,554
triangles in two parts; every triangle faces −X and none is degenerate. The
exported names and exact replacement paths are:

- `Reference street thresholds and detail/Factory brush upper`
- `Reference street thresholds and detail/Factory brush lower`

Replace only the mesh at each existing path; use the same matte `BrushPaint`
contract below. Do not transform the world-space vertices a second time.
`ReferenceStreetPass.ApplyMetalV3` imports this focused revision into its
separate `RevisionV3` asset folder, retaining prior maps, materials and meshes.
The source review is a candidate handoff; final native lighting, close-up and
moving review must judge the combined revision.

## Original authoring and bake correction

Execute `author_metal_materials.py` with `ACTION = 'AUTHOR'` through the live
Blender MCP. It creates a separate scene and saves `metal-studio-v1.blend` and
`metal-import-contract.json`. Then execute the same script with `ACTION = 'BAKE'`
and `BAKE_FAMILY = 'ShutterSteel'`. The four 4096² PNG bakes are written beneath
`textures/ShutterSteel`, with hashes and timings in `bake.json`. An optional
`BAKE_FAMILY = 'AgedSteel'` bake excludes the shutter-specific lip rust for
separately reviewed coated doors, rails and louvres. All bakes refuse to replace
existing PNGs. Recover from an interrupted bake by preserving its directory and
working in a new recorded revision, rather than silently overwriting it.

The initial metal bake is rejected: the bake plane retained an unused second
material slot with an active photographic texture, producing circular-target
warnings and two completions for each channel. `prepare_metal_rebake.py` preserves
that output under `rejected-metal-bake-v1`, checks original disk hashes against
the pre-bake contract, reloads the authoritative source pixels and leaves exactly
one active material slot. The corrected bake also enforces one slot and rechecks
the originals. It records bake revision 2 and saves `metal-studio-v2.blend`,
retaining the initial studio. All four original photographic disk hashes were
verified unchanged before the correction was dispatched.

The material nodes combine a fine charcoal coating, low-amplitude paint fading,
sparse tiny paint loss, short horizontal abrasion, restrained photographic oxide
colour and normal relief. Rust on the shutter follows its actual horizontal
slat lips, interrupted by local variation; broad floating orange islands are
absent. Colour and scalar maps are emission bakes, and the normal is a tangent
bake with OpenGL +Y convention. No directional lighting is baked into colour.

The photographic input is the retained CC0 Poly Haven `rusty_metal_sheet` by
Amal Kumar, under `refs/quality_20260909/building-materials/rusty_metal_sheet`.
The script records source hashes and the source page in the generated contract.
Original source resolution and maps remain untouched.

## Unity material contract

The generated contract names the exact twenty Field Supply slat source paths.
Assign `ShutterSteel` only to those renderers, keeping the current four-metre
world UV0 from `FacadeMaterialPass`: the visible −X-facing surface has
`U = world Z / 4`, `V = world Y / 4`. Use material scale `(1,1)`, offset `(0,0)`.
Rust is registered to lower lip heights `0.506 + i × 0.14` metres and upper
heights `0.634 + i × 0.14`, for `i = 0…19`. This deliberately registered material
is not a generic V-periodic tile. Its horizontal noise is periodic across the
negative-world-Z UV seam. Do not assign it to Finery louvres or arbitrarily
rescale its UVs.

Create a new URP Lit material, tint white; base colour is sRGB, normal and packed
data linear. Pack metallic into red and `1 − roughness` into alpha. Set normal,
metallic and smoothness multipliers to one and the appropriate URP texture
keywords. Retain full 4096 import size, mips, streaming, 8× anisotropy and high
quality BC7 compression. Do not flip the green normal channel. The optional
`AgedSteel` material also expects a four-metre tile and has no registered stripes.

## Brush lettering

Execute `author_brush_graffiti.py` through the live Blender MCP. It creates a
separate source scene, `brush-graffiti-v1.blend`, two exported meshes and a
manifest. The phrase stays exactly `THE FACTORIES` / `NEVER SLEEP.`. The glyphs
are original hand-drawn stroke paths with uneven paint loading, tapered tips,
small bristle edges and slight per-letter lean. They use no font or image asset.
Paint stays on the existing `x = 17.936` plane and is explicitly clipped to the
twenty saved slat bounds, including their gaps.

`brush-graffiti-meshes-v1.json` uses Unity world positions in metres, normals,
UV0 and triangle indices. Create the new visual group at identity; do not apply
the historical source transforms again. Both meshes use `BrushPaint`, no
colliders, and do not cast shadows. Create a fresh matte URP Lit paint material:
base colour `(0.73, 0.66, 0.53, 1)`, metallic `0`, smoothness `0.08`, cull `0`,
no base/normal/metallic textures and no emission. The old WardPlaster clone
multiplied a plaster photograph into the lettering and made it too dark.

Disable and retain old `GraffitiSolid` visual objects under `Field Supply and
Finery weathering/field_supply`; leave their source assets and all gameplay
objects intact. Rebuild render chunks after changing the source renderers.
Inspect native sun/shade readability and first-person depth/slat gaps before
acceptance. The scripts have passed Python syntax compilation; execution,
baking and native review are separate steps recorded by the integrating task.
