# Factory brush pigment candidate — 10 September 2026

Staged source preview and material-only Unity installer. No Blender/Unity calls or
Assets edits were made in preparing this candidate. Native acceptance is pending.

The supplied street reference uses faded, irregular bone-coloured brush paint on
the Field Supply shutter. The retained two meshes already encode the exact phrase,
stroke outline and slat gaps: **THE FACTORIES / NEVER SLEEP.** Their 4,554 triangles
have zero thickness. UV0 is `(world Z, world Y) / 4`; BaseMap scale `(2,2)` therefore
gives the authored **2 m** tile without changing UVs or placement.

The supplied BaseColor/Opacity/Roughness maps were viewed before choosing a cutoff.
The candidate keeps the source contract's **0.45** cutoff after 1,024,650
area-weighted samples on the actual letters: retained paint is 99.632% on the upper
line and 99.637% on the lower. The opacity map adds sparse fine losses; it cannot
produce heavy fade by itself. The original stroke edges remain the main brush
character. Source roughness R spans 229–245/255; metallic is zero. No bump,
displacement, parallax or fabricated raised paint edge is introduced.

`BaseRGBA.png` copies encoded source sRGB BaseColor RGB and raw Opacity R to A.
`MetalSmooth.png` has zero RGB and `A = 255 - raw Roughness R`. Both are new 4K
RGBA files. All channel bytes were checked after PNG decoding; scalar channels are
not colour-managed or averaged. The original maps and their authoring source stay
unchanged. The scalar source RGB channels can differ by one encoded code from bake
dithering; R is the explicit scalar authority.

## Source audition

The exclusive live Blender operator executes
`art/reference_street_20260910/preview_brush_pigment_lit_v1.py` with `ACTION='AUTHOR'`.
It creates the isolated scene **Factory brush pigment Lit v1 source audition** and
`preview-source.blend`, restoring the previously active scene afterward. It copies
the exact two brush meshes and 20 retained shutter slats, preserving positions,
indices, normals and UVs; the slats use the new `metal-v4/candidate-v1/ShutterSteel`
maps at their retained scale 1. The baseline brush is the current plain paint
material's recorded colour/roughness. Every new image datablock is private.

Then execute once per combination with `ACTION='RENDER'`, `VIEW='phrase'`, `'close'`
or `'grazing'`, and `MODE='before'` or `'after'`. `MODE='albedo'` is an optional
diagnostic. Each call renders only one image, at 1920×1080, Cycles 48 samples,
Standard/None colour transform and a matched neutral world/soft light. Existing
view files are never overwritten. These are source comparisons, not native proof.

The current letter plane is **8.999 mm ahead of the shutter's frontmost plane**.
That placement is explicitly preserved. Inspect the grazing view for floating
paint or an extruded appearance; this material pass does not establish that the
retained offset is visually acceptable. Reject or request a separately scoped
surface-conforming change if the view still fails. Also check chip visibility,
readability and the new paint/shutter response before native installation.

## Native audition installer

After source review, the root operator may stage `BrushPigmentLitPass.cs` in Editor
and invoke `AthenHill.Editor.BrushPigmentLitPass.Apply()` through the working Unity
MCP. It requires the clean saved scene and fresh render chunks. It guards the two
current v3 mesh assets/meta GUIDs and hashes, original material asset/meta, world
positions/normals/UV0, exact triangle indices, phrase source, visibility and shadow
casting. It assigns one new **ordinary Universal Render Pipeline/Lit** material.

The new material uses opaque alpha clipping, double-sided rendering, packed alpha
smoothness and no normal map. Standard URP validation sets the alpha-test queue and
alpha-to-coverage state; the resulting state is recorded. New textures keep full
4K source, trilinear mips, streaming, anisotropy 8 and high-quality compression.
Only the colour/opacity texture uses sRGB and mip alpha-coverage preservation at
0.45; the packed scalar texture is linear. The final imported format is recorded
for native assessment rather than assumed lossless.

The installer records a before-scene copy/evidence, runs ShowSources, replaces only
the two material bindings, rebuilds chunks and compares all untouched components
(including the complete MeshFilters and renderer state except materials), roots,
colliders/routes and gameplay. It saves only after preservation checks pass. The
original mesh/material assets and metas are hash-checked again. Outputs are new
`Assets/AthenHill/Art/ReferenceStreet/20260910/BrushPigmentLitV1` assets and dated
`unity/evidence/reference-street/20260910/brush-pigment-lit-v1` evidence.

Inspect the saved/reopened native shutter at noon and in shade, front and grazing,
then in a moving player-height view. Check mip coverage, flicker, aliasing, apparent
depth and readable wording. Source compilation/channel checks do not accept those
visuals. A failure retains evidence and the recoverable before-scene copy.

`staging-check.json` records the clean offline compiler result and script hashes;
`channel-geometry-check.json` records numeric packing, UV/plane and coverage proof.
