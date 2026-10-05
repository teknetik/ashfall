# Meshy turret and benches — 4 October 2026

Carl supplied two Meshy models "to replace the turret and benches" (sources and inspection:
`meshy/turret-bench-20261004/README.md`). What they replace was taken from the saved scene (`survey.txt`, step `survey`):

* **Turret**: the Ward has no standalone turret. The only guns are the two round-two pintle guns (with riveted
  shields) modelled into the West Gate gabion bastions at the spawn (`WL_GateBastionS/N`, Ward life pass). The retrofit
  "scrap turrets" are all retired. The Post Sentinel enemy droid was left alone.
* **Benches**: the street kit's Poly Haven `SD_bench_painted` (7 placements: two hill-foot benches, the plaza bench, the
  Finery frontage, the hydroponics growers' rest bench, the water-ration court and the range's waiting bench) and four
  primitive 2.8 m slab benches still drawn by the render chunks (`AuthoredWorld/PROP_bench_00–03` with `COL_bench_00–03`,
  on both sides of the avenue at x ±30). Work benches (Brann's workbench, the range shooting/repair benches, the
  potting bench, vices) are a different object and stay.

## Runtime models (`prepare_meshy.py`, Blender 5.2)

Uniform scale only, front to Unity +Z, base on the ground at the footprint centre, three LODs by collapse decimation of
the full source with the source's split normals transferred onto each LOD. LOD0 keeps Meshy's UV-island seams split,
because welding them let the collapse smear UVs into a dark notch on the bench back. LOD1/LOD2 are welded, because their
heavier reductions tear at split borders. Comparison: `review/lods_sheet.png`.

| Model | Scale | Unity size (m) | LOD0 / LOD1 / LOD2 triangles |
| --- | --- | --- | --- |
| `TB_SentinelTurret` | 1.0 | 0.83 × 1.49 × 1.90 (barrel at +Z) | 29,622 / 7,404 / 2,220 |
| `TB_CyberBench` | 0.614 (seat 0.45 m, the kit's sit height) | 1.17 × 0.67 × 0.44 | 45,192 / 9,037 / 2,107 |

The bench's footprint matches the Poly Haven bench it replaces (1.16 × 0.50 m), so no placement moved. The maps are the
Meshy 2k maps byte for byte (BC7, streamed). The URP Lit mask is built from the glTF metal-rough map. The bench was
~99 % full metal on a dark albedo, which reads black against the city's small sky probe (the street kit's galvanised bins
did the same), so its metallic is × 0.5. Materials `Art/TurretBench/Materials/TB_*.mat` (template `SD_field_generator`).
Prefabs `Prefabs/TurretBench/`: LODGroup, box colliders (turret base/post/housing, barrel left out; bench body) and
the bench's two `NPC sit point` markers (±0.3, 0.45, 0.05) as on the old bench.

## Scene changes (`Editor/TurretBenchPass20261004.cs`)

* **Bastions** (`bastions`): `author_buildings.gate_bastion` has a `GATE_GUN` switch, and `author_life.py` sets it False.
  `author_life.py -- bastion` was re-run. Its output is deterministic: an unmodified re-run reproduced every part
  vertex for vertex (`compare_glb.py`). Without the gun, only the Metal and Hardware parts change (S LOD0 33,936 → 32,948,
  N 32,308 → 31,320). The steel deck stays. The bastion json gains a `Sentinel turret` mount, so a future
  `WardLifePass build` places it too. The WL prefabs were edited in place, not rebuilt: every renderer is rebound to
  its glb's material slots by name, and the turret is mounted under `Fittings` at (±1.1, 0.37, 0.32), yaw ±50°. It
  covers the inner mouth of the gate, and its muzzle clears the gabion return by ~13 cm. Aimed straight along the
  wall, it went through the return (`clearance.py`, `review/bastion_audition.png`). Mount colliders are stripped as
  WardLifePass does. The bastion's `COL_GunPlatform` covers the deck.
* **Benches** (`benches`): each active `SD_bench_painted` gets a `Meshy bench (<old name>)` sibling with the same
  transform, and the old one goes inactive. Each primitive slab and its collider go inactive, with two Meshy benches
  0.2 m apart in its place facing the avenue (scene root **Ward Meshy benches**, 8 benches). The render chunks were
  rebuilt. Totals: 15 Meshy benches, 30 sit points.
* Review cameras `cam_tb_*` (root **Turret and bench review cameras**): both gate posts from the street, a turret
  close-up, hill-foot benches, plaza bench, avenue pair.

Rollback: `--steps rollback`. It removes what was created, restores the old benches and slabs, copies the 3 Oct
bastion models back from `previous/`, rebinds the prefabs, takes the turret off and rebuilds the chunks. Also set
`AB.GATE_GUN = True` in `author_life.py`. Record: `record.json`.

## Verification (4 Oct 2026, `unity/evidence/turret-bench/20261004/`)

* `verify` PASS: 2 bastion prefabs with turret, 15 Meshy benches active, 0 old benches active, 0 slab parts active,
  chunk fingerprint ok, 0 missing scripts. The touched passes' own verify steps (`others`: WardLife, StreetDressing,
  Hydroponics, TrainingRange) report no missing materials or prefabs, no retired objects active and matching chunk
  fingerprints. WardLife's one marker note (`qa_motion_wall` 0.35 m from the unchanged `COL_Return`) is
  pre-existing.
* Edit Mode 268/268.
* Editor captures `editor/cam_tb_*.png` (13:00 editor lighting).
* **Not natively tested.** No player build, lookbook, A/B or city loop yet; that belongs to the next combined batch. The
  bench cost (45k LOD0 near the camera, up to ~4 benches in close view) and the turrets (30k each at the gate) should
  be checked in its gate/hill A/B.
* Not yet accepted by Carl.

Open: the turret is static (one mesh, no separate yaw head), and the hill-foot benches stand in the edge of the
wall-foot sand banks laid round the old benches.
