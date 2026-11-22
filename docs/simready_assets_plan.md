# NVIDIA SimReady Central — Reusable Asset Plan

**Date:** 22 November 2026  
**Target:** `unity/AthenHill` (Unity 6000.6.0f1, URP 17.6.0, glTFast 6.20.0, Linux x86-64)  
**Sources:**
- Catalog UI: https://huggingface.co/spaces/nvidia/simready-central
- Submission index repo: https://github.com/NVIDIA-Omniverse/simready-central (`submissions/` lists 28 datasets, ~4,900+ commit-pinned OpenUSD asset packages)

## Summary

SimReady Central is **selectively reusable** for Ward and the Outer Berms, primarily as **industrial props, workshop dressing, salvage scrap, scanned lived-in clutter, and pre-Fall corporate infrastructure**. Because every package is authored as **OpenUSD** for Omniverse/Isaac Sim rather than game-ready glTF, assets are not drop-in — they require a Blender conversion, LOD/decimation, and weathering pass before importing into `unity/AthenHill`.

## Highest-Value Datasets

Every major multi-asset pack sampled below reports `CC-BY-4.0` in its `com.nvidia.simready.packaging.json` (commercial use and modification allowed with attribution). Always verify the exact `license` field per imported package.

| Submission (`submissions/...`) | Assets | Sampled License | Primary Fit for Ward / Outer Berms |
| --- | ---: | --- | --- |
| `NdotLight/SimReady_Assets` | 49 | `cc-by-4.0` | **Highest hit rate.** Yards, Salvage, Repairs, Berms outposts: `h_frame_scaffolding`, `concrete_barrier`, `bollard`, `steel_drum`, `jerrycan`, `gas_cylinder`, `industrial_cabinet`, `storage_rack`, `pallet`, `pallet_stand`, `platform_dolly`, `handtruck`, `frame_cart`, `signal_tower`, `machine_guard`, `anvil`, `angle_grinder`, `crowbar`, `power_drill`, `monkey_wrench`, `spanner`, `pegboard`, `shovel`, `safety_barrier`. |
| `nvidia/simready-assets` | 2,902 | `CC-BY-4.0` | **Deepest prop & scrap library.** Berms/warehouse structures (`modular_warehouse_*`, `structure_beam_*`, `warehouse_*`, `pallet_*`, `box_*`, `drum_*`, `pail_*`, `barrier_fence_metal_*`, `lighting_overheadLed_*`); Salvage/Repairs mechanical scrap (`engineComponent_*`, `bodyPart_*`, `drivetrain_*`, `coolingSystem_*`, `fuelSystem_*`, `electricalSystem_*`, `exhaustSystem_*`, `suspension_*`); workshop gear (`handTool_*`, `powerTool_*`, `serviceTool_*`, `equipment_*`, `furniture_workbench_modular_a01`, `ladder_*`); market/interior dressing (`food_*`, `kitchenware_*`, `dishware_*`, `decor_candle_*`, `paint_*`). |
| `ALLSIDES/simready-scanned-objects` | 150 | `cc-by-4.0` | **3D-scanned real-world props** (better organic silhouettes than CAD for lived-in stalls/interiors): `clay_pot`, `basket`, `lantern`, `crate`, `canteen`, `bucket`, `bolt_cutter`, `chisel`, `clamp`, `metal_file`, `ball_valve`, `electronics_housing`, `earth_anchor`, `toolbox`, `rope`. |
| `M-XR/marso-simready` | 174 | `cc-by-4.0` | **3D-scanned everyday & workshop items:** `ceramic_jug`, `ceramic_pitcher`, `ceramic_bowl`, `enamel_mug`, `coiled_rope`, `carved_wooden_chest`, `folding_step_ladder`, `g_clamp`, `dead_blow_hammer`, `garden_trowel`, `antique_bar_stool`. |
| `Vertiv/simready-assets` | 44 | `cc-by-4.0` | **Pre-Fall corporate infrastructure:** heavy electrical/cooling units (`1800A_MSB`, `400ABusbar`, `PPC_500KVA`, `16OCP_ORV3_racks`, `MCV330_12FAN` chillers, `XDU2300`). Strong silhouettes for Air + Water, Relay Works, Quantum Tube substations, and ruined Berms set-pieces once logos are stripped and weathered. |
| `ForgeCAD/simready-assets` | 76 | `cc-by-4.0` | **Workshop & mechanical props:** `bench_vise`, `bar_clamp`, `combination_wrench_set`, `ratchet_socket_set`, `gate_valve`, `gear_meshing_kit`, `spiral_parcel_chute`, `wheelbarrow`, `attached_lid_tote`, `laboratory_incubator`, `data_connector_pack`, `aircraft_ground_power_connector`. |
| `UCLA-VAIL/UrbanVerse-SimReady-Validated` | 106 | `CC-BY-4.0` | **Street & yard props:** `dumpster`, `bench`, `bollard`, `guard_stone`, `barrel_or_bucket`, `lamppost`, `caution_sign`. |
| `nvidia/isaacsim-assets` + OEM robot repos | 133+ | `CC-BY-4.0` (verify OEM packs) | **Articulated industrial robot arms & grippers** (FANUC, Comau, Robotiq, OnRobot, Franka, Standard Bots) — background nanofab arms, derelict Berms factory arms, or kitbash bases for rogue industrial machines. |
| `PalatialSim/palatial-nv-asset-library` | 957 | `cc-by-4.0` | Indexed by opaque IDs (`D00001`–`D00957`); requires reading package metadata (`index_to_library.py` in the GitHub repo) to catalog contents. |

### Skip / Low Fit
- Modern branded **residential appliances** (`LGElectronics/simready-assets`, clean kitchen appliances) and **hospital/surgical** props — too contemporary and off-tone for Tir/Ward.

## Integration Pipeline (`OpenUSD` -> Unity URP `.glb`)

1. **Pin & record provenance:** Keep the exact commit-pinned Hugging Face URL from `NVIDIA-Omniverse/simready-central/submissions/<org>/<dataset>` and record the package license and attribution in the local `art/` asset folder README.
2. **Verify license & strip branding:** Confirm `CC-BY-4.0` (or compatible commercial license) in `com.nvidia.simready.packaging.json`. Remove any real-world OEM logos/decals from textures and geometry.
3. **Blender conversion pass:**
   - Import the `.usd`/`.usdc` payload into Blender.
   - Check scale (meters), pivot/grounding, and triangle count; decimate CAD-heavy meshes and generate LOD0/LOD1 where appropriate.
   - Convert MDL/Omniverse shaders to standard PBR metallic-roughness textures (albedo, normal, metallic/roughness) compatible with URP / `glTFast`.
   - Reuse or simplify the package's collision meshes if helpful for Unity colliders.
4. **Weathering pass:** Apply Ward/Berms grime, dust, rust, and edge wear so clean digital-twin assets match the masonry/scrap art direction.
5. **Export & validate:** Export `.glb` into `unity/AthenHill`, verify material rendering in daylight and night lighting, and check frame-time impact.

## Suggested Pilot Test

Before batch-pulling assets, run a small 3-asset pipeline validation:
- `NdotLight/SimReady_Assets`: `h_frame_scaffolding`, `gas_cylinder`, `industrial_cabinet` (or `steel_drum`)
- `ALLSIDES/simready-scanned-objects`: 1–2 scanned props (e.g. `clay_pot`, `lantern`, or `toolbox`)

Check: USD import cleanliness in Blender, raw vs. decimated triangle counts, texture/material extraction, and final `.glb` appearance in `unity/AthenHill`.
