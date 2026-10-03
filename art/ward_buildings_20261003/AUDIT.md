# Ward buildings audit — 2/3 October 2026 (night)

Carl: "There are buildings in ward that need replacing too." This audit lists every building or large structure inside
the Ward walls (x −62…62, z −52…52), says whether it has been rebuilt on the shared Ward masonry kit
(`art/ward_masonry_kit`, Masonry Lit weathering, battle damage), and ranks the ones that have not by how visible and how
weak they are in the actual gameplay frame.

Sources: a fresh renderer/collider dump of the saved scene (`audit/audit.json.gz`, local only, `StreetDressingAudit.DumpBatch`,
22:39 on 2 Oct; `audit/group.py` groups it), the latest native lookbooks (`unity/evidence/combined/20261001/batch*/`,
`unity/evidence/next-level/20261002/nl3/`; sheets in `audit/sheets/a–d.jpg`) and six new editor captures at player
height (`audit/editor/audit_*.png`, sheet `audit/sheets/editor_audit.jpg`; `WardBuildingsPass --steps auditcap`).

## Already rebuilt (not candidates)

| Structure | Pass | Notes |
| --- | --- | --- |
| Vanguard Hall | `art/vanguard_hall_20260930` | Ashlar hall, LODs, floodlights. Meshy hall inactive. |
| Relay Works, Air + Water, Tool Exchange, Finery, Field Supply | `art/hall_district_20260930` | Masonry kit, sign family. |
| Salvage, Repairs, Thread + Hide, Basic General | `art/north_avenue_20260930` | Masonry kit; Salvage walk-in since 1 Oct. |
| Hill plinth, stairs, tree ring, kiosks | `art/hill_20260930` | |
| Perimeter walls (N, S, E rampart, Berms walls) | `art/perimeter_walls_20261001` | |
| West Gate arch gates | `art/west_gate_arches_20261001` | The Meshy arches themselves are unchanged (accepted look). |
| Hydroponics interiors and yard | `art/hydroponics_20261001` | Quonset frames/skins are still the 26 Sep retrofit shells (solid, not enterable) but read acceptably. |
| Rooftops, shade sails, wall-foot drifts, night life, paving | 1 Oct passes | Dressing, not buildings. |
| Ring Gate | Meshy (accepted) | Not a candidate. |
| West Gate outpost (−X Berms gantry) | `art/west_gate_20260926` | Authored kit; outside the walls. |

## Not rebuilt — ranked

All of these come from the 26 Sep **Ward district retrofit** prefab (`art/ward_retrofit_20260926/build_retrofit.py`,
one glTF instance `Ward district retrofit`, groups of `Structure` / `Detail` / `Decals` / `Glow` meshes): simple
bevelled boxes with tiled Poly Haven concrete/steel textures and decal stencils, no masonry, no vertex weathering, no
LODs other than a 3 % screen-height cull on the Detail mesh. They predate every masonry pass, so they now clash with the
rebuilt stone city around them.

