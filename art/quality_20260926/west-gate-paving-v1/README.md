# West Gate paving technical-map candidate — 26 September 2026

**Staged outside Unity Assets. Not imported, installed or visually accepted.**
The first complete bake is in `refined-joints/`. The enclosed-hole cleanup is in
`clean-joints/`. The first edge-smoothed bake is retained in `periodic-candidate/`,
but exceeded the intended physical height range and is not an import candidate.
The bounded successor in `periodic-v2/` is baked, saved and numerically checked.
It is the current candidate for reversible native audition. Final independent
map review permits that audition with a small edge-artifact caveat; native
appearance/import acceptance remains pending. Work was paused at the user's request.
The original maps and current shared material remain unchanged.

See `unity/evidence/quality/20260926/HANDOFF.md` at repository root for resumption.
The staged `normal-only-install-request.json` has not been executed and has a
known CS0122 error: `Texture.activeTextureColorSpace` is inaccessible in the
installed Unity API. Fix its reporting field and revalidate before use.

## Source diagnosis

The saved `Paving Local wear` material uses a 1254×1254 albedo and a byte-identical
`Paving_NormalSource.png` (SHA-256
`9d8a4d78479096af5c1e33f98ccffbb5be8336cf232646a2cac25b022d22bc0c`).
The importer converts that color image to normals with height scale 0.12; the
material then uses normal strength 0.72. Mineral color variation therefore becomes
surface relief. No roughness map is assigned: initial smoothness is 0.17, followed
by the WeatheredLit shader's broad world-space wear modulation. That wear changes
albedo and smoothness together but does not distinguish worn tops from joints.

The editable cube spans 120×90m, with 20×15 material repeats: each texture repeat
covers 6×6m. Source density is 209 texels/m before mip selection and compression.
The candidate does not upscale the albedo or claim new color detail. The older
image-generator provenance is retained in `refs/materials/textures-provenance.json`;
the current color-graded runtime texture is preserved exactly. The exact historical
grading recipe has not been located, so it is not reconstructed or invented here.

## Authored technical maps

`author_maps.py` records the first export, including its failed partial-library
source-save operation. Those exported files are retained at this folder's root.
`author_maps_v2.py` adds a missing short lower-edge joint and produces
`refined-joints/` through the live Blender MCP. `bake_normal.py` bakes its actual
tangent normal in Cycles on a separate 6m plane and saves the whole editable file
as a copy. It preserves the recovered default Cube, Camera and Light scene.

- `Albedo-preserved.png`: exact original1254×1254 RGB bytes.
- `Height-metres.exr`: authored floating-point height in metres.
- `Height-normalized.png`: 16-bit height encoding `metres = value*.016-.008`.
- `Joint-classification.png`: material mask constrained to manually traced
  corridors. Dark mineral pixels outside the corridors cannot become holes.
- `Joint-review-overlay.png`: green accepted joints, magenta corridor boundary.
  This is inspection data, not a new base-color texture.
- `Roughness.png`: authored roughness, approximately0.73–0.96; worn stone is
  quieter/smoother, protected joint fill rougher. These are art-direction starting
  values, not a measured scan of a real surface.
- `MetallicSmoothness.png`: linear RGBA, metallic red0 and alpha `1-roughness`.
- `Normal-OpenGL.png`: actual16-bit Cycles tangent-normal bake, positiveY.
- `Paving-authoring.blend`: complete editable source copy with plane, material,
  packed maps and bake target. Both authored and original scenes were read back
  successfully through Blender's library metadata API.

The height recipe uses 6mm recessed joints, 19mm eased edges and independent quiet
top relief (0.116mm RMS, clamped to0.3mm), rather than grayscale albedo as height.
`source-maps.json`, `normal-bake.json` and `normal-physical-validation.json` record
parameters and checks. The first bake used CPU,4threads,1sample,1254×1254 pixels,
zero margin, tangent space and positiveX/Y/Z channels. It took1.34seconds.

The saved normal agrees in orientation with metre-derived height gradients, but
the discrete central-difference comparison is imperfect near steep joints.
Opposing-edge normal differences reach about9.7degrees at the95th percentile on
one axis, and first/last height samples differ by up to1.96mm. These need explicit
periodic boundary review; the candidate is not yet called seamless. Adjacent
edge pixels have finite physical spacing, so their inequality alone does not prove
a discontinuity. A repeat preview and derivative continuity checks are required.

