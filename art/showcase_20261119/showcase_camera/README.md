# Showcase camera: conversation camera and photo mode (19 November 2026)

Gap 3 of the showcase programme: conversations were framed by wherever the follow camera happened to be, and there
was no way to take clean stills for the promo site and trailer.

**Status: code written and compile-checked only.** `unity/tools/compile_check.py` passes for Runtime, Editor and Edit
Mode tests. Unity has not run: the installer has not been applied to the scene, the Edit Mode tests have not been
executed, and nothing here has been seen on screen. Not accepted by Carl.

## What changed

### Conversation camera

- When a dialogue opens, the gameplay pose eases (0.6 s, smoothstep, unscaled time) to an over-the-shoulder shot:
  the NPC's head lands on the right third (x 0.667, y 0.64) over the player's right shoulder, or the left third over
  the left shoulder. The shoulder is the side the gameplay camera was already on; if that side is walled in and the
  other is clear, it swaps. The sideways offset is solved so the player's head sits near x 0.3 (it is capped at
  0.65 m); the rotation is solved exactly for the thirds point, with no roll.
- The camera looks at the NPC's head bone (`ActorLookAt.head`, else a bone named `Head`, else root + 1.6 m), smoothed
  over 0.25 s so the talk animation's head sway does not shake the frame.
- Obstruction: the lens is swept (radius 0.18 m) from the player's head to the shot position against
  `FollowCamera.worldMask` and pulled in short of anything hit. The eased in-between positions are swept again, so a
  blend never cuts a corner. If the clear distance is under 0.35 m, or the lens would come within 0.5 m of the NPC's
  head, it falls back to the player's eye line (NPC centred, body hidden as in first person).
