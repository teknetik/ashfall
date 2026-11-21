#!/usr/bin/env python3
"""Writes events.json: the Steady Hands bench audio event table (audio agent, 20 Nov 2026).

Each event: id asm.<group>.<name>, what the player must learn from it, kind (oneshot/loop), source (el = ElevenLabs
eleven_text_to_sound_v2, one paid take per prompt; syn = numpy synthesis in gen_sfx.py), request seconds, loudness
target (event LUFS for one-shots, integrated LUFS for loops), peak cap, pitch range the runtime may use, and one prompt
per variant. Edit here, re-run, then gen_sfx.py. Cached takes are keyed by their exact request: a changed prompt is a
new paid take under a new name (gen_sfx refuses to reuse a mismatched cache)."""
import json
from pathlib import Path

D = 'Close-miked workbench foley, one single event only, dry, no room echo, no music, no voices.'
L = 'Continuous and steady with no start and no ending, close-miked workbench foley, dry, no music, no voices.'
E = []


SHIFT = -4   # balance pass: every bench effect 4 dB under its first target so the loudest real sets stay under -1.5 dBFS


def ev(id, learn, kind, src, sec, lufs, prompts=None, peak=-6, pitch=(0.92, 1.08), note='', synth=None, variants=None):
    prompts = prompts or []
    if id != 'asm.amb.bed': lufs, peak = lufs + SHIFT, peak + SHIFT
    E.append({'id': id, 'learn': learn, 'kind': kind, 'source': src, 'request_seconds': sec, 'variants': variants or len(prompts),
              'lufs': lufs, 'peak_cap_dbfs': peak, 'pitch_range': list(pitch), 'note': note,
              **({'prompts': [p + ' ' + (L if kind == 'loop' else D) for p in prompts]} if prompts else {}),
              **({'synth': synth} if synth else {})})


O, LP = 'oneshot', 'loop'
LOOP_PITCH = (0.8, 1.3)
# ---------------------------------------------------------------- seat: contact matrix (part material x surface)
ev('asm.seat.steel_rubber', 'a steel part (pistol, frame, tool) has landed on the rubber work mat', O, 'el', .5, -26, [
    'A small steel pistol frame set down on a thick rubber workbench mat: one soft dull thud with a faint metal tick.',
    'A steel hand tool laid down on a rubber mat: muted low knock with a tiny metallic edge.',
    'A heavy steel part placed on a rubber bench mat: one deadened thump, a short faint ring.',
    'A steel screwdriver set down on rubber matting: soft compact thud and a light clink of the shaft.'])
ev('asm.seat.alloy_rubber', 'a light alloy part (servo case, sheet, plate) has landed on the mat', O, 'el', .5, -27, [
    'A light aluminium servo casing set down on a rubber mat: one hollow soft knock.',
    'A thin aluminium sheet laid flat on a rubber workbench mat: soft flat slap with a faint tinny ring.',
    'A small alloy plate placed on rubber: light hollow tap, short.'])
ev('asm.seat.wood_rubber', 'a wooden grip scale has been set down on the parts mat', O, 'el', .5, -28, [
    'A small dry wooden pistol grip panel laid on a rubber mat: one soft woody tick.',
    'A thin piece of old dry wood set down on rubber: muted light knock.',
    'A worn wooden grip scale placed on a bench mat: short soft dry tap.'])
ev('asm.seat.wood_steel', 'a wooden scale has lifted off or come against the steel frame', O, 'el', .5, -27, [
    'A dry wooden pistol grip scale lifted off a steel frame: a small woody click and a short scrape on metal.',
    'Old dry wood knocking against a steel pistol frame: one light hollow woody clack.',
    'A wooden grip panel sliding off a metal frame: brief dry scrape ending in a tick.'])
ev('asm.seat.steel_steel', 'a steel part has gone home on a steel fixture (cradle, press bed, pocket)', O, 'el', .5, -25, [
    'A steel part seating into a steel cradle: one solid metal clunk, tight and short.',
    'A steel mould dropping into a keyed steel press bed: heavy precise metal clack.',
    'A machined steel ring pressed into a fitted steel pocket: one firm dense clunk with a short ring.',
    'Two machined steel parts seating together: crisp heavy metal click-clunk.'])
ev('asm.seat.alloy_alloy', 'a side plate has dropped onto its pegs on the grip core', O, 'el', .5, -27, [
    'An aluminium plate pressed down onto two small metal pegs: a light double tick and a soft seat.',
    'A thin alloy grip plate seating onto locating pins: one crisp light metal click.',
    'A metal side plate pushed onto its pegs: short tight tick with a faint tinny note.'])
