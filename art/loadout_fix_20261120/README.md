# Loadout and hotbar fixes (20 November 2026)

Carl's interface notes from his 20 November playtest (`art/showcase_phase2_20261120/PLAYTEST-NOTES.md`, notes 1-4) and
his three screenshots (implants page, hotbar strip, armour page, played at 3840 × 2160). Not yet accepted by Carl.

## What was wrong, and the fix

### 1. "Implants need a eye slot"

- **Added** an EYE implant slot: `implant_eye`, label *Eye*, section IMPLANTS, directly after `implant_head` in
  `Resources/CharacterCatalog.asset` (installed by `Editor/LoadoutFixPass20261120.cs`, step `install`). Its dot ends on
  the eye socket on the image's right and its box sits top right.
- **No implant was moved.** The catalog's head implants are the *Neural Targeting Implant* Mk I and Mk II ("a basic
  targeting lattice that improves sighting and pistol control", tags `implant:head`). It is a neural lattice, not plainly
  an eye or optic implant, so it stays in HEAD. The droid parts named "optic" (Cracked Optic Lens, Sentinel Optic) are
  crafting salvage, not implants. No new items were invented, so the eye slot is empty and nothing fits it yet.
- **Empty state.** Selecting an empty slot now says what fits it ("Fits here: …"); a slot nothing fits says
  "Nothing made or sold in Ward fits the eye slot yet."
- **Saves.** Equipment is saved per slot id (`CharacterState.equipped`), so the change is additive: a save from before
  the slot (v4 or older) loads with the eye empty and everything else in place. No migration was needed because nothing
  moved. Test: `LoadoutFixTests.ASaveFromBeforeTheEyeSlotLoadsWithTheEyeEmpty`.

### 2 and 3a. Leader lines pointed at the wrong body parts (implants and armour)

**Cause.** The dots were never placed against the figure. `CharacterLoadoutPanel.AnatomyPosition` gave each slot a
percentage *height* for its box, and the dot and its 25 px leader were drawn at that same height, a fixed 135 px in from
the map's edge. The box height list was spaced evenly down the panel, so the dot landed wherever the box happened to be
(ARMS at the box's height = upper chest, WRIST = pelvis, HAND = knee, …). The figure itself is drawn with
`ScaleToFit` inside a 306 px map, so it is letterboxed and its position changes with the panel height; nothing tied the
dots to it. Boxes 112 px wide on a 306 px map also covered the figure's hands.

**Fix.** `Scripts/AnatomyLayout.cs`:
- an **anchor table** per page: each body part's point measured on the figure image itself (`Resources/UI/ImplantBody.png`,
  1024 × 1536), stored as image fractions, plus the side its box goes on;
- `Arrange()` sizes the map from the available height (the figure keeps its proportions, the boxes sit in a column either
  side of the figure, the inspector keeps at least 160 px), puts each dot at image rectangle + anchor × image size, and
  stacks each column's boxes as close to their dots' heights as they fit without overlapping. When the page is too
  narrow for the figure at full height (the ARMOUR page beside the colonist preview in a 4:3 window), the boxes go
  compact (88 px, no illustration, 12 px text) so the figure stays larger;
- the leader runs from the box edge facing the figure to its dot, drawn with `Painter2D` on one overlay element
  (`anatomy-leaders`); the selected slot's leader and dot are brighter. Leaders only cross the space between the two box
  columns, so they cannot cross another box or its label.
`CharacterLoadoutPanel.ArrangeAnatomy` re-runs it whenever the page's size changes, so it holds at every window size and
aspect. The UI panel scales with the window (reference 1920 × 1080, match 0.5), so 3840 × 2160 lays out exactly like
1920 × 1080 at twice the pixels.

Anchors (image pixels): head 512,80 (cranium) · eye 540,131 (eye socket) · arms 683,410 (humerus) · chest 512,385
(sternum) · wrist 792,735 · waist 512,590 (lumbar) · hand 810,782 (palm) · legs 415,880 (thigh) · feet 653,1413;
armour adds PACK at 650,318 (shoulder, where the straps sit).

