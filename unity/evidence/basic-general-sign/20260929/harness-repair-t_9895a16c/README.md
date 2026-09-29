# Basic General capture harness repair — t_9895a16c

Board: Ashfall. Offline repair only. Original integration t_196932d9 remains BLOCKED.
No Unity, native player, native smoke, game tests, builds, scene edits or collider edits were performed.

## Diagnosis and scope

Diagnosis t_f7e4e844 established an initial six-stall waypoint failure, followed by worker-driven full-stage retries, a likely read-during-overwrite PNG failure, and separate unexplained player exits. The original launcher discarded player exit status, report writing happened only at the end, and callers used output pipelines that could hide errors. This repair does not establish the collider/input cause of the stall or the cause of historical player exits.

Changed code (relative to /home/teknetik/code/ao2):

- unity/tools/capture_basic_general_sign.py (previously untracked work preserved in rollback): required explicit CLI stage; `smoke --leg left|right`; retained approach, one lane alignment, exactly one selected oblique leg and one noon screenshot; no matrix/profiles/video in smoke; no fallback to `all`. `all` and `approach` now require an explicit video name and window ID.
- unity/tools/launch_phase1_qa.py: import-safe launcher, fresh directory required, incremental launch report, full stdout/stderr logs, supervised `--smoke-leg` mode, exact owned Popen PID cleanup and real child/player return codes. Legacy explicit launch-only mode still detaches; its report says `detached`, not smoke success.
- unity/tools/relaunch_qa.sh (previously untracked): compatibility filename only; now requires NEW directory and `left|right`, execs one supervised launch, never pkill, rotate, retry or pipe to tail.
- unity/tools/test_basic_general_harness.py (new): offline tests only.

New evidence is confined to this directory. `repair.patch` describes the three existing-file changes against their actual pre-repair contents, not HEAD. No commits were made. The shared walking implementation, desktop input helper, scene, RenderChunks, Meshy sign/source files and concurrent Air+Water assets were not edited.

## Behaviour and bounds

- Smoke retains seven APPROACH waypoints, one lane alignment and exactly one existing oblique target: left `(6.2,0,18.8)` OR right `(9.8,0,18.8)`. It does not claim that either target is geometry-approved. Owner must review clearance before authorisation.
- Original six-stall guard is unchanged. Each smoke/retained still-route waypoint keeps 0.3 m horizontal tolerance and 70 s route limit, with an additional hard asynchronous 70 s wrapper. No relaxed assertions or collider movement.
- Bridge command acknowledgement remains bounded by the existing client's 10 s matching-ID wait. Missing/invalid bridge files, non-Play state, incorrect resolution, renderScale other than 1, insufficient actors, focus loss and stalled bridge fail rather than trigger retries.
- Initial advancing-snapshot check: 3 s. Smoke body: 780 s cap. Supervisor: startup bridge 60 s, floating-window helper 15 s, capture child 800 s; polls player every 0.1 s during children. Normal combined supervisor budget is 895 s including up to 20 s for both owned-child cleanup waits (plus scheduling/I/O overhead).
- Every PNG uses a UUID filename, refuses a pre-existing destination, requires complete PNG IEND, Pillow verify and full 1920x1080 decode, then identical bytes on two polls. Decode wait is 18 s after capture acknowledgement; polls 0.15 s. Hash is calculated from the exact decoded bytes, not a later re-read.
- Each run gets a unique `basic-general-sign-smoke-<uuid>.json`; atomic checkpoint before commands/legs and after successful shots/legs. It records current command/leg, acknowledged command, pose/snapshot, exact PID/window/focus, completed captures, and final exception/cancellation. Launch report starts before Popen and is updated throughout.
- Supervisor stops at the first failure. Nonzero helper exit is propagated; player signal -N maps to shell status 128+N and raw status is retained in JSON. Premature player exit 0 is a failure (shell 1). Deadline is 124; operator SIGINT 130, supervisor SIGTERM 143. Intentional player termination after capture is separately labelled so -15 is not presented as a spontaneous crash.
- Cleanup only signals Popen-owned player/helper PIDs; no global process matching or restart. Capture child receives SIGINT to allow its failure checkpoint, then SIGKILL if still alive after 5 s. Player receives SIGTERM then SIGKILL after 5 s. Each final reap wait is 5 s. SIGKILL, host power loss, uninterruptible kernel I/O or an unwritable/full evidence filesystem cannot guarantee a final report; earlier atomic checkpoints remain the available evidence.
- Existing float helper behaviour is retained; it may tolerate a compositor float/resize dispatch failure. Subsequent focus, settings and screenshot dimension assertions still fail the smoke if the required native state is not reached. Compositor/window integration has NOT been tested natively here.

## Exactly one separately authorised smoke — NOT executed

Prerequisites: owner reviews this patch and chooses ONE geometry-reviewed oblique target; confirms no competing QA or desktop automation, correct unchanged development build identity, and a working local desktop. Do not use this as permission to resume integration. No source/asset rebuild is part of this smoke.

From the repo root, after explicit authorisation for LEFT only:

```sh
cd /home/teknetik/code/ao2
OUT="$PWD/unity/evidence/basic-general-sign/20260929/smoke-authorised-$(date -u +%Y%m%dT%H%M%SZ)-$$"
DISPLAY=:0 bash unity/tools/relaunch_qa.sh "$OUT" left
status=$?
printf 'supervised smoke exit=%s evidence=%s\n' "$status" "$OUT"
```

