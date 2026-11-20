"""Native review frames of the three Ward residents (art/ward_residents_20261120/README.md): Nadje (Karaveen trader, caravan
market), Pell (Node 07 dock clerk) and Oren (water carrier, south wall homes -> ration taps).

The residents walk their routes with work stops, so fixed cameras miss them. Their face, body and beside review cameras
(cam_res_<name>_face|_body|_beside) carry ResidentReviewCamera, which follows the resident every frame; "view" copies that
pose into the game camera at the moment it is called, so this script re-issues the view before every capture.
  1. 13:00, 17:00, 20:30 (clock paused): face close-up (~0.9 m) and full body (~3 m) of each resident, wherever they are,
     plus the walker's state (clip, position) at that moment.
  2. One sequence per resident at a short work stop, filmed from that stop's fixed camera: a frame every 0.5 s from about
     3 m before the stop, through the stop, until about 3 s after the walk out (Nadje: pottery stall, Pell: platform
     scale, Oren: ration tap).
  3. Conversation distance: the player is put on the res_<name> QA landmark beside the resident's main stop, waits for the
     resident to be at work there, faces them and is captured in the normal follow view; the cam_res_<name>_beside frame
     (eye height, ~1.4 m) is taken at the same moment.
The HUD stays on (reviewHud only works inside a dialogue). Face and body frames wait until the resident is at a work stop. Frames are 1920x1080 PNGs in the run folder, listed in report.json with the actor state.
  ATHEN_EXE=<player> ATHEN_OUT=<folder> python unity/tools/capture_residents_native.py [OUT]
Run through the native wrapper (lock, memory cap, QA display), like the check_showcase_*.py checks.
"""
import math, time
import showcase_qa as S
from showcase_qa import qa, ok, note

# name, actor (ActorAnimation object), clip prefix, sequence stop (x, z) and its camera, main-stop clip (for "beside")
RESIDENTS = [
    dict(name='nadje', actor='WardResident Nadje', clip='trader', stop=(-37.25, 5.2), stop_cam='cam_res_nadje_pottery_and_water',
         main_xz=(-40.15, 12.0), main_clip='trader_talk'),
    dict(name='pell', actor='WardResident Pell', clip='clerk', stop=(10.4, 35.6), stop_cam='cam_res_pell_platform_scale',
         main_xz=(12.3, 30.95), main_clip='clerk_talk'),
    dict(name='oren', actor='WardResident Oren', clip='carrier', stop=(2.3, -27.95), stop_cam='cam_res_oren_ration_tap',
         main_xz=(2.3, -27.95), main_clip=None),   # at the tap: drink (talk) then wait (idle), both count
]
HOURS = [13.0, 17.0, 20.5]


def actor(r):
    a = S.actors().get(r['actor'])
    if not a:
        raise RuntimeError('actor not found: ' + r['actor'])
    return a


def at_work(a, r):
    return bool(a.get('CurrentClip')) and not a['CurrentClip'].endswith('_walk')


def wait_work(r, timeout):
    t_end = time.monotonic() + timeout
    while time.monotonic() < t_end:
        if at_work(actor(r), r):
            time.sleep(.6)   # let the turn to the stop's facing settle
            return True
        time.sleep(.4)
    return False


def shot(name, camera, r=None, extra=None):
    """View a camera (a following resident camera is re-read at this moment), capture, record the walker's state."""
    qa.view(camera)
    time.sleep(.12)
    st = None
    if r:
        a = actor(r)
        st = {'clip': a.get('CurrentClip'), 'position': a.get('position')}
    qa.cmd('capture', name=name, settle=0)
    time.sleep(.35)
    S.report['captures'].append({'png': str(qa.RUN / (name + '.png')), 'camera': camera, 'resident': r and r['name'], 'state': st, **(extra or {})})
    S.save_report()
    return st


