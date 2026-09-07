"""In-place locomotion for the fitted MPFB game_engine colonist.

Load this file, then call ``report = animate_colonist(rig)`` in Blender.
Nothing executes on import. No mesh, rest bone, rig object transform, scene
camera, export or file is changed. Four muted NLA tracks are prepared for glTF
NLA_TRACKS export; the unanimated preview is left in the relaxed idle pose.

World convention: metres, Z up, character facing -Y. Limb directions are
converted through the *posed* parent and actual rest matrices, including bone
roll. Analytic two-bone legs are baked to FK, so no runtime IK is required.
"""
import math
import bpy
from mathutils import Matrix, Quaternion, Vector


ANIMATION_TAG = 'colonistAnimationV1'
# NLA export samples integer scene frames. 120 Hz retains the corrected
# quarter-frame density of the original 30 fps motion without changing time.
FPS = 120
CLIPS = {'idle': 360, 'walk': 96, 'run': 96, 'talk': 360}
SIDES = (('l', 1.0), ('r', -1.0))
REQUIRED = ('pelvis', 'spine_01', 'spine_02', 'spine_03', 'neck_01', 'head') + tuple(
    part + '_' + side for side, _ in SIDES
    for part in ('clavicle', 'upperarm', 'lowerarm', 'hand', 'thigh', 'calf', 'foot', 'ball'))
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
FORWARD = Vector((0, -1, 0))


def _rotation(axis, angle):
    return Quaternion(axis, angle)


def _smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3.0 - 2.0 * t)


def _curves(action):
    """Both legacy actions and Blender 4.4/5.x slotted actions."""
    legacy = getattr(action, 'fcurves', None)
    if legacy is not None:
        yield from legacy
        return
    for layer in action.layers:
        for strip in layer.strips:
            for bag in getattr(strip, 'channelbags', ()):
                yield from bag.fcurves


def _activate_action(rig, action):
    rig.animation_data.action = action
    if action is not None and hasattr(action, 'slots') and len(action.slots):
        rig.animation_data.action_slot = action.slots[0]


