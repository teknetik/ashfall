"""Native real-input check and captures of the 20 Nov 2026 loadout fixes (art/loadout_fix_20261120/README.md).

Carl's playtest notes: the implants page needs an EYE slot; implant and armour leader lines end on the wrong body parts;
a stray "Head" sits under both body maps; hotbar item labels stay on screen and stack up; the hotbar cannot be reordered.

With a fixture save (Warden kit, Neural Targeting Implant in HEAD, medkits, nano cells and a trauma kit) and real X11
keyboard and mouse input this checks:
  1. body maps at 1920x1080, 1280x720, 1440x1080 and 1920x800: every slot's dot lies on the body part its slot names
     (regions measured on the 1024x1536 figure, kept here independently of AnatomyLayout.cs), inside the drawn figure,
     not under a box; boxes do not overlap; the leader (box edge to dot) crosses no other box; the EYE slot exists and
     its empty state says what fits; no bare selection label under the map.
  2. drag labels: hovering a strip cell or a pack tile and moving away leaves none; during a drag there is exactly one;
     Escape, closing the pack mid-drag, and a page change leave none.
  3. hotbar: real mouse drags of strip cell 3 onto 5 (move) and 4 onto 5 (swap); a focused cell and a number key moves
     it; cells 1 and 2 do not move; dragging a pack item still assigns, a key still assigns, right-click and dragging
     off the strip still clear; the HUD hotbar follows; the order is saved and comes back after a restart.
  ATHEN_EXE=<player> ATHEN_OUT=<folder> python unity/tools/capture_loadout_native.py
"""
import json, time
from pathlib import Path
import showcase_qa as S
from showcase_qa import qa, ok, note, cap

# Body-part regions on the 1024 x 1536 figure (x0, y0, x1, y1), measured on a 25 px grid over ImplantBody.png.
REGIONS = {
    'head': [(430, 40, 595, 235)],                 # skull
    'eye': [(465, 110, 505, 150), (520, 110, 562, 150)],
    'arms': [(300, 320, 380, 540), (640, 320, 725, 540)],   # upper arms
    'chest': [(470, 300, 555, 470)],               # sternum
    'wrist': [(205, 700, 265, 760), (760, 700, 820, 760)],
    'waist': [(440, 540, 585, 640)],               # waist / lumbar
    'hand': [(150, 730, 265, 880), (760, 730, 880, 880)],
    'hands': [(150, 730, 265, 880), (760, 730, 880, 880)],
    'legs': [(370, 760, 460, 1060), (570, 760, 660, 1060)],  # thigh to knee
    'feet': [(320, 1340, 470, 1500), (580, 1340, 720, 1500)],
    'storage': [(560, 270, 700, 360), (330, 270, 465, 360)],  # shoulder (pack straps)
}
IMPLANT_SLOTS = ['implant_head', 'implant_eye', 'implant_arms', 'implant_wrist', 'implant_hand', 'implant_chest', 'implant_waist', 'implant_legs', 'implant_feet']
ARMOUR_SLOTS = ['armour_head', 'armour_arms', 'armour_hands', 'armour_chest', 'armour_legs', 'armour_feet', 'storage']


def fixture():
    folder = S.kit_save(S.OUT / 'save', extra_items=[('nano_cell', 3), ('trauma_kit', 1), ('scrap_alloy', 2)])
    path = folder / 'ward-save.json'
    s = json.loads(path.read_text())
    s['character']['equipped'].append({'slot': 'implant_head', 'itemId': 'targeting_implant_mk1'})
    path.write_text(json.dumps(s, indent=1))
    return folder


# ---------------------------------------------------------------- pointer helpers (window pixels)
def panel(layout):
    return (qa.el(layout, 'hud') or {}).get('bounds', [0, 0, layout['width'], layout['height']])


def px(point, layout):
    p = panel(layout)
    return ((point[0] - p[0]) * layout['width'] / p[2], (point[1] - p[1]) * layout['height'] / p[3])


def centre(b):
    return b[0] + b[2] / 2, b[1] + b[3] / 2


def at(layout, name):
    e = qa.el(layout, name)
    if not e or not e.get('visible'):
        raise AssertionError(f'{name} is not visible')
    return px(centre(e['bounds']), layout)


def move(x, y):
    from Xlib import X
    from Xlib.ext import xtest
    d = qa.focus(center=False)
    o = d.screen().root.translate_coords(qa.window(), 0, 0)
    xtest.fake_input(d, X.MotionNotify, x=o.x + int(x), y=o.y + int(y))
    d.sync(); time.sleep(.07)


def park():
    lay = qa.ui()
    move(lay['width'] - 25, 30)
    time.sleep(.3)