## Current bounded candidate

`author_maps_v3.py` fills553 enclosed pixels only in the critic's three marked
joint-bed regions; boundary-connected chips remain intact. `refine_periodic_v2.py`
adjusts only12-pixel(57.4mm) edge bands using monotone cubic transitions, matching
shared boundary values and zero boundary slope without exceeding the predecessor's
height range. The earlier unbounded attempt is preserved in `periodic-candidate/`
and rejected for import. All slab-interior technical samples outside these bands
remain unchanged from the cleaned source, and the albedo bytes remain exact.

The current bake takes1.33seconds on four CPU threads. The62.55MB whole-file copy
retains the original Scene plus prior authored versions and the named `Ward Paving
V2 physical-height source` scene with packed material maps. Readback confirms all
scenes and materials. The PNG normal, roughness and packed maps are16-bit/channel;
the height EXR contains uncompressed FLOAT32 RGB channels. Runtime normal/block
compression may reduce this precision and must be inspected separately.

`periodic-v2/normal-physical-validation.json` records normal unit length
0.999986–1.000049. Median/p95/p99 central-difference error is0.088/3.175/6.613degrees;
the maximum24.1degree error remains localized near steep joints and is not called
an exact analytic bake. Opposing columns now differ by2.234degrees at p95, rows by
0.079degrees. Extrapolated boundary-height mismatch is at most0.0127mm. These are
sampled diagnostics, not proof that final native tiling is invisible. The exact
2×2 normal repeat preview shows no broad invented ridge through a slab interior;
small edge-band responses and original albedo repetition require native closeups.

The current `manifest.json` contains file hashes, dimensions, source recipes,
channel meanings, import settings and limitations. Keep all earlier attempts.

## Intended native material audition

The agreed first comparison now uses the existing `Paving Local wear` material,
with reversible authored material edits and separate native builds. It avoids
new geometry and boundary shaders while isolating the verified material defect:

1. Preserve a native baseline with the current material.
2. Replace only the normal map, using the authored strength1 response; preserve
   original albedo, UVs, smoothness, wear controls, all geometry and colliders.
3. Compare a second variant adding the authored metallic/smoothness map with
   smoothness multiplier1, retaining all other settings.

Use matched gate sun/shade close-ups and a wider avenue view. Back up the original
material and record all field/keyword changes. These are planned comparisons,
not implemented by the map-authoring scripts; no candidate has been accepted.
The source-level defect is shared by this single material family, so if the
repair consistently improves it, a material-only save is simpler than a split.

The earlier8×12m patch proposal remains available for genuinely localized wear:
x[42,50],z[-6,6],y0, non-overlapping top-only split, original cube side/bottom
faces/UVs and collider unchanged, with boundary response blending. It is deferred;
no split geometry, raised overlay, shader or chunk rebuild has been introduced.

For later import, the normal is already a normal map: **disable grayscale-to-normal
conversion**, use NormalMap type/linear data and preserve source dimensions.
Use candidate normal strength1 for the authored metre-scale response. Import the
packed map as linear default texture; metallic workflow samples red0 and alpha
smoothness, with `_Smoothness=1` and `_METALLICSPECGLOSSMAP` enabled. Preserve the
existing albedo, tile scale, nonmetallic response and unrelated scene settings.
Retain repeat wrapping, mipmaps, streaming and anisotropic filtering; actual
runtime format/mip residency remain Unity/native checks.

## Recovery record

The first data-only Blender authoring call exported its maps, then Blender5.2.1
crashed with SIGSEGV at13:43:38BST. `bpy.data.libraries.write` was the next
uncompleted operation. Native frames were stripped, so the exact failing C++
function is unproven. Available memory was9.9GiB and no matching kernel OOM entry
was found. The crash was diagnosed using the
[diagnose-crash skill](/home/teknetik/.codex/skills/diagnose-crash/SKILL.md).
Evidence is under `unity/evidence/quality/20260926/ground-audit/blender-crash/`.
The temporary extracted core was removed after analysis; no crash report was sent.

The authoring session was recovered on the existing private Xvfb display, retaining
the ordinary default scene. Whole-file `wm.save_as_mainfile(copy=True)` succeeded;
the failed partial-library save was not repeated. All original source textures,
Unity content and existing saved Blender files remained untouched.