class _ColonistPose:
    """Small FK solver retaining Blender's actual rest-coordinate bases."""

    def __init__(self, rig):
        self.rig = rig
        self.rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
        self.parent = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
        self.world = rig.matrix_world.copy()
        self.world_inverse = self.world.inverted()
        self.world_q = self.world.to_quaternion()
        self.rest_world_q = {name: (self.world @ matrix).to_quaternion()
                             for name, matrix in self.rest.items()}
        self.rest_head = {b.name: self.world @ b.head_local for b in rig.data.bones}
        self.rest_tail = {b.name: self.world @ b.tail_local for b in rig.data.bones}
        # Scale all motion distances with measured leg length, rather than the
        # unapplied 1.03596 rig scale or a hard-coded armature-space distance.
        self.leg_lengths = {side: tuple((self.rest_tail[p + '_' + side] -
                                        self.rest_head[p + '_' + side]).length
                                       for p in ('thigh', 'calf')) for side, _ in SIDES}
        self.motion_scale = sum(self.leg_lengths['l']) / .893
        self.ground = float(rig.get('colonistGroundZ', 0.0))
        self.sole = {}
        for side, _ in SIDES:
            name = 'foot_' + side
            ankle = self.rest_head[name]
            # Contact probes represent the underside of the boot, not the
            # foot bone's elevated ankle and ball. Export QA must additionally
            # inspect the fitted boot mesh; these are bone-space diagnostics.
            self.sole[side] = (
                Vector((0, .052 * self.motion_scale, self.ground - ankle.z)),
                Vector((0, self.rest_tail['ball_' + side].y - ankle.y,
                        self.ground - ankle.z)),
            )
        self.reset()

    def reset(self):
        self.local = {name: Matrix.Identity(4) for name in self.rest}
        self.cache = {}
        self.targets = {}
        self.reach_error = 0.0

    def neutral(self, name):
        parent = self.parent[name]
        return (self.matrix(parent) @ self.rest[parent].inverted() @ self.rest[name]
                if parent else self.rest[name].copy())

    def matrix(self, name):
        if name not in self.cache:
            self.cache[name] = self.neutral(name) @ self.local[name]
        return self.cache[name]

    def head(self, name):
        return self.world @ self.matrix(name).translation

    def world_rotation(self, name, target):
        neutral_q = self.neutral(name).to_quaternion()
        local_q = neutral_q.inverted() @ self.world_q.inverted() @ target
        translation = self.local[name].translation.copy()
        self.local[name] = local_q.normalized().to_matrix().to_4x4()
        self.local[name].translation = translation
        self.cache.clear()

    def delta_from_rest(self, name, delta):
        self.world_rotation(name, delta @ self.rest_world_q[name])

    def aim(self, name, direction):
        rest_direction = self.rest_tail[name] - self.rest_head[name]
        swing = rest_direction.normalized().rotation_difference(direction.normalized())
        self.world_rotation(name, swing @ self.rest_world_q[name])

    def vertical_pelvis(self, amount):
        # Translation channels precede the pelvis's own rotation. Convert
        # world vertical through the neutral bone basis, not its posed axes.
        neutral = self.world @ self.neutral('pelvis')
        self.local['pelvis'].translation = neutral.to_3x3().inverted() @ (Z * amount)
        self.cache.clear()

    def leg(self, side, ankle, foot_pitch, support):
        thigh, calf, foot = (p + '_' + side for p in ('thigh', 'calf', 'foot'))
        hip = self.head(thigh)
        upper, lower = self.leg_lengths[side]
        to_ankle = ankle - hip
        distance = to_ankle.length
        limit = upper + lower - .0002 * self.motion_scale
        self.reach_error = max(self.reach_error, max(0.0, distance - limit))
        distance = min(limit, max(abs(upper - lower) + .001, distance))
        axis = to_ankle.normalized()
        along = (upper * upper - lower * lower + distance * distance) / (2 * distance)
        height = math.sqrt(max(0.0, upper * upper - along * along))
        # Both knees bend toward the character's front. The pole is projected
        # perpendicular to the hip/ankle line, so pitched hips cannot invert it.
        pole = FORWARD - axis * FORWARD.dot(axis)
        pole.normalize()
        knee = hip + axis * along + pole * height
        self.aim(thigh, knee - hip)
        self.aim(calf, ankle - self.head(calf))
        self.delta_from_rest(foot, _rotation(X, foot_pitch))
        # Toe bones retain their relative rest pose, including the authored
        # toe-out angle; no global reset that counters the foot's own rotation.
        self.targets[side] = {'ankle': tuple(ankle), 'support': support,
                              'pitch': foot_pitch}

    def apply(self, previous=None, frame=None):
        previous = previous if previous is not None else {}
        for p in self.rig.pose.bones:
            p.rotation_mode = 'QUATERNION'
            quaternion = self.local[p.name].to_quaternion()
            if p.name in previous and quaternion.dot(previous[p.name]) < 0:
                quaternion.negate()
            p.rotation_quaternion = quaternion
            p.location = self.local[p.name].translation
            p.scale = (1, 1, 1)
            previous[p.name] = quaternion.copy()
            if frame is not None:
                p.keyframe_insert(data_path='rotation_quaternion', frame=frame)
                if p.name == 'pelvis':
                    p.keyframe_insert(data_path='location', frame=frame)