def drag(start, end, during=None, release=True):
    move(*start); qa.button(1, True)
    try:
        time.sleep(.15)
        move(start[0] + 12, start[1])
        for step in range(1, 15):
            move(start[0] + (end[0] - start[0]) * step / 14, start[1] + (end[1] - start[1]) * step / 14)
            if step == 9 and during:
                during()
        time.sleep(.12)
    finally:
        if release:
            qa.button(1, False)
    time.sleep(.5)


def press(name, settle=.5):
    """A key press that does not move the pointer (qa.tap re-centres it, which would end a held drag)."""
    qa.key(name, True); time.sleep(.08); qa.key(name, False); time.sleep(settle)


def ghosts(layout=None):
    lay = layout or qa.ui()
    return [e for e in lay['elements'] if e.get('visible') and ('equipment-drag-ghost' in (e.get('classes') or []) or 'tooltip' in (e.get('name') or '').lower())]


def bar():
    return {e['slot']: e.get('item') for e in (S.snap().get('hotbar') or [])}


def hud_cell(layout, slot):
    e = qa.el(layout, f'slot{slot}')
    return None if not e else ('empty' if 'empty-slot' in e['classes'] else 'filled')


# ---------------------------------------------------------------- body map geometry
def inside(p, b, inset=0):
    return b[0] + inset <= p[0] <= b[0] + b[2] - inset and b[1] + inset <= p[1] <= b[1] + b[3] - inset


def cross(a, b, c, d):
    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    d1, d2, d3, d4 = o(c, d, a), o(c, d, b), o(a, b, c), o(a, b, d)
    return ((d1 > 0 > d2) or (d1 < 0 < d2)) and ((d3 > 0 > d4) or (d3 < 0 < d4))


def enters(a, b, box, inset=1.0):
    x0, y0, x1, y1 = box[0] + inset, box[1] + inset, box[0] + box[2] - inset, box[1] + box[3] - inset
    if x0 <= a[0] <= x1 and y0 <= a[1] <= y1 or x0 <= b[0] <= x1 and y0 <= b[1] <= y1:
        return True
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return any(cross(a, b, corners[i], corners[(i + 1) % 4]) for i in range(4))


def body_map(tag, slots, size):
    lay = qa.ui()
    img = qa.el(lay, 'anatomy-image')
    ok(img and img['visible'], f'{tag}: the figure is shown', img and img['bounds'])
    ib = img['bounds']
    ok(abs(ib[2] / ib[3] - 1024 / 1536) < .01, f'{tag}: the figure keeps its proportions', ib)
    boxes, wrong, info = {}, [], {}
    for sid in slots:
        cell, node = qa.el(lay, 'equipment-' + sid), qa.el(lay, 'anatomy-node-' + sid)
        if not (cell and cell['visible'] and node and node['visible']):
            wrong.append((sid, 'missing'))
            continue
        boxes[sid] = cell['bounds']
        n = centre(node['bounds'])
        u, v = (n[0] - ib[0]) / ib[2] * 1024, (n[1] - ib[1]) / ib[3] * 1536
        part = sid.split('_', 1)[1] if '_' in sid else sid
        on = any(x0 <= u <= x1 and y0 <= v <= y1 for x0, y0, x1, y1 in REGIONS[part])
        info[sid] = {'image_px': [round(u), round(v)], 'on': on}
        if not on:
            wrong.append((sid, 'off ' + part, [round(u), round(v)]))
        if not inside(n, ib):
            wrong.append((sid, 'dot outside the figure'))
        # leader: from the box edge facing the figure (the side nearer the dot) at the box's middle height
        b = cell['bounds']
        start = (b[0] + b[2], b[1] + b[3] / 2) if n[0] > b[0] + b[2] / 2 else (b[0], b[1] + b[3] / 2)
        info[sid]['leader'] = [start, n]
    ok(not wrong, f'{tag}: every dot sits on the body part its slot names', {'wrong': wrong, 'dots': {k: v['image_px'] for k, v in info.items()}})
    clashes = []
    for a in boxes:
        n = info[a]['leader'][1]
        for b in boxes:
            if a == b:
                continue
            if inside(n, boxes[b], 1):
                clashes.append((a, 'dot under', b))
            if enters(*info[a]['leader'], boxes[b]):
                clashes.append((a, 'leader through', b))
            ba, bb = boxes[a], boxes[b]
            if a < b and ba[0] < bb[0] + bb[2] - 1 and bb[0] < ba[0] + ba[2] - 1 and ba[1] < bb[1] + bb[3] - 1 and bb[1] < ba[1] + ba[3] - 1:
                clashes.append((a, 'box overlaps', b))
            if a < b and cross(*info[a]['leader'], *info[b]['leader']):
                clashes.append((a, 'leader crosses', b))
    ok(not clashes, f'{tag}: no box overlaps another, no leader crosses a box or another leader', clashes)
    sel = qa.el(lay, 'equipment-selection')
    ok(not (sel and sel['visible']), f'{tag}: no bare slot name under the body map', sel and sel.get('text'))
    report = S.report.setdefault('bodyMaps', {})
    report[tag] = {'size': size, 'image': ib, 'slots': info}
    return lay


