#!/usr/bin/env python3
"""Offline poses of the installed Steady Hands bench prefab (no Unity): where marks, places and tool axes really point.

    python3 prefab_pose.py            # the report used for the 22 Nov 2026 playtest fixes

Everything is in the bench surface's frame: +x right, +y up, +z towards the player."""
import re
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PREFAB = ROOT / 'unity/AthenHill/Assets/AthenHill/Data/Assembly/SteadyHandsBench.prefab'
NUM = r'(-?[\d.]+(?:[eE]-?\d+)?)'


def vec(body, key, axes='xyz'):
    m = re.search(key + r': \{' + ', '.join(f'{a}: {NUM}' for a in axes) + r'\}', body)
    return np.array([float(v) for v in m.groups()]) if m else None


def rot(q):
    x, y, z, w = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])


def ref(body, key):
    m = re.search(r'\b' + key + r': \{fileID: (\d+)', body)
    return m.group(1) if m else None


class Bench:
    def __init__(self, path=PREFAB):
        self.tf, self.name, self.part, self.marker, go_tf, behaviours = {}, {}, {}, {}, {}, []
        for doc in path.read_text().split('\n--- !u!')[1:]:
            head, body = doc.split('\n', 1)
            kind, fid = head.split(' &')
            fid = fid.split()[0]
            if kind == '1':
                self.name[fid] = re.search(r'm_Name: (.*)', body).group(1)
            elif kind == '4':
                self.tf[fid] = (vec(body, 'm_LocalPosition'), rot(vec(body, 'm_LocalRotation', 'xyzw')),
                                vec(body, 'm_LocalScale'), ref(body, 'm_Father'))
                go_tf[ref(body, 'm_GameObject')] = fid
            elif kind == '114':
                behaviours.append(body)
        for body in behaviours:
            t = go_tf.get(ref(body, 'm_GameObject'))
            found = re.search(r'\n  id: (\S+)', body)
            if found and '::AthenHill.AssemblyPart\n' in body:
                self.part[found.group(1)] = dict(t=t, body=body, tip=ref(body, 'tip'), grab=ref(body, 'grab'))
            elif found and '::AthenHill.AssemblyMarker\n' in body:
                self.marker[found.group(1)] = dict(t=t, body=body)
            if '::AthenHill.AssemblyBench\n' in body:
                self.surface = ref(body, 'surface')
        self.by_name = {self.name.get(g): t for g, t in go_tf.items()}
        self.frame = np.linalg.inv(self.raw(self.surface))

    def raw(self, t, moved=None):
        if not t or t == '0' or t not in self.tf:
            return np.eye(4)
        if moved and t in moved:
            return moved[t]
        p, r, s, up = self.tf[t]
        m = np.eye(4)
        m[:3, :3], m[:3, 3] = r @ np.diag(s), p
        return self.raw(up, moved) @ m

    def pose(self, t, moved=None):
        return self.frame @ self.raw(t, moved)

    def seated(self, part, place):
        """`moved` overrides that put a part at a place, as AssemblyBench.Put does."""
        return {self.part[part]['t']: self.raw(self.marker[place]['t'])}


def unit(v):
    return v / np.linalg.norm(v)


if __name__ == '__main__':
    b = Bench()
    show = lambda v: np.array2string(v, precision=3, suppress_small=True)
    clamp = b.seated('pistol.frame', 'fixtures.vise/seat_work')
    crack = b.pose(b.marker['pistol.frame/crack']['t'], clamp)
    print('crack at', show(crack[:3, 3]))
    print('  +Z (what Reveal tests)', show(unit(crack[:3, 2])))
    print('  +Y (out of the face)  ', show(unit(crack[:3, 1])))
    cam = b.pose(b.by_name['cam_bench_vise'])[:3, 3]
    axis = b.pose(b.part['fixtures.vise']['t'])[:3, 3]
    print('  camera', show(cam), 'swivel axis', show(axis))
    print('  yaw   old test(+Z)   face(+Y)')
    for deg in range(0, 360, 15):
        c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
        r = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
        at = axis + r @ (crack[:3, 3] - axis)
        eye = unit(cam - at)
        print(f'  {deg:4d}   {unit(r @ crack[:3, 2]) @ eye:8.3f}   {unit(r @ crack[:3, 1]) @ eye:8.3f}')
    print('tools: cosine between the tip axis and the tool length (grab to tip)')
    for pid, p in sorted(b.part.items()):
        if not pid.startswith('tools.') or p['tip'] in (None, '0') or p['grab'] in (None, '0'):
            continue
        tip, grab = b.pose(p['tip']), b.pose(p['grab'])
        length = unit(tip[:3, 3] - grab[:3, 3])
        print(f'  {pid:22s} +Z {unit(tip[:3, 2]) @ length:6.3f}   +Y {unit(tip[:3, 1]) @ length:6.3f}')
    pin = b.part['pistol.housing_pin']
    moved = dict(clamp)
    mark = b.pose(b.marker['pistol.housing_pin/punch']['t'], moved)
    stood = dict(clamp)
    stood[b.part['tools.punch']['t']] = np.linalg.inv(b.frame) @ mark
    tip, grab = b.pose(b.part['tools.punch']['tip'], stood), b.pose(b.part['tools.punch']['grab'], stood)
    print('pin end', show(mark[:3, 3]), 'punch length on it', show(unit(tip[:3, 3] - grab[:3, 3])),
          'pin axis', show(unit(b.pose(pin['t'], clamp)[:3, 1])))
    print('mallet drives along (0,-1,0) today')
    anvil = b.pose(b.marker['fixtures.vise/anvil']['t'])
    print('anvil +Y', show(unit(anvil[:3, 1])))
    for pl in ('fixtures.pad', 'fixtures.partsmat', 'fixtures.workmat'):
        print(pl, show(b.pose(b.part[pl]['t'])[:3, 3]))
