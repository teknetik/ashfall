---
name: Athen Hill field interface
description: Worn colony equipment framing an open view of the city.
colors:
  primary: '#58d5d7'
  brass: '#a48a62'
  surface: '#161e1e'
  text: '#eee9dc'
  muted: '#bcbcad'
  vitality: '#c65c4f'
typography:
  body:
    fontFamily: Liberation Sans Narrow
    fontSize: 18px
    fontWeight: 400
  title:
    fontFamily: Liberation Sans Narrow
    fontSize: 30px
    fontWeight: 400
spacing:
  small: 8px
  medium: 16px
  large: 24px
---

## Overview

The supplied reference is the visual authority. The interface reads as worn colony equipment: bronze rails, clipped corners, inset charcoal enamel and restrained cyan indicators. This applies to every HUD element and every modal.

The startup menu uses original Ward arrival artwork with an ivory Athen Hill title,
bronze controls and restrained cyan focus. **Start Game** enters the existing West
Gate spawn; **Settings** opens the shared sound/video panel, including reduced
motion, and returns to the startup menu. The city HUD stays hidden and gameplay
stays blocked until Start Game. Escape cannot bypass this screen. Music remains
active in the menu and settings. The background is menu illustration, not an
in-game capture. Edit **UI/StartupMenu.uxml** and **UI/StartupMenu.uss** in UI Builder;
the original artwork and generation prompt are in **UI/MenuArt**.

## Colors

Cyan identifies focus, interaction and lattice energy. Bronze belongs to structural edges. Warm white carries text; muted text remains readable on opaque dark surfaces. Red and cyan differentiate vitality and nano.

## Typography

Compact humanist sans lettering follows the reference. At 1080p, small HUD labels are 14–16 reference pixels, ordinary text 18, dialogue 22, modal titles 30. Below 1500 pixels wide or 900 pixels high, HUD labels increase to 20 reference pixels, including when resizing without changing aspect ratio. Text stays native and selectable by UI bindings; illustrations contain no words.

## Layout

Identity and vitals share the upper-left instrument panel. A heading compass centers above the city. Field notes and a utility strip sit upper-right. Local log sits bottom-left, a compact ten-slot hotbar bottom-center, keyboard hints bottom-right. The bar is 688 × 90 reference pixels, with ten approximately 64-pixel square slots. Slots 1–6 retain their illustrated actions; 7–0 are empty reserves. The center remains open. A compact arrangement reduces peripheral widths for narrow windows. Modal content has consistent headers, inset rows and a bounded scrolling area.

Warden radio lines (field briefings) have their own panel under the compass: one line at a time, on screen for its reading time (about 0.3 s a word, 5–24 s), queued rather than replaced, and counting down only during play. Short notices sit directly below it while a line is up; salvage pickups use the toast under the utility strip and the local log, never the notice banner.

Outer Berms additions (2 October 2026): in the Berms the compass carries small rotated-square markers for the places the Wardens have marked (amber sites, dimmed once cleared; cyan waystation once found; pale West Gate), and the one under the centre of the compass is named with its distance just below the compass. Incoming damage shows a short red bar on a ring 178 reference pixels round the crosshair, turned toward the attacker and fading in about two seconds; it appears only when hurt, so the centre stays open.

The field fabricator and Basic General use a wide modal (1400 reference pixels, at most 96 % of the window). The fabricator shows schematics, the selected schematic (parts, actions, guidance) and the pistol (three slot cards and a Stat / Now / With mod / Change table) side by side; Basic General shows Supplies and Buy parts beside Sell salvage. Both fit at 1080p; in smaller windows the modal scroll view follows keyboard focus.

