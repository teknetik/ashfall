# t_6c931016 review round 2 (r7): 27 Sep 2026, 19:26–20:55 BST
Snapshot only: /home/teknetik/code/.snap/ao2-t_6c931016. The shared checkout /home/teknetik/code/ao2 is untouched
(793 porcelain entries at 20:53). Nothing committed. r6 evidence (20260927-pm/) and r6 builds
(unity/AthenHill/Builds-r6/, reflink copy) are preserved. This is for independent review (qa-harness); it is not
self-accepted.

## Worker history this round
- Run 4685 built the v5 hands (below) and started V5AndBuild. systemd-oomd killed its worker scope at 20:16:36
  (app.slice pressure 54% > 50%) in the middle of the Development build, because that Unity ran inside the worker scope.
- Run 4689 (this one): every Unity/player run is in its own `systemd-run --user --scope` (MemoryHigh 12G, MemoryMax 16G).
  There were no further oomd kills.
- Housekeeping not done: the 4689 run could not delete an orphaned 16 GB-sparse /dev/shm/udsMem0a903c… segment
  (and its sem.*) left by the 20:16 kill, because the safety policy blocked `rm`. It had no owners (`fuser` rc 1, no
  /proc maps). Unity has run fine alongside it since. It also could not delete a 5 GB stale `Temp/…resS` in the
  snapshot. Ops can remove both.

## Request #6: FP hands v5 (supersedes v3)
Source: `art/character_feel_20260927/fp_arms/build_fp_hands_v5.py` (Blender 4.x, headless). Output:
`PlayerFPHands_v5.glb/.blend`, `PlayerFPHands_v5_tex/` (2048 normal + AO), `build_checks_v5.json`.
- Base: MakeHuman hm08 base mesh and game-engine skin weights. Both are explicitly CC0: the base.obj header reads
  "explicitly released as CC0 in september 2020", and the weights JSON says `"license": "CC0"`. The copies are in
  `fp_arms/makehuman_cc0/`.
- **Open licence item:** `mpfb_fingernails.jpg` comes from the MPFB 2.0.17 add-on data. It is used only at build time,
  as a mask to select nail vertices. It carries no per-file licence notice, and MPFB's code is GPL-3.0. Confirm it
  before shipping, or replace it with a hand-painted nail selection.
- Method: cut the forearm/hand cage, rig the fingers from the mesh's joint helpers, and fit each finger by
  collision-aware curl onto the view-model pistol (1 mm voxel occupancy).
  - Results: 0 vertices deeper than 1 mm inside the pistol, and 0 more than 1 mm inside the other hand.
  - Minimum clearance is about 1.1–1.5 mm per finger.
  - Scale is 1.075× MakeHuman, about adult size.
  - 2 × 54,144 = 110,328 tris.
- Materials: glove, skin and nail use URP Lit with the baked normal and AO. Shadows are off, as before.
- Hip pose changed on the saved view model: hipOffset (0.13, −0.16, 0.46) → (0.10, −0.105, 0.40), and hipEuler
  (3, −5, −8) → (6, −4, −4). It was chosen from six Editor candidates (`fp-grip/hip-tune/contact.png`) because the old
  pose cut the grip off at the frame bottom. ADS is unchanged.
- Code:
  - `FPGripPass.cs` adds `HipTune` and `HipApplyAndBuild`.
  - `FPHandsV2Tests.cs` raises the tri ceiling from 40k to 150k. The 40k ceiling was a v2 procedural-mesh
    assumption, and the reason is recorded in the test. It was the only EditMode failure.

### What improved vs r6 (the reviewer's comment #903 items)
1. The fingers are now anatomical and curled round the grip; they were straight and splayed.
   - The support fingers wrap under the trigger guard over the firing fingers.
   - There are no detached tip capsules; the nails are part of one skin mesh.
   - See `fp-grip/blender-v5/left.png`, `right.png`, `below.png` and the `*_nopistol` variants.
2. The hip view now shows both hands and the wrap: `native/requests-1-6/06-fp-hip-dusk.png`,
   `native/character-feel/fp-hip.png`.
3. The material now has a baked normal and AO, so it is no longer flat albedo.

### Remaining #6 defects (my own read of the native 1920×1080 captures; not accepted)
- **ADS does not match the reference photo's wrap.**
  - In the photo, the support palm covers the firing hand's fingers and both thumbs sit under the slide.
  - In `06-fp-ads-dusk.png` (crop around px 660–1260 × 560–1080), the two hands read as side-by-side smooth forms
    with the support thumb crossing the top. The back of the firing hand is a large, uniform, rounded mass behind the
    rear sight.
  - At dusk, finger separation is only partly readable, and the knuckle/tendon detail from the normal map barely
    shows at this distance.
- The skin/glove reads slightly plasticky. There is no albedo variation map, only a base colour with normal and AO.
- The hold is static. The trigger finger does not animate on fire.
- The hands (110k tris) are rendered at full detail. No LOD was made; they are always close to the camera.

### Post-build iteration (20:58–21:05, scratch only, not installed)
- Two re-placements of the support hand were tried in
  `~/.hermes/profiles/game-dev/cache/scratch/t_6c931016/v5/c1` and `c2`, with the comparison sheets in `cmp.png`.
  - c1 moved the support-hand landmarks 6–10 mm towards the grip, with hug×2.
  - c2 also moved the firing web and wrist and used hug×3.
