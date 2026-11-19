# Interface: conversation lower third, Settings toggles, adaptive HUD (19 November 2026)

Gap 9 of the showcase programme (four corner panels plus banners cover much of a 1080p frame) and the follow-ups the
showcase camera and NPC life packages left open: the new conversation camera could not be seen behind the centred
dialogue window and its 66 % shade, and neither it nor bark captions had a Settings control.

**Status: code written and compile-checked only.** `unity/tools/compile_check.py` passes for Runtime, Editor and Edit
Mode tests. Unity has not run: the Edit Mode tests have not been executed, UXML/USS have not been loaded, and nothing
here has been seen on screen. Not accepted by Carl. No scene, prefab or asset change, so there is no installer.

## What changed

### Dialogue lower third

- `DialogueLayoutRule` (pure) picks the layout. Centred (today's window, unchanged) when the conversation camera is
  off (`ConversationCamera.Enabled`, the component or its `framingEnabled`), photo mode is open, a review camera owns
  the view (`FollowCamera.FixedView`), or the camera is engaged but not framing (first person: depth of field only).
  Lower third when the camera is engaged and framing (shoulder shot or its eye-line fallback). The camera decides first
  person in its own LateUpdate after the dialogue opens, so for the first 0.25 s the HUD predicts from
  `FollowCamera.FirstPerson`; a camera that has not engaged by then counts as not framing.
- `CityHud` puts the class `dialogue-lower-third` on `#shade`; USS does the rest. No shade colour; the modal sits at the
  bottom centre, 1240 px (≤ 94 %, 1100 compact), ≤ 42 % high, 24 px above the edge. Heading = name plate (name in
  capitals, role · topic in bronze), line on the left, YOUR RESPONSE and the three response buttons in a 470 px column
  on the right, footer hidden, long lines scroll within 250 px. The modal's opaque enamel is the backing.
- The UXML gained two plain wrappers inside `#dialogue-panel` (`dialogue-line`, `dialogue-responses`) so the lower
  third can set them side by side. No name was renamed; the centred window lays out exactly as before.
- While the lower third is up the event log, key hints and hotbar fade out (opacity, then `visibility: hidden`) and come
  back afterwards, in Full and Adaptive. Identity, compass and Field Notes stay.
- The dialogue modal is draggable; `HudWindowLayout.Hold` keeps it at its authored place in the lower third (no saved
  offset, no drag) and restores the player's saved placement for the next centred window.
- Keyboard and mouse, voices, branches, `choice0–2`, focus and Tab cycling are the same code paths as before.

### Settings

- Sound › Accessibility: **Bark captions** reads and writes `BarkDirector.CaptionsEnabled` (which saves itself under
  `AthenHill.Settings.v1.BarkCaptions`).
- Controls › Camera and interface: **Conversation camera** (on by default) and **Interface: Full / Adaptive** (Full by
  default). Saved as JSON under `AthenHill.Settings.v1.Interface` (QA prefix under `--athen-qa`) like Controls; a
  missing key or field keeps the defaults; an unknown mode reads as Full. `GameSettings` sets
  `ConversationCamera.Enabled` on Awake and on every save. **Reset controls** now also resets these two.
- The combat feedback rows (Camera shake, Hit markers and ticks) are untouched.

### Adaptive HUD

- `AdaptiveHudModel` (pure, serialized on `CityHud.adaptive`): quiet 6 s, fade out 0.6 s, in 0.2 s (Inspector).
  Panels: identity (`#identity`), Field Notes (`#objective-box` + `#top-actions`), log (`#chat`), key hints
  (`#key-hints`); the hotbar (`#quickbar`) only gives way to the lower third.
- Wakes: identity on a whole-number change of vitality or nano; Field Notes when the objective title, instruction,
  progress or credits text changes; log on a new line; key hints while a prompt is offered. Holds (every panel, quiet
  time restarts when they end): any window open, combat (weapon drawn or hurt in the last `hurtHoldSeconds` = 6 s),
  Left Alt (`GameInput.CursorFreed`).
- Opacity steps in `CityHud.LateUpdate`; at full opacity the inline styles are cleared, so Full mode is the authored
  HUD. Reduced Motion cuts.
- Radio and notices: already at most two deep (RadioQueue shows one line at a time, the notice is one replaceable
  slot placed under it). No code was needed; the dev bridge reports the depth.

### Dev bridge

`snapshot.json` → `hud`: `dialogueLayout` (`none` / `centred` / `lowerThird`), `shadeDimmed`, `modalHeld`,
`interfaceMode` (`full` / `adaptive`), `conversationCamera` (static), `conversationCameraSetting`, `barkCaptions`,
`hidden` (panel ids below 0.001 opacity: `identity`, `fieldNotes`, `log`, `keyHints`, `hotbar`), `opacity` (per id),
`quietSeconds`, `topCentre {radio, notice, depth}`.
Command `interfaceMode {mode: "full" | "adaptive"}` (saved under the QA prefix). Existing `conversationCamera {enabled}`
and `barkCaptions {on}` set the statics directly (not the saved setting).

## Files

New:
- `unity/AthenHill/Assets/AthenHill/Scripts/HudPresentation.cs`: `DialogueLayout`, `InterfaceMode`, `HudPanel`,
  `DialogueLayoutRule`, `HudFrame`, `AdaptiveHudModel`.
- `unity/AthenHill/Assets/AthenHill/Tests/Editor/InterfacePresentationTests.cs`: 18 Edit Mode tests.

Changed (owned): `Scripts/CityHud.cs`, `Scripts/HudWindowLayout.cs` (`Hold`, `Held`), `Scripts/GameSettings.cs`
(`InterfaceOptions`, `SaveInterface`, `ResetInterface`), `Scripts/SettingsPanel.cs`, `UI/CityHUD.uxml` (two wrappers),
`UI/CityHUD.uss` (lower-third rules appended at the end), `unity/DESIGN.md` (two Layout paragraphs).
Changed (shared, additive): `Scripts/NativeQa.cs` (snapshot key `hud`, command `interfaceMode`).
Not touched: GameSession, FollowCamera, GameInput, Controls.inputactions, Camera/*, Npc/*, Combat/*, dialogue data.

## Native test plan (development build, 1920 × 1080, real input)

Read `snapshot.json` → `hud` after each step.

1. **Lower third.** New game, walk to Mira, E. Expect within one frame `dialogueLayout = lowerThird`,
   `shadeDimmed = false`, `modalHeld = true`; the panel spans x ≈ 340–1580, bottom ≈ 1056, no darkening; Mira's head
   near (1280, 389) is clear of the panel. `hidden` contains `log`, `keyHints`, `hotbar` within 0.6 s; identity, compass
   and Field Notes visible. Title reads `MIRA`, subtitle role · topic.
2. **Navigation and branches.** Down/Up move between responses, Tab cycles Close and the responses only, Enter and a
   mouse click choose; the voice plays per node; "Show me your stock" opens Basic General as the centred wide modal
   (`dialogueLayout = none`, shade dimmed). Esc from a dialogue returns to play and the three panels return
   (`hidden` empty in Full mode).
3. **Fallbacks.** Wheel into first person, talk: `centred`, shade dimmed, panel 860 px centred. Settings › Controls ›
   Conversation camera off, talk in third person: `centred`, `conversationCamera = false`; on again: `lowerThird`. QA
   `view cam_hill` during a dialogue: `centred`.
4. **Bright and dark.** Talk to Torr at 13:00 on open sand and to Brann inside Salvage at 20:30: text readable on the
   panel in both (capture both).
5. **Moved window.** Ctrl-drag a centred window (e.g. pause) or the dialogue in first person to the top left; talk in
   third person: the lower third is still at the bottom; back in first person the dialogue returns to the saved place.
6. **Settings persistence.** Set Bark captions off, Conversation camera off, Interface Adaptive; quit and relaunch
   without `--athen-qa` (or check the QA prefix keys): the three values are kept. Reset controls restores camera on and
   Full.
7. **Adaptive.** `interfaceMode {mode:"adaptive"}`, stand still in the city, no prompt: after ~6.6 s `hidden` =
   `identity, fieldNotes, log, keyHints`; compass and hotbar visible. Hold Left Alt: all back within 0.2 s; release:
   hidden again ~6.6 s later. Walk to a colonist: `keyHints` returns while the prompt shows. Buy a flask: Field Notes and
   log return. Draw the pistol in the Berms: everything stays up while armed and 6 s after holstering; take a hit:
   identity returns. Open the pack (Tab): all four visible behind it.
8. **Reduced Motion.** Repeat 7 with Reduced Motion on: opacity jumps 0 ↔ 1, no intermediate values in consecutive
   snapshots.
9. **Photo mode.** In Adaptive with panels hidden, P, Interface row on: the HUD shows as the player had it; P closes,
   nothing stuck.
10. **Top centre.** Trigger a field-order radio line and a pickup notice together: `topCentre.depth ≤ 2`.
11. **Regression.** City loop and range tutorial checks pass in Full mode; `ui-layout.json` in a centred dialogue
    matches a pre-change capture except for the two wrapper elements.

## Rollback

Revert the files listed above (and delete the two new files). No scene, prefab, asset or save change. Saved
`AthenHill.Settings.v1.Interface` keys are ignored by older builds.

## Carl's decision (19 Nov 2026)

The 6 s quiet time for the Adaptive HUD is a starting value; he will judge it in play.

## Known risks

- Nothing has been seen. USS uses only selectors and properties already in `CityHUD.uss`; the panel height (≈ 300 px
  for a three-response node with a 350-character line) is estimated.
- The lower third covers the NPC's lower body in a 40° shoulder shot; the head and shoulders are framed above it.
- For one frame at most, a dialogue opened while the follow camera is zoomed between first and third person could show
  the lower third and then switch to centred when the camera reports first person.
- `BarkDirector.CaptionsEnabled` saves without the QA prefix, so toggling it in a QA run changes the player's setting
  (BarkDirector's behaviour, not this package's).
- The Field Notes wake compares label text; a CombatHud line added inside `#objective-box` later would not wake it.
- `unity/README.md` (not this package's file) does not mention the new Settings rows yet.

## Native QA fixes (19 Nov 2026, build batch-qa5 onward)

- **Identity, Field Notes (long objective and its button row) and the compass crowded the conversation shot.** While the
  lower third is up every HUD panel now gives way (`HudPanel.Compass` added; `AdaptiveHudModel.Target` returns 0 for all
  panels in the lower third, Full and Adaptive alike; the compass is not adaptive otherwise). Restored on close; the centred
  dialogue (camera off, first person, review camera) is unchanged. `InterfacePresentationTests` updated (lower third hides
  all six; QA ids gain "compass").
- Native (`check_showcase_interface.py` 22/22 on batch-qa5): Settings rows, persistence over a restart, Reset controls,
  Adaptive fade / Left Alt / prompt / windows, Reduced Motion cuts, photo-mode Interface row, top centre at most 2 deep.
  Not tested: Ctrl-drag of a moved window against the lower third (step 5).
