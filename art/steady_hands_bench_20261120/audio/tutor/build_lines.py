#!/usr/bin/env python3
"""Writes lines.json for Brann's guided first job (tutor agent, 21 Nov 2026). The table below is the source; edit it here
and re-run. Kinds: welcome (first entry), step (the step becomes the next useful thing), action (one repeat inside a
row), verb (first appearance of an input archetype), recovery (a recovery step becomes the next thing).
Steps listed in SILENT are deliberately not voiced by the tutor (the reason is given)."""
import json, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]

ROWS = [
    # kind, step or verb, action key, text
    ('welcome', '', '', "First one's by hand. I'll talk you through it."),
    # stage 0 (full)
    ('step', 's0.pistol', '', "Pistol first. Lay it on the black mat, flat."),
    ('step', 's0.roll', '', "Your tool roll. Undo the strap, then roll it out."),
    ('step', 's0.salvage', '', "Servo, both alloy sheets and the vial. Into the tray."),
    ('action', 's0.salvage', 'vial', "Vial's round. Set it down gentle or it rolls."),
    ('recovery', 's0.salvage.r', '', "It rolled. Pick it up and try again, slower."),
    ('step', 's0.card_before', '', "Pistol up. Three pulses at the card. See how it walks."),
    ('step', 's0.shake_before', '', "Give it a shake if you like. Hear that rattle."),
    ('step', 's0.cell', '', "Cell out before anything else. Thumb the latch, then pull."),
    # verbs (first appearance of each archetype; Point and Window have two forms)
    ('verb', 'seat', '', "Take it and carry it over. Square it up and it drops in."),
    ('verb', 'turn', '', "Hold on it and circle the mouse slow. Feel it bite."),
    ('verb', 'point_aim', '', "Hold it on the card. It wanders. Fire when it's on."),
    ('verb', 'point', '', "Tool on the mark, then click. Just the mark."),
    ('verb', 'flick', '', "Hold it and shake the mouse. Short and sharp."),
    ('verb', 'path', '', "Hold and follow the line. Steady pace, don't rush it."),
    ('verb', 'window_strike', '', "Hold to lift, let go to strike. Higher hits harder."),
    ('verb', 'window_hold', '', "Hold it down and listen. Let go when it sounds right."),
    ('verb', 'wipe', '', "Hold and scrub over it. Keep going till it's bright."),
    # refusals (Carl, 21 Nov: idiot proof): a wrong click says what is wrong; the caption says what to do instead
    ('refused', 'blocked', '', "Something's still holding it. Free that first."),
    ('refused', 'not_yet', '', "Not that one yet. Look for what's lit."),
    ('refused', 'needs_tool', '', "You'll want a tool for that."),
    ('refused', 'wrong_tool', '', "Wrong tool for that. Put it back."),
    # stage 1 (full)
    ('step', 's1.clamp', '', "Frame in the vise. Snug, not tight, or you'll mark it."),
    ('step', 's1.bind', '', "Cutters. Snip both wire twists on the old grip."),
    ('step', 's1.tape', '', "Peel the tape off. Find the loose end and follow it round."),
    ('step', 's1.screw_a', '', "Upper screw first. Slotted bit in the driver."),
    ('action', 's1.screw_a', 'dish', "Screws go in the dish. Lose one and you're making another."),
    ('step', 's1.screw_b', '', "Oil on the lower screw first. One drop. Let it soak."),
    ('action', 's1.screw_b', 'tap', "Now tap the driver's head. Two taps. Wakes the thread up."),
    ('recovery', 's1.screw_b.r', '', "Slot's gone round. Pliers on the head, back it out slow."),
    ('step', 's1.scales', '', "Screws are out. Lift both scales off, onto the mat."),
    ('step', 's1.lead', '', "Trigger lead. Pinch the tab, not the wire."),
    ('step', 's1.pin', '', "Punch on the pin, then the mallet. Three firm taps."),
    ('action', 's1.pin', 'pull', "Pliers now. Pull it the rest of the way."),
    ('recovery', 's1.pin.r', '', "Bent it. On the vise, tap it straight."),
    ('step', 's1.housing', '', "Slide the housing off. Thumb on that spring, it jumps."),
    ('step', 's1.inspect', '', "Turn the frame round in the vise. Look at the tang."),
    # stage 2 (shorter)
    ('step', 's2.swap', '', "Frame to the stand. Servo in the vise."),
    ('step', 's2.dust', '', "Brush it. The screws are under that muck."),
    ('step', 's2.screws', '', "Case screws. Cross bit this time."),
    ('step', 's2.stripped', '', "That one's chewed. Squeeze the pliers first, then turn."),
    ('step', 's2.pry', '', "Pick in the seam. Three clips. Lean, don't stab."),
    ('step', 's2.leads', '', "Snip the leads at the board end. On the bands."),
    ('step', 's2.board', '', "Burnt board out. Keep its resistor, bin the rest."),
    ('step', 's2.circlip', '', "Circlip next. Pliers. Keep hold or it flies."),
    ('step', 's2.gears', '', "Gears off. Top one first."),
    ('step', 's2.trunnion', '', "Two small screws, then lift the gimbal. That's the prize."),
    ('step', 's2.winding', '', "Wind the copper onto the bobbin. Steady, it snaps."),
    # stage 3 (shorter)
    ('step', 's3.bath', '', "Gimbal in the jar. Swirl it."),
    ('step', 's3.brush', '', "Brush the race and both trunnions. Bright metal."),
    ('step', 's3.pick', '', "Pick the grit out. Three little holes."),
    ('step', 's3.oil', '', "One drop on each trunnion. One."),
    ('step', 's3.spin', '', "Flick the rotor. Listen to it."),
    ('step', 's3.trim', '', "Trim the leads at the marks. Sense lead, flush."),
    ('recovery', 's3.lead.r', '', "Frayed lead. Strip it back and twist it tidy."),
    ('step', 's3.strip', '', "Strippers. Squeeze, then pull. Don't bite the copper."),
    ('step', 's3.tin', '', "Iron and solder. Tin the ends till they shine."),
    ('step', 's3.loop', '', "Leads in the clip. Solder across the resistor, then shrink."),
    ('recovery', 's3.loop.r', '', "Short lead. Splice a bit on. One more joint."),
    ('step', 's3.test', '', "Probes across the resistor. Lamp should light."),
    ('step', 's3.scribe', '', "Old scale on the sheet. Scribe round it."),
    ('step', 's3.cut', '', "Clamp both sheets. Snips, cut on the line."),
    ('action', 's3.cut', 'strap', "Strip off the edge first. That's your strap."),
    ('step', 's3.file', '', "File to the line. Long strokes. Stop at the line."),
    ('step', 's3.punch', '', "Template back on. Punch each hole mark."),
    ('step', 's3.drill', '', "Four holes. Let the bit cut, don't lean on it."),
    ('step', 's3.strap', '', "Strap in the vise. Bend it to the mark. Twice."),
    ('recovery', 's3.strap.r', '', "Cracked. Spare strip's on the mat. Same again."),
    # stage 4 (shorter)
    ('step', 's4.mould', '', "Tang mould from the rack. Seat it, brush it out."),
    ('step', 's4.charge', '', "Offcuts in, then pour the nanites to the line."),
    ('step', 's4.press', '', "Close and lock it. Pump, then hold."),
    ('step', 's4.open', '', "Vent it first. Pliers, it's hot. Then quench."),
    ('step', 's4.flash', '', "Knock the sprue off. File the flash. Ease the pocket."),
    ('step', 's4.pressfit', '', "Rotor out, then press the gimbal home. Stop at flush."),
    ('recovery', 's4.pressfit.r', '', "Cracked the lug. Bead of nanites on it, it'll hold."),
    # stage 5 (only on a stall or a mistake)
    ('step', 's5.loop', '', "Tuck the loop in the side channel. Into the clips."),
    ('step', 's5.rotor', '', "Rotor back in. Ring on, snap it home."),
    ('step', 's5.strap', '', "Strap over the spine. It clicks."),
    ('step', 's5.plates', '', "Plates on their pegs. Left, turn it over, right."),
    ('step', 's5.start', '', "Start the screws by hand. Feel them catch."),
    ('step', 's5.torque', '', "Drive them home, then torque. Stop when it pitches up."),
    ('step', 's5.seam', '', "Applicator along both seams. Steady."),
    ('step', 's5.cure', '', "Lamp over. Ten seconds. Leave it be."),
    ('step', 's5.damp', '', "Tilt it hard. It should swing once and stop."),
    ('recovery', 's5.damp.r', '', "Lead's pinched. Ease it back along its channel."),
    # stage 6 (only on a stall or a mistake)
    ('step', 's6.slide', '', "Frame back in the vise. Grip up onto the tang."),
    ('step', 's6.plug', '', "Lead down the back channel. Plug it, right way up."),
    ('step', 's6.pin', '', "Pin back in. Two taps."),
    ('recovery', 's6.pin.r', '', "Pin's proud. Tap it flush."),
    ('step', 's6.screws', '', "New screws from the dish. Cross bit."),
    ('step', 's6.cell', '', "Old bits in the bin. Pistol on the mat. Cell in."),
]

