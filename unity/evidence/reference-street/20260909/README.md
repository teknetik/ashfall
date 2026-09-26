# Reference street — 9 September 2026

Field Supply and Finery received a saved native Unity material, threshold and
daylight pass against the user's supplied image. Native functionality and the
recorded performance profile pass. **The reference's visual fidelity is not yet
met or accepted by the user.** [qualification.json](qualification.json) is the
final index; earlier failed inspections remain intact.

![Final native street view](after-native-final/cam_reference_street.png)

## Source and change

- Target: [unaltered user image](../../../../refs/reference-street/20260909/user-target.png).
- Starting HEAD: `618eae098c11dc65d7ad2c5ecf482ddfc6102ee5`; the starting tree was
  already modified. [baseline.json](baseline.json), [before-scene.unity](before-scene.unity)
  and [git-status-before.txt](git-status-before.txt) preserve that working baseline.
- Final saved scene SHA256:
  `b95781410e3cdb71002f4a0e25e6753ba51651071608b3c4a127a103f96877ed`.
- [Source record](../../../../art/reference_street_20260909/README.md) retains live
  Blender studios, detailed geometry, full 4K bakes, import contracts and provenance.
  Unity assets are under `Assets/AthenHill/Art/ReferenceStreet/20260909`.
- New plaster maps and eight localized mineral films; carved joints/chipped
  thresholds on four existing visual meshes; small grit and eight reused dry plants.
- V3 dark painted metal with broken shutter-lip corrosion and small coating losses;
  broader original brush lettering. The initial clean-grey metal audition was
  superseded after native review. Original materials, meshes and lettering survive.
- A cloned noon profile turns sunlight onto the facades, adjusts ambient/fill and
  exposure, and uses a revised cloud shader. Noon reflections were rebaked after
  the final integration. Original profile, sky and original courtyard reflection
  assets remain available. Other day/night keyframes, URP and OpenGL remain.
- [Install log](installation.json), [V3 log](metal-v3-installation.json),
  [runoff log](mineral-runoff-installation.json), [plant placements](joint-growth-placements.json)
  and [reflections](reflection-bakes.json) record the exact affected sources.

The source renderers were shown for editing and chunks explicitly rebuilt. The
[saved scene reopened with fresh chunks](build-v3/reopened-source.json): 6,019
source renderers and 134 generated chunk objects. No disposable chunk was edited
directly. Collision JSON before/after is byte-identical. The original gameplay
signature is identical, and a separate [all-four-walker audit](actor-route-preservation.json)
verifies 16 ordered waypoints and 54 serialized route/ancestor documents, including
the mechanic. The native roster remains nine actors. Package/version files and
both built gameplay assemblies match the starting baseline.

## Native verification

Both [development](build-v3/development-build.json) and
[release](build-v3/release-build.json) Linux builds succeeded, each with zero errors
and one reported warning. [Release smoke](release-native/report.json) verified
visible rendering, keyboard response and that the development QA option is ignored.
The final player log contains no matched runtime exception or shader failure.

Final evidence is in [after-native-final](after-native-final). The saved source,
scripts included in the identity record, and packed build data remained unchanged
through verification; see [identity manifest](after-native-final/reference-identity-after.json).

- One recorded, unmeasured full route; then a separate warmed traversal through
  41 destinations, plus its starting checkpoint. Both passed. Video recording
  had stopped before timing began.
- [Proximity V3](after-native-final/reference-proximity-v3.json): 17 real-input
  checkpoints across both facades, both treads, porches and plant views, with real
  wheel zoom/mouse look and camera-clearance assertions. All passed.
- [City loop](after-native-final/city-loop.json): 29 checks passed, including all
  four dialogues, modal blocking, atomic flask purchase/scrap sale, inventory,
  notes, pause, Lattice destinations, offline Ring Gate and objectives.
- [Lighting](after-native-final/reference-lighting.json): 20 native views at
  midnight, 06:30, noon and 17:30. Eight additional saved NPC face/full-body views
  verify the new lighting on all four talking characters.
