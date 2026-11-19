# Ward weather: wind and dust fronts (19 Nov 2026)

Status: code, shader edits, audio and installer written; C# compiles (`unity/tools/compile_check.py`: runtime,
editor and Edit Mode tests OK). **Not installed, not run, not seen or heard.** Unity could not run on the day
(machine at its memory limit), so the installer, the shaders, the Edit Mode tests and every look/sound value
below are unverified until the first native batch. Not accepted by Carl.

## What it does

A weather layer on top of the day/night clock. The clock stays the base: weather only multiplies or blends the
values the clock has already evaluated, and new shader globals are 0 when unset, which is the accepted look.

* **States** (Inspector: `Ward weather` > Weather Director > Schedule): Calm, Breezy, Gusting, and a dust front in
  three phases (Front Build Up, Front Peak, Front Clearing). Each state has a duration range, a weight for being
  chosen next, an ease time and a mix (wind strength, wind clock rate, gust, haze, dust emission, blowing sand,
  sun dim, warmth). **Breezy is today's look** (all neutral); Calm is slightly stiller.
* **Schedule**: seeded (`seed` 0 = new random sequence each session). After New Game or Continue the weather is
  calm for `startGraceSeconds` (480 s), no front before `firstFrontEarliestSeconds` (900 s) and at least
  `minSecondsBetweenFronts` (1200 s) between the end of one front and the start of the next. **No front while
  the Berms primer is unfinished** (`holdFrontsBeforePrimer`, default on: the Approach step counts too, so the
  arrival and the range stay clear). If a primer step becomes active mid-front, the front goes straight to its
  clearing phase rather than cutting off.
* **Runs on scaled time**: pause, photo mode and conversation cameras (timeScale 0) freeze it.
* **Not saved**: a loaded game starts calm with the same grace period (detected when `GameSession.HasStarted`
  turns true; no save-format change).
* **Drives**
  * vegetation and cloth sway: wind clock rate (`CityAtmosphere` integrates `windSpeed × WeatherConditions.WindRate`,
    so phases stay continuous) and amplitude through `_AthenWindBoost`; gusts as a slow CPU swell plus a
    travelling wave (`_AthenWindGust`) in the tree, canopy and ground-cover shaders;
  * fog: `RenderSettings` fog start/end divided by `haze` (density multiplied in exponential modes), from the
    values saved in the scene; terrain haze (`WardDesertTerrainV2`, `BermsGroundV2`) through `_AthenWeatherHaze`;
  * light: `CityTimeOfDay.FrameModifier` → `WeatherLighting.Apply`: key intensity × (1 − sunDim), warmer sun,
    fog colour tinted, sky horizon/middle/zenith, clouds and ridges veiled towards the fog colour, sky sun disc
    dimmed, a little more sky fill. Hour, sun direction, lamp strength and exposure stay the clock's;
  * dust: the existing viewer-following `Windborne dust` systems (emission and drift speed, once the installer
    sets Follow Weather) and the `City Atmosphere` drifting dust (emission);
  * blowing sand: one new viewer-centred `Blowing sand` ParticleSystem, only during a front (see performance);
  * sound: `WeatherAudio`, a wind bed following wind strength (gusts included) and a heavier dust-front layer,
    both on the city's Ambience mixer group and scaled by the Ambience volume setting (master, mute and pause act
    through the AudioListener as for all other sources);
  * radio: one Warden Ossa line when a front starts building, one when it clears (text only, tags
    `weather:front:N` / `weather:clear:N`; a warning still queued when the front clears is dropped).
* **Reduced Motion**: no blowing sand, no gust swell and no wind-strength change (`_AthenWindBoost` and
  `_AthenWindGust` held at 0; the wind clock was already frozen); fog and light still change, easing
  `reducedMotionEaseScale` (2.5×) more slowly.