ev('asm.seat.plastic_rubber', 'a plastic part (board, cell) has been set down', O, 'el', .5, -29, [
    'A small plastic circuit board set down on a rubber mat: one light hollow plastic tick.',
    'A plastic battery cell placed on a rubber pad: dull light plastic knock.',
    'A small plastic housing laid on a bench mat: soft short plastic tap.'])
ev('asm.seat.glass_rubber', 'a glass vial or jar has been set down', O, 'el', .5, -28, [
    'A small glass vial set down on a rubber mat: one soft glassy tick.',
    'A small glass jar of liquid placed on a bench mat: light glassy tock and a tiny slosh, no low thud.',
    'A glass vial stood upright on rubber: light clear tap, very short.'])
ev('asm.seat.copper_rubber', 'a copper part (bobbin, lead, coil) has been set down', O, 'el', .5, -30, [
    'A small spool of copper wire set down on a rubber mat: soft light metallic tap.',
    'A coil of thin copper wire laid down on rubber: quiet springy soft tick.',
    'Two short copper wire leads dropped on a bench mat: faint light metal patter.'])
ev('asm.seat.canvas_rubber', 'the canvas tool roll has been put down', O, 'el', .8, -27, [
    'A rolled canvas tool roll set down on a workbench: soft cloth pat and a light muffled clink of steel tools inside, no heavy thump.',
    'A heavy canvas tool wrap laid on a bench: dull fabric flop and tools knocking inside.'])
ev('asm.seat.tiny_steel', 'a tiny steel part (pin, circlip, ring, resistor) has been set down', O, 'el', .5, -31, [
    'A tiny steel pin set down on a hard bench: one very small bright tick.',
    'A small steel spring clip placed on metal: tiny light clink.',
    'A tiny metal part dropped a few millimetres onto a bench: single delicate tick.'])
ev('asm.seat.blocked', 'the part will not seat: something blocks it (wrong way round, wrong order)', O, 'el', .5, -25, [
    'A metal part pushed against another that will not let it in: a quick double knock and a short rattling shudder.',
    'A steel part jammed against a blocking part: stubborn metal clack-clack and a brief buzzy rattle.',
    'Forcing a misaligned metal part into place: hard short knock and jittering rattle, it does not go in.'])
ev('asm.seat.spring_click', 'a spring catch has snapped home (strap over the spine, lead into its clip)', O, 'el', .5, -27, [
    'A small spring steel clip snapping into place: one crisp bright click.',
    'A metal strap clicking over a spine: sharp springy snap, very short.',
    'A plastic wire clip snapping shut on a cable: one tight snappy click.'])
ev('asm.seat.dovetail', 'the grip has slid fully onto the pistol tang', O, 'el', .8, -24, [
    'A heavy metal grip block sliding onto a steel dovetail rail and stopping: short scrape into one solid heavy clunk.',
    'A machined metal part pushed along a steel rail until it seats: brief metal slide and a deep solid clunk.'])
ev('asm.seat.slide', 'a part is sliding along a rail against spring pressure', O, 'el', .8, -27, [
    'A steel pistol backstrap housing sliding off its rail: a short gritty metal scrape with a spring creak.',
    'A metal cover sliding along a steel rail: smooth short scrape with a faint spring tension.'])
# ---------------------------------------------------------------- screw
ev('asm.screw.turn', 'the screw is turning; pitch follows resistance (loose low, tight high)', LP, 'el', 3, -30, [
    'A small steel screw turned continuously by a screwdriver in a threaded hole: uninterrupted fine gritty metallic thread creak, even and steady.',
    'A screwdriver slowly turning a tight machine screw: continuous fine metallic thread grind with soft clicks.'],
    peak=-10, pitch=LOOP_PITCH, note='2 variants: pick one per screw; set pitch from resistance')
ev('asm.screw.start', 'the first threads have caught', O, 'el', .5, -31, [
    'A small machine screw catching its first thread: one tiny metal tick and a soft click.',
    'A screw tip finding the thread in a hole: faint metallic click, very short.',
    'The first turn of a screw biting into a thread: small dry tick.'])
ev('asm.screw.seat', 'the screw head has seated at torque (inside the window)', O, 'el', .5, -27, [
    'A machine screw tightening the last bit and seating firmly: one tight crisp metal click.',
    'A screw head bottoming out snugly against a metal plate: short firm click-tick.',
    'Final torque on a small screw: a tight creak ending in a solid tick.'])
ev('asm.screw.camout', 'BAD: the bit has slipped out of the head (wrong bit or too much force)', O, 'el', .5, -22, [
    'A screwdriver bit slipping violently out of a screw head: sharp harsh metal skitter and scrape.',
    'A screwdriver camming out of a seized screw: a sudden ugly metallic bark and grinding slip.',
    'Steel screwdriver tip skidding off a screw slot: short loud scraping squeal of metal on metal.'])
