# Character progression native evidence, 1 October 2026

## Scope and identity

- Isolated checkout: `codex/character-progression`, based on `3ebd801b`.
  The environment checkout and saved scene were not edited or merged.
- Unity 6000.6.0f1, native Linux x86-64 development player, OpenGL Core.
- Full Edit Mode run after removing diagnostics: 195 passed, 0 failed
  (`editmode-results.xml`).
- Linux development build: succeeded, 0 errors, 352 warnings, 106.6 seconds;
  build report is `linux-build.json`.

## Real-input check

`unity/tools/check_character_progression.py` launches the saved-scene player
with a private QA save directory. The passing clean-build run is `native-clean/`:

- A rifle drop was rejected with `Requires Rifle 20.` and left the item carried.
- A head implant was installed, Rifle trained once, then the rifle was equipped.
- Field boots dropped on Primary were rejected without changing inventory.
- The inventory was captured at 1920x1080 and 1280x720; Continue restored the
  primary rifle, head implant and the same carry/pack capacity values.
- `native-clean/report.json` records the checks; its player log had no errors.

Earlier local runs remain in this worktree for diagnosis. Some stopped on
test-harness focus, clipping or element-name errors; the actual rifle
requirement rejection was intentional gameplay. None is treated as passing
evidence.

## Limits

- This pass does not replace world art, character models or the held pistol mesh.
- Weapon modifications are associated with a weapon definition, not an item
  instance; two copies of one weapon cannot have independent fitted sets yet.
- No new warmed traversal performance qualification was run for this systems
  pass. The development build alone does not establish the 60 FPS target.