* **Gameplay hooks** (read-only, for later use by Combat; nothing in Combat was changed):
  `AthenHill.WeatherConditions.Visibility` (0–1, 1 = clear; ≈0.45 at a front's peak),
  `WeatherConditions.Wind` (world `Vector3`, m/s, gusts included; zero without weather),
  plus `WindStrength`, `State`, `Active`. Without a director they read clear, still air.

## Files

New (all owned by this package):

| File | Purpose |
| --- | --- |
| `unity/AthenHill/Assets/AthenHill/Scripts/Weather/WeatherModel.cs` | `WeatherKind`, `WeatherMix` (easing), state/schedule settings with defaults, `WeatherSchedule` (pure), `WeatherLook` + `WeatherLighting` (frame composition), `WeatherRules`, static `WeatherConditions` |
| `unity/AthenHill/Assets/AthenHill/Scripts/Weather/WeatherDirector.cs` | Runtime component: schedule, easing, globals, fog, clock modifier, sand layer, radio, dev/QA state |
| `unity/AthenHill/Assets/AthenHill/Scripts/Weather/WeatherAudio.cs` | Two looping 2D wind layers |
| `unity/AthenHill/Assets/AthenHill/Editor/WeatherInstall20261119.cs` | Idempotent installer, verify, rollback |
| `unity/AthenHill/Assets/AthenHill/Tests/Editor/WeatherTests.cs` | Edit Mode tests (schedule, grace, primer suppression, gap, seeds, forcing, easing, frame composition, defaults) |
| `unity/AthenHill/Assets/AthenHill/Audio/Weather/weather_wind_bed.wav`, `weather_dust_front.wav` | 30 s seamless mono loops, 44.1 kHz |
| `art/showcase_20261119/weather/generate_weather_audio.py` | Generator (numpy only, seed 20261119) |
| `art/showcase_20261119/weather/audio-provenance.json` | Seed, parameters, sha256 of both loops |

Changed (owned): `Scripts/CityAtmosphere.cs` (wind clock rate and drifting-dust emission from
`WeatherConditions`), `Scripts/WindborneDust.cs` (new `followWeather` flag, default off, so the cookfire and
anything not opted in is unchanged).

Changed (shared, additive):
* `Scripts/CityTimeOfDay.cs`: `FrameModifier` property (`Func<DayNightFrame, DayNightFrame>`, applied right after
  `profile.Evaluate`) and `Refresh()` (re-applies while the clock is paused). Null modifier = identical behaviour.
* `Scripts/DevBridgeCommands.cs`: `dev.weather.set` / `dev.weather.reset` implemented (they returned
  `unavailable`; they still do when no director exists, which `DevBridgeTests` asserts); `weather` in `dev-state.json`
  is the director's state.
* `Scripts/NativeQa.cs`: `weather` object in `snapshot.json`.

Not touched: `GameSession.cs`, `CityAudio.cs`, `AthenDebugBridge.cs` (not needed: `GameSession.Radio`,
`RadioLine.Drop`, `HasStarted` and `Settings` are already public), anything in Combat/Npc/Camera, settings, HUD/UI,
and the saved profile/grade assets.

## Shader edits (check these first in the next build log)

Shaders could not be compiled today. Every edit declares a global outside the material CBUFFER (as
`_AthenAtmosphereTime` already is) and is neutral at 0.

1. `Shaders/WardCanopy/LitInput.hlsl`, `Shaders/WardTree/LitInput.hlsl`, `Shaders/WardGroundCover/LitInput.hlsl`:
   after `float _AthenAtmospherePreviousTime;` added `float _AthenWindBoost; float _AthenWindGust;` and
   `float WardWeatherWind(float3 p, float windTime)` returning `max(0, 1 + _AthenWindBoost + _AthenWindGust * wave)`;
   the final `p.xz += …` line of `WardTreeWind` is multiplied by `WardWeatherWind(p, windTime)`. Motion vectors pass
   the previous wind time, so the gust wave stays consistent for TAA.
2. `Shaders/HillGrass.shader`: `float _AthenWindBoost;` after `float _AthenAtmosphereTime;`; the blade offset is
   multiplied by `max(0.,1.+_AthenWindBoost)`.
3. `Shaders/WardDesertTerrainV2.shader`, `Shaders/BermsGroundV2.shader`: `float _AthenWeatherHaze;` after
   `float4 _AthenTerrainHazeScale;`; `haze = 1 - exp(-opticalDepth * (1 + max(_AthenWeatherHaze, 0)))`.

Not edited: `WardSkyV2.shader` (the sky is veiled through the clock's colours, and its clouds speed up with the
wind clock), `DriftingDust.shader` (emission covers it).

## Install

Close the Unity Editor first; one Unity job at a time, in its own memory-capped scope:

```
Unity -batchmode -nographics -projectPath unity/AthenHill \
  -executeMethod AthenHill.Editor.WeatherInstall20261119.RunBatch --steps install,verify -logFile -
```

Adds only the scene root `Ward weather` (WeatherDirector, WeatherAudio, `Weather wind bed`, `Weather dust front`,
`Blowing sand`), the material `Art/Weather/BlowingSand.mat` (URP Particles/Unlit, soft particles, camera fade,
the Dustbowl `SoftPuff.png`), sets the two WAVs to mono Vorbis compressed-in-memory, and turns Follow Weather on
for the viewer-following `Windborne dust` component. Re-running re-binds the same objects. It writes
`art/showcase_20261119/weather/install-record.json`. Render chunks are not involved. Then run the Edit Mode tests
(`WeatherTests`, `DevBridgeTests`, `DayNightTests`) and build.

## Native test plan (development build, batch QA display)

Commands go through `command.json` as usual. Force each state with an instant snap and capture the review cameras
(`cam_hill`, `cam_avenue`, `cam_gate`, plus one Berms view such as a `cam_nextlevel_*` camera and a player-height
follow view), at 13:00 and 20:30:

```
{"id":"t1","action":"dev.time.set","hour":13}
{"id":"w1","action":"dev.weather.set","state":"calm","instant":true}      # then breezy, gusting, buildup, peak, clearing
{"id":"r1","action":"dev.weather.reset"}                                    # back to the schedule, calm
{"id":"f1","action":"dev.weather.set","state":"front"}                      # a whole front on normal timings, with radio
```

`dev.weather.set` holds the named state until `dev.weather.reset` (`front` runs its course instead). Read
`dev-state.json` → `weather` (state, held, windStrength, visibility, wind, haze, sand, sunDim, fogStart/End,
sandParticles, audio volumes and mixer group) and `snapshot.json` → `weather`.

Expected:

| State | 13:00 | 20:30 |
| --- | --- | --- |
| calm | as today, sway a little slower and smaller, fewer dust sheets | as today |
| breezy | identical to the pre-weather build (A/B capture should match apart from particle randomness) | identical |
| gusting | stronger, swelling sway on the hero tree, birches, beds and grass; more grit; very slight haze | same, darker |
| buildup | horizon and far ridges ochre, fog closer (end ≈ 280 m), sun ~20 % dimmer and warmer, sand starting | lamps unchanged (clock), haze warmer and darker |
| peak | far wall and basin ridges veiled (fog end ≈ 190 m), sun ~40 % dimmer, sky disc faint, sand sheets streaming past the player, visibility ≈ 0.45 | sand tinted by night fog colour, not glowing |
| clearing | easing back over ~60 s | same |

Also check: radio line once at build-up and once at clearing for the `front` run; nothing in the first 8 minutes
after New Game (`dev-state.json` `grace: true`, state calm) and `frontAllowed: false` until the primer completes;
Esc pause and photo mode freeze `remaining`/`elapsed`; Reduced Motion on → `sandParticles` 0, `_AthenWindBoost` 0
(sway pose unchanged when forcing gusting), fog/light still change slowly; Continue from a save starts calm; the
city loop and range tutorial still pass.

## Performance risk and how to measure

The game is GPU-bound on the 3060. Costs added:

* **Blowing sand** (front only): ≤ 80 alpha-blended unlit soft particles, 2.5–6 m, screen size capped at 0.33,
  no lights or shadows. Main risk is overdraw when the camera is inside the sheets. Measure with alternating
  frame-time runs at `peak` vs `calm` (`dev.weather.set` instant) on the same walk in the Berms and on the avenue;
  if over budget, lower `Max Particles` on `Blowing sand`, `sandRate`, or the max particle size.
* **Windborne dust at higher emission**: grit ×2 at the peak (cap 260), dust sheets are already near their cap of 110.
* CPU: a few global floats and fog values per frame; the clock re-applies only when the light mix moves by more
  than 0.002 (paused clock) — reflection probes recapture through their existing 8 s throttle as the sun dims.
* Shader cost: one extra `sin`/`saturate` per vertex in the tree, canopy and ground-cover passes, a multiply in grass
  and terrain haze. Expected within drift; confirm with the usual A/B at `breezy` against the previous build.

## Values that most need tuning by eye

1. Front peak `haze` (2.2), `sunDim` (0.4), `warmth` (0.8) and `WeatherLook.skyVeil` (0.7): the beige-flattening
   risk the visual direction warns about. If the city goes flat, lower warmth/skyVeil before haze.
2. `Blowing sand` tint alpha (`sandTint.a` 0.16) and `sandRate` (28/s).
3. Gusting `windStrength` (1.3) and `gust` (0.55), and `shaderGustShare` (0.35): the hero tree may over-bend.
4. Audio: `windBedVolume` 0.3, `frontVolume` 0.4 against the existing desert bed; `silentStrength`/`fullStrength`.
5. Schedule timing (grace 480 s, first front 900 s, gap 1200 s, front weight 0.45).

## Rollback

```
Unity -batchmode -nographics -projectPath unity/AthenHill \
  -executeMethod AthenHill.Editor.WeatherInstall20261119.RunBatch --steps rollback
```

Removes the `Ward weather` root and turns Follow Weather off; without a director every global reads 0 and
`WeatherConditions` reads neutral, so the shaders, fog, light, dust and clock behave as before. The code edits are
inert without the director; to remove them entirely revert the files listed above.

## Carl's decisions (19 Nov 2026)

* Dust fronts come only after Ossa's primer is finished: `holdFrontsBeforePrimer` stays on.
* Lamps do **not** come on during a dust front: Ward is saving power, and the dark front is more interesting. Keep the
  clock's lamp strength.

## Still open

* Whether dust fronts may arrive before the primer is finished (`holdFrontsBeforePrimer`, currently on).
* Whether lamps should come on during a daytime front (currently not: lamp strength stays the clock's).
* The radio speaker (Warden Ossa) and the two lines (serialized on the director).

## Native QA fixes (19 Nov 2026, from batch-showcase-qa)

- **NullReferenceException on quit.** `WeatherDirector.OnDisable` re-applied the day/night clock after removing its
  frame modifier; when the player quits, the clock's key light can already be destroyed, and `CityTimeOfDay.Apply` threw
  (seen once in two perf runs, Player.log at quit). OnDisable now only refreshes a live clock (`isActiveAndEnabled` and its
  key light present). No effect during play.
- Native (`check_showcase_weather.py` 13/13 on batch-qa1): new game calm in grace with no front before the primer;
  Continue calm; every state forced at 13:00 and 20:30 from cam_hill, cam_gate and cam_bx_relay_knoll (contact sheets
  qa/p1/weather/weather-sheet-1300.jpg, -2030.jpg); fog end 420 / 280 / 191 m (breezy / build-up / peak), visibility
  0.45 at the peak, blowing sand around the player at the peak and none under Reduced Motion; Esc freezes the schedule; a
  full front ran build-up 83 s, peak 165 s, clearing 85 s, then calm, with Ossa's warning and all-clear on the radio.
  The 20:30 states differ only slightly (by design: night fog colour). Not heard: the wind bed and front layers (their
  sources play at 0.19 / 0.40 at the peak, Ambience group).
