# West Gate arches — sealed working gates at the spawn (1 October 2026)

Art-direction review item 4 (30 Sep, "the arches are blind"): both arches of the "WEST GATE" structure at the +X
spawn opened onto nothing — no leaves, no threshold, no depth — which contradicts Vex's first line ("Keep the passage
clear and watch for the carts") and the "caravan goods waiting" vignette beside them. This pass makes them read as a
sealed working gate. Unity side: `Assets/AthenHill/Editor/WestGateArchesPass.cs`. Evidence:
`unity/evidence/west-gate-arches/20261001/`.

## The arches as found

The two arches are the Meshy `District gate` instances (`Prefabs/District/gate.prefab`, 4,530 triangles each,
non-uniform "Fitted visual" scale from 8 Sep, drawn by the render chunks `Chunk_*_District_gate_*`). They are not
touched by this pass. Measured from the saved chunk meshes (`extract_gate_mesh.py`, `measure_opening.py`,
`review/gate_slices.png`): each instance is two piers (x 46.4–49.6) and a 2.1 m arch wall (tunnel x 47.05–48.95,
chamfered/rounded reveals to x 46.88 and 49.1) with a 4.93 m opening (jambs z ±2.465 about the arch centre),
vertical jambs to y ≈ 5.0 and a basket head (crown y 6.74). Arch A is centred z 0 (the spawn arch), arch B z 12.
Beyond the arches lies the enclosed strip (x 49.7–58) and the perimeter strip wall at x 59; nothing there is used by
the game.

## What is built

Leaves set 1.6 m back in each arch passage (city face of the frame at x 48.6), so the arch keeps a shadowed passage
in front of a closed gate:

