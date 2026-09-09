# Two-building weathering pass — 9 September 2026

Field Supply and Finery now carry Blender-authored damage, chipped stone,
shutter corrosion, curled posters, painted factory lettering and sparse dried
blood marks, with localized runoff and foundation deposits. The accepted
[painted reference](../../../../refs/building_weathering_20260909/weathering-concept-v1.png)
guided this pass. Native acceptance by the user is still pending.

## Source, scope and recovery

The [source record](../../../../art/building_weathering_20260909/README.md) identifies
the Blender files, export scripts, provenance and recovery operation. Original
building meshes and collider proxies are retained. Installation and V3 update
both verified unchanged gameplay/collision signatures; source transforms and
prefab links remain. The saved scene was reopened and its render-chunk source
fingerprint verified fresh before building. All nine actors remain present.

This workspace already contained substantial uncommitted work. `initial-git-status.txt`
and `baseline-identity.json` record the starting point; `final-build-identity.json`
records the tested scene, final source export and player files. This evidence
qualifies that working-tree snapshot, not every change since the Git base.
`scene-diff-summary.json` compares the immediate saved baseline to the final
scene, including regenerated chunks. Do not restore the entire baseline scene
over subsequent edits.

## Build and visual evidence

- `baseline-development-build.json`: original saved scene built successfully.
- `development-build.json` and `release-build.json`: updated players succeeded,
  with zero build errors; one development warning and three release warnings.
  Existing project warnings are retained in `editor.log`.
- `before-native/`: 23 original 1920×1080 captures, including six views of each
  building and standard district cameras. The original capture process was
  interrupted by focus/memory pressure; retained reports document this. An
  optional HUD-hiding command was rejected by the existing diagnostic guard.
  The usable baseline captures retain the HUD.
- `after-native/field-captures.json` and `finery-captures.json`: completed matched
  native capture plans at 1920×1080, render scale 1, four-sample MSAA, full source
  textures, existing lighting/exposure and frozen reference time. Diagnostic
  cameras test appearance; real traversal is recorded separately.
- `candidate-v2-editor/`: rejected intermediate renders. Incorrect triangle
  winding caused edge/shading artifacts. V3 was rebuilt from original geometry
  with the correct rotation/winding conversion and updated in place.

Useful views: `after-native/cam_courtyard_facade.png`,
`cam_shop_recovery_field.png`, `cam_audit_field_supply_door.png`,
`cam_audit_finery_door.png` and the two `side_left`/`side_right` captures.
The after images are native game renders, not the generated paint-over.

## Visual assessment

Scores are a local review of these two facades against the accepted concept,
not a whole-game quality claim. Before and after use the same named native views.

| Category | Before | After | Observation |
| --- | ---: | ---: | --- |
| Composition and silhouette | 4 | 4 | Rooflines, entrances and signs remain recognizable. |
| Scale | 4 | 4 | Existing metre scale and door proportions retained. |
| Material detail | 2 | 3 | Torn paper, exposed substrate and shutter wear improve close views; some crack segments and plaster edges remain angular. |
| Lighting and depth | 3 | 3 | Actual shallow cuts and curled paper add contact depth. Existing deep canopy shade still suppresses detail. |
| Density and storytelling | 2 | 4 | Existing Karaveen/Ward motifs, localized damage and small stains make the two facades read as inhabited survivors. |
| Character and animation | 3 | 3 | Existing roster/animations retained; character improvements are outside this pass. |
| UI readability | 4 | 4 | Existing HUD and functional labels retained. |

This is a first implementation of the weathering direction. It does not yet
match the concept's fine fracture variation, broad surface aging or worn cloth.
The requested two-building change is intentionally localized; clean surfaces
elsewhere in Ward remain a separate rollout decision.

## Native checks

The native QA results and timing summary are recorded in `verification.json`.
`after-native/environment.json` and `settings.json` record the actual RTX 3060 /
i9-10850K host, driver, OpenGLCore API, 1920×1080 resolution, rendering settings
and nine-actor roster. Blender and Unity were closed for the traversal timing.
The unmeasured warm-up alone was recorded to video; recording stopped before
the measured pass. Unavailable timing or residency counters remain unavailable.

Runtime validation includes the saved source/chunk state, both porch approaches,
the existing district route, first-person zoom and mouse look, the city loop,
and a release smoke check. Detailed reports distinguish diagnostic placement
from real keyboard/mouse checks. Timing is scoped to this build and route;
there was no matched before-performance measurement under comparable memory
conditions, so this pass does not claim a before/after performance delta.
