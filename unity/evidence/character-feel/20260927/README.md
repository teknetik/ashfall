# Character feel — 27 Sep 2026

Scope from Carl: Wardens look "shifty" (constant peering), character animation generally (rebuild characters if
needed), loud and unrealistic player footsteps (ElevenLabs allowed), a visible weapon when firing and aiming in first
person, and better gunshot sounds. Handover: `art/character_feel_20260927/HANDOFF.md`; log: `PROGRESS.md` beside it.

Tested revision: the working tree of 27 Sep 2026, uncommitted, on top of `31720d59`. Builds: Linux development and
release players, both 0 errors (`unity/AthenHill/Captures/linux-build-{dev,release}-20260927.json`). Edit Mode tests
65/65 (61 existing + 4 new in `Tests/Editor/CharacterFeelTests.cs`). All native runs had the Unity Editor closed.

## Evidence

| Folder | What |
| --- | --- |
| `native-before/` | Baseline on the 04:43 development build (before any change): videos with desktop audio, captures, `report.json` with EBU R128 per segment |
| `native-after/` | The same script on the final build: `guards.mp4`, `surfaces.mp4`, `pistol-third-person.mp4`, `pistol-first-person.mp4`, stills, fire frames, `report.json` |
| `native-checkpoint/` | `unity/tools/check_checkpoint.py` (10 checks, including the city loop) on the final build |
| `native-depot/` | `unity/tools/check_depot.py` on the final build |
| `performance.json` | Frame-time summaries for the checkpoint and depot routes |

The check script is `unity/tools/check_character_feel.py` (real keyboard/mouse input; it works against old builds so it
records the baseline too).

## 1. Wardens: why they looked paranoid, and the fix

Measured on the rig (head direction per 0.1 s over the loop):

| Clip | Head yaw range | Head motion | Chest yaw range |
| --- | --- | --- | --- |
| `idle_meshy` (was on all six guard-model characters) | ~258° | 127°/s | ~102° |
| `talk_meshy` (was on all six) | 58° (held ~54° off the listener) | 24°/s | 48° |
| new idles (library 243/244/246/252) | 3–22° | 1–8°/s | 2–12° |
| new talk (library 313/314) | 13–18° | 17°/s | 8° |

- The Sep 2026 guard rig task is gone (Meshy 404), so the same Meshy model was re-rigged
  (`meshy/character-feel-20260927/rig_guard.py`, `ward-guard/rig.json`). The new skeleton matches the installed one
  (rest rotations within ~1°, joints within ~3 mm), so clips keep rotations plus the Hips translation only; the installed
  mesh, bind pose and bone lengths are untouched (`Editor/CharacterFeelPass.cs`).
- Each character has its own loop: Ossa 243 / talk 313, Rell 252 / 314, Torr 244 / 313, Mira 246 / 314, Linn 252 / 313,
  Vex 243 / 314. `ActorAnimation` also derives a start phase and a ±8 % rate from placement, so none move in step.
- New `ActorLookAt` (on `WardGuard.prefab`): levels the gaze (several library idles tilt the head), turns toward the
  player inside 4 m (±45° yaw, ±15° pitch, eased over ~0.5 s), holds eye contact in dialogue, and otherwise makes one slow
  glance every 10–20 s. Native run: Ossa and Rell both report `Focused` when the player steps in.
- Old clips (`idle_meshy`, `talk_meshy`) remain in the project for rollback.

## 2. Player animation

- Idle: the static single-frame pose is replaced by a retargeted breathing idle (library 252).
- Player rig: the colonist was re-rigged in Meshy from its own mesh (`rig_player.py`, `player/rig.json`); its joint
  frames differ from the installed skeleton (~110° at hips/chest), so clips are retargeted by bind-pose deltas
  (`CharacterFeelPass.Retarget`). Ten library clips were retargeted (aim, draw, walk/back/left with gun, turns, idles).