def open_pack():
    if qa.state() != 'Inventory':
        qa.tap('Tab', settle=.8)
    qa.wait(lambda: qa.state() == 'Inventory', 5, what='pack open')


def click(name):
    lay = qa.ui()
    qa.click_at(*at(lay, name))
    time.sleep(.35)


def maps(size):
    w, h = size
    tag = f'{w}x{h}'
    click('character-tab-implants')
    lay = body_map('implants ' + tag, IMPLANT_SLOTS, size)
    cap(f'implants-{tag}')
    click('character-tab-armour')
    body_map('armour ' + tag, ARMOUR_SLOTS, size)
    cap(f'armour-{tag}')


def body():
    save = fixture()
    S.launch(save=save)
    S.start()
    S.time_set(13)
    open_pack()
    S.note('fixture', {'hotbar': bar()})
    ok(bar().get(3) == 'medkit' and bar().get(4) == 'nano_cell', 'fixture: medkit on 3, nano cell on 4 (defaults)', bar())

    # ---- 1. body maps at 1920x1080
    maps((1920, 1080))
    click('character-tab-implants')
    click('equipment-implant_eye')
    lay = qa.ui()
    eye = qa.el(lay, 'equipment-implant_eye')
    texts = ' '.join((e.get('text') or '') for e in lay['elements'] if e.get('visible'))
    ok(eye and eye['visible'] and 'fits the eye slot' in texts, 'the EYE slot is on the implants page and its empty state says what fits', {'eye': eye and eye['bounds']})
    head = qa.el(lay, 'equipment-implant_head')
    ok(head and 'Neural' in json.dumps(lay), 'the Neural Targeting Implant stays in HEAD')
    cap('implants-eye-selected-1920x1080')
    click('equipment-implant_head')
    cap('implants-head-selected-1920x1080')

    # ---- 2. drag labels
    park()
    move(*at(qa.ui(), 'packbar-slot3')); time.sleep(.8)
    ok(not ghosts(), 'hovering hotbar cell 3 shows no floating label', ghosts())
    park(); ok(not ghosts(), 'moving away from the cell leaves no label')
    move(*at(qa.ui(), 'inv-medkit')); time.sleep(.8); park()
    ok(not ghosts(), 'hovering a pack tile and moving away leaves no label', ghosts())
    counts = []
    lay = qa.ui()
    drag(at(lay, 'inv-nano_cell'), at(lay, 'equipment-implant_arms'), during=lambda: (counts.append(len(ghosts())), cap('drag-in-progress')), release=False)
    press('Escape', .4)
    qa.button(1, False); time.sleep(.4)
    ok(counts == [1], 'exactly one drag label while dragging', counts)
    if qa.state() != 'Inventory':
        open_pack()
    ok(not ghosts(), 'Escape mid-drag leaves no label', ghosts())
    lay = qa.ui()
    drag(at(lay, 'packbar-slot4'), at(lay, 'inv-scrap_alloy'), during=lambda: press('Tab', .5), release=True)
    ok(qa.state() == 'Play' and bar().get(4) == 'nano_cell', 'Tab closes the pack mid-drag and nothing changes', {'state': qa.state(), 'bar': bar()})
    ok(not ghosts(), 'closing the pack mid-drag leaves no label in play', ghosts())
    open_pack()
    ok(not ghosts(), 'reopening the pack shows no stale label')
    click('character-tab-secondary'); click('character-tab-armour')
    ok(not ghosts(), 'page changes leave no label')

    # ---- 3. hotbar reordering with the real mouse
    lay = qa.ui()
    drag(at(lay, 'packbar-slot3'), at(lay, 'packbar-slot5'))
    b = bar(); lay = qa.ui()
    ok(b.get(5) == 'medkit' and b.get(3) is None and b.get(4) == 'nano_cell', 'dragging strip cell 3 onto 5 moves the medkit', b)
    ok(hud_cell(lay, 5) == 'filled' and hud_cell(lay, 3) == 'empty', 'the HUD hotbar follows (3 empty, 5 medkit)', {'3': hud_cell(lay, 3), '5': hud_cell(lay, 5)})
    ok(not ghosts(lay), 'no label left after the drop', ghosts(lay))
    cap('hotbar-3-onto-5')
    drag(at(lay, 'packbar-slot4'), at(lay, 'packbar-slot5'))
    b = bar()
    ok(b.get(4) == 'medkit' and b.get(5) == 'nano_cell', 'dragging 4 onto 5 swaps them', b)
    lay = qa.ui()
    drag(at(lay, 'packbar-slot1'), at(lay, 'packbar-slot6'))
    ok(bar() == b and not ghosts(), 'cell 1 (primary weapon) does not drag', bar())
    drag(at(lay, 'packbar-slot5'), at(lay, 'packbar-slot2'))
    ok(bar() == b, 'a cell dropped on 2 (sidearm) stays where it was', {'bar': bar(), 'notice': S.snap()['session']['notice']})
    # keyboard: focus cell 5 with a click, press 7
    click('packbar-slot5'); qa.tap('7', settle=.5)
    b = bar()
    ok(b.get(7) == 'nano_cell' and b.get(5) is None, 'a focused strip cell and the 7 key move the nano cell to 7', {'bar': b, 'focused': S.snap()['session']['focused']})
    # assignment as before
    lay = qa.ui()
    drag(at(lay, 'inv-trauma_kit'), at(lay, 'packbar-slot10'))
    ok(bar().get(10) == 'trauma_kit', 'dragging a pack item onto cell 0 still assigns it', bar())
    click('inv-medkit'); qa.tap('8', settle=.5)
    ok(bar().get(8) == 'medkit' and bar().get(4) is None, 'selecting the medkit and pressing 8 still assigns (moves) it', bar())
    lay = qa.ui()
    qa.click_at(*at(lay, 'packbar-slot10'), b=3); time.sleep(.4)
    ok(bar().get(10) is None, 'right-click still clears a cell', bar())
    lay = qa.ui()
    drag(at(lay, 'packbar-slot7'), at(lay, 'inv-scrap_alloy'))
    ok(bar().get(7) is None, 'dragging a cell off the strip still clears it', bar())
    drag(at(qa.ui(), 'inv-nano_cell'), at(qa.ui(), 'packbar-slot6'))
    final = {k: v for k, v in bar().items() if v and int(k) >= 3}
    ok(final == {6: 'nano_cell', 8: 'medkit'}, 'final order: nano cell on 6, medkit on 8', final)
    lay = qa.ui()
    help_text = (qa.el(lay, 'pack-hotbar-help') or {}).get('text') or ''
    ok('reorder' in help_text and '1 and 2' in help_text, 'the strip help line says what can be done', help_text)
    ok(not ghosts(lay), 'no label left after all strip work', ghosts(lay))
    cap('hotbar-final-order')
    qa.tap('Escape', settle=.6)
    lay = qa.ui()
    ok(hud_cell(lay, 6) == 'filled' and hud_cell(lay, 8) == 'filled' and hud_cell(lay, 3) == 'empty' and hud_cell(lay, 4) == 'empty', 'the HUD hotbar shows 6 and 8 filled, 3 and 4 empty',
       {s: hud_cell(lay, s) for s in (3, 4, 5, 6, 7, 8, 10)})
    S.report['finalOrder'] = final

    # ---- 1b. body maps at other window sizes (the panel scales with the window; other aspect ratios change its shape)
    for size in [(1280, 720), (1440, 1080), (1920, 800)]:
        qa.cmd('resize', width=size[0], height=size[1]); qa.PARK = (size[0] - 25, 25); time.sleep(1.5)
        open_pack()
        maps(size)
        qa.tap('Tab', settle=.6)
    qa.cmd('resize', width=1920, height=1080); qa.PARK = None; time.sleep(1.2)

    # ---- restart: the order survives
    errs = [e['text'][:200] for e in S.errors() if 'Exception' in e['text'] or 'NullReference' in e['text']]
    ok(not errs, 'no runtime exceptions in the first run', errs[:8])
    S.stop()
    saved = json.loads((save / 'ward-save.json').read_text())
    hb = {e['slot']: e['itemId'] for e in saved.get('hotbar') or []}
    ok(saved.get('version') == 4 and hb == {6: 'nano_cell', 8: 'medkit'}, 'the save (v4) records the new order', saved.get('hotbar'))
    S.launch('run2', save=save)
    S.start()
    final2 = {k: v for k, v in bar().items() if v and int(k) >= 3}
    ok(final2 == final, 'after a restart and Continue the hotbar order is the same', final2)
    lay = qa.ui()
    ok(hud_cell(lay, 6) == 'filled' and hud_cell(lay, 8) == 'filled' and hud_cell(lay, 3) == 'empty', 'the HUD hotbar shows it after the restart')
    cap('hud-after-restart', layout=False)


S.run(body)
