# kit/family.py: one object that carries a family build from an empty scene to export/, so a family's build.py is
# only its parts. See READY.md for the example.
#
#   F = Family('servo', __file__, budget=45000)       # reads --nobake --size N --spp N --review [--samples N]
#                                                      # [--only six,bench,close,exploded]
#   M = F.mats                                         # mats.library(); add your own with mats.make(...)
#   ... build parts with geo / am_parts, register them with contract (CT.part, CT.fastener, CT.clear, ...) ...
#   F.rig = RG.Rig('servo', parent=case); F.rig.hinge(...); F.rig.finish()        (optional)
#   CT.sequence([...])
#   F.finish()        # hierarchy, validate, UVs, bake, save export/<family>.blend, export GLB, parts.json, stats.json
#
# Outputs in <family>/export/: <family>.glb, <family>.blend (the source check.py and review.py open; rig still
# driven), parts.json, stats.json, tex/*.png. With --nobake the GLB carries flat authoring colours: it is for
# geometry, checks and review renders (which use the procedural materials), never for Unity.
import bpy, os, sys, json, time
from mathutils import Vector, Matrix

KIT = os.path.dirname(os.path.abspath(__file__))
if KIT not in sys.path:
    sys.path.insert(0, KIT)
import geo as G
import mats as MT
import contract as CT
import bake as BK
import rig as RG


class Family:
    def __init__(self, name, build_file, budget=None, unit_scale_m=1.0, reset=True):
        self.name = name
        self.dir = os.path.dirname(os.path.abspath(build_file))
        self.out = os.path.join(self.dir, 'export')
        os.makedirs(self.out, exist_ok=True)
        argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
        self.argv = argv

        def opt(k, d, cast=int):
            return cast(argv[argv.index(k) + 1]) if k in argv else d
        self.nobake = '--nobake' in argv
        self.size = opt('--size', 2048)
        self.spp = opt('--spp', 24)
        self.review = '--review' in argv
        self.review_samples = opt('--samples', 40)
        self.review_only = opt('--only', None, str)
        self.review_hero = ()
        self.budget = budget
        self.rig = None
        self.uv_weights = {}
        self.t0 = time.time()
        if reset:
            bpy.ops.wm.read_factory_settings(use_empty=True)
        CT.begin(name, unit_scale_m)
        self.mats = MT.library()
        self.notes = {}

    def log(self, *a):
        print('[%s %6.1fs]' % (self.name, time.time() - self.t0), *a, flush=True)

    def parts(self):
        return CT.parts(self.name)

    def export_objects(self):
        P = list(self.parts().values())
        helpers = [e for e in bpy.data.objects if e.type == 'EMPTY' and e.get('sh_helper') and e.get('sh_of') in {o.name for o in P}]
        arm = [self.rig.arm] if self.rig else []
        return P, helpers, arm

    def finish(self, glb=None, export=True, extra=None):
        """Hierarchy, validation, UVs, bake (unless --nobake), source .blend, GLB, parts.json, stats.json.
        Stops (exit code 1) if the contract does not validate. Returns (parts.json dict, stats dict)."""
        name = self.name
        CT.build_hierarchy(name)
        bad = CT.validate(name, self.budget)
        for b in bad:
            self.log('CONTRACT', b)
        P, helpers, arm = self.export_objects()
        for o in P:
            G.triangulate(o)
        self.log('parts', len(P), 'helpers', len(helpers), 'tris', sum(CT.tris(o) for o in P))
        stats_extra = {'notes': self.notes, 'nobake': self.nobake}
        tex = None
        uv = BK.unwrap(P, self.size, self.uv_weights, align=bool(getattr(self, 'uv_align', False)))
        stats_extra['uv'] = uv
        self.log('uv fill', uv['fill'], 'min px/cm', min(v['px_per_cm'] for v in uv['objects'].values() if v['uv_fraction'] > 0))
        if not self.nobake:
            tex = BK.bake(P, name, self.out, self.size, self.spp)
            stats_extra['textures'] = {k: os.path.relpath(tex[k].filepath_raw, self.out) for k in ('color', 'normal', 'orm', 'emit') if tex.get(k)}
            stats_extra['texture_size'] = self.size
            stats_extra['bake'] = tex['stats']
            if tex.get('dirty'):
                stats_extra['textures_dirty'] = {k: os.path.relpath(v.filepath_raw, self.out) for k, v in tex['dirty'].items()}
                for o in P:
                    d = json.loads(o['sh'])
                    for w in d.get('wipes', []):
                        w.update({k: stats_extra['textures_dirty'][k] for k in ('color', 'normal', 'orm')})
                    o['sh'] = json.dumps(d)
        # the source scene: procedural materials still on (review renders use them), rig still driven
        blend = os.path.join(self.out, name + '.blend')
        bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True, copy=True)
        self.log('saved', blend)
        # what kit/review.py needs to make the same pictures later, from the .blend or from the GLB
        shown_ = getattr(self, 'review_objs', None) or P
        ex_ = getattr(self, 'explode', None) or {}
        json.dump({'hide': [o.name for o in P if o not in shown_], 'hero': list(self.review_hero),
                   'explode': {'f': ex_.get('f', 1.5), 'extra': {k: [float(x) for x in v] for k, v in (ex_.get('extra') or {}).items()}}},
                  open(os.path.join(self.out, 'review.json'), 'w'), indent=1)
        if self.review:
            import kitload
            RV = kitload.load('review')        # by file: a family's own review.py may be ahead of kit/ on sys.path
            RV.WARM = '--warm' in self.argv
            RV.studio(samples=self.review_samples)
            shown = getattr(self, 'review_objs', None) or P        # F.review_objs: leave loose extras (cards) out of the pictures
            for o in P:
                o.hide_render = o not in shown
            ex = getattr(self, 'explode', None) or {}      # F.explode = {'f': 1.0, 'extra': {node name: world offset}}
            RV.render_family(os.path.join(self.dir, 'review'), shown, samples=self.review_samples, tag='warm_src_' if RV.WARM else 'src_',
                             only=self.review_only.split(',') if self.review_only else None, hero=self.review_hero,
                             explode_f=ex.get('f', 1.5), explode_extra=ex.get('extra'))
            for o in P:
                o.hide_render = False
        pj = st = None
        if export:
            if tex:
                stats_extra['runtime_material_tris'] = BK.assign_runtime(P, name, tex)
            if self.rig:
                self.rig.bake_actions()
            path = os.path.join(self.out, glb or name + '.glb')
            has_anim = bool(self.rig and any(not j['continuous'] for j in self.rig.joints))
            BK.export_glb(path, P + helpers + arm, animations=has_anim)
            if has_anim:
                keep = {j['param'] + '_param': [j['bone']] for j in self.rig.joints if not j['continuous']}
                stats_extra['animation_channels'] = BK.filter_animations(path, keep)
            stats_extra['glb'] = BK.glb_summary(path)
            stats_extra['glb_bytes'] = os.path.getsize(path)
            pj, st = CT.write(name, self.out, glb or name + '.glb', extra=extra, stats_extra=stats_extra, budget=self.budget)
            self.log('wrote parts.json (%d parts, %d params) and stats.json (%d tris)' % (len(pj['parts']), len(pj['params']), st['tris_total']))
        if bad:
            self.log('FAILED: %d contract problems' % len(bad))
            sys.exit(1)
        return pj, st
