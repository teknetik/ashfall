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

## Colors

Cyan identifies focus, interaction and lattice energy. Bronze belongs to structural edges. Warm white carries text; muted text remains readable on opaque dark surfaces. Red and cyan differentiate vitality and nano.

## Typography

Compact humanist sans lettering follows the reference. At 1080p, small HUD labels are 14–16 reference pixels, ordinary text 18, dialogue 22, modal titles 30. Below 1500 pixels wide or 900 pixels high, HUD labels increase to 20 reference pixels, including when resizing without changing aspect ratio. Text stays native and selectable by UI bindings; illustrations contain no words.

## Layout

Identity and vitals share the upper-left instrument panel. A heading compass centers above the city. Field notes and a utility strip sit upper-right. Local log sits bottom-left, a compact ten-slot hotbar bottom-center, keyboard hints bottom-right. The bar is 688 × 90 reference pixels, with ten approximately 64-pixel square slots. Slots 1–6 retain their illustrated actions; 7–0 are empty reserves. The center remains open. A compact arrangement reduces peripheral widths for narrow windows. Modal content has consistent headers, inset rows and a bounded scrolling area.

Every HUD group and modal can be moved by its frame, header or small bronze grip. Ctrl-drag also works over controls without activating them. Positions persist across restarts and stay within the window when resized. NPC nameplates retain a movable offset from their character. Pause provides **Reset UI positions** to restore the authored layout.

## Elevation & Depth

Frames use original scalable artwork: a recessed black edge, bronze bevel, light upper rim, dark lower rim, small steel corner joints and restrained scratches. Item illustrations carry volume. Avoid bloom on whole panels; cyan illumination is a control state.

## Shapes

Clipped frame corners and rectangular inset controls. Small diamond markers identify colonists and progress. The Free Column insignia is original geometric artwork.

## Components

Shared nine-slice frame and button artwork. Hover brightens the inset, keyboard focus gains a cyan perimeter, pressed states darken, disabled states dim. Hotbar items retain compact number keycaps and labels, with square cells and prominent illustrations in a low bar. Trade and inventory rows share the same item illustrations. Dialogue, shop, lattice, notes, credits and pause share modal chrome. Lattice progress, drag grips and scrollbars use this palette.

## Do's and Don'ts

Preserve named controls and game data. Keep decorative children from intercepting mouse input. Use real heading, credits, quantities and objective state. A local event log must not look like a working multiplayer message field. Preserve reduced-motion behavior and keyboard access.
