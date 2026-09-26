# Independent visual review — 26 September 2026

Verdict: **REVISE. The inspected Ward frames are visibly below the chosen ARK: Survival Ascended reference. No AAA acceptance, perfection, or “wowed” verdict is supported.**

This is a read-only critique of dated saved imagery, with narrow source inspection. It is not a qualification of the current 26 September scene. No scene, material, shader, gameplay, or imported asset was changed by this reviewer. New candidate captures must be judged separately.

## Evidence actually inspected

The images below were decoded and visually inspected using `view_image`:

- `unity/evidence/karaveen-market/20260911/captures/west-gate-opening-fixed.png`: 1280 × 720 native development capture. Broad paving, blank side walls, two actors, distant tree.
- `unity/evidence/karaveen-market/20260911/captures/truck-repaired.png`: 640 × 304 elevated asset/placement view. Useful for placement only; insufficient for close material acceptance.
- `unity/evidence/reference-street/20260910/iteration-04-native/cam_reference_street.png`: detailed Field Supply/Finery frontage.
- `unity/evidence/reference-street/20260910/iteration-04-native/cam_hill.png`: whole district and tree.
- `unity/evidence/reference-street/20260910/iteration-04-native/cam_hero.png`: close upward tree/canopy view.
- `unity/evidence/reference-street/20260910/iteration-04-native/iteration-first-person-field-threshold.png`: near shutter and sandstone threshold.
- `unity/evidence/reference-street/20260910/iteration-04-native/shade-cam_canopy_under-hour-16.png`: close cloth and practical lamp.
- Three official ARK reference images listed below.

The reference-street settings and environment records identify native Linux 1920 × 1080 at 100% render scale, MSAA 4, full textures, postprocessing enabled, VSync disabled, uncapped, nine actors, OpenGLCore, Unity 6000.6.0f1, RTX 3060 12 GB, i9-10850K, NVIDIA 595.84. Shadow distance is recorded as only 18 m. These settings apply to that dated capture set, not automatically to current work. The 11 September repair record identifies its native check as 1280 × 720/OpenGL. No current frame-time qualification was performed here.

The prior `critic-iteration-04.json` was read after initial independent image inspection. Its REVISE status and observed material limitations remain consistent with this review; its motion review was not repeated and is not claimed as new evidence.

## Official reference provenance

References are retained here solely for analysis/comparison, not as distributable game assets. Their hardware, render scale, quality, exact lens, exposure, capture mode and possible promotional processing are unknown. They cannot establish same-hardware performance, identical-camera parity, physics, or temporal stability.