ev('asm.screw.strip', 'BAD: the head or thread has stripped (over-torque)', O, 'el', .8, -23, [
    'A screw thread stripping under too much force: a crunchy metallic grind and then a loose free spinning rattle.',
    'Over-tightening a small screw until it strips: sharp crack of metal giving way into a gritty empty turn.'])
ev('asm.screw.crack_free', 'the seized screw has broken free after oil and taps', O, 'el', .5, -24, [
    'A rusted seized screw suddenly cracking loose under a screwdriver: one sharp metallic pop-creak.',
    'A stuck screw breaking free: short sharp crack of corrosion giving way.'])
ev('asm.screw.crossthread', 'BAD: the screw went in crooked and binds', O, 'el', .8, -24, [
    'A screw cross-threading in a hole: harsh gritty grinding bind and a squeak, it jams.',
    'A crooked machine screw forced into a thread: rough crunching metal grind that stops hard.'])
ev('asm.screw.pliers', 'pliers biting a chewed screw head and turning it', O, 'el', .8, -26, [
    'Pliers gripping a damaged screw head and twisting it: a grinding serrated bite and slow metal creak.',
    'Gripping a stripped screw with pliers and turning it out: gritty jaw scrape and a slow squeaking turn.'])
ev('asm.screw.dish', 'a screw or small part has dropped into the steel parts dish', O, 'el', .5, -27, [
    'A small steel screw dropped into a shallow steel parts dish: one bright clink and a short rattle.',
    'A tiny screw falling into a metal magnetic tray: crisp single clink that stops quickly.',
    'A small screw landing in a steel dish: light ringing tink and a little roll.',
    'A screw dropped into a metal bowl: short bright metallic clink.'])
# ---------------------------------------------------------------- vise
ev('asm.vise.thread', 'the vise screw is turning; pitch follows load (open low, closing high)', LP, 'el', 3, -29, [
    'A heavy bench vise handle being turned: steady deep metallic thread grind with a slow rhythmic creak.'],
    peak=-10, pitch=LOOP_PITCH)
ev('asm.vise.bite', 'the vise jaws have closed snug on the part', O, 'el', .5, -25, [
    'Bench vise jaws closing on a metal part with soft pads: one firm dull clamp thunk.',
    'A vise tightening onto a part: short solid squeeze and a muted metal knock.',
    'Steel vise jaws gripping through rubber pads: dense short clunk.'])
ev('asm.vise.creak', 'BAD (over-tight) or press-fit load: metal under strain', O, 'el', .8, -25, [
    'A bench vise overtightened on a part: one single strained metallic creak.',
    'Metal under heavy pressure in a vise: slow stressed creaking squeal.'])
ev('asm.vise.stop', 'the press fit has gone home: a dead stop', O, 'el', .5, -24, [
    'A part pressed home in a vise hitting its stop: one dead solid thunk, no ring.',
    'A metal fitting pressed fully in: short heavy dull stop.'])
ev('asm.vise.release', 'the vise has let go of the part', O, 'el', .5, -27, [
    'A bench vise loosened and the part dropping free in the jaws: soft metal clunk.',
    'Vise jaws opening and releasing a part: short loose knock.'])
# ---------------------------------------------------------------- cut, peel
ev('asm.cut.snip', 'the cutters have gone through a wire or lead', O, 'el', .5, -26, [
    'Wire cutters snipping through a thin copper wire: one crisp sharp snip.',
    'Side cutters cutting a small insulated electrical lead: short tight crunchy snip.',
    'Flush cutters cutting a resistor leg: tiny bright snap-snip.',
    'Snipping a twisted steel binding wire with cutters: one hard sharp clip.'])
ev('asm.cut.spring', 'a cut wire twist has sprung open', O, 'el', .5, -29, [
    'A cut binding wire springing loose: a quick light metallic twang and flick.',
    'A twisted wire uncoiling after being cut: short springy zing.'])
ev('asm.peel.tape', 'tape is peeling cleanly; keep the pace', LP, 'el', 2.5, -29, [
    'Cloth tape being peeled slowly and steadily off a metal handle: one long continuous uninterrupted sticky ripping sound, even in level.'], peak=-10, pitch=(0.85, 1.2))
ev('asm.peel.tear', 'BAD: the tape has torn', O, 'el', .5, -26, [
    'A strip of old tape tearing across: one short sudden rip.',
    'Brittle tape snapping and tearing mid peel: quick ragged rip.'])
ev('asm.peel.leather', 'the dry leather wrap is coming away', LP, 'el', 2.5, -29, [
    'Dry old leather wrap being slowly unwound and pulled off a handle: continuous soft creaking leather and faint stickiness.'], peak=-10, pitch=(0.85, 1.2))