- Both stay collision-clean: 0 hand-in-hand vertices and ≤9 pistol vertices, all under 1 mm.
- The gain was only marginal. The mean palm-to-grip gap stays at 16–18 mm, because the Meshy pistol grip's bulk and
  the fitter's non-penetration constraint block the palms from closing further.
- The ADS view therefore still doesn't reach the photo's compact wrap. Getting there likely needs one of:
  - a thinner or cleaned-up grip collision proxy;
  - soft-tissue compression, where the palm is allowed to deform against the grip;
  - a sculpted or animated hand-grip asset, which needs an art decision.

## Requests #1–5 (saved-scene read-back `requests-1-5-verify.json`; native `native/requests-1-6/`)
1. Run cadence: playback 1.457 at 6 m/s. Video: `01-run-dusk.mp4`. Unchanged from r6.
2. Warden feet: Ossa +6.3 mm and Rell −3.0 mm.
3. Road tree: off the road (−87.5, −1.18, −7.0), collider off. Depot route clear.
4. Truck: uniform 0.65. **Correction to r6 and review round 1:** 3.39 m is the truck's *height*, not its width.
   - The mesh read-back gives body width 2.54 m, overall width 2.95 m (mirrors and wheel arches) and length 7.65 m.
   - The collider is 7.65 × 2.96 × 3.39 m (L × W × H in the truck's local axes).
   - So the body matches Carl's ~2.5 m guide, and the height of 3.39 m is just under the 3.5–4 m range.
   - No mesh change was made. Carl or the reviewer should confirm; I haven't self-accepted it.
   - Native: `34-cam_berms_gate.png`, `34-cam_market*.png`.
5. Dusk default: hour 17.0, sun ~11°, intensity 0.98, exposure −0.12. `time-state` in `report.json` confirms it.

## Builds, tests and native checks (r7)
- Linux Development: Succeeded, 0 errors, 95 s (`linux-build-dev.json`).
- Linux Release: Succeeded, 0 errors, 119 s (`linux-build-release.json`).
- EditMode:
  - First run 65/66: `FPHandsV2Tests` failed on the tri ceiling (`editmode-results-r7.xml` was overwritten; log
    `unity-editmode-r7.log`).
  - After widening the ceiling: **66/66 passed**, 128 s (`editmode-results-r7.xml`).
  - The change is to a test only, so the builds are unaffected.
- Native checks, with the Editor closed, dev build, OpenGLCore 1920×1080, RTX 3060:
  - `check_character_feel`: passed, 0 exceptions.
  - `check_checkpoint`: passed, 0 exceptions.
  - `check_depot`: passed, 0 exceptions. The first attempt was killed by my tool timeout and is kept as
    `native/depot-interrupted-2039/`.
  - `capture_requests`: done, 0 exceptions, hour 17.0 (`native/requests-1-6/`, including `06-fp-pistol-dusk.mp4` and
    `01-run-dusk.mp4`).

### Frame timing: FAILS the p99 ≤ 16.67 ms criterion in this run, and the cause is the host, not v5
The host was heavily loaded throughout: load average 17–25, with the Hermes desktop at about 630% CPU and ChatGPT and
codex running. r6 was measured at a quieter time.

`native/frame-timing-summary.json`:

| Route | Average FPS | p50 (ms) | p95 (ms) | p99 (ms) | Max (ms) |
| --- | --- | --- | --- | --- | --- |
| Checkpoint | 150 | 5.5 | 16.6 | 25.1 | 30.0 |
| Depot route | 133 | 6.0 | 18.5 | 23.7 | 33.6 |
| Depot fight | 110 | 7.6 | 19.9 | 24.2 | 26.9 |

Interleaved A/B on the same route under the same load (`native/ab-checkpoint/`, the unchanged `check_checkpoint.py`
with only the player path swapped; all four runs passed):

| Build | Average FPS | p99 (ms) |
| --- | --- | --- |
| r6-1 (v3 hands) | 148.8 | 25.7 |
| r7-1 (v5 hands) | 144.4 | 25.3 |
| r6-2 (v3 hands) | 153.5 | 24.6 |
| r7-2 (v5 hands) | 146.0 | 24.6 |

- p99 is the same for r6 and r7.
- r7's average FPS is about 3–5% lower, consistent with the extra 84k view-model tris.
- The r6 build that measured p99 16.2 ms at 17:13 now measures 24.6–25.7 ms, so the regression is host contention.
- The frame-time criterion therefore still needs re-measuring on an idle host. It is **not** qualified by this run.
- GPU ms is unavailable (the bridge reports 0).

## Rollback
- Hands: delete or rename `PlayerFPHands_v5.glb` and FPGripPass installs v3. `UseOldArms(vm,true)` gives v1.
- Hip pose: set hipOffset (0.13, −0.16, 0.46) and hipEuler (3, −5, −8).
- r6 builds: `Builds-r6/`.
- Whole snapshot baseline: `/home/teknetik/code/.snap/ao2-t_6c931016-baseline`.
- Porting to the shared checkout needs an explicit reviewed copy step. That has not been done.
