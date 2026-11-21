# Contracts between the agents

Three boundaries are fixed here so agents can work at the same time: **A** assets (modellers to Unity), **B** runtime
(the bench system to the existing crafting system), **C** audio. If a contract is wrong or lacks something, tell the
orchestrator; do not change it on your own (AGENT-RULES, Reporting).

## Who owns what

| Agent | Owns (may create and edit) |
|---|---|
| `bench` (interaction system) | `Scripts/Assembly/**`, `Editor/Assembly*.cs`, `Tests/Editor/Assembly*Tests.cs`, `Data/Assembly/**`, and the shared files `GameSession.cs`, `GameInput.cs`, `Data/Controls.inputactions`, `FollowCamera.cs`, `Camera/CinematicCamera.cs`, `CityHud.cs`, `DevBridgeCommands.cs`, `NativeQa.cs` (small additive edits) |
| `craft` (crafting integration and weapon feel) | `Scripts/Crafting/**`, `Scripts/Orders/**`, `Scripts/Journal/**`, `Scripts/Save/**`, `Scripts/Combat/**` (feel only), `Scripts/QuestConditions.cs`, `Tests/Editor/*` it adds or already-existing crafting tests, `art/steady_hands_bench_20261120/data/apply_data.py`, and through that script `WardCrafting.asset`, `WardFieldOrders.asset`, `CityCatalog.asset`, `npc_brann.asset`, `npc_ossa.asset` |
| `model-pistol` | `art/steady_hands_bench_20261120/kit/**`, `grip/**`; `Assets/AthenHill/Art/Bench/Grip/**` (and `pistol/**` until 20 Nov 18:05) |
| `model-pistol-surface` (from 20 Nov 18:05) | `pistol/**`; `Assets/AthenHill/Art/Bench/Pistol/**`: surfaces and the final bake only, no change to nodes, marks, params or outline |
| `model-servo` (finished 19:00) | `servo/**`; `Assets/AthenHill/Art/Bench/Servo/**`. From 21:05 `model-servo-surface` owns both for the can's last surface pass (surfaces and bake only; `model-materials` finished at 21:00 without starting it) |
| `model-materials` (from 20 Nov 18:10; the family moved from `model-servo`, which wrote its `PARTS.md`) | `materials/**`; `Assets/AthenHill/Art/Bench/Materials/**` |
| `model-bench` | `fixtures/**`; `Assets/AthenHill/Art/Bench/Fixtures/**` (and `tools/**` until 20 Nov 21:45) |
| `model-tools` (from 20 Nov 21:45) | `tools/**`; `Assets/AthenHill/Art/Bench/Tools/**`. `tools/src/mbk.py` is frozen in behaviour (fixtures import it) |
| `audio` | `audio/**`; `Assets/AthenHill/Audio/ElevenLabs/Bench/**` |
| `integration` (from 20 Nov 20:20) | `Editor/SteadyHandsBenchInstall20261120.cs`, `Prefabs/Bench/**`, `Shaders/Bench*`, scene objects under the root **Steady Hands bench** |

Paths without a prefix are under `unity/AthenHill/Assets/AthenHill/`; `art/...` paths are under this folder.

## A. Assets

### Families and folders

`pistol` (scrap pistol, charge cell, old grip parts, its fasteners, test cards), `grip` (Stabilised Pistol Grip
sub-parts), `servo` (Damaged Servo and everything inside it), `materials` (alloy sheets and what is cut from them,
nanite vial, bobbin, plug, lead states), `tools` (Field Toolkit and Brann's bench tools), `fixtures` (everything fixed
to or standing on the bench).

Each family folder holds: `sheets/` (reference sheets and their `*.prompt.txt`), `PARTS.md`, `build.py`, `check.py`,
`review/` (compare renders), and `export/` with `<family>.glb`, `parts.json`, `stats.json`, `check.json`. When
`check.json` passes, the agent copies `<family>.glb` to `Assets/AthenHill/Art/Bench/<Family>/` and `parts.json` beside
it as `<family>.parts.json`. Modelling agents do not run Unity.

