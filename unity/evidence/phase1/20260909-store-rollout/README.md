# Six-store installation — 9 September 2026

The saved native scene now has replacements for **9/9 store buildings**. Finery, Basic General and Relay Works were already installed; this pass installs the remaining six. Vanguard Hall is a separate landmark and retains its existing uniform fit; its new source is still staged. Replacement count does not establish final visual acceptance. Phase 1 remains open.

![Six installed stores in the native Unity player](native-front.jpg)

The [individual building ledger](../../../../docs/building-repairs-20260909.md) keeps each remaining defect open. These are actual native captures of the saved scene, not Blender source previews.

## Installed geometry and preservation

| Store | Separate source parts | Source triangles | New colliders | Distinguishing construction |
| --- | ---: | ---: | ---: | --- |
| Air + Water | 375 | 98,432 | 6 | Offset entrance, broad upper window, connected roof tanks, facade filter bank |
| Field Supply | 274 | 60,024 | 9 | Low pitched roof, loading shutter, separate staff door, post-supported loading canopy |
| Repairs | 297 | 77,972 | 6 | Workshop shutter and side entry, raised ventilation, exhaust and rear louvre |
| Salvage | 361 | 82,340 | 7 | Pitched loft, unequal windows, reclaimed panels and wall-mounted hoist |
| Thread + Hide | 333 | 87,988 | 6 | Narrow upper windows, plum canopy, roof drying frame and cloth |
| Tool Exchange | 289 | 74,364 | 5 | Broad shutter, recessed display, clerestory and offset roof monitor |

The six retain 1,929 separate source parts and 481,120 source triangles. Those are asset counts, not camera-visible or multipass submission counts. Each revision 04 prefab uses the original parcel at uniform scale. Detailed meshes, UVs, tangents, shadows and full shared source maps remain editable. Existing materials are reused with individual cloth tints; no district atlas or destructive source reduction was introduced. Original meshes and separate old signs remain recoverable with their renderers disabled.

Live Unity Editor operations installed the prefabs, rebuilt derived render chunks, saved and reopened the scene. [Saved-scene verification](saved-installation-verification.json) confirms all six are in the current chunk source records. [Preservation comparison](preservation-comparison.json) records all nine actors unchanged, no lost collider IDs, six old warped-shell colliders disabled and 39 new wall/door/post/roof colliders. Every other collider, including the original steps and porches, is unchanged. Seven rejected `District rebuild` candidates remain inactive; both existing gate arches remain active. The courtyard, gameplay roots/data, terminals and actor routes were retained.

## Build identity and native views

[Build identity](build-identity.json) records scene, importer and prefab hashes over working-tree base `d4b867bb22a1489b5cd05373221b55dbec7bd5d4`. This is not a clean commit build. The saved scene SHA-256 is `35bf18b475d2a70800970dbd75073b81f973cbb661ebfbabd1cda158a2714956`. [Reverification](build-identity-verification.json) confirms those eight files still match the tested build.

[Development](development-build.json) and [release](release-build.json) Linux builds both succeeded with zero errors and one warning each (31.54 / 30.11 seconds). The retained Editor log reports reduced additional punctual-light shadow resolution to fit the 2048 atlas; existing obsolete-API warnings also appear during Editor compilation. These warnings remain unresolved.

The [baseline identity](baseline-identity.json) matches the previous three-store build. [Before captures](before-native/building-pass-captures.json) contain 43 clear native frames: seven overview cameras plus six original audit angles for each new store. [After captures](after-native/building-pass-captures.json) repeat all 43 and add 18 front/door/roof views. All [61 after frames](after-native/capture-validity.json) and all [43 before frames](before-native/capture-validity.json) are in Play at native 1920×1080. The initial environment/settings header was taken during window resizing and says 1920×1043; actual per-capture snapshots and PNG dimensions are 1920×1080.

[Matched before/after fronts](native-before-after.jpg), [door close-ups](native-door.jpg), [roofs](native-roof.jpg), [left sides](native-side_left.jpg), [right sides](native-side_right.jpg) and [backs](native-back.jpg) retain the individual native originals in their capture folders. Noon lighting, exposure and the original camera transforms/lenses are matched. Diagnostic cameras leave the player at its existing position, so the Vex interaction overlay in these stills does not mean Vex moved to every store.

## Real-input route and timing

