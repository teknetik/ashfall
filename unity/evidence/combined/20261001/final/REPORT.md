# Ward visual programme — final report, 1 October 2026

Carl's overnight brief was walls that look too clean, bare greenhouses, a weak training-robot area, and the art-direction
review's "next wins". The programme was restarted on 1 Oct after the 30 Sep out-of-memory kill and ran in three
batches under batched verification (AGENTS.md §7) and the new machine limits (§8). Codex's character progression
branch is merged on top. Nothing here is accepted by Carl yet; every pass keeps a rollback copy and its old visuals
inactive.

## What is in the build

Commits on `ward/next-level`: `66a0668b` (environment programme), `9062b001` (merge of `codex/character-progression`,
`b15c9119`), plus the commit that adds this report and the final evidence.

| Pass | Scene root / scope | Review cameras |
|---|---|---|
| Perimeter walls | Ward perimeter walls — 479 m of battle-scarred masonry, collapses, HESCO breach repair | `cam_pw_*` |
| Hydroponics | Ward hydroponics — planted, fitted-out quonsets and a worked yard | `cam_hy_*` |
| Warden training range | Outer Berms/Warden training range — bays, backstop, machine lane, service apron | `cam_range_*` |
| Night life | Ward night life — 8 posts + 3 brackets, lit terminals, fire, smoke, steam, haze | `cam_nl_*` |
| Basin mountains | Basin mountains — eroded 185k-triangle basin, haze retune | `cam_bm_*` |
| City paving | Paving on world-mapped sandstone flags; chunk UV metrics fixed | `cam_pv_*` |
| West Gate arches | Ward west gate arches — sealed working gates at the spawn | `cam_wga_*` |
| Rooftops | Ward rooftops — roof kit per shop, cross-street service lines | `cam_rt_*` |
| Berms road | Berms ground on a V2 shader with road splats, edge stones, cairns | `cam_br_*` |
| Texture memory | 434 textures compressed; glTF add-on on by default; player VRAM 8.0 → 4.5 GB | `cam_tm_*` |
| Night facade | Wall lamps as soft spots, lens fixes, per-street window glass, masonry normal 0.65 | `cam_nf_*` |
| Wall-foot drifts | Ward wall-foot drifts — 334 sand banks + 320 decals | `cam_wfd_*` |
| Birch canopy | Baked canopy shading, Ward Canopy shader, re-aimed bed uplights | `cam_bc_*` |
| Shade sails | Ward shade sails — four form-found sails with festoon lights | `cam_ss_*` |
| Character progression (Codex) | Attributes, skills, implants, carry/storage limits, crafting requirements, loadouts, save v2 | — |

## Final test results

Merged tree `9062b001`, development build `Builds/final` (copy of `LinuxDevelopment`) and release build `Builds/Linux`,
both built with `-nographics`. RTX 3060 12 GB / i9-10850K, OpenGL Core, 1920×1080 window, High preset, render scale
100 %, texture streaming budget 5632 MB. Quiet machine (no agents running). Evidence in this folder (`run.log`).

**Function: all pass.**
- Edit Mode tests: **195/195 passed** on the merged tree, 0 compile errors (`editmode-results.xml`).
- Builds: development and release both "Build Finished, Result: Success" (`build-both.log`), 7.9 GB each (about 11 GB
  before texture compression).
