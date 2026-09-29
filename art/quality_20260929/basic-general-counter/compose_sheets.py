"""Compose old|new side-by-side sheets and a contact sheet from the review renders (Blender + numpy only, no PIL).

    sh bl.sh --python compose_sheets.py
Outputs renders/compare_<view>.png (old left, new right) and renders/contact_sheet_new.png (3 x 3, labelled by order in README).
"""
import bpy, numpy as np
from pathlib import Path

R = Path('/home/teknetik/code/ao2/art/quality_20260929/basic-general-counter/renders')


def load(p):
    im = bpy.data.images.load(str(p), check_existing=False)
    w, h = im.size
    a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(im)
    return a


def save(a, p):
    h, w = a.shape[:2]
    im = bpy.data.images.new('tmp', w, h, alpha=True)
    im.pixels.foreach_set(a.reshape(-1))
    im.filepath_raw = str(p)
    im.file_format = 'PNG'
    im.save()
    bpy.data.images.remove(im)


def down(a, f):
    h, w = a.shape[:2]
    h2, w2 = h // f, w // f
    return a[:h2 * f, :w2 * f].reshape(h2, f, w2, f, 4).mean(axis=(1, 3))


pairs = [('door', 'old_door', 'new_door'), ('door_mira', 'old_door_mira', 'new_door_mira'), ('eye_approach', 'old_eye_approach', 'new_eye_approach'),
         ('eye_porch_left', 'old_eye_porch_left', 'new_eye_porch_left'), ('eye_porch_right', 'old_eye_porch_right', 'new_eye_porch_right'),
         ('over_counter', 'old_over_counter', 'new_over_counter')]
bar = np.zeros((1200, 16, 4), np.float32); bar[..., 3] = 1
bar[..., 0] = .9; bar[..., 1] = .75; bar[..., 2] = .2
for name, o, n in pairs:
    if (R / f'{o}.png').exists() and (R / f'{n}.png').exists():
        save(np.concatenate([load(R / f'{o}.png'), bar, load(R / f'{n}.png')], axis=1), R / f'compare_{name}.png')
        print('compare', name)
sel = ['new_lit_eye_approach', 'new_eye_porch_left', 'new_eye_porch_right', 'new_close_left_bay', 'new_close_right_bay', 'new_close_hooks',
       'new_close_counter_face', 'new_close_counter_top', 'new_close_material_steel']
tiles = [down(load(R / f'{s}.png'), 2) for s in sel if (R / f'{s}.png').exists()]
rows = [np.concatenate(tiles[i:i + 3], axis=1) for i in range(0, len(tiles) - len(tiles) % 3, 3)]
save(np.concatenate(rows, axis=0), R / 'contact_sheet_new.png')
print('contact', len(tiles))
