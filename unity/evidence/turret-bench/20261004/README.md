# Turret and bench pass — evidence, 4 October 2026

Pass record: `art/turret_bench_20261004/README.md`. Working tree on `ward/next-level` after 1c232f74, uncommitted changes
of this pass. Unity 6000.6.0f1, batch mode (`-nographics` except the editor captures).

* `install.log`: assets, bastions, benches, cameras, verify (PASS). `cameras2.log`: camera fix and verify again.
* `others.log` / `other-verifies.txt` (summary) and `other-verifies/*.json` (full): WardLife, StreetDressing, Hydroponics and
  TrainingRange verify output. Those steps also write into their own dated evidence folders; the originals there were
  restored from git, so that older evidence is unchanged.
* `editmode.xml` / `editmode.log`: 268/268 passed.
* `editor/cam_tb_*.png`: editor captures, 1920×1080. These are not native evidence.
* `survey*.log`: read-only scene survey (`art/turret_bench_20261004/survey.txt`).

No native build, lookbook, frame-time A/B or real-input check was run for this pass.