### Geometry and export

- Blender 5.2.2, metres, Z up; `build.py` runs headless from one command and takes `--nobake`, `--size`, `--spp`.
  glTF export with `export_yup=True`, tangents, applied modifiers.
- **A family GLB is exported assembled**: every part at its seated place on its parent, in the as-found state
  (pistol with the old grip on, servo closed and whole, grip complete). The seated pose of a part is its rest
  transform. Loose things (tools, sheets, jars) lie at their bench rest orientation with the origin where they touch
  the bench.
- One node per part, named `<family>_<part>` in lower snake case. Rigid parts only; mechanisms are AnyMachine rigs
  (`ANYMACHINE.md` section 2).
- **Directions and poses are given as empties, never as vectors in JSON**, so no axis conversion can go wrong:
  - `<node>__clear`: a sibling empty at the pose where the part is just clear of what it seats on (lifted off, slid
    off, backed out). The runtime moves the part between this pose and its rest pose. For a screw it is the fully
    backed-out pose on the screw's axis.
  - `<node>__grab`: optional child, the point the hand holds (default: bounds centre).
  - `<node>__tip`: tools only, the working point; its local +Z in Blender points out of the tool along the working
    direction.
  - `<node>__path_<id>_<nn>`: ordered empties along a line to follow (peel, scribe, cut, seam, harness route), 8 to 40
    per path, on the surface.
  - `<node>__mark_<id>`: a point target (snip mark, oil point, detent, probe pin, punch mark).
  - `<node>__zone_<id>`: a box empty bounding an area to wipe.
- Budgets (LOD0 only; the bench is seen close): pistol family 45k triangles, grip 25k, servo 45k, materials 15k,
  tools 60k in total (2k to 6k each), fixtures 70k in total. Stay under; say where the triangles went.
- Triangles are spent on silhouette at 0.3 m: screw heads and slots, knurled bands, wire, clips, edges with real
  bevels. Bake-only detail is under about 0.4 mm.

### Materials and textures

- Baked PBR per family: base colour, normal (OpenGL, +Y), and occlusion/roughness/metallic packed for glTF. One 2048
  set per family; the pistol and grip may use 4096 if 2048 does not hold up at 0.3 m (say so). Target at least
  60 px/cm on hero parts (pistol, grip, gimbal), 30 px/cm on tools and fixtures.
- No baked directional light or highlights in base colour. Stone, cloth, rubber, wood and dust are not metallic.
- Look: `AGENTS.md` section 4. Salvaged industrial metal, patched and repaired, wear at edges, handles, threads and
  where hands and tools go, not uniform grunge. Restrained cyan only where something is powered.
- Emissive parts (status pip, tester lamp, cure lamp, press vents) are their own small material.
- **Parts that get cleaned or change surface** (servo case dust, gimbal corrosion, mould residue, tinned lead ends,
  nanite seam) carry two baked sets on the same UVs: the clean one in the GLB, and the as-found one as loose PNGs in
  `export/tex/<part>__dirty_{color,normal,orm}.png`, listed under `wipes` in `parts.json`. Unity blends them with a
  mask.
- **Things that are cut** (alloy sheet into plates, strap and offcuts; leads) are modelled as the finished pieces
  lying together as the uncut whole, each piece its own node, with the cut line as a path.

### parts.json

