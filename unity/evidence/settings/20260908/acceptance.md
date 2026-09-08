# Sound and Video settings — 8 September 2026

Scope: the native Unity game only. Both user-supplied MP3s replace the active
music. The existing city, dialogue, trade and travel sounds remain.

## Delivered behavior

- Esc → Settings · Sound and video, styled with the existing bronze HUD.
- Master, Music, Ambience and Effects sliders, mute, effects preview, next track.
  Ambience controls the four environmental sources; Effects controls SFX and UI.
- Both supplied tracks stream in stereo, alternate and crossfade over three seconds.
  Dialogue/travel ducking and normal Pause behavior remain. Settings pauses the
  city while allowing the user to hear volume adjustments.
- Video: monitor-reported resolutions, Windowed/borderless Fullscreen,
  Low/Medium/High/Custom, render scale, shadows, MSAA, texture resolution,
  post-processing, VSync and frame limit.
- Apply previews video for 15 seconds. Keep persists; Escape, Revert or timeout
  restores the last confirmed values. The recovery timer runs when focus is lost.
  Escape on an open dropdown dismisses that dropdown before leaving Settings.
- Audio settings and confirmed video settings persist across restart. Explicit
  `-screen-*` launch arguments override saved display settings for recovery.
- Runtime rendering uses a cloned URP asset. User changes do not modify project assets.

## Verification

Native checks use real keyboard and X11 mouse events; diagnostic commands only
read state or capture images. Preferences are isolated from the player's profile.
See `native/report.json`, `options/report.json`, screenshots and build reports
in this folder for the final results. The independent UI review passed Sound,
Video, confirmation and the 1280×720 layout.

The initial and prior baseline builds both report two existing errors about the
missing Desert Landscape prefab reference, GUID
`1488c4ab626b85cd382c7d134ed658f3`. This task does not change that terrain reference.
The shared live editor was busy with separate asset changes, so the final build
is made from an isolated snapshot; no copied project assets are written back.

## Source changes

`GameSettings.cs` persists options and applies/restores previews.
`SettingsPanel.cs` binds the native UI Toolkit controls. `CityAudio.cs` manages
channel levels and the two-source music playlist. `SettingsAudioPass.cs` imports
and assigns the supplied music. Existing HUD, input and session state code integrate
the Settings screen. `check_settings.py` and `check_settings_options.py` exercise
native controls, renderer/audio state, resolution changes, rollback and persistence.
