# Scrap Pistol mod attachments v1 (30 September 2026)

These are the visual attachments for the six Scrap Pistol mods, one per crafted item. Each slot (grip, barrel, cell)
has a Mk I and a Mk II. I authored them in Blender 5.2.1 as hard-surface models around the actual
`Art/OuterBerms/ScrapPistol.glb` and checked them against the first-person hands (`PlayerFPHands_v5.glb`) placed as
the view model places them.

**Status:** ready for a Unity audition (AGENTS.md §5 step 6). Nothing under `unity/AthenHill/Assets` was touched and
Unity was not run. They have not been tested in a native build.

**Provenance:** original work, built procedurally in Blender by the scripts in `src/`. No Meshy credits and no
external assets were used.

## Files

| Path | What it is |
|---|---|
| `export/PistolMods.glb` | Blender glTF exporter output (Y-up, Apply Modifiers, normals and tangents, one UV set). It holds six top-level nodes named after the mod item ids, each with an identity transform, with mesh data in ScrapPistol.glb's own glTF units and axes. Its two materials embed the atlas (glTF PBR: baseColor, metallicRoughness = ORM, normal, occlusion, emissive). The file is 17 MB. |
| `export/PistolMods_BaseColor.png` | 2048², sRGB |
| `export/PistolMods_Normal.png` | 2048², tangent space, OpenGL +Y (Unity convention), linear |
| `export/PistolMods_MaskMap.png` | 2048², linear RGBA: **R metallic, G ambient occlusion, B 0, A smoothness** |
| `export/PistolMods_Emission.png` | 2048², sRGB. Black except the emitter islands, normalised so the brightest texel is 1 (relative strengths are kept). |
| `export/PistolMods_ORM_gltf.png` | glTF packing (R AO, G roughness, B metallic). It is the same data the GLB embeds and is not needed for URP. |
| `export/mods_manifest.json` | Triangle counts, per-slot triangle counts, hand clearance, texel density and muzzle points in every frame |
| `export/verify_reimport.json` | Re-import check (see Verification) |
| `source/pistol_mods_v1.blend` | Assembled source in the metric frame, on the pistol with the FP hands. It has the baked runtime materials and the procedural authoring materials. |
| `src/` | `build_all.py` (build, clearance, UV, bake, export), `mods_{grip,barrel,cell}.py`, `pm_geo.py`, `pm_mats.py`, `review.py`, `verify_export.py`, `make_sheets.sh`, plus the probes used to find free space |
| `review/` | Renders from the **exported** GLB re-imported next to ScrapPistol.glb. The `sheet_*.png` files are contact sheets. |
| `work/` | Inspection renders, free-space maps, logs. These are scratch files. |

Rebuild everything with `./run_blender.sh src/build_all.py`, then `src/verify_export.py`, then `src/review.py`, then
`src/make_sheets.sh`. The build takes about 8 minutes and the renders about 15 minutes, all on the CPU.

## Frames and conventions

- In ScrapPistol.glb (a single node with an identity matrix), the muzzle points along **glTF −X**, up is +Y, and the
  player's right is −Z. The pistol is about 1.9 glTF units long. In game it is scaled by **0.13674**, which makes it
  0.26 m long.
- glTFast negates X on import. In the Unity mesh-local space of the ScrapPistol object the barrel is therefore **+X**.
  AttachPistol then rotates the mesh −90° about Y inside the holder (`Berms held pistol` / `View model pistol`,
  metres), so the barrel runs along holder +Z.
- The attachments use exactly the same space. **Parent the instantiated `PistolMods` root (or each child) under the
  ScrapPistol instance with local position 0, rotation 0 and scale 1**, and they sit in place in both the view model
  and the third-person held pistol. Do not rescale them: the parent already carries the 0.13674 scale.
- I verified the whole chain by fitting the glb vertices to `pistol_frame.json`/`.obj` (residual 5e-6 m) and by the
  FP hands landing on the grip exactly as they do in game.

## The six attachments

