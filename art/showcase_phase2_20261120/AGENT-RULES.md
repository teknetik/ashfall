# Showcase phase 2: rules for every agent

These rules bind every agent working on phase 2 (started 19 November 2026, evening; dated 20 November). They sit under
`AGENTS.md` at the repository root, which stays the authority. Read `AGENTS.md` sections 4 to 8 before you start.

Repository: `/home/teknetik/code/ao2`, branch `ward/next-level`, Unity project `unity/AthenHill`
(Unity 6000.6.0f1, URP 17.6, Linux, OpenGL Core). Several agents work in this checkout at the same time.

## Read first

- `AGENTS.md` (sections 4 to 8 at least) and the rows of section 3 that concern your item.
- `art/showcase_20261119/README.md` (phase 1) and the part of `unity/EDITING.md` for your area.
- Notes from earlier sessions in `~/.claude/projects/-home-teknetik-code-ao2/memory/`: `gpu-job-limits.md`,
  `unity-editor-pitfalls.md`, `ward-render-notes.md`, `native-qa-environment.md`, `mpfb-base-body.md`,
  `user-quality-bar.md`. They record what already went wrong on this machine. Treat them as dated facts and check
  them against the code.

## Git and files

- Do not commit, push, stash, reset, check out or switch branches. Carl asks for commits himself.
- Change only what your item needs. Other agents are editing other files right now: do not reformat, move or "tidy"
  files you do not own.
- Shared files are the usual collision points: `CityHud.cs`, `UI/CityHUD.uxml`, `UI/CityHUD.uss`, `NativeQa.cs`,
  `DevBridgeCommands*.cs`, `GameSession.cs`, `CityCatalog.asset`. Avoid them. If you must touch one, make a small
  additive edit and name it in your report.
- No hand-written scene, prefab or `.asset` YAML. Scene and asset changes come from your Editor installer.
- Keep stable identifiers: asset GUIDs and paths, scene object names, dialogue ids, routes, landmark ids, save keys.
  Internal names still say "West Gate" for the +X spawn arches (the player reads "East Gate"); the West Gate the
  player reads is the -X portal into the Berms by the market.
- The C# tree must compile at all times, because a compile error blocks every other agent's Unity job. Write a file
  completely before saving it, then run `python3 unity/tools/compile_check.py` (about 5 s, no Unity needed).
- Never re-run an older installer wholesale (`MainCharacterInstall`, `TutorialSetInstall`, `PlayerFace20261003`
  `install`, `WardWalkerInstall`, `BermsExpanseInstall`, `NightFacadePass`, and so on). Re-runs have silently reverted
  later scene edits. If you need one of their helper methods, call it narrowly from your own pass and check the result.

## One installer per item

- One idempotent Editor class per item under `unity/AthenHill/Assets/AthenHill/Editor/`, with
  `RunBatch --steps ...` and at least the steps `install`, `verify` and `rollback`. `verify` works with `-nographics`
  on the saved scene and writes a `verify.json` (installed, prefab links intact, no missing materials or scripts,
  retired objects inactive, counts). Running `install` twice must give the same scene.
- Keep the previous version recoverable: retire by deactivating, record originals in a json file, never delete source.
- Review cameras named `cam_<pass>_*` at player height (about 1.6 m) under one camera root, as earlier passes do.
- A dated folder under `art/` with a `README.md`: what changed, where to edit it, values, install and rollback
  commands, what was verified and what was not, open defects. Heavy media in `art/` and `meshy/` is git-ignored; only
  `.py`, `.md`, `.sh`, `.txt` and `.json` are versioned there, so anything the game needs must live under
  `unity/AthenHill/Assets`.
- Evidence (logs, captures) goes under `unity/evidence/showcase_phase2/20261120/<your item>/`.

## Machine limits (the machine has crashed three times from this)

The box has 32 GB of RAM and a 12 GB RTX 3060, shared with Carl's desktop, and it is short of memory tonight.
A watchdog (`ward-watchdog`) kills the largest job when swap passes 27 GB or less than 1.2 GB is available.
Never stop it or raise its limits.

- Never start Unity, Blender or the game player directly. Use the wrappers in
  `~/.local/state/ward-programme/showcase-phase2-20261120/` (called `P2` below). Read a wrapper before first use.
  - `P2/seq.sh install NAME Namespace.Class.RunBatch STEPS [extra args]`: one `-nographics` Unity batch run on the
    shared Unity lock, memory-capped, scene copied first (`P2/scenes/before-NAME.unity`). Log:
    `unity/evidence/showcase_phase2/20261120/install-NAME.log`. Name your runs `<item>-<n>`.
  - `P2/seq.sh tests TAG`: the Edit Mode suite (5 to 7 minutes).
  - `P2/blender.sh script.py [-- args]`: headless Blender 5.2, one job at a time across all agents, 6 GB cap.
    `P2/slot.sh command...` puts any other Blender-class command in the same slot (for example the MPFB launcher
    `art/tutorial_set_20261002/blender/blender_mpfb.sh`).
  - Other heavy Python (large texture bakes): `~/.local/state/ward-programme/heavy.sh command...` (4 GB cap).
  - Graphics-mode Unity (Editor captures only, never for installs):
    `DISPLAY=:0 WAYLAND_DISPLAY=wayland-1 ~/.local/state/ward-programme/unity.sh LOG Namespace.Class.RunBatch --steps capture ...`
    At most six cameras per run. It takes several GB of VRAM and waits while Carl's game is running.
