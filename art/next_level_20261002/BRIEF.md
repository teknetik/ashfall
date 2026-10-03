# Ward "next level" programme, 2 October 2026 — shared brief for every agent

Read `AGENTS.md` first (production rules, machine limits, batched verification). This file adds the programme rules.
Carl's request (verbatim, 2 Oct 15:50):

> swap out the main character for char_main_OK. NOK is to be used later but put that asset in the right place for now.
> some new music add it to the original but make this the default track as I am sick of hearing the old one now lol.
> The rifle is backwards I just watched my character shoot himself 100 times and live :D
> Also 3 more enemy droids for the outer berms. scatter a few more places, POI and encounter, loot crates and rewards.
> There are higher level droids and once the player finds these comfortable to take on its a sign they should progress
> to the next area. they would need good weapons not starter guns and a full set of basic Armour. the life bar
> indicator above the enemies should be grey (easy no xp) green (normal xp) red (danger - high xp) this is relative to
> the player level and stats IE damage with current weapons equipped. make sure the suitable mechanics exist for this
> game play. I dont like the noise it makes when you buy or sell, it sounds like a bell or hitting an empty can. should
> be quiet but digital, *click*. The feral gunners seem to be attached to the other droids? Each weapon needs to have an
> appropriate range, pistol for example has far to much range. Accuracy should depend both on weapon stats and player
> stats. also adding a new model for the salvage npc.

Delivered files are staged in `meshy/incoming-20261002/` (copied from ~/Downloads; keep the originals):
`main_char_OK.glb` (unrigged, 595k triangles, 1.9 m), `main_char_NOK.glb` (unrigged, 11.9k triangles, same shape),
`Meshy_AI_Ironclad_Warden_biped/*_Walking|Running_withSkin.glb` (66-joint Mixamo-named rig, 11.4k tris, 1.7 m),
`Meshy_AI_Scrap_Reaper_biped/*` (43-joint rig, 8.6k tris, 1.7 m), `Meshy_AI_Post_Sentinel_1002142607_texture.glb`
(static, 8.6k tris, 1.89 m), `Oasis of Ruins.mp3` (4:00, 48 kHz). No salvage-NPC model was delivered; say so in your
report and do not invent one.

## Machine and job rules (crashes took the machine down three times this week)

- **One Unity job at a time**, always under `flock /home/teknetik/.local/state/ward-programme/unity.lock`, always
  batch mode with `-nographics` unless a step renders. Use the wrapper:
  `~/.local/state/ward-programme/unity.sh <logfile> <Namespace.Class.Method> -nographics -quit` (it takes the lock,
  caps memory, logs to `~/.local/state/ward-programme/jobs.log`). Editor captures (graphics) run the same way without
  `-nographics`, with `DISPLAY=:0 WAYLAND_DISPLAY=wayland-1` exported, at most six cameras per run.
- **Never launch the interactive Editor, never build the player, never run the native player.** The orchestrator runs
  one combined native batch when every agent has delivered. Your verification is: `-nographics` Edit Mode checks or
  tests, and small batch editor captures.
- Blender only through `~/.local/state/ward-programme/blender.sh <script.py>` (clean env, capped). Meshy generation,
  rigging and animation are pre-approved; record every task id, options, credits and outcome in a manifest under your
  folder; the key is `MESHY_API_KEY` in `/home/teknetik/code/ao2/.env` (export it; never print it).
- Keep scripts and run state under the repo (`art/next_level_20261002/<agent>/`) or `~/.local/state`, not `/tmp`.
- Python helpers: `uv run --offline --with <pkgs> python ...`; numpy is available to `python3`. `magick` for sheets.

## Editing rules

- Scene changes only through an **Editor install method** you write (idempotent: re-running replaces your objects and
  keeps everything else), run in batch mode via `unity.sh ... -executeMethod`. It must open
  `Assets/AthenHill/Scenes/AthenHill.unity`, make the change, save the scene and assets, and write a short log file.
  Validate with a `-nographics` check method (installed objects present, prefab links intact, no missing references).
  Keep retired objects inactive, keep GUIDs, routes, NPC points, colliders and the existing gameplay roots.
- Unity data assets are YAML: when text-patching `.asset` files, validate with pyyaml **and** know that Unity's reader
  is stricter (no blank lines between list items, no `: ` inside unquoted strings, a newline before each `  - id:`).
  A broken asset shows only as "Unable to parse file" in the Editor/build log and loads empty.
- Scripts: C# in `Assets/AthenHill/Scripts` (runtime) or `Assets/AthenHill/Editor`. New files need a `.meta`
  (copy a sibling's and give it a fresh `guid: <32 hex>`). Edit only the files your task owns (below); if you must
  touch a shared file, make a minimal, clearly commented change and say so in your report.
- Codex (another assistant) is integrating an inventory redesign in `~/.codex/worktrees/ashfall-inventory/ao2`; it
  will overwrite `CityCatalog.asset`, `Resources/CharacterCatalog.asset`, `CityHud.cs`, `NativeQa.cs`,
  `DevBridgeCommands.cs`, `InventoryView.cs`, `PackPanel.cs`, `CharacterModel.cs`, `CharacterCatalog.cs`,
  `UI/CityHUD.uss|uxml`. Keep changes to those files in **re-runnable patch scripts** (see
  `art/rifle_armour_20261002/apply_data.py` for the pattern) so they can be re-applied after Codex lands.
- Record provenance (Meshy tasks, library clip ids, Blender scripts) and keep previous versions recoverable.

## Deliverables (each agent)

`art/next_level_20261002/<agent>/REPORT.md`: what changed (files, scene objects, data), the Editor methods to re-run,
how to verify (a `unity/tools/check_<pass>.py` real-input check is welcome: follow `unity/tools/check_rifle_quest.py`,
which uses `unity/evidence/gameplay-v2/20260930-reqa2/qa.py`; the orchestrator will run it in the batch), review
cameras added (`cam_<pass>_*` at player height), known defects, credits used. Keep the report honest: what you did
not verify is "not verified".

## Shared contract: enemy difficulty and experience

`Assets/AthenHill/Scripts/Combat/DroidThreat.cs` (owned by the combat agent) sits on every droid prefab:
`level` (int, 1 = the depot workers), `experience` (int, awarded on kill), and the static
`DroidThreat.Tier(FeralDroid droid, PlayerCombat player)` returning `ThreatTier.Easy|Normal|Danger`, computed from the
player's time-to-kill with the equipped weapon versus the droid's time-to-down the player (armour applied). The
enemies agent **adds the component with values** to its prefabs (and to the existing prefabs if asked), the combat
agent **implements the tier rule, the HUD bar tint (grey/green/red) and the XP award** (Easy = 0 XP).
