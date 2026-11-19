# World map (19 November 2026)

Carl has got lost in the Outer Berms before ("no drone in sight"). Until now navigation was the compass strip, one
tracked-mission marker and the Warden trail cairns. This adds a **world map on M**: one north-up sheet of Ward and the
~495 × 425 m Berms bowl, with pan and zoom, the player arrow, a scale bar, labels, and the places the player has found.
It is a navigator's sheet, not a radar: no enemy or loot positions.

Status: code written and compiled with `unity/tools/compile_check.py` (Runtime, Editor, Edit Mode tests OK). Nothing has
been run in Unity or the native player: the window, the drawing, the survey render and the tests are all unverified.

## What it does

- **Key and window.** M (new `UI/Map` action in `Data/Controls.inputactions`, in the always-on UI map so the same key
  closes it) opens the map from plain play, like J opens the journal: new `CityState.Map`, gameplay input off, cursor
  freed, game time keeps running (as with the journal). M or Escape closes it. It uses the shared modal (bronze frame,
  title, Close button, footer) at 1680 px / 96 % wide and 92 % high; the modal's scroll view is swapped for the sheet.
- **Sheet (left).** North up, world X to the right. Drag, arrows/WASD (Shift faster) pan; wheel, + / − zoom about the
  pointer or centre; double-click zooms in; C centres on you, T on the tracked target, F shows the whole sheet. Zoom runs
  from the whole sheet to 14 px per metre. Scale bar (1/2/5 × 10ⁿ m) bottom left, N badge top right, SURVEY or
  SCHEMATIC bottom right. The sheet takes keyboard focus when it opens (cyan rule).
- **Column (right).** YOU ARE (region and distance to the nearest named place), TRACKED (the journal's tracked mission,
  its marker label and distance; "Show on the sheet · T"), IF YOU GO DOWN (where the Wardens would bring you, and the last
  knock-down if any), PLACES (a button per place shown, grouped WARD / OUTER BERMS; Enter or click centres the sheet).
- **Layers.**
  - City places, always: Hill Tree, Lattice Jack, Vanguard Hall, Basic General, the eight shops, the water ration point,
    Node 07 goods dock, Nanofab 2, Processing 11, Aquifer 3, hydroponics, the barred +X gates; the home once leased.
    Shop names show from 3.2 px/m; zoomed out a single WARD label stands for them.
  - Berms places, always: West Gate (the compass's gate point), the Warden post, the training range.
  - Berms sites (the twelve expanse sites, the four next-level sites and the machine depot): **only once discovered**.
    Discovery = the player stood within 55 m (ground plane) of the site's centre during play (`WorldMap.siteRadius`). A
    one-line notice says "<site> marked on your map · M". Cleared sites are dimmed (as on the compass).
  - Warden waystations: shown once found (their existing story flag `waystation:ID` is also the map id). A cyan ring marks
    the active respawn: the nearest found waystation, else the gate post (`WardenWaystation.NearestFound`, as PlayerCombat).
  - Tracked target: the journal's tracked mission target (same as the compass). A fixed target is a cyan diamond in a ring;
    when the target is a machine (mission `droid`, or a FeralDroid under the target) the map shows a dashed 35 m area on
    the nearest known site within 120 m, else on a 25 m grid square, so a droid is never tracked live. Off-sheet targets
    and the player get an arrow on the sheet's edge.
  - Last knock-down: a red cross where the player last went down (recorded from the previous frame's position, because
    PlayerCombat raises Downed after it has already moved the player).
  - Warden trails (sites.json routes) as dashed bronze lines on both bases.
- **Base picture.** With no survey asset the panel draws a schematic from data (`WorldMapSchematic`): the bowl floor with
  four contour-like rings inset from the mountain foot, hatching outward along the foot, the old Berms ground (road), the
  city floor, the hill disc, building footprints (Processing 11 dashed as a ruin), the Tube conduit, walls in bronze and
  the gate openings dashed. When `Resources/WorldMap/WorldMapSurvey.asset` exists, its pictures replace that base (the
  trails and all markers stay on top).
- **Persistence.** Save stays version 4; `WardSaveData.map` (`MapState`: discovered ids, last knock-down) is additive.
  An older save without it loads with what its progress implies: every found waystation flag, and the machine depot once
  the primer is complete. Carl's current save (primer done, no waystation flag) would load with only the depot found.
  Discoveries and knock-downs autosave. An older v4 build ignores the field (it would drop it on its next save).

## Files

New (all mine):

- `unity/AthenHill/Assets/AthenHill/Scripts/Map/WorldMap.cs` – live state component (places, discovery, respawn, tracked
  marker, knock-down, save capture/restore); added to the GameSession object at runtime, no scene edit.
- `.../Scripts/Map/WorldMapPanel.cs` – the window (built in code; Painter2D drawing; labels; input).
- `.../Scripts/Map/WorldMapMath.cs` – `MapView` transform, scale bar, slug, discovery radius, tracked-marker rule.
- `.../Scripts/Map/WorldMapData.cs` – `MapState`, `MapPlace`, `WorldMapDiscovery`, `WorldMapSchematic` (data with sources).
- `.../Scripts/Map/WorldMapSurvey.cs` – ScriptableObject for the survey pictures and their world rectangles.
- `.../Scripts/Map/WorldMapQa.cs` – QA snapshot and commands.
- `.../Resources/WorldMap/WorldMap.uss` – the window's styles (loaded from Resources and added to the HUD root; the HUD
  UXML/USS are untouched). There is no UXML: the panel is built in code like the journal.