- Unity jobs queue behind each other and can wait a long time. So that no call is cut off at the 10 minute tool limit,
  start every Unity job, long Blender job and native job detached, then wait for it:
  `P2/run.sh TAG command args...` then `P2/wait.sh TAG` (blocks up to 9 minutes; exit 99 means still running, call
  it again). One job per call, and do not end your turn while a job of yours is still running: you would be
  handed back and the job left unattended.
- If a job ends with 137 or 143 it was killed (its cap or the watchdog). Look at
  `~/.local/state/ward-programme/watchdog.log` and `jobs.log`. If `pgrep -x Unity` and `pgrep -x Unity.DataStore`
  show nothing, delete `/dev/shm/udsMem*` and `/dev/shm/sem.udsMem*`, then retry once. If it is killed again, stop
  and report: do not keep retrying.
- `P2/gpu_free.sh` says whether Carl is playing and how much memory is left. While he plays, GPU jobs wait. If a GPU
  step has waited 30 minutes, carry on with everything that does not need it; if nothing is left, finish your report
  with the pending steps listed exactly (commands included) instead of polling for hours.
- Keep scripts and state out of `/tmp` (a reboot clears it). Use your `art/` folder.
- After Unity jobs run `git status -- unity/AthenHill/ProjectSettings unity/AthenHill/Packages unity/AthenHill/Assets/Settings`
  and put stray Unity-made changes back (`git checkout -- <file>` on that one file only). Unity is known to empty
  `Assets/Settings/UniversalRenderPipelineGlobalSettings.asset` and to drop a scripting define from `ProjectSettings.asset`.

## Carl may be playing

- Never write to or delete `unity/AthenHill/Builds/batch-playtest1119` or `Builds/batch-showcase-qa`.
- Do not build the player and do not run native checks unless your brief says you may. Verification is batched
  (`AGENTS.md` section 7): you author, install into the saved scene and verify with `-nographics`; the orchestrator
  runs one combined native batch and sends defects back to you. Design your pass so its cost can be measured later:
  one scene root or one switch that turns it off.
- Do not touch Carl's save (`~/.config/unity3d/Free Column/Athen Hill/ward-save.json`) or his desktop windows.

## Credits and outside services

- Keys are in the repository's `.env` (git-ignored). Never print them, never put them in logs, READMEs or reports.
- Meshy has 126 credits in total and they are reserved for the residents item. No other item may spend Meshy credits.
- OpenAI image generation (`OPENAI_API_KEY`, model `gpt-image-2`) may be used for concept sheets and textures.
  ElevenLabs (about 11,000 credits left) is for voiced lines only.
- Use only original, CC0 or properly licensed sources and record provenance in your README.

## Reporting

- Append one line per milestone to `art/showcase_phase2_20261120/PROGRESS.md`:
  `HH:MM <item>: what happened` (installed, verified, blocked, killed job, and so on). Append only.
- Your final message is read by the orchestrator, not by Carl. Lead with the outcome. Then: what is installed in the
  saved scene and the `verify` result; what you looked at with your own eyes and what you did not; your review camera
  names; what the native batch should check for your item; anything in your brief that turned out to be wrong; open
  defects. Say plainly what is unverified. Do not describe something as done unless a saved file or a log shows it.

## Addendum, 19 November 20:27: heavy Unity jobs are held

The watchdog killed eight Unity jobs between 19:50 and 20:19. With several agents working, system swap reaches the
27 GB line whenever a Unity job runs for more than about a minute. Until the orchestrator says otherwise:

- No Edit Mode test runs, no player builds or native runs, no graphics-mode Unity captures. Do not retry killed ones.
- Short `-nographics` installs and `verify` runs (about a minute) are fine, one at a time.
- Finish everything else, then hand back with the pending heavy steps listed as exact commands. The orchestrator
  resumes one agent at a time on a quiet machine for captures, tests, builds and fix rounds.

## Addendum, 20 November 07:45: playtest fix round

Carl's six playtest notes (`PLAYTEST-NOTES.md`) are being fixed by three agents: loadout interface, Linn's voice,
gate barrels. The rules above hold, with these changes:

- The machine is healthy again (about 19 GB available, swap 7 GB). Edit Mode runs, builds and native runs are allowed
  where your brief says so. Check `P2/gpu_free.sh` first; it now tells Carl's own game from test players.
- Graphics-mode Unity (Editor captures) is still not allowed: it does not fit in memory. Review in the player.
- Native runs: `P2/native_check.sh NAME script.py ENV=VALUE...` through `P2/run.sh` and `P2/wait.sh`. The private
  display :5 is up; do not take it down. Builds: `P2/build_to.sh p2-<name>`, only if your brief allows it.
- `Builds/batch-p2-final` and `Builds/batch-playtest1119` are Carl's: never write to them. Every build rewrites
  `Builds/LinuxDevelopment`; that is expected.
- The ward-watchdog is running. Never stop it or raise its limits.