- Pistol hold: `Player/pistol_hold.anim`, the settled frame of library 95 ("Gun Hold Left Turn") with its hips turn
  removed and the torso squared (−8° yaw, −16° lean). Auditioned against the other gun holds; it is the only one that keeps
  both hands on the grip.
- Third person (`PlayerWeaponPose`): the hold is mixed from `Spine02` on legacy layer 5 over idle/walk/run while aiming,
  for 0.9 s after a hip shot, and briefly on draw; the spine follows camera pitch, the hand turns the barrel onto the aim
  line, and each shot kicks. The pistol is now mounted for the aim hold (it was mounted for the hanging idle hand, which
  tilted the barrel up when raised).

## 3. Footsteps

Before: three stone clips in fixed order, distance cadence, same sound on every surface, set loudness −23.3 LUFS with a
9 dB spread between clips, peaks at −3 dBFS.

After (`FootstepAudio` on the player; CityAudio's cadence is bypassed):
- Trigger on foot contact: the foot bone falling below 0.165 m after lifting above 0.21 m (measured: planted feet sit
  0.13–0.16 m above the root in the Meshy walk/run).
- Surfaces: collider rules (aprons, jersey barriers → concrete; crates, benches → wood; containers, wrecks, truck →
  metal; hill grass and hesco → sand) then the Berms map (88×204 grid baked from `BermsGroundSplat`: gravel road vs sand),
  default sandstone paving. Native route saw Stone, Concrete, Gravel and Sand in order.
- Sets from ElevenLabs (`unity/tools/generate_footstep_audio.py`, 46 takes sliced at onsets): walk and run 8–12 variants
  per surface for stone, sand, gravel, concrete, metal (walk 8), wood; landings stone 8, sand 10, gravel 12, concrete 5,
  metal 2 (falls back to run). Each set is level-matched and mastered to −30 LUFS walk / −28 run / −26 land, with
  surface offsets (sand −2.5 … metal +1.5). Per-file numbers: `unity/staging/elevenlabs-audio/footsteps/footstep-manifest.json`.
- Random choice without immediate repeats, ±5 % pitch, ±2 dB; 0.7× in first person, 0.75× while aiming.
- Level: walking on stone is about 13 dB below the old steps at the source (−6.7 dB mastering, −6 dB trim).
  Recorded mix of the whole surface walk (ambience and music included): **−18.1 LUFS before → −24.6 LUFS after**.

## 4. First-person weapon

Before: the camera hides every player renderer in first person, so nothing was visible; in third-person aim the
pistol hung at the side (see `native-before/tp-aim.png`, `fp-ads.png`).

After (`FirstPersonViewModel`): the player's own forearms and hands (split from the colonist in Blender,
`art/character_feel_20260927/fp_arms/extract_arms.py`, 1,373 triangles, the player's materials) hold a copy of the scrap
pistol on layer 9 `ViewModel`, rendered by a URP overlay camera stacked on `MainCamera` (never clips: see
`native-after/fp-wall-*.png` against the Warden post container). Hip and aim-down-sights poses, look sway, walk bob,
recoil kick, draw/holster slide, reduced-motion aware; hidden when holstered, inside Ward, and outside Play. The overlay
camera is enabled only while the view model is visible. `MuzzleFlash` cards (procedural star, additive HDR cyan-white)
fire in both views; the tracer starts at the first-person muzzle.

Also fixed: entering aim locked the cursor and the recentring was read as one large mouse delta (the camera snapped to
look at the ground in the baseline too); `FollowCamera` now ignores look input for two frames after entering aim.

## 5. Gunshots

Before: one clip, ±5 % pitch, played through the **UI** mixer group.

After (`unity/tools/generate_pistol_audio.py`, 25 ElevenLabs takes): 6 mechanical snaps + 6 nano-crack/thump bodies + 6
desert slapback tails, combined at random without repeats; closer and drier in first person or aiming (mechanism ×1.15,
tail ×0.7); tail on its own 2D source; 3 empty clicks, 2 draw, 2 holster. A tanh "glue" stage levels each layer's variants
to within ~1.5 dB (they came back 12 dB apart). Layer gains put the worst-case aligned sum of the loudest variants at
−1.5 dBFS. Weapon audio now routes to the **SFX** group.

Recorded (desktop audio, whole segments including ambience):

| Segment | Before | After |
| --- | --- | --- |
| Third person: 4 aimed + 3 hip + 8 rapid | −22.2 LUFS, peak −4.0 dBTP | −19.2 LUFS, peak −1.6 dBTP |
| First person: 4 aimed + 3 hip + walk | −23.0 LUFS, peak −4.1 dBTP | −16.6 LUFS, peak −1.5 dBTP |

No clipping on rapid fire at the 0.28 s interval. The shot is louder and fuller than before by design; it can be trimmed
with `PlayerCombat.mechGain/bodyGain/tailGain` if it sits too hot against music.

## Performance (final build)

| Route | Avg fps | p50 ms | p95 ms | p99 ms | Max ms | >50 ms | Previous (handover) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Checkpoint route | 212.8 | 3.84 | 14.52 | 17.42 | 19.33 | 0 | 213.7 fps, p99 16.71–16.99 ms |
| Depot walk (warmed) | 171.5 | 4.87 | 14.51 | 16.59 | 20.66 | 0 | p99 16.00 ms |
| Depot fight | 151.9 | 6.36 | 8.47 | 9.63 | 12.25 | 0 | — |

Against the last pass the checkpoint route is about the same on average (212.8 vs 213.7 fps) but p99 is 0.4–0.7 ms
worse (17.42 vs 16.71–16.99 ms); the warmed depot walk is 0.6 ms worse at p99 (16.59 vs 16.00 ms). No hitches over 50 ms
anywhere. Run-to-run spread is real: an earlier run of this pass measured the checkpoint route at 207.4 fps / p99 17.12 ms,
and one before that (overlay camera always on) at 193.8 fps / p99 17.5 ms, after which the overlay camera was changed to
run only while the view model is visible. Likely remaining costs: six head look-at solves, the extra upper-body layer and
the footstep raycast (all small). The 16.67 ms p99 target is missed on both routes; judged leniently per Carl (low-end GPU,
development game) and left for a dedicated frame-time pass.

## Credits and provenance

- Meshy: guard re-rig `01a0e213-0645-7031-9f0d-71d75d08f0b5` (5) + 10 animations (30); player re-rig
  `01a0e226-5a19-7367-ae56-4501b38999bf` (5) + 10 animations (30). **70 credits**, preapproved (AGENTS.md §5).
  Library previews and the catalogue are in `meshy/character-feel-20260927/`.
- ElevenLabs `eleven_text_to_sound_v2`: 71 generations, 2,083 characters billed; requests, response ids and hashes beside
  each source in `unity/staging/elevenlabs-audio/{footsteps,pistol}/`.

## Remaining defects (honest list)

- Third-person aim from directly behind: the raised pistol is mostly hidden by the torso; a wider `aimShoulder`
  (0.55 → ~0.75) would show it but changes camera feel, so it is left for review.
- The first-person hands come from the 20k-triangle colonist: fingers are faceted and slightly large close up. A
  dedicated FP arms mesh would be the next quality step.
- The pistol hold is a static frame; it breathes only through sway/bob. No reload.
- Strafe and backpedal while aiming still use the forward walk legs (library "walk left/back with gun" are retargeted
  but not wired); no turn-in-place yet (clips retargeted, not wired). No draw/holster body animation (the view model and
  aim layer blend in instead).
- Worker droid idle/hit clips were not revisited.
- Footsteps: metal landing has 2 variants; foot contact uses a bone-height threshold, so a very slow shuffle can skip a
  step. NPC footsteps not added.
- Guard audition renders in the Editor need `SkinnedMeshRenderer.forceMatrixRecalculationPerRender` or off-screen
  renders show a stale pose (used for all pose checks here; noted for future passes).
- Decisions still with Carl: texture streaming stays on (rollback copy in `outer-berms-depot/20260927`); frame-time target
  judged leniently per his instruction.
