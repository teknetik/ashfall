# Player shoulder and clothing review — 5 October 2026

The main character asset was updated and the native Linux development player rebuilt. Walking no longer pulls the shoulder attachment down from its relaxed idle pose; the exported gait also has less excess pelvis motion and a corrected ground offset. The suit has a lower collar, softer matte fabric response, and a fitted utility belt with canvas pockets, seams and catches. This is a focused revision of the existing MPFB character. Carl's visual acceptance is pending.

## Review media

- [Matched before/after motion](shoulders-before-after.mp4): native front-view walk, stop, run and jump, cropped equally side by side and labelled. The motion has not been retimed.
- [Updated front view](after/cam_player_face_20261003_body_front-h13.00.png), [rear view](after/cam_player_face_20261003_follow_back-h13.00.png), [face view](after/cam_player_face_20261003_face_quarter-h13.00.png).
- `motion-before/` and `motion-after/`: original full-resolution front/rear recordings, pose captures and motion traces. `before/` and `after/`: matched noon character/hill/avenue/gate views; the after set also records 20:30. `before-wide/` and `after-wide/` cover the grid, whompah and hero cameras at noon.
- `rifle/`: 21 additional native views, including held weapons, first-person aiming, and the Warden plate carrier.

## Scope and verification

Source, provenance and rollback: [art record](../../../../art/character_polish_20261005/README.md). The exported model retains its GUID, all 54 rest bones, inverse bind matrices, skin UVs, equipment mounts and body scale. Existing scene and prefab references inherit the asset change. The scene file is byte-identical to the pre-pass copy; gameplay movement settings are unchanged. Body triangles increase from 71,867 to 76,043; material slots from five to seven.

| Check | Result |
| --- | --- |
| Unity Edit Mode | 290/290 passed; includes shoulder relationship and gait loop regression |
| Character integration | PASS; 54 bones, no missing references, pistol/rifle bindings 24/24 |
| Range tutorial | 10/10 passed, real movement/interact/fire input |
| City loop | 29 checks, complete; dialogue, buy/sell, travel, modal input |
| Rifle quest | 38/38 passed; first-person models, equip, fire, switch, plate carrier and save |
| Native motion and lookbook logs | No runtime exceptions in the reviewed runs |

The body asset's old walk clavicles differed from idle by 37–40 degrees, run by 27–33 degrees. The new source audit measures walk at most 0.62 degrees and run at most 2.41 degrees. Hip vertical excursion changes from 6.64 to 4.50 cm in walk, and 6.32 to 5.18 cm in run. Small sole penetrations remain between baked keys: up to 11.5 mm walking and 18.3 mm running in the Unity audit. No claim of complete ground IK is made.

`build-identity.json` records hashes of each build's scene/assets/runtime assembly at working-tree HEAD `1c232f74c3e7b1dc11672ad2fc464caf28a5a310`. These are dirty working-tree builds, not a committed revision. The baseline is preserved at `unity/AthenHill/Builds/character-before-20261005`; the updated player is `unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64`. The executable's timestamp does not identify changed Unity data, so the data hashes are included. The runtime assembly hash is identical before/after.

The first build was killed at its memory cap. Retrying with two job workers and one importer succeeded: zero errors, 346 existing build warnings. The final editor-only evidence-preservation helper was then compiled and audited separately. Logs and the full test XML are under `art/character_polish_20261005/`.

## Measured cost

Linux RTX 3060 12 GB, i9-10850K, 31,969 MB system memory, NVIDIA 610.57.04, OpenGLCore. Native 1920×1080, High preset, render scale 100%, TAA, high shadows, post-processing enabled, VSync off, uncapped; no frame generation. Environment/settings files are captured before the native QA window resize and may list 1890×1029. The motion report's `resolution`, final snapshot and capture dimensions confirm 1920×1080 for the measurements. Native snapshots report 16 active actors. No actors or scene effects were disabled for the comparison.

These are four-second unrecorded, warmed West Gate walk samples, ordered before/after/after/before. Video recording is separate. They measure the cost of this character edit, not a full representative route qualification. `performance.json` retains full measurements; unavailable GPU, draw-call and batch counters are null.

| Run | Average FPS | p50 ms | p95 ms | p99 ms | Maximum ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Before A | 42.43 | 23.45 | 26.36 | 28.29 | 35.28 |
| After A | 43.04 | 23.08 | 25.68 | 26.57 | 27.10 |
| After B | 41.07 | 23.52 | 31.94 | 55.37 | 57.35 |
| Before B | 40.54 | 23.46 | 33.95 | 56.94 | 61.48 |

After-minus-before median deltas are -0.37 ms and +0.05 ms, within observed run variation. Both builds remain below the 60 FPS target in this view. The slower B pair has tail spikes in both builds. CPU mean/p95 are retained in the JSON; submitted triangles include multiple passes and are not the character's visible geometry count. Memory/load data from the functional run are in `gameplay/memory.json` and `gameplay/environment.json`; these are not isolated character-cost measurements.

## Visual assessment

Scores are provisional reviewer judgments from the saved native views and motion, against the requested believable Ward character direction. They do not certify whole-game GTA6 parity. The goal of 4 in every applicable category is not yet met.

| Category | Before → after (0–5) | Evidence and remaining defect |
| --- | --- | --- |
| Composition / silhouette | 3 → 3.5 | Lower collar clears the neck; belt gives a more legible waist. Suit and chest kit still have a broad, generic outline. |
| Scale | 4 → 4 | 1.800 m idle body, unchanged rest anatomy and equipment sizing. |
| Material detail | 2.5 → 3 | Fabric reads less glossy, belt has distinct weave and hardware. Original garment texture remains noisy; face/hair need dedicated close-up work. |
| Lighting / depth | 3 → 3 | Daylight describes the form; night views leave the face too dark. Lighting was not changed. |
| Density / storytelling | 3 → 3.5 | Small practical pouches and closures improve the worn field-clothing read. They do not yet establish a distinctive hero costume. |
| Character / animation | 2 → 3.5 | Shoulder collapse corrected, less excess bounce and floating. Underlying walk/run acting, minor sole penetration and hand quality still need work. |
| Temporal stability | 3 → 3.5 | Loop endpoint and shoulder transition corrected; no new native animation flicker observed. Existing hair/detail shimmer and fast gait remain visible. |
| UI / readability | 4 → 4 | Gameplay HUD unchanged. The fixed front review camera lets the compass overlap the top of the head; face and moving views provide complementary inspection. |

The primary shoulder defect is corrected and functional regression checks pass. Further face/hair, costume texturing and authored locomotion work is still needed to reach the intended character standard.