def _foot_path(clip, phase, scale):
    """Constant backward stance velocity, eased recovery, grounded foot roll."""
    running = clip == 'run'
    stance = .34 if running else .60
    stride = (.98 if running else .72) * scale
    if phase < stance:
        u = phase / stance
        y = stride * (u - .5)
        # A modest heel strike settles promptly; the final stance rolls over
        # the toe. Both ends join the swing at the exact same pitch and height.
        pitch = (-.10 if running else -.16) * (1 - _smooth(u / .20))
        pitch += (.38 if running else .25) * _smooth((u - .72) / .28)
        lift = 0.0
        support = True
    else:
        u = (phase - stance) / (1 - stance)
        y = stride * (.5 - _smooth(u))
        # Early heel recovery clears the pavement, with a slower final descent.
        lift = (.24 if running else .095) * scale * math.sin(math.pi * u) ** 1.35
        pitch = (.38 if running else .25) * (1 - _smooth(u / .55))
        pitch += (-.10 if running else -.16) * _smooth((u - .6) / .4)
        support = False
    return y, lift, pitch, support


def _pose_at(solver, clip, phase):
    solver.reset()
    # Exact endpoint reuse avoids floating-point sine differences at the seam.
    phase = phase % 1.0
    t = math.tau * phase
    scale = solver.motion_scale
    moving, running = clip in ('walk', 'run'), clip == 'run'
    gesture = (.5 - .5 * math.cos(t)) ** 1.2 if clip == 'talk' else 0.0
    if moving:
        bob = (-.15 + .028 * math.sin(t * 2 - .6) if running
               else -.080 - .015 * math.cos(t * 2)) * scale
        pelvis_pitch = .072 if running else .012
        lean = .18 if running else .025
        twist = (.042 if running else .024) * math.sin(t)
        roll = (.018 if running else .012) * math.sin(t)
    else:
        bob = (-.016 + .0018 * math.sin(t)) * scale
        pelvis_pitch = .004
        lean = .008 * math.sin(t) + .016 * gesture
        twist = .012 * math.sin(t)
        roll = .006 * math.sin(t)
    solver.delta_from_rest('pelvis', _rotation(Z, -twist * .7) @
                           _rotation(Y, roll) @ _rotation(X, pelvis_pitch))
    solver.vertical_pelvis(bob)
    for name, amount in (('spine_01', .45), ('spine_02', .72), ('spine_03', 1.0)):
        solver.delta_from_rest(name, _rotation(Z, twist * amount) @
                               _rotation(X, lean * amount))
    solver.delta_from_rest('neck_01', _rotation(Z, twist * .30) @
                           _rotation(X, lean * .35))
    solver.delta_from_rest('head', _rotation(Z, .025 * math.sin(t) + .035 * gesture) @
                           _rotation(X, .018 * math.sin(t * 2) * gesture + lean * .12))

    for side, sign in SIDES:
        cycle = (phase + (0 if side == 'l' else .5)) % 1.0
        foot = 'foot_' + side
        if moving:
            y, lift, pitch, support = _foot_path(clip, cycle, scale)
        else:
            y, lift, pitch, support = 0.0, 0.0, 0.0, True
        rest_ankle = solver.rest_head[foot]
        foot_delta = _rotation(X, pitch)
        ankle_z = solver.ground - min((foot_delta @ v).z for v in solver.sole[side]) + lift
        # The original rest pose has ankle centres ~40 cm apart. Bring them
        # under the hips without moving the rig or changing leg bone lengths.
        hip_x = solver.rest_head['thigh_' + side].x
        ankle = Vector((hip_x + sign * .025 * scale, rest_ankle.y + y, ankle_z))
        solver.leg(side, ankle, pitch, support)

        # First relax the A-pose by aiming both segments in world space. The
        # forearm's authored bend/roll does not become an extra Euler bend.
        swing = (math.cos(math.tau * cycle) * (.54 if running else .27)) if moving else .008 * math.sin(t)
        bend = 1.02 if running else .20
        upper = Vector((sign * .245, -.025, -1.0))
        lower = Vector((sign * .070, -.015, -1.0))
        if clip == 'talk' and side == 'r':
            swing -= .38 * gesture
            bend += .88 * gesture
            upper.x += sign * .16 * gesture
        upper = _rotation(Z, twist) @ (_rotation(X, swing) @ upper)
        lower = _rotation(Z, twist) @ (_rotation(X, swing - bend) @ lower)
        solver.aim('upperarm_' + side, upper)
        solver.aim('lowerarm_' + side, lower)
        solver.aim('hand_' + side, lower)
        # Retain the MPFB fingers' fitted, slightly curved rest shape. Small
        # additional local curl uses the actual posed hand orientation.
        hand = 'hand_' + side
        hand_change = (solver.world_q @ solver.matrix(hand).to_quaternion()) @ solver.rest_world_q[hand].inverted()
        palm_inward = hand_change @ Vector((-sign, 0, 0))
        for name in solver.rest:
            if not name.endswith('_' + side) or not any(name.startswith(prefix + '_')
                                                       for prefix in ('index', 'middle', 'ring', 'pinky')):
                continue
            neutral_q = solver.world_q @ solver.neutral(name).to_quaternion()
            direction = neutral_q @ Y
            axis = direction.cross(palm_inward)
            if axis.length > .001:
                curl = .065 if not running else .13
                if clip == 'talk' and side == 'r':
                    curl *= 1.0 - gesture * .8
                solver.world_rotation(name, _rotation(axis.normalized(), curl) @ neutral_q)


