# Ward Window Interior (`Athen Hill/Ward Window Interior`)

An opaque URP 17.6 lit shader for shop and loft windows. It shows a believable room
behind every pane, lit by daylight in the day and by room lamps at night. It replaces
the flat, near-black `WardGlass` (URP/Lit, base colour about .024/.045/.048).

The shader uses only world position and the geometric normal. So it still works
after `StaticRenderChunksEditor.Rebuild` merges the panes into chunk meshes, where
the per-pane UVs are metric but have arbitrary offsets.

Status (30 Sep 2026): the shader was written without opening Unity. It has had two
checks:

- **Compile check:** every pass compiles with `glslangValidator` (HLSL to SPIR-V)
  against stub declarations that match the URP 17.6 signatures in
  `Library/PackageCache`. Variants covered: base, cluster light loop with light
  layers and rendering layers, additional lights, DepthOnly, and DepthNormals with
  oct normals and smoothness.
- **Visual check:** the room and glass logic was mirrored on the CPU (numpy) and
  rendered by day and night against the real pane layout.

**No native Unity compile, capture or GPU timing exists yet.**

## Integrate

1. **Switch the material.** Set the shader of
   `Art/Quality/RelayArchitecture/Revision02/Materials/WardGlass.mat` to
   **Athen Hill/Ward Window Interior**. The 27 window renderers under
   `Ward shop architecture/.../Window and reveals` and `Upper construction`, and
   their render chunks, all reference this asset. No chunk rebuild is needed.
2. **Set `_EmissionColor` after switching.** The old material stores black, which
   would leave every room lamp off. Use HDR (3,3,3).
   Also set `_Smoothness` to 0.93. The old value of 0.72 carries over and makes the
   glass look frosted.
   The old URP/Lit values (`_BaseColor`, `_Metallic` and so on) are ignored.
3. **Add `WardGlass.mat` to `CityLightCircuit.emissiveMaterials`** on the city light
   circuit in `Scenes/AthenHill.unity`, which currently lists 4 materials.
   - At runtime the circuit clones the material, enables `_EMISSION` (harmless,
     because this shader has no such keyword), and swaps the clone onto every
     renderer, chunks included.
   - Each frame it writes `_EmissionColor = authored × lerp(daytimeStrength 0.04, 1, clock.LampStrength)`.
     Lamps, bulbs, standby LEDs and backlit blinds all come from `_EmissionColor`,
     so the whole interior dims by day and brightens at night.
4. **Rerunning the Editor pass.** `WardRelayArchitecturePass.Supplemental("WardGlass")`
   builds a URP/Lit `WardGlass` material. Rerunning that pass would bring the black
   glass back, so re-apply steps 1–2 afterwards.

## Rooms and the default grid

Rooms sit on a world grid behind each facade. The grid is set by `_RoomSize`
(width × height × depth in metres) and `_RoomOffset` (grid origin; its Y is a floor
level). It is placed along the facade using the horizontal normal. Axis-aligned
facades within about 5° snap exactly to the world axes; any other facade keeps its
own frame.

The defaults come from the saved scene:

- **Shop positions.** All shops stand at world Y 0.5, rotated ±90°. Their glass is
  at x = ±18.02, and the shop centres are at z = ±9 and ±18.
- **Width.** `_RoomSize` = (9, 3.4, 4) with `_RoomOffset` = (4.5, 0.5, 4.5) puts room
  boundaries only on shop edges (z = ±4.5, ±13.5), so no pane shows a partition.
  Each shop floor is one continuous room.
- **Why not 4.5 m.** A 4.5 m grid would give two rooms per floor, but a partition
  would cut the centre panes of `thread_hide` and the `tool_exchange` clerestory. A
  12 cm wall end is drawn wherever a boundary crosses glass.
- **Floor levels.** Floors fall at world Y 0.5 and 3.9. Display-window sills then sit
  0.83 m above the ground floor, and loft sills 0.75–1.15 m above the upper floor.

**Room contents.** Hashes of (room cell, facade) decide each room's contents:

- **Use:** ground floors become shops, workshops or stores; upper floors become
  dwellings, workshops or stores.
- **Surfaces and materials:**
  - wall palette: limewash, ochre, grey-green, whitewash, terracotta or concrete
  - dado and skirting, and scuffed lower walls
  - floor: concrete, tile or planks
  - ceiling: beams and conduit
- **Back-wall detail:** a doorway, a pegboard with hanging tools, or a hanging
  textile.
- **Furniture (two parallax planes):**
  - shelving with goods
  - a fabricator cabinet with cyan standby LEDs and a display
  - a wardrobe
  - a counter with goods
  - a workbench with a stool and vise
  - a table, chair and potted plant
  - stacked crates
- **Lamp:** a pendant with shade, cord and bulb, or a tube fitting in cool rooms.
- **Window coverings:** roller blinds, slatted blinds with light between the slats,
  or curtains in 1.5 m bays, at a random level. When the room is lit they glow from
  behind.

Change `_RoomSeed` to re-deal every room.

## Properties (defaults)