def portraits():
    for hour in HOURS:
        S.time_set(hour)
        time.sleep(1.0)
        h = ('%05.2f' % hour).replace('.', '')
        for r in RESIDENTS:
            # a walking resident moves out of a close frame between "view" and the capture: wait until they work
            if not wait_work(r, 120):
                note(f"{r['name']} not at a work stop within 120 s at {hour}; frames taken while walking")
            shot(f"{r['name']}_face_h{h}", f"cam_res_{r['name']}_face", r, {'hour': hour})
            shot(f"{r['name']}_body_h{h}", f"cam_res_{r['name']}_body", r, {'hour': hour})
    S.time_set(13.0)


def sequence(r, approach=3.0, timeout=200):
    """Wait until the resident walks to within `approach` m of the stop, then a frame every 0.5 s until 3 s after leaving."""
    t_end = time.monotonic() + timeout
    last = None
    while time.monotonic() < t_end:
        a = actor(r)
        d = S.dist(a['position'], r['stop'])
        if not at_work(a, r) and d < approach and (last is None or d < last):
            break
        last = d
        time.sleep(.3)
    else:
        ok(False, f"{r['name']} reached the sequence stop within {timeout} s", {'last': last})
        return
    frames, worked, left_at, k = [], False, None, 0
    t0 = time.monotonic()
    while time.monotonic() - t0 < 60 and k < 120:
        tk = time.monotonic()
        st = shot(f"{r['name']}_seq_{k:03d}", r['stop_cam'], r, {'t': round(tk - t0, 2)})
        frames.append(st)
        work = st and st['clip'] and not st['clip'].endswith('_walk')
        worked = worked or work
        if worked and not work and left_at is None:
            left_at = tk
        if left_at and tk - left_at > 3:
            break
        k += 1
        time.sleep(max(0, .5 - (time.monotonic() - tk)))
    ok(worked and left_at is not None, f"{r['name']}: sequence covers the walk in, the stop and the walk out", {'frames': len(frames), 'clips': [f and f['clip'] for f in frames]})


def beside(r, timeout=200):
    qa.view('follow')
    qa.goto('res_' + r['name'])
    time.sleep(.8)
    t_end = time.monotonic() + timeout
    while time.monotonic() < t_end:
        a = actor(r)
        here = S.dist(a['position'], r['main_xz']) < .3 and at_work(a, r) and (r['main_clip'] is None or a['CurrentClip'] == r['main_clip'])
        if here:
            break
        time.sleep(.5)
    else:
        note(f"{r['name']} was not at the main stop within {timeout} s; beside frames taken where they are")
    a = actor(r)
    qa.view('follow')
    qa.face(a['position'][0], a['position'][2])
    qa.pitch(8)
    time.sleep(.6)
    p = qa.pos()
    shot(f"{r['name']}_beside_player", 'follow', r, {'playerDistance': round(S.dist(p, a['position']), 2)})
    shot(f"{r['name']}_beside_eye", f"cam_res_{r['name']}_beside", r)
    qa.view('follow')


def body():
    S.launch(run='run', save=S.kit_save(S.OUT / 'save'))
    S.start()
    S.time_set(13.0)
    # b4 (20 Nov 00:24): reviewHud throws outside a dialogue ("Unobstructed companion captures require an actual active
    # dialogue"), which Player.log then reports; the frames are taken with the HUD on instead.
    names = S.actors()
    ok(all(r['actor'] in names for r in RESIDENTS), 'the three residents are in the build', [r['actor'] for r in RESIDENTS if r['actor'] not in names])
    portraits()
    for r in RESIDENTS:
        sequence(r)
    for r in RESIDENTS:
        beside(r)
    sizes = {}
    for c in S.report['captures']:
        p = c['png']
        try:
            sizes[p.rsplit('/', 1)[-1]] = S.png_stats(p)['size']
        except Exception as e:  # noqa: BLE001
            sizes[p.rsplit('/', 1)[-1]] = 'missing: ' + str(e)[:80]
    ok(sizes and all(v == (1920, 1080) for v in sizes.values()), '%d frames at 1920x1080' % len(sizes), {k: v for k, v in sizes.items() if v != (1920, 1080)})


S.run(body)