# ---------------------------------------------------------------- tap, punch
ev('asm.tap.strike', 'the mallet has struck the pin punch (each tap counts)', O, 'el', .5, -24, [
    'A small mallet striking a steel pin punch: one sharp ringing metal tap.',
    'A hammer tapping a steel drift punch against a pin: bright short ping.',
    'A mallet hitting a steel punch: crisp metallic tock with a short ring.',
    'Tapping a steel pin out with a small punch and hammer: one bright high metallic tink, no low thud.'])
ev('asm.tap.miss', 'BAD: the mallet glanced and hit the frame', O, 'el', .5, -23, [
    'A hammer glancing off a punch and hitting a steel frame: ugly dull clank and a scrape.',
    'A missed hammer blow on metal: flat harsh knock, no ring.'])
ev('asm.tap.pin_out', 'the pin is walking out / being pulled', O, 'el', .8, -28, [
    'A small steel roll pin sliding out of a hole: short gritty metal scrape.',
    'Pulling a tight pin out with pliers: brief squeaky metal slide ending in a tick.'])
ev('asm.tap.pin_flush', 'the pin has seated flush', O, 'el', .5, -25, [
    'A pin tapped fully home flush with a frame: one dead solid metal tap.',
    'The last hammer tap seating a pin: short dull solid tock.'])
ev('asm.punch.dimple', 'the centre punch has marked the plate', O, 'el', .5, -25, [
    'A centre punch struck once into aluminium plate: one sharp small metallic tick-thud.',
    'A hammer hitting a centre punch on sheet metal: short crisp dink.',
    'A spring-loaded centre punch snapping into metal: one bright snap.'])
# ---------------------------------------------------------------- brush, solvent, oil
ev('asm.brush.wire', 'the wire brush is scrubbing metal clean', LP, 'el', 3, -29, [
    'A small steel wire brush scrubbing back and forth on a metal ring: continuous bristly scratching.'], peak=-10, pitch=(0.85, 1.25))
ev('asm.brush.dust', 'brushing caked dust and grime off a casing', LP, 'el', 3, -31, [
    'A stiff brush sweeping caked dust off a plastic and metal casing: continuous soft gritty brushing.'], peak=-10, pitch=(0.85, 1.25))
ev('asm.solvent.swirl', 'the part is swirling in solvent; grime clouding off', LP, 'el', 3, -30, [
    'A small metal part swirled around in a glass jar of solvent: continuous gentle liquid sloshing.'], peak=-10, pitch=(0.85, 1.2))
ev('asm.solvent.dip', 'the part has gone into the solvent jar', O, 'el', .8, -28, [
    'A small metal part lowered into a glass jar of liquid: soft plop and a faint clink on glass.',
    'Dipping a metal ring into solvent in a jar: gentle liquid plunk.'])
ev('asm.solvent.lift', 'the part has come out of the solvent, dripping', O, 'el', .8, -29, [
    'A metal part lifted out of a jar of liquid: small splash and a few drips.',
    'Pulling a part out of solvent: wet trickle and drips falling back into the jar.'])
ev('asm.oil.drop', 'one drop of oil has landed', O, 'el', .5, -32, [
    'One single drop of oil squeezed from a dropper onto metal: tiny soft wet tick.',
    'A single oil drop landing on a small bearing: very faint wet plip.',
    'A squeeze of an oil dropper and one drop falling: tiny soft drip.'])
ev('asm.oil.wipe', 'excess oil wiped off with a rag', O, 'el', .8, -29, [
    'One single quick wipe of a cloth rag across a small oily metal part: soft short swipe.',
    'A rag rubbing a metal part clean: short soft fabric swipe.'])
# ---------------------------------------------------------------- spin, servo, damper, wind
ev('asm.spin.true', 'GOOD: the bearing is clean and true (long smooth whirr)', LP, 'el', 3, -28, [
    'A freshly cleaned and oiled metal bearing ring spinning freely: smooth steady high whirr, clean and even.'],
    peak=-10, pitch=LOOP_PITCH, note='fade out over the spin-down; pair with asm.spin.grind')
ev('asm.spin.grind', 'BAD: grit in the bearing (gritty grinding spin)', LP, 'el', 3, -27, [
    'A dirty gritty metal bearing spinning roughly: continuous crunchy grinding rumble with scraping grit.'],
    peak=-10, pitch=LOOP_PITCH, note='pair with asm.spin.true; must never be mistaken for it')
ev('asm.spin.brake', 'the rotor brakes within a turn (damper coil closed)', O, 'el', .8, -28, [
    'A small spinning metal rotor braking hard to a stop within a turn: short whirr that drops and stops with a soft click.',
    'A spinning gimbal rotor slowing abruptly to a halt: quick descending whirr into a soft stop.'])