```json
{
  "family": "pistol", "glb": "pistol.glb", "blender": "5.2.2", "generated": "2026-11-20T15:00:00Z",
  "parts": [
    {
      "id": "pistol.scale_l", "node": "pistol_scale_l", "label": "Left grip scale",
      "kind": "part", "parent": "pistol.frame", "item": null,
      "material": "wood", "mass": "light", "tris": 820, "size_mm": [42, 96, 9],
      "seat": { "clear": "pistol_scale_l__clear", "symmetry": 1, "tol_mm": 5, "tol_deg": 20 },
      "held_by": ["pistol.screw_grip_a", "pistol.screw_grip_b", "pistol.bind_wire"],
      "steps": ["s1.scales"]
    },
    {
      "id": "pistol.screw_grip_a", "node": "pistol_screw_grip_a", "label": "Upper grip screw",
      "kind": "fastener", "parent": "pistol.frame", "material": "steel", "mass": "tiny",
      "seat": { "clear": "pistol_screw_grip_a__clear", "symmetry": 0, "tol_mm": 3, "tol_deg": 25 },
      "fastener": { "bit": "slot", "turns": 6, "holds": ["pistol.scale_l", "pistol.scale_r"] },
      "steps": ["s1.screw_a", "s6.screws"]
    }
  ],
  "params": [
    { "id": "pistol.cell_latch", "node": "pistol_rig", "action": "cell_latch_param", "type": "hinge",
      "min": 0, "max": 22, "unit": "deg", "continuous": false }
  ]
}
```

Fields: `kind` is `part`, `fastener`, `tool`, `fixture` or `consumable`. `material` is the contact class for sound:
`steel`, `alloy`, `wood`, `rubber`, `plastic`, `copper`, `glass`, `canvas`, `paper`, `ceramic`. `mass` is `tiny`,
`light`, `medium` or `heavy` and sets the carry spring. `symmetry` is how many turns about the insertion axis seat
(1 = one way only, 2 = also reversed, 0 = any angle). `item` is the catalog item id when the part is an inventory item
(`droid_servo_damaged`, `scrap_alloy`, the nanite item, `copper_filament`, `field_toolkit`, the scrap pistol, the grip
mod). `steps` names the `DESIGN.md` step ids the part takes part in. Tools add
`"tool": {"verbs": ["turn", "window"], "tip": "<node>__tip", "tags": ["tool:screwdriver"]}`. Parts with paths, marks,
zones or wipes list them by id. `stats.json` gives triangles per part, texture sizes and bounds; `check.json` gives
the results of the checks in `ANYMACHINE.md` section 3.

### Review gate

Per `ANYMACHINE.md`: compare renders beside the sheets for every family, from the sheet's directions and from the
bench camera (about 40 degrees down, 0.6 m away, 35 mm), plus a close view at 0.3 m of each hero part, and an exploded
render that matches the exploded sheet. Look at them. List what differs. A build that ran without errors proves
nothing about how it looks.

## B. Runtime: the bench system and the crafting system

The bench system (`Scripts/Assembly/`) knows parts, tools, steps and the camera. The crafting system knows items,
recipes, weapons, orders and saves. They meet only here.

- `CityState.Assembly` is appended to the enum (`bench`). `GameSession.OpenAssembly(CraftingStationMarker station,
  string recipeId)` enters it; `Close()` leaves it as for every state. Esc therefore steps back from the bench.