The field pack (Tab / 5) follows the user's **Ashfall inventory references of 2 October 2026**, superseding the 30 September pack composition while retaining Ward's bronze frame, dark teal enamel, ivory lettering and restrained cyan focus. At the 1920 × 1080 reference size, the modal is 1740 reference pixels (at most 97% of the window). The left pack has search, catalogue filters, 64-pixel item cells with 47-pixel illustrations and quantities, and separate live **slots** and **carry weight** meters. One carried item-type stack occupies a slot; the model also enforces stack caps, pack weight and total carried weight. Capacity is data, never inferred from decorative empty cells.

The selected-item inspector sits **immediately to the right of the pack grid**. One click or arrow-key selection updates its larger illustration, description, unit weight, stack limit, trade value, equipment requirements and known crafting uses. Selection keeps the grid and filters interactive. Schematics use that same inspector for the selected recipe's parts. The next region has **PRIMARY / SECONDARY / STATS / IMPLANTS / ARMOUR** tabs. Primary and Secondary each show the actual item illustration, named attachment sockets and expandable effective weapon statistics; the separate pane renders a mesh-only copy of that weapon under studio lighting, rotated by dragging. A catalogue `previewPrefab` can provide any weapon, with the authored Scrap Pistol and Field Rifle as current sources. The copy runs no gameplay scripts and cannot appear in the world camera.

**Implants are strictly two dimensional.** The generated anatomical scan has positioned body slots; selecting an installed implant opens its details and exactly three augmentation sockets. Selecting a socket opens a further panel for the installed augmentation and compatible carried candidates. The 3D camera is disabled throughout this tab. **Armour** uses the same body-slot language with the live colonist preview alongside it. Selected pieces expose their authored component sockets (for example chest plates and leg motors), with real requirements, inventory transfers and stat effects. The preview currently depicts the supplied colonist mesh; component installation does not invent a separate visible armour mesh. Empty slots explain what can be fitted, and rejected changes preserve inventory and report the reason.

Keyboard arrows traverse the pack; Up from the top row reaches filters and then tabs. The search field retains text input. Tab reaches loadout tabs, equipment slots, modification candidates and actions. Focus and selected equipment use a cyan border. Dragging a carried item to a compatible equipment or weapon socket uses the same model transaction as **Equip selected**; dragging installed equipment back to the pack removes it. Augmentation installation and removal use the nested socket panel. Escape closes the pack (or cancels an active drag / explicit external item inspection first).

Every HUD group and modal can be moved by its frame, header or small bronze grip. Ctrl-drag also works over controls without activating them. Positions persist across restarts and stay within the window when resized. NPC nameplates retain a movable offset from their character. Pause provides **Reset UI positions** to restore the authored layout.

## Elevation & Depth

Frames use original scalable artwork: a recessed black edge, bronze bevel, light upper rim, dark lower rim, small steel corner joints and restrained scratches. Item illustrations carry volume. Avoid bloom on whole panels; cyan illumination is a control state.

## Shapes

Clipped frame corners and rectangular inset controls. Small diamond markers identify colonists and progress. The Free Column insignia is original geometric artwork.

## Components

Shared nine-slice frame and button artwork. Hover brightens the inset, keyboard focus gains a cyan perimeter, pressed states darken, disabled states dim. Hotbar items retain compact number keycaps and labels, with square cells and prominent illustrations in a low bar. Trade and inventory rows share the same item illustrations. Dialogue, shop, lattice, notes, credits and pause share modal chrome. Lattice progress, drag grips and scrollbars use this palette.

## Do's and Don'ts

Preserve named controls and game data. Keep decorative children from intercepting mouse input. Keyboard: one arrow press is one step (lists and grids handle UI Toolkit's navigation event themselves; grid columns come from the laid-out tiles); a list is one Tab stop whose focus never changes the selection; every scroll view scrolls the focused control into view; after an action disables its own button, focus moves to the nearest usable control. In play the HUD cannot hold keyboard focus: WASD, arrows, Tab and Enter never navigate or press HUD buttons (they have hotkeys). Use real heading, credits, quantities and objective state. A local event log must not look like a working multiplayer message field. Preserve reduced-motion behavior and keyboard access.