ev('asm.servo.twitch', 'the servo rotor kicks when the tester drives the coil', O, 'el', .5, -28, [
    'A small electric servo motor twitching once: quick tiny motor buzz and a mechanical tick.',
    'A small coil motor kicking: short electric zip and a click.'])
ev('asm.servo.whirr', 'the rotor is spinning under the tester (coil driven)', LP, 'el', 3, -29, [
    'A small electric servo motor spinning steadily: smooth electric whirr with a faint hum.'], peak=-10, pitch=LOOP_PITCH)
ev('asm.wind.crank', 'copper wire winding onto the bobbin; pitch follows crank speed (too fast snaps)', LP, 'el', 3, -30, [
    'Fine copper wire being wound onto a spool by a hand crank: continuous thin singing wire hiss with a soft ratchet ticking.'],
    peak=-10, pitch=LOOP_PITCH)
ev('asm.wind.snap', 'BAD: the copper wire snapped (wound too fast)', O, 'el', .5, -25, [
    'A thin taut copper wire snapping: one sharp high twang and a whip.'])
ev('asm.damper.tick', 'GOOD: the damper caught the swing (one soft tick)', O, 'syn', 0, -27, variants=4,
   synth={'recipe': 'damper_tick'}, note='synthesised: padded mass hitting a damped stop')
ev('asm.damper.settle', 'the mass swings once and settles (with the tick on top)', O, 'syn', 0, -31, variants=2,
   synth={'recipe': 'damper_settle'})
# ---------------------------------------------------------------- strip, solder, tester
ev('asm.strip.squeeze', 'the strippers have bitten the insulation', O, 'el', .5, -29, [
    'Wire strippers closing on an insulated wire: one small crisp crunch.',
    'Stripping pliers biting into wire insulation: short tight squeeze click.'])
ev('asm.strip.pull', 'the insulation has slid off', O, 'el', .5, -29, [
    'Insulation sliding off the end of a copper wire: short soft plastic slide.',
    'Pulling the cut insulation off a wire: quick light rubbery zip.',
    'Wire insulation slipping off copper strands: tiny soft scrape.'])
ev('asm.strip.twist', 'the bare strands are being twisted', O, 'el', .8, -31, [
    'Twisting fine copper wire strands between fingers: faint crinkly metallic rustle.',
    'Fine stranded wire twisted tight: soft delicate wiry crackle.'])
ev('asm.solder.hiss', 'the iron is on the work; flux is heating', LP, 'el', 3, -30, [
    'A hot soldering iron tip touching rosin flux on a wire: continuous soft sizzling crackle.'], peak=-10, pitch=(0.9, 1.15))
ev('asm.solder.flow', 'GOOD: the solder has melted and flowed', O, 'el', .8, -26, [
    'Solder melting and flowing onto a hot wire joint: a bright sizzle burst and crackle that settles.',
    'A soldering iron flowing solder into a joint: quick crisp fizz and a soft crackle.',
    'Molten solder wetting a copper wire: short lively sizzle.'])
ev('asm.solder.cold', 'BAD: a cold joint (the iron drags, nothing flows)', O, 'el', .5, -28, [
    'A cool soldering iron dragging on a dull lump of solder: dry faint scratch, no sizzle.',
    'A soldering iron tip scraping a cold solder joint: dull short gritty scrape.'])
ev('asm.solder.scorch', 'BAD: too hot, the insulation is scorching', O, 'el', .8, -25, [
    'Plastic wire insulation scorching under a soldering iron: harsh crackling burn and a small pop.',
    'Wire insulation melting from too much heat: sputtering crackle and hiss.'])
ev('asm.solder.shrink', 'the heat-shrink sleeve has tightened', O, 'el', .8, -31, [
    'Heat shrink tubing tightening around a wire: soft faint crinkle and tick.',
    'A small plastic sleeve shrinking under heat: quiet crinkly squeeze.'])
ev('asm.tester.probe', 'a probe has touched a contact', O, 'syn', 0, -30, variants=3, synth={'recipe': 'probe'})
ev('asm.tester.lamp', 'GOOD: circuit closed, the tester lamp relay clicked on', O, 'syn', 0, -25, variants=2, synth={'recipe': 'lamp'},
   note='pair with asm.tester.buzzer')
ev('asm.tester.buzzer', 'BAD: open circuit, the tester buzzes', O, 'syn', 0, -24, variants=2, synth={'recipe': 'buzzer'})
# ---------------------------------------------------------------- scribe, shear, file, drill, bend
ev('asm.scribe.scratch', 'the scribe is cutting a line in the alloy; keep it steady', LP, 'el', 2.5, -31, [
    'A sharp steel scriber dragged steadily across aluminium sheet: continuous thin high scratching line.'], peak=-10, pitch=(0.85, 1.2))