### 3b. The stray "Head" under both body maps

It was the `equipment-selection` label: the selected slot's name, with nothing after it, under the map. The inspector
beside the map already names the slot (HEAD), shows what is fitted or "Empty", its stats and sockets, or what fits. The
label is now hidden on the IMPLANTS and ARMOUR pages; on the weapon pages it reads "Secondary · Scrap Pistol" or
"Socket: Grip · Empty", never a bare word.

### 4a. Hotbar names that did not go away

**Cause.** They were not tooltips (runtime UI Toolkit draws no tooltips): they were **drag labels** (`equipment-drag-ghost`)
left behind by the HOTBAR strip's own drag code in `PackPanel` (`BarDown/BarMove/BarUp`). Carl's screenshot shows
counts of 0 on 3 and 4, so he was dragging the strip cells themselves. That code made a new label each time a drag
started and only removed the one it last remembered, and its release handler sat only on the panel root. When the
release did not reach it, the drag never ended: the slot was neither moved nor cleared (so reordering looked impossible),
and the next press started another label on top. The labels stayed until the pack closed, and over other pages.

**Fix.** The strip now uses the loadout panel's drag (the one pack items already use, proven by the earlier native checks):
- one drag label at most: making one first removes every label under the panel root, and ending a drag removes them all;
- the release is handled on the pressed cell as well as on the root (pointer and mouse events), a lost capture ends
  the drag, and a 100 ms watchdog drops the drag where the pointer was if the left button is up but no release arrived
  (released outside the window, focus lost);
- Escape, a new press, a pack page or loadout page change and closing the pack all end the drag and remove the label.

### 4b. Rearranging the hotbar

`HotbarModel.Swap` already existed (a move when the target is empty). The strip now actually uses it:
- drag a cell (3–0) onto another cell: moves it, or swaps the two; the cell under the pointer lights up and the dragged
  one dims;
- keyboard: focus a strip cell (Tab or click) and press a number: its item goes to that slot (swapping); Delete or
  Backspace clears the focused cell;
- 1 and 2 are fixed to the equipped primary weapon and sidearm (as in the model): they do not drag, an item dropped on
  them is refused with a notice, and they have a duller frame and a gap before 3;
- still as before: dragging a pack item onto a cell or selecting it and pressing a number assigns it; right-click,
  dragging a cell off the strip, or Delete clears it; the HUD hotbar redraws from the same model; the order is saved in
  the save's existing `hotbar` field (v4).
Help line: "3–0: drag from the pack or select an item and press its key · drag a cell onto another to reorder ·
right-click or drag off to clear · 1 and 2 follow your weapons" (`PackPanel.HotbarHelp`).

## Where to edit

- Body-map anchors and box sides: `Scripts/AnatomyLayout.cs`, the two anchor tables (measure on the 1024 × 1536 image:
  pixel x, y). Box size, spacing and the inspector's minimum width are the constants at the top (keep `BoxWidth/Height`
  equal to the `.anatomy-slot` USS rule).
- The slot list: `Resources/CharacterCatalog.asset` → `slots` (id, label, section). A new IMPLANTS or ARMOUR slot needs an
  anchor in `AnatomyLayout` (until then it is spread down the spine and `LoadoutFixPass20261120 verify` reports it).
- What fits a slot: each `equipment` entry's `slots` list in the same asset.
- Styles: `UI/CityHUD.uss` (`.anatomy-*`, `.packbar-fixed`, `.drop-target`, `.drag-source`).
- Strip behaviour: `PackPanel.cs` (`BuildHotbarStrip`, `MoveHotbar`, `ClearHotbar`); drags: `CharacterLoadoutPanel.cs`
  (`BindHotbarCell`, `DropAt`, `CancelDrag`).

## Install, verify, rollback

