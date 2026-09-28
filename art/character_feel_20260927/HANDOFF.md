# Handover — character animation, footsteps, first-person weapon, gunshots (27 Sep 2026)

## Request (Carl, verbatim)

> areas of focus are character aminations. rebuild the cars if needed. the wardens look "shifty" constantly peering
> around as in a state of paranoid delusionment. the main character footsteps are loud annoying and dont sound real.
> use elevenlabs if required. FPS we should be able to see the weapon when fireing and aim. better gun shot sounds.

"Rebuild the cars" is read as **rebuild the characters** (chars) where a model cannot reach the animation quality
bar. If Carl meant vehicles (the Karaveen truck), treat that as out of scope and ask. **ElevenLabs is now authorised**
for this workstream (as Meshy already is). OpenAI image generation is available for references. Keys are in the
project-root `.env`: MESHY_API_KEY, ELEVENLABS_API_KEY, OPENAI_API_KEY. Never print them.

The quality bar is AAA. Judge everything in the native build, at player height, in motion, with audio on.

## Read first

1. `AGENTS.md`: project rules, character and animation requirements, evidence and performance rules.
2. `unity/MESHY_PLAYER.md`, `docs/model-import.md`, `meshy/ward-guard/README.md`, `unity/AUDIO.md`.
3. The last two passes, for the toolchain and verification pattern:
   - `unity/evidence/west-gate/20260926/README.md`
   - `unity/evidence/outer-berms-depot/20260927/README.md`
4. `art/outer_berms_depot_20260927/BRIEF.md` → "Reusable toolchain" and "Hard-won pitfalls". They all still apply:
   - Close the Unity Editor before native runs.
   - The native checks release stuck XTEST keys before driving input.
   - Use `unity/tools/unity_exec.py` and `unity/tools/editor_capture.py` for Editor work and captures.
   - Blender 5.2 runs headless (`blender -b -P`).

Keep a log in `art/character_feel_20260927/PROGRESS.md`: append after every milestone with time, change, files,
what was verified and what's next. Evidence goes under `unity/evidence/character-feel/20260927/`. Preserve unrelated
dirty work. Do not commit. Nothing below changes gameplay rules, IDs, dialogue or routes.

## Pending decisions from the overnight pass (flag in the morning report, don't undo)

- **Texture mip streaming** (PC quality, 4096 MB budget) was switched on by the depot session to stop GPU memory
  exhaustion (8.35 GB → ~4.2 GB textures). It is awaiting Carl's review; the rollback copy is
  `unity/evidence/outer-berms-depot/20260927/QualitySettings-before-streaming.asset`.
- **Checkpoint route p99 is 16.71–16.99 ms** against the 16.67 ms target. The slow frames face east into the city.
  Anything added here (a first-person overlay camera, extra animation layers, more audio voices) must be measured
  on that route and the depot route.

---

## 1. Wardens look "shifty" (constant peering)

**Cause.** `Prefabs/WardGuard.prefab` → `ActorAnimation.idle` = `Art/CharacterMotion/Guard/idle_meshy.anim` (GUID
f6c33d79…). That is the Meshy library idle, which scans head and torso continuously. The same prefab drives **all six**
guard-model characters: the Wardens Ossa and Rell, and the four city colonists Mira, Torr, Vex and Linn. They loop in
sync-ish phase, so the whole cast reads as paranoid. `Guard/idle.anim` (non-Meshy) also exists; audition it before
authoring anything new. `ActorAnimation` plays legacy `Animation` clips (idle/walk/run/talk, crossfades; see
`Scripts/ActorAnimation.cs`).

**Plan.**
- Build a calm **"at ease" Warden idle**: planted feet, slow breathing, a small weight shift, hands resting on the
  belt or crossed. At most one deliberate slow head turn every 10–20 s. Options, in order of preference:
  1. The Meshy animation library on the guard's rig. The API pattern is `meshy/outer-berms-20260926/rig_and_animate.py`:
     `GET /openapi/v1/animations/library`, `POST /rigging`, `POST /animations` with an `action_id`. Search for
     standing, guard, relaxed or breathing idles. The rig must match the imported guard skeleton or be retargeted in
     Blender. Record every task id, option and credit spent in `meshy/character-feel-20260927/`.
  2. Author in Blender on the existing armature: breathing, weight shift and head keys, 8–12 s, seamless loop.
  3. A mocap BVH retargeted in Blender, only with a clear licence (CMU mocap is free to use; note its terms).
- Add **variation** so guards never move in sync: a per-instance random start time and a ±8 % speed jitter
  (serialized on `ActorAnimation` or an `IdleVariation` component).
- Optional: a small head look-at toward the player within ~4 m, clamped to ±45° yaw and ±15° pitch, eased and applied
  in LateUpdate after the legacy animation samples. The Wardens should acknowledge you, not scan the horizon.
