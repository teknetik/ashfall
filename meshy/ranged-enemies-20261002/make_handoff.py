#!/usr/bin/env python3
"""Compose handoff.json for the gameplay prefabs from the Unity verify evidence
(unity/evidence/ranged-enemies/20261002/verify.json + import.json), the build records (gunner/build/build.json,
lancer/proc/lancer.json) and the walk/run stride speeds measured on the clip GLBs (planted-toe slide speed, numpy FK).
Usage: python3 make_handoff.py"""
import json, math
from pathlib import Path
import numpy as np
from gltf_io import GLB, world

HERE = Path(__file__).parent
EV = HERE.parents[1] / 'unity/evidence/ranged-enemies/20261002'
verify = json.loads((EV / 'verify.json').read_text()); imp = json.loads((EV / 'import.json').read_text())
build = json.loads((HERE / 'gunner/build/build.json').read_text()); lancer = json.loads((HERE / 'lancer/proc/lancer.json').read_text())
G, L = verify['gunner'], verify['lancer']
scale = G['visualScale'][0]


def stride_speed(name):
    """Native ground speed of an in-place locomotion clip: how fast the planted (lower) toe slides backward."""
    g = GLB(HERE / 'gunner/build/clips' / f'{name}.glb'); an = g.j['animations'][0]
    ch = {}
    for c in an['channels']:
        s = an['samplers'][c['sampler']]; ch[(c['target']['node'], c['target']['path'])] = (g.acc(s['input']), g.acc(s['output']))
    t = next(iter(ch.values()))[0]
    toes = [g.node_index('LeftToeBase'), g.node_index('RightToeBase')]
    P = []
    for k in range(len(t)):
        rot = {n: v[k] for (n, p), (tt, v) in ch.items() if p == 'rotation'}
        tr = {n: v[k] for (n, p), (tt, v) in ch.items() if p == 'translation'}
        P.append([world(g, i, rot, tr)[0] for i in toes])
    P = np.array(P)                       # frames x 2 x 3, metres, model faces +Z
    low = P[:, :, 1].argmin(1); y = P[np.arange(len(P)), low, 1]; z = P[np.arange(len(P)), low, 2]
    dt = float(t[1] - t[0]); v = -(np.diff(z) / dt)
    planted = (y[:-1] < y.min() + .03) & (low[:-1] == low[1:])
    return round(float(np.median(v[planted])) * scale, 3) if planted.any() else None


