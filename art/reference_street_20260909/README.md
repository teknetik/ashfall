# Field Supply / Finery reference street · 9 September 2026

Target: the user's supplied `Codex Image Sep 9, 2026, 07_38_57 PM.png`, preserved
unchanged at `refs/reference-street/20260909/user-target.png`. This is the visual
reference for this local street pass. It supplements the accepted district layout;
it does not authorize replacing gameplay, other shops or the entire city.

The immediate native baseline is the saved four-facade revision identified by
`unity/evidence/reference-street/20260909/baseline.json`. Fresh baseline native
captures use the original build, current camera poses, noon profile, 1920×1080,
render scale 1 and nine actors. The previous Unity scene and uncommitted status
are preserved. Existing source files, rejected candidates and asset GUIDs survive.

The installed source revision addresses direct warm facade illumination and cooler
ambient light, connected plaster cracking and mineral variation, dark painted
steel with rust at shutter lips, original brush lettering, and carved porch joints
and chipped edges. Detailed sources remain ordinary Blender scenes and full 4K
image bakes. Unity receives saved mesh/material assets through the scoped
Editor importer `ReferenceStreetPass.cs`. Final native functionality and the
recorded performance profile pass; the supplied reference's visual fidelity is
still unmet. See the [final evidence record](../../unity/evidence/reference-street/20260909/README.md).

- `PLASTER.md`: photographic CC0 inputs, editable nodes, material/film contracts.
- `METAL_AND_LETTERING.md`: verified source maps, worn steel and original brush mesh.
- `author_thresholds.py`: V2 subtractive revision of four current visual meshes.
- `threshold-source.json`: exact current source world buffers before replacement.
- `verify_reference_street.py`: existing native test orchestration and honest
  result collation; it does not assign art scores.

All bakes use live Blender 4.5.13 through its existing MCP addon. The first metal
bake had a circular-target warning from an unused material slot; it is rejected
and archived in `rejected-metal-bake-v1`. Original source-file hashes were checked
and remained intact. Corrected bakes use exactly one material slot and reload
verified original image data. This failure is retained for provenance.

The first combined native candidate, preserved under
`unity/evidence/reference-street/20260909/after-native`, showed metal that was
too clean and grey and lettering that was too thin. Its metal appearance is
rejected as the final treatment. The focused V3 follow-up uses
`author_metal_v3.py`, `metal-studio-v3.blend` and the full 4096² material sets in
`textures-v3/{ShutterSteel,AgedSteel}`. It darkens the coating, increases small
connected paint-loss regions and broken shutter-lip oxidation, and retains the
original photographic detail. Both families baked successfully with unchanged
source-file hashes and no circular-target warnings. `metal-v3-manifest.json`
and each family's `bake.json` retain the source/output hashes and bake results.

V2's studio retained only its last actively used AgedSteel material graph. V3
copies that common photographic graph, reconstructs the registered shutter-lip
field, and explicitly retains both new material graphs with fake users so they
survive future saves. The V2 studio, regeneration script and output maps remain
unchanged. `METAL_AND_LETTERING.md` records this source-retention correction.

`author_brush_v3.py` produces `brush-graffiti-v3.blend` and
`brush-graffiti-meshes-v3.json`: the same phrase and centerlines with brush
radii 1.7 times wider, still clipped to the original shutter slats. Its two
replacement meshes contain 4,554 triangles, all consistently facing the street.
The existing scene paths are preserved. The scoped `ApplyMetalV3` importer uses
a separate `RevisionV3` Unity asset folder so the prior meshes, materials and
maps remain recoverable. This revision still needs its own native audition;
the first candidate's captures cannot qualify V3. Its preflight stopped before
timing began; that attempt remains intact.

## Installed assets and retained sources

The assets live under `Assets/AthenHill/Art/ReferenceStreet/20260909`.
`installation.json` in the evidence directory maps prior mesh/material references
and active states to the installed revision. The importer compares the gameplay
and collision signatures; the exact before/after JSON records are saved alongside
it. These checks apply to installation and do not replace native input tests.

Thirty-five Field Supply/Finery plaster renderers use `ReferencePlaster`. Twenty
Field Supply shutter slats use the dedicated lip-registered `ShutterSteel` map.
The separately verified AgedSteel assignment covers 37 Field Supply coated parts,
50 Finery louvres and four Finery door parts. Its three material variants retain
the UV scale corrections in `aged-steel-assignment-contract.json`; the shutter's
registered rust pattern is confined to the shutter. Base colour and normal source
PNGs remain full resolution; URP's metallic/smoothness pack is a derived import.

Two original brush meshes carry `THE FACTORIES` and `NEVER SLEEP.` across the
actual shutter slats. The 46 superseded `GraffitiSolid` objects are disabled and
retained. Original lettering geometry, source materials and related font notices
remain available; this brush revision introduces no new font dependency.

