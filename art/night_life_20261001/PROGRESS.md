# Night lighting & ambient life — progress (1 Oct 2026)

## Done
- 12:15 started; read brief + BRIEF.md.
- 12:15 audit-before.json + survey.json (-nographics). check_compile.py (offline Roslyn check) before any C# goes into Assets.
- 12:40 layout: night_layout.py + night_layout_fixtures.py -> night-layout.json (0 problems); review/layout-map.png.
- 13:05 terminal emission map (prepare_terminal_emission.py). NightLifePass build,install,verify: 12 fixtures, 15 circuit lights, terminals on MissionTerminal_Lit, 5 effects; rollback scene in evidence/rollback.
- 13:10 editor-1 captures: brackets on masonry; rampart-north bracket landed on the processing-hall ruin -> removed (relayout). Flames -> stretched billboards.
- 13:25 native-off-1/on-1: lamps too weak at 2.6 -> posts 6.0/15 m, brackets 4.0/10 m (avenue lamps are 6.24/18.4). native-on-2 OK. North-collapse camera moved out of the greenhouse.
- 13:45 effects debug (fxstats/fxprobe): flames used a Circle shape (sideways into the barrel wall) -> Cone; barrel smoke too thin/fast; steam/haze denser.

- 14:20 snapshot-3 A/B builds (on 14:03, off 14:07): native-off-3/native-on-3 (42 captures each), A/B ab/3-* (cam_hill, cam_nl_courtyard x2 alternating) -> ab/summary-3.json; dbg-courtyard13-* / dbg-courtyard-late13-* show the courtyard 13:00 spike is a first-view artefact (+0.61 ms after warm-up).
- 14:50 Carl's process change (no more own builds/lookbooks/A-B/city loops). Final: fxmats,lodcuts,rebuildfx,abclean,verify (-nographics) OK -> verify-saved-scene.json (11/11 fixtures linked, 0 missing materials, 14 circuit lights, chunk fingerprint matches). Builds/nl-ab-on/off deleted (22 GB). Evidence README, art README (review cameras), DOCS_SNIPPET written.

## State: DONE pending the orchestrator's combined test
- Installed and ON in the saved scene. Not seen natively yet: the final effects retune (HDR barrel flame material, denser
  smoke/steam/haze), the moved cam_nl_market_fire, the post LOD1->LOD2 cut 0.15.
- City loop and final frame times: pending the orchestrator's combined test.
- If a fix round comes: edit night_layout_fixtures.py -> python3 night_layout.py -> NightLifePass relayout/retune;
  effects -> staging/NightLifePass.cs (check_compile.py first) -> fxmats/rebuildfx. Never re-run "build" after install.