- `craft` adds `Scripts/Crafting/AssemblyHost.cs` with this surface on `CraftingSession` (names are binding, bodies
  are `craft`'s):

```csharp
public enum CraftQuality { Rough = 0, Standard = 1, Fine = 2 }

public sealed class AssemblyTicket {          // what is on the bench for one job
    public string recipeId, stationId, weaponId;
    public ItemStack[] inputs;                // reserved from the pack (and locker), not yet consumed
    public bool resumed;                      // true when an unfinished job was reopened
}
public sealed class AssemblyResult {
    public string recipeId; public CraftQuality quality; public float score;   // 0..1
    public int faults; public float seconds; public ItemStack[] byproducts;    // e.g. copper_filament x1
}

// on CraftingSession
bool HasAssembly(string recipeId);                        // the recipe has a hands-on job
bool HandMade(string recipeId);                           // made by hand at least once (unlocks the timed craft)
bool CanBeginAssembly(string recipeId, out string reason);
AssemblyTicket BeginAssembly(string recipeId, out string reason);   // reserves inputs and takes the weapon to the bench
AssemblyTicket OpenTicket { get; }                        // unfinished job, also after loading a save
string AssemblyBlob { get; set; }                         // opaque JSON of the bench job; saved as WardSaveData.benchJob
void   ReportAssemblyStage(string stageId, string label); // for the journal and Field Notes line
bool CompleteAssembly(AssemblyResult result, out string reason);    // consume, grant with quality, fit, award, byproducts
bool AbandonAssembly(string[] spentInputs, out string reason);      // return the weapon and what was not spent
event Action AssemblyChanged;
```

- While a ticket is open the weapon cannot be drawn or fitted elsewhere; `craft` owns that rule and its notice.
- The recipe-to-job link is data: `CraftRecipe.assembly` (an id) in `WardCrafting.asset`, set by `craft`'s
  `apply_data.py`; the job itself is `Data/Assembly/<id>.asset` (`AssemblyRecipe`, owned by `bench`).
- Opening the bench: `CraftingStationMarker.Use()` (`craft`) opens the assembly directly when the current order's
  recipe has a job, is not yet hand-made and `CanBeginAssembly` holds, or when a ticket is open; otherwise it opens the
  Fabricator window as today. The Fabricator window gets a **Build by hand** button for recipes with a job, and its
  timed **Fabricate** is refused for them until `HandMade` (reason text from `craft`).
- Quality: stored by `craft` (per fitted slot on `WeaponLoadout`, and for carried mods in `CraftingState`), saved
  additively, scaling the mod's effects through `WeaponLoadout.Compute`. Old saves read as Standard.
- Order stages: with a job, fabricate and fit happen in one bench visit, so `Fit` is not seen. `craft` updates the
  journal step text, Brann's stage lines and the QA that expects `Fit`.
- Weapon feel (`DESIGN.md` section 10): `craft` adds the stats and reads them in combat and the view model. The bench
  system asks `craft` for a weapon's handling numbers before and after to place the holes on the test cards:
  `WeaponHandling CraftingSession.HandlingFor(string weaponId, string withModId = null, CraftQuality q = Standard)`
  returning sway amplitude (degrees), kick (degrees), side step (degrees), recovery (seconds), scatter growth.
- Save: `WardSaveData.benchJob` (string, additive, no version bump, null = no job), captured from `AssemblyBlob`.
- QA: `bench` adds `dev.assembly.*` commands (state, complete step, set fault, finish with a quality, abandon) and an
  `assembly` block in `snapshot.json`; `craft` adds what it needs under `dev.craft.*`.

## C. Audio

- Events are named `asm.<group>.<name>` (`DESIGN.md` section 11). The audio agent delivers WAVs under
  `Assets/AthenHill/Audio/ElevenLabs/Bench/<group>/` named `<group>-<name>-<nn>.wav` (variants `01..`), with `.meta`
  files written as the crafting voice generator does (stable GUIDs), and `audio/manifest.json`:
  `{"events": [{"id": "asm.screw.turn", "files": [...], "loop": true, "lufs": -24, "pitch_range": [0.9, 1.25],
  "note": "pitch follows resistance"}]}`.
- The bench system plays them through `AssemblyAudio` (its own pooled sources on the SFX mixer group, its own voice
  limit). It needs: loops that can be pitch-shifted cleanly (turn, drill, gyro, knit), one-shots with 3 or more
  variants for anything repeated (seat, snip, tap, click), and a contact matrix by material pair.
- Voice: `audio/lines.json` with `{id, speaker, text, trigger, file}`; Brann is `npc_brann` (voice Callum), Ossa
  `npc_ossa` (voice Victoria), existing settings. The bench system plays Brann's lines on his voice source with a
  caption (`BarkCaptionView`); Ossa's range lines are dialogue or radio lines bound by `craft`'s data script.
