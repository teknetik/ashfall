# Dust-bowl atmosphere and Karaveen market — 26 September 2026

Scope: atmosphere/grade pass plus the Blender-built caravan market
([source record](../../../../art/karaveen_market_20260926/README.md)).
Editor pass: `Assets/AthenHill/Editor/DustbowlMarketPass.cs`. `pass.json` records
what was installed and the original values for rollback.

## What changed

- **Lighting clock** now uses `Art/Atmosphere/Dustbowl/WardDustbowl.asset` (copy of
  WardAfternoonShade): dustier noon, new 16:00 frame (lower warm sun, darker/warmer
  ambient, hazier sky) and default hour 16:00. The original profile is unchanged.
- **Grade** `WardDustbowlGrade.asset` on *AAA Global Volume*: ACES, contrast 22,
  saturation −7, warm filter/white balance, shadows/midtones/highlights and
  lift/gamma/gain split, bloom, darker vignette, film grain, slight chromatic
  aberration. Original `AthenHillBeautyVolume.asset` is unchanged.
- **Fog** 12–118 m (was 32–132). **Sky** coverage .53, wisps .07, cloud opacity .8,
  thickness 1.7, dusty tint. **SandstoneBasin** haze density .0068 (was .0048).
- **Windborne dust** (scene root): large drifting dust sheets and fast stretched grit
  near the ground, centred on MainCamera, cleared by Reduced Motion (`WindborneDust`).
- **Market**: `Karaveen caravan market` prefab instance, 49 box colliders, 8 goods
  LODGroups, 9 lanterns added to the Ward lighting clock's `CityLightCircuit`, cookfire
  light with `FireFlicker`, flames/embers/smoke. Placeholder stalls disabled.
- Review cameras `cam_market`, `cam_market_lane`, `cam_market_produce`, `cam_market_cookfire`.

## Verification

- 50/50 EditMode tests passed (`editmode-results.xml`).
- Development Linux build succeeded; native stills at 16:00 and 20:30 in
  `native-captures/`, smoke retune in `native-captures-2/`. **The player window was
  tiled by the window manager to 936×1040**, so these are look/lighting evidence only,
  not 1080p acceptance or performance evidence.
- Editor stills with the clock's default frame applied: `captures/`.

Not done: warmed moving traversal performance on the RTX 3060, keyboard/gameplay
re-verification of the market area, lantern glass emission (lantern light pools work).