- City loop: **PASS** (`cityloop/`).
- Range tutorial (real input): **PASS 10/10** (`tutorial/report.json`).
- Character progression (Codex's real-input check): **PASS** — rifle rejected with "Requires Rifle 20.", incompatible
  slot rejected, rifle/implant/vest/backpack saved and restored through Continue with the same carry and pack values
  (CARRY 13.2 / 30 kg, PACK 3.3 / 30 kg), no log errors (`progression/report.json`).
- Release smoke: **PASS** (`release-smoke/`).
- Lookbook: 135 cameras (10 standard + 125 review cameras from all passes) × 13:00 / 20:30 = **270 captures, 0 errors**,
  nine chunks (`lookbook-p01…p09`, contact sheets per chunk).
- GPU memory: native runs peaked at 6.9–7.6 GB system VRAM (about 11–11.8 GB before the texture-memory pass).

**Frame time** (alternating runs, 2 per arm, 8 s profiles; this desktop drifts about ±1–1.5 ms between runs):

| View | Baseline 3ebd801b → final | Batch 2 → final (batch 3 + Codex) |
|---|---|---|
| cam_hill 13:00 | 67.6 → 62.0 fps, p50 +1.30 ms | 63.1 → 60.6 fps, p50 +0.62 ms |
| cam_hill 20:30 | 74.1 → 66.8 fps, p50 +1.41 ms | 68.0 → 66.9 fps, p50 +0.20 ms |
| cam_avenue 13:00 | 58.9 → 54.7 fps, p50 +1.21 ms | 56.8 → 54.7 fps, p50 +0.67 ms |
| cam_avenue 20:30 | 62.8 → 58.2 fps, p50 +1.18 ms | 60.4 → 57.9 fps, p50 +0.60 ms |
| cam_gate 13:00 | 174.5 → 130.9 fps, p50 +1.99 ms | 137.4 → 131.4 fps, p50 +0.35 ms |
| cam_gate 20:30 | 177.1 → 126.2 fps, p50 +2.31 ms | 130.4 → 127.2 fps, p50 +0.19 ms |

**Warmed real-input walk** (`unity/tools/profile_north_walk.py`: West Gate → east lane → Basic General → north end →
west lane, noon then night; baseline and final alternated, two rounds each):

| Walk | Baseline (2 runs) | Final (2 runs) |
|---|---|---|
| Noon | 100.6 / 99.7 fps, p50 7.9 / 8.0 ms, p99 19.2 / 19.5 ms | 78.5 / 86.9 fps, p50 9.9 / 9.3 ms, p99 44.7 / 26.6 ms |
| Night | 79.5 / 76.5 fps, p50 12.4 / 12.7 ms, p99 16.9 / 23.2 ms | 71.0 / 69.3 fps, p50 13.4 / 13.6 ms, p99 19.2 / 37.8 ms |

- The AGENTS §7 target (average ≥ 60 FPS on a warmed traversal at 1080p High) is **met** on the walk (69–87 fps).
- The whole day costs about **+1.2 to +1.4 ms** at the wide and avenue views and about +2 ms at the gate (where the
  arches, sails and lamps sit, still 126–131 fps).
- **Hitches got worse.** Walk p99 rose (noon 19 → 27–45 ms) and the first final night walk had a single **585 ms** frame;
  the second night walk's maximum was 58 ms. That pattern matches the night facade pass's predicted one-off shader
  compile when cookie spot lights first appear at dusk; not yet confirmed. It is the main regression to fix or
  explain (AGENTS §7).
- cam_avenue at 13:00 is below 60 fps (54.7) as a single static view; the baseline was already 58.9 there.
- GPU time is unavailable in this player.

## Decisions for Carl

1. **Texture streaming budget.** The paving pass raised the PC budget from 4096 to 5632 MB because uncompressed
   textures had pinned everything at quarter resolution. After the texture-memory pass the recommendation is 3584 MB.
2. **The 32-light cap.** On the Linux OpenGL Core player URP draws at most 32 lights per camera; courtyard views see
   68–85, so lamps beyond ~26–36 m are not drawn (part of why night is dark). Options: Vulkan (a graphics-API change;
   AGENTS says not to change it silently) or a light-budget pass.
3. **Gate naming.** "WEST GATE" is signed on the +X spawn arches (east on the compass) and on the −X Berms gantry.
   AGENTS §2 says "spawn at West Gate … gate openings", but the +X openings are now sealed; the strip behind the rampart
   (x 49.7–58) is unreachable.
4. **Night facade look.** Facades are now downlit and darker between lamps; masonry normal strength 0.65 applies to all
   shared Ward stone by day too. The Finery "orange streak" is the moonlight shadow of avenue lamp 02's mast — softening
   it means changing the night moonlight district-wide.
5. **Shared decal shader.** `WardDecal.shadergraph` has angle fade off, so ground decals smear onto risers and prop sides.
   Turning it on fixes it project-wide but changes street dressing, West Gate and weathering decals.
6. **Rooftops.** Set-back roof kit is mostly hidden by parapets at avenue eye level. Stronger front-edge pieces? Keep or
   merge the old retrofit service poles with the new lines?
7. **Berms road.** Accept the paler, basin-matched floor? Move the range's earth bank to the V2 material?
8. **Birch 4b.** Darker (risks looking dead) or as is?
9. **Shade sails.** Market sail tied to the retrofit I-beam poles with the fire barrel beside it; four unguyed poles on
   stone footings; camera-only canvas colliders; canvas shadow at both LODs; dye choices.
10. **Mira as a civilian trader** (next-wins item 5) was held as high risk: go or no-go.
11. **`promo-site/`** (the Ashfall friends & early-testers website from another session) is in the working tree but
    deliberately not committed.

## What is missing or still weak

### Across the programme
- No moving walkthrough video: temporal stability (TAA shimmer on thin cables and leaves, LOD pops, cross-fades) and
  first-person clipping are unreviewed for every pass.
- Every lookbook capture includes the HUD and the stale "E · Talk to Vex" prompt; a HUD-off capture option is not done.
- Night overall is dark outside lamp pools; the 32-light cap (decision 2) is part of the cause.
- Each pass's own-view cost is above the ~0.5 ms guide in several places (hydroponics +0.7/+1.0 ms, range +0.7 ms,
  walls +0.6 ms close); the whole programme costs about +1.2 to +1.4 ms at wide views (see the results above).
