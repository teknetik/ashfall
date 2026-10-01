# Training range workstream — progress (restart 1 Oct 2026)

Resume notes for a restart. Newest at the bottom.

## Inherited from the 30 Sep run (killed 23:56 by the OOM)
- survey.json (Unity survey step, 23:31 30 Sep), plot_survey.py, ground.py (ground sampler + range frame), glb_bounds.py
- fetch_polyhaven.py + polyhaven/ (8 CC0 models, 2 wood textures) — downloaded
- layout.py + layout.json (firing bays, range officer, machine lane, service apron, backstop, decals, lights, cameras)
- author_range.py → Art/TrainingRange/Structures/*.glb (all 19 kit pieces exported, unreviewed)
- Editor/TrainingRangePass.cs (survey step only)
- evidence: native-before-existing/ (lookbook 13:00 / 20:30 of the current range) = the BEFORE set

## 1 Oct (restart)
- [x] re-survey current scene (07:08; identical to 30 Sep apart from ordering) — survey-20260930.json kept
- [x] review authored kit (review_kit.py → review/kit/*.png, kit-sheet-a/b.jpg). Fixed: floating top rest bag
- [x] layout.py fixes: tyres lay flat on the ground (were 0.22 m in the air), revetment toe moved onto the range floor
      (30 Sep line climbed the mound → stepped wall top) with a smoothed level base, scatter retirement by
      parent+name+centre (30 Sep prefixes would have retired every rock in the outpost), stones kept off fire lanes only,
      y modes recorded for Unity, distance posts / spent-cell bin / waiting bench added, earth-bank toe for Unity
- [x] make_textures.py (timber x3, sand, range orders, machine lane sign, lane/distance numbers, painted numbers, decals)
- [x] prepare_ph_props.py (8 Poly Haven props) + prepare_prop_textures.py
- [x] author_range.py re-run for TR_ShootingBench, TR_DistanceMarker_1-3, TR_Revetment
- [x] TrainingRangePass.cs (survey, build, toggle, batch) + TrainingRangeInstall.cs (install, berm, retire, decals,
      lights, cameras, verify, capture) written
- [x] robot display prefabs (TR_TrainingDrone from the live drone's split meshes; TR_WorkerDroidShell baked idle pose)
- [x] native BEFORE set with the new review cameras (07:40): evidence native-before/, native-before-close/
- [x] install1 → install4 (reinstall iterations, editor captures editor-review/install1..4): lane boards lowered,
      bench items off the tool board, charge rings cyan (TR_ChargeGlow), firing line moved in front of the benches,
      painted lane numbers on the sleeper face at bay centres, varied berm crest, spill cones at the wall ends
      (no vertical cut faces), goal-post droid frame with chains to the shoulders, decal orientation fixed,
      sand-cart run + spill decals, after-only cameras cam_range_lane_start / cam_range_bench
- [x] native AFTER set 1 (08:0x, scene = install4): evidence native-after1/, native-after1-close/. Findings: floods too
      weak at 20:30, sleepers too black in shade, 91 shadow casters, revetment LOD switching close
- [x] install5 (08:20): field lantern on the officer's table (TR_Lantern, TR_LampGlow on the light clock), floods
      70/45, lighter creosote, revetment more grey timber, no shadows from hand-sized/flat props (35 renderers),
      revetment LOD1 at 0.45 screen height. Verify clean (0 missing materials, shotsBlocked [], chunks match).
- 08:35 MACHINE FROZE (not this job: Unity jobs swapping). Reset. Scene saved 08:30:15 still holds install5
  (lantern + earth bank present). /tmp wiped: helper scripts now in run/ (after.sh, ab.sh, tutorial.sh) using
  $O=/home/teknetik/.local/state/ward-programme. Keep Unity runs to one step each (memory).
- 08:50 verify after reset: clean (install5 in scene, 62 shadow casters, 0 missing materials, chunks match)
- 08:50 dev build killed (137) at 13G+2G (everyone's were); coordinator raised build cap to 17G+3G; retry OK 08:56
- [x] native AFTER set 2 on install5 (08:58): native-after2/, native-after2-close/. Wide 13:00 218.5 fps (before 243.7),
      20:30 214.1 (235.7); close 312.7 (285.8). Night floods now read. Defect: cam_range_lane_start sat inside the
      searsia shrub (blue leaf backfaces) → camera moved to (1.3, 8.2) (layout.py; cameras step 09:0x)
- [x] cameras step 09:05 (lane-start camera moved, saved)
- 09:09 ab1-off build killed by the watchdog VRAM guard (graphics-mode builds reach 11.8 GB VRAM); build_player.sh is
  now -nographics. ab1-on measured (09:22-09:25, own build): wide 13:00 269.0 fps, 20:30 213.0; close 341.2.
  Run-to-run drift is large (after2 = same state: 218.5 / 214.1 / 312.7), so A/B is redone alternating.
- [x] run/ab2.sh (09:31-10:0x; API limit paused me until 11:40): builds tr-ab-off / tr-ab-on, scene ends ON (checked
      11:41: root m_IsActive 1). Results (mean frame ms, on vs off): wide 13:00 3.71 vs 3.02 (+0.69); wide 20:30
      4.67 vs 3.90 (+0.77); close 13:00 r2 3.14 vs 2.42 (+0.73) (r1 on-close killed by the VRAM watchdog; r1 off-close
      4.10 is a drift outlier). setPass wide +52, tris +0.91 M.
- [x] city-view A/B (run/ab_city.sh, 11:45-11:55, same two builds, alternating): cam_hill 15.94/15.30 on vs
      15.05/15.19 off with identical tris (11.40 M) and SetPass (321) → the range draws nothing there; the difference is
      run drift. cam_westgate_mouth 4.57/4.48 vs 4.35/4.35 (+0.17 ms, +330 k tris, +17 SetPass).
      Builds/tr-ab-on|off (11 GB each, git-ignored) left for the orchestrator to remove.
- NEW RULES: -nographics on every non-rendering Unity step; editor captures ≤ 6 cameras per Unity run (my capture step
  does 14 → split if used again; native lookbook is the evidence of record).
- [x] final build 12:01 → tutorial check PASSED 10/10 (native-tutorial/report.json, 0 exceptions) → CITY LOOP PASS
- [x] evidence README (what/numbers/A-B table/checks/pairs/defects), compare/ pairs
- [x] art README, DOCS_SNIPPET updated; final report sent (12:1x). DONE — scene ends with the range ON.
