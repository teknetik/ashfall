# Docs snippet — hydroponics greenhouses (1 Oct 2026)

For the orchestrator to merge. Numbers are from `unity/evidence/hydroponics/20261001/README.md`.

## For unity/EDITING.md

## Hydroponics greenhouses (1 October 2026)

**Ward hydroponics** fills the two retrofit quonsets (`Ward district retrofit/Hydroponics bays`) and the ground round
them. It holds:

- **Interior**: 14 prefab instances at their authored pivots (`Prefabs/Hydroponics/Interior/HY_Fitout_A/B` and twelve
  `HY_Crops_<bay>_<side>_<third>` crop sections, each a 3-level LODGroup: full plants within about 9 m, reduced heads to
  about 25 m, one cross card per plant beyond). The racks, NFT channels, feed lines, LED bars, vine gutters, fans and
  floor are in the fit-out; lettuces, chard, herbs, seedlings, microgreens, cordon tomatoes and runner beans are in the
  sections. The crop bar LEDs (`HY_LED`) are on the **Ward lighting clock**; the propagation-tier LEDs (`HY_LEDProp`)
  stay on.
- **Yard**: 58 prefab instances in 12 vignette groups (*harvest by the A door*, *potting bench*, *nursery under shade*,
  *growers' rest bench*, *cart loaded for the market*, *nutrient totes*, *dosing* …), each group's origin at its centre,
  with ground grime/scuff decal projectors. `HY_crate_*`, `HY_basket_*` and `HY_pot_*` nest the street kit's scanned
  crate, basket or pot (`Prefabs/StreetDressing`) with a produce fill. Stools and the bench carry **NPC sit point**
  markers. Nothing in the yard is a render-chunk source: move, duplicate or delete instances directly.
- **Grow glow lights**: four night-only point lights inside the bays on the light circuit (`practicalLights` and
  `nightOnlyLights`).
- **Retrofit planters and tank fittings**: a filtered copy of the retrofit's `Hydroponics bays Detail` mesh
  (`Art/Hydroponics/Retrofit/Hydroponics_bays_Detail_kept.asset`) without its 93k triangles of desert succulents.

Retired by the one-time **Install** (inactive, kept for rollback): `Hydroponics bays Detail` and `Hydroponics bays
Glow`. The `Hydroponics bays Structure` renderer's polycarbonate slot is a prefab-instance override to `HY_Polycarbonate`
(dust/condensation film, double-sided, **no shadow pass** so sun reaches the crops); revert that override to restore the
retrofit skin. The quonsets keep their solid colliders (they are not enterable).

Change geometry through `art/hydroponics_20261001` (Blender: `author_hydroponics.py --only interior|props`; textures:
`prepare_textures.py`; layout: `layout.py`, which checks colliders, door thresholds and walking lines) and **Athen Hill →
Hydroponics → Build assets** (re-imports, rebuilds materials and prefabs; scene instances update). Materials are in
`Art/Hydroponics/Materials` (crops use **Athen Hill/Ward Ground Cover** with no wind and leaf transmission). Crop
sections cast shadows only within their LOD0 range, through a shadow-only copy of the LOD1 heads. Review cameras `cam_hy_*`
(**Hydroponics review cameras**); evidence, the rollback scene copy and the A/B (+0.73 ms day / +0.98 ms night at the
yard's own wide view, +0.14 ms at `cam_hill`) in `evidence/hydroponics/20261001`. For a timing A/B use
`HydroponicsPass abbuild:on|off` (both arms from one snapshot; the saved scene is not changed).

## For the AGENTS.md baseline table (§3)

| Hydroponics greenhouses | 1 Oct 2026 (`art/hydroponics_20261001`, scene root **Ward hydroponics**): both quonsets fitted out (racks, NFT channels, feed lines, LED bars on the light clock, vine gutters) and planted in 12 LOD'd crop sections (lettuces, chard, herbs, seedlings, tomatoes, runner beans); polycarbonate skin copy with film and no shadow pass; working yard of 58 props in 12 vignettes (harvest crates, potting bench, nursery under shade with drying herbs, rest bench with sit points, market handcart, nutrient totes, dosing trolley, compost, herb planters); retrofit Detail (succulents) and Glow inactive. Quonsets still solid. Not yet accepted by Carl. |