- **Hitches:** walk p99 and one 585 ms night frame (see results) need a fix or an explanation; first suspect is the
  cookie spot lights' first-use shader compile (try `lamps.cookie=false` in the night facade tune, or prewarm shaders).
- Characters are unchanged: the four talking NPCs are still the supplied Ward Guard; the player's idle/talk are static.

### By pass
- **Perimeter walls:** rubble cones read as gravel heaps; scrap screens are flat boxes; craters are flat planes behind
  knocked-out blocks; intact bays repeat from raised views; a pier pokes 5 cm out at x 49; the QTA stencil is fainter.
- **Hydroponics:** crops are leaf cards (flat lettuces, sphere tomatoes); LOD pop at ~25 m; flat-colour aisle props;
  the painted bench reads as a red box; night grow glow is subtle; bays are not enterable.
- **Training range:** drones have one LOD, the compressor is 79k triangles, 24 decals; no edge wear up close; the droid's
  arms are raised and its chains don't meet the shoulders; drones keep feral yellow paint; the bank's back is unchecked.
- **Night life:** smoke is nearly invisible at night; unshadowed lamps light through walls and containers; the north
  wall foot is dark outside the collapse; terminal badges glow by day; Reduced Motion untested in the player.
- **Basin mountains:** still pale cream at noon (17:00 is the strong hour); some far crests are serrated fins and some
  gullies straight V-gorges; near west hills read as scree mounds at noon.
- **City paving:** courses run east–west everywhere and read slightly tiled at 20–40 m; flags are flat (normal map only);
  depth/normals passes use mesh UVs; the service bands are simply switched off; 23 render chunks still report UV metric 1.
- **West Gate arches:** the Meshy arch itself is unchanged (the stretched 8 Sep fit, soft texture); gate numbers are
  small; ruts are subtle with no groove; guard stones are plain blocks.
- **Rooftops:** quiet at eye level; alley lines barely read; ladders are decorative; no night or motion review.
- **Berms road:** marbled sandstone on the steep border band at player height; plain flats; windrow gravel looks like
  garden pebbles; edge stones read cool grey; the Berms ground mesh still carries the old basin's facets.
- **Texture memory:** glTF textures still don't stream (1.16 GB resident); glTF meshes report UV metric 1 so the streamer
  picks the wrong mips on them (fix tested on one mesh, needs its own A/B); 437 MB of compressed importer textures don't
  stream; 1,186 MB is spent on textures used only by inactive rollback objects; ~165 MB odd-sized textures stay
  uncompressed.
- **Night facade:** upper facades darker between lamps (deliberate); the hall portal lamp pools on the right door leaf;
  possible one-off dusk shader hitch when cookie lights appear (unmeasured); window interiors still procedural; shop or
  arch prefab rebuilds revert the tune (re-run `NightFacadePass apply`).
- **Wall-foot drifts:** porch decks get little sand; post collars can read as discs; 320 decals' cost to be judged
  (skirts first to cut).
- **Birch canopy:** 4b is +7 % luminance; outer crown reads pale grey-green under the moon; vendor leaf normals show vein
  stripes at grazing angles; the hill ring lenses (`VH_LampLens`) probably still clip.
- **Shade sails:** canvas undersides may read dark at noon; barrel smoke passes under the market sail's corner.
- **Character progression (Codex):** weapon mods are per weapon definition, not per item instance; equipment and the held
  pistol have no new art; Codex's worktree still holds 26 untracked evidence files that are not in its commit.

## Machine and process notes
- Three crashes in three days (29 Sep driver OOM, 30 Sep oomd killing the Claude app, 1 Oct swap-thrash freeze) led to
  the job wrappers, `ward-watchdog` and AGENTS.md §8. GPU memory was the hardest limit until the texture-memory pass.
- A pre-programme baseline build (`Builds/base-3ebd801b`) comes from a sparse worktree at
  `/home/teknetik/code/ao2-baseline-3ebd801b` with a reflinked Library; remove it with `git worktree remove` when done.
- Run state lives in `~/.local/state/ward-programme` (brief, wrappers, queue log, jobs.log, watchdog.log).
