# Private-display functional attempts — 26 September 2026

The native controls, city loop and twelve-checkpoint route remain **unqualified**.
The private Xvfb setup made isolated input possible without touching the locked
desktop, but the software renderer was too slow for the existing test timing and
the hardware-backed Zink experiments failed rendering validation. No 60 FPS,
visual-quality, audio-quality or whole-game acceptance is claimed.

All attempts used the same recorded development build (Runtime DLL SHA-256
`d52781641006b6e8a80aee3b42f542b64c4c83fb74c6ca60b640d3cfdd004f21`),
1920×1080 window and nine actors. The deliberately low functional profile used
render scale 0.5, no shadows, 1× AA, mip limit 2, no post-processing and a 30 FPS
cap. Sound master volume was zero in isolated preferences. Each attempt records
its actual build hashes, renderer, environment, settings and log locally.

| Attempt | Actual renderer | Outcome |
| --- | --- | --- |
| [software-01](software-01/launch.json) | Mesa llvmpipe, OpenGL 4.6 | First settings command exceeded the ordinary 10-second timeout during initial shader/frame startup. No input tests ran. |
| [software-02](software-02/launch.json) | Mesa llvmpipe, OpenGL 4.6 | Explicit startup warmup succeeded after 11.8 seconds. All three original input suites failed with their assertions/timings intact; observed steady frames arrived every 1.8–2.0 seconds. |
| [zink-01](zink-01/renderer-failure.json) | Mesa Zink, OpenGL over NVIDIA RTX 3060 Vulkan 1.4 | Input updates ran, but a captured image was black and 7,679 Mesa memory-allocation errors were recorded. Invalid rendering. |
| [zink-02](zink-02/renderer-preflight.json) | Same Zink path, lazy descriptors and compact descriptor sets | Preflight image contained the scene/HUD, but 7,509 allocation errors remained. No functional tests ran after the failed preflight. Driver experiments stopped. |

The software-02 controls failure was `Unheld mouse moved the camera`, after short
fixed waits could not establish settled camera state. The city loop reached Vex's
dialogue and passed its modal-movement assertion, then expected Dialogue but saw
Play after Return. Slow-frame queueing/key repeat is a possible explanation, not
a proven game regression. The route walked 10.2 metres while grounded, but its
unchanged 35-second timeout expired before the first target 31 metres away.
Original reports and console logs are retained, with no passing replacement claim.

Zink-01 passed the first left-drag/no-right-drag camera assertion, then failed the
HUD-drag assertion. Runtime UI layout proves a separate harness defect: the old
point `(840,960)` lies above the current hotbar. Slot1 bounds were
`[629,988,64,64]`, center `(661,1020)`. The staged coordinate-only test queries the
live bounds instead. Its 27 original assertion ASTs and input durations are
unchanged. This correction has not yet passed on a valid renderer.

The bounded Zink retry used options documented by
[Mesa](https://docs.mesa3d.org/drivers/zink.html): `lazy` changes descriptor binding
strategy, and `compact` uses no more than four descriptor sets. Neither option
promises to fix allocation failures. The game's configured OpenGL API, Unity
pipeline, scene and shipping settings were not changed by these experiments.

[Cleanup evidence](owned-player-cleanup.json) confirms all four owned native
players exited. The root agent retains ownership of the private Xvfb server.
The staged frame-aware fallback was never executed, so its private-server
autorepeat adjustment was never applied. No global packages, desktop settings,
lock-screen state or user preferences were changed by this testing agent.
