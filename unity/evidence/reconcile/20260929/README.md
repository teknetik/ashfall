# Ward crafting + developer-UI reconciliation onto main — 29 September 2026

Task `t_c7c1e1ca` (Ashfall board). Base for all three trees: `0b4496ad`. Unity 6000.6.0f1, URP 17.6.0, OpenGL (unchanged).
No push, deploy, branch deletion, stash, reset --hard or clean was performed. Source worktrees `ao2-crafting` and `ao2-devui` were only read.

## 1. Inventory and ownership (before any change)

| Tree | Branch | Tracked M | D | Untracked | Owner of the work |
| --- | --- | --- | --- | --- | --- |
| `/home/teknetik/code/ao2` | main | 18 (scene, ProjectSettings, AGENTS.md, RenderChunks 82-84, inventory evidence, 2 tools) | 108 (old RenderChunks) | 149 | Basic General counter/sign, Tool Exchange, render-chunk rebuilds, inventory QA evidence, Air+Water source art (`art/quality_20260929`) |
| `/home/teknetik/code/ao2-crafting` | feature/ward-crafting | 18 | 0 | 13 | Crafting slice (fabricator, loot, recipes, tests, evidence) |
| `/home/teknetik/code/ao2-devui` | feature/ward-dev-ui | 20 | 0 | 19 | Dev bridge + Item Lab **and an integrated crafting copy** |

Overlap (paths changed by more than one tree): the only path changed by main **and** either feature tree is
`Scenes/AthenHill.unity`. Crafting and dev-UI share 47 paths; the dev-UI copy of crafting is byte-identical to
the crafting tree for 44 of them (source, prefabs, catalogue, HUD, combat, serialized data, **the scene**). The three
files that differ are the deliberate reconciliations recorded in `integration/20260928/README.md`: `GameSession.cs`,
`ShopModel.cs`, `NativeQa.cs` (dev-UI adds dev hooks/correlated ACKs on top of crafting's changes; verified by diff that the
crafting hunks are all present). `AthenHill.EditModeTests.asmdef` is a dev-UI-only change (Newtonsoft reference).
Crafting-lane evidence (`unity/evidence/crafting/20260928/**`) is not in the dev-UI tree (moved/renamed into
`final-qa` / `integration`); it is kept in commit 1 for provenance. **Conclusion: dev-UI subsumes crafting** (all 144
crafting paths are present with identical or superset content; supersession = dev-UI wins on the 3 code files).

## 2. Snapshots (safe, reversible)

Full working-tree commits built from temporary indexes (real index/working tree untouched), stored as refs:

| Ref | Commit | Tree |
| --- | --- | --- |
| `refs/snapshots/t_c7c1e1ca/main` | `a80d4b56860fe8823aba90b0e2b0c64feb4026ee` | `907983119e79094680636ac332c7b5b20a3ea3fd` |
| `refs/snapshots/t_c7c1e1ca/crafting` | `65ae13279c9c0f695f8617c8c47fa21af66b7cf8` | `b32888c57713b9457a2b5e94b74807a98d3886f3` |
| `refs/snapshots/t_c7c1e1ca/devui` | `3594fa329616bc01683bf416d696182090e0918f` | `0b7962bcbdc8db9954b7c351112d301240e99a9f` |

Refs live in the main repo's object store (the worktrees share it). Also on disk: `/home/teknetik/code/_snapshots_20260929/`
(`*-dirty-files.tgz` tarballs of every modified/untracked file per tree — main 391 MB, 841 files — plus `*-status.txt`).
Deleted RenderChunk files are recoverable from `refs/snapshots/.../main^` (= HEAD) and the tarball's status file.
Library/Builds (gitignored) were not snapshotted; previous player builds were overwritten by this task's builds.

## 3. Conflict analysis and resolution

