# Crafting Studio: one bench system for every weapon, armour piece and utility

Written 21 November 2026 from Carl's ask: turn the Steady Hands bench into a crafting studio that any item can be
pulled into (a rifle, a recipe, a blueprint), taken apart and upgraded, without two days of code per item.
Proposal. Nothing here is built yet. It builds on `art/steady_hands_bench_20261120/` (DESIGN, CONTRACT, SEAM).

## 1. Where Steady Hands leaves us

**The runtime is already mostly generic.** `Scripts/Assembly/` (about 4,900 lines) has no step table in code. It runs
any `AssemblyRecipe`: 7 verbs (Seat, Turn, Path, Window, Wipe, Point, Flick), a dependency graph of steps, faults and
recovery, quality, save and resume, the crafting hand-off, and a bot (`AssemblyBot`) that can play a job end to end.
Parts, seats, fasteners, marks, paths, wipes and params all come from each art family's `parts.json`.

**What ties it to the pistol grip** (small, but it blocks a second job):

| Coupling | Where |
|---|---|
| Weapon id hard-coded `weapon_scrap_pistol` | `AssemblyCraftLink.cs:41`, `:92` |
| Bench fixture ids in code: `tools.roll`, `fixtures.vise`/`vise_swivel`, `fixtures.board/`, `fixtures.schematic_*` | `AssemblySession.cs:187,283,1077,1082`, `AssemblyVerbs.cs:94` |
| The test stage (aim at the card) tuned for a pistol in `AssemblySettings` (`aimReach`, `aimSide`, `aimLow`) | `AssemblySettings.cs:45-48` |
| One scene root, **Steady Hands bench**, with one job's parts baked into its prefab | `SteadyHandsBench.prefab`, the dated installers |
| `layout.json` mixes the bench's own places (vise, dish, mat, roll) with this job's (97 places in one file) | `data/layout.json` |
| Installers are per programme and dated (`AssemblyBenchInstall20261120`, `SteadyHandsBenchInstall20261120`, `BenchTutorInstall20261121`, about 2,300 lines) | `Editor/` |

**What actually costs the two days is content, not code.**

- `steps.json`: 81 steps and 213 actions, written by hand (58 KB). 95 of the actions are Seat, and most of those are
  "undo this screw, lift that part off, put it back".
- `layout.json`: 97 places, also by hand.
- Six Blender families, each with its own `build.py` and `check.py`.

A second job built the same way repeats all of that. So the studio has to make content cheap: most of it should be
**generated from the model's own data**, and only the interesting middle part should be written by hand.

## 2. The idea: four layers, each authored once

```
 Station        Brann's metal bench, Tamsin's soft-goods table, ...   (once per vendor)
   + Item       a weapon / armour piece / pack as separable parts      (once per item)
   + Module     an upgrade that fits a slot (grip, barrel, stock, ...) (once per module)
   + Blueprint  a short file: which item, which slot, which module,     (once per recipe)
                which operations make it, what it changes
   = Job        the generated step table the existing runtime already plays
```

### 2.1 Station (once per bench)

Everything that belongs to the bench and not to the job: fixtures, tool roll, places on the bench (vise jaws, dish
slots, mats, pads, card board), camera shots, lamps and ambience. `layout.json` splits into `station.json` (stays with
the bench) and the job's own few places (generated, section 2.4).

The hard-coded ids become **roles** in `station.json`: `holder` (the vise and its swivel), `toolStore` (the roll),
`testBoard` (card board), `schematic`, `dish`, `scrap`. The code asks the station for "the holder", not for
`fixtures.vise`. Tamsin's table then supplies its own holder (a clamp frame) and its own tool store with no code change.

### 2.2 Item (once per weapon, armour piece, pack)

A family GLB plus `parts.json`, exactly as the contract already specifies, with one addition: **standard slot nodes**
per item class, so every weapon is cut along the same lines.

| Class | Slots (node `slot_<name>` with a pose mark and an interface id) |
|---|---|
| Pistol | frame, grip, barrel, cell, sight, muzzle |
| Rifle | receiver, stock, grip, barrel, cell, optic, muzzle, handguard |
| Armour piece | shell, liner, strap set, plate pockets |
| Pack | frame, body, belt, pouches |

Each slot names an **interface** (`dovetail_tang_v1`, `barrel_thread_m14`, `cell_bus_a`). A module fits any item whose
slot has the same interface. That replaces the current `CraftModifier.weaponIds` list for bench jobs, so a grip made
for the pistol's tang interface also fits a later pistol with the same tang.