def _snapshot(rig, solver, phase, targets):
    """Read actual evaluated pose matrices after Blender dependency update."""
    bpy.context.view_layer.update()
    evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
    points = {}
    selected = ('pelvis', 'head', 'upperarm_l', 'lowerarm_l', 'hand_l',
                'upperarm_r', 'lowerarm_r', 'hand_r', 'thigh_l', 'thigh_r',
                'calf_l', 'calf_r', 'foot_l', 'foot_r')
    for name in selected:
        p = evaluated.pose.bones[name]
        points[name] = {'head': list(evaluated.matrix_world @ p.head),
                        'tail': list(evaluated.matrix_world @ p.tail),
                        'quaternion': list(rig.pose.bones[name].rotation_quaternion)}
    feet = {}
    for side, _ in SIDES:
        p = evaluated.pose.bones['foot_' + side]
        ankle = evaluated.matrix_world @ p.head
        delta = ((evaluated.matrix_world @ p.matrix).to_quaternion() @
                 solver.rest_world_q['foot_' + side].inverted())
        probes = [ankle + delta @ v for v in solver.sole[side]]
        feet[side] = {'support': targets[side]['support'], 'ankle': list(ankle),
                      'targetError': (ankle - Vector(targets[side]['ankle'])).length,
                      'clearance': min(v.z for v in probes) - solver.ground,
                      'heel': list(probes[0]), 'toe': list(probes[1])}
    pelvis = Vector(points['pelvis']['head']) - solver.rest_head['pelvis']
    return {'phase': phase, 'bones': points, 'feet': feet,
            'pelvisHorizontalOffset': math.hypot(pelvis.x, pelvis.y),
            'pelvisVerticalOffset': pelvis.z}