ev('asm.shear.bite', 'the snips have taken one bite along the line', O, 'el', .5, -26, [
    'Tin snips biting through thin aluminium sheet: one crunchy metallic shear.',
    'Aviation snips cutting sheet metal: short sharp chomp with a scrape.',
    'Hand shears cutting a bite of thin metal plate: crisp crunch.',
    'Metal snips closing through sheet: one tight shearing clip.'])
ev('asm.shear.offcut', 'an offcut has dropped (it is kept)', O, 'el', .5, -28, [
    'A small aluminium offcut dropping onto a rubber bench mat: light tinny tap.',
    'A thin metal scrap falling a short way onto a bench: small clattering tick.'])
ev('asm.file.stroke', 'one file stroke has taken metal off', O, 'el', .5, -27, [
    'One push stroke of a flat metal file across an aluminium edge: short rasping scrape.',
    'A single stroke of a bastard file on metal: one coarse gritty rasp.',
    'Filing a metal edge once: crisp short raspy swipe.',
    'One file stroke on alloy plate: brief bright rasp.'])
ev('asm.file.round', 'one stroke of the round file in the pocket', O, 'el', .5, -28, [
    'One stroke of a small round file inside a metal hole: short hollow rasp.',
    'A rat-tail file pushed through a bore: brief gritty swish.'])
ev('asm.drill.turn', 'the hand drill is cutting; pitch follows speed, rough when pushed too hard', LP, 'el', 3, -28, [
    'An old geared hand drill cranked steadily, the bit cutting into aluminium: continuous gear whirr and fine metal cutting.'],
    peak=-10, pitch=LOOP_PITCH)
ev('asm.drill.bind', 'BAD: the bit has bound (pushing too hard)', O, 'el', .5, -24, [
    'A drill bit binding and jamming in metal: sudden harsh grinding stall and creak.',
    'A hand drill bit catching in a hole: abrupt crunching jam.'])
ev('asm.drill.through', 'the bit has broken through the plates', O, 'el', .5, -27, [
    'A drill bit breaking through thin metal: quick release crunch and a tinkle of metal swarf.',
    'A hand drill punching through the last of an aluminium plate: brief sharp grind dropping away.'])
ev('asm.bend.yield', 'the strip is bending in the vise (yielding metal)', LP, 'el', 2.5, -29, [
    'A flat aluminium strip being slowly bent by hand in a vise: continuous low metal creak and strain.'], peak=-10, pitch=(0.85, 1.2))
ev('asm.bend.crack', 'BAD: the strip has cracked (bent back too often)', O, 'el', .5, -23, [
    'A metal strip cracking after being bent too far: one sharp brittle metallic crack.'])
# ---------------------------------------------------------------- press, quench, seam, cure
ev('asm.press.lever', 'the press lid has closed and locked', O, 'el', .8, -24, [
    'A heavy steel press lever pulled down and locking: deep mechanical clunk and latch.',
    'Closing a heavy machine press lid and locking it: solid heavy metal clack.'])
ev('asm.press.pump', 'one pump stroke has raised the pressure', O, 'el', .5, -27, [
    'One stroke of a small hydraulic hand pump: short squishy mechanical push with a faint hiss.',
    'A hydraulic pump handle pushed once: compact pneumatic chuff and click.',
    'One pump of a hand-operated press: brief hydraulic squelch.'])
ev('asm.press.hiss', 'the press is under pressure', LP, 'el', 3, -31, [
    'A small hydraulic press holding pressure: continuous steady soft pneumatic hiss.'], peak=-12, pitch=(0.9, 1.15))
ev('asm.press.knit', 'the nanites are knitting; pitch follows pressure (in band = steady tone)', LP, 'el', 3, -27, [
    'Microscopic machines knitting metal together inside a pressure chamber: continuous fine granular crackling fizz with a steady soft electronic tone.'],
    peak=-10, pitch=LOOP_PITCH, note='layer with asm.press.hiss; pitch rises with pressure into the band, steady inside it')
ev('asm.press.pour', 'nanite fluid pouring into the mould (stop at the line)', LP, 'el', 3, -30, [
    'A thick grey metallic fluid pouring slowly from a vial into a small mould: continuous viscous trickle with faint crawling fizz.'],
    peak=-10, pitch=(0.9, 1.15))
ev('asm.press.vent', 'the press has vented', O, 'el', 1.0, -24, [
    'A small pressure chamber venting: sharp burst of hissing air that tails off quickly.',
    'Releasing pressure from a hydraulic press: short loud pneumatic hiss burst.'])
