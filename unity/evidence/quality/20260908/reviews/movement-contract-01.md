# Character movement — independent handoff review 01

8 September 2026. Reviewer: `visual_critic`. **Decision: ready for installation/testing, not visually accepted.** No new native motion has been supplied. No animation quality score is assigned from clip names, source clearance samples, state-machine assertions or code.

Reviewed the [movement handoff](../movement/README.md), [real-input test script](../movement/check_character_motion.py) and [source audit](../movement/source-audit.json). The handoff explicitly preserves controller tuning and character identities, records limitations and distinguishes generated source motion from native acceptance. This is a useful, honest contract. This review has not executed its tests, inspected actual new clip playback or reviewed the implementation code for correctness.

## What the planned automatic run actually establishes

The script records standing and running jumps, held/repeated jump inputs, inventory input blocking, a hill walk-off, a stair jump and a level-ground first-person jump. It checks motion samples for accepted jumps, phase presence, height, grounding and continued running on moving landing. It records one optional 1080p/60 video from the selected follow camera and finishes with an actor snapshot. These are valuable behavioural checks when they pass in the saved native build.

That single video is **not** the complete independent visual evidence requested in the handoff. Specifically, the script does not provide the following:

| Missing evidence | Required native capture and rejection checks |
| --- | --- |
| Third-person front/side jump views | Same standing and running jump from front three-quarter, side and rear, at useful full-body scale. Review takeoff compression, arm arcs, pelvis/leg timing, boots, landing contact and transition back into movement at normal speed, then inspect questionable frames slowly. Reject knee inversions, armour/body intersections, a rigid airborne stand, pose snaps or sliding recovery. |
| Guard idle/talk loops | All four talking guards, full body plus conversation distance, with at least three complete repetitions of each assigned idle/talk loop and idle→talk→idle transitions. The recorded 4 s idle and 5.1667 s talk need clips long enough to show seams rather than one short sample. Check planted soles, knees, pelvis drift, gesturing hands, helmet/torso clipping and return to the authored interaction root. |
| Player idle and locomotion transitions | Continuous starts/stops, walk↔run changes, turning in place, running turns and movement immediately after landing. The phase/state checks alone cannot establish compatible stride phase or convincing footwork. |
| Ambient route corners | Each traveler and the mechanic seen approaching, traversing and leaving representative corners. The handoff preserves piecewise-linear travel while easing heading; explicitly check visible sideways travel, shoulder-leading pivots and foot sliding at that mismatch. A smoother rotation is not automatically a convincing turn. |
| First-person edge cases | Jump/land on stairs and near walls/door frames, walk off a ledge, zoom between views while movement settles. Inspect near clipping, camera overlap and unwanted body/shadow discontinuities. Current first-person automated scenario only jumps on level ground from reset. |
| Clear timing and identity | Supply tested scene/build hash, settings, scenario start/end timestamps in the recording, actor/clip assignments and exact test results. The combined video starts before scenarios but currently records no per-scenario video-offset index; provide an index or separate named clips so findings are reproducible. |
| Preservation in native builds | Verify saved/reopened animation references and development/release builds, unchanged controller path/height/speed/collision where promised, dialogues, routes, modal controls and reduced motion. An actor snapshot or a source map does not prove the correct clip was playing throughout. |

Source heel/toe clearance of millimetres after a constant hips correction is useful diagnostic evidence. It does not establish planted feet in Unity, slope contact, final skin deformation or horizontal sliding. A 24-bone source without articulated fingers/facial motion also limits what an idle/talk pass can accomplish; retain those defects explicitly rather than calling the whole character AAA after its body begins moving.

The baseline's **VEX-02 remains rejected** and animation/temporal scores remain **U** for the candidate. On native handoff I will inspect the clips independently, record exact time/view defects and request specific revisions. Material recovery from `ActorSurfaceFidelityPass` will receive a separate native surface review; improved animation cannot accept unresolved armour/face/hand geometry by association.