`reference-thresholds-v2.blend` and the V2 replacement/addition JSON files are the
installed threshold sources. Four existing porch/approach visual meshes retain
their world transforms, outer envelopes and maximum step-top elevations. Joints
divide the visible stone courses; selected joint ends and corners lose irregular
pieces across their top/front edges. The replacement geometry contains 33,179
triangles; 36 small separate grit pieces add 2,880. These are source counts, not
visible scene or submitted render-pass totals. Large construction-face normals
are explicitly locked and audited; the central walking surfaces remain planar.

V1's regularly spaced pits below a clean rim were rejected. Its script is retained
as `author_thresholds-v1.py`, with its Blender source, exports and source-review
image. V2's shadowed and unshadowed Workbench images are source inspection only;
the dark triangles observed in Workbench require native comparison before an
acceptance claim. The original `threshold-source.json` stays unchanged.

The eight optional mineral-runoff films were installed for native audition under
**Reference street mineral runoff**. They use the separate transparent, clamped
RGBA material, with depth writing and shadow casting disabled and no new
colliders. `mineral-runoff-installation.json` records their additions. Their
source films and scalar alpha remain separate so individual placements can be
omitted if native review shows excessive darkening or overlap.

Eight additional joint-growth plants reuse the original courtyard
`Dry_joint_growth_18.asset`. Their retained source mesh, uniform scales and
corner/base placements are recorded in `joint-growth-placements.json` in the
evidence directory. They add localized vegetation near the two facade and porch
ends; the existing courtyard plant sources remain intact.

## Daylight and reflections

The ordinary day/night clock uses a cloned `WardReferenceDaylight.asset` and
`WardReferenceSky.mat`; the previous profile and sky assets remain intact.
The noon profile turns the key light to Euler `(38, 140, 0)`, keeps its intensity
at 1.7, sets fill intensity to 0.27 and exposure to -0.18, and uses cooler sky
ambient with warm ground bounce. Other profile keyframes remain available to the
same clock. The new sky shader controls cloud scale, edge softness and sparse
wisps through editable material properties.

The saved authored terrain-light orientation remains the reference for distant
terrain's baked directional shadow data; the clock suppresses that contribution
when the active sun direction differs. This pass keeps URP and OpenGLCore.

The City sky reflection (128) and Courtyard reflection (256) were rebaked at noon
under the cloned profile after ground detail was installed. Both saved EXR
cubemaps are referenced as Custom probe textures.
`reflection-bakes.json` records the final bake; the earlier
`reflection-bakes-before-ground-detail.json` is preserved. Non-noon appearance
still requires native day/night review.

## Recovery and verification

For a scoped recovery, use `installation.json` to restore affected mesh/material
references and the prior lettering active states. Remove only this pass's added
detail roots and its entries in the render-chunk source-root list; remove optional
runoff and joint-growth instances by their recorded names. Restore the original
profile/sky and reflection references from the earliest corresponding records.
Show source renderers before editing, then rebuild chunks and save. Do not replace
the whole scene with `before-scene.unity` over later work. Keep source files, asset
GUIDs, full bakes and rejected revisions available.

After root launches a fresh development player into a new evidence directory,
run `verify_reference_street.py` with `ATHEN_NATIVE_DIR` set to that directory.
It reads the player's `pid` file and sets `ATHEN_EVIDENCE` itself. It includes the
new `cam_reference_street` alongside the matched baseline cameras, records an
unmeasured route before timing the next traversal, exercises both porches and the
city loop, and captures midnight, 06:30, noon and 17:30 lighting. It refuses to time
with Unity or Blender authoring processes open. Use `--collate-only` to refresh
the report after the separate release smoke check; this mode launches no checks.

The final saved scene and build identity are recorded in
`unity/evidence/reference-street/20260909/qualification.json`. Both Linux builds,
the warmed full route, 29 city-loop checks, corrected first-person approaches and
release smoke passed. The native 1080p uncapped walking sample measured 173.15 FPS
average and 13.44 ms p99 over 134.685 seconds; the separate interaction profile
retains three first-use UI hitches. Full settings, counters, memory observations,
images, video and remaining art gaps are in the evidence record.

The first two dedicated proximity attempts exposed test-waypoint and settling
errors, not changed collision geometry. Their sources and failed evidence remain
preserved. For this inspection, use the corrected standalone
`unity/evidence/reference-street/20260909/check_reference_proximity_v3.py` instead
of the historical first proximity script. It passed both facades, both treads,
porches, localized plants, wheel zoom, mouse look and camera clearance. The initial
wrapper reports intentionally retain their incomplete status; `qualification.json`
indexes the separate successful completion records. Whole-view art scores remain
below the supplied reference target, and no user acceptance or AAA parity is claimed.
