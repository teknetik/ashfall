# Phase 1 first repair pass — 8 September 2026

**Phase 1 started after “Add localized dirt and wear” finished. This first pass is not completion of Phase 1 or acceptance of the district's visual target.** The predecessor's courtyard and other uncommitted work are preserved.

## Saved changes and identity

The [build identity](build-identity.json) records base commit, working-tree status, saved-scene SHA-256, render-source fingerprint and development/release file hashes. [Before scene](before-scene.unity) and [final scene](final-scene.unity) preserve the complete authoring state. Unity 6000.6.0f1, URP 17.6 and Linux OpenGLCore remain in use.

- **Finery:** replace its distorted Relay visual with 267 original Blender parts, 51,052 triangles, a solid two-storey facade, recessed shutters, 2.35 m door leaves, roof/copings, tank/services and a small modelled practical light. Retain the existing porch, steps, canopy, notices and props. Preserve the old visual and MeshCollider disabled; a fitted closed-shop proxy follows the new shell. The original sign lettering is retained and fitted by renderer bounds, with a dark backing and warm lettering. The earlier pivot mistake is documented in [sign refit](finery-sign-refit.json).
- **Hall:** uniform scale restores source proportions while preserving its front edge and base. The plinth visual and collider are refitted to the new depth. See [exact transform report](hall-refit.json). Warped source construction remains a separate repair.
- **Vex:** recover original 2K PBR maps, calculate tangents on a separate compatible mesh and restore shadows; remove the dark albedo tint. Vertices, normals, UVs, topology, bone weights and bindposes are retained. Only Vex receives this material/mesh override. The generated 4K candidate is unassigned because it invented lettering and changed identity details; [source and credit record](../../../../meshy/ward-guard/phase1-20260908/README.md).
- **Tree:** a separately authored connected root flare closes the old joins; full 4K CC0 bark uses OpenGL normals and roughness-to-smoothness packing. A rejected projection switch produced a hard texture seam; continuous flared-cylinder coordinates remove that seam. Existing root collision and upper crown geometry remain. Visible wood/foliage shadows replace three crude shadow proxies. Crown geometry, flow UVs, tangent validity on legacy branches and foliage still need work.