ev('asm.quench.sizzle', 'the hot core has gone into the quench', O, 'el', 1.2, -24, [
    'A hot metal part plunged into water: violent sizzle and steam hiss that fades.',
    'Quenching hot steel in a small water bath: sharp bubbling sizzle dying away.'])
ev('asm.seam.trace', 'the applicator is laying the nanite seam; keep it moving', LP, 'el', 3, -31, [
    'A fine nozzle applicator laying down a thin bead of paste along a seam: continuous faint fine hiss with tiny crackles.'],
    peak=-12, pitch=(0.9, 1.15))
ev('asm.cure.hum', 'the cure lamp is on (seam curing)', LP, 'syn', 0, -32, variants=1, synth={'recipe': 'cure_hum'}, peak=-14, pitch=(0.95, 1.05))
ev('asm.cure.switch', 'the cure lamp has switched on or off', O, 'syn', 0, -28, variants=2, synth={'recipe': 'switch'})
ev('asm.cure.arm', 'the lamp arm is swinging over', O, 'el', .8, -29, [
    'A spring-balanced metal lamp arm swung across a bench: short creaky spring stretch and joint squeak.'])
# ---------------------------------------------------------------- latch, cell, pulse, card, rattle
ev('asm.latch.snap', 'the cell latch has snapped open or home', O, 'el', .5, -26, [
    'A small spring latch on a pistol snapping open: one crisp metallic snap.',
    'A battery latch clicking shut: sharp tight snap.',
    'A thumb latch springing: quick bright click-clack.'])
ev('asm.latch.stuck', 'BAD: the cell will not come out while the latch holds it', O, 'el', .5, -27, [
    'Tugging a battery that is latched in: short stubborn rattle and knock, it does not move.',
    'Pulling at a locked latch: quick blocked clack.'])
ev('asm.cell.pop', 'the charge cell has left or entered its contacts', O, 'el', .5, -27, [
    'A small battery cell popping out of spring contacts: short springy pop and click.',
    'A power cell pushed into its contacts: tight snap with a faint electrical tick.'])
ev('asm.cell.power_down', 'the pistol status lamp has died (cell out)', O, 'syn', 0, -30, variants=1, synth={'recipe': 'power_down'})
ev('asm.cell.power_up', 'the pistol has power again (amber, then cyan)', O, 'syn', 0, -27, variants=1, synth={'recipe': 'power_up'})
ev('asm.pulse.shot', 'a low-power test pulse (clearly weaker than a real shot)', O, 'el', .5, -27, [
    'A tiny low power electric test pulse from a pistol: small soft electric snap and a thin zip, weak and quiet, not a gunshot.',
    'A training pistol firing a weak test discharge: light electric pop with a short fizz, small and thin.',
    'A low-power energy pistol test shot: a thin high electric click-zap, very short, no bang, no bass, no boom.'],
    peak=-8, note='checked against Combat/Pistol body layers: must be at least 6 dB quieter in event loudness')
ev('asm.pulse.hit', 'the pulse has holed the paper card', O, 'el', .5, -29, [
    'A small hole punched through a stiff paper card by a fast pellet: one sharp paper pop.',
    'A paper target card hit by a small projectile: crisp papery tick.',
    'A stiff card on a board pierced by a tiny shot: short dry paper snap.'])
ev('asm.card.clip', 'the card has been clipped to the board', O, 'el', .5, -29, [
    'A stiff paper card slid under a spring metal clip on a board: soft paper slide and a clip snap.',
    'Clipping a paper card to a board: light papery rustle and small click.'])
ev('asm.rattle.shake', 'BAD (before): the bare pistol rattles loose', O, 'el', .8, -25, [
    'Shaking a loose worn pistol by hand: loose metal parts rattling and a wobbly grip clacking.',
    'A battered old handgun shaken: rattly loose clatter of a wobbly grip and loose pins.',
    'A pistol with a loose grip shaken once: short rattling clack of loose parts.'],
    note='pair with asm.damper.tick (after): one tick, no rattle')
# ---------------------------------------------------------------- pry, part, kit, wire (groups added, see README)
ev('asm.pry.creak', 'the case clip is under the pick (pry)', O, 'el', .8, -28, [
    'Prying a plastic casing open with a small pick: strained plastic creak.',
    'A pick levering a plastic case seam: short tense creak.'])
ev('asm.pry.release', 'a case clip has let go', O, 'el', .5, -27, [
    'A plastic case clip releasing: one sharp plastic snap.',
    'A snap-fit clip on a plastic housing popping open: crisp click.',
    'A casing clip unhooking: short plastic tick-snap.'])
ev('asm.pry.break', 'BAD (cosmetic): the clip snapped off', O, 'el', .5, -25, [
    'A small plastic clip breaking off: brittle crack with a tiny piece flicking away.'])