def colonist_animation_diagnostics(rig, sample_phases=(0, .25, .5, .75, 1)):
    """Evaluate real baked actions; restore action, pose and scene afterwards.

    Dense frame checks report root drift and foot probes. Sample poses include
    actual evaluated heads/tails and local quaternions for render/audit tooling.
    Foot probes are not a claim that the fitted skin/armour never intersects.
    """
    solver = _ColonistPose(rig)
    scene = bpy.context.scene
    old_frame, old_subframe = scene.frame_current, scene.frame_subframe
    old_action = rig.animation_data.action
    old_basis = {p.name: (p.matrix_basis.copy(), p.rotation_mode) for p in rig.pose.bones}
    old_mute = [(track, track.mute) for track in rig.animation_data.nla_tracks]
    report = {'fps': FPS, 'boneCount': len(rig.data.bones), 'clips': {},
              'footEvidence': 'bone-space sole probes; fitted mesh inspection required',
              'rigMatrixUnchanged': True}
    try:
        for track, _ in old_mute:
            track.mute = True
        for clip, frames in CLIPS.items():
            actions = [a for a in bpy.data.actions if a.get(ANIMATION_TAG) == rig.name
                       and a.get('colonistClip') == clip]
            if len(actions) != 1:
                raise ValueError('Expected one authored action for ' + clip)
            _activate_action(rig, actions[0])
            snapshots = []
            maximum_root, minimum_sole, maximum_contact, target_error = 0.0, float('inf'), 0.0, 0.0
            # Check halfway between every 120 Hz baked key as well. This
            # catches interpolation errors at 240 Hz, including contact edges.
            phases = sorted(set([i / (frames * 2) for i in range(frames * 2 + 1)] + list(sample_phases)))
            first, last = None, None
            for phase in phases:
                _pose_at(solver, clip, phase)
                frame = 1 + phase * frames
                scene.frame_set(math.floor(frame), subframe=frame % 1)
                snapshot = _snapshot(rig, solver, phase, solver.targets)
                maximum_root = max(maximum_root, snapshot['pelvisHorizontalOffset'])
                for foot in snapshot['feet'].values():
                    minimum_sole = min(minimum_sole, foot['clearance'])
                    target_error = max(target_error, foot['targetError'])
                    if foot['support']:
                        maximum_contact = max(maximum_contact, abs(foot['clearance']))
                if phase in sample_phases:
                    snapshots.append(snapshot)
                signature = {p.name: (list(p.location), list(p.rotation_quaternion)) for p in rig.pose.bones}
                if phase == 0:
                    first = signature
                if phase == 1:
                    last = signature
            loop_position, loop_angle = 0.0, 0.0
            for name, (location, rotation) in first.items():
                loop_position = max(loop_position, (Vector(location) - Vector(last[name][0])).length)
                a, b = Vector(rotation), Vector(last[name][1])
                a.normalize()
                b.normalize()
                difference = min((a - b).length, (a + b).length)
                loop_angle = max(loop_angle, 4 * math.asin(min(1.0, difference / 2)))
            report['clips'][clip] = {'duration': frames / FPS, 'frames': frames + 1,
                'maxPelvisHorizontalOffset': maximum_root, 'minSoleClearance': minimum_sole,
                'maxSupportHeightError': maximum_contact, 'maxAnkleTargetError': target_error,
                'loopPositionError': loop_position, 'loopRotationErrorRadians': loop_angle,
                'samples': snapshots}
        report['rigMatrixUnchanged'] = all(abs(rig.matrix_world[r][c] - solver.world[r][c]) < 1e-8
                                             for r in range(4) for c in range(4))
    finally:
        _activate_action(rig, old_action)
        for track, muted in old_mute:
            track.mute = muted
        scene.frame_set(old_frame, subframe=old_subframe)
        for p in rig.pose.bones:
            p.rotation_mode = old_basis[p.name][1]
            p.matrix_basis = old_basis[p.name][0]
        bpy.context.view_layer.update()
    return report



