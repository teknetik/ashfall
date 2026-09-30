# Field pack after the Ark reference — 30 September 2026

The user asked for the inventory to look more like a supplied ARK: Survival Evolved inventory screenshot (tabbed item
grid with search and filters, a central "YOU" column of equipment slots around a character card with stat bars, and a
large turnable character view in bracketed corners, in a cyan-on-dark-teal instrument style). The screenshot is not
stored here; no ARK art, UI chrome or logos were copied. This pass rebuilt Ward's field pack in that layout, using
Ward's own frame, palette, font and item illustrations.

Tested working tree: branch `ward/next-level` at `782b2ab6` plus the uncommitted pack changes listed below. Linux
development player, OpenGL, 1920×1080 windowed (High preset), RTX 3060 12 GB host.

## What changed

- `UI/CityHUD.uxml`, `UI/CityHUD.uss`: the `inventory-panel` is now three panels in a 1580-reference-pixel modal:
  **PACK** (PACK / SCHEMATICS tabs, credits, search, filter chips, 6-wide cell grid completed with empty cells,
  selected-item strip, counts footer) | **YOU** (sidearm and grip/barrel/nano-cell slots around the colonist card,
  city-visit/field-order progress bar, vitality and nano bars, pistol stats vs base) | **colonist view** (live render,
  bracket corners, dot grid, drag to turn). Item details take the colonist view's place. Modal footers keep their
  spacing (`white-space: pre`; before, the separators collapsed to single spaces in every modal).
- `Scripts/PackPanel.cs` (new): builds and drives the pack; replaces the inventory code that lived in `CityHud`.
- `Scripts/InventoryView.cs`: filter categories from catalog tags (consumable, salvage, refined, weapon_mod) and search.
- `Scripts/CharacterPreview.cs` (new) and scene object **Character preview** (camera + Key/Fill/Rim studio lights):
  renders only the player colonist, only while the pack shows it. For that camera's pass the colonist's renderers join
  the new `CharacterPreview` layer (10), Sun, Sky fill and any lamp whose range reaches the colonist switch off and the
  studio lights switch on; all restored after the pass. Shadow-only proxies, effects and first-person arms stay out.
- `Editor/CharacterPreviewInstaller.cs`: **Athen Hill → UI → Install field-pack colonist view** (creates the rig only when
  missing). Scene diff: additions only (the rig, and CityHud's new `characterPreview` reference).
- `UI/Art/preview-grid.png`: original 44 px dot tile for the view background.
- Only recorded facts are shown: no weight, durability or capacity was invented. Fitting mods still happens only at
  the field fabricator; the pack shows slots read-only.

## Checks

- EditMode: 166 / 166 passed after the final change (`PackPanelTests`: 8 new tests for filters/search, layout, grid,
  schematics tab, loadout/stats, no-pistol state, details swap, per-pass isolation of the colonist view).
- Native real-input run (`tools/check_pack.py`, `native-v2/`; `native-v1/` is the pre-polish run): Tab opens the pack
  with the first cell focused; arrows move one cell; Up from the top row → filter chip → tab; tabs switch with Enter;
  MODS chip leaves the two carried mods; typing `alloy` in Search (WASD letters type, focus stays) leaves 3 cells;
  Down returns to the grid; Backspace clears; hovering the barrel slot shows the fitted Lattice-Focused Barrel and its
  stat changes; dragging turns the colonist; Enter on the Quantum Lattice Shard opens details in the view's place with
  focus on Close, Esc returns to the pack with the shard focused; Tab closes; 1280×720 layout fits. Player.log: 0 errors.
- The save is a copy of `rendering/20260930/pistol-mods-mk2/save` with nine extra item stacks added (listed in
  `report.json`) so the grid and filters have content. The original save was not touched.
- Colonist lighting was auditioned in the Editor (`audition/`): `compare-ab.png` shows the first two intensity
  variants, where a West Gate street lamp still tinted the shins cyan; `final-compare.png` is after lamps near the
  colonist were muted for the preview pass.

## Performance (West Gate, 17:00, 6 s samples, uncapped)

| Pack | avg FPS | p50 ms | p99 ms | triangles | SetPass |
| --- | --- | --- | --- | --- | --- |
| closed | 37.6 | 26.5 | 29.4 | 27.31 M | 529 |
| open | 36.6 | 27.3 | 29.3 | 27.34 M | 535 |

The colonist view adds about 31 k triangles and 6 SetPass calls; there is no clear frame-time difference.
The ~37 FPS at this West Gate view was there before this change: earlier runs today recorded 33–38 FPS with
26–34 M triangles at the same spot (`rendering/20260930/perf-*`, `gameplay-v2/20260930-reqa/run2-continue`). It is
below the 60 FPS target and needs its own performance pass.

## Remaining defects / notes

- Tile names are one line with an ellipsis ("Damaged Se…"); the full name is in the selected-item strip and tooltip.
- The grid switches to 5 columns if more than 24 item kinds are carried (the scrollbar takes width).
- The colonist view shows the idle pose the player has in the world; there is no separate inventory pose or animation.
- ARK's cyan look is used inside the pack only; the rest of the HUD keeps its bronze frames.
