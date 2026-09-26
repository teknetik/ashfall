# Reference street pause — 10 September 2026

The user requested a safe stop and a rebuilt Linux player because of usage limits. This overrides the earlier request to keep iterating. **Do not resume art production until the user asks.** The critic's current verdict is **REVISE**, not AAA acceptance.

## Playable checkpoint

- Scene: `AthenHill/Assets/AthenHill/Scenes/AthenHill.unity`.
- Release executable: `AthenHill/Builds/Linux/AthenHill.x86_64`.
- Build, launch and source records: [pause-checkpoint](evidence/reference-street/20260910/pause-checkpoint).
- Release rebuild succeeded with zero errors and one existing warning about pre-baked collision import settings on 19 meshes. The native release smoke passed: rendered startup and pause screens, real keyboard input, no matching runtime errors, and no development QA listener. The player and authoring apps were closed after verification.
- The checkpoint keeps the installed native04 visuals: masonry V3, threshold V2, canopy geometry V3 with Surface V2, afternoon ShadeBalance V1, and the single crate/trash/scrap auditions. It does not install the unfinished metal, generator, brush or sack candidates.
- Scene reopening verified nine actors, four walkers and fresh render chunks. Recorded scene/runtime/settings sources match native04 byte-for-byte. The development build from native04 is also retained.

## Evidence and remaining quality gap

[Native04 evidence](evidence/reference-street/20260910/iteration-04-native) contains 17 fixed views, four first-person views, 16 successful local threshold checkpoints, 12 short asset movies, and 35 matched stills across noon, afternoon, dusk and night. No command errors or matching runtime error lines were found; capture-time build/source identities stayed unchanged. Both reflection probes completed the diagnostic time changes.

[Independent critique](evidence/reference-street/20260910/critic-iteration-04.json): street shade readability and canopy construction score 4; cloth material, local lighting and aging remain 3. The critic reviewed the stills and short successive-frame samples. Full continuous-motion and performance qualification remain open. Do not present these checks as whole-game AAA acceptance or a new full 60 FPS qualification.

The next canopy step is to isolate the stable angular bands caused by the Finery lamp, its shadows, canvas shadows and normal maps. Keep the physically scaled weave; do not enlarge yarn or add global fill merely to make grain visible. Metal still has repeated wear, the sacks read too smooth, and the generator source needs its guard repaired.

The original Meshy ground source counts were indeed very small: trash 432 triangles, crate 679, scrap 896 and generator 1,619. The installed single auditions retain 180,000, 100,000 and 100,592 triangles respectively for trash/crate/scrap. The generator remains unchanged in the game. Paving is already about 945,000 triangles and is not a low-poly Meshy asset. Geometry and material failures need separate treatment.

## Saved work for resumption

- **Metal V4 candidate V2:** all six full-resolution map families completed; hashes verified. Source scene is `../art/reference_street_20260910/metal-v4/candidate-v2/metal-v4-source.blend`. The full live session is saved as `../art/reference_street_20260910/blender-session7/pause-checkpoint.blend`. Source previews and independent acceptance are pending. The 300-second client timed out while Blender continued; do not rerun AUTHOR into the existing folder. Door-front compositor, standard Lit receiver installer, coating packager and coating installer are staged under `../art/reference_street_20260910/metal-v4/` and its parent; read `coating-README.md` and `candidate-v2-README.md` before use.
- **Generator:** service construction V4/material V4 handback is retained. Core guard repair and service material V5 scripts are staged but not executed. The corrected core script includes seated positive-overlap fixings; see `../art/reference_street_20260910/generator-core-repair-inputs/README.md`. The protected painted-panel study **was** generated under `../meshy/ground-detail-20260910/generator-v4-panel-study`; source PBR/mask review and material audition are pending. No new generator runtime asset is installed.
- **Brush paint:** source maps and exact packed Lit textures are saved. Preview and material-only installer are staged; see `../art/reference_street_20260910/brush-pigment-lit-v1/README.md`. The preserved lettering sits roughly 9 mm off the shutter and the new opacity removes only 0.37% of painted area; both require actual source review.
- **Trash cloth:** candidate multi-view selections are staged, not executed or accepted. No cloth mask has been exported. Read `../art/reference_street_20260910/trash-cloth-v3-plan/PAUSED-STAGING-20260910.md`. The 35-triangle Blender discrepancy is from opposite-winding coincident source triangles with different UVs, not proven degenerate triangles.
- **Canopy diagnosis:** `../art/reference_street_20260910/NativeCanopyLightingReview.cs` and `NativeQa-canopy-diagnostic-candidate.cs.txt` are deliberately uninstalled. Before use, add OnDisable restoration and correct the all-camera scope of material/shadow isolates. Read `canopy-diagnostic-PAUSED.md`. Shipping NativeQa and the capture driver were restored exactly to native04.

Preserve all rejected/source revisions and unrelated working-tree changes. Root was the sole live-app operator; serialize Blender, Unity and native player on this 32 GB host. No asset tasks or scheduled continuation should be started during this pause. The original art goal is unfinished and was not marked accepted.
