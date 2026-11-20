"""Native review frames for the character arms pass (art/character_arms_20261120/README.md), phase 2 of the showcase
programme. Captures only (plus a few state checks); the arms are judged by eye from the frames.

  1. Every talking colonist (Mira, Torr, Vex, Linn, Brann, Tamsin, Ossa, Rell, and the residents when their prompt is
     reachable): walk up, E, then a frame every 0.5 s for 6 s in the conversation camera (the shot Carl sees), Esc.
  2. The player colonist unarmed on the open spawn apron (east of the East Gate arches), filmed by the riding review rigs
     (ArmsReviewRig: the camera rides with the colonist at 3.4 m, 40 degree lens, full body about 70 % of the frame, HUD
     hidden): idle from front / front-right / right / behind; walk and run from the right, front-right and behind; a
     turn on the spot from the front.
  3. The scrap pistol at the Warden firing line (Berms, open ground), same rigs: draw (right, front-right), lowered carry
     standing / walking / running (right, front-right), raised aim standing (right, front-right, front), aim walking
     (right), firing (right, front-right), lower after the shot, holster; plus one gameplay over-the-shoulder aim frame.
  4. Each ambient walker passing its review camera (cam_arms_<walker>), frames while it is within 7 m of where it stood
     at load (the camera's target).

  ATHEN_EXE=<player> python unity/tools/capture_character_arms_native.py [OUT]
Run through the phase 2 native wrapper (QA display, lock, cap). Output: OUT/run/*.png and OUT/report.json.
"""
import math, time
import showcase_qa as S
from showcase_qa import qa, ok, note, cap

RIGS = ('front', 'right', 'left', 'frontright', 'frontleft', 'behind', 'backright')


def rig(name=None):
    """Switch the riding review rig (None = back to the gameplay follow camera)."""
    qa.cmd('setActive', prefix='Arms review rig [', active=False)
    if name:
        qa.cmd('setActive', prefix=f'Arms review rig [{name}]', active=True)
        time.sleep(.25)
    else:
        qa.view('follow')


def hud(hidden):
    # reviewHud only works while a dialogue is open; outside one the player logs an InvalidOperationException
    # ("Unobstructed companion captures require an actual active dialogue"), which failed this script's own
    # no-exceptions check on builds p2-b3 and p2-b4 (20 Nov 2026). The frames are taken with the HUD as the player
    # sees it.
    return


SAVE = S.kit_save(S.OUT / 'save', flags=['home_asked', 'home_leased'])
NPCS = [  # name, landmark, npc x/z (as in check_showcase_camera.py)
    ('Mira', 'basic_general', (8.0, 15.8)),
    ('Torr', 'mission_slab', (9.0, -12.0)),
    ('Vex', 'west_gate', (41.7, -1.5)),
    ('Linn', 'oa_hill', (2.5, 4.7)),
    ('Brann', 'salvage_counter', (-15.8, 15.45)),
    ('Tamsin', 'field_supply_counter', (20.45, -11.7)),
    ('Ossa', 'checkpoint_ossa', None),
    ('Rell', 'checkpoint_rell', None),
]


def burst(prefix, seconds=6.0, every=.5, layout=False):
    n = int(round(seconds / every))
    t0 = time.monotonic()
    for i in range(n + 1):
        cap(f'{prefix}-{i * every:04.1f}s', layout=layout)
        dt = t0 + (i + 1) * every - time.monotonic()
        if dt > 0:
            time.sleep(dt)


def hold_burst(keys, prefix, seconds, every=.5):
    """Hold keys (real input) while capturing a burst."""
    qa.focus()
    for k in keys:
        qa.key(k, True)
    try:
        time.sleep(.6)   # into the gait
        burst(prefix, seconds, every)
    finally:
        for k in keys:
            qa.key(k, False)
        qa.release_all()