```
P2/seq.sh install loadout_fix-N AthenHill.Editor.LoadoutFixPass20261120.RunBatch install,verify
P2/seq.sh install loadout_fix-N AthenHill.Editor.LoadoutFixPass20261120.RunBatch rollback     # removes the eye slot
```
`install` is idempotent and records the previous slot list in `previous/character-slots.json`. No scene change.
`verify` writes `unity/evidence/showcase_phase2/20261120/loadout_fix/verify.json`. Code and USS roll back with git.
The Item Lab export `Data/Crafting/Export/ward-crafting.v1.json` was not regenerated (it has been stale since 3 October;
`CraftingDataExporter.Export` refreshes it with everything else that changed).

## Tests

- Edit Mode: `Tests/Editor/LoadoutFixTests.cs` (eye slot and old saves; every anchor lies in the measured region of its body part and off the dark background in the
  image itself; at 30 sizes per page dots equal anchors, boxes stay inside and apart, no leader crosses a box or another
  leader; the body map builds a dot per slot and hides the bare label; hotbar move, swap, fixed 1–2, save order; the
  strip's MoveHotbar/ClearHotbar redraw it).
- Native: `unity/tools/capture_loadout_native.py` (real X11 mouse and keyboard; see its docstring).

## Verified natively

Builds `Builds/batch-p2-ui1`, `p2-ui2`, `p2-ui3` (final). Evidence: `unity/evidence/showcase_phase2/20261120/loadout_fix/`
(`ui1/`, `ui2/`, `ui3/`; console output in `../lf-*.out`). Runner: `art/loadout_fix_20261120/run_checks.sh BUILD TAG`.

| Build | Loadout check | check_inventory_redesign | check_showcase_interface | check_home_journal_native |
| --- | --- | --- | --- | --- |
| p2-ui1 | 71/72 (the one failure was the check counting weapon slots 1–2 in the final order; corrected) | not run | not run | not run |
| p2-ui2 | 72/72 | 39/39 | 22/22 | 36/36 |
| **p2-ui3 (final)** | **72/72** | **39/39** | **22/22** | **36/36** |

p2-ui2 → p2-ui3 changed only the compact boxes' text size (12 px), after "Field Backpack" broke mid-word at 4:3.
None of the three existing checks needed changing. `LoadoutFixPass20261120 verify`: ok, 16 body-map slots, no item fits
the eye slot, scene unchanged (`loadout_fix/verify.json`).

What I looked at myself (zoomed): the implants and armour pages at 1920 × 1080 (`ui*/loadout/run/implants-1920x1080.png`,
`armour-1920x1080.png`, `implants-eye-selected-1920x1080.png`), 1280 × 720, 1440 × 1080 and 1920 × 800; the drag in
progress (`drag-in-progress.png`: one label, the dragged tile dimmed); the strip after reordering
(`hotbar-final-order.png`) and the HUD hotbar after the restart (`run2/hud-after-restart.png`); the inventory regression's
implant capture (`ui2/inventory/run/02-implants-augmentation-1080.png`). Every dot is on its part: HEAD on the cranium,
EYE on the eye socket, ARMS on the upper arm, CHEST on the sternum, WRIST on the wrist, WAIST on the lumbar spine, HAND on
the palm, LEGS on the thigh, FEET on the foot, PACK on the shoulder; no leader crosses a box; no stray word under the map;
no label left behind anywhere.

Not verified: Carl's own 3840 × 2160 screen (the panel is resolution-independent at 16:9, so it lays out as 1920 × 1080
at twice the pixels; not captured at 4K because the QA display is 1920 × 1080); a release outside the game window during
a drag (the 100 ms watchdog covers it, not exercised natively); gamepad. The Edit Mode suite was not run by me (the
orchestrator runs it); `LoadoutFixTests` compile.

## Open defects

- At 4:3 the ARMOUR page is narrow (the colonist preview takes 260 px), so the figure is about two thirds of the page
  height and the boxes are compact; long item names wrap to two lines there.
