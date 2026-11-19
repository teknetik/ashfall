# Gate names: the +X spawn arches are the East Gate (19 November 2026)

Carl's decision (19 Nov 2026): **"West Gate" is the gate near the market**, the -X portal into the Outer Berms
(x about -59, map place `berms:west_gate`; Ossa's Warden post beyond it). Everything that calls that gate West Gate
stays as it is (Ossa's role and lines, `BermsTutorial`, the "WEST GATE FIELD BRIEFING" notice, the "WEST GATE /
WARDENS" sign, the compass point, the map's "West Gate" and the "West Gate post" respawn line).

The two Meshy "District gate" arches at the **+X spawn** (x 46.3-49.7, centred z 0 and z 12; the player spawns at
(43, 0, 0), R returns there and Continue resumes there) were also called West Gate. Their player-facing name is now
**East Gate** (the spawn is on the east side of the north-up map). Carl may still change the name; the places that
hold it are listed under "Renaming the gate again".

Unity side: `Assets/AthenHill/Editor/GateNamesPass20261119.cs`. Evidence: `unity/evidence/gate-names/20261119/`.

## What changed

### Plaques over the baked lettering

Both arches carried a baked "— WEST GATE —" plaque in the Meshy texture on **both** faces: the city face (-X, the
one the player sees) and the outer face (+X, over the closed strip behind the rampart). The atlas is a fragmented
auto-UV layout, so it is not repainted. `measure_plaques.py` reads the saved render-chunk meshes (read only) and the
Meshy atlas and renders orthographic texture projections of each face (`review/face_*.png`, depth in
`review/depth_*.npy`):

| | Baked plaque | Arch face under it |
| --- | --- | --- |
| City face (A and B) | 4.465 x 0.90 m, y 7.25-8.15, z -2.24..2.225 about the arch centre | flat, x 46.846-46.876 |
| Outer face (A and B) | 4.465 x 0.90 m, y 7.24-8.155 | x 49.140-49.158, with a hole in the Meshy mesh through the "S" |

Four new plates (`GN_Plaque` mesh, 4.54 x 0.965 x 0.07 m, i.e. 3-4 cm larger than the baked plate all round) sit with
their front faces 2.5 cm proud of the most-proud point of each face (x 46.821 city, 49.183 outer) and their backs
buried in the stone, so there is no gap behind them to see old lettering through. Scene root **Gate name plaques**:

| Object | Position | Yaw |
| --- | --- | --- |
| East Gate plaque A city face | (46.821, 7.70, -0.0075) | -90 |
| East Gate plaque B city face | (46.821, 7.70, 11.9925) | -90 |
| East Gate plaque A outer face | (49.183, 7.70, 0.0075) | 90 |
| East Gate plaque B outer face | (49.183, 7.70, 12.0075) | 90 |

The outer faces are covered too, although the player cannot normally reach a view of them (the gates are shut and
sealed by colliders; the strip behind is closed). Covering them was cheaper than proving no view exists, and it also
closes the hole in the Meshy outer face.

Texture (`make_plaques.py`, 2048 x 512, `Art/GateNames/Textures/GN_Plaque_{BaseMap,Normal,Mask}`), matched to the
baked plaque sampled from the Meshy maps: dark iron plate (albedo 0.20/0.17/0.14, metallic about 0.9, smoothness
about 0.2, as the Meshy metallic/smoothness map has it), ivory lettering (0.745/0.686/0.62) in Noto Sans Bold
(horizontally condensed to the baked lettering's 0.50 m cap height and 2.79 m name width), dashes 0.375 m long either
side, worn bright edges, a domed bolt in each corner, light rust and dust. Material `Art/GateNames/Materials/GN_Plaque.mat`
(URP Lit, mask = metallic R, occlusion G, smoothness A). No colliders, not a render-chunk source; each plate is 12
triangles, one material, shadows on.

Not touched: the Meshy arch, `Prefabs/District/gate.prefab`, its render chunks (`Chunk_8_District_gate_2_0`,
`Chunk_9_District_gate_2_1`, hashes recorded before and after in `install.json` and checked by `verify`), its saved
colliders, and the gate fittings of root **Ward west gate arches**.

### Text the player reads

Classified by position: anything about where the player arrives (spawn (43, 0, 0), R, Continue) is the +X arches.

| Where | Old | New | Gate |
| --- | --- | --- | --- |
| `UI/StartupMenu.uxml` Continue tooltip | Resume your saved game at West Gate | Resume your saved game at East Gate | +X spawn |
| `UI/StartupMenu.uxml` Start Game tooltip | Enter the city at West Gate | Enter the city at East Gate | +X spawn |
| `UI/CityHUD.uxml` pause button `reset` | Return to West Gate | Return to East Gate | +X spawn (R teleports to the spawn) |
| `UI/CityHUD.uxml` pause controls list | R · Return to West Gate | R · Return to East Gate | +X spawn |
| `Scripts/SettingsPanel.cs` Controls note | R return to West Gate | R return to East Gate | +X spawn |
| `Data/CityCatalog.asset` notes (journal Ward notes tab; changed by the pass) | R returns to West Gate. | R returns to East Gate. | +X spawn |
| `Scripts/CityCatalog.cs` default `notes` | R returns to West Gate. | R returns to East Gate. | +X spawn |
| `Scripts/Save/WardSaveGame.cs` Continue summary before the primer | Arrived at West Gate | Arrived at East Gate | +X spawn |
| `Scripts/Map/WorldMapData.cs` map place `city:barred_gates` | Barred gates | East Gate | +X arches (id kept) |
| Meshy arch plaques (4, baked texture) | — WEST GATE — | — EAST GATE — (covering plates) | +X arches |
| `unity/README.md` Continue paragraph and controls table | West Gate | East Gate | +X spawn |
| Comment in `Scripts/Save/WardSaveData.cs` | resumes at West Gate | resumes at the East Gate | +X spawn |

Kept, because they mean the -X Berms portal (positions checked): Ossa's role "West Gate watch" and greeting
(`Data/npc_ossa.asset`, voiced), `BermsTutorial.lineStart`, the checkpoint `speaker` "West Gate checkpoint" and its
"WEST GATE FIELD BRIEFING" notice, the "WEST GATE / WARDENS" and "WEST GATE FIELD BRIEFING" sign texts, the
`WG_SignGate*` and `WG_SignPost` textures, the compass point `displayName: West Gate` (Berms), the map's "West Gate"
place, `WorldMapPanel`'s "West Gate post" respawn line, the journal's primer texts ("the West Gate post", "Report to
Warden Ossa at the West Gate post"), Brann's "market gate" lines and the primer's "Go through the market gate".
Vex's lines and barks (he stands at the +X arches) say only "the gate"; no voiced line names the +X arches as West
Gate, so no audio is affected.

### Internal names that keep "West Gate"

Scene objects (`Ward west gate arches`, `West gate arch A (spawn, wicket)`, `West gate arch B`, `West Gate apron sail`,
`West gate arch review cameras`), the QA landmark id `west_gate` (the spawn transform), review cameras (`cam_wga_*`,
`cam_westgate_*`), Editor passes and asset folders (`WestGateArchesPass`, `Art/WestGateArches`, `Art/WestGate`,
`art/west_gate_arches_20261001`), the map place id `city:barred_gates`, dialogue ids and save data. Developer tool
docstrings in `unity/tools/*.py` that say "west gate" for the spawn are internal and unchanged.

### Review cameras

Root **Gate name review cameras** (disabled cameras, eye 1.65 m): `cam_gn_spawn` (turning round at the spawn,
plaque A from below), `cam_gn_spawn_b` (arch B from the spawn), `cam_gn_avenue` (the avenue approach from x 24),
`cam_gn_rampart_n` and `cam_gn_rampart_s` (grazing along the rampart face from the north and the south),
`cam_gn_under_b` (right under plaque B).

### Tests

`Tests/Editor/WorldMapTests.GateLabelsFollowTheCompass` (East Gate is +X, West Gate is -X, no +X place is called West
Gate) and `Tests/Editor/GateNamesTests` (menu tooltips, pause button and controls list name the East Gate and never
"West Gate"; the catalog notes say "R returns to East Gate.").

## Run order

```
uv run --with pillow --with numpy python measure_plaques.py   # review/face_*.png, depth maps, projections.json
uv run --with pillow --with numpy python make_plaques.py      # Art/GateNames/Textures/GN_Plaque_*, review/plaque_preview.png
~/.local/state/ward-programme/showcase-20261119/seq.sh install gates1 AthenHill.Editor.GateNamesPass20261119.RunBatch install,verify
```

Native checks (private display :5 up): `unity/evidence/showcase/20261119/qa/run_packages.sh gates gates world_map interface gate_names`
(`gate_names` = `unity/tools/check_showcase_gate_names.py`), and the lookbook through `native_check.sh` with
`run_lookbook.py` (arguments from `GN_OUT`, `GN_CAMS`, `GN_HOURS`, `ATHEN_EXE`, because `native_check.sh` passes none).
`review/` holds the face projections and depth maps (disposable, regenerated by `measure_plaques.py`).

`install` is idempotent: it re-imports the textures, rebuilds `GN_Plaque.mat` and `GN_Plaque.asset`, replaces its own
root, updates its cameras and the catalog notes line. `verify` throws (exit 1) on any problem and writes
`unity/evidence/gate-names/20261119/verify.json`.

## Renaming the gate again

1. `make_plaques.py`: set `GATE_NAME` and re-run (the name is scaled to the baked lettering's box).
2. The text rows of the table above (two `.uxml` files, `SettingsPanel.cs`, `CityCatalog.cs`, `WardSaveGame.cs`,
   `WorldMapData.cs`, `unity/README.md`) and the `NewNote` constant in `GateNamesPass20261119.cs` (set `OldNote` to the
   current text), plus the two tests that assert the name.
3. Re-run the pass (`install,verify`), the Edit Mode tests and a build.

## Rollback

`RunBatch --steps rollback` removes the two roots and puts "R returns to West Gate." back into the catalog notes; the
assets in `Art/GateNames` stay. The plain-text edits (`.uxml`, `.cs`, `unity/README.md`, the tests) are reverted
with git. The scene before the first install is `~/.local/state/ward-programme/showcase-20261119/scenes/before-gates1.unity`.

## Sources and licences

Poly Haven `metal_plate_02` and `rusty_metal_02` (CC0, via `art/west_gate_20260926/polyhaven`), Noto Sans Bold (SIL
OFL 1.1, `art/hall_district_20260930/fonts`). Procedural; no Meshy, ElevenLabs or image generation.

## Verification record (19 Nov 2026)

Done:

- Pass `install,verify` clean (`unity/evidence/gate-names/20261119/verify.json`: 4 plaques, `GN_Plaque.mat` URP Lit,
  both Meshy arches active, `Ward west gate arches` active, render-chunk fingerprint matches, District gate chunk
  assets byte-identical before/after, 6 cameras, catalog notes updated, no problems).
- `rollback` tested on the installed scene: removed both roots and restored the notes line; the only remaining scene
  difference from the pre-install copy was Unity re-serialising two default fields (`faceSpeaker`, `faceTurnRate`) on
  eight existing components. The installed scene and catalog were then put back byte-identical to the built state
  and `verify` re-run clean.
- Edit Mode tests: 393/393 after the first install (390 before + 3 new) and 393/393 again on the final scene
  (`unity/evidence/showcase/20261119/editmode-gates1.summary`, `editmode-gates2.summary`).
- Build `Builds/batch-gates` (also `Builds/LinuxDevelopment`), 19 Nov 18:50, `Result: Success`, no shader or
  compile errors, no "Unable to parse".
- Native on `batch-gates` (display :5): world map package 29/29, interface package 22/22, new
  `unity/tools/check_showcase_gate_names.py` 12/12 (Continue summary "Arrived at East Gate", pause button and
  controls list, journal Ward notes, real R back to the spawn, map label East Gate east of West Gate, "You are ·
  10 m from East Gate", no exceptions), city loop PASS, range tutorial 10/10.
- Native lookbook (`unity/evidence/gate-names/20261119/lookbook-r2`, 13:00 and 20:30): all `cam_gn_*`, `cam_gate`,
  `cam_wga_spawn`. Looked at every frame: no old lettering visible from below at the spawn, under arch B, from the
  avenue or at ~60-65 degrees along the rampart; no z-fighting or floating (the plate's 7 cm side reads as a mounted
  plate at oblique angles); letter tone and plate colour match the baked plaques in sun and at night (readable at
  20:30 under the night readability lighting). Round 1 (`lookbook-r1`) had the spawn camera inside the player's
  head and the rampart cameras against the piers; moved in round 2.

Not done / not verified:

- `cam_gn_avenue` (x 24.5): the West Gate apron sail and a shop corner hide most of the plaques from that spot; that
  is what a player sees there, the plates read fully from `cam_gate` and the apron.
- The outer-face plates were not seen in a native capture (no player-reachable view; checked only by placement
  numbers from the chunk depth maps).
- No frame-time A/B (four 12-triangle plates, one material, no lights).
- Carl has not reviewed the name or the plates.
