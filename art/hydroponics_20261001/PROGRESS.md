# Hydroponics greenhouses — progress (restart 1 Oct 2026)

Resume notes for a restart. Newest at the bottom. Wrappers: `$O` = scratchpad/overnight (unity.sh, blender.sh, native.sh,
build_player.sh, heavy.sh).

## Inherited from the 30 Sep run (killed 23:56 by the OOM), treated as an unverified draft
- inspect_retrofit.py + review/retrofit-hydro-parts.json: retrofit "Hydroponics bays" parts (Detail = 93k tris of tray
  succulents + 3 planters + tank bands; Glow = 8 pink LED slabs; Structure = ribs, skin, trays, doors, tanks, pump)
- fetch_polyhaven.py + polyhaven/ (leaf scans, hose reel, trowel, spade, boots, hat; planks, soil, wood chip, concrete)
- make_textures.py -> textures/HY_CropAtlas(+_Normal).png, crop_atlas.json, HY_PVC, HY_ShadeCloth, HY_SkinFilm
- hykit.py (Geo helpers, leaves, crops, vines), author_hydroponics.py (fit-out + 12 crop sections, LOD0/1/2),
  hyprops.py (yard props, never run), review_hydroponics.py (Cycles review with a stand-in quonset)
- Interior GLBs exported (Art/Hydroponics/Interior, hy-manifest.json): 309k LOD0 tris in 12 sections + 2 fit-outs
- evidence: audit-before.json, native-before-existing/ (lookbook 13:00/20:30, cam_retrofit_hydro, cam_sd_hydroponics,
  cam_hill, cam_whompah) = the BEFORE set

## 1 Oct (restart, from 07:05)
- [x] Unity probe: the skin (Retro_Polycarbonate, glTFast transparent, double-sided) HAS a shadow pass and the
      Structure renderer casts -> the interior sits in full shadow. Fix: HY_Polycarbonate copy without ShadowCaster.
- [ ] review interior renders critically; fix defects (fruit, vines, rockwool, LED bars)
- [ ] build yard props (hyprops) + review renders
- [ ] layout.py for the yard (validated like street dressing) -> layout.json
- [ ] HydroponicsPass.cs: build assets, install (one time, rollback copy), verify, capture, toggle
- [ ] editor captures -> fix -> build player -> native lookbook 13:00/20:30
- [ ] A/B profile wide + close; city loop
- [ ] READMEs, DOCS_SNIPPET

## Log
- 07:10 props rebuilt (fills for the street kit's yellow crate / wicker basket instead of primitive crates; new PH
  scans: nutrient jug, dosing trolley, step ladder, onion); hose reel on a timber post
- 07:30 prepare_textures.py (Textures/ + materials.json), layout.py (52 placements, 0 problems, review/layout-map.png)
- 07:35 HydroponicsPass.cs written; Unity build OK (0 unmapped materials), review cameras cam_hy_* saved in the scene,
  editor-before/ captured
- 07:40 interior: tomatoes denser (leaves from 30 % height, spiral), fruit LOD0 smoother (80 tris), truss stalks
  thicker; LED bars split: HY_LED (crop tiers, on the light clock) / HY_LEDProp (propagation tiers, always on)
- next: player build (before) -> native before lookbook; Unity build+install+verify+capture -> iterate
- 08:05 first install (editor-after1): interior reads lush through the skin; skin film too milky -> lighter film
  (alpha 0.12-0.42, fewer runs), denser shade cloth, trays off the floating shelf, herb pots by the A door (editor-after2)
- 08:25 handcart loaded for market (bed floor 0.53 m measured); A/B chain started: reinstall+capture (editor-off1 holds
  the ON captures), toggle off, build, native off (wide+all cams 13/20.5, skin_close, cam_hill)
- next: review night; toggle on, build, native on; city loop; README/DOCS_SNIPPET with numbers

## 1 Oct 08:35 machine freeze -> resumed ~08:50 (programme folder now $O=/home/teknetik/.local/state/ward-programme)
- State found: A/B off phase complete (native-off1: cam_hy_wide 85.0 fps @13h / 75.3 @20.5h, skin_close 322.6,
  cam_hill 60.3); toggle:on saved 08:19; the on build finished 08:26 but its native run never started. The scene was
  saved again at 08:30:15 by another workstream (walls), so the off/on builds are not a clean pair -> redo the A/B as
  alternating runs on the current scene: on (now) -> off -> on.