If the owner approves RIGHT instead, replace only the final `left` with `right`; do not run both. No `all`, no `| tail`, no automatic retries. Directory must not already exist; it is not moved or overwritten. This command launches ONCE, captures ONCE, and stops its owned player even on success.

Pass gate: zero supervisor exit; launch-report status passed/complete true; capture report status passed/complete true with all retained approach/alignment entries and selected target reached; exactly one fresh decoded 1920x1080 noon PNG, correct pose/focus/bridge/settings and no new QA/player errors. Review Player.log, player-stdio.log, window-stdio.log and capture-stdio.log. Do not infer visual acceptance from decode success. Any failure stops the investigation at its recorded stage; preserve the folder and do not relaunch. Owner decides whether to resume t_196932d9 separately.

## Offline verification

Commands run:

```sh
uv run --offline --with python-xlib --with pillow python unity/tools/test_basic_general_harness.py
uv run --offline --with ruff ruff check --select E9,F unity/tools/capture_basic_general_sign.py unity/tools/launch_phase1_qa.py unity/tools/test_basic_general_harness.py
bash -n unity/tools/relaunch_qa.sh
python -m py_compile unity/tools/capture_basic_general_sign.py unity/tools/launch_phase1_qa.py unity/tools/test_basic_general_harness.py
git diff --check -- unity/tools/launch_phase1_qa.py
```

Results: 21/21 focused tests PASS (2.437 s in final saved run); selected Ruff checks PASS; Python syntax PASS; bash syntax PASS; scoped whitespace checks PASS on all four code files. `focused-tests.txt` and `validation.txt` are actual tool output. Tests only launch harmless short Python subprocesses (and a fake uv wrapper); no test can invoke the real player through the mocked launch calls. Coverage includes CLI errors, one-shot selection for both choices, stale/partial/corrupt/wrong-size PNGs, report success/failure/cancellation, bridge stagnation, focus loss, key cleanup failure, six-stall behaviour and .3/70 arguments, startup exit/signal/timeout, child timeout/failure, exact wrapper status, fresh-directory refusal, and preservation of an unrelated synthetic process.

The repository-wide `git diff --check` found existing scene trailing whitespace at lines 50121, 110383, 131365 and 174822. That is outside scope and was not changed. This was not hidden as a clean repository-wide check.

`protected-before.json` and `protected-check.json` cover 18,186 pre-existing files under Unity Assets, the sign source and historical sign evidence: all hashes unchanged. This is preservation evidence, not native game validation.

## Historical captures reusable as PARTIAL pre-integration baseline

Root: unity/evidence/basic-general-sign/20260929. Offline Pillow verify/full decode was re-run here: all 50 PNGs valid at 1920x1080. `historical-captures.json` gives every exact path, size and SHA-256; no files were overwritten.

- `before-native.stale-144133`: 15 PNGs. Fixed `cam_audit_basic_general_front`, `cam_audit_basic_general_door`, `cam_audit_basic_general_side_left`, and player `fp_sign_far`, `fp_sign_street`, each at noon/dusk/night. Reusable as one partial 15-image baseline group.
- `before-native.stale-144342`: same 15 view/hour combinations; alternate partial baseline group. Choose one group for comparisons, do not present both as independent route passes.
- `before-native.stale-143929`: 18 PNGs: the same 15 plus `fp_sign_left` at noon/dusk/night. Mixed/overwritten attempts; left used OLD target `(4.6,0,19.6)`, not the current `(6.2,0,18.8)`. Reusable only as labelled historical visuals, not a current-target matched oblique/traversal pass.
- `before-native.stale-144429`: only `cam_audit_basic_general_front-noon.png` and `cam_audit_basic_general_front-dusk.png`; partial duplicate front-view reference, not a full set or proof of successful timeSet/night capture.
- `before-native`, `before-native.stale-144446`, `before-native.stale-144509`: no reusable PNGs.

Missing: completed historical per-shot reports and reliable per-shot pose attribution; current-target oblique route success; right/porch captures; completed MP4; actual status/signal and cause of historical player exits. Integration's matched AFTER views, moving before/after approach, installed sign acceptance, gameplay/trade verification, saved/reopened scene verification and development/release qualification remain outside this repair and unfulfilled by it. A repaired smoke is still not a substitute for those acceptance gates.

## Rollback — only these harness edits

Do not use git reset/clean or restore the scene; capture and relaunch were already untracked local work.

1. Stop if another worker has since edited any of the four code files. Inspect `repair.patch` against the current files first; preserve later changes.
2. From /home/teknetik/code/ao2, restore the exact pre-repair capture/launcher/wrapper copies:

```sh
BACKUP=unity/evidence/basic-general-sign/20260929/harness-repair-t_9895a16c/rollback
cp -p "$BACKUP/unity/tools/capture_basic_general_sign.py" unity/tools/capture_basic_general_sign.py
cp -p "$BACKUP/unity/tools/launch_phase1_qa.py" unity/tools/launch_phase1_qa.py
cp -p "$BACKUP/unity/tools/relaunch_qa.sh" unity/tools/relaunch_qa.sh
```

3. If reverting the repair entirely, archive/remove only the newly added `unity/tools/test_basic_general_harness.py` after verifying no later edits. Keep this repair evidence and all original captures/source assets. Restoring the old wrapper restores unsafe retry behaviour, so it must NOT be run without a fresh review.
