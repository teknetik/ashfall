# Ward residents: Meshy records (20 Nov 2026)

Three residents for the city (who and why: `art/ward_residents_20261120/README.md`). Pipeline copied from
`meshy/ward-walkers-20261003/` (concept sheet -> multi-image-to-3D -> rig -> library clips -> `prepare_unity.sh` ->
`Editor/WardResidentsInstall20261120.cs`).

## Status: done, 123 credits

19 Nov 19:51: the free plan refused task creation (402; `blocked_20261119/`). After Carl's upgrade (paid key, balance
1100) the calls below ran 20:50-21:30 (balance 1100 -> 977). The machine rebooted at 20:54 between the models and the
rigs; nothing was re-created (records and balance checked first).

| Key | Resident | Model task | Rig task | Clip tasks | Credits |
| --- | --- | --- | --- | --- | ---: |
| trader | Nadje | `01a1f591-8762-753d-bd9b-02c842fe5d74` | `01a1f5af-79b8-724b-8604-b08032acb9e2` | walk_566 `01a1f5b0-d91f-76d9-8eaa-1411a5286332`, inspect_281 `01a1f5b0-dd09-7356-9c52-a96656f9da60` | 41 |
| clerk | Pell | `01a1f591-9317-7449-ae1d-26c36a29651e` | `01a1f5af-894b-74c1-af1f-8bc59e396045` | walk_566 `01a1f5b0-ebea-7230-be90-3caa92f59e70`, checkout_34 `01a1f5b0-efd6-7018-b0ed-0d31c0236141` | 41 |
| carrier | Oren | `01a1f591-9ed8-71ec-9702-cf8c5094d8c7` | `01a1f5af-9912-72fa-a9d7-0d34aa08f5f1` | walk_553 `01a1f5b0-f744-764b-b018-e4a9030571f8` (unused: 0.17 m/s shuffle), drink_342 `01a1f5b0-fc77-7123-8a69-3960baa81617` | 41 |

Outputs: `<key>/model.glb`, `rigged.glb` (4k base colour, 4k normal, 2k metal-roughness; 66-68 bones incl. fingers,
root `SmartRigArmature`), clip GLBs, `anim_only/`, `rigged_fixed.glb` (LOD0 ~20k with the head protected, LOD1 6k,
re-baked 2k normal), `renders/`. Triangles from Meshy: 61,817 / 61,954 / 61,892. Usage records in `<key>/record.json`
and `ledger.json`.

## Prices checked before spending (docs.meshy.ai/en/api/pricing, 19 Nov 2026)

Multi-Image to 3D with texture: 30 (2k or 4k), 35 (8k), mesh only 20. Rigging 5 per request (finger bones free).
Animation 3 per action. Retexture 10. Remesh 5. Text to Image 3-9.

## Calls as planned

| Key | Resident | Sheet | Height | Clips bought | Credits |
| --- | --- | --- | ---: | --- | ---: |
| trader | Nadje | `concept/trader_sheet_v2.png` | 1.74 | walk_566 (Walking 2), inspect_281 (Female Bend Over Pick Up Inspect) | 41 |
| clerk | Pell | `concept/clerk_sheet_v1.png` | 1.86 | walk_566, checkout_34 (Checkout Gesture) | 41 |
| carrier | Oren | `concept/carrier_sheet_v1.png` | 1.66 | walk_553 (Elderly Shaky Walk), drink_342 (Stand and Drink) | 41 |

Model options: `ai_model latest` (Meshy 7.1), triangle remesh 60k, PBR, `texture_resolution 4k`, `pose_mode a-pose`.
Rig: `height_meters`, `include_fingers true`. Clips at 30 fps. Total 123 of 126.

## Files

- `residents_meshy.py`: resumable pipeline, refuses a call the balance cannot cover.
- `prepare_unity.sh`: smooth normals, re-baked normal map, LOD0 20k (head protected) / LOD1 6k, anim-only clip copies.
- `inspect_npc.py`, `smooth_normals.py`, `rebake_normals.py`, `lod_blender.py`, `glb_lod.py`, `strip_clip.py`,
  `add_tangents.py`, `render_dump.py`: copies of the 3 Oct walker tools (unchanged).
