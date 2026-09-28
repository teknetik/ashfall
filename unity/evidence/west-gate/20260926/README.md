# West Gate exit and Warden outpost — 26/27 September 2026

User request: tidy the exit from Ward to the Outer Berms and bring the Warden outpost up from "amateur" toward AAA.
Sources, scripts and provenance: `art/west_gate_20260926/README.md`. Editor pass: `Editor/WestGateOutpostPass.cs`
(Athen Hill → Outer Berms → West Gate: build assets / install outpost / upgrade wreck gantry).

## Result

- Gate: armoured concrete piers, knee-braced lintel with WEST GATE / WARD signs, gantry, floodlights, beacon, banners,
  parked sliding gate on its rail, concrete ramp apron. The inside wreck gantry is now textured riveted I-sections.
- Warden post: converted container with issue window, canopy, arms locker, roof kit, generator/fuel; boom barrier,
  scanned jersey barriers, sandbag nest, briefing board with map/notice/roster; range bench, signs, flag, light tower.
- Ground: layered scanned PBR shader with splat (track, ruts, drifts, trodden areas), rock scatter, shrubs, decals.
- Wardens Ossa/Rell: non-emissive field-khaki armour variant (city guards unchanged).
- Gameplay kept: same interaction roots/IDs/tutorial wiring; Ossa, Rell, locker, board, range control, respawn and
  landmarks moved per `art/west_gate_20260926/layout.json`; dialogue/objective text updated to the new layout.
- Replaced visuals are inactive in the scene (booth, barriers, TextMesh signs, crate locker, service-road strip,
  original wreck boxes). `scene-before-west-gate.unity` and `BermsGround-before-pad.asset` are the rollback copies;
  `install.json` / `wreck-gantry.json` list every retired and moved object.

## Verification

- `edit-mode-tests.json`: 57/57 passed, including the updated saved-checkpoint test and a new test that each
  checkpoint landmark resolves to its intended interaction under GameSession's NPC-first rules.
- `development-build.json`, `release-build.json`: both Linux players built, 0 errors.
- `native/report.json`: all 10 real-input checks passed on the final development build (gate walk, both Warden
  dialogues, briefing board, first-person zoom, locker issue, range reset, three plates with real pistol input,
  holster on return, full city dialogue/trade/travel/modal regression). No runtime exceptions in Player.log.
- `performance-review.json`: same warmed 20.25 s checkpoint route as the previous pass: 230.4 FPS average,
  p99 16.50 ms, max 17.6 ms, no hitches (1920×1080, uncapped, RTX 3060, OpenGL, Editor closed). Narrow pass of the
  16.67 ms p99 target. `native-pre-perf-fix/` keeps the earlier failing sample (166.8 FPS, p99 17.06 ms, one 99 ms
  hitch) before the night-only light / dim-shadow / shrub LOD fixes; it is retained, not replaced.
- Earlier native attempts are kept: `native-attempt1..2` (VRAM contention with the open Editor: commands not
  acknowledged), `native-attempt3` (transient GL context failure), `native-attempt4` and `probe-gate-walk*` (a key left
  held on the X session by an aborted XTEST run; `check_checkpoint.py` now releases movement keys before driving input).
- `visual-review.json`: local before/after scores and remaining defects. `editor-review/` holds Editor captures
  (before-* are the pre-pass state); native captures in `native/` are the authoritative in-game views.

Not done: whole-district performance qualification, a release-build play session by the user, and animation work on
the Warden model. The release player was built but not left running (it holds ~8 GB VRAM).
