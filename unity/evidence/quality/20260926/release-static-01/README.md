# Release build 01: static native render check

**Passed the bounded static render check.** Three PID-owned XGetImage captures show the district, actors and full HUD at a measured 1920×1080 drawable size. The first and final images were inspected visually: they contain the game scene, with no black viewport or missing/pink shader output. Different actor positions across captures establish that these are distinct observations; they do not qualify animation quality or frame pacing.

The player used direct **NVIDIA GeForce RTX 3060 / OpenGL 4.5.0 / NVIDIA 610.57.04** on the ordinary display. It was not the failed Zink or llvmpipe profile. The desktop remained locked. Only the newly launched process's compositor client was floated/resized; X11 reads targeted that exact PID's window. No focus request, input, desktop capture or lock interaction occurred.

The release received `--athen-qa` and `--athen-qa-background` with a fresh mailbox containing a harmless settings-snapshot request. It produced no acknowledgment, snapshot or other QA output. Fresh XDG preference directories isolated this run from the player's saved settings. No profile counters were available through the intentionally disabled release bridge; the observed drawable resolution is verified, while the fresh release quality defaults are a source-based description, not a runtime settings snapshot.

The run lasted 31.95 seconds. No exception, assertion, shader or allocation-failure markers were found in the Player log. PID 1100419 was terminated after capture with SIGTERM and exited cleanly with code 0; it is no longer running. The parent received the process/GPU handoff before launching development build 04.

Build identity, scoped launch variables, exact owned-window operations, capture geometry and pixel statistics are retained in `launch.json`, `report.json`, `owned-client-before.json`, `owned-window-dispatches.json` and the three capture records. The release runtime assembly hash is `6d9437c43555cbeef94dad06d6d666bfd7c64b99abf75a467bf27bbd7dd6c6d6`.

This result verifies static release rendering and the negative QA-listener check. It does **not** pass real-input controls, the city loop, traversal, performance qualification or the AAA art target. The coarse paving response visible in these frames remains the subject of the separate ground-material audit.
