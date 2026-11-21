# kit/rig.py: 0-1 parameter rigs in the AnyMachine form (ANYMACHINE.md section 2; after laptop/scripts/build.py and
# export.py in the AnyMachine repository, MIT, read and rewritten).
#
#   R = RG.Rig('pistol', parent=frame_obj)                 # armature '<family>_rig' with a 'root' bone
#   R.hinge('cell_latch', origin, axis, 0, 22, [latch])    # degrees about `axis` through `origin` (right-hand turn)
#   R.slide('cell_seat', origin, axis, 0, 0.018, [cell], requires={'cell_latch': 1.0})    # metres along `axis`
#   R.continuous('rotor', origin, axis, [rotor], parent='gimbal_roll')                    # code-driven, no clip
#   R.finish()                                             # properties, drivers, limits, bone parenting, extras
#   ... save the .blend (check.py sweeps the DRIVEN rig) ...
#   R.bake_actions()                                       # just before export: drivers -> '<param>_param' actions
#
# A joint is as modelled when its bone is unposed: that is parameter 0 for a range that starts at 0, and the middle
# for one that swings both ways; parts.json gives it as `rest` per parameter (SEAM.md section 7).
# Each parameter is a custom property 0-1 on the armature object, named as the parameter. The bone lies on the joint
# axis (bone +Y = axis), carries a Limit constraint so values outside 0-1 clamp, and every rigid part is bone-parented
# to exactly one bone. '<param>_param' is linear and one second long at 24 fps: sample it at t = value.
# The joint specs ride on the armature node as glTF extras ('anymachine') and are written to parts.json ('params').
import bpy, json, math
from mathutils import Vector, Matrix

FPS = 24