The item's `parts.json` already says what holds what (`held_by`) and how each fastener comes out (`fastener.bit`,
`turns`, the `__clear` pose). **That is enough to generate disassembly.**

### 2.3 Module (once per upgrade)

The new part, as its own family or as parts within one: the grip core, the plates and so on. Same contract, plus
`fits: <interface>` and the effects it has on the weapon (already data in `WardCrafting.asset`, scaled by quality).

### 2.4 Blueprint (once per recipe): the file a designer writes

```yaml
id: assembly_rifle_precision_barrel
recipe: recipe_rifle_precision_barrel      # existing CraftRecipe: inputs, skill, XP
station: brann_metal
item: weapon_field_rifle
slot: barrel                               # strip down to this slot, swap, rebuild
module: barrel_precision_rifle
depth: standard                            # flagship | standard | service (section 3)
make:                                      # the hand-made middle, from the operation library
  - op: clean_bore        { part: rifle.barrel_old }          # wipe + flick test
  - op: cut_from_stock    { stock: materials.tube, piece: barrel_precision.blank, path: cut }
  - op: drill_pattern     { part: barrel_precision.blank, marks: [vent_1, vent_2, vent_3, vent_4] }
  - op: lap_bore          { part: barrel_precision.blank }    # turn with a window
  - op: thread_end        { part: barrel_precision.blank, die: tools.die_m14 }
test: range_card_long                      # the before/after card, sized for a rifle
byproducts: [{ item: scrap_alloy, n: 1 }]
```

A **generator** in the editor expands it into the same `steps.json` form the runtime reads today:

1. **Lay out**: item onto the station's work place, toolkit out, before-card (from the `test` profile).
2. **Strip** to the slot: walk `held_by` from the slot's part outward. For each blocker, emit the steps its data
   describes (a fastener emits Turn with its bit and turns, then Seat to the dish; a part emits Seat to its
   parts-mat outline; a param latch emits a Turn `noSpin` with `drive`). Order comes from the graph, and parts with no
   dependency between them land in one `free` step so the player picks the order.
3. **Make**: each `op` is a template from the **operation library** (below), filled with the part names.
4. **Fit**: the reverse of strip, with the module's parts in place of the removed ones; screws get their torque
   window on the way back in.
5. **Test**: the test profile's card and shake steps.

