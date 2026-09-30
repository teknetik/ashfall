# Tool Exchange sci-fi display props (30 Sep 2026)

Carl: "if you rebuild the tool shop remember sci-fi not woodworking shop from the 90s as it looks now". The rebuilt
Tool Exchange (art/hall_district_20260930) has a glazed display alcove; these five props replace the old hand tools
(pegboard, pipe wrench, lump hammer, bolt cutters).

`generate.py` (Meshy text-to-3D, meshy-7.1 preview with remesh → refine with PBR, 2k textures; key from `.env`
`MESHY_API_KEY`, never written to disk). Credits: 30 per prop (preview 20 + refine 10), **150 total**
(pre-approved routine generation, AGENTS.md §5). Task IDs and requests are in each `<prop>/record.json`.

| Prop | Preview task | Refine task | Target size (m) | In Unity |
| --- | --- | --- | --- | --- |
| nanofab_bench | 01a0f221-490c-77cf-88a6-160aa7f0d19a | 01a0f223-733c-76c8-b3e1-cf828a8533f0 | 1.7 × 1.5 × 0.8 | 1.40 × 1.02 × 0.73 |
| tool_wall | 01a0f221-50bf-7589-a288-5321afcb45d1 | 01a0f223-03b6-7724-9300-d8b68d4d55fd | 1.6 × 1.1 × 0.22 | 1.10 wide, on a steel backboard |
| servo_arm | 01a0f221-5889-74fb-b473-5bffe03d2aa2 | 01a0f223-8a82-7181-baa1-345cc8964950 | 0.7 × 1.3 × 0.7 | 1.0 m tall |
| plasma_cutter | 01a0f221-6059-7659-8105-818ff20dbed0 | 01a0f223-130d-76e0-9c2a-2c8144151ede | 0.5 × 0.25 × 0.14 | 0.34 long |
| drone_chassis | 01a0f221-6827-71fe-84a6-2d0cbd5e4bab | 01a0f223-ccf7-75ae-bfd7-9c26137bd0a5 | 0.75 × 0.3 × 0.75 | 0.65 wide |

Downloads (`textured.glb`, previews, `refined-sheet.jpg`) stay local per `.gitignore`; copies used by the game are
`unity/AthenHill/Assets/AthenHill/Art/WardShops/ToolExchangeProps/TE_<prop>.glb` (unmodified). Fitted uniformly by
**Athen Hill → Ward shops → Fit Tool Exchange display props** (`WardShopsPass.FitDisplayProps`). Inspection: the
refined thumbnails show clean hard-surface forms; the tool wall is a loose set of tools (no board), so the prefab
adds a dark steel backboard and a cyan charging-rail strip. Not inspected closer than the display glass (~0.6 m).