class Rig:
    def __init__(self, family, parent=None, name=None):
        self.family = family
        self.name = name or family + '_rig'
        ad = bpy.data.armatures.new(self.name)
        self.arm = bpy.data.objects.new(self.name, ad)
        bpy.context.scene.collection.objects.link(self.arm)
        self.arm.show_in_front = True
        self.joints = []
        self.logical_parent = parent
        self._edit(lambda eb: self._bone(eb, 'root', Vector((0, 0, 0)), Vector((0, 0.01, 0)), None))

    # ------------------------------------------------------------------ internals
    def _edit(self, fn):
        vl = bpy.context.view_layer
        for o in bpy.context.scene.objects:
            o.select_set(False)
        vl.objects.active = self.arm
        self.arm.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        fn(self.arm.data.edit_bones)
        bpy.ops.object.mode_set(mode='OBJECT')

    def _bone(self, eb, name, head, tail, parent, ref=None):
        b = eb.new(name)
        b.head = head; b.tail = tail
        if ref is not None:
            b.align_roll(Vector(ref))
        if parent:
            b.parent = eb[parent]
        b.use_connect = False
        return b

    def _add(self, kind, param, origin, axis, lo, hi, parts, parent, requires, unit, length=0.02):
        origin = Vector(origin); ax = Vector(axis).normalized()
        ref = Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))
        self._edit(lambda eb: self._bone(eb, param, origin, origin + ax * length, parent or 'root', ref))
        # the parameter value at which the joint is as modelled (bone unposed): 0 when the range starts at 0, the
        # middle for a joint that swings both ways (-12..+12 degrees rests at 0.5)
        rest = 0.0 if (kind == 'continuous' or hi == lo or not (min(lo, hi) < 0.0 < max(lo, hi))) else (0.0 - lo) / (hi - lo)
        self.joints.append({'param': param, 'type': kind, 'bone': param, 'min': lo, 'max': hi, 'unit': unit, 'rest': rest,
                            'continuous': kind == 'continuous', 'parent_bone': parent or 'root',
                            'requires': requires or {}, 'parts': [o.name for o in parts],
                            'origin': [round(x, 6) for x in origin], 'axis': [round(x, 6) for x in ax]})
        self._parts = getattr(self, '_parts', {})
        self._parts[param] = list(parts)

    # ------------------------------------------------------------------ joints
    def hinge(self, param, origin, axis, min_deg, max_deg, parts, parent=None, requires=None):
        """Turn about `axis` through `origin`; the parameter 0..1 maps to min_deg..max_deg (right-hand rule)."""
        self._add('hinge', param, origin, axis, float(min_deg), float(max_deg), parts, parent, requires, 'deg')

    def slide(self, param, origin, axis, min_m, max_m, parts, parent=None, requires=None):
        """Travel along `axis`; the parameter 0..1 maps to min_m..max_m metres (written to JSON in millimetres)."""
        self._add('slide', param, origin, axis, float(min_m), float(max_m), parts, parent, requires, 'm')

    def continuous(self, param, origin, axis, parts, parent=None):
        """A free turn (rotor, crank, screw): driven by code from a turn count, so it gets a bone and extras, no clip."""
        self._add('continuous', param, origin, axis, 0.0, 360.0, parts, parent, None, 'deg')

    # ------------------------------------------------------------------ finish
    def finish(self):
        arm = self.arm
        vl = bpy.context.view_layer
        vl.update()
        for j in self.joints:
            pb = arm.pose.bones[j['bone']]
            pb.rotation_mode = 'XYZ'
            if j['continuous']:
                continue
            arm[j['param']] = float(j['rest'])       # parts are parented below with every joint at its rest
            ui = arm.id_properties_ui(j['param'])
            ui.update(min=0.0, max=1.0, soft_min=0.0, soft_max=1.0, description='0-1 parameter (%s)' % j['type'])
            if j['type'] == 'hinge':
                lo, hi = math.radians(j['min']), math.radians(j['max'])
                c = pb.constraints.new('LIMIT_ROTATION'); c.owner_space = 'LOCAL'
                c.use_limit_x = c.use_limit_y = c.use_limit_z = True
                c.min_y, c.max_y = min(lo, hi), max(lo, hi)
                fc = pb.driver_add('rotation_euler', 1)
            else:
                lo, hi = j['min'], j['max']
                c = pb.constraints.new('LIMIT_LOCATION'); c.owner_space = 'LOCAL'
                c.use_min_x = c.use_max_x = c.use_min_y = c.use_max_y = c.use_min_z = c.use_max_z = True
                c.min_y, c.max_y = min(lo, hi), max(lo, hi)
                fc = pb.driver_add('location', 1)
            d = fc.driver; d.type = 'SCRIPTED'
            v = d.variables.new(); v.name = 'p'; v.type = 'SINGLE_PROP'
            v.targets[0].id = arm; v.targets[0].data_path = '["%s"]' % j['param']
            d.expression = '%.8f + p * %.8f' % (lo, hi - lo)
        # rigid parts: each to exactly one bone, keeping its world pose. The drivers are live and every parameter is
        # at its rest, so the bones are unposed: the modelled pose is the GLB's rest pose (before 18:20 on 20 Nov the
        # parameters stood at 0 here, which was wrong for a joint whose range does not start at 0).
        arm.update_tag()
        bpy.context.scene.frame_set(bpy.context.scene.frame_current)
        vl.update()
        seen = {}
        for j in self.joints:
            for o in self._parts[j['param']]:
                if o.name in seen:
                    raise ValueError('%s is on two bones (%s and %s)' % (o.name, seen[o.name], j['bone']))
                seen[o.name] = j['bone']
                vl.update()
                mw = o.matrix_world.copy()
                o.parent = arm; o.parent_type = 'BONE'; o.parent_bone = j['bone']
                vl.update()
                o.matrix_world = mw
                if 'sh' in o:
                    dd = json.loads(o['sh']); dd['rides'] = j['param']; o['sh'] = json.dumps(dd)
        if self.logical_parent is not None:
            vl.update()
            mw = arm.matrix_world.copy()
            arm.parent = self.logical_parent
            arm.matrix_parent_inverse = self.logical_parent.matrix_world.inverted()
            arm.matrix_world = mw
        arm['anymachine'] = json.dumps({'joints': [{k: j[k] for k in ('param', 'type', 'bone', 'min', 'max', 'unit', 'continuous', 'rest')}
                                                   | {'axis': 'bone +Y'} for j in self.joints]})
        sc = bpy.context.scene
        params = json.loads(sc.get('sh_params', '[]'))
        for j in self.joints:
            mm = j['type'] == 'slide'
            params.append({'id': '%s.%s' % (self.family, j['param']), 'node': self.name, 'bone': j['bone'],
                           'action': None if j['continuous'] else j['param'] + '_param', 'type': j['type'],
                           'min': round(j['min'] * 1000, 4) if mm else j['min'], 'max': round(j['max'] * 1000, 4) if mm else j['max'],
                           'unit': 'mm' if mm else 'deg', 'continuous': j['continuous'], 'rest': round(j['rest'], 6), 'parent_bone': j['parent_bone'],
                           'requires': j['requires'], 'parts': [json.loads(bpy.data.objects[n]['sh'])['id'] if 'sh' in bpy.data.objects[n] else n
                                                               for n in j['parts']]})
        sc['sh_params'] = json.dumps(params)
        sc['sh_rig'] = self.name
        sc['sh_joints'] = json.dumps(self.joints)
        vl.update()
        return self

    def set(self, **values):
        """Pose the driven rig: R.set(cell_latch=1.0)."""
        set_params(self.arm, values)

    def bake_actions(self):
        bake_actions(self.arm)


