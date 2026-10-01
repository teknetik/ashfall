# Docs snippet: West Gate arches (1 Oct 2026) — for the orchestrator to merge

## unity/EDITING.md section

### West Gate arches (1 Oct 2026)

The two `District gate` arches at the +X spawn (the Meshy instances under `District rebuild`, still drawn by their
render chunks and untouched) carry sealed working gates set 1.6 m back in each arch passage. Scene root **Ward west
gate arches** holds one prefab instance per arch: `Prefabs/WestGateArches/WGA_GateA.prefab` (spawn arch, centred
z 0, wicket door in the south leaf) and `WGA_GateB.prefab` (z 12, repair plate on the north leaf), both at x 48 with
identity rotation and scale.

- Each prefab is a LODGroup (LOD0 bevelled and bolted within ~15 m, LOD1 to ~45 m, plain LOD2 beyond) over the groups
  Leaves (timber leaves, steel skin, transom, head grille: cast shadows), Iron (hardware: no shadows), Stone (guard
  stones on Athen Hill/Masonry Lit: cast), StoneBand and Lamp (no shadows); plus `Colliders` (one box sealing the
  opening at the leaves, one per guard stone), `Bulkhead light` (warm unshadowed spot on the Ward lighting clock) and
  `Decals` (URP projectors: cart ruts, scuffs, sand, grime skirt, jamb scrapes, a painted KEEP CLEAR stencil and the gate
  number on the transom).
- Sources: `art/west_gate_arches_20261001` (`author_gate_arches.py` → `Art/WestGateArches/Models/WGA_Gate{A,B}.glb`;
  `layout.py` → `layout.json` with placements, decals, light and cameras, validated against a scene audit;
  `make_decals.py` → the rut and jamb-scrape textures). The leaves are fitted to the arch opening measured from the
  saved chunk meshes (`extract_gate_mesh.py`, `measure_opening.py`). Rebuild: `WestGateArchesPass.RunBatch --steps
  build,verify` (menu Athen Hill → West Gate arches).
- Materials are shared, not copied: `TR_Timber*` (training range), `WG_*` steel, rubber and decals (West Gate kit),
  `VH_*` (Vanguard Hall); only the three decal materials `WGA_DecalCartRuts`, `WGA_DecalJambScrape`, `WGA_DecalStencil` are new (copies of
  the weathering decal template).
- Editing: move or swap a gate instance in the Scene view only together with its arch (they are fitted to the Meshy
  opening, jambs ±2.465 m); decals are children of each prefab. The lights are on `CityLightCircuit.practicalLights`
  and `nightOnlyLights`; a reinstall unhooks and re-adds them.
- Collision: the leaves' box seals each arch, so the strip behind the rampart is no longer reachable; the city stays
  enclosed. No saved collider changed; nothing retired. Scene before the install:
  `unity/evidence/west-gate-arches/20261001/rollback/`.
- Review cameras `cam_wga_*` (6, under "West gate arch review cameras") for `unity/tools/lookbook.py`.
- Naming: the arches still carry the Meshy "WEST GATE" sign although they are on the east (+X) side; renaming is a
  decision for Carl.

## AGENTS.md baseline-table row

| West Gate arches | 1 Oct 2026 (`art/west_gate_arches_20261001`, scene root **Ward west gate arches**): the two spawn arches closed with steel-faced timber gates set back in the arch passage — framed, ledged and braced leaves with strap hinges on jamb pintles, a wicket door (arch A), drop bar in stirrups and jamb pockets, transom and head grille to the soffit, worn steel threshold, guard stones and corner guards, cart-rut/scuff/sand/grime decals, a bulkhead lamp per arch on the light clock. LOD0–2; the leaves' collider seals each opening; Meshy arches, their chunks and saved colliders unchanged. Not yet accepted by Carl. |
