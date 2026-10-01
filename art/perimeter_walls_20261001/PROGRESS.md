# Perimeter walls — progress log (restart 1 Oct 2026)

Workstream brief: overnight/prompts/01-perimeter-walls-rebuild.md (scratchpad). Predecessor (30 Sep 22:20–23:56) left a
draft kit (author_perimeter_walls.py, pw_layout.py, review_walls.py), EX GLBs and editor 'before' captures; it was
killed by the 23:56 OOM. Nothing was installed in the scene.

## Done
- 07:2x Read brief, AGENTS, masonry kit, predecessor draft and transcript.
- Native 'before' lookbook started from the 30 Sep 23:50 build (old walls, includes the cam_pw_* review cameras):
  unity/evidence/perimeter-walls/20261001/native-before (13:00, 20:30).
- Fixed an infinite loop in `screen_panel` (last sheet width -> x never advanced; the NS build ate 5.8 GB and was
  killed by hand). Re-running the NS build.

## Next
- Build NS / EX / BW at three LODs, review renders, fix geometry.
- Fresh scene audit (clearances near the wall faces, arch geometry at the District gate).
- Unity pass: build assets (materials, prefabs with LODGroups and shadow proxies), install, verify, captures.
- Native after captures, A/B frame time, city loop, READMEs, DOCS_SNIPPET.

## 1 Oct, 07:30–08:45
- Native 'before' lookbook done (23 cams × 13:00/20:30): unity/evidence/perimeter-walls/20261001/native-before.
- Fresh scene audit (audit-before.json, 07:14). pw_validate.py checks every module footprint (piers, buttresses,
  cones, fallen blocks, repairs, sand) against it: 0 blocking overlaps after re-ordering variants (Berms south:
  impact, collapse, breach, impact...; EX: merlons away from the watchtowers), slimmer EX buttresses (0.68/0.56/0.38 m),
  fallen stones kept close to the city-side feet, siege debris clear of the arch pier and the aquifer seep pipe.
- Kit fixes from review renders: no cantilevered string/sill/merlon stones over breaks (support test ±0.35 m),
  rubble core under the stepped surviving face stones (+skirts), crater bowls cover exactly the knocked-out blocks,
  broken rim blocks (irregular outlines), mortar cores behind stacked through-stones, crack stitches + pattress
  plates (repair), HESCO two deep + second tier + supported sandbag stacking (breach), screens on the BW collapse,
  a north-wall collapse (collapse_n, small inner spill: Quantum Tube pylons 1.3 m off the face).
- LOD3 = shadow-only massing (~100–340 tris/module), inset 9 cm behind every lit face (first editor captures showed
  the walls self-shadowed and far too dark with a coincident caster). Kit (repairs, rubble cones, sand) casts its own.
- Unity pass written (build/install/verify/cameras/capture/toggle). Installed once (install.json, rollback copy
  rollback/before-perimeter-walls.unity). 87 modules, 0 missing materials, chunk fingerprint OK, colliders kept.
- First install had LOD cuts computed from a 1 m default size (all LOD0): fixed; rebuilding prefabs.

## 08:35 machine freeze (reset) and recovery
- The freeze hit during my one-session A/B build job (`abbuild`: toggle off → build pw-ab-off). pw-ab-on had finished;
  the saved scene (08:30:15) was left with the walls root INACTIVE. Recovery job queued: `toggle:on,build,verify`.
- The A/B step no longer toggles the saved scene: `abbuild:on` builds the saved scene, `abbuild:off` builds a temporary
  scene copy with the root off (deleted afterwards), one build per Unity job.
- Programme folder moved to /home/teknetik/.local/state/ward-programme ($O); ab_runs.sh updated. New caps: Unity/build
  13 GB + 2 GB swap, player 10 GB + 1 GB, Blender 6 GB + 1 GB; watchdog in $O/watchdog.log, per-job peaks in $O/jobs.log.
- Kit state at the freeze: GLBs of 08:28 (supported stepped breaks, closed block backs at breaks, no sandbags on the
  NS collapse tops, inset shadow massing, rubble cones on PW_Rubble, sheet patchwork) — validated intact after reboot.
- Native after-1 lookbook (08:20 build, before the last two kit fixes): unity/evidence/perimeter-walls/20261001/native-after-1.

## Next
1. Recovery job → verify walls root active, chunk fingerprint, prefabs rebuilt from the 08:28 GLBs.
2. Editor captures of the story beats; fix anything wrong.
3. abbuild:on, abbuild:off (separate jobs) → ab_runs.sh at cam_hill (wide) and cam_pw_south_lane (close).
4. Native lookbook (final) 13:00/20:30 from pw-ab-on; build_player.sh + native.sh cityloop.
5. Evidence README, DOCS_SNIPPET.md, final report.

## 08:47–09:00
- Recovery job done: walls root back on, prefabs rebuilt from the 08:28 GLBs, verify OK (87 modules, 0 missing
  materials, chunk fingerprint matches, nothing retired active, kept colliders OK). Note: LOD0 2.32M tris summed over all
  87 modules (never all on screen), LOD1 267k, LOD2 107k, shadow massing 8.4k.
- Capture job killed at the old 13 GB cap (orchestrator), retried at 17 GB: editor-after-3 (story beats look right:
  stepped breaks, no floating stones/bags, HESCO breach, sheet patchwork).
- Queued abbuild:on then abbuild:off (separate jobs).

## 09:05–09:20 A/B builds
- abbuild:off (with graphics) killed by the new VRAM watchdog (11.7 GB); temp scene copy removed by hand. All my non-render
  Unity steps now run with -nographics; editor captures ≤ 6 cameras per run.
- First -nographics pair (pw-ab-off 09:08, pw-ab-on 09:12) is NOT usable: another pass toggled its own root off in the
  saved scene at 09:10:57 between my two builds. abbuild now snapshots the saved scene once (on/off copies written by the
  "on" job), the "off" job builds the off copy and deletes both copies. Requeued (abbuild-on3/off3 logs).

## 09:20–09:55 A/B, final lookbook
- Snapshot A/B builds OK (pw-ab-on 09:20, pw-ab-off 09:24, both from one scene snapshot; temp copies deleted).
- ab_runs.sh (alternating, 13:00, 8 s): cam_hill on 68.3 / off 69.5 fps, p50 +0.22 ms; cam_pw_south_lane (walls fill the
  frame) on 153.4 / off 169.9 fps, p50 +0.60 ms. cam_gate off-arm runs were killed by the VRAM watchdog (11.85 GB with the
  desktop; a training-range run was killed alongside) — dropped, the wide + close pair is the record (ab/summary.json).
- Final native lookbook from pw-ab-on: native-after (29 cams, 13:00/20:30). Night views read darker than the old pale
  boxes (the masonry matches the hall's; moonlight is the night-lighting stream's).
- Queued: build_player.sh (final LinuxDevelopment) → native.sh cityloop → evidence/perimeter-walls/20261001/cityloop.

## 10:00–11:43 wrap-up
- Final build 09:59 (rc 0) → native.sh cityloop 10:03: CITY LOOP PASS (evidence cityloop/).
- Session limit 10:12–11:40. Resumed: final verify (11:42, -nographics) OK; evidence README, compare/story-beat sheets,
  DOCS_SNIPPET.md written. Workstream complete pending Carl's review.
