# Steady Hands playtest fixes, 22 November 2026

Carl's playtest of `batch-sh-gemini2`. Data half: `apply_data.py` (idempotent, `--check`). Geometry probe without Unity:
`prefab_pose.py`. Build: `unity/AthenHill/Builds/batch-sh-playtest22b`. Nothing is committed.

| Note | Cause | Fix |
|---|---|---|
| Radio sent the player to Brann | `lineComplete` predated the Identify step; Ossa had no marker | Radio and objective say return to Ossa; `ossa` guidance target; her dialogue sends the player to Brann |
| Cell onto the pad, parts onto mats | Needed about 18 mm of the socket after spring lag; letting go cancelled a pull-in | Drop areas over and 7 cm round pad, mats, tray, dish, cradle, bin, holster (`snapSurfaces`); release does not cancel |
| Camera lost | Zoom followed the held part, which follows the pointer, which follows the camera; zoom survived shot changes | Follows the work, held still during a verb; kept in the picture; zoom resets per shot; G / Home resets |
| Spin the vise at all times | Swivel existed only inside two verbs | Drag the vise, or hold V with mouse, wheel, Q or arrows, in any state; G squares it |
| A & E side-step | New | A left, E (or D) right, remembered per shot. Arrows steer and move focus; Q / Shift+Q rotate |
| Tool angles | Blender +Z arrives as Unity +Y; code used tip +Z for every tool; punch lay across the pin | `AssemblyToolPose`: one rule per kind of tool for hover and work; punch in line; side-on shot for pin blows |
| Crack did not count | Read the mark's +Z (up the pistol), so the score hardly changed with yaw and failed when zoomed; counted only sideways motion though the line said circle | Reads the face (+Y); any turning or side-step counts; click works; squares up afterwards |

Found on the way: over-tightening piled up unseen and blocked the step (now one fault and done); opening the vise or a
latch the "wrong" way did nothing (either way works); a handle press with a tool in hand (puts it down); the drill
crank and servo rotor tumbled about +Z (bone +Y, also fixed in `AssemblyKitBuilder`); arrow-key focus was mirrored.

The stand-in bench uses +Z empties, so its tests cannot catch axis faults. `BenchPlaytestTests` plays the installed prefab.

## Verified (evidence `unity/evidence/bench_playtest/20261122`)

- Edit Mode 605/606. The failure is the known `AssemblyBenchTests.APartHeldInPlace...` from the Gemini merge record.
- `check_bench_playtest_native.py` 37/37: every note with XTEST input, plus a copy of Carl's save resuming.
- Whole job: 302/302, Fine 0.927, no faults (`parity`); 289/289 with a frame of each tool in use (`full2`; the captures
  lengthen holds, hence that run's four faults).
- Primer and rifle quest from a new game: 41/41.
- `check_crafting_flow_native.py` 17/18 here and on `batch-sh-gemini2` alike: the script still waits for the
  Fabricator where E now opens the bench job.

## Not verified / open

- Not played by a person; mouse tests were XTEST on :5, not a physical mouse. Keyboard-only job: Edit Mode only.
- No lookbook, city loop or frame-time run on this build.
- The sight check and installer `verify` were not re-run after the shot and prefab edits.
- Decided (Carl, 22 Nov 2026): Esc keeps undoing the step in progress (DESIGN section 9). Not a bug; do not change it.
- The build also holds another session's uncommitted Linn dialogue and no-starting-armour work.

## Builds deleted (Carl, 22 Nov 2026)

`batch-sh-playtest22`, `batch-sh-real12`, `batch-p2-craft13`, `batch-sh-gemini2` and the Codex inventory worktree's
`LinuxDevelopment` were deleted for disk space on Carl's instruction. References to them in older records are history.
Only `batch-sh-playtest22b` (and its reflinked `LinuxDevelopment` twin) remains: there is no committed fallback or A/B
baseline on disk. For a frame-time A/B, build fcf53cae first; `gm_batch.sh ab` still names real12 and will fail.