The generated file sits in the job folder and can be **hand-edited where a step needs flavour** (the seized screw, the
cracked tang, Brann's lines). Overrides go in the blueprint as patches by step id (`patch: { strip.screw_b: {...} }`),
so regenerating does not lose them.

### 2.5 Operation library (written once, reused everywhere)

Steady Hands already contains most of the operations a weapon or armour job needs. Each is lifted out as a template
with named holes:

| Operation | From Steady Hands | Reused for |
|---|---|---|
| `unfasten` / `fasten` (bit, turns, torque window, cam-out, strip) | s1.screw_a, s5.torque | every screw on every item |
| `seized_fastener` (oil, tap, turn, round-off recovery) | s1.screw_b | flavour on any item |
| `clamp` / `release` | s1.clamp | anything in the holder |
| `drive_pin` | s1.pin, s6.pin | pins on any frame |
| `unplug` / `plug` (keyed) | s1.lead, s6.plug | cell bus, sensors |
| `clean` (solvent, brush, pick, oil, spin test) | s3.bath to s3.spin | bores, bearings, actuators |
| `solder_join` (trim, strip, tin, join, sleeve, test) | s3.trim to s3.test | any wiring job |
| `cut_from_stock` (scribe, clamp, cut, file) | s3.scribe to s3.file | plates, straps, shims |
| `drill_pattern` (punch, drill) | s3.punch, s3.drill | mounting holes |
| `bend` | s3.strap | straps, brackets |
| `press_fuse` (mould, charge, press, open, flash) | stage 4 | any nanite-fused core |
| `seam_cure` | s5.seam, s5.cure | any nanite seam |
| `card_test`, `shake_test` | s0.card_before, s7.* | every weapon, by test profile |

Tamsin's bench adds `stitch`, `rivet`, `punch_hide`, `cut_pattern` later, on the same seven verbs.

## 3. Depth: not every upgrade should be 17 minutes

Carl's rule from 21 November stands: **everything is built by hand, with no Auto-assemble**. If every swap is a 15 to 20
minute job, though, a player with a rifle and six mods faces two hours at the bench. I recommend three depths, all hands-on:

| Depth | Length | What is hand-written | Example |
|---|---|---|---|
| **Flagship** | 15 to 20 min | most of it; generator gives strip and fit | Steady Hands, a first-of-its-kind quest job |
| **Standard** | 4 to 8 min | 2 to 5 `op` lines | rifle precision barrel, overclocked cell |
| **Service** | 1 to 2 min | nothing: strip to the slot, swap, fit, test | moving an already-made mod between weapons, refitting a looted module |

Depth only changes how many operations sit in "make" and whether the long test runs. The verbs, feel, quality and
faults are the same.

## 4. What making the rifle upgrade would take after this

1. **Art:** build `rifle` as a family with the weapon kit: standard slot nodes, `held_by`, fasteners, marks; run
   `check.py`. This is the largest remaining cost and it is real modelling work. The in-game rifle is a fused mesh
   like the pistol was, so it has to be rebuilt to the same outline. A **rifle template** in the kit (receiver,
   stock, barrel, handguard as parametric builders, slot nodes placed by rule) shortens it a lot.
2. **Module art:** `barrel_precision` family (two or three parts).
3. **Blueprint:** the 20-line file above.
4. **Run `AssemblyStudio build assembly_rifle_precision_barrel`:** imports the families, generates the job, builds the
   recipe asset, verifies it against the station and `parts.json`, and has `AssemblyBot` play it to the end at three
   quality levels. A job the bot cannot finish never reaches the player.
5. **Tune in play** (window widths, Brann's lines, the test profile).

No new C# for steps 3 to 5. The only code you'd expect is a new verb or test profile when a job really needs one.

## 5. The one-time engine work

In order. Each phase leaves Steady Hands working and is checked by the bot replaying it.

| Phase | Work | Proof it is done |
|---|---|---|
| **1. Unpin** | Weapon id from the ticket and recipe; fixture ids become station roles; the test aim from a test profile, not `AssemblySettings` | Steady Hands bot run unchanged; grep finds no family id in `Scripts/Assembly/` |
| **2. Split station from job** | `station.json` and job places; the bench spawns the job's families at session start instead of carrying them in the prefab; one generic `AssemblyStudio` editor command replaces the dated installers (they stay for rollback) | the bench prefab holds no pistol or servo parts; Steady Hands loads and plays as a job |
| **3. Generator** | strip and fit from `held_by` and fastener data; operation templates; blueprint patches | regenerate Steady Hands from a blueprint, then diff against the hand-written `steps.json`: same steps in strip and fit, the rest from ops and patches |
| **4. Slots and interfaces** | slot nodes in the kit; `fits` and interfaces on modules; `WeaponLoadout.Accepts` reads interfaces for bench-made mods | the gyro grip (Mark II) fits through its interface, as before |
| **5. Second job** | `assembly_rifle_precision_barrel` at Standard depth | played by the bot and by Carl |

Phases 1 and 2 are refactors of code that exists. Phase 3 is the new piece that pays for itself. Before phase 5, a cheap
test is a **Service** job on the pistol with no new art: strip the grip slot and refit the existing Mark II gyro
grip. It exercises the generator and the swap with models we already have.

## 6. Decisions (Carl, 21 November 2026, 20:10)

1. **Depth tiers: decided.** Flagship, Standard and Service as in section 3. Steady Hands stays the flagship and the
   **introduction to every tool and process at the bench**: later jobs can assume the player has learnt the seven
   verbs, the toolkit, the vise, the press and the test card there, so Standard and Service jobs carry no tutorial.
2. **Removed parts are kept: decided.** A module taken out of a slot goes back to the pack as an item, with its quality,
   and can be refitted later by a Service job. Parts the item came with (the old grip scales, the stock barrel) are
   also kept as items where they are whole; parts cut, fused or spent in a job are not.
   Consequence for phase 4: `WeaponLoadout` must give a removed module back with its quality (today `Set(slot, null)`
   drops the quality), and the save must carry quality on carried mods, as `CraftingState` already does for bench-made ones.
3. **Every item is rebuilt as separable parts: decided.** No Meshy auto-split route. Each weapon, armour piece and pack
   that gets a bench job is rebuilt in Blender to its current outline, as the pistol was. The weapon kit's class
   templates (rifle, pistol, armour shell, pack frame) are therefore part of phase 3, not optional.
4. **Order: default.** Pistol Service job (refit the Mark II gyro grip) first, then the rifle precision barrel.

## 7. Clash with the running programme

The Steady Hands agents were still working at 20:04 on 21 November (`bench` publishing `READY FOR BUILD real11`).
`bench` owns `Scripts/Assembly/**` and the installers (`CONTRACT.md`, "Who owns what"), which phases 1 to 3 change.
Studio work on those files starts when that programme's round has finished, or is handed to `bench` through the
orchestrator. It must not be done alongside it.