* **Scene** — the one true overlap. 3-way `git merge-file` (base HEAD, ours main-dirty, theirs dev-UI) produced **one** conflict
  hunk: main's dirty scene inserted `Chunk_25_District_gate…` (render-chunk objects, fileIDs 1028438984–7) at the same anchor
  where dev-UI inserts the `Field fabricator tool cart` PrefabInstance (1027828637/8). They are independent YAML documents
  with different fileIDs; resolution = keep both (main's first). This is a documented, deliberate choice, not an ours/theirs pick.
  Verification: merged − main = exactly the 9 new dev-UI document IDs; nothing from main lost (0 IDs); 0 duplicate IDs; a
  line diff of main→merged equals the base→dev-UI diff (179 added, 1 changed line: Ossa's `lineComplete`). All referenced
  fileIDs (`CitySession` 1607540210, `Outpost` 226721071, `Landmarks` 1851674839, player combat, tutorial) exist in main, and
  the prefab `PH_ToolCart` GUID `1c8fc96a…` is tracked in HEAD.
* **Render chunks** — not touched by crafting/dev-UI; main's `Art/RenderChunks` deletions/renames (Chunk_89–142 → different set)
  and its stored fingerprint were left exactly as main had them. The scene's stored fingerprint still matches (section 5).
* **GUIDs** — 18 incoming `.meta` GUIDs, 0 collide with any different asset in main.
* **Design collisions needing a decision: none** from handoffs/source. Two carry-overs to be aware of: the fabricator sits in
  the West Gate outpost (`Outer Berms/West Gate outpost/Outpost/Field fabricator`); the Air+Water/Basic General/Tool Exchange
  changes are in other parts of the scene and were not modified.
* Files applied: 292 non-scene files (`apply_nonscene.py`): abort-if-main-dirty guard fired 0 times. Post-application, exactly
  293 paths differ from main's pre-integration snapshot, all of them crafting/dev-UI paths (`verify_preserved.py`).

## 4. Verification (against the integrated tree, main working copy)

| Check | Result | Evidence |
| --- | --- | --- |
| Dev-UI Python tests (`unittest discover unity/tools/devui`) | 14/14 pass; `node --check app.js` ok | this README (stdout) |
| Unity EditMode (all assemblies) | **82/82 passed**, 0 failed/skipped | `editmode.xml` |
| Development Linux build | Succeeded, 0 errors, 348 warnings, 119 s | `development-build.json/.log` |
| Release Linux build | Succeeded, 0 errors, 348 warnings, 108 s | `release-build.json/.log` |
| Native real-input crafting (`check_crafting.py`) | **pass** — E pistol, real-fire drone + depot, E fabricator, Enter craft (1 servo/2 alloy/5 residue), Enter fit, recoil 38→31, F shot 1.55° kick, live dev bridge reads 9 items/4 loot/1 craft/fitted grip; 0 runtime errors | `crafting-native/report.json` |
| Native real-keyboard city route (`check_city.py`) | **pass**, `route_exit=0` (West Gate → hill → Ring Gate → west lane → Lattice, dialogue, modal block, Basic General buy/sell, pause/inventory/notes, Ring Gate offline) | `city-native/report.json` |
| Basic General trade route (this tree's Mira route) | **pass**: buy flask −4 cr, sell coil +1 cr, flask +1, scrap −1 | `basic-general-route.out` |
| Tool Exchange frontage traversal + Vex prompt | **pass**, all legs reached | `tool-exchange-route.out` |
| Release bridge denial | **pass**: alive 35 s with `--athen-qa`, no bridge folder, no dev QA log, 0 errors | `release-native/report.json` |
| Scene reopen + chunk fingerprint (`ReconcileVerify.Run`, read-only) | fingerprint stored == recomputed (`SZgKIO2O…`), sources hidden, 138 generated chunk renderers, 725 colliders, all 9 gameplay roots present, fabricator + `CraftingSession` + `checkpoint_fabricator` wired; scene SHA-256 `79e2cf11…3081` unchanged by Unity | `reopen-verify.json` |
| Runtime errors in any Player.log | 0 (`Exception`/`NullReference`) | `*-native/Player.log` |

Attempts recorded, not hidden: `crafting-native-attempt1-stale-readback` (the harness read `dev-state.json` up to 0.5 s after the
fit, so gripSlot was still null — a harness race, not a game defect; I added a ≤4 s poll for that one read in
`check_crafting.py`, original kept as `check_crafting.orig.py`), and `crafting-native-attempt2-respawn-stuck` (player was knocked
down and respawned at the checkpoint mid-fight, the harness's existing "walk back" is timing dependent — a flaky pass/fail of
the pre-existing QA script, no code change; attempt 3 passed). One earlier dev-build attempt exited instantly because the
shell had no `DISPLAY`; it built cleanly when relaunched (`development-build.log` is the successful run).

**Not verified / limits**: no 1920×1080 frame-time (p99) run, no visual-quality review, no shade/night look at the fabricator cart,
Basic General/Tool Exchange visual acceptance is unchanged from their own tasks, no full release-mode gameplay traversal (release
was smoke + denial only), no multi-run flake analysis of the combat step. Build warnings not triaged. ProjectSettings.asset in
main has an incidental Unity define `SENTIS_ANALYTICS_ENABLED` that predates this task (present in the main snapshot); it was left
uncommitted.

## 5. What was committed

Local commits on `main` (parents chain from `0b4496ad`); only crafting/dev-UI/reconcile paths are in them:

1. `Add Ward field-fabricator crafting slice` — the crafting tree delta as snapshotted (144 paths including its evidence; scene = HEAD + crafting objects only).
2. `Add Ward native developer console, Item Lab and dev bridge` — dev-UI delta on top, plus crafting-lane evidence retained.
3. `Record crafting + dev-UI reconciliation` — this folder + `ReconcileVerify.cs`.

**Deliberately not committed** (remain as uncommitted main work, same as before): Basic General counter/sign, Tool Exchange
display, the render-chunk regeneration, main's own scene edits (the committed scene is HEAD + fabricator objects; the working
scene is that plus main's edits), inventory evidence edits, `AGENTS.md`, `ProjectSettings.asset`, `art/quality_20260929`
(Air + Water source), and the various untracked tools/evidence. Working tree contents were not altered by committing.

## 6. Rollback

* Undo the integration commits only (keep all files on disk): `git update-ref refs/heads/main 0b4496adf34d0eb01a6f5050cac1b163989ad923 && git read-tree 0b4496adf34d0eb01a6f5050cac1b163989ad923` (branch and index back to the old HEAD; working tree untouched). The three commits stay reachable via `git reflog`.
* Restore the exact pre-integration main working tree: `git read-tree refs/snapshots/t_c7c1e1ca/main` then check out only the files you need with `git checkout-index`/`git restore --source=refs/snapshots/t_c7c1e1ca/main -- <path>` (the scene pre-merge is `git show refs/snapshots/t_c7c1e1ca/main:unity/AthenHill/Assets/AthenHill/Scenes/AthenHill.unity`), or extract from `_snapshots_20260929/main-dirty-files.tgz`.
* Source worktrees are unchanged and can still be inspected/continued; their snapshots are the `crafting` and `devui` refs.
* The Builds folders were rebuilt (development and release) from the integrated tree; the earlier main players from 15:31 are not recoverable except by rebuilding the snapshot scene.

## 7. Scripts

`snapshot.py`, `overlap.py`, `preflight.py`, `scene_probe.sh`, `resolve_scene.py`, `apply_nonscene.py`, `verify_preserved.py`,
`verify_commits.py`, `make_commits.py` (all under this folder), `check_*.py`, `run_shop_route.sh`.