- Lens: 40° vertical field of view, blended with the gameplay lens.
- Depth of field: a transient global URP Volume (priority 1000, created at runtime, destroyed when the blend ends; the
  saved grade `WardDustbowlGrade.asset` and the clock's runtime profile are not touched). Bokeh, f/5.6, 50 mm, focus
  on the NPC's head. It blends in through the aperture (f/32 to f/5.6) with the focus already on the NPC, so the subject
  never drifts out of focus.
- First person (including the container home's confined view): the view stays where it is; only the depth of field
  is added.
- Reduced Motion: cuts in and out instead of easing.
- Restore: the conversation camera never writes FollowCamera's yaw, pitch, boom, zoom or recoil. It only overlays the
  pose FollowCamera is about to write. At weight 0 the overlay code is skipped and the lens logic is the old one, so
  the gameplay camera is exactly as before the dialogue.
- Not applied while a review camera (`FollowCamera.FixedView`, QA `view`) is active.
- Switches: serialized `ConversationCamera.framingEnabled` and the static `ConversationCamera.Enabled` (both must be
  on). **A Settings toggle can set `ConversationCamera.Enabled`.** GameSettings/SettingsPanel belong to another agent
  and were not changed.

### Photo mode (P)

- **P** in plain play (no dialogue, window, pause, review camera or developer menu). P was free in
  `Controls.inputactions` and `unity/README.md`.
- Freezes the game (`Time.timeScale = 0`); everything in photo mode runs on unscaled time. GameSession's own key
  handling (Tab, J, Esc, notice timers) is skipped while it is open, so it cannot open the pack or pause.
- Free camera from the current view: WASD (forward follows the view pitch), Space/E rise, C/Q fall, Shift ×4, Ctrl
  ×0.25, mouse look (Settings sensitivity and invert), wheel = field of view. It stays within 15 m of the colonist's
  head and is swept against the world (radius 0.2 m, one slide), so it cannot pass through walls, roofs or the ground.
- Panel (UI Toolkit, hosted in the HUD's document, bronze frame and button art from CityHUD.uss, cyan selected row),
  fully keyboard-operable: ↑↓ choose, ←→ adjust (Shift ×5), Enter toggles or activates. Rows: Field of view (15–90°),
  Roll (±45°), Depth of field (On/Off), Focus distance (0.3–80 m), Aperture (f/1.4–f/22), Exposure (±3 EV, added to
  the time-of-day exposure), Time of day (through `CityTimeOfDay.SetHour`), Colonist (shown/hidden), Interface
  (hidden by default), Capture, Exit. H hides the panel, R resets the view, hold Left Alt for the pointer (sliders and
  buttons work with the mouse).
- Depth of field and exposure use a second transient volume (priority 1001). The photo lens focal length follows the
  field of view (full-frame equivalent), so zooming in gives shallower focus.
- Capture (F12, left click with the cursor locked, or the Capture row): hides the panel and interface for one frame,
  saves the screen as `~/Pictures/Ashfall/Ashfall_yyyyMMdd_HHmmss.png`, then renders the camera again at 2× the window
  size through a URP render request and saves `…_2x.png`. PNG encoding and writing run on a worker thread; the panel
  shows the saved path. Names never overwrite (`-2`, `-3` …).
- Overlay cameras (first-person arms) are taken out of the camera stack while open, so they do not float in front of
  the free camera.
- P, Esc or the Exit row close it. Restored in reverse order: panel, interface (then `CityHud.Refresh`), volume, time of
  day, colonist renderers, overlay camera stack, camera pose and lens, input map and cursor lock, time scale. If
  something else leaves Play while it is open (developer time menu, a pause click), it closes itself and leaves the
  time scale to the new state. It never saves the game or touches quest state.

### Camera shake hook

`CinematicCamera.UnderControl` (static, `Scripts/Camera/CinematicCamera.cs`) is true while photo mode is open or the
conversation camera is engaged (including the first-person depth-of-field case). Additive effects such as
`CameraImpulse` should skip their offset while it is true. FollowCamera still writes an absolute pose every frame
outside photo mode.

## Files

New:
- `unity/AthenHill/Assets/AthenHill/Scripts/Camera/CinematicCamera.cs`: the static ownership flag.
- `…/Scripts/Camera/ConversationFraming.cs`: pure framing maths (side, shoulder offset, exact thirds aim, pull-in,
  blend step, focal length).
- `…/Scripts/Camera/ConversationCamera.cs`: the conversation component.
- `…/Scripts/Camera/TransientVolume.cs`: runtime-only global volume with its own profile.
- `…/Scripts/Camera/PhotoMode.cs`, `PhotoModeModel.cs` (controls, flight maths, file names, restore ledger, camera
  state), `ShowcaseQa.cs` (QA state and commands).
- `unity/AthenHill/Assets/AthenHill/UI/PhotoMode.uxml`, `PhotoMode.uss`.
- `unity/AthenHill/Assets/AthenHill/Editor/ShowcaseCameraInstall20261119.cs`: installer.
- `unity/AthenHill/Assets/AthenHill/Tests/Editor/ShowcaseCameraTests.cs`: 14 Edit Mode tests (18 cases).

Changed:
- `Scripts/FollowCamera.cs`: `conversation`/`photo` references (found on the same object when empty); skips
  everything while photo mode is open; hands the finished pose to `ConversationCamera.Compose`; lens logic now also
  holds the lens during a conversation; `ShowPlayerForPhoto()`. Behaviour with no conversation is unchanged.
- `Scripts/GameInput.cs`: Photo action map (`PhotoEnabled`, `PhotoHeld/Pressed/Move/Look/Zoom/Device`, `SetPhoto`);
  the cursor stays locked in photo mode; `Cancel` is withheld while photo mode is open and on the frame it closes.
  Gameplay behaviour is unchanged.
- `Data/Controls.inputactions`: Gameplay action `PhotoMode` on P; new `Photo` map. Existing action ids kept.
- Shared, additive: `Scripts/GameSession.cs` (one line: `Update` returns while `PhotoMode.Active`),
  `Scripts/NativeQa.cs` (snapshot key `showcase`; commands `photoMode {open}`, `photoCapture`,
  `conversationCamera {enabled}`), `unity/README.md` (two control rows).

## Install

Close the Editor first (one Unity job at a time, memory-capped scope):

```
unity.sh LOG AthenHill.Editor.ShowcaseCameraInstall20261119.RunBatch --steps install,verify -nographics
```

`install` adds `ConversationCamera` and `PhotoMode` to the object with the single `FollowCamera` (only if missing),
wires them, and saves the scene (a copy goes to `unity/evidence/showcase-camera/20261119/rollback/` the first time).
`verify` writes `unity/evidence/showcase-camera/20261119/verify.json` and fails on any missing wiring or input action.
Menu items: Athen Hill › Showcase camera › Install / Verify / Uninstall.

Then run the Edit Mode tests (`ShowcaseCameraTests`) and build the development player.

## Native test plan (real input, development build)

Snapshot keys below are in `snapshot.json` → `showcase`.

1. **Regression first**: city loop and the mouse-look check unchanged (`check_mouse_look_native.py`); outside dialogue
   `showcase.cinematic` stays false and `camera.*` matches the previous build.
2. **Conversation, third person**: walk to Mira at the default boom, press E. Expect `conversation.active` true,
   `framing` true, `weight` 1 after about 0.6 s, the NPC's head on the right (or left) third in a capture, the
   player's shoulder in the foreground, mild background blur, `camera.overlaps` empty. Close with Esc: the camera eases
   back and `camera.yaw/pitch/boom/position` equal the values before E (within 1 mm), `conversation.weight` 0, no
   `Conversation depth of field` object left in the scene.
3. **Tight spaces**: talk to Brann across the Salvage counter and Tamsin in Field Supply from several angles,
   including backed against a wall. Expect no overlaps, `eyeLine` true only when the shoulder shot cannot fit.
4. **First person**: wheel into first person, talk to Vex. Expect the view unchanged, `framing` false, `active` true
   (depth of field only).
5. **Reduced Motion on**: repeat 2; the framing cuts in and out on the E and Esc frames.
6. **Switch**: `conversationCamera {enabled:false}`; repeat 2; the camera stays where it was.
7. **Photo mode**: press P in the city. Expect `photo.active` true, `timeScale` 0, NPCs and walkers frozen, HUD hidden,
   panel shown, cursor locked. Fly with WASD/Space/C, look around, try to fly through a shop wall, under the paving and
   beyond 15 m: the camera stops. ↑↓/←→ over every row; check DOF, exposure and time of day change the image.
8. **Capture**: press F12. Expect two files in `~/Pictures/Ashfall/` (1920×1080 and 3840×2160), opaque, upright, with
   no HUD or panel, and the status line showing the path; `photo.lastCapture` and `lastSupersampled` set.
9. **Exit and restore**: press P (and separately Esc). Expect `timeScale` 1, the camera back on the follow pose, the
   clock hour as before, HUD back, cursor locked, `session.state` Play (Esc must not open the pause menu).
10. **Refusals**: P in dialogue, the pack, the journal, the pause menu: nothing happens. F8 (developer time menu) while
    in photo mode: photo mode closes, the game stays paused by the menu.
11. **Container home**: open photo mode inside the home and fly out through the door; close and check first person is
    held again inside.
12. **Performance**: frame time during a conversation with Bokeh on, against the previous build (expect a small DOF
    cost only while talking); capture hitch is acceptable while paused.

## Rollback

`--steps uninstall` removes the two components and clears FollowCamera's references; with them gone the code paths
do nothing. Revert the files listed above with git for a full rollback. The scene copy from the first install is in
`unity/evidence/showcase-camera/20261119/rollback/`.

## Known risks and open questions

- **The dialogue window covers the shot.** The dialogue is the centred 860 px modal over a 66 % dark shade, so the
  NPC's face on the right third sits under the window and is dimmed. The framing will only read if the dialogue becomes
  a lower-third panel without the full-screen shade (CityHUD.uxml/.uss, not owned by this package). Carl's decision.
- The supersampled copy is rendered through `RenderPipeline.SubmitRenderRequest` at a new resolution, so TAA has no
  history for it; it may be slightly less clean than the 1x screen grab. It also briefly needs about 4K-sized URP
  buffers (a few hundred MB of VRAM).
- `ImageConversion.EncodeArrayToPNG` on raw texture bytes is assumed to give the same orientation as `EncodeToPNG`.
  Check that test 8's images are upright.
- Bokeh depth of field at 1080p on the RTX 3060 costs frame time during conversations; `depthOfFieldMode` can be set
  to Gaussian (background only, cheaper) or `depthOfField` off.
- QA scripts that capture the follow camera during a dialogue (not the fixed review cameras) will now see the
  conversation framing; use `conversationCamera {enabled:false}` for those runs.
- `NativeQa`'s `ui-layout.json` now lists the photo panel's elements (hidden unless photo mode is open).
- Other camera writers that run in LateUpdate after FollowCamera (none found besides the new `CameraImpulse`) would
  need to respect `CinematicCamera.UnderControl`.

## Native QA fixes (19 Nov 2026, build batch-qa2 onward)

- **Mira's (and Torr's) shoulder shot showed only the player's shoulder.** Symptom: across Mira's counter the frame was
  filled by the colonist's back and arm and Mira was not visible; by Torr's slab the back of the head covered half the
  frame. Cause: the obstruction sweep pulled the lens in toward the player's head but the fallback only triggered under
  0.35 m, so a lens pulled in to roughly a third of its 0.95 m shot sat right behind the shoulder (the player's own body
  is not in `worldMask`). Fix: `ConversationFraming.TooTight` and `ConversationCamera.minShotFraction` (0.75): a shot
  pulled in to less than three quarters of its full distance uses the eye-line fallback. `showcase.conversation.shotFraction`
  reports the share left after the sweep. Edit Mode test `APulledInShoulderShotFallsBackToTheEyeLine`.
- **Photo mode opened from first person looked at the inside of the colonist's face** (container home, or wheeled into
  first person): the free camera starts at the first-person eye and the Colonist row defaulted to Shown. `PhotoMode.Open`
  now starts with the colonist hidden when it opens from first person; the Colonist row still shows it.
- **The colonist did not face the NPC.** With Brann, Ossa and Rell the shot showed the colonist's face large in the
  foreground; with Vex and Linn a profile. `ConversationCamera.Compose` now sets `PlayerMotor.TalkYaw` (new, additive:
  the motor's own facing, eased at `talkTurnRate` 10/s ≈ 0.3 s, cut under Reduced Motion through `TalkYawSnap`) to face
  the NPC while the dialogue is open and releases it on close or Suspend; nothing in first person. The follow camera's
  yaw/pitch/boom/position still come back exactly (the colonist may stay turned). Test `TheColonistTurnsToFaceTheNpc`.
- **The shoulder filled about half the frame.** `Shot.Default` re-tuned (back 0.7 → 1.25 m, height 0.02 → 0.05, shoulder
  limit 0.65 → 0.75 m, player at x 0.27): the colonist's back and helmet now take about a third of the width. New installer
  step `--steps shot` writes the default onto the scene's ConversationCamera (run 19 Nov 15:35; overwrites Inspector tuning).
- **Standing at Mira's counter the NPC was behind the player's own head**, and the eye-line fallback then sat a few
  decimetres from her face. New `minSeparation` (1.2 m, `ConversationFraming.TooClose`): closer than that the eye line is
  used; on the eye line the lens steps back along the NPC-to-player line to `eyeLineDistance` (1.3 m), swept. Test
  `StandingRightAtTheNpcUsesTheEyeLine`.
- Native result (batch-qa5, `check_showcase_camera.py` 97/97): all eight colonists frame with the NPC's face on its third
  and the player's back about a third of the width; captures in unity/evidence/showcase/20261119/qa/p5/camera/run/.
- **Spoken to from behind, the NPC kept its back to the camera** (Vex walk-up from the south). `NpcAgent.faceSpeaker`
  (shared file, additive; on by default): while a dialogue with the colonist is open its visual (the ActorLookAt
  transform) turns about world up to face the player at `faceTurnRate` 6/s (cut under Reduced Motion) and eases back to
  its authored facing afterwards; colliders and roots do not move. Torr now faces the player from the mission slab.
- Final (batch-showcase-qa, 16:56, `check_showcase_camera.py` 99/99 incl. walk-ups to Vex from his east and south
  sides): captures in unity/evidence/showcase/20261119/qa/final2/camera/run/.
