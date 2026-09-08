# Unity atmosphere pass — 8 September 2026

The saved Unity city now has a layered cloud sky, a warm dust horizon with distant
ridge silhouettes, mottled olive/soil ground cover, wind-bent grass and sparse
floating dust. The sky reflection is baked into a 128px cubemap. The recent stone,
paving and gunmetal texture work and sun lighting have been retained.

All additions are original project shaders or numerical procedural data. No
external environment assets or Meshy credits were used. The installed Meshy skill
is scoped to humanoid character generation; this environment pass does not need a
new character. Existing Ward Guards and walking Travelers remain in place.

## Editing and geometry

See [Unity editing controls](../../../EDITING.md#sky-grass-and-drifting-dust).
Four separately editable grass patches use saved mesh assets and cost 1,360
triangles total. Their placement avoids the path strips, root centre, terminal
feet and NPC standing positions. Dust is limited to 64 particles (128 triangles).
Grass has no shadow pass. The sky/backdrop needs no new environment geometry.
The runtime component advances only the wind clock; it does not generate meshes.

The authoring comparison preserved all 264 colliders, four talking NPC placements,
and three walker roots/routes. Existing render chunks passed the unchanged source
fingerprint check; no world batch was rebuilt. The add-atmosphere menu refuses to
replace a previously installed setup. Shader/scene/material/mesh hashes are saved
in `source-sha256.json`.

## Native verification

Both Linux builds succeeded with zero errors. The development player completed
continuous keyboard traversal of the hill stairs, Ring Gate and Lattice Jack,
all four conversations, buying a flask, selling scrap, linking a destination,
modal input checks, inventory, notes, pause and reset. Shader/runtime error checks
passed. Reduced Motion clears the dust and freezes both grass and cloud animation;
switching it off resumes them. These behaviours are asserted in `native/report.json`.

At 1920×1080 on the RTX 3060 / i9-10850K desktop, the final pass recorded 21,937
walking frames at **433.5 FPS average**, **3.38 ms p99**, and **5.25 ms maximum**.
The maximum walking triangle counter was **249,475**, below 250,000. GPU timing
and Unity draw counters are unavailable/reported as zero, so draw counts are
verified separately through OpenGL tracing. The final trace measured a maximum of
**78 draw submissions** and **249,423 submitted triangles**, including
world, actors, shadows, atmosphere and native HUD. The release smoke check also
passed movement/dialogue/pause input, nonblank rendering and absence of the
development QA listener. This is desktop evidence; a medium
laptop has not been qualified.

`native/` contains the final six fixed cameras, close grass view, gameplay results,
profile and player log. `native-initial/` retains the first grass rendering before
its blades were made broader, more curved and less uniformly golden. `before/`
contains the pre-atmosphere native views and performance evidence. `editor/`
contains the final fixed-camera renders without HUD.

## Visual review against the frozen reference

Scores are subjective, 0–5, for the same three hero cameras. They describe the
whole frame; this pass does not claim completion of the larger environment remake.

| Camera | Palette | Sky/haze | Silhouette | Light direction | Roughness | Density | Scale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Hill | 4 | 4 | 3 | 3 | 4 | 3 | 4 |
| Avenue | 4 | 4 | 3 | 3 | 4 | 3 | 4 |
| Gate | 4 | 4 | 4 | 3 | 4 | 3 | 4 |

The sky now has cloud structure, a continuous warm horizon and atmospheric depth.
The flat green hill surface has ground variation and visible blades at eye level.
The original tree's regular forks, low-detail canyon meshes and flat raised garden
still differ from the frozen concept. No claim is made that those silhouettes or
the wider Phase 6 visual acceptance have been solved by this atmosphere pass.
