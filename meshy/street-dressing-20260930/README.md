# Ward street dressing: Meshy hero props (30 Sep 2026)

Carl: "A lot of the street trash and props looks very low quality can we rebuild them in blender and or meshy? I want the
area to have a lived in look but not be too mesy." Part of the street-dressing pass
([art/street_dressing_20260930](../../art/street_dressing_20260930/README.md)).

Four single objects: whole clutter piles were a recorded failure (the 10 Sep ground-detail trash job fused sacks and
collapsed a jug), so Meshy only makes pieces that no CC0 scan covers in the Ward's terms. `generate.py`: text-to-3D
meshy-7.1 preview (remesh, triangles) → refine (PBR, 2k), key from `.env` `MESHY_API_KEY` only (never written to disk).
Credits: 30 per prop (preview 20 + refine 10), **120 total** (pre-approved routine generation, AGENTS.md §5).

| Prop | Preview task | Refine task | Size in game (m) | LOD0 / 1 / 2 tris | Use |
| --- | --- | --- | --- | --- | --- |
| field_generator | 01a0f417-d4d9-7461-926a-f6ee8a34447c | 01a0f419-d753-7635-b330-6e04a9ceb146 | 1.25 × 0.94 × 0.81 | 60,256 / 10,823 / 4,281 | replaces the six 1,619-tri salvage generators |
| water_point | 01a0f417-dc75-7479-acdb-04c9091897b5 | 01a0f419-19a7-7711-a3bb-e1442f5dcbf5 | 0.75 × 1.65 × 0.89 | 48,745 / 8.8k / 2.4k | Air + Water frontage |
| handcart | 01a0f417-e440-74f0-a577-9c95b8714633 | 01a0f419-9634-772e-bb22-a4b5ebdca49e | 1.70 × 0.73 × 0.75 | 45,631 / 8,211 / 2,279 | east yard, West Gate, Repairs (under repair) |
| refuse_bin | 01a0f417-ec16-7392-be4c-7b08cfa48ba2 | 01a0f419-6284-71a5-92ca-1a0bf19288f9 | 1.28 × 1.25 × 1.00 | 36,615 / 6.6k / 1.8k | refuse points at Basic General and Vanguard Hall |

Inspection (refined thumbnails, Blender kit review, Unity solo auditions in scene lighting): clean hard-surface forms,
no holes or fused parts found at player distance. The handcart came back with four wheels rather than the two asked for;
it still reads as a salvage cart and was kept. The generator's roll cage is thin but reads correctly. Downloads
(`textured.glb`, previews, thumbnails) stay local per `.gitignore`; game copies are prepared by
`art/street_dressing_20260930/prepare_meshy_props.py` (uniform scale, LODs, source maps byte-for-byte).