- Saved scene: Ward hydroponics active, HY_Polycarbonate override present (pass ON).
- Helper scripts moved from /tmp into tools/ (pair.py, chain_ab.sh).
- 08:48 on2 build killed (rc 137: anon 11.1 GB + swap 2 GB at the 13G+2G cap, 48 s in). verify+toggle:on itself OK
  (anon 10.1 GB, swap 2 GB peak). Retrying the build once.
- 08:51 retry also killed (same cap); orchestrator raised Unity/build caps to 17G+3G -> rerunning on2 (build + native only)
- 09:10 native on2 reviewed (native-on2/): day reads lush through the skin; night: pink glow subtle, moon/sun specular
  hotspots on the glossy skin. Close view cost vs off1 ~+1.6 ms (not a clean pair). Fixes: crop shadows now from LOD1
  only (shadow-only proxy at LOD0), grow glow 2.2/7 m, HY_LED 4.0, skin smoothness 0.72; captures capped (6 views, no
  MSAA), non-rendering Unity steps -nographics. Next: tools/final_ab.sh (prep -> off3 -> on3 -> city loop).
- 09:11 final prep done (build assets with LOD1 shadow proxies, reinstall, verify: 14 sections, 58 yard instances,
  0 missing materials, 12 shadow proxies, chunk fingerprint OK, toggle off). off3 build 09:16 OK.
- NOTE: the three workstreams share one player build folder; the training-range build (09:18) and the walls in-process
  build (09:21) ran between my off3 build and its native run, so the native run uses the newest build. Provenance of
  each native run is taken from $O/jobs.log (the hydroponics state of the saved scene at that build time is what counts).
- 09:30 HydroponicsPass abbuild:on/off (snapshot A/B into Builds/hy-ab-on|off, like PerimeterWallsPass) + tools/snapshot_ab.sh; to run after the final_ab chain's on3 + city loop
- 09:40 on3 (pass on, saved scene) + CITY LOOP PASS (evidence cityloop-native/). off3 vs on3 (same city state: cam_hill
  tris 11,403,897 vs 11,404,036): cam_hy_wide 13h 10.49 -> 11.47 ms (+0.98), 20.5h 12.00 -> 12.77 (+0.77), skin_close
  2.75 -> 4.59 (+1.84), cam_hill 14.56 -> 14.90 (+0.34). Wide-view cost above the ~0.5 ms target -> optimise: crop
  shadows only at LOD0 range (proxy), none at LOD1; fit-out LOD1 no shadows; then snapshot A/B with arms on/off/noyard.
- 09:52 snapshot A/B builds OK (Builds/hy-ab-on 142 s, hy-ab-off 99 s; crops cast no shadows at LOD1, LOD0 via proxy;
  fit-out LOD1 no shadows). Alternating native profiles running (logs/snapshot_ab.out).
- skin follow-up (applied at the next "build"): no direct specular highlights (moon/sun hotspot), smoothness 0.85,
  correct URP blend setup (srcBlend SrcAlpha, no premultiply). materials.json updated in place.

## 11:41 resumed after the API session limit (stopped ~10:12)
- Snapshot A/B COMPLETE (logs/snapshot_ab.out; native-ab1-on/off/noyard, native-ab2-on/off, each with -close/-hill):
  cam_hy_wide 13h on 87.6/88.5 fps vs off 94.9/93.3 (+0.73 ms); 20.5h on 75.9/76.9 vs off 81.8/83.3 (+0.98 ms);
  skin_close on 222.7/221.9 vs off 353.5/365.2 (+1.72 ms at ~220 fps); cam_hill on 67.5/67.8 vs off 68.0/68.6 (+0.14 ms).
  noyard arm: the yard is ~0.5 ms of the wide-view cost, interior+skin ~0.2-0.4 ms.
- Next: skin follow-up (build assets -> player build -> final native lookbook 13/20.5 incl. cam_hill) -> city loop ->
  READMEs, DOCS_SNIPPET, report.
- 11:52 skin follow-up done (no direct specular, smoothness 0.85): build assets + verify OK, development build OK,
  native lookbook of record native-after/ (13:00, 20:30, 13 cams incl. cam_hill), CITY LOOP PASS (cityloop-final/).
  Moon hotspot gone at night. Before/after sheets review/final-pairs-{day,night,hill}.jpg.
- 11:58 READMEs (art + evidence) and DOCS_SNIPPET updated with numbers and remaining defects. Saved scene: pass ON.
## DONE (1 Oct ~12:00). Possible follow-ups: yard cost (~0.5 ms at the wide yard view), enterable bays, crop LOD fades.