Authoring is retained in [Blender sources](../../../../art/phase1_20260908/README.md). The accepted courtyard reference remains [here](../../../../refs/courtyard_20260908/accepted-target.png). Tree bark is [Poly Haven Bark Willow 02](https://polyhaven.com/a/bark_willow_02), Charlotte Baglioni, CC0; original maps and download hashes are retained under refs/phase1_20260908/materials. Shipping licence notices include these assets.

## Native review

[Before](before-native/capture-report.json) and [final](final-native-02/capture-report.json) include 18 matched views; three new Finery views supplement the final set. They use the same saved camera positions/lenses, native 1920×1080, 100% render scale, 4× MSAA and the existing exposure. Fixed diagnostic cameras retain the HUD; the interaction prompt follows the player at Basic General, not the camera location. These diagnostic teleports do not qualify traversal.

| Review | Before | Final |
| --- | --- | --- |
| Finery pedestrian frontage | [Before](before-native/cam_courtyard_facade.png) | [After](final-native-02/cam_courtyard_facade.png) |
| Finery front / door / roof | — | [Front](final-native-02/cam_p1_finery_front.png), [door](final-native-02/cam_p1_finery_door.png), [roof](final-native-02/cam_p1_finery_roof.png) |
| Hall proportions / back | [Front](before-native/cam_p1_hall_front.png), [back](before-native/cam_grounding_hall_back.png) | [Front](final-native-02/cam_p1_hall_front.png), [back](final-native-02/cam_grounding_hall_back.png) |
| Vex close-up | [Before](before-native/cam_p1_vex_face.png) | [After](final-native-02/cam_p1_vex_face.png) |
| Root joins | [Before](before-native/cam_p1_tree_roots.png) | [After](final-native-02/cam_p1_tree_roots.png) |
| District / tree silhouette | [Before](before-native/cam_hill.png) | [After](final-native-02/cam_hill.png) |

Provisional 0–5 review against the production target; 4 means strong at intended viewing distance. These scores do not imply user acceptance.

| Category | Before | After | Evidence / remaining issue |
| --- | ---: | ---: | --- |
| Finery construction / silhouette | 2 | 4 | Correct doors, real reveals, solid roof and varied roofline; rear wall remains plain. |
| Finery scale / clearance | 2 | 4 | Measured door leaves and uniform authored geometry; retained porch and route. |
| Close materials | 2 | 3 | Tiled stone and root bark improve clarity; door wear is repetitive, original hall and Vex maps remain soft. |
| Lighting / depth | 2 | 3 | Entrance practical and Vex/tree shadows improve contact; broader bounce and shaded metal still need work. |
| Density / storytelling | 3 | 3 | Existing courtyard retained; tank/services make the frontage functional, surrounding walls remain bare. |
| Character / animation | 2 | 2 | Surface restoration helps Vex; unchanged soft source detail and static talk/idle pose remain prominent. |
| Tree root shape | 1 | 3 | Joins are closed; some roots are bulbous and side UVs stretch. Upper crown quality remains unfinished. |
| Temporal stability | — | 3 | Short moving review supplements fixed frames; longer foliage and shadow-edge inspection remains. |
| UI / readability | 4 | 4 | HUD, keyboard access and readable Finery sign retained. |

These results do not meet 4 in every category. Continue with source-level Vex detail, tree branching/canopy and varied building construction; do not infer GTA6 or whole-game AAA parity from this pass.

## Accounting and preservation

The first inventory records 917 intended active source instances / 770 unique meshes / 1,401,874 source triangles. The final inventory records 1,169 instances / 1,027 unique meshes / 1,642,388 source triangles. Hidden/rejected geometry and generated chunks are recorded separately. Those counts are neither unique visible-camera geometry nor multipass GPU submissions. No LODGroups are installed in this pass; detailed source remains available for reviewed distance variants when measured cost warrants them.

[Preservation comparison](preservation-report.json) verifies all nine actor paths/positions unchanged. Collider changes are limited to hall visual fitting, the hall plinth, the retired Finery MeshCollider and its new fitted proxy. Duplicate gate hierarchy names were compared as multisets with bounds, avoiding a false duplicate-path mismatch. Seven rejected shops remain inactive. [Audit and individual follow-ups](../../../../docs/mesh-audit.md) keep wider visual review open.

## Verification and measurement

Final route/state/motion and release results are recorded below. Early attempts are retained: `native-route` passed route/verbs but used a 60 FPS cap; `after-native` predates the sign pivot fix; `final-native` stopped before capture because the window manager initially reduced height to 1043; `final-route` stopped at startup because the driver attached before the first snapshot. They are not substituted for final evidence. The private QA XML now includes Unity's required version attributes, and the measured viewport and uncapped settings are explicitly checked after startup.

The final uncapped player uses RTX 3060 12 GB / i9-10850K, NVIDIA 595.84, OpenGLCore, native 1920×1080, render scale 1, 4× MSAA, 4096 main shadow map / 18 m shadow distance, full textures, post-processing, HUD/audio/effects and all nine actors. Editor and Blender were closed. No frame generation.

| Sample | Seconds | Frames | Mean FPS | p50 ms | p95 ms | p99 ms | Max ms | >33.33 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Fixed Vex view | 10.18 | 2,505 | 246.0 | 3.70 | 5.47 | 5.73 | 11.20 | 0 |
| Real-input district / hall traversal | 100.25 | 22,756 | 227.0 | 4.38 | 6.68 | 7.57 | 20.21 | 0 |
| Warmed shop / travel / UI | 25.63 | 8,053 | 314.2 | 2.48 | 6.02 | 6.85 | 12.79 | 0 |

Both moving and state samples meet average FPS ≥60 and p99 ≤16.67 ms. Shop was measured for 5.28 s at 209.1 FPS / p99 5.98 ms; Grid for 6.85 s at 418.2 FPS / p99 3.59 ms. These are recorded samples, not an every-route/long-session guarantee. Cold loading was not instrumented.

Traversal CPU frame mean is 4.41 ms and main-thread mean 4.40 ms. Submitted triangles average 3.90 million, p95 9.15 million and maximum 9.93 million across rendering passes; these are not unique visible triangles. SetPass averages 57.1, max 116. Draw/batch, render-thread and GPU-time counters are unavailable; none is reported as zero cost. The extra local shadow work is measured, not hidden by a retired triangle/draw limit. See [performance and counters](performance.json).

The sampled player GPU allocation is 1,363,148,800 bytes (1.27 GiB), RSS 800,564 KiB and peak RSS 878,028 KiB on this run. Resident texture memory is unavailable; GPU process allocation includes more than textures. See [hardware](final-route-02/hardware.json).

[Final route report](final-route-02/report.json) and [grounded checkpoints](final-route-02/walking.json) cover the west approach, tree/north stairs, terminals, Finery porch/notices, hall tread/plinth/side/back and service lane. [City-loop checks](final-route-02/city-loop.json) retain all four dialogues, atomic flask purchase/scrap sale, modal blocking, Lattice choices, Ring offline response, inventory/notes, pause, mute and reduced motion. [Warmed state report](final-states/report.json) measures those UI/travel states separately.

The earlier capped run is retained separately: 59.99 average FPS / p99 16.75 ms over 100.30 s, max 17.53 ms. It misses the strict qualification boundary due to the 60 FPS cap and is not combined with the final uncapped measurements.


[Moving close-up report](final-motion/motion-report.json) passes real wheel zoom and
strafe at Finery, the root flare, hall and Vex; Vex conversation also opens correctly.
Each clip is 10 seconds at 1920×1080 / 30 FPS capture, with 60 FPS/VSync-limited play,
separate from the uncapped timings. Review samples at 2, 6 and 8.67 seconds show the
geometry through viewpoint changes. Finery and roots are clearer, but the hall's
close door map remains soft, Vex remains stiff, and root-side stretch remains.
These short samples do not certify long-session foliage/shadow stability.

- [Finery motion](final-motion/finery-motion.mp4)
- [Root motion](final-motion/tree-motion.mp4)
- [Hall motion](final-motion/hall-motion.mp4)
- [Vex motion](final-motion/vex-motion.mp4) and [conversation](final-motion/vex-conversation.png)

Both final Linux builds succeed with zero errors and one existing pre-baked mesh
collision import warning each. [Release smoke](final-release/report.json) passes
native rendering, real keyboard responses and absence of the development bridge;
the release ignores `--athen-qa`. Native logs contain no runtime exceptions or
shader-creation failures. Saved/reopened source scene and the built scene hash
match; build checks enforce the render-source fingerprint. New QA Python files
compile successfully. Diff review leaves Unity's three generated blank-value
trailing-space lines unchanged to preserve the exact tested serialized scene.

The mesh count ledger is complete accounting; the wider Phase 0 visual audit is
not complete. Phase 1 remains open for the individual building tasks, Vex's source
and pose quality, hero crown/leaf geometry, legacy branch tangents/UVs and stronger
close-range material/lighting work. No shared-guard rollout or rejected shop
reactivation occurred. No banked Codex reset was needed for this pass.