- `.../Editor/WorldMapInstall20261119.cs` – installer (anchors, survey, verify, rollback).
- `.../Tests/Editor/WorldMapTests.cs` – 10 Edit Mode tests.

Shared files, additive edits:

- `Scripts/GameSession.cs`: `CityState.Map` appended; `Map` property (adds `WorldMap` in Awake like the journal);
  `input.MapPressed` → `ToggleMap()`.
- `Scripts/GameInput.cs`: `MapPressed`. `Data/Controls.inputactions`: UI map action `Map` on `<Keyboard>/m` (new ids;
  existing ids unchanged; JSON validated).
- `Scripts/CityHud.cs`: builds `WorldMapPanel`, calls its `Refresh()` in `Refresh` and `Opened()` on entering Map.
- `Scripts/HudWindowLayout.cs`: `NoDragClass` ("no-window-drag"): elements with it never start a window drag (the
  sheet pans instead of moving the modal).
- `Scripts/Save/WardSaveData.cs`, `WardSaveGame.cs`: `map` field, capture, restore after flags/primer, autosave hook.
- `Scripts/NativeQa.cs`: snapshot key `map`; commands `mapOpen {open}` and (development builds) `mapDiscover {site}`.
- `unity/README.md`: controls rows for M and the map's keys.

## Installer and the survey render

`AthenHill.Editor.WorldMapInstall20261119.RunBatch --steps …`, also under the menu *Athen Hill → World map*:

| Step | Graphics? | What it does |
| --- | --- | --- |
| `anchors` | no (`-nographics` fine) | reads Vanguard Hall, Nanofab 2, Processing 11, Aquifer 3, hydroponics, the water point, the goods dock and the Salvage / Field Supply interiors from the saved scene (renderer bounds centres, active objects only, must lie inside the walls) into the survey asset's anchors, which replace the schematic's recorded positions |
| `survey` | **yes** | two top-down orthographic renders of the saved scene: `berms` x −600…80, z −260…240 at 4 px/m (2720 × 2000) and `city` x −64…64, z −48…48 at 16 px/m (2048 × 1536); each rendered at 2× and halved; fog off, no sky (solid sheet colour), no post-processing, LOD bias 40, a temporary copy of the URP asset with 1400 m single-cascade 4096 shadows, the sun fixed at elevation 55° lit from the north-west with soft shadows; everything restored afterwards; the scene is never saved. PNGs in `Assets/AthenHill/Art/WorldMap/` (BC7, mipmaps, trilinear, clamp); the asset gets each layer's exact world rectangle (the world-to-map transform: u = (x − xMin)/width, v = (z − zMin)/height, north up), also written as `Art/WorldMap/WorldMapSurvey.json`, `unity/evidence/world-map/20261119/survey.json` and `art/showcase_20261119/world_map/survey.json` |
| `verify` | no | `unity/evidence/world-map/20261119/verify.json`: asset loads from Resources with usable layers whose texture aspect matches the rectangle, anchors name known places, the style loads, M is bound to exactly UI/Map, action ids unique |
| `rollback` | no | deletes the survey asset, both PNGs and the JSON: the map draws its schematic again |