- Give the Wardens a Warden-specific idle first, then audition the same idle (or a civilian variant) on the four
  colonists. The user complained about the Wardens, but the colonists share the problem. Capture before and after
  for all six.
- Check the talk clip for the same scanning problem.

**Accept when** a 30 s native video of each Warden shows no continuous scanning and a believable breathing, weight-
shifting stance, with no foot sliding, arm intersection or popping at crossfades.

## 2. Character animation generally (and rebuild characters if needed)

**Current state and known gaps.**
- **Player** (`meshy/mpc`, see `unity/MESHY_PLAYER.md`): walk and run come from Meshy. The idle and talk are the
  single-frame static source pose. There are jump clips. There is **no aim, fire, draw, holster, strafe or
  turn-in-place** animation; the Berms pass noted "no aim/shoot pose".
- **Worker droid:** Meshy library humanoid clips. The idle is a combat stance, the punch is sped up, the hit sways
  ~0.5 m, and there is no turn-in-place.
- **Ambient walkers:** a traveler model with a supplied walk.

**Plan.**
- Priority order:
  1. Player breathing idle.
  2. Player pistol aim pose as an upper-body layer, used by §4.
  3. Fire recoil additive.
  4. Draw and holster.
  5. Walk and strafe while aiming, with backpedal.
  6. Turn-in-place.
  7. Worker droid idle and hit fixes.
- Legacy `Animation` supports upper-body layering. Use `AnimationState.AddMixingTransform(spine)` on a higher layer,
  so the aim pose rides on top of walk and run without a full Animator migration. If an Animator migration is truly
  needed, justify it in PROGRESS and keep every current state working.
- Check stride speeds against clip foot speed (`walkStrideSpeed`/`runStrideSpeed`) for foot sliding, and check blend
  times at every transition in a slow-motion capture.
- **Rebuild a character** only if its rig, topology or bind pose blocks the quality bar. For example, the guard's
  arms-at-sides source pose, or bad deformation at shoulders and hips. Use Meshy (image or text to 3D → rig →
  animate) with a front/side/back reference. Audition it next to the current model, keep roles, prefab roots,
  NpcAgent and dialogue data, and keep the previous model inactive for rollback, following the character steps in
  AGENTS.md §5.

**Accept when** native captures and slow-motion video show idle, walk, run, jump, aim, fire, draw and holster with
clean contacts and transitions. Check player face and full body in sun and shade.

## 3. Player footsteps are loud, annoying and unreal

**Cause** (`Scripts/CityAudio.cs`, lines ~115–125):
- Three clips (`Audio/ElevenLabs/stone-step-01..03.wav`) cycle in a **fixed order**.
- Pitch only alternates 0.97/1.03, with no volume variation.
- Cadence is distance-based (`walkStepDistance` .95 m, `runStepDistance` 1.45 m), so steps don't line up with foot
  contacts.
- The same stone sound plays on sand, gravel, concrete and steel plate.
- The level is too high for a sound that repeats every ~0.3 s.

**Plan.**
- Generate new sets with ElevenLabs. The pipeline pattern is `unity/tools/generate_berms_combat_audio.py`
  (`eleven_text_to_sound_v2`; staging and manifests in `unity/staging/elevenlabs-audio/`).
  - Surfaces: sandstone paving, packed sand and fine gravel (Berms), concrete apron, steel plate/threshold/grating,
    plywood or wood.
  - Separate walk and run sets, **8+ variants each**, plus jump-landing sets.
  - Make them short and dry, with a soft boot on grit, not a clatter. Add a very quiet gear/cloth rustle layer.
  - Trim silence, normalise loudness per set, and record LUFS and peaks.
- **Surface detection:** raycast under the player's feet and map colliders or materials to a surface. On the Berms
  ground, sample the CPU-readable splat (`Art/WestGate/Ground/BermsGroundSplat.png`: R gravel road, G sand, B crust,
  A compaction) to choose sand or gravel. The apron and threshold are concrete or steel.
- **Timing:** trigger on foot contact. Use animation events on the walk and run clips, or a foot-bone height crossing,
  rather than distance.
- **Variation:** random selection that never repeats, pitch ±5 %, volume ±2 dB.
- **Mix:** bring the player's footsteps down clearly, starting around −10 dB from the current level and tuning by ear
  against music and ambience. Make them near-field spatial at the feet, and quieter in first person and while aiming.
  Keep the mute and reduced-motion behaviour.
- NPC footsteps are optional: spatial, quieter, same system.

**Accept when** you have a recorded native walk and run over paving → gate threshold → apron → Berms sand/gravel →
depot concrete, with audio. Record LUFS numbers before and after in the evidence. Nothing should sound machine-gunned
or repeat audibly.

