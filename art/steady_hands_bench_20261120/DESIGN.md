# Steady Hands at the bench: interaction design, flow and state machine

Written 20 November 2026 from Carl's brief (`BRIEF.md` in this folder). This is the design every agent on the
programme builds from. It carries out phases 4 to 6 of [the crafting rework plan](../crafting_assembly_20261120/PLAN.md)
at a larger scale: the first hand-made Stabilised Pistol Grip is a 15 to 20 minute job at Brann's bench, not a short
mini-game. Read [AGENTS.md](../../AGENTS.md) first (machine limits, batched verification, lore).

Status words used below: **decided** (by Carl, or by the lead where he hands such choices over), **default** (the
lead's choice, Carl can overrule, built so it is cheap to change), **open**.

## 1. What the player does and feels

The player brings a scrap pistol that rattles and walks off target, a Damaged Servo that Ossa identified, two Scrap
Alloy and five tier-one nanites to Brann's bench. They take the pistol's grip off, open the servo, clean and rewire
its gimbal, cut and drill two side plates, fuse a grip core in the nanite press, plug the parts together, fit the grip
and test it. Nothing is done from a menu. Every part is an object on the bench that is picked up, turned, seated,
fastened or worked with a tool, and every action has weight, sound and a visible result.

The job proves itself twice: a **before and after card** (three low-power test pulses at a paper card before the strip
and after the fit, pinned side by side by Brann), and a **shake test** (the bare pistol rattles and keeps swaying; the
finished one settles at once with a single soft tick of the damper).

## 2. Decisions and defaults

| # | Subject | Choice | Status |
|---|---|---|---|
| 1 | Parts are real separate 3D models, laid out, seated and fastened | from PLAN.md | decided (Carl) |
| 2 | Asset method: reference sheets first, part by part in Blender Python, AnyMachine `PIPELINE.md` | from PLAN.md | decided (Carl) |
| 3 | What AnyMachine is used for | It is a Blender method and helper kit, not a Unity library. We use its reference-first modelling, its 0-1 parameter rigs baked to linear glTF actions (vise, screws, latches, press, pliers), its sweep checks for parts passing through each other, and its export verification. The Unity socket, fastener and tool logic is ours (section 9). See `ANYMACHINE.md` | decided (lead) |
| 4 | Length | 15 to 20 minutes for the first hand-made grip, about 95 actions in 8 stages | decided (Carl's brief) |
| 5 | Repeats | **No Auto-assemble.** Every Stabilised Pistol Grip is built by hand at the bench, the first and every later one (Carl, 21 Nov 2026: "i should have no option to auto fabricate it, the only game option is to build it yourself"). Replaces the earlier rule from PLAN.md (Auto-assemble on the timer after one hand-made success) | decided (Carl) |
| 6 | Leaving the bench mid-job | Progress is kept. Finished steps stay finished, the pistol stays on the bench in pieces and cannot be drawn until the job is done or abandoned at the bench (abandon returns pistol and unused inputs). Saved in the save file. A step in progress resets | default |
| 7 | Damage or Esc | Esc steps back from the bench with the job kept (rule 6). The shop is in the city, so damage is not expected; if it happens the same rule applies | default |
| 8 | Hands | Tools and parts are driven directly with weight and their own motion; the player's hands are not shown during fine work. The test stage shows the first-person arms on the pistol if a bench driver for the existing view model proves clean (it is tied to combat state and weapons are holstered inside the shop), otherwise it too is hands-free. Hands on tools by IK is a later round, judged from captures | default |
| 9 | Quality | Rough / Standard / Fine from mistakes and precision; the grip's effect scales with it | decided (PLAN.md), numbers default |
| 10 | Base pistol feel | The unmodified scrap pistol gets visibly more sway, kick and scatter; the grip removes most of it. Numbers in data, tuned in play. The range tutorial must stay passable with the bare pistol | default |
| 11 | Interface | No panels for the core work. One step line in the existing Field Notes corner, captions for Brann, a pinned schematic on the bench backboard and a parts mat with outlines carry the guidance | decided (Carl's brief) |
| 12 | Where | Brann's workbench in the Salvage shop (`station_field_fabricator`), nowhere else for now | decided |
| 13 | The scrap pistol model | The in-game pistol is one fused Meshy mesh (12k triangles) and cannot come apart. It is rebuilt as separable parts to the same outline, bore, rail and grip position, so the five other mods and the hand poses still fit; the rebuilt pistol replaces it in the hand as well as on the bench, with the Meshy one kept for rollback | decided (PLAN.md phase 5) |
| 14 | Mark I against Mark II | The existing Mark II grip (`grip_gyro_braced`) is the powered gyro with the cyan status pod. This grip is therefore a **passive damper**: the servo's gimbal carries its rotor as a swinging mass inside the damping coil, and the coil is wired closed through a trim resistor. No power from the cell, no cyan light. The whirr the brief asks for is heard when the bench tester drives the coil | default |
| 15 | Brann | He stays behind his counter, about 4 m from the bench, and speaks from there with captions. He does not walk over in this round | default |

## 3. The grip, as an object

Ossa's line fixes the fiction: the servo's gimbal "is still true. Wired into a pistol grip, that should take the kick
out of your scrap pistol." The Stabilised Pistol Grip is therefore:

| Sub-part | Made from | How |
|---|---|---|
| Grip core (spine with a bearing pocket and a dovetail for the frame tang) | alloy offcuts + 5 nanites | fused in the nanite press |
| Gimbal damper (gimbal ring, rotor as the swinging mass, damping coil, cradle) | the servo's gimbal assembly | cleaned, oiled, spin-tested, pressed into the pocket |
| Damper loop (the two coil leads joined across a trim resistor) | the servo's leads and a resistor snipped from its burnt board | trimmed, stripped, tinned, soldered, tested |
| Left and right side plates | 2 Scrap Alloy | scribed from the old grip scale, cut, filed, drilled |
| Reinforcement strap (old Warden orange paint outward, as on the present grip mod) | alloy strip left from the plates | bent in the vise |
| 4 plate screws | the servo's case screws | reused |
| Nanite seam | residue in the press hopper | traced with the applicator, cured under the lamp |

Spare parts to the pack: 1 Copper Filament (stator winding). Scrap bin: burnt board, chewed gears, old grip scales.

## 4. The bench

The bench is the existing Meshy workbench (worktop 2.2 x 1.15 m at 0.864 m, clear in front of its screen; its texture
is too soft for a 0.3 m view and its vise is fused to the lower shelf). Everything the player works on therefore sits
on our own surfaces, and the Meshy bench is the out-of-focus surround.

Fixed things: a steel-edged rubber **work surface** laid over the worktop, **vise** with soft jaws (left), **parts mat** with worn outlines (centre front), **work mat**
(centre), **magnetic dish** for fasteners, **cradle stand** for the stripped frame, **solvent jar**, **bench tester**
(two probes, a lamp and a buzzer), **card board** on the rear frame with a clip for two test cards, **nanite press** with a mould rack (right rear), **cure lamp** on an arm, **bench
rule** set into the front edge, **scrap bin**, **schematic** clipped to the rear frame. Carried: the **Field Toolkit** roll (screwdriver with slotted and cross bits, pliers, wire cutters, wire
strippers, wire brush, pick, pin punch, scribe). Brann's bench tools (fixed to the station, per the phase 2 tool tags):
mallet, flat and round file, snips, hand drill, soldering iron with stand and solder, oil dropper, nanite applicator.

**Look target (accepted).** `concept/bench_overview_fal.jpg`, a generated picture of the whole bench that Carl saw on
20 November and answered with "that image looks sick". It fixes the character the game has to reach in the bench
camera: one warm work lamp with soft contact shadows, a black rubber mat with a rule along its front, a dark green
cast-iron vise, a worn yellow press, a waxed canvas roll of re-taped tools, flaking orange Warden paint on the alloy,
the pistol's cyan cell as the only cool light, shallow depth of field. It is a picture, not the game: nothing is
accepted in the game until Carl has seen it there. Its servo is wrong (a robot fist); the servo is a joint actuator.

**Camera (default).** A bench camera at standing eye height looking down about 40 degrees, framing the whole top.
Right mouse held orbits a little (about ±25 degrees yaw, ±12 pitch); the wheel zooms between the whole bench and a
close view that follows the active part. Stages that need it move the camera on their own (vise close-up, press,
tester). Entering blends from the player's view in about 0.8 s; Reduced Motion cuts instead. Depth of field follows the
focus object and is off under Reduced Motion.

## 5. Controls

Mouse first, with complete keyboard access (AGENTS.md section 2: keyboard access is kept).

| Action | Mouse | Keyboard |
|---|---|---|
| Point | move | arrows or WASD move a focus ring between objects; Tab cycles in step order |
| Pick up / put down / use | left button (hold to carry, release to place) | Space or Enter |
| Turn a held part about the bench normal | wheel | Q / E |
| Flip a held part | middle button | R |
| Tool action (turn, stroke, squeeze, heat) | hold left, with motion where the verb needs it | hold Space; A / D or Left / Right for motion |
| Put the tool back | right click, or click its slot | X |
| Look around the bench | hold right button | hold Left Shift + arrows |
| Zoom | wheel with nothing held | Z / C |
| Hint | (waits on its own, section 8) | H |
| Step back from the bench | Esc | Esc |

Mouse-motion verbs all have a hold-and-time keyboard form so the job can be finished without a pointer.

## 6. Verbs

Eighteen actions on the bench, built from seven input archetypes. An archetype is one class; a step names the
archetype, the tool, the target and its numbers.

| Archetype | What the player does | Used for | Good / bad outcome |
|---|---|---|---|
| **Seat** | carry a part, turn it to its key, bring it to its socket; it pulls in when close and aligned | place, lift off, slide on, plug in, drop into the dish | click and settle / will not seat, the blocking part shudders |
| **Turn** | hold on a target and turn (mouse circle or wheel; keyboard hold) against resistance | screws, vise handle, bobbin crank, solvent swirl, hand drill | steady progress / cam-out, cross-thread, bind |
| **Path** | follow a line at a steady pace | peel the tape, scribe, snip along a line, trace the nanite seam, route the harness | clean line / wander is marked and costs quality |
| **Window** | hold or strike, and stop inside a window you read from sound, colour or position | final torque, punch taps, tin and solder, press pressure, pour, bend to angle, file to the line, press fit | in the window / over or under, each with its own recovery |
| **Wipe** | rub a tool over a surface until it is clean | wire brush, dust off the servo, clean the mould | reveals metal / missed patches show in the spin test |
| **Point** | aim at a small mark and click | snip a wire, oil a trunnion, pick a detent, probe a pin, centre punch | exact / wrong spot has a consequence (short lead, spilled oil) |
| **Flick** | throw the mouse, or shake a held object | spin test, shake test | reads the object's state back to the player |

Feel rules for every verb: the object follows the hand on a critically damped spring with a little lag and tilt, so
it has weight; heavy things (vise handle, press lever) move slower and overshoot nothing; a seat ends with a 60 to
90 ms pull-in, a contact sound chosen by the two materials, a 2 to 3 mm camera nudge (none under Reduced Motion) and a
brief rim flash on the seam; resistance is carried by sound pitch, tool vibration and how far the tool moves per unit
of input, never by a floating gauge.

## 7. Flow

Stages are ordered. Inside a stage, steps form a dependency graph: any step whose prerequisites are met can be done,
so the player chooses the order of screws, leads and plates. `id` is stable and used by data, saves, audio and QA.
Times are for a first play at an unhurried pace.

### Stage 0: lay out (about 1:15)

| id | Step | Archetype / tool | Feedback | Mistake and recovery |
|---|---|---|---|---|
| s0.pistol | Lay the pistol on the work mat | Seat | steel on rubber | none |
| s0.roll | Untie and unroll the toolkit | Turn (strap), then Seat | canvas, tools clink | none |
| s0.salvage | Tip the servo, alloy and nanite vial into the tray | Seat | parts tumble and settle | a part rolls off: pick it up from the floor tray |
| s0.card_before | Three test pulses at the card on the wall | Point (aim wanders) | weak pulse, hole in card; the card goes on the left clip and Brann calls his verdict from the counter | none; this is the "before" record |
| s0.shake_before | Pick the pistol up and shake it | Flick | rattle, long sway | optional, prompted once |
| s0.cell | Thumb the latch and pull the charge cell; set it on the insulated pad | Seat (latch is a 0-1 rig) | latch snap, contact pop, status lamp dies | pulling without the latch: it will not move, latch glints |

### Stage 1: strip the pistol (about 2:30)

| id | Step | Archetype / tool | Feedback | Mistake and recovery |
|---|---|---|---|---|
| s1.clamp | Set the frame in the vise and close it snug | Seat, Turn (vise) | screw thread, jaws bite on the pads | over-tight: creak, marked frame, small quality loss; back off |
| s1.bind | Snip the two wire twists holding the old grip | Point / cutters | snip, wire springs open | none |
| s1.tape | Peel the tape and leather wrap | Path | tearing tape, dry leather | tape tears: start the peel again from the tear |
| s1.screw_a | Take out the upper grip screw | Turn / screwdriver, slotted bit | thread unwinding, screw rises, drops in the dish | wrong bit cams out |
| s1.screw_b | The lower screw is seized: oil it, tap it, then take it out | Point / dropper, Window / driver handle, Turn | driver slips with a bark of metal; after oil and two taps it cracks free | forcing it rounds the slot: turn it out with pliers (slow) |
| s1.scales | Lift off the left and right scales, set them on the parts mat | Seat | dry wood on steel | blocked while a screw holds them |
| s1.lead | Pinch the tab and pull the trigger lead off the cell bus | Seat / pliers or bare | tab click, connector pop | pulling by the wire frays it: re-strip in stage 3 |
| s1.pin | Drive the housing pin out with punch and mallet, pull it with pliers | Window (three taps), Seat | ringing taps, pin walks out | a miss dents the frame (quality), a bent pin is straightened in the vise |
| s1.housing | Slide the backstrap housing off its rail, keeping a thumb on the spring | Seat (slide) | scrape, spring load | let go early: the spring jumps; find it on the bench |
| s1.inspect | Turn the bare frame over and find the cracked tang | Seat (free turn) | crack catches the light; Brann comments | none |

### Stage 2: open the servo (about 2:30)

| id | Step | Archetype / tool | Feedback | Mistake and recovery |
|---|---|---|---|---|
| s2.swap | Move the frame to the cradle stand; clamp the servo | Seat, Turn (vise) | as s1.clamp | as s1.clamp |
| s2.dust | Brush the caked dust off the case to find the screws and seam | Wipe / wire brush | bristles on alloy, dust falls | none |
| s2.screws | Four case screws, cross bit | Turn / screwdriver | each drops in the dish | slotted bit cams out; these screws are reused, a damaged head costs quality |
| s2.stripped | One head is already chewed: grip it with pliers and turn | Turn / pliers | grinding bite | slips if not squeezed first |
| s2.pry | Lever the case open at three clips along the seam | Point then Window / pick | plastic creak, clip release | too hard snaps a clip (cosmetic) |
| s2.board | Unplug and lift out the burnt control board, snip the trim resistor off it, bin the board | Seat, Point / cutters | connector pop, snip, board into the bin | resistor cut with a short leg: harder to solder (smaller window) |
| s2.leads | Snip the two coil leads and the sense lead at the board end, at the bands | Point / cutters | snip | cut short: splice later (one extra solder joint) |
| s2.circlip | Spring the circlip off the gear post | Window / pliers | ping | it flies if not held: find it |
| s2.gears | Lift the three gears off, top first, bin them | Seat | toothed scrape | wrong order: blocked gear shudders |
| s2.trunnion | Two trunnion screws, then lift the gimbal out with its leads | Turn, Seat | the gimbal swings as it comes free | none |
| s2.winding | Wind the stator copper onto the bobbin: one Copper Filament to the pack | Turn (crank) | wire singing | too fast snaps the wire: rejoin and go on |

### Stage 3: process the parts (about 4:00)

| id | Step | Archetype / tool | Feedback | Mistake and recovery |
|---|---|---|---|---|
| s3.bath | Swirl the gimbal in the solvent jar | Turn (swirl) | liquid, grime clouds off | none |
| s3.brush | Wire-brush the race and trunnions clean | Wipe / wire brush | bright metal appears | missed patches fail s3.spin |
| s3.pick | Pick the grit out of three detents | Point / pick | tick, grit flicks out | none |
| s3.oil | One drop of oil on each trunnion | Point / dropper | drop lands and wicks in | too much: wipe it off with the rag |
| s3.spin | Flick the rotor and listen | Flick | smooth long whirr, or a grind if it is not clean | grind: back to the brush |
| s3.trim | Trim the two coil leads to the mark on the bench rule; cut the sense lead off flush | Point / cutters | snip | short: splice |
| s3.strip | Strip 8 mm off each coil lead and twist the strands | Window (squeeze) then Seat (pull) / strippers | insulation slides off | nicked strands: trim and strip again |
| s3.tin | Tin both ends and the resistor's legs | Window / iron and solder | solder flows bright, smoke curl | cold: dull grey, reheat; hot: insulation scorches, trim |
| s3.loop | Join the two leads across the trim resistor: hold each in the third-hand clip, solder, slide the sleeves over and shrink them | Seat, Window, Window | solder flows, sleeve tightens | a cold joint is caught by s3.test |
| s3.test | Put the bench tester's probes across the resistor | Point / tester probes | lamp lights, the rotor kicks and whirs; flicked now, it brakes within a turn | no lamp: a cold joint, reflow it |
| s3.scribe | Lay an old scale on the alloy as a template and scribe round it | Seat, Path / scribe | scratch line | wandering line: scribe again |
| s3.cut | Clamp both alloy sheets stacked, cut to the line | Seat, Turn, Path / snips | shearing metal, offcut drops (kept for the core) | wander leaves more to file |
| s3.file | File the stacked edges to the line and break the corners | Window (strokes) / flat file | file bite, filings | past the line: a gap the nanite seam must fill (quality) |
| s3.punch | Centre-punch four hole marks through the scale's holes | Point then Window / punch and mallet | dimple | off-centre: punch again beside it |
| s3.drill | Drill the four holes through both plates | Turn with pressure / hand drill | swarf curls, break-through | pushing hard binds the bit: back out |
| s3.strap | Bend the alloy strip twice in the vise to make the strap | Seat, Window (lever to the angle mark) | metal yields | over-bent: bend back once; twice cracks it, use the spare strip |

### Stage 4: fuse the grip core (about 2:30)

| id | Step | Archetype / tool | Feedback | Mistake and recovery |
|---|---|---|---|---|
| s4.mould | Pick the pistol-tang mould from the rack (the schematic names it), seat it in the press, brush it out | Seat, Wipe | steel on steel | wrong mould will not seat on the keyed bed |
| s4.charge | Lay the alloy offcuts in the cavity and pour the nanites to the line | Seat, Window (pour) | grey fluid, faint crawling sound | over-pour: flash to file off later |
| s4.press | Close and lock the press, pump to the green band and hold while the nanites knit | Turn (lever), Window (hold, with drift) | hiss, glow in the vents, rising then steady tone | out of band: the knit pauses; long drops leave voids (quality) |
| s4.open | Vent, open, lift the core out with pliers and quench it | Window, Seat | vent burst, sizzle | bare hand on hot metal is refused |
| s4.flash | Knock the flash off and ease the bearing pocket with the round file until the gimbal drops to its shoulder | Window / files, Seat (test fit) | pocket takes the gimbal with a soft stop | too many strokes: loose pocket, shim with seam paste (quality) |
| s4.pressfit | Press the gimbal cradle home in the vise, stopping at the flush line | Seat, Window (vise) | creak, then a dead stop | past flush cracks the cradle lug: nanite-mend it (time) |

### Stage 5: assemble the grip (about 2:30)

| id | Step | Archetype / tool | Feedback | Mistake and recovery |
|---|---|---|---|---|
| s5.loop | Tuck the damper loop into the core's side channel and press it into two clips | Path, Seat | lead slides, clips snap | a lead pinched under a plate is caught at s5.damp |
| s5.rotor | Drop the rotor back into the gimbal and fit the retaining ring | Seat, Window / pliers | ring snaps into its groove | ring flies: find it |
| s5.strap | Slide the strap over the spine until it clicks | Seat | spring click | back to front will not seat |
| s5.plates | Left plate on its pegs, right plate on its pegs | Seat | peg seat | swapped plates will not seat |
| s5.start | Start the four servo screws by hand | Turn | first threads catch | cross-thread: back out and restart |
| s5.torque | Drive them in a cross pattern, then final torque each | Turn, Window / screwdriver | plate pulls down evenly; pitch rises into the window | one side first rocks the plate: loosen and redo; over-torque strips (pliers, spare screw from Brann's jar) |
| s5.seam | Trace both plate seams with the nanite applicator | Path | fine hiss, seam greys then closes | gaps left: retrace them |
| s5.cure | Swing the cure lamp over and wait ten seconds; put tools back meanwhile | Seat (lamp arm), wait | lamp hum, seam goes bright then dull | lifting early leaves a soft seam (quality) |
| s5.damp | Hold the grip and tilt it sharply | Flick | the mass swings once and stops dead with a soft tick | it keeps swinging: a pinched or broken lead, open one plate |

### Stage 6: fit the grip (about 1:30)

| id | Step | Archetype / tool | Feedback | Mistake and recovery |
|---|---|---|---|---|
| s6.slide | Slide the grip up onto the frame tang | Seat (dovetail) | heavy clunk | not square will not start |
| s6.plug | Feed the pistol's trigger lead down the grip's rear channel and plug it back onto the cell bus | Path, Seat (keyed) | lead slides, connector click | upside down will not seat |
| s6.pin | Tap the housing pin back in | Window (two taps) | pin seats flush | proud pin blocks the screws |
| s6.screws | Two new grip screws from Brann's jar, to torque | Turn, Window | as s5.torque | as s5.torque |
| s6.cell | Open the vise, lay the pistol on the mat, cell in, latch home | Turn, Seat | latch snap, the pistol's status lamp goes amber then cyan | none |

### Stage 7: test (free, at least 0:45)

| id | Step | Archetype / tool | Feedback | Mistake and recovery |
|---|---|---|---|---|
| s7.inspect | Pick the pistol up and look it over | Seat (free turn, first-person hands) | the finished grip from every side | none |
| s7.shake | Shake it | Flick | no rattle, sway dies at once, one soft tick from the damper | none |
| s7.card_after | Three test pulses at a fresh card | Point | tight group; the card goes on the right clip beside the first and Brann answers from the counter | none; can be repeated |
| s7.leave | Holster and step back | Esc or the holster hook | Brann sends the player to the range | none |

Count: 67 step rows, about 95 separate actions (screws, leads, holes and plates repeat inside a row).
Total: about 17 minutes.

## 8. Knowing what to do next without a checklist

1. **The schematic** on the backboard is a drawn exploded view of the grip. The region for the current stage is lit
   by the clip lamp; finished regions carry Brann's chalk tick.
2. **The parts mat** has an outline for every part that comes off; an empty outline is a part still to remove, a part
   on its outline is done.
3. **Affordance light.** Objects that can be used now have a faint rim under the cursor or focus ring. Nothing else
   glows.
4. **Idle hints, in three steps.** 10 s with no progress: the next useful object glints once. 25 s: Brann says a
   short line. H or 45 s: a ghost of the part appears at its socket or the tool's path is drawn for two seconds.
   Hints never cost quality.
5. **One line** in the Field Notes corner names the stage ("Strip the pistol"), not the step.

## 9. Runtime model (Unity)

Ours, in `Scripts/Assembly/`; AnyMachine supplies the rigs and checks, not this logic.

- `AssemblyRecipe` (ScriptableObject): stages, steps, parts, sockets, fasteners, tools, quality rules, audio and bark
  ids. One recipe: `assembly_grip_stabilised_pistol`, attached to `recipe_grip_stabilised_pistol`.
- `AssemblyPart` (prefab component): item or sub-part id, sockets (`socket_*`), fastener points (`screw_*`), grab
  points, material class for contact sounds, mass class for the carry spring.
- `AssemblySocket`: pose, key symmetry (how many turns of 360 degrees seat), tolerance in mm and degrees, insertion
  axis and travel, what blocks it.
- `AssemblyFastener`: bit type, turns, torque window, damage state.
- `AssemblyParam`: plays an AnyMachine `*_param` clip at a 0-1 value (vise, latch, lever, jaws, lamp arm).
- `AssemblyTool`: tip transform, verbs it can do, carry pose.
- `IAssemblyVerb` with seven implementations (section 6); each reads input through `AssemblyInput` (mouse and
  keyboard forms) and reports progress, faults and a precision score.
- `AssemblyJob`: the state of one job (completed steps, part states, faults, scores, elapsed time). Pure C#,
  serialisable, tested in Edit Mode without a scene.
- `AssemblySession` (MonoBehaviour): owns the bench camera, focus, hints, audio events, Brann's barks and the hand-off
  to `CraftingModel` when the job completes.

### Session states

```
Closed -> Entering -> Working -> Leaving -> Closed
                      Working <-> Paused (settings, pause menu)
                      Working  -> Completing -> Leaving
Working sub-state:  Idle -> Hover -> Carry(part) -> Seating -> Idle
                    Idle -> Hover -> ToolInHand(tool) -> Engaged(verb) -> ToolInHand
                    Engaged -> Fault(kind) -> Recovering -> ToolInHand
                    any -> CameraMove(stage shot) -> previous
```

- `Closed -> Entering`: interact with the bench in Fabricate stage with the inputs, the toolkit and an unfinished or
  no job. Inputs and the pistol are moved to the bench (reserved, not consumed). Camera blends in.
- `Working`: steps become available by their prerequisites. Completing the last required step of a stage plays the
  stage shot and lights the next schematic region.
- `Fault`: a verb reports a fault kind (cam-out, stripped, short lead, cold joint, over-bend, flew off). The step
  records it and makes its recovery step available. Faults never end the job.
- `Leaving` with the job unfinished: the job is saved (`benchJob` in the save, additive), the pistol stays on the
  bench, the player gets control back.
- `Completing`: quality is computed, `CraftingModel` consumes the reserved inputs and grants the grip with its
  quality and the Copper Filament, fits it to the pistol, grants XP and skill use, returns the pistol to the loadout,
  sets Auto-assemble for this recipe, and the order moves to TestFire.
- Abandon (held at the bench, confirmed by Brann's line, not a dialog): reserved inputs and the pistol go back to the
  pack as they were when the job started, except parts already cut or fused, which are lost.

### Step states

`Locked -> Available -> Active -> Done`, with `Active -> Faulted -> Available(recovery)`. A step in `Active` when the
player leaves goes back to `Available`. Stage completion = all required steps `Done`.

### Quality

Each step yields a precision score 0 to 1 and a fault count. Job score = weighted mean of precision minus fault
penalties; Rough under 0.55, Standard to 0.85, Fine above. Time taken does not lower quality (mistakes already cost
time). Grip effect by quality is in data (start: recoil -5 / -7 / -10; sway and recovery scale likewise, section 10).

## 10. Before and after, in the world

The fitted grip today only lowers one number (recoil 38 to 31). To be felt it has to change what the hands and eyes
get. All of it is data on the weapon and mod, read by the existing combat and view-model code:

| What | Bare scrap pistol | With the grip (Standard) |
|---|---|---|
| Idle aim sway | wide, slow figure of eight plus a small tremor | under half the amplitude, no tremor |
| Kick per shot | sharp muzzle climb with a random sideways step | lower climb, almost no sideways step |
| Recovery | slow, overshoots once | fast, critically damped |
| Scatter while firing fast | grows quickly | grows slowly |
| Sound | a rattle on draw, movement and every shot | no rattle; one soft damper tick as it settles after a shot |
| Look | leather strips and tape, wire-bound, over cracked scales on a cracked tang | plated alloy grip with brass screws and an orange Warden strap |

The range tutorial is done with the bare pistol, so its plates must stay hittable: the bare pistol's first aimed shot
stays as accurate as today, and the roughness is in sway, recovery and rapid fire.

## 11. Audio events

Ids are `asm.<group>.<name>`; the audio agent delivers a clip set per id and the table that maps contact pairs
(material x material) and verbs to them. Groups: `seat` (by material pair), `screw` (turn loop by resistance, cam-out,
strip, seat, drop in dish), `vise`, `cut`, `peel`, `tap`, `brush`, `solvent`, `oil`, `spin` (grind, true, brake), `servo` (twitch and whirr
under the tester), `damper` (tick, settle), `strip`, `solder` (hiss, flow, scorch), `tester` (lamp, buzzer), `scribe`, `shear`, `file`,
`punch`, `drill`, `bend`, `press` (lever, pump, hiss, knit loop, vent), `quench`, `seam`, `cure`, `latch`, `cell`,
`pulse` (test shot before and after), `card`, `rattle`, `ui` (hint glint, stage done, job done), `amb` (bench bed:
shop hum, lamp tick, distant street).

Voice: Brann at stage starts, first fault of each kind, the stuck screw, the cracked tang, the spin test, the press,
the damper test, the two cards and the hand-over; Ossa at the range for the test fire (before the first shot, after
the group, on completion). Lines and ids are in `audio/lines.json` once written.

## 12. Budgets

- Bench set in view: under 250k triangles and under 120 colour draws added in the bench camera; one 2048 texture set
  per object family (pistol, servo, grip, tools, fixtures), 4096 only where the close view needs it.
  (20 Nov 21:45: 4096 is granted for the pistol, the hand tools and roll, and the work surface and mats; integration
  reports the resident texture memory, about 320 MB expected against the 169 MB measured at 2048.)
- No new real-time lights beyond one bench lamp and the cure lamp, both on the interior layer and inside the light
  budget (`LightBudget` counts them).
- Frame time in the bench camera no worse than the shop's present walk-in view; measured once per batch.

## 13. What is deliberately not in this round

Hands on tools by IK; other recipes (barrel, cell, armour, overhaul); benches elsewhere; multiplayer; controller
input; condition of the salvage changing the job.

### Later (Carl, 21 November 2026)

Carl: "maybe we need different vendors with different benchs, brann for weapons and another for armour?" Proposed for the
later round of hands-on crafting ("we can work on the advanced crafting of those parts later"): Brann's metal bench at
Salvage keeps weapons and weapon mods; Tamsin at Field Supply gets a soft-goods bench (sewing and riveting table: awl,
hide mallet, rivet setter, punch, plate shears) for armour and packs, with its own step tables, shots and her own guided
first job, built on the same bench system. Each bench has its own physical layout, fixtures and camera shots (Carl: "the bench layouts will be different"); only the interaction system is shared. Not started; the timed Craft stays for those recipes until then.
