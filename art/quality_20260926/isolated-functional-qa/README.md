# Prepared isolated functional checks — 26 September 2026

After the root agent's handoff, two llvmpipe attempts and two separate Zink attempts
were run. None qualified the complete functional suites. All four owned players
were stopped; the root still owns the private Xvfb server. See the
[attempt report](../../../unity/evidence/quality/20260926/headless-functional/ATTEMPTS.md).
No additional driver experiments are planned. The private Xvfb display was
prepared separately by the root agent; these scripts neither create a display
nor change the user's desktop, lock, system configuration or installed packages.

The player uses software Mesa/llvmpipe on `:93`, a fresh evidence-local
`XDG_CONFIG_HOME`, and a 1920×1080 window so existing HUD coordinates remain
valid. Rendering uses 50% scale, no shadows, 1× AA, mip limit 2, no post-processing
and a 30 FPS cap. The cap is a workload limit, not a measured result. Sound master
volume is zero in the isolated preferences; the mute flag begins false so the
existing UI toggle test retains its assertion. This does not verify audible mix.

`launch.py` prints its plan by default; `--launch` starts the normal graphics
player (no batch mode), verifies the actual renderer and requested settings, and
records build hashes. It terminates its own player on startup verification failure.
The Xauthority path is passed through the environment; its cookie is never read
or logged. On successful launch the player remains running for the checks. Quit
it through the QA `quit` command after all tests; the root owns the display server.

`run_check.py` uses the existing `settings_test_input.focus` helper because bare
Xvfb has no EWMH window manager. It verifies the process identity and private
display, focuses and positions only that player's window, then runs the existing
check. Assertions and input durations are untouched. The wrapper releases keys
and mouse buttons afterward. Run checks sequentially, never concurrently against
the same command mailbox. Preserve every failure before attempting a repeat.

After handoff, from the repository root, use a new evidence directory:

```sh
uv run --offline --with python-xlib python art/quality_20260926/isolated-functional-qa/launch.py unity/evidence/quality/20260926/headless-functional/software-01 --launch
uv run --offline --with python-xlib python art/quality_20260926/isolated-functional-qa/run_check.py unity/evidence/quality/20260926/headless-functional/software-01 controls
uv run --offline --with python-xlib python art/quality_20260926/isolated-functional-qa/run_check.py unity/evidence/quality/20260926/headless-functional/software-01 city-loop
uv run --offline --with python-xlib python art/quality_20260926/isolated-functional-qa/run_check.py unity/evidence/quality/20260926/headless-functional/software-01 route
```

Controls cover real mouse look/zoom, first person, HUD blocking, jumping and modal
input. City-loop covers four dialogues, trade transactions, travel, objectives,
pause, inventory/notes and toggles; its interaction fixtures use QA teleportation.
The route walks twelve checkpoints after reset using real W-key movement; its
heading is set through the QA camera command. Neither is a wholly manual playthrough.

The original tests contain brief 8–80 ms key events, fixed waits, a 10-second bridge
timeout and 35-second route checkpoint timeout. Software rendering may make those
checks fail or leave sparse motion samples. Record such failures and actual frame
cadence; do not silently lengthen events or weaken assertions and call the result
the original test. Passing functional checks here does not establish hardware
input latency, temporal image quality, 60 FPS performance, audio quality or art
acceptance. Those remain separate native RTX 3060 qualification work.

`launch_zink.py` and `run_check_zink.py` are a separate, explicitly labeled
OpenGL-over-NVIDIA-Vulkan functional experiment. Their latest profile additionally
uses `ZINK_DESCRIPTORS=lazy` and `ZINK_DEBUG=compact`, as described in the
[official Mesa documentation](https://docs.mesa3d.org/drivers/zink.html). The second
attempt produced an image but still logged 7,509 memory-allocation errors, so its
rendering preflight failed and no input suite was run. This experiment never
changed the game's graphics API, saved scene, project settings or default pipeline.

`controls-layout-check.py` fixes a confirmed stale test coordinate by querying the
runtime `slot1` bounds. The original point `(840,960)` is above the current hotbar;
the observed slot1 center is `(661,1020)`. Its 27 assertion ASTs and input timings
match the original controls test. The changed output filename preserves the old
failure evidence. It is staged and has not been executed on a valid renderer.

`adapted-controls.py`, `software_input.py` and `run_adapted.py` are an unexecuted
fallback for frame-aware software input. See `adapted-controls-notes.md` for its
separate physics-trace scope and explicitly untested short-tap timing. They were
not needed for further testing after the decision to stop isolated experiments.
The private Xvfb autorepeat mode was never changed by these staged helpers.
