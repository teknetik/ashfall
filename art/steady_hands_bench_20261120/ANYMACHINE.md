# AnyMachine in this programme: what it is, how it is set up, what we take from it

[AnyMachine](https://github.com/apekshik/anymachine) (MIT) is cloned at `/home/teknetik/code/vendor/anymachine`,
commit `d5e8889` (17 November 2026). It was written for Blender 5.2 (older experiments 5.0); this machine has
Blender 5.2.2 LTS.

## What it is and is not

It is a **method and a set of Blender Python scripts** for building machines as code: references first, every part a
separate mesh built by one script, working joints exposed as 0-1 parameters, machine checks for parts passing through
each other, glTF export verified by re-import. Its own README calls the repository "experiments"; there is no package,
no endpoint and nothing that runs in Unity.

Carl's brief asks for it to be used "for complex assembly, constraint, and machine-like interaction logic". The
interaction logic at the bench (grab, key, seat, fasten, tool verbs, faults, the step graph) is therefore our own
Unity code, described in `DESIGN.md` section 9. AnyMachine supplies the four things below, which are what make that
code trustworthy: parts that really are separate, joints on real axes, and proof that the assembly order works.

## 1. Reference-first, part by part (PIPELINE.md part 2)

Every object family gets reference sheets before any geometry:

1. an **overall sheet**: one object from six directions on grey, real size in the prompt, no labels;
2. **close-up sheets**, one mechanism per panel, generated with the overall sheet as the input image so the design
   does not drift; an **exploded sheet** for anything that comes apart on the bench;
3. a **parts breakdown** (`PARTS.md`): axes, origin, dimensions, every part, what it is made of, what holds it,
   which way it comes off;
4. one **build script** per family that makes every real part as its own mesh, on a shared kit;
5. **compare renders**: the model from the sheet's own directions, beside the sheet, differences written down;
6. a planned **second pass** where the model is plainer than the sheet;
7. **bake** (Cycles, CPU, here) and **export** with a stats file.

Our scale is different from AnyMachine's oil rig. Its rule "anything under about 8 mm is bake-only" was written for
props seen from metres away. The bench camera is 0.3 to 0.9 m from the work, so here: **anything that changes a
silhouette at 0.3 m is real geometry** (screw heads and slots, knurling bands, wire, solder pads, clips), and only
detail under about 0.4 mm (machining marks, scratches, stamped lettering, fine knurl) is bake-only.

Kit: our own `art/pistol_mods_20260930/src` (`pm_geo.py`, `pm_mats.py`, the bake in `build_all.py`) is the base,
copied into `kit/` in this folder and extended. Builders worth taking from AnyMachine's
`hardsurface/dugout_blender/props_hand/_common/hs.py` and `hardsurface/guns/*/svd_parts.py` (lathes with fluting,
slotted, cross and socket screws, hex bolts, pin heads, hinge knuckles on a pin, pipes with bends) are read, then
copied into `kit/am_parts.py` with the MIT notice. Its scripts are not executed.

One warning from its notes: the image service refused nearly all of its gun reference prompts, and that was not worked
around. If our sheets for the scrap pistol are refused, the pistol is modelled from grey renders of the existing
in-game pistol, written briefs and how the mechanism works, exactly as AnyMachine's rifles were. Prompts are not
reworded to get round a refusal.

## 2. Joints as 0-1 parameters

Every mechanism on the bench is a rig in the AnyMachine form:

- a bone on the real axis; rigid parts are bone-parented, each to exactly one bone;
- a custom property 0-1 on the armature, a driver, and a limit constraint, so out-of-range values clamp;
- baked to a **linear action one second long** named `<param>_param`, so `seek(t = value)` poses it in any engine;
- the joint spec in the node's glTF extras under `anymachine`: `{param, type, axis, min, max, unit}`.

In Unity the `AssemblyParam` component samples that clip at the parameter value (legacy clip sampling or a Playable,
never time-driven). Screws, the vise handle and cranks are continuous turns: they are driven by code from a turn count
and a pitch, not by a clip, but their axes and limits come from the same extras.

Rigs in this programme (the list in `CONTRACT.md` is the authority):

| Object | Parameters |
|---|---|
| Bench vise | `jaw` (0 open to 1 closed on the largest part; handle turns derived from jaw travel and thread pitch) |
| Scrap pistol | `cell_latch`, `trigger`, `cell_seat` (travel of the cell in its well) |
| Toolkit roll | `unroll` |
| Pliers, wire cutters, strippers | `jaws` |
| Screwdriver | `bit` (collar lock, for the bit change) |
| Hand drill | `crank` (continuous), `chuck` |
| Nanite press | `lever`, `platen`, `lock`, `vent` |
| Cure lamp | `arm_swing`, `arm_reach` |
| Bench tester | `probe_l`, `probe_r` (stowed to free) |
| Solvent jar, oil dropper | `lid`, `bulb` |
| Servo | `clip_1..3` (case clips springing), `gimbal_pitch`, `gimbal_roll`, `rotor` (continuous) |
| Stabilised grip | `gimbal_pitch`, `gimbal_roll`, `rotor` (continuous) |

## 3. Checks by machine before anyone looks

AnyMachine sweeps every parameter and counts triangle overlaps. We run that, and add the check an assembly needs:

- **Parameter sweep**: each 0-1 parameter in 50 steps, triangle overlaps against every part on another bone, minimum
  clearance reported. Zero overlaps that are not present at rest.
- **Assembly path sweep** (ours): for every Seat step in `DESIGN.md`, the part is moved along its insertion axis from
  clear to seated in 40 steps against every part that is seated at that point of the step graph. Requirements: no
  overlap anywhere on the path, and at the seated end contact only on the faces listed for that joint. The same sweep
  run backwards proves each removal. A part that cannot leave without passing through another is a modelling error or
  a wrong step order, and either way it is found here and not in the game.
- **Fastener check**: every screw's axis passes through the holes of everything it holds, and its seated head touches.
- **Export verify**: the GLB is re-imported into an empty scene and counted against `parts.json`: nodes, triangles,
  bounds, empties, actions and their lengths.

The check script writes `check.json` per family. A family is not handed to Unity with a failing check.

## 4. Write the numbers out

AnyMachine's `stilt_info.json` holds every part, bone, axis and stroke for whoever imports it. Ours is `parts.json`
per family (schema in `CONTRACT.md`): the Unity installer builds every prefab, socket, fastener and parameter from it,
so the modeller and the runtime cannot disagree about where a part seats or which way it comes off.

## What we do not take

- Image-to-3D meshes as skins (its first route): not for bench parts, which are seen from 30 cm.
- The GPU render farm: bakes run locally on the CPU, one at a time, through the Blender slot.
- The motion-reference step with video models: fal has no credit, and tool and part motion here is short and
  mechanical; it is written from how the mechanism works and judged in the player.