| Rank | Structure (scene path) | Where / who sees it | Tris (struct + detail) | What is wrong at player height |
| --- | --- | --- | --- | --- |
| **1** | **Nanofab workshop** (`Ward district retrofit/Nanofab workshop`), 14 × 10 × 7.4 m at (36, −33) | SE yard, straight down the spawn apron's south view (`cam_nl_apron_south`), the yard mechanic's loop, `cam_pw_east_south`, `cam_nl_rampart_south` | 2.8k + 22k | A flat teal "glass" box with a white cap and five ribs; the loading door is a flat grey slab; the stencil floats; two plain shipping containers block the front; nothing ties it to the city's stone. The lore's one working nanofab reads as a portable cabin. `audit/editor/audit_nanofab.png`. |
| **2** | **Processing hall ruin** (`…/Processing hall ruin`), 28 × 13 × 14 m at (36, 34), facing the city | NE yard, the spawn apron's north view (`cam_nl_apron_north`), `cam_pw_north_east`, `cam_whompah` from the Ring Gate | 6.9k + 1.3k | Untextured-looking grey precast columns, panels with a marbled concrete texture, a bare truss, rubble cones; no sense of a building that once stood or of what destroyed it. `audit/editor/audit_processing_hall.png`. |
| **3** | **Watchtowers 1–4** (`…/Watchtower 1…4`), 17 m, at the four wall corners | On the skyline of nearly every outdoor view (`cam_pw_west_south`, `cam_pw_west_north`, `cam_hy_wide`, `cam_pw_corner_nw_high`, `cam_nl_south_lane`) | 2.6k + 1.1k each | Thin steel lattice legs carrying a flat olive box with a slit; it reads as a construction-site hut on stilts against the new stone curtain walls. Four instances, so one rebuild changes four silhouettes. |
| 4 | **Aquifer pump station** (`…/Aquifer pump station`), 18 × 6 × 11 m at (−35, −33) | SW quadrant: the market and the Berms gate approach, the mining droid's patrol | 5.3k + 4.2k | A plain marbled box with a monopitch roof, a flat green "door" panel and a pipe elbow; "AQUIFER 3" is a decal on red tiles. Primitive. `audit/editor/audit_aquifer.png`. |
| 5 | **Quantum Tube node housings** and conduit (`…/Quantum Tube conduit`), N wall either side of the Ring Gate | Seen from the Ring Gate approach and `cam_whompah`, `cam_pw_north_foot` | 1.4k + 3.3k | Two white boxes with a flat cyan rectangle; a black pipe with cyan rings on concrete posts. Goods-only lore must stay (no passenger implication). `audit/editor/audit_node_housing.png`. |
| 6 | **Perimeter dwellings** (`…/Perimeter dwellings`), five container homes on the wall feet | S and W wall feet, `cam_pw_west_south`, `cam_pw_south_high` | 0.9k + 54k | Bare 20 ft containers with a ladder; the "stacked" one floats a metre from the wall; no doors, windows, awnings or life at player height. `audit/editor/audit_dwelling.png`. |
| 7 | Lattice terminal hoop (`AuthoredWorld/PROP_lattice_*`, chunk sources) at (0, −39) | The Lattice transition (gameplay verb), `cam_nl_lattice` | ~2k | Box primitives with a flat cyan disc; a gameplay object with an interaction root — rebuild needs care with `Lattice interaction`. |
| 8 | Shop retrofits layer (`…/Shop retrofits`) | Over the rebuilt shops | 0.6k + 36k | 26 Sep cyan strips, blade signs, corner guards and roof kit authored for the old shells; the north avenue/hall passes filtered some of it (`WardShopsPass.FilteredRetrofit`). Needs a check that nothing floats off the new facades. **Checked 3 Oct (`audit/editor2/audit_retro_*.png`, sheet `audit/sheets/retro.jpg`): nothing floats; the remaining service poles and pipe bridges read as dressing.** |

Not buildings, not ranked: service lanes poles, gate defences HESCO, street clusters (dressing), hall banners.

## Decision for this run

Rebuild 1–3 to the standard of the rebuilt shops and the West Gate arches (Carl's preferred look: chipped sandstone,
blackened steel, grime, "this place saw a battle long ago"; sci-fi where the lore is technology, not 90s woodwork),
one focused pass each, in rank order, then 4 if time allows. Outcome: ranks 1–6 rebuilt and installed (see README.md);
rank 7 (the Lattice hoop) left for a dedicated pass — it is a gameplay object built from render-chunk sources next to
`Lattice interaction`, so it needs a chunk rebuild and a gameplay check, and a Meshy hero piece may suit it better. Concepts (Codex image_gen, prompts saved beside them):
`concept/nanofab_concept_v1.png`, `concept/hall_concept_v1.png`, `concept/tower_concept_v1.png`.
Progress and resumption notes: `PROGRESS.md`.

## Round two re-check (3 Oct 2026, 02:37)

Ranks 1–6 rebuilt in round one; round two fixed their defects (README_round2.md). Remaining candidates, from a fresh
look at the on2 lookbook, the 1 Oct batch-2 lookbook and the audit dump (`Ward district retrofit` children still active):

| Rank | Structure | Seen from | Verdict |
| --- | --- | --- | --- |
| **1** | **Gate defences** (`Ward district retrofit/Gate defences`): flat HESCO runs at x 44.6, z −13.5…−7.5 / 19.5…25.5, scrap turret (white pole + red box), three jersey barriers | The spawn and gate apron: `cam_nl_apron_north`, `cam_pw_east_north`, `cam_gate`, every walk out of the gate | **Rebuilt** as the West Gate bastions. |
| 2 | Lattice hoop (round one rank 7) | `cam_nl_lattice`, `cam_grid` | Reads as a ring with stone clamps and a console; chunk-source gameplay object. Left for a dedicated pass. |
| 3 | Hydroponics pump tanks (inside `Ward hydroponics/Retrofit planters and tank fittings`) | `cam_hy_pump` | Plain grey/rust cylinders in a mixed retrofit mesh (needs triangle filtering). Next candidate. |
| 4 | Hydroponics quonset shells, `Service lanes` poles, `Street clusters`, `Shop retrofits` | various | Read acceptably / dressing (round one rank 8 checked clean). |