- [Walkthrough](after-native-final/store-walkthrough.mp4) and
  [final first-person recording](after-native-final/reference-first-person-v3.mp4)
  retain moving gameplay. Three extracted frames at 54–55 seconds were inspected
  for gross geometry/material popping and ghost trails. This is sampled motion
  review, not certification of complete temporal stability or animation quality.

### Recorded performance

RTX 3060, 12,288 MiB VRAM; i9-10850K; NVIDIA 595.84; Linux/OpenGLCore. PC profile,
1920×1080, render scale 1, MSAA 4, shadows 3/4096, 18 m shadow distance,
post-processing enabled, nine actors, HUD/effects active, VSync off and uncapped.
Unity and Blender authoring processes were absent during measurement.

| Measurement | Warmed walking | Separate interactions |
|---|---:|---:|
| Duration | 134.685 s | 29.246 s |
| Frames | 23,321 | 7,818 |
| Average FPS | 173.15 | 267.32 |
| p50 | 4.26 ms | 2.85 ms |
| p95 | 11.59 ms | 6.94 ms |
| p99 | 13.44 ms | 8.27 ms |
| Maximum | 27.18 ms | 136.38 ms |
| Frames >33.33 ms | 0 | 3 |

Both meet average >=60 and p99 <=16.67 ms. The interaction recording retains
127.02 ms in Dialogue, 136.38 ms in Shop and 117.70 ms in Grid; these first-use
hitches remain a limitation. No performance improvement over an unmatched earlier
run is inferred. Full frame/counter data is retained. Mean walking main-thread time
was 5.77 ms; GPU/render-thread time, draw calls and batches were unavailable.
Submitted triangles averaged 8.11 million across rendering passes, not visible
source geometry; mean SetPass count was 54.59.

One pre-route memory observation recorded process RSS 2,026,548 kB and GPU process
memory 3,074 MiB. GPU process memory includes more than textures; resident texture
bytes and measured loading duration are unavailable. These are observations, not
whole-run peak-memory claims.

## Preserved failed attempts and corrections

`after-native` captured the first material audition. Its preflight misclassified
the player by its Unity thread name and also found abandoned import workers.
`after-native-v3` captured the final material revision but still found two old
workers which had ignored SIGTERM. Their original Editor parent was absent; they
were stopped, and the process guard returned an empty authoring-process list.
Neither attempt produced a walking timing result.

The first new proximity test placed its Finery plant-view waypoint inside the
unchanged salvage crate at `(15.65, .505, -20.7)`. V2 moved that inspection to the
north plant, but a descending-tread observation stopped too near the upper porch.
With the saved 0.35 m controller radius, X=14.233 still intersected the raised
porch edge. V3 uses X=14.05, an 8 cm arrival tolerance and 0.5 s settling before
the same grounded/height checks. It passed completely. No collider, prop or game
logic was moved to pass these tests.

All initial reports, screenshots, videos and logs remain under their original
names. The unchanged walking measurement is reused because source/build identity
matches. Interaction/lighting completion and V3 proximity results are indexed in
`qualification.json`; the initial incomplete wrapper reports intentionally remain
incomplete. The corrected standalone test is
[check_reference_proximity_v3.py](check_reference_proximity_v3.py); use it instead
of the historical first proximity script when reproducing this inspection.

## Visual review and remaining work

The [independent native review](independent-native-v3-review.json) confirms that
the dark metal and brush improvements survive native rendering. Whole-view
scores remain composition 3, scale/construction 4, materials 3, lighting 3,
density/storytelling 3 and static UI 4 out of 5. The new screenshot is closer to
the target; it does not establish the required 4 in every applicable art category.

The largest gaps are pale repeated plaster mottling and isolated thick spall
edges, regular threshold construction, faceted debris, generic wear across metal
parts and flat close-range paint. The canopy, terrain and cloud structure remain
simpler than the supplied reference. Nighttime Field Supply retains very dark
unlit areas. Existing character texture/joint/hand limitations remain; this pass
does not qualify animation or whole-game contemporary AAA fidelity.