clips = G['clips']
shots = build['shot_times']
gun_clip_notes = {c: build['clips'][c]['note'] for c in build['clips']}
handoff = {
    'generated': 'make_handoff.py from unity/evidence/ranged-enemies/20261002/verify.json (Unity batch verify, 0 failures)',
    'editor_script': 'unity/AthenHill/Assets/AthenHill/Editor/OuterBermsRangedEnemies.cs (RunBatch --steps import,prefab,verify)',
    'feral_gunner': {
        'prefab': G['prefab'], 'guid': G['guid'], 'model': G['model'],
        'structure': 'FeralGunnerVisual (origin at the feet, faces +Z, unscaled) > Visual (uniform scale %.4f; the legacy Animation lives here) > '
                     'Armature (glTFast instance of the model, renamed so the clip paths Armature/Hips/... resolve) > char1 (SkinnedMeshRenderer, body) + Hips/... bones; '
                     'the forearm gun is a MeshRenderer node ForearmGun under the RightForeArm bone, with Muzzle under it.' % scale,
        'standing_height_m': G['standingHeight'], 'faces_plus_z': G['facesPlusZ'],
        'animation': dict(host_path=G['animationHostPath'], **G['animation']),
        'clips': {n: dict(length_s=c['length'], wrap=c['wrap'], sole_at_frame0=c['soleAtFrame0'], height_at_frame0=c['heightAtFrame0'],
                          note=gun_clip_notes.get(n)) for n, c in clips.items()},
        'shot_times_s': shots, 'shot_normalized_time': {k: round(v / clips[k]['length'], 3) for k, v in shots.items()},
        'locomotion_native_speeds_mps': {'walk': stride_speed('walk'), 'run': stride_speed('run'),
                                         'strafe_left': build['clips']['strafe_left']['native_speed_mps'], 'strafe_right': build['clips']['strafe_right']['native_speed_mps']},
        'muzzle': dict(path=G['muzzle']['path'], parent=G['muzzle']['parent'], local_position=G['muzzle']['localPosition'], local_rotation_xyzw=G['muzzle']['localRotation'],
                       relative_to_RightForeArm=G['muzzle']['relativeToRightForeArm'], plus_z_out_of_barrel=True,
                       aim_pose_prefab_space=G['muzzle']['aimPose'], fire_recoil_peak=G['muzzle']['fireRecoilPeak'],
                       note='Muzzle is 1 cm ahead of the bore on the gun, which is rigidly parented to the RightForeArm bone (gun local scale 100 cancels the '
                            'centimetre armature). In aim/fire/strafe clips the barrel points along the prefab +Z, level, at about 1.65 m height and 0.98 m ahead; '
                            'in idle/walk/run it follows the arm.'),
        'gun': G['gun'],
        'optic': dict(renderer_path=G['opticRenderer'], material='Assets/AthenHill/Art/OuterBerms/Ranged/Materials/FR_FeralGunner.mat',
                      emission='optics-only emission map (FeralGunner_Emission.png): drive _EmissionColor on this renderer (glowRenderers = [char1])',
                      optic_rest_position_prefab=[0.003, 1.80, 0.109], head_bone=G['headBone'],
                      suggested_glow=dict(calm=[1.1, .45, .1], hostile=[3.2, 1.0, .2], windup=[8, 4.6, 2]),
                      eye_light_note='parent an eye light to the Head bone, ~0.1 m in front of the optic, pointing forward'),
        'toe_bones': G['toeBones'],
        'skinned_renderer': dict(path=G['body']['path'], root_bone=G['body']['rootBone'], local_bounds_cm_in_root_bone_space=G['body']['localBounds'],
                                 bounds_cover_all_clips=G['body']['boundsCoverAllClips'], update_when_offscreen=G['body']['updateWhenOffscreen'],
                                 note='localBounds = the skinned envelope over all ten clips + 12 % per side; the gun has its own MeshRenderer bounds'),
        'triangles': dict(body=G['body']['triangles'], gun=G['gun']['triangles'], total=G['body']['triangles'] + G['gun']['triangles']),
        'materials': [m for m in imp['import']['materials'] if 'Gunner' in m['name']],
        'recommended_FeralDroid_wiring': dict(kind='Walker', animationSource=G['animationHostPath'] + ' (Animation)', idle='idle', walk='walk', run='run',
                                               attack='fire (with fireClipPerShot = true: one recoil per bolt, shot at 0.05 s) or fire_raise (single shot at 0.55 s, normalized 0.458) without an aim wind-up',
                                               aim='aim', strafeLeft='strafe_left', strafeRight='strafe_right', hit='hit', death='death', muzzle='Muzzle',
                                               glowRenderers='[char1]', feet='[LeftToeBase, RightToeBase]'),
    },
    'feral_lancer': {
        'prefab': L['prefab'], 'guid': L['guid'], 'model': L['model'],
        'structure': 'FeralLancerVisual (origin at the centre of lift = rotor hubs\' centroid, at the hull mid-height; faces +Z) > Visual (glTFast instance of the model) > '
                     'Body, Rotor A..D (each with a Blur disc child), Lens cap, Muzzle. No skinning, no animation.',
        'size_m': L['span'], 'faces_plus_z': True,
        'rotors': L['rotors'], 'rotor_layout': 'A front-left, B front-right, C rear-left, D rear-right (Unity: left = -X)',
        'recommended_rotor_order': ['Rotor A', 'Rotor B', 'Rotor D', 'Rotor C'],
        'rotor_order_note': 'FeralDroid counter-rotates alternate rotors by index; [A, B, D, C] spins the diagonal pairs A/D and B/C the same way, matching the blade hands',
        'blur_discs': 'RB_RotorBlur.mat on RB_RotorDisc (shared with the scrap drone), scaled to each blade radius x 1.02, 5 mm above the hub, shadows off',
        'muzzle': dict(L['muzzle'], plus_z_out_of_barrel=True),
        'lens_cap': L['lensCap'],
        'eye': dict(glow_renderer=L['lensCap']['path'], suggested_glow=dict(calm=[1.2, .32, .07], hostile=[3.6, .9, .15], windup=[8, 2.6, .6]),
                    eye_light_note='a forward spot ~0.1 m in front of the lens cap (prefab z ~1.03, y ~0.1), like the scrap drone'),
        'body': dict(path=L['body']['path'], triangles=L['body']['triangles']),
        'triangles_total': L['totalTriangles'],
        'materials': [m for m in imp['import']['materials'] if 'Lancer' in m['name']],
        'recommended_FeralDroid_wiring': dict(kind='Hover', rotors='[Rotor A, Rotor B, Rotor D, Rotor C]', muzzle='Muzzle', glowRenderers='[Lens cap]',
                                               note='hoverHeight: the hull is 0.67 m tall and the lance hangs 0.24 m below the origin (lowest point about -0.33 m)'),
    },
    'known_defects': {
        'gunner': ['three-fingered claw hands with partly fused fingers, no finger bones (Meshy auto-rig)',
                   'a few small inner shell faces are back-facing: pin-holes at close range with back-face culling',
                   'run: the gun passes within 1.5 cm of the thigh/torso for a few frames; aim/fire_raise brush the torso armour when the alert idle leans',
                   'death: the barrel rests on the ground at the end',
                   'strap bands carry a stretched patch of the gun texture',
                   'no LOD: 86.6k body + 33.4k gun triangles'],
        'lancer': ['the lower inner lip of each duct keeps a ragged, toothed edge (visible from below at close range)',
                   'front ducts slightly smaller than the rear pair (as generated)',
                   'authored rotor blades are plain twisted plates on a small dark-steel UV patch',
                   'no LOD: 64.6k body triangles'],
    },
}
(HERE / 'handoff.json').write_text(json.dumps(handoff, indent=1)); print(json.dumps(handoff['feral_gunner']['locomotion_native_speeds_mps']))