def open_dialogue(name, landmark, xz):
    qa.goto(landmark); qa.view('follow'); time.sleep(.9)
    if xz:
        qa.face(*xz); time.sleep(.3)
    prompt = S.snap()['interaction']['prompt'] or ''
    if name not in prompt and xz:
        p = qa.pos(); d = math.hypot(xz[0] - p[0], xz[1] - p[2])
        if d > 2.2:
            try:
                qa.walk_to(xz[0] + (p[0] - xz[0]) * 1.8 / d, xz[1] + (p[2] - xz[1]) * 1.8 / d, tol=.5, timeout=10)
            except TimeoutError:
                pass
            qa.face(*xz); time.sleep(.3)
        prompt = S.snap()['interaction']['prompt'] or ''
    if name not in prompt:
        return False, prompt
    qa.tap('e', settle=.05)
    return bool(S.wait_for(lambda: qa.state() == 'Dialogue', 3)), prompt


def draw(slot, weapon):
    for _ in range(4):
        c = S.snap()['combat']
        if c['Armed'] and c.get('weaponId') == weapon:
            return True
        qa.tap(slot, settle=.7)
    c = S.snap()['combat']
    return c['Armed'] and c.get('weaponId') == weapon


def gait_set(prefix, place, yaw, views, keys, seconds, every):
    """For each view: back to the start, heading yaw, hold keys (W walks along the heading whatever the view), frames."""
    for v in views:
        rig(None); qa.goto(place); qa.view('follow'); qa.yaw(yaw); qa.pitch(10); time.sleep(.8)
        rig(v); time.sleep(.3)
        hold_burst(keys, f'{prefix}-{v}', seconds, every)
        time.sleep(.4)


