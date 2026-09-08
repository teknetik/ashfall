# Mountains and terrain — 8 September 2026

The flat, detached mesa blocks have been replaced by a continuous original desert
basin: eroded escarpments, foothills, low passes and overlapping rear ridges. The
landscape is authored in Blender through its live MCP addon and imported as GLB.
The eight sectors total 5,120 triangles and extend to roughly 470 m from the city.
Twenty-six chipped stones add 520 triangles in the hill's planted quadrants.

The sandstone material uses original generated albedo, blended projections on
three axes, two texture scales, broad sediment variation, distance-faded surface
relief and exponential haze. Vertex colours carry baked sun occlusion and sky
access for the scene's fixed sun. The opaque forward pass writes depth without
repeating the distant landscape in the city's SSAO prepass. The ground material
blends detailed soil, gravel, olive cover and exposed rock. Existing grass remains.
Both generated albedo images are 1254×1254; the geological scalar texture is 1024².
Exact prompts, built-in ImageGen provenance and saved paths are in
[image-generation.json](image-generation.json).

## Preservation and editing

All 264 colliders, four talking NPC placements and three walker roots/routes were
preserved by the editor's before/after comparison. The old 36 mesa/buttress source
renderers remain disabled, and the static city chunks were rebuilt. Independent
GLB inspection found no degenerate triangles, no vertices in the playable city,
and matching normals at all 88 shared sector-border vertices. Camera far planes
are 650 m; the sky's flat ridge overlay is disabled. Lighting, sky, buildings,
player and gameplay systems are retained. Concurrent controls and audio work was
preserved and included in the final players.

See [editing controls](../../../EDITING.md#mountains-and-terrain). The terrain is
render-only outside the city walls; this does not create a second playable zone.
The baked geological lighting must be regenerated if the sun direction changes.

## Validation

Both Linux players built successfully, including the concurrent controls and audio
updates. The raw reports preserve Unity's two startup licensing-error counts;
`final-build.log` contains no C# compiler or shader compilation failure. The native
player logged no runtime exceptions or shader failures.

At 1920×1080 on the RTX 3060 / i9-10850K desktop, 21,362 moving frames
averaged **422.0 FPS**, with **3.65 ms p99** and
**6.72 ms maximum**. Every sampled walking frame stayed above
60 FPS. Maximum walking geometry was **249,679 triangles**.
The exact frame data is retained in [native/profile.json](native/profile.json).
GPU timings are unavailable; performance is measured from actual frame intervals.

Real-keyboard traversal passed the hill stairs, Ring Gate and Lattice Jack.
All four conversations, modal input, buying a flask, selling scrap, linking a
Lattice destination, inventory/notes, pause/reset and Reduced Motion passed.
The native result is [native/report.json](native/report.json).

Independent OpenGL tracing over 401 rendered city frames measured
**80 draw submissions** and **249,667 submitted triangles** at most,
including world, actors, shadows, terrain, atmosphere and HUD. Both rendering
budgets pass. See [gl-trace/report.json](gl-trace/report.json). This instrumented
trace is draw/geometry evidence, not FPS evidence.

Exact source and both built-player hashes are preserved in `source-sha256.json`,
`Linux-sha256.json` and `LinuxDevelopment-sha256.json`.

The final release passed launch, movement/dialogue/pause input, nonblank rendering,
absence of runtime exceptions, and absence of the development QA listener. See
[release-smoke/report.json](release-smoke/report.json). The QA players are closed
and the desktop resolution was restored.

## Visual assessment

The six fixed Unity cameras were inspected after each substantial pass. The first
iteration was rejected for crowding the sky and noisy surface gradients; the next
was refined to suppress texture repetition and add geological shadowing. The
initial native run passed gameplay but exceeded the triangle contract; its
`complete: false` result is retained in `native-initial/`. The first two trace
reports are intermediate evidence, not final acceptance.

Scores below are subjective 0–5 for the mountain/ground work in the three fixed
hero frames against the frozen reference palette and geological character.
They are not scores for the entire inherited city or a photorealism certification.

| Camera | Terrain palette | Ridge silhouette | Light/depth | Rock roughness | Ground detail |
| --- | --- | --- | --- | --- | --- |
| Hill | 4 | 4 | 4 | 4 | 4 |
| Avenue | 4 | 4 | 4 | 4 | 4 |
| Gate | 4 | 4 | 4 | 4 | n/a |

The result is a substantially more finished terrain treatment within the existing
2001 sci-fi city style. The broad mountain slopes still use a deliberately small
mesh budget; the original tree shape and flat raised garden are wider environment
art limitations outside this terrain material/backdrop pass. A medium laptop has
not been qualified; the final measured machine is identified in the native report.

`before/` holds the pre-terrain native views. `editor/` and `native/` hold the final
Unity views. The six Blender source-geometry cameras are in
`blender/previews/terrain-20260908/`; Unity is the final material/atmosphere authority.