- The selected HEAD dot and the EYE dot are close together (about 15 reference pixels at 1080p); both are readable.
- The anatomy-slot `compact` class shares its name with the HUD root's `compact` arrangement class; harmless (rules are
  scoped by `.anatomy-slot`/`.anatomy-map`), could be renamed.
- The Item Lab export (`Data/Crafting/Export/ward-crafting.v1.json`) does not list the eye slot until it is regenerated.

## Proposed text for the shared documents

**unity/EDITING.md**, in "Controls, hotbar, journal and the container home", replace the last sentence of the Hotbar
paragraph ("The HUD bar is drawn by … Saved as `hotbar` (save v4).") with:

> The HUD bar is drawn by `HotbarView`; the field pack's HOTBAR strip by `PackPanel` (drag targets carry `HotbarDrop`).
> Since 20 November 2026 the strip reorders: dragging a cell (3–0) onto another moves or swaps them
> (`PackPanel.MoveHotbar` → `HotbarModel.Swap`), a focused cell and a number key send it there, right-click, Delete or
> dragging off the strip clears it; 1 and 2 follow the equipped weapons and do not move. Strip and pack drags share
> `CharacterLoadoutPanel`'s drag (one drag label at most). Saved as `hotbar` (save v4).

and add a paragraph:

> **Body map (implants and armour).** Slots come from `Resources/CharacterCatalog.asset` (`slots`, section IMPLANTS,
> ARMOUR or STORAGE; the EYE slot `implant_eye` was added by `Editor/LoadoutFixPass20261120.cs`). Each slot's dot is an
> anchor on the figure image `Resources/UI/ImplantBody.png` (1024 × 1536), in the tables in `Scripts/AnatomyLayout.cs`
> (pixel x, y and the box side); `AnatomyLayout.Arrange` places the figure, boxes, dots and leaders for any page size. A
> new body slot needs an anchor there (`LoadoutFixPass20261120 verify` lists any without one). Record:
> `art/loadout_fix_20261120/README.md`.

**unity/DESIGN.md**, after "**Implants are strictly two dimensional.** … Selecting a socket opens a further panel …":

> Body-map slots sit in a column either side of the figure, each as close as it fits to the height of the body part it
> names; a thin cyan leader runs from the box edge to a dot on that part (head on the cranium, eye on the eye socket,
> arms on the upper arm, chest on the sternum, wrist, waist, hand on the palm, legs on the thigh, feet, pack on the
> shoulder). The selected slot's leader and dot are brighter. No leader crosses a box. Implant slots: Head, Eye, Arms,
> Chest, Wrist, Waist, Hand, Legs, Feet. An empty slot's inspector says what fits it, or that nothing made in Ward does.
> When the page is narrow the boxes drop their illustration (88 pixels wide).

and in the Layout paragraph, after "The field pack gains a HOTBAR strip under the grid: …":

> Cells 1 and 2 (weapons) have a duller frame and a small gap before 3; while a cell or a pack item is dragged the cell
> under it takes the focus frame and the dragged one dims. The strip's help line names the verbs.

**AGENTS.md**, a new row in section 3:

> | Loadout fixes | 20 Nov 2026 (`art/loadout_fix_20261120`, `Editor/LoadoutFixPass20261120.cs`, `Scripts/AnatomyLayout.cs`): Carl's playtest notes. EYE implant slot (`implant_eye`, empty: no eye implant exists; Neural Targeting stays in HEAD; old saves load unchanged); implant and armour leaders end on the body part their slot names at every window size (anchors on the figure image, boxes beside the figure); no bare "Head" under the maps; leftover hotbar drag labels fixed (one label at most, ended by release, Escape, page change or closing); the pack's HOTBAR strip reorders by drag or focused cell + number key, 1–2 fixed to the weapons, order saved. Native on `Builds/batch-p2-ui3`: loadout check (`unity/tools/capture_loadout_native.py`), inventory redesign, interface, home/journal. Not yet accepted by Carl. |
