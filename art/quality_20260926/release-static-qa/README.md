# Release static window check

`run.py` launches only the Linux release build after an explicit `--launch` handoff. It uses fresh XDG config/cache/data directories, direct NVIDIA OpenGL, windowed 1920×1080 launch arguments, and the development QA flags as a negative test. No development listener, scene code or release backdoor is added.

The runner identifies its own process in Hyprland and X11, floats/resizes only that client using the coordinator's verified Lua dispatch syntax, and reads only the PID-owned client drawable through XGetImage. It never requests focus, injects keys/mouse, unlocks the desktop, changes display configuration or captures a desktop/root drawable. A separate bounded capture subprocess prevents an unavailable X11 read from hanging cleanup. The runner terminates only its child and retains all logs, failed attempts, black images and metadata.

The default invocation prints the launch plan without creating output or launching a process. A new output folder is mandatory for actual execution. Typical authorized invocation:

```sh
uv run --with python-xlib --with pillow python art/quality_20260926/release-static-qa/run.py --output unity/evidence/quality/20260926/release-static-01 --launch
```

`complete` means the direct NVIDIA OpenGL release produced at least one non-blank 1920×1080 owned-window capture, ignored the QA mailbox, and had no scanned runtime error markers. Inspect the images visually as well. The check does not exercise input, prove actual quality counters/render scale, qualify performance or establish AAA visual quality.

The current runner uses explicit `relative=false` resizing. The actual first release run used the earlier dispatch text, preserved in its own `runner.py` and operation receipt; its X11 drawable was independently verified at1920×1080 in all three captures. No dimensions from that later syntax change are retroactively assumed.