def set_params(arm, values):
    for k, v in values.items():
        arm[k] = float(v)
    arm.update_tag()
    sc = bpy.context.scene
    sc.frame_set(sc.frame_current)
    bpy.context.view_layer.update()


def bake_actions(arm):
    """Replace the drivers by one linear action per parameter ('<param>_param', frames 1..25 at 24 fps = one second),
    each on its own NLA track, for glTF. Call just before the export; the saved .blend keeps the drivers."""
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, FPS + 1
    joints = json.loads(sc.get('sh_joints', '[]'))
    if not arm.animation_data:
        arm.animation_data_create()
    for j in joints:
        if j['continuous']:
            continue
        pb = arm.pose.bones[j['bone']]
        if j['type'] == 'hinge':
            pb.driver_remove('rotation_euler', 1)
        else:
            pb.driver_remove('location', 1)
        for c in list(pb.constraints):
            pb.constraints.remove(c)
    for j in joints:
        if j['continuous']:
            continue
        pb = arm.pose.bones[j['bone']]
        act = bpy.data.actions.new(j['param'] + '_param')
        arm.animation_data.action = act
        if j['type'] == 'hinge':
            pb.rotation_mode = 'QUATERNION'
            for i in range(FPS + 1):
                a = math.radians(j['min'] + (j['max'] - j['min']) * i / FPS)
                pb.rotation_quaternion = (math.cos(a / 2), 0, math.sin(a / 2), 0)
                pb.keyframe_insert('rotation_quaternion', frame=1 + i)
            pb.rotation_quaternion = (1, 0, 0, 0)
        else:
            for i in (0, FPS):
                pb.location = (0, j['min'] + (j['max'] - j['min']) * i / FPS, 0)
                pb.keyframe_insert('location', frame=1 + i)
            pb.location = (0, 0, 0)
        for fc in _fcurves(act):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
        act.use_fake_user = True
        trk = arm.animation_data.nla_tracks.new(); trk.name = act.name
        st = trk.strips.new(act.name, 1, act)
        try:
            if st.action_slot is None and act.slots:
                st.action_slot = act.slots[0]
        except Exception:
            pass
        trk.mute = False
        arm.animation_data.action = None
        if j['type'] == 'hinge':
            pb.rotation_quaternion = (1, 0, 0, 0)
        else:
            pb.location = (0, 0, 0)
    bpy.context.view_layer.update()


def _fcurves(act):
    """F-curves of an action in both the legacy and the layered (Blender 4.4+) layout."""
    try:
        fcs = list(act.fcurves)
        if fcs:
            return fcs
    except Exception:
        pass
    out = []
    try:
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    out += list(bag.fcurves)
    except Exception:
        pass
    return out