1. **Desert courtyard**: Studio Wildcard's [Scorched Earth launch announcement](https://steamcommunity.com/games/2399830/announcements/detail/4174347361792746505). [Image](https://clan.fastly.steamstatic.com/images/44719856/41798a1b8cae10f220da4e4c94becd5384c83a92.jpg), saved as `ark-scorched-earth-official-courtyard.jpg`, 2560 × 1440. Retrieved 26 September 2026. Web search tied this image to the official announcement; direct web-tool image retrieval timed out, and normal HTTP retrieval succeeded. Actual image pixels were inspected. Best comparison for Ward's desert steps, masonry, oasis foliage, sun/shade depth and ground transitions.
2. **Oasis/creature**: official [Scorched Earth Steam store](https://store.steampowered.com/app/2849450/ARK_Scorched_Earth_Ascended/) screenshot 0, retrieved using [Steam appdetails](https://store.steampowered.com/api/appdetails?appids=2849450). Saved as `ark-scorched-earth-store-00.jpg`, 1920 × 1080. Exact image URL is in `store-reference-provenance.json`. Secondary context for canopy volume, vegetation clustering, surface response and depth; not a like-for-like architecture or human-character comparison.
3. **Desert creature encounter**: the same official store/API, screenshot 3, saved as `ark-scorched-earth-store-03.jpg`, 1920 × 1080. Inspected, but excluded from Ward street scoring because subject, scale and cinematic framing are mismatched.

**This initial comparison is not blind.** I located the references and know their identity. Concealing filenames later does not erase that knowledge; ARK's statues/creatures and Ward's recognizable HUD are also visual identity cues. A randomized pair can test preference but must be described as anonymized presentation with possible recognition, not a scientifically blind experiment.

## Comparative judgement

The official ARK courtyard looks better overall. Its major advantage is coherent spatial detail: irregular stair edges, sand and stone debris distributed by plausible accumulation, varied plant forms occupying different heights, deep shaded vegetation interiors, colored leaf transmission, and masonry whose shape and wear reinforce one another. The foreground leads into an architectural focal point with substantial overlap between depth planes. Some highlight detail is sacrificed to backlighting/bloom; that is not a requirement for Ward to copy.

Ward's improved street already has credible lintels, quoin blocks, openings, thresholds and readable signage. Preserve that work. Its repeated orange corrosion islands are visibly soft at first-person range; much of the building weathering has a uniform authored quality. The hill view is weaker than the street: the large pale tree crown has insufficient shadowed volume, the surrounding pale basin reads as similarly textured rounded walls, and large unbroken paving regions expose repetition. The close tree does have branched geometry and recognizable leaves, so “needs more polygons” is not a demonstrated diagnosis.

## Rubric and scores

Scale: 0 missing/broken; 1 severe visible failures; 2 functional but conspicuously artificial; 3 credible progress with clear focal weaknesses; 4 strong at the intended distance with only minor defects; 5 chosen reference target met in this view. Null means not assessed, never a pass. Scores are visual judgement, not an objective AAA certification.

| Category | Ward street | Ward hill/tree | ARK courtyard reference | Evidence / limitation |
| --- | ---: | ---: | ---: | --- |
| Composition / silhouette | 3 | 2 | 4 | Street has clear facade hierarchy. Hill exposes isolated buildings, broad empty paving and repetitive basin. ARK layers vegetation, thresholds and ruins. |
| Scale / construction | 4 | 3 | 4 | Street thresholds and door framing read convincingly. Tree branching exists but crown/root acceptance needs current close captures. |
| Material detail | 3 | 2 | 4 | Shutter corrosion is blurred and repeated; tree foliage reads chalky/gray. ARK varies leaf, sand, rock and metal response. |
| Lighting / depth | 3 | 2 | 4 | Ward close shadow detail exists, but far tree and district flatten. ARK retains clear dark canopy interiors and backlit leaf color. |
| Density / storytelling | 3 | 2 | 4 | Posters and shop identity help Ward street. Large district paving regions and isolated props do not explain activity convincingly. |
| Character / animation | null | null | null | Static distant actors and statue/creature reference cannot qualify human anatomy or animation. |
| Temporal stability | null | null | null | No continuous motion review performed in this pass. |
| UI / readability | 4 | 4 | null | Ward text and action slots are readable. Reference has no gameplay HUD. |

## Prioritized defects and next focused pass

1. **Hero tree and its shade are the most obvious central-view weakness.** Pale leaf clusters lack a convincing difference between sunlit exterior and shaded crown interior. Inspect current native tree imagery first, since these frames are dated. If reproduced, diagnose leaf texture color space/normal response/transmission together with shadow distance and canopy occlusion before changing geometry. Preserve the existing tree prefab, material GUIDs and source maps; audition bounded variants under matched sun/shade and exposure.
2. **Whole district floor and background read as repeated surfaces.** Broad paving dominates spawn and hill views; distant geology lacks convincing stratified silhouette and material variation. Add purposeful ground transitions, localized accumulated material and service-space construction through separately reviewed art passes. Do not scatter random clutter or expand the playable layout to hide repetition.
3. **Closest focal metal still fails the reference standard.** The shutter has repeated soft orange rust patches, weak handling/drainage wear history and a broadly uniform finish. Its geometry is legible; a higher source resolution alone will not fix the wear design. Preserve text and functional thresholds while revising material regions at physical scale.
4. **Canopy material and local lighting remain visibly artificial.** The hour-16 underside has large smooth dark areas and angular bright bands near the lamp. Diagnose mesh normal interpolation, point-light response, shadow bias and cloth BRDF separately; do not brighten global ambient to conceal it. Retain existing seam/fold geometry until demonstrated defective.
5. **Characters and motion are unqualified.** Existing role/model assignments remain. Require face/full-body sun/shade, locomotion/turn/idle transitions, foot contact, clipping and real-input camera review before acceptance. This review does not score physics or combat from pictures.

Recommended first environment experiment: **current-tree daylight material and shadow audition**, with an unchanged baseline plus one bounded leaf/shadow candidate. Required cameras: current `cam_hill`, `cam_hero`, a player-height trunk/ground view, crown underside in frontlight and backlight, and a short moving approach across the old shadow-distance boundary. Record settings and evaluate visible gain against source and native baseline. Keep any improved candidate only if it preserves or improves ground contact, alpha edges, motion and frame-time cost. Rejection remains appropriate if leaf cards wash white, crown looks hollow/flat, near bark is soft, shadows pop, or geometry clips.

Narrow source inspection corroborates a useful diagnostic: `GameSettings.cs:145` assigns 18 m to both high and ultra shadows (12 m to low), and `CityTimeReflections.cs:120` clamps reflection-capture shadow distance to 18 m. The saved hero leaf material has no AO map, a white tint and transmission 0.22. Its albedo metadata is sRGB and its packed metallic/smoothness map is linear; no obvious color-space import error was found. The custom forward shader flips leaf backface normals before baked-GI evaluation. These are leads, not proof that a single parameter explains every visible defect. Preserve source geometry and compare native candidate imagery before adopting a change.

## Acceptance remains open

The current evidence does not support stopping at “perfect.” A new scene capture and review can establish specific improvements. It cannot retroactively accept the entire district, all systems, or latest-AAA parity. Keep failures and unknown categories in the record; never raise scores merely to end an iteration loop.