| Group | Property | Default | Notes |
| --- | --- | --- | --- |
| Rooms | `_RoomSize` | (9, 3.4, 4, 0) | Width, height, depth (m). |
| | `_RoomOffset` | (4.5, 0.5, 4.5, 0) | World origin of the grid; Y is a floor level. |
| | `_RoomSeed` | 0 | Re-deals room types, lights and blinds. |
| | `_WallTint` | white | Multiplies the wall palette. |
| | `_FurnitureAmount` | 0.85 | Share of rooms that have furniture. |
| | `_BlindAmount` | 0.6 | Share of rooms with blinds or curtains. |
| Daylight inside | `_InteriorDaylight` | 0.5 | Fraction of the facade's ambient SH that lights the room, fading with depth. |
| | `_InteriorFill` | (.012, .011, .010) | Constant floor level, so unlit rooms are never pure black. |
| | `_SunSpill` | 0.35 | Main light (shadowed at the glass, and only when the sun faces the facade) spilling onto the floor near the window. |
| Night lights | `_EmissionColor` (HDR) | (3, 3, 3) | Room-light intensity. **CityLightCircuit scales it.** Keep it near neutral; the tints below carry the colour. |
| | `_LitFraction` | 0.55 | Share of rooms with a lamp on. |
| | `_CoolFraction` | 0.3 | Share of cool tech lights (1.8× more likely in workshops, 0.6× elsewhere). |
| | `_WarmLight`, `_CoolLight` | (1, .62, .32), (.55, .86, 1) | Tungsten and cyan-white tints. `_CoolLight` also colours the LEDs. |
| | `_LampRange` | 2.6 | Lamp falloff radius (m). |
| Glass | `_GlassTint` | (.86, .94, .93) | Tint on the transmitted room image. |
| | `_Smoothness` | 0.93 | Glass smoothness; dust lowers it toward 0.35. |
| | `_ReflectionStrength` | 1 | Scales the Fresnel-weighted environment reflection. |
| | `_DirtColor`, `_DirtAmount`, `_DirtScale` | (.42, .36, .28), 0.45, 1.6 | World-space haze and faint drip streaks. |
| | `_EdgeGrime` | 1 | Grime where SSAO finds the sill, mullions and reveals, which are the pane edges. |
| Atlas (optional) | `_UseRoomAtlas`, `_RoomAtlas` | off, black | Replaces the procedural walls and furniture; blinds and lamps stay. |
| | `_AtlasGrid` | 2 | Tiles per side of the atlas (2 or 4). |
| | `_AtlasBackWallScale` | 0.5 | How much of each tile the back wall fills. |

For the atlas, author each tile as a one-point-perspective view through the window,
with the back wall filling `_AtlasBackWallScale` of the tile.

## Technique

1. **Facade frame.** The shader takes the horizontal normal N and the along-facade
   axis T. Facade coordinates are (dot(pos − origin, T), y). The room cell index and
   the local entry point come from those coordinates.
2. **Room intersection.** The view ray, in room space (T, up, −N), is intersected
   with the room box using a slab test to find the back wall, side walls, floor and
   ceiling.
3. **Parallax planes.** The front furniture plane (0.8–1.6 m deep), the back plane,
   and a blind plane 4 cm behind the glass are each hit analytically.
4. **Antialiasing.** Every procedural edge is antialiased with `fwidth` taken outside
   branches, and branches only pick between room types.
5. **Interior lighting:**
   - daylight: the ambient SH seen by the facade, × `_InteriorDaylight`
   - sun spill through the window
   - a lamp with a shaded cone and inverse-square falloff, plus a floor pool
   - bounce light and fill
6. **Glass:**
   - Schlick Fresnel (F0 0.04)
   - `GlossyEnvironmentReflection` with a slightly wavy normal; this supports probe
     blending, box projection and the Forward+ probe atlas
   - GGX specular from the main light and additional lights, shadowed, with light
     layers and the cluster loop
   - a dust layer lit by the sun and SH, which also takes a little hazy glow from lit
     rooms
   - `MixFog`
7. **Passes.**
   - Included: UniversalForward, DepthOnly, and DepthNormals (writes smoothness when
     `_WRITE_SMOOTHNESS` is on, and rendering layers).
   - No ShadowCaster: windows do not cast.
   - No Meta pass.
   - SRP Batcher compatible.

## Cost (estimate)

The optimized SPIR-V holds about 1,550 static ALU operations across all
room-type branches. Each pixel runs one type branch, so roughly 700–900 operations
plus the URP lighting, probe sampling and cluster loop. That is about 1.5–2× URP Lit
per pixel.

Windows cover a small part of the screen, so frame cost should be small. Measure it
in the Frame Debugger or profiler with a window filling the screen.

## Limits

- **Emission only:** the interior is emission-only. It ignores scene point lights
  except the sun spill; street lamps show only as glass specular.
- **SSAO:** the pane-edge grime needs SSAO in the lit pass (`AfterOpaque` off, as in
  `PC_Renderer`). Without SSAO only the haze and streaks remain.
- **Not compiled:** screen-space reflections, DOTS / GPU Resident Drawer (disabled in
  `PC_RPAsset`), lightmaps and the deferred GBuffer path. The renderer is Forward+.
- **Grid seams:** the room grid is per world, not per pane. Other building layouts
  need `_RoomSize` and `_RoomOffset` tuned, or they will show partition ends in their
  panes.

## Tune first (native, matched cameras, day and night)

1. Night readability: `_EmissionColor` intensity and `_LitFraction`.
2. Daytime balance against the sunlit facade: `_InteriorDaylight` and
   `_ReflectionStrength`.
3. Dust: `_DirtAmount` and `_EdgeGrime`. In the CPU preview a heavier setting read
   as rain streaks.
4. Try another `_RoomSeed` if the current mix of room types or lights looks
   repetitive.

Also check that no windows show a partition, and that toggling Reduced Motion is
irrelevant here (nothing in this shader animates).