| Item id (node name) | Tris | Slot 0 `MI_PistolMods` / slot 1 `MI_PistolMods_Emissive` | Where it sits |
|---|---|---|---|
| `grip_stabilised_pistol` (Mk I) | 2,128 | 2,128 / 0 | A rubber band around the lower grip, from under the lower leather strap down to the base pad. A Warden-orange riveted brace with a palm swell runs down the backstrap, round the heel and onto the base. |
| `grip_gyro_braced` (Mk II) | 5,408 | 5,088 / 320 | A gyro drum made from a feral droid's actuator hangs under the base plate. It has bone-white droid paint with an orange panel band, a gunmetal flange with 6 bolts, windows onto a brass flywheel and a **cyan status ring** on the rear cap. It sits in a bolted saddle. An alloy brace bar with lightening slots runs up the backstrap, with a cable and connector. A small **gyro status repeater (cyan LED facing the shooter)** is clipped to the frame's left rear above the support thumb. |
| `barrel_bored_alloy` (Mk I) | 3,574 | 3,574 / 0 | A bored alloy sleeve over the pistol's muzzle ring, held by a **worm-drive hose clamp** (band, housing, slotted hex screw, tail, collar relief slits). It has three rows of cooling slots onto a finned inner barrel, a ported crown with temper colours and a Warden-orange band. It adds 45 mm to the length. |
| `barrel_lattice_focused` (Mk II) | 4,444 | 4,204 / 240 | A machined collar with 3 socket screws and an octagonal anodised focusing shroud. Side windows show six copper focusing coils around a glowing lattice filament, and the top has vent ports. A three-claw cage holds a **faceted lattice crystal behind a salvaged optic** (a knurled brass bezel and a glowing lens). It adds 92 mm to the length. |
| `cell_salvaged_capacitor` (Mk I) | 4,202 | 4,202 / 0 | A salvaged can capacitor (teal sleeve, polarity stripe, vent-scored alloy top, rubber bung) on the **left** of the dust-cover rail. Two P-clamps with rubber liners hold it, and the front clamp is packed out with two washers because the rail narrows there. Brass post terminals with ring lugs feed a pair of wires into a grommet in the frame. |
| `cell_overclocked` (Mk II) | 2,688 | 2,522 / 166 | A finned, anodised overclocked cell in the same place. It has **twin glowing core windows** on the outer face, **glowing vent channels** between the top fins, a Warden-orange front plate, a **lattice-shard window** on the rear boss, through-bolts (with a spacer at the front) and a braided cable into the grommet. |

Everything is within the 1.5–6k triangle brief. The atlas is 2048² shared by all six at about **4.8–5.1 texels/mm**
(47 % coverage, 4 px gutters, dilated). At the hip eye, 0.4–0.6 m away at 1080p, that is roughly 2 texels per screen
pixel.

### Hand clearance (PlayerFPHands_v5 in its view-model pose)

| Mod | Vertices inside the hands | Minimum gap |
|---|---|---|
| Barrels, cells | 0 | ≥ 27 mm (cells), not near (barrels) |
| `grip_gyro_braced` | 0 | 6.7 mm |
| `grip_stabilised_pistol` | 8 of 1,472 (worst 0.52 mm deep) | 0.07 mm |

The rubber wrap was thinned automatically wherever a finger comes within 0.3 mm (75 vertices). It is never thinned to
less than 0.15 mm above the real grip. The remaining 8 vertices are in two spots where the v5 hands already touch the
pistol's own grip panel, at the top of the band on the left and at the lower right. They sit under fingers and cannot
be seen from the eye.

## Muzzle points (where the flash should emit with the barrel fitted)

The stock `Muzzle` transform is **not on the bore**. It sits at the front of the lower dust cover, about 29 mm below the
bore axis. Both barrel points below lie on the real bore axis at the crown or optic face.

| | glTF pistol units | Unity ScrapPistol mesh-local (glTFast, X negated) | Unity holder frame, metres (the `Muzzle` transform's parent) |
|---|---|---|---|
| `barrel_bored_alloy` | (−1.28346, 0.43038, −0.00548) | (1.28346, 0.43038, −0.00548) | **(0.00142, 0.05897, 0.25926)** |
| `barrel_lattice_focused` | (−1.63083, 0.43038, −0.00548) | (1.63083, 0.43038, −0.00548) | **(0.00142, 0.05897, 0.30676)** |
| stock Muzzle today (reference) | (−0.95166, 0.21771, −0.00088) | (0.95166, 0.21771, −0.00088) | (0.00079, 0.02989, 0.21389) |
| stock bore mouth (optional fix) | (−0.95143, 0.43038, −0.00548) | (0.95143, 0.43038, −0.00548) | (0.00142, 0.05897, 0.21386) |

Move the existing `Muzzle` child of the holder rather than parenting a new one under the mod mesh. Under the mesh it
would inherit the 0.13674 scale and shrink the flash card. The view model and the held pistol share the same holder
layout, so the same holder-frame values serve both.

## Unity integration notes

1. **Import:** copy `PistolMods.glb` and the four PNGs (BaseColor, Normal, MaskMap, Emission), for example to
   `Art/OuterBerms/PistolMods/`. glTFast's default materials already look right because the textures are embedded.
   For project-standard URP materials:
   - `MI_PistolMods`: URP/Lit, Metallic workflow, opaque. Base Map = BaseColor. Metallic Map = MaskMap (Smoothness
     source Metallic Alpha, slider 1). Normal Map = Normal (texture type Normal map, strength 1). Occlusion =
     MaskMap (G, strength 1; lower to about 0.7 if it looks heavy with SSAO).
   - `MI_PistolMods_Emissive`: the same, plus Emission on. Emission Map = Emission, colour HDR white at about
     intensity 3–4 (the glb uses emissive strength 4), Global Illumination None. The cyan is in the texture.
   - Texture import: MaskMap and Normal are linear (clear sRGB; Normal as type Normal map). BaseColor and Emission are
     sRGB. Max size 2048, aniso 4–8, mip streaming on.
2. **Per loadout:** parent the six nodes under **both** ScrapPistol instances, the view model one and the
   third-person one. Enable only the fitted item in each slot and disable the others; the node name equals the
   item id. The view-model copies need the pistol's view-model layer on every child (as `FPGripPass.Attach` does for the
   hands) and shadows Off, matching the pistol. The third-person copies can cast shadows.