def body():
    S.launch(save=SAVE)
    S.start()
    S.time_set(13)

    # ---- 1. conversation shots (the real conversation camera), a frame every 0.5 s for 6 s
    S.report['dialogues'] = {}
    for name, landmark, xz in NPCS:
        opened, prompt = open_dialogue(name, landmark, xz)
        S.report['dialogues'][name] = {'opened': opened, 'prompt': prompt}
        if not ok(opened, f'{name}: dialogue opened', prompt):
            continue
        S.wait_for(lambda: S.show()['conversation']['weight'] >= .999, 3)
        time.sleep(.3)
        burst(f'talk-{name.lower()}', 6.0, .5, layout=False)
        qa.tap('Escape', settle=.4)
        S.wait_for(lambda: qa.state() == 'Play', 3)
    # residents (added 20 Nov 2026 with QA landmarks res_<name>)
    for name in ('Nadje', 'Pell', 'Oren'):
        try:
            opened, prompt = open_dialogue(name, 'res_' + name.lower(), None)
        except Exception as e:  # noqa: BLE001
            note(f'{name}: landmark res_{name.lower()} not usable', repr(e)[:200]); continue
        if opened:
            S.wait_for(lambda: S.show()['conversation']['weight'] >= .999, 3); time.sleep(.3)
            burst(f'talk-{name.lower()}', 6.0, .5); qa.tap('Escape', settle=.4)
            S.wait_for(lambda: qa.state() == 'Play', 3)
        else:
            note(f'{name}: no talk prompt at res_{name.lower()} (a walking resident may have moved on)', prompt)

    # ---- 2. the player unarmed, riding review rigs, open apron by the spawn (heading west along the avenue)
    hud(True)
    CITY, WEST = 'west_gate', 270
    rig(None); qa.goto(CITY); qa.view('follow'); qa.yaw(WEST); qa.pitch(10); time.sleep(1.0)
    for v in ('front', 'frontright', 'right', 'behind'):
        rig(v); time.sleep(.6)
        burst(f'player-unarmed-idle-{v}', 1.5, .5)
    gait_set('player-unarmed-walk', CITY, WEST, ('right', 'frontright', 'behind'), ['w'], 2.5, .2)
    gait_set('player-unarmed-run', CITY, WEST, ('right', 'frontright', 'behind'), ['Shift_L', 'w'], 1.6, .15)
    # a turn on the spot: tap S (turn to face back), frames from a front rig fixed at the start heading
    rig(None); qa.goto(CITY); qa.view('follow'); qa.yaw(WEST); time.sleep(.8)
    rig('front'); time.sleep(.3)
    qa.focus(); qa.key('s', True); time.sleep(.1); qa.key('s', False)
    burst('player-unarmed-turn-front', 1.5, .15)
    rig(None)

    # ---- 3. the pistol in third person at the firing line (open ground)
    RANGE = 'checkpoint_firingline'
    qa.goto(RANGE); qa.view('follow'); qa.yaw(WEST); qa.pitch(5); time.sleep(1.0)
    rig('right'); time.sleep(.3)
    qa.focus(); qa.tap('2', settle=.05)
    burst('pistol-draw-right', 1.2, .1)
    ok(draw('2', 'weapon_scrap_pistol'), 'pistol drawn with 2 at the range')
    time.sleep(1.5)   # the draw raise and the face-the-view time pass
    for v in ('right', 'frontright', 'front', 'behind'):
        rig(v); time.sleep(.5)
        burst(f'pistol-carry-idle-{v}', 1.0, .5)
    gait_set('pistol-carry-walk', RANGE, WEST, ('right', 'frontright'), ['w'], 2.0, .2)
    gait_set('pistol-carry-run', RANGE, WEST, ('right', 'frontright'), ['Shift_L', 'w'], 1.4, .15)
    rig(None); qa.goto(RANGE); qa.view('follow'); qa.yaw(WEST); qa.pitch(3); time.sleep(.8)
    # aim (right mouse) seen from the rigs; the heading stays the follow camera's (the steering proxy)
    for v in ('right', 'frontright', 'front'):
        rig(v); time.sleep(.3)
        qa.focus(); qa.button(3, True)
        try:
            time.sleep(.6)
            burst(f'pistol-aim-{v}', 1.0, .25)
            if v == 'right':
                qa.key('w', True)
                try:
                    time.sleep(.4); burst('pistol-aim-walk-right', 1.6, .2)
                finally:
                    qa.key('w', False)
        finally:
            qa.button(3, False)
        time.sleep(.8)
    for v in ('right', 'frontright'):
        rig(v); time.sleep(.3)
        qa.focus(); qa.key('f', True)
        try:
            burst(f'pistol-fire-{v}', 1.0, .1)
        finally:
            qa.key('f', False)
        time.sleep(.3)
        burst(f'pistol-lower-after-shot-{v}', 1.4, .2)
    rig('right'); time.sleep(.3)
    qa.focus(); qa.tap('2', settle=.05)
    burst('pistol-holster-right', 1.0, .1)
    # the gameplay view Carl sees: over the shoulder, aiming
    rig(None); hud(False)
    draw('2', 'weapon_scrap_pistol'); time.sleep(.8)
    qa.focus(); qa.button(3, True)
    try:
        time.sleep(.8); cap('pistol-aim-gameplay-over-shoulder', layout=True)
    finally:
        qa.button(3, False)
    S.report['pistolEnd'] = S.snap()['combat']
    qa.tap('2', settle=.6)

    # ---- 4. ambient walkers passing their review cameras (target = where the walker stood at load)
    hud(True)
    import json
    cams = {c['name']: c for c in json.loads((S.ROOT / 'art/character_arms_20261120/review_cameras.json').read_text())}
    homes = {}
    for walker in ('npc_walker_01', 'npc_walker_02', 'npc_walker_03', 'npc_yard_mechanic'):
        cam = 'cam_arms_' + walker.replace('npc_', '')
        try:
            qa.view(cam)
        except Exception as e:  # noqa: BLE001
            note(f'{walker}: no review camera {cam}', repr(e)[:200]); continue
        frames = 0; t_end = time.monotonic() + 90
        while time.monotonic() < t_end and frames < 16:
            acts = S.actors()
            me = next((a for n, a in acts.items() if walker in n or n in walker), None)
            if me is None:
                note(f'{walker}: not in actors.json', list(acts)[:20]); break
            pos = me['position']
            t = cams.get(cam, {}).get('target')
            homes.setdefault(walker, [t[0], 0, t[2]] if t else pos)
            if S.dist(pos, homes[walker]) < 7:
                cap(f'walker-{walker}-{frames:02d}', layout=False); frames += 1
                time.sleep(.35)
            else:
                time.sleep(.5)
        note(f'{walker}: {frames} passing frames')
    hud(False)
    qa.view('follow')


S.run(body)
