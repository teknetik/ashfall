# U5 — Linux standalone — 7 September 2026

Technical build and gameplay acceptance passed. Unity 6000.6.0f1 / URP 17.6.0,
Linux x86-64, OpenGL Core; no unresolved build errors. The saved scene was reopened
before the release build. See development-build.json and release-build.json.
Development: 343 MB, 1 collision pre-bake warning. Release: 251 MB, 6 warnings
(upstream MCP assembly-enumeration compatibility and collision pre-bake warning).
Unity currently pre-bakes the imported collider automatically; future engine
versions may require explicitly enabling that importer option.

The native development player at 1920×1080 passed the continuous gate/hill/ring/
Lattice route, then all four NPC dialogues, modal movement blocking, buy/sell,
objective completion, Lattice destinations, Ring offline bark, pause, inventory,
notes, mute, reduced motion and credits. Actual keyboard checks and screenshots
are under native/. Final native startup/player log contained no exceptions.

The release player at 1280×720 windowed was separately launched outside the
Editor. Real E opened Vex dialogue, W moved, Escape paused, native clicks opened
credits and Quit exited the process. The explicit --athen-qa argument produced
no listener/output directory in release. See release/smoke.json and captures.

Performance evidence and limitations are in ../U4/acceptance.md and
native/qualification.json. Native counters sometimes aggregate a missed sample;
one zero sample followed an exact doubled triangle/SetPass count. Raw data is
retained. Independent trace counts avoid substituting Unity's unavailable draw
counter. The trace maximum is 78 draws and 234,938 submitted triangles. GPU timing
and medium-laptop performance remain unqualified; final art likeness is open.

The first blank-frame build is rejected and documented in first-build-failure/.
Its disabled SSAO renderer feature still initialized stripped resources. Removing
the unused feature and postprocess data fixed native rendering. Later clean
builds and actual screenshots, not the initial build-success flag, are evidence.

These builds qualify the original imported PlayerCandidate baseline. The parallel
“Use new Meshy character” task subsequently changes the editable working scene;
that replacement is not covered by this baseline build/performance qualification.
No other task's scene edits were overwritten to restore the baseline.
