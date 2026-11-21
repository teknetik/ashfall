#!/usr/bin/env python3
"""Writes instructions.json: the plain on-screen instruction for every action of the bench job (tutor agent, 21 Nov 2026,
Carl: "the tutorial needs to be idiot proof"). Shown in the bench's action line for the whole first job, every stage.

The text for an action is OVERRIDES[step:key] when given, else made from its verb, tool, part and target with the names
below. At run time BenchTutor puts a prefix in front when the hand is not ready ("Take the screwdriver: click it",
"Click the pistol to pick it up", "Put the pliers back first: right click") and a suffix when the camera is about to move
("· the view moves to the vise"). Edit the tables here and re-run; the installer copies the file into BenchTutorLines.asset.
Check: every action of data/steps.json has a text (the script fails otherwise)."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]

NAMES = {
    'pistol.frame': 'the pistol', 'pistol.cell': 'the charge cell', 'pistol.cell_latch': 'the cell latch', 'pistol.housing': 'the backstrap housing',
    'pistol.housing_pin': 'the housing pin', 'pistol.housing_spring': 'the spring', 'pistol.lead': 'the trigger lead', 'pistol.lead_plug': 'the trigger lead plug',
    'pistol.scale_l': 'the left scale', 'pistol.scale_r': 'the right scale', 'pistol.screw_grip_a': 'the upper grip screw', 'pistol.screw_grip_b': 'the lower grip screw',
    'pistol.wrap': 'the tape and leather wrap',
    'servo.board': 'the burnt board', 'servo.case_body': 'the servo', 'servo.case_lid': 'the case lid', 'servo.circlip': 'the circlip',
    'servo.clip_1': 'the first case clip', 'servo.clip_2': 'the second case clip', 'servo.clip_3': 'the third case clip',
    'servo.gear_low': 'the bottom gear', 'servo.gear_mid': 'the middle gear', 'servo.gear_top': 'the top gear', 'servo.gimbal_cradle': 'the gimbal',
    'servo.gimbal_race': 'the gimbal race', 'servo.gimbal_retainer': 'the retaining ring', 'servo.gimbal_rotor': 'the rotor', 'servo.lead_plug': 'the board plug',
    'servo.screw_case_a': 'the case screw', 'servo.screw_case_b': 'the case screw', 'servo.screw_case_c': 'the case screw', 'servo.screw_case_d': 'the chewed screw',
    'servo.screw_trunnion_a': 'the trunnion screw', 'servo.screw_trunnion_b': 'the trunnion screw',
    'materials.bobbin': 'the bobbin', 'materials.core_flash': 'the flash', 'materials.core_sprue': 'the sprue', 'materials.lead_a_slug': 'the insulation slug',
    'materials.lead_a_strands': 'the lead', 'materials.lead_b_slug': 'the insulation slug', 'materials.lead_b_strands': 'the lead', 'materials.loop_resistor': 'the damper loop',
    'materials.resistor': 'the resistor', 'materials.sheet_a': 'the alloy sheet', 'materials.sheet_b': 'the second alloy sheet', 'materials.sheet_a_plate': 'the left plate',
    'materials.sheet_b_plate': 'the right plate', 'materials.sheet_a_plug_1': 'the hole slug', 'materials.sheet_a_plug_2': 'the hole slug', 'materials.sheet_a_plug_3': 'the hole slug',
    'materials.sheet_a_plug_4': 'the hole slug', 'materials.sheet_a_strap': 'the alloy strip', 'materials.sheet_b_strap': 'the spare strip', 'materials.strap_bent': 'the strap',
    'materials.strap_bent_1': 'the strap', 'materials.vial': 'the nanite vial', 'materials.vial_stopper': 'the vial stopper',
    'grip.core': 'the grip', 'grip.screw_a': 'the new screw', 'grip.screw_b': 'the new screw',
    'fixtures.lamp_head': 'the cure lamp', 'fixtures.mould_tang': 'the tang mould', 'fixtures.press_lever': 'the press lever', 'fixtures.press_vents': 'the press vent',
    'fixtures.vise': 'the vise', 'fixtures.vise_screw': 'the vise handle', 'tools.punch': 'the punch', 'tools.roll': 'the tool roll',
}
TOOLS = {
    'tool:applicator': 'the nanite applicator', 'tool:brush': 'the wire brush', 'tool:cutters': 'the wire cutters', 'tool:drill': 'the hand drill',
    'tool:file': 'the flat file', 'tool:file_round': 'the round file', 'tool:mallet': 'the mallet', 'tool:oil': 'the oil dropper', 'tool:pick': 'the pick',
    'tool:pliers': 'the pliers', 'tool:probe': "the tester's probes", 'tool:punch': 'the punch', 'tool:screwdriver': 'the screwdriver',
    'tool:scribe': 'the scribe', 'tool:snips': 'the snips', 'tool:solder': 'the soldering iron', 'tool:strippers': 'the wire strippers',
}
SHOTS = {
    'wide': 'the whole bench', 'work': 'the work mat', 'vise': 'the vise', 'over': 'a view from above', 'vise_l': 'the vise, from the left',
    'vise_r': 'the vise, from the right', 'mat': 'the work mat, close', 'parts': 'the parts mat', 'card': 'the test card on the board',
    'tray': 'the tray', 'press': 'the nanite press', 'tester': 'the bench tester', 'room': 'the shop',
    'press_low': 'the nanite press, from low down',
    'press_side': 'the nanite press, from the side', 'roll': 'the tool roll',
}
# where a part goes, by the start of the target id
PLACES = [
    ('fixtures.workmat', 'the black work mat'), ('fixtures.tray', 'the tray'), ('fixtures.vise', 'the vise jaws'), ('fixtures.dish', 'the magnetic dish'),
    ('fixtures.partsmat', 'its outline on the parts mat'), ('fixtures.bin', 'the scrap bin'), ('fixtures.cradle', 'the cradle stand'),
    ('fixtures.jar', 'the solvent jar'), ('fixtures.press', 'the press'), ('fixtures.pad', 'the insulated pad'), ('fixtures.mouldrack', 'the mould rack'),
    ('fixtures.holster', 'the holster'), ('tools.roll', 'its slot in the roll'), ('place.mat', 'the work mat'), ('place.rest', 'its place'),
    ('place.roll', 'its place on the bench'), ('place.thirdhand', 'the third-hand clip'), ('place.bench', 'the bench'), ('place.holster', 'the holster'),
    ('place.sheet', 'the other sheet'), ('place.plate', 'the plates'), ('place.servo', 'the servo'), ('place.mould', 'the mould'), ('place.press', 'the press'),
]
# plain words with the control, where the made-up text would not be clear enough
OVERRIDES = {
    's0.pistol:lay': 'Drag the pistol onto the black work mat and let go',
    's1.bind:snip_a': 'With the wire cutters, click the lit wire twist',
    's1.bind:snip_b': 'With the wire cutters, click the second lit wire twist',
    's0.roll:untie': 'Hold left on the tool roll strap and circle the mouse slowly to untie it',
    's0.roll:unroll': 'Drag the tool roll flat onto the bench to unroll it',
    's0.shake_before:shake': 'Optional: hold the pistol up and shake the mouse side to side to hear it rattle',
    's0.cell:latch': 'Hold left on the cell latch and circle the mouse to open it',
    's0.cell:cell': 'Drag the charge cell out onto the insulated pad',
    's1.clamp:snug': 'Hold left on the vise handle and circle the mouse until the jaws are snug, then let go (not too tight)',
    's1.tape:peel': 'Hold left on the loose end of the tape and follow the lit line round the grip at a steady pace',
    's1.screw_b:oil': 'With the oil dropper, click the lower screw head: one drop',
    's1.screw_b:tap': 'With the screwdriver on the lower screw, hold left to lift and let go to tap it: two taps',
    's1.inspect:find': 'Hold left on the vise and circle the mouse to turn the frame round until you see the crack',
    's2.swap:open': 'Hold left on the vise handle and circle the mouse the other way to open the jaws',
    's2.stripped:grip': 'With the pliers on the chewed screw, hold left to squeeze; let go when they bite',
    's3.bath:swirl': 'Hold left on the gimbal in the jar and circle the mouse to swirl it',
    's3.spin:flick': 'Hold the gimbal up and flick the mouse sharply, then listen',
    's3.strip:a_pull': 'With the strippers still closed, drag away from the lead to pull the insulation off',
    's3.strip:b_pull': 'With the strippers still closed, drag away from the lead to pull the insulation off',
    's4.press:close': 'Hold left on the press lever and circle the mouse to close and lock the press',
    's4.press:knit': 'Hold left to pump the press into the green band and keep it there until the core has knit',
    's4.charge:pour': 'Hold left to tip the vial and pour; let go at the line',
    's4.open:vent': 'Hold left on the press vent; let go when the hiss stops',
    's5.cure:swing': 'Hold left on the cure lamp arm and circle the mouse to swing the lamp over the grip',
    's5.cure:wait': 'Leave the grip under the lamp for ten seconds: put tools back meanwhile, do not lift it',
    's5.cure:away': 'Hold left on the cure lamp arm and circle the mouse to swing it away',
    's5.damp:tilt': 'Hold the grip up and flick the mouse sharply to tilt it: it should swing once and stop',
    's7.inspect:look': 'Optional: pick the pistol up and turn it with the wheel to look it over',
    's7.shake:shake': 'Hold the pistol up and shake the mouse side to side',
    's7.leave:holster': 'Put the pistol in the holster, or press Esc to step back',
}
# ids that an installed recipe may still have while steps.json has moved on (kept so an older build still has a line)
LEGACY = {
    's1.bind:snip': 'With the wire cutters, click each lit wire twist',
}
REFUSED = {
    'blocked': 'The {part} will not come yet: {other} holds it. Free that first.',
    'not_yet': 'Not {part} yet.',
    'needs_tool': 'That needs {other}: click it to take it.',
    'wrong_tool': '{other} is the wrong tool for that: right click to put it back.',
    'wrong_place': '{part} does not go there.',
}
PREFIX = {
    'take_tool': 'Take {tool}: click it',
    'put_back': 'Put {held} back first: right click',
    'pick_up': 'Click {part} to pick it up',
    'view': 'the view moves to {shot}',
    'view_now': 'Now: {shot}',
    'view_back': 'Back to {shot}',
}


def place(target):
    if not target: return 'its place'
    if target == 'seat' or target == 'start': return 'its socket'
    if target == 'clear': return None
    for pre, name in PLACES:
        if target.startswith(pre): return name
    return NAMES.get(target.split('/')[0], 'where it glows')


def text(step, a):
    key = f"{step['id']}:{a['key']}"
    if key in OVERRIDES: return OVERRIDES[key]
    v, m = a['verb'], a.get('mode') or ''
    part = NAMES.get(a.get('part') or '', 'it')
    tool = TOOLS.get(a.get('tool') or '', None)
    with_tool = f'With {tool}, ' if tool else ''
    if v == 'Seat':
        if m == 'inspect': return f'Pick up {part} and turn it with the wheel to look it over'
        to = place(a.get('target'))
        if to is None: return (with_tool + f'drag {part} off and away').capitalize() if not tool else with_tool + f'drag {part} off and away'
        s = f'drag {part} to {to} and let go (the wheel turns it to fit)'
        return (with_tool + s) if tool else s[0].upper() + s[1:]
    if v == 'Turn':
        if m == 'stop': return f'Hold left on {part} and circle the mouse until it is snug, then let go'
        if m == 'reveal': return f'Hold left on {part} and circle the mouse to turn it round'
        out = (a.get('turns') or 0) < 0
        if a.get('part') == 'fixtures.vise_screw': return 'Hold left on the vise handle and circle the mouse to ' + ('open the jaws' if out else 'close the jaws')
        s = f'hold left on {part} and circle the mouse slowly' + (' to undo it' if out else ' to turn it in' if tool == TOOLS['tool:screwdriver'] else ' to turn it')
        return (with_tool + s) if tool else s[0].upper() + s[1:]
    if v == 'Path':
        s = 'hold left at the start of the lit line and follow it to the end at a steady pace'
        return (with_tool + s) if tool else s[0].upper() + s[1:]
    if v == 'Wipe':
        s = 'hold left and scrub over the dirty patch until it is clean'
        return (with_tool + s) if tool else s[0].upper() + s[1:]
    if v == 'Point':
        if m == 'aim': return 'Hold the pistol on the card and click to fire'
        s = 'click each lit mark'
        return (with_tool + s) if tool else s[0].upper() + s[1:]
    if v == 'Flick': return f'Hold {part} up and shake the mouse side to side'
    if v == 'Window':
        if m == 'strike': return (with_tool if tool else 'With it, ') + 'hold left to lift and let go to strike'
        if m == 'sustain': return 'Hold left to pump into the green band and keep it there'
        if m == 'wait': return 'Wait: leave it be'
        s = f'hold left on {part}; let go when it looks and sounds right' if part != 'it' else 'hold left; let go when it looks and sounds right'
        return (with_tool + s) if tool else s[0].upper() + s[1:]
    raise SystemExit(f'no text for {key}')


def main():
    layout = json.loads((ROOT / 'art/steady_hands_bench_20261120/data/layout.json').read_text())
    missing = [x['id'] for x in layout.get('shots', []) if x.get('id') and x['id'] not in SHOTS]
    if missing: raise SystemExit(f'no name for shots {missing}')
    steps = json.loads((ROOT / 'art/steady_hands_bench_20261120/data/steps.json').read_text())
    actions = {}
    for s in steps['stages']:
        for st in s['steps']:
            for a in st['actions']:
                actions[f"{st['id']}:{a['key']}"] = text(st, a)
                for t in (a.get('tool'),):
                    if t and t != '*' and t not in TOOLS: raise SystemExit(f'no name for tool {t}')
                if a.get('part') and a['part'] not in NAMES: raise SystemExit(f"no name for part {a['part']}")
    for k, v in LEGACY.items(): actions.setdefault(k, v)
    doc = {'note': 'On-screen instructions for the guided first job (tutor agent, 21 Nov 2026). Generated by build_instructions.py.',
           'actions': actions, 'names': NAMES, 'tools': TOOLS, 'shots': SHOTS, 'prefix': PREFIX, 'refused': REFUSED}
    (HERE / 'instructions.json').write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    print(f'{len(actions)} actions, {len(NAMES)} part names, {len(TOOLS)} tools, {len(SHOTS)} shots')


if __name__ == '__main__':
    main()