Both the unmeasured warm-up and measured traversal pass all **41 waypoints**, including all nine store porches, Hall, hill stairs and mission slab. All nine actors, HUD, shadows and existing effects remain active. The day clock is held at noon; simulation time is 1.0. [Route results and timing](after-native/traversal-performance.json) belong to this build.

The [135.07-second walkthrough](after-native/store-walkthrough.mp4) records the unmeasured route at native 1080p/30 FPS. Video encoding exited before the measured route. The clip preserves real input and moving actors; it is not a full temporal-art acceptance.

| Metric | Measured traversal |
| --- | ---: |
| Duration / frames | 134.76 s / 21,914 |
| Average FPS | 162.62 |
| p50 / p95 / p99 | 4.99 / 11.30 / 15.29 ms |
| Maximum | 38.60 ms |
| Frames over 33 / 50 ms | 1 / 0 |
| Main-thread / CPU mean | 6.15 / 6.15 ms |
| GPU / render-thread time | Unavailable |
| Draws / batches / resident texture bytes | Unavailable |
| Submitted triangles, mean / max | 8.56 M / 26.45 M across renderer passes |
| SetPass mean / max | 54.62 / 125 |

This sample meets the current average >=60 FPS and p99 <=16.67 ms criteria. It includes one 38.60 ms hitch. Main-thread time includes waits. Submitted geometry is not visible source geometry. Loading is outside the warmed route; no separate loading qualification is claimed.

[Hardware](after-native/hardware.json): RTX 3060 / i9-10850K, driver 595.84, 12 GiB VRAM, approximately 32 GiB system memory; OpenGLCore, native 1920×1080, render scale 1.0, MSAA 4, full texture setting, 4096 main shadows at 18 m, VSync off, uncapped, no frame generation. Editor closed. After the route, the native process used 2.46 GiB GPU allocation and 1.68 GiB RSS. GPU allocation includes more than textures; texture residency is unavailable.

## Interaction and release checks

The [29.52-second real-input city loop](after-native/city-loop.json) passes all four dialogues, modal movement blocking, flask purchase (25 to 21 credits), scrap sale (21 to 22 credits), inventory, notes, pause, audio/reduced-motion controls, two Lattice destinations and the Ring Gate offline response. [Separate interaction timing](after-native/interaction-performance.json) records 134.49 ms Dialogue, 116.48 ms Shop and 128.41 ms Grid transition hitches. [Hitch samples](after-native/interaction-hitches.json) are preserved; this build is not hitch-free.

The shipping [release smoke test](release-native/report.json) passes startup, nonblank rendering and real keyboard input with no runtime exceptions. The release ignores the development QA option and produces no command snapshot. Native [startup](release-native/startup.png) and [pause](release-native/pause.png) frames are retained. This is a bounded release smoke test; the full route and city-loop assertions above ran in the matching development build.

## Individual visual findings and remaining work

The [per-store native review](visual-review.json) compares front/entrance/sides/back/roof captures with the retained [courtyard target](../../../../refs/courtyard_20260908/accepted-target.png). Distinct silhouettes and human-scale entrances replace the repeated stretched shells. The roof/door connections and porch bases show no gross detached geometry in these views.

Material detail and shaded depth remain at **2.5/5**, working-space detail at **2/5**, below the target of 4. All six have overly plain side/rear wall fields. Dark windows, shutters and metal fittings lose depth; stock, services and shop-specific props remain sparse. Air + Water needs better filter fittings, Salvage needs hoist working context and controlled panel ageing, Thread + Hide needs stronger cloth/textile detail, and Tool Exchange has an empty dark display. Full sun/shade motion and temporal quality acceptance remain open. These replacements must not be called an accepted district standard.

## Source provenance and recovery

The [source manifest](../../../../art/quality_20260909/relay-family/store-variants-04/manifest.json) records the six original editable architectural sources. Its historical source-preparation status is retained; `prepared-*.json` and `installed-*.json` here record the subsequent Unity installations. The earlier [source review](../20260909-buildings/source-review.md) and [export verification](../20260909-buildings/source-export-v4-verification.json) preserve the corrected revision 04 door seals and original geometry. No rejected Meshy candidate was re-enabled.

The full [before scene](before-scene.unity) restores the starting three-store state. Individual `before-*.unity` copies preserve each installation step; intermediate copies may have editable sources shown and require an explicit render-chunk rebuild. Original source maps, asset GUIDs and [material provenance](../../../AthenHill/Assets/AthenHill/Art/THIRD_PARTY_LICENSES.txt) are retained. No previous dated build evidence is relabelled as evidence for this rollout.