SILENT = {
    's1.housing.r': "Brann's fault line 'Little ones fly. Find it before you go on.' already says it (fault.first:flew_off).",
    's2.circlip.r': "as s1.housing.r (flew_off).",
    's3.spin.r': "Brann's spin_bad line already says it ('Grinding. There's still grit in it.').",
    's3.test.r': "Brann's fault_cold_joint line already says it ('Cold joint. Dull and grey. Heat it again.').",
    's5.rotor.r': "as s1.housing.r (flew_off).",
    's7.inspect': "stage 7 keeps its existing lines (stage7, damper, cards, hand_over); the tutor is silent.",
    's7.shake': "stage 7 keeps its existing lines.",
    's7.card_after': "stage 7 keeps its existing lines (card_after_*).",
    's7.leave': "stage 7 keeps its existing lines (hand_over).",
}


def ident(kind, ref, key):
    if kind == 'welcome': return 'tutor_welcome'
    return 'tutor_' + re.sub(r'[^a-z0-9]+', '_', (ref + ('_' + key if key else '')).lower()).strip('_') + {'verb': '_verb', 'refused': '_refused'}.get(kind, '')


def main():
    steps = json.loads((ROOT / 'art/steady_hands_bench_20261120/data/steps.json').read_text())
    stage_of = {st['id']: i for i, s in enumerate(steps['stages']) for st in s['steps']}
    lines = []
    for kind, ref, key, text in ROWS:
        if kind in ('step', 'action', 'recovery') and ref not in stage_of: raise SystemExit(f'unknown step {ref}')
        trigger = {'welcome': 'tutor.welcome', 'step': f'tutor.step:{ref}', 'action': f'tutor.action:{ref}:{key}',
                   'verb': f'tutor.verb:{ref}', 'recovery': f'tutor.recovery:{ref}', 'refused': f'tutor.refused:{ref}'}[kind]
        i = ident(kind, ref, key)
        lines.append({'id': i, 'speaker': 'npc_brann', 'kind': kind, 'step': ref if kind in ('step', 'action', 'recovery') else '',
                      'verb': ref if kind in ('verb', 'refused') else '', 'key': key, 'stage': stage_of.get(ref, -1), 'trigger': trigger, 'text': text,
                      'file': f'Assets/AthenHill/Audio/ElevenLabs/Bench/Tutor/npc_brann-{i}.wav'})
    ids = [l['id'] for l in lines]; assert len(ids) == len(set(ids)), 'duplicate ids'
    # every step of the table is voiced or deliberately silent
    voiced = {l['step'] for l in lines if l['kind'] in ('step', 'recovery')}
    missing = [s for s in stage_of if s not in voiced and s not in SILENT]
    if missing: raise SystemExit(f'steps neither voiced nor silent: {missing}')
    doc = {'note': "Brann's guided first job (tutor agent, 21 Nov 2026). Generated by build_lines.py; caption text = text. "
                   "Paths are relative to unity/AthenHill. Triggers are the tutor's own (BenchTutor), not the bench's.",
           'voices': {'npc_brann': {'name': 'Callum', 'id': 'N2lVS1w4EtoT3dr4eOWO'}},
           'lines': lines, 'silent': SILENT}
    (HERE / 'lines.json').write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    chars = sum(len(l['text']) for l in lines)
    print(f'{len(lines)} lines, {chars} characters, {len(SILENT)} silent steps')


if __name__ == '__main__':
    main()