def animate_colonist(rig):
    """Bake idle/walk/run/talk, verify integrity, return measured diagnostics."""
    if rig.type != 'ARMATURE':
        raise TypeError('animate_colonist requires an MPFB game_engine armature')
    missing = [name for name in REQUIRED if name not in rig.data.bones]
    if missing:
        raise ValueError('Missing game_engine bones: ' + ', '.join(missing))
    if any(p.constraints for p in rig.pose.bones):
        raise ValueError('Bake/remove pose constraints before authoring FK clips')
    scales = rig.matrix_world.to_scale()
    if min(scales) <= 0 or max(scales) - min(scales) > 1e-5:
        raise ValueError('The fitted rig must have positive uniform object scale')
    rig.animation_data_create()
    if rig.animation_data.action and rig.animation_data.action.get(ANIMATION_TAG) != rig.name:
        raise ValueError('Preserve or remove the unrelated active action first')
    for track in rig.animation_data.nla_tracks:
        if any(strip.action is None or strip.action.get(ANIMATION_TAG) != rig.name for strip in track.strips):
            raise ValueError('Preserve or remove unrelated NLA tracks first')
    # Re-running only removes this rig's own generated actions/tracks.
    _activate_action(rig, None)
    for track in list(rig.animation_data.nla_tracks):
        rig.animation_data.nla_tracks.remove(track)
    for action in list(bpy.data.actions):
        if action.get(ANIMATION_TAG) == rig.name and action.users == 0:
            bpy.data.actions.remove(action)
    solver = _ColonistPose(rig)
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1.0
    scene.frame_start, scene.frame_end = 1, max(CLIPS.values()) + 1
    maximum_reach_error = 0.0
    for clip, frames in CLIPS.items():
        action = bpy.data.actions.new('COLONIST_' + clip)
        action[ANIMATION_TAG], action['colonistClip'] = rig.name, clip
        action['inPlace'] = True
        action['authoredFps'] = FPS
        action['nominalMetersPerSecond'] = (.72 * solver.motion_scale / (.60 * frames / FPS) if clip == 'walk'
                                           else .98 * solver.motion_scale / (.34 * frames / FPS) if clip == 'run' else 0.0)
        _activate_action(rig, action)
        previous = {}
        subdivisions = 1
        action['keySubdivisions'] = subdivisions
        for i in range(frames * subdivisions + 1):
            _pose_at(solver, clip, i / (frames * subdivisions))
            maximum_reach_error = max(maximum_reach_error, solver.reach_error)
            solver.apply(previous, frame=i / subdivisions + 1)
        for curve in _curves(action):
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
        action.use_frame_range = True
        action.frame_start, action.frame_end = 1, frames + 1
        track = rig.animation_data.nla_tracks.new()
        track.name = clip
        strip = track.strips.new(clip, 1, action)
        strip.action_frame_start, strip.action_frame_end = 1, frames + 1
        strip.blend_type, strip.extrapolation = 'REPLACE', 'NOTHING'
        track.mute = True
        _activate_action(rig, None)
    scene.frame_set(1)
    _pose_at(solver, 'idle', 0)
    solver.apply()
    bpy.context.view_layer.update()
    report = colonist_animation_diagnostics(rig)
    report['maxUnreachableTargetDistance'] = maximum_reach_error
    report['restMatricesUnchanged'] = all(
        abs(rig.data.bones[name].matrix_local[r][c] - matrix[r][c]) < 1e-8
        for name, matrix in solver.rest.items() for r in range(4) for c in range(4))
    problems = []
    if not report['rigMatrixUnchanged'] or not report['restMatricesUnchanged']:
        problems.append('Rig object/rest matrices changed')
    if maximum_reach_error > .003:
        problems.append('A leg target exceeded its measured reach by over 3 mm')
    for clip, result in report['clips'].items():
        if result['maxPelvisHorizontalOffset'] > 1e-5:
            problems.append(clip + ': horizontal pelvis motion')
        if result['loopPositionError'] > 1e-5 or result['loopRotationErrorRadians'] > .001:
            problems.append(clip + ': discontinuous loop endpoints')
        if result['minSoleClearance'] < -.004 or result['maxSupportHeightError'] > .006:
            problems.append(clip + ': foot contact outside tolerance')
        if result['maxAnkleTargetError'] > .006:
            problems.append(clip + ': ankle differs from intended target')
    report['integrityPassed'], report['problems'] = not problems, problems
    # Caller gets the complete diagnostic report even if visual/contact review
    # rejects this pass; no silent export or fallback to the previous anatomy.
    return report