3. **Muzzle:** when a barrel is fitted or removed, set the holder's `Muzzle` localPosition to the table values in
   both the view model and the held pistol. The tracer and muzzle light read `viewModel.muzzle` and
   `combat.muzzlePoint`.
4. **Emission and bloom:** the emitters are small, so check that bloom does not wash the Mk II crystal and lens into
   a blob at the hip view.
5. **Not checked here:**
   - The third-person colonist's hand has no fingers. The Mk II drum hangs about 25 mm under the base and the Mk I
     brace tab wraps the heel, so check the held pistol against the colonist's hand and forearm in the aim pose.
   - No LODs are provided. These objects are always within about 1 m of the camera for the owning player, so LOD0
     only is reasonable. Add a LOD1 if other players ever see them at range.

## Verification

- `src/verify_export.py` re-imports `PistolMods.glb` with Blender's official importer next to ScrapPistol.glb, with
  the root scaled by 0.13674. It checks the result against the metric source objects in `source/pistol_mods_v1.blend`:
  - all six nodes are present, top-level, with identity transforms;
  - triangle counts match;
  - the maximum vertex deviation is **0.0000 mm**;
  - the UVs and the two material slots survive the round trip.

  The results are in `export/verify_reimport.json`.
- Every review image is rendered from that re-imported GLB with its embedded baked textures, not from the authoring
  scene.

## Review renders (`review/`, all from the exported GLB)

The FP images use the in-game hip eye from `pistol_frame.json`: 50° vertical FOV, with the pistol pose relative to the
camera. The FP hands render with the neutral grey material they carry in their glb, because Unity assigns the real
hand materials in FPGripPass. The world is levelled with a 5° down look, and each image is a crop of a 2880×1620 render. "Sun" is a warm sun
behind and left of the shooter with a dim sky. "Shade" blocks the sun and leaves skylight only.

- `sheet_<mod>.png` for each mod: FP hip and 3/4 views, in sun and in shade.
- `sheet_combo_mk1.png`, `sheet_combo_mk2.png`: all three Mk I or Mk II mods fitted, with FP, left and rear-left views
  in sun and shade.
- `sheet_fullframe.png`: the true 1920×1080 hip frame for stock, Mk I and Mk II.
- The individual PNGs are `<mod>_{fp,34}_{sun,shade}.png`, `combo_mk{1,2}_{fp,34,rear}_{sun,shade}.png` and
  `fullframe_*_fp_sun.png`.

### Assessment

- **Barrels and cells: strong.** They have believable construction (clamps, packing washers, terminals, fasteners)
  and read clearly in first person. The cells sit on the camera-facing side. The materials match the pistol's
  palette (weathered steel, rust-orange accents, brass, dark polymer) with edge wear and cavity grime.
- **Weakness: detail density.** The pistol's own texture is a painterly, rust-blotched Meshy map. The attachments are
  crisper and somewhat cleaner, so up close they read as newer parts, which fits "freshly fitted" but is a slight
  style step. The Mk I crown's temper colours are fairly saturated.
- **Grips: limited first-person payoff.** The grip is almost completely covered by the v5 two-hand cup grip, and its
  lower half is below the bottom edge of the in-game hip frame (see `sheet_fullframe.png`). The Mk I wrap and brace
  and the Mk II drum are therefore mainly third-person and inspection visuals. For that reason Mk II has the frame
  status repeater, whose cyan LED is visible just above the support thumb in first person. Mk I has no
  first-person-visible element.
- **Emitters are pale.** The emissive parts render as a pale cyan-white. That is by design for the crystal; the cores
  may want a slightly higher intensity in Unity.
- **Known minor defects:**
  - Some fan-triangulated end caps show faint cross-hatched AO in the atlas. It is not visible in the renders.
  - The Mk II claws are thin bent bars.
  - The rubber wrap's top edge meets the Meshy strap's ragged lower edge, which shows as an uneven seam.
  - A few surfaces are hidden, such as the collar interiors and the rims tucked into the grip. They take atlas space
    but are harmless.