Commands (one Unity job at a time, Editor closed, memory-capped wrapper):

    ~/.local/state/ward-programme/unity.sh <log> AthenHill.Editor.WorldMapInstall20261119.RunBatch --steps anchors,survey,verify -quit
    ~/.local/state/ward-programme/unity.sh <log> AthenHill.Editor.WorldMapInstall20261119.RunBatch --steps anchors,verify -nographics -quit

Only `survey` needs graphics, two renders in all (the largest target is 5440 × 4000 plus depth, about 170 MB of VRAM).

## Native test plan (real input, development build)

Start from a save with the primer complete and no waystation found (or Carl's save copied into a QA save folder).

1. Play, press **M**. Expected: snapshot `session.state` = `Map`, `map.open` true, cursor unlocked and visible, the sheet
   focused (`session.focused` = `map-viewport`), title "World map", centred on the player arrow. City places labelled;
   only the Machine depot among the Berms sites (old-save rule), West Gate / Warden post / range shown.
2. Press **M** again: back to `Play`, cursor locked. Open again, press **Escape**: back to `Play` (not Paused).
3. Drag with the left mouse: `map.view.centre` changes, the modal does not move. Wheel up over a shop: `map.view.scale`
   rises and the point under the pointer stays put. Hold →, hold +, press C, F, T: centre/scale change as described.
   Tab: focus moves to Close, the buttons and the place list; Enter on a place centres on it.
4. `goto berms_relay_knoll` (landmark 18 m from the site centre), wait a second in Play: notice "Relay knoll marked on
   your map · M"; `map.discovered` contains `site:relay_knoll`; the save file's `map.discovered` contains it after the
   autosave. Quit and Continue: still discovered.
5. `goto berms_waystation` (18 m out) and walk into the camp (its own radius is 11 m): `waystation:berms_mid` discovered; open M: cyan ring on the
   waystation when the player is nearer to it than to the gate post (`map.respawn` = `waystation:berms_mid`).
6. Track a field order with a droid target: `map.tracked.area` true and `map.tracked.world` equals a site centre or a
   25 m grid point, never a droid position from `combat.enemies`. Track the home mission (fixed target):
   `map.tracked.area` false and `world` equals the locker's x/z.
7. Get knocked down in the Berms (`damage` command): `map.lastDowned` ≈ the position before the respawn; red cross shown.
8. `mapOpen {open:true}` / `{open:false}` and `mapDiscover {site:"site:mesa_roost"}` acknowledge success; an unknown site
   id fails with "Unknown map place".
9. With the survey asset installed: `map.survey.present` true, `layers` ["berms","city"], `shown` true; lookbook capture
   of the open map at 13:00 and 20:30 (the picture does not change with time of day: it is baked).
10. Performance: open map, hold → for 5 s: no hitch above the normal walk; the map costs nothing while closed (it only
    builds when opened, and the discovery check is a loop over ~40 places).

## Rollback

- Survey picture: `--steps rollback` (the map falls back to its schematic).
- The feature: remove `Scripts/Map/`, `Resources/WorldMap/`, the installer and test; revert the marked lines in
  GameSession (`Map` state, property, `MapPressed` line, `ToggleMap`), GameInput (`MapPressed`), CityHud (four lines),
  HudWindowLayout (`NoDragClass`), the save files (`map` field and three lines), NativeQa (three lines), the UI/Map
  action and its binding in Controls.inputactions, and the README rows. Saves written meanwhile keep a `map` field that
  older code ignores.

## Known risks and open points

- Nothing has been seen: the window layout, label sizes, colours and the Painter2D drawing are reasoned, not reviewed.
  First things to check natively: that the sheet fills the modal (flex/height rules in `WorldMap.uss`), that labels do not
  pile up at the city scale, and that dragging pans rather than moves the modal.
- Schematic building footprints for Nanofab 2, Processing 11, Aquifer 3, hydroponics, the Tube nodes, wall homes and
  watchtowers are approximate (layout roots plus estimated sizes); the shops, Basic General, Vanguard Hall, the hill and
  the walls are from measured layout records. The `anchors` step corrects label positions, not footprints; the survey
  picture replaces the footprints entirely.
- The survey render has not run. Risks: custom URP renderer features or atmosphere shaders may still add haze to an
  orthographic view; the sun object may be driven by `CityTimeOfDay` in edit mode (only matters if it updates between
  setting and rendering, which it should not in one call); some LODGroups may still cull at 4 px/m; the solid clear
  colour shows wherever the basin mesh has holes.
- Naming, decided by Carl on 19 Nov 2026: "West Gate" is the gate near the market, the Berms portal, as labelled here.
  The +X spawn arches are no longer West Gate; they become "East Gate" (`art/gate_names_20261119`).
- Discovery radius 55 m: accepted by Carl on 19 Nov 2026; sites are 60–130 m apart, so neighbours are not found together. The machine depot is
  a map site but not a compass point.
- The map does not pause the game (like the journal); opening it mid-fight in the Berms leaves the player exposed.
- The window shows a place list but no layer toggles; the legend is the column's wording.

## Native QA fixes (19 Nov 2026, build batch-qa2 onward)

- **The primer's depot was discovered by walking out of the gate.** Symptom: a new game marked "Machine depot" on the
  map (with its notice) on the first walk past the Warden post, before the primer sends the player there; the road runs
  within 55 m of the depot. Cause: discovery used the radius rule for every site. Fix: `WorldMapDiscovery.PrimerAllows`
  (`Scripts/Map/WorldMapData.cs`) keeps `site:machine_depot` undiscoverable until the primer reaches its Depot step (the
  moment the HUD shows the MACHINE DEPOT guidance); `WorldMap.cs` passes the current step to `Visit`. Every other place
  keeps the 55 m rule; an old save with the primer complete still loads with the depot found. Edit Mode test
  `ThePrimerDepotIsNotDiscoveredBeforeThePrimerSendsThePlayerThere`; native: `check_showcase_world_map.py` (new-game run).
- **Black void around the survey picture.** The sheet's background (`.map-viewport`, `Resources/WorldMap/WorldMap.uss`)
  was near-black (#101717), so the area beyond the surveyed rectangles read as a missing texture at the city scale and
  in the whole-sheet view. Now a darker sand (#7f6245) close to the survey's edge colour. The schematic fallback
  (no survey) draws on the same colour; not reviewed natively since the survey is installed.
- Survey render ran once (graphics mode, 14:39): berms 2720x2000, city 2048x1536, verify PASS; both pictures read well.
- **"Node 07 goods dock" overlapped "Lattice Jack".** `WorldMapMath.Declutter` (pure): when two labels would overlap at
  the current zoom the higher-priority one is shown (home > gates/landmarks > sites/waystations > Berms places > shops >
  services; the place last chosen in the PLACES list wins), the other returns once zooming in separates them. Test
  `OverlappingLabelsKeepTheHigherPriorityOneOrTheSelectedPlace`.
- **"Show on the sheet · T" was offered for a tracked mission with no map target** (Carl's save tracks Warden Kit: Helm,
  whose step has no marker). The button is now hidden when there is no target.
- Native (`check_showcase_world_map.py` 29/29 on batch-qa5, on a copy of Carl's save plus a new-game run).
