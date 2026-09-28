# t_6c931016 — status at 16:20 BST, 27 Sep 2026 (PARTIAL, not accepted)

Work lives only in the isolated snapshot `/home/teknetik/code/.snap/ao2-t_6c931016` (btrfs reflink of the dirty
shared checkout, 15:15). The shared checkout `/home/teknetik/code/ao2` is untouched. Baseline:
`/home/teknetik/code/.snap/ao2-t_6c931016-baseline`. Nothing is committed.

## Done (in the snapshot)
- Request #6: procedural first-person hands `PlayerFPHands_v2` (Blender, ~26k tris). Source, script and checks are in
  `art/character_feel_20260927/fp_arms/`. They are attached under the view-model pistol by
  `Assets/AthenHill/Editor/FPGripPass.cs`, and the old arms are kept disabled for rollback.
- Editor renders before and after (hip, ADS, recoil, sway, draw, sun behind): `fp-grip/editor-before`,
  `fp-grip/editor-after` (after re-rendered 16:11).
- Edit Mode tests: 66/66 passed (`editmode-results.xml`, 15:50).
- Requests #1–5 are read back from the saved scene into `requests-1-5-verify.json` (16:11). Run playback is 1.457
  (6 m/s), the truck is uniform 0.65 (8.2 × 3.39 × 5.56 m bounds), the default hour is 17.0 with the sun at 11°, and
  road trees are moved. Ossa's feet are 6 mm above ground, but Rell's are still about 56 mm above ground (floating).

## Not done
- Linux Development/Release builds were not produced. Three attempts died:
  1. 15:55: systemd-oomd killed the whole run-4676 worker scope, including the Claude lane and Unity, because
     app.slice memory pressure was 67% (over the 50% limit).
  2. 15:58: an AssetImportWorker SIGBUS in a UDS/DataStore read hung the batch; it was killed.
  3. 16:12: Unity was SIGKILLed (rc 137) during `LinuxBuild.Development()` under critical memory pressure.
- Native checks (`check_character_feel.py`, `check_checkpoint.py`, `check_depot.py`), native captures, video and
  timings: not run.
- No playability claim. The Editor renders are not native evidence.

  4. 16:14–16:20: an automatic re-run got through Install, Render and the #1–5 verify, then aborted (rc 134) in
     `LinuxBuild.Development()`. The error was "Fatal Error! The file 'VirtualArtifacts/Primary/63125dc308dbedef0954bac5f808720b'
     is corrupted" in the snapshot's `Library/DataStore`, which is fallout from the SIGBUS and kill. Log:
     `/tmp/fpw/logs/r2/build.log`.

## Root cause and what is needed
- The host has 31 GB RAM with about 3 GB available and 30 GB of swap in use.
- `/dev/shm` holds orphaned Unity DataStore segments, which live in RAM: `udsMemb8ce5b…` (5.7 GB, from 14:10, which
  looks like the shared checkout's closed Editor) and `udsMem0a903c…` (about 4.9 GB, from the snapshot runs).
- The agent cannot delete them in this unattended mode. An operator should remove both (and their `sem.` companions)
  with no Unity running, and ideally free more RAM, before the build is rerun: `bash /tmp/fpw/run_final.sh`.
  `/dev/shm` is a 16 GB tmpfs, and a new Editor maps a further 16 GB sparse segment, so running out of tmpfs space is
  the likely cause of the SIGBUS.
- The snapshot DataStore then needs repair. Either move `unity/AthenHill/Library` aside and reflink-copy the Library
  from `ao2-t_6c931016-baseline` (a consistent pre-lane state; Unity then re-imports only the changed assets), or
  remove the corrupted artefact as Unity instructs.
- Prefer launching Unity in its own scope (`systemd-run --user --scope`) so oomd cannot take the worker down with it.

## Remaining visual defects (#6, from the Editor renders)
- ADS reads as a two-hand wrap, but it is a smooth, low-detail "rubber glove" form. The fingers are merged and have
  no knuckle, nail or seam detail.
- The gloves are very dark in dusk shade.
- The support thumb crosses the back of the firing hand in a thick tube, which is not the photo's thumbs-forward
  along-the-frame pose.
- The hip view shows mostly a sleeve and wrist block.
- It is not yet at the photo reference; treat it as an improvement over the faceted v1 only.