## 4. First person: see the weapon when firing and aiming

**Cause:**
- `FollowCamera.HidePlayer` switches every player renderer to ShadowsOnly when the camera is closer than 0.65 m. That
  hides the hand-held pistol (`PlayerCombat.heldPistol`, parented to the hand bone) in first person.
- In third-person aim (RMB), the colonist has no aim pose, so the pistol hangs at the side, out of view.
- The shot is presented only as a point light plus a LineRenderer tracer from `muzzleOffset`/`muzzlePoint`, and there
  is no recoil.

**Plan.**
- **First-person viewmodel:**
  - Build gloved arms (split from the player mesh, or a dedicated FP-arms mesh made with Meshy or Blender) holding
    `Art/OuterBerms/ScrapPistol.glb`, parented to the view.
  - Render it on its own layer with a URP overlay camera (camera stacking) at its own FOV (~55–60°), so it never
    clips into walls and keeps a stable screen size.
  - States: idle sway and bob from player speed, ADS (RMB moves the weapon to the centre and narrows FOV slightly),
    fire (recoil kick and recover, slide or actuator motion, muzzle flash sprite or mesh, light, nano-vent particles),
    draw and holster (slot 7), empty/low-nano click.
  - Reduced Motion disables bob and sway.
  - Hide the viewmodel when holstered, inside Ward, and in dialogue, shop or pause.
- **Third-person aim:** use the §2 upper-body aim layer so the pistol is raised along the aim line and visible over
  the shoulder. The muzzle flash and tracer should start at the real `muzzlePoint` on the drawn pistol in both views.
- **Crosshair and HUD:** check `CombatHud` for hip-fire versus ADS, and hit-marker timing with the new recoil.
- **Keep working:** the aim assist, `fireInterval`, nano costs, the tutorial steps, the holster-inside-Ward rule and
  the native check steps (plates are shot from fixed cameras with F).

**Accept when** native first- and third-person captures show the weapon at the fire frame and while aiming, video
shows a readable recoil and flash, and there's no clipping against the gate piers or container walls at 0.3 m. The
overlay camera's cost is measured on both routes.

## 5. Better gunshot sounds

**Cause:** a single `Audio/ElevenLabs/Combat/scrap-pistol-shot.wav` with ±5 % pitch. It has no layers, variants,
tail or perspective.

**Plan.**
- Design the scrap/nano pistol as three ElevenLabs layers:
  1. A sharp mechanical transient: actuator snap and slide.
  2. A body: nano-charge discharge crack with a low thump.
  3. An outdoor desert tail: slapback echo off the wall and berms.
- Make 5–6 variants per layer, randomly combined, with first-person or aim (closer, drier, wider) and third-person
  perspectives.
- Also make empty/low-nano clicks, draw and holster foley, and shell or nano-vent tinkles if the viewmodel ejects
  anything. Match the droid-hit and plate-clang impacts to the new shot loudness.
- Keep the SFX mixer group, mute and duck behaviour. Check for clipping on rapid fire at `fireInterval` .28 s with
  voice limits.

**Accept when** an A/B recording of old versus new (single shots, rapid fire, at the range and inside the depot) is in
the evidence, and there's no clipping.

---

## Verification (all required before reporting)

- **Edit Mode tests:** currently 61. Add tests for the new components' serialized wiring (idle variation,
  footstep surface map, viewmodel references).
- **Builds:** Linux development and release players, 0 errors (menu `Athen Hill/Build/…` via delayCall; result in
  `unity/AthenHill/Captures/linux-build.json`).
- **Native checks, with the Editor closed:**
  - `unity/tools/check_checkpoint.py` (10 checks, including the city loop).
  - `unity/tools/check_depot.py`.
  - A new check that walks the surface route with audio capture, draws the pistol, enters first person, aims and
    fires at a plate, and asserts that the viewmodel is visible, the pistol is holstered inside Ward, and there are
    no exceptions.
- **Performance:** measure the checkpoint and depot routes. Report avg, p50, p95, p99 and max honestly, next to the
  last numbers:
  - checkpoint: 213.7 fps avg, p99 16.71 ms
  - depot walk: p99 16.00 ms
- **Evidence:** before/after videos with audio, captures, loudness numbers, task and credit records, and an honest
  remaining-defects list in `unity/evidence/character-feel/20260927/README.md`.

## Suggested order

1. Baseline: native video with audio of the Wardens idling, the player walking every surface, and first- and
   third-person aim/fire. Measure loudness.
2. Warden idle fix (smallest change, most visible complaint).
3. Footstep system and new sets.
4. Gunshot layers.
5. Player aim/fire upper-body layer, then the first-person viewmodel.
6. Remaining animation work (player idle, strafe, turn-in-place, droid clips) and any character rebuild.
7. Full verification and report.