ev('asm.part.circlip', 'the circlip or retaining ring has sprung off/on', O, 'el', .5, -27, [
    'A small steel circlip springing off a shaft: quick bright metallic ping.',
    'A retaining ring snapping into its groove: sharp springy ting.'])
ev('asm.part.gear', 'a gear is lifting off its post', O, 'el', .5, -29, [
    'A small metal gear lifted off its shaft: short toothed scrape and click.',
    'Plastic gear pulled off a post, teeth catching: brief ratchety scrape.',
    'A small gear sliding off a spindle: light toothy rattle.'])
ev('asm.part.spring_jump', 'BAD: the spring has jumped out', O, 'el', .5, -25, [
    'A small compressed spring launching out of a mechanism: quick boing twang and a skittering tick as it lands.'])
ev('asm.part.connector', 'a connector or tab has unplugged or plugged in', O, 'el', .5, -28, [
    'A small electrical connector unplugged from a board: short plasticky pop.',
    'Plugging a wire connector onto a pin header: crisp tight click.',
    'A spade tab connector pulled off: quick snick.'])
ev('asm.part.bin', 'a scrapped part has gone into the scrap bin', O, 'el', .5, -27, [
    'A small broken circuit board dropped into a metal scrap bin: clattery tinny crash.',
    'A few small metal gears tossed into a steel bin: short jangling clatter.',
    'A piece of scrap dropped into a metal bucket: hollow clunk and rattle.'])
ev('asm.part.floor', 'a part has fallen to the floor', O, 'el', .5, -26, [
    'A small metal part falling onto a concrete floor: sharp clink and bounce.',
    'A small part dropping off a bench onto the floor: tick, bounce and roll.'])
ev('asm.kit.untie', 'the tool roll strap is coming undone', O, 'el', .8, -29, [
    'Untying a canvas strap on a tool roll: a buckle clink and fabric strap sliding.'])
ev('asm.kit.unroll', 'the tool roll is unrolling across the bench', O, 'el', 1.5, -26, [
    'A canvas tool roll unrolled across a workbench: fabric flap and a row of steel tools clinking in their pockets.'])
ev('asm.kit.tool', 'a tool has been taken from or put back in the roll', O, 'el', .5, -29, [
    'Pulling a steel screwdriver out of a canvas pocket: soft fabric slide and a small clink.',
    'Sliding pliers into a canvas tool roll pocket: short cloth whisk and metal tick.',
    'Taking a small file out of a fabric tool roll: quick rustle and tink.'])
ev('asm.wire.slide', 'a lead is sliding along its channel (route it at a steady pace)', LP, 'el', 2.5, -32, [
    'An insulated wire being pulled slowly through a narrow plastic channel: continuous soft rubbery slide.'], peak=-12, pitch=(0.85, 1.2))
# ---------------------------------------------------------------- ui, amb
ev('asm.ui.glint', 'idle hint: look here', O, 'syn', 0, -33, variants=2, synth={'recipe': 'glint'})
ev('asm.ui.stage', 'a stage is complete (the schematic gets its tick)', O, 'syn', 0, -28, variants=1, synth={'recipe': 'stage'})
ev('asm.ui.job', 'the job is complete', O, 'syn', 0, -25, variants=1, synth={'recipe': 'job'})
ev('asm.amb.bed', 'where you are: Brann\'s shop from the bench (quiet bed)', LP, 'el', 22, -38, [
    'Quiet interior room tone of a small salvage workshop: a faint distant air compressor humming on and off, low electrical hum of lamps, '
    'very distant muffled street outside with indistinct far voices and a cart, calm. Continuous ambience, no music, no close sounds, no speech.'],
    peak=-16, pitch=(1, 1), note='stereo; a synthesised lamp tick layer is added, periodic in the loop')
E[-1]['prompts'] = [E[-1]['prompts'][0].split(' ' + L)[0]]   # the bed keeps its own wording (no foley suffix)

out = {'pass': 'Steady Hands bench audio (20 Nov 2026)', 'model': 'eleven_text_to_sound_v2', 'prompt_influence': 0.55,
       'loudness': 'one-shots: event LUFS (four repeats, 0.5 s gaps, as the 19 Nov combat pass); loops: integrated LUFS of the mastered loop',
       'events': E}
Path(__file__).with_name('events.json').write_text(json.dumps(out, indent=1) + '\n')
el = [e for e in E if e['source'] == 'el']
print(len(E), 'events;', sum(e['variants'] for e in E), 'clips;', sum(e['variants'] for e in el), 'paid takes;',
      round(sum(e['variants'] * e['request_seconds'] for e in el), 1), 's requested;', len({e['id'].split('.')[1] for e in E}), 'groups')