| Part | Construction |
| --- | --- |
| Leaves | Two per arch, 2.43 × 4.52 m, closed. Vertical boards (weathered `TR_Timber`, a few darker and a few fresh replacement boards) on a riveted steel skin (`WG_PlateSteel`, seam straps on the outer face); stiles, three rails and hinge-side braces in dark timber on the city face; steel shoe, kick plates, meeting-edge cover strip, corner plates, rubber sand sweep; cane bolts dropping into the threshold. Arch A's south leaf carries a 0.88 × 1.80 m wicket door (own boards, ledges, braces, strap hinges, ring pull, slide bolt, vision hatch, kick plate). Arch B's north leaf has a riveted repair plate over old shell damage. |
| Hinges | Three strap hinges per leaf on the rails, knuckles on pintles let into the jambs (iron tang into the stone, lead-run patch on the jamb face). |
| Drop bar | One dark timber bar (0.17 × 0.22 × 5.03 m) per arch across both leaves, in steel stirrups standing on the lock rail, iron end bands, two lifting handles; its ends sit in steel-framed pockets let into the jambs. |
| Head | Heavy timber transom with a steel nosing at the leaf head; a fixed steel grille (29 bars, two tie bars, a band following the measured soffit 3 cm inside it) fills the arch head, so the sky still shows through. |
| Threshold | Worn steel threshold plate in three sections (x 48.25–49.0) with countersunk bolts, a leaf stop bar and cane-bolt sockets; steel stop angles and rubber leaf buffers at the jambs. |
| Wheel guards | A dressed guard stone (Ward masonry kit, battered street and city faces, low pyramid top, steel wear band) at each tunnel mouth corner, leaving a 4.36 m cart passage; steel corner angles with rubber buffers on the jamb arrises. |
| Decals | URP projectors: cart ruts (two worn tracks, 1.45 m gauge plus a fainter narrower pair) from the apron to the threshold, scuffs in the passage, sand caught against the leaf foot, a grime skirt on the lower leaves, hub scrapes on both jambs; a worn painted stencil "KEEP CLEAR" across both leaves (it runs over rails, braces and straps, painted after assembly) and the gate number (1, 2) on each transom. |
| Lamp | A caged bulkhead on each transom with a conduit down the south jamb; a warm unshadowed spot (125°, 7.5 m, intensity 3) on the Ward lighting clock (`practicalLights` + `nightOnlyLights`); lens `VH_LampLens` (already on the circuit's emissive list). |

Colliders: one box per arch seals the whole opening at the leaves (from the bar to the stop, up to the soffit), so the
city stays enclosed and the player can walk into the passage up to the gate; one box per guard stone. The Meshy
arches keep their own mesh colliders; no saved collider is changed. Nothing is retired; no render-chunk source changes.

Triangles (LOD0 / LOD1 / LOD2): arch A 25.4k / 11.3k / 1.5k, arch B 24.2k / 10.1k / 1.4k (leaves 7.7k/6.1k at LOD0,
the rest is hardware and bolts, which never cast shadows). LOD switches at ~15 m and ~45 m (PC lod bias 2), culled
past ~400 m. Shadow casters: the leaves/transom/grille group and the guard stones. Two new lights (one per arch).

## Review cameras

Root "West gate arch review cameras" (disabled cameras, eye 1.65 m): `cam_wga_spawn` (what the player sees on turning
round at the spawn), `cam_wga_front` (both arches from the apron), `cam_wga_close` (arch A leaves, three-quarter),
`cam_wga_wicket` (wicket at arm's length), `cam_wga_head` (arch B transom, head grille, repair plate),
`cam_wga_threshold` (arch B threshold, ruts, guard stone).

## Run order

```
python3 extract_gate_mesh.py                               # gate_world.obj, gate_profile.json (from the saved render chunks)
python3 measure_opening.py                                 # opening.json: soffit and jamb profile at the leaf planes
$O/blender.sh author_gate_arches.py                        # -> Art/WestGateArches/Models/WGA_Gate{A,B}.glb, gate-arches.json (~5 s)
$O/blender.sh review_gate.py -- r1 A --views spawn,close3q,wicket,head,guard,hinge   # Cycles review renders -> review/r1
uv run --with pillow --with numpy python make_decals.py    # -> Art/WestGateArches/Textures/WGA_Decal*.png
$O/unity.sh <log> AthenHill.Editor.StreetDressingAudit.DumpBatch --out <audit.json> -nographics
uv run --with matplotlib python layout.py [audit.json]     # layout.json + validation (0 problems) + review/layout-map.png
$O/unity.sh <log> AthenHill.Editor.WestGateArchesPass.RunBatch --steps build,capture --out <dir>          # graphics, <= 6 cams
$O/unity.sh <log> AthenHill.Editor.WestGateArchesPass.RunBatch --steps install,verify -nographics
```

`install` is one time (refuses when "Ward west gate arches" exists; `reinstall` replaces the root during authoring,
unhooking its lights from the circuit first). `capture` places the gates in memory when they are not installed and never
saves. `$O` = `/home/teknetik/.local/state/ward-programme` (the programme wrappers).

## Sources and licences

- Geometry: authored procedurally in Blender 5.2 (`author_gate_arches.py`); the guard stones on the shared Ward
  masonry kit (`art/ward_masonry_kit/ward_masonry.py`). Fitted to the Meshy arch geometry read from the saved render
  chunks (this repository).
- Materials reused in Unity: `TR_Timber`, `TR_TimberDark`, `TR_TimberFresh` (training range, Poly Haven `rough_wood`,
  CC0); `WG_RustSteel`, `WG_PlateSteel`, `WG_Rubber`, `WG_DecalSandSpill`, `WG_DecalGrime` (West Gate kit, CC0 sources
  recorded in `art/west_gate_20260926`); `VH_Ashlar`, `VH_Dark`, `VH_Steel`, `VH_LampLens` (Vanguard Hall); the
  weathering decal atlas `Art/Weathering/Sand grime scuffs and runoff.mat` (scuff quadrant).
- Decal textures `WGA_DecalCartRuts`, `WGA_DecalJambScrape`, `WGA_DecalStencil`: generated procedurally
  (`make_decals.py`); the stencil lettering uses Stardos Stencil (SIL OFL, already in `art/west_gate_20260926/fonts`).
- No Meshy generation was used for this pass.

Heavy outputs (`review/`, logs, `gate_world.obj`) are git-ignored or disposable.

## Not changed / for Carl

- The gate keeps its name. The "WEST GATE" sign on these +X arches contradicts the compass (+X is east) and duplicates
  the -X Berms gantry's "WEST GATE": a naming and lore decision for Carl.
- The Meshy arch itself (non-uniform fitted scale from 8 Sep, 4.5k triangles, soft 1k atlas tile) is unchanged.
