"""STAGED live source review; no app launch. One immutable view per call.
CORE_VIEW=front_oblique/grille_close/guard_oblique, CORE_VARIANT=before/selection/after.
Set CORE_TAG for a separate revision. Geometry/camera/light remain matched.
"""
import bpy,json
from pathlib import Path
from mathutils import Vector
S=bpy.data.scenes['Generator v4 core repair audition'];bpy.context.window.scene=S;O=Path(S['generator_core_repair_output']);out=O/'renders';out.mkdir(exist_ok=True)
view=globals().get('CORE_VIEW','front_oblique');variant=globals().get('CORE_VARIANT','after');tag=globals().get('CORE_TAG','core-v4');assert variant in ('before','selection','after')
views={'front_oblique':((2.5,-3.4,1.8),(.10,0,.53),64),'grille_close':((.12,-1.4,.76),(0,-.24,.60),70),'guard_oblique':((.44,-1.12,.69),(-.12,-.155,.462),78)}
assert view in views;path=out/(view+'-'+tag+'-'+variant+'.png');assert not path.exists()
original=bpy.data.objects[S['generator_core_repair_original']];core=bpy.data.objects[S['generator_core_repair_core']];mask=bpy.data.objects[S['generator_core_repair_mask']];parts=list(bpy.data.collections[S['generator_core_repair_authored_collection']].objects)
objs=[original,core,mask]+parts;saved={o:o.hide_render for o in objs};p,t,lens=views[view];cam=S.camera;cam.location=p;cam.rotation_euler=(Vector(t)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='PERSP';cam.data.lens=lens;cam.data.clip_start=.01;cam.data.dof.use_dof=False
try:
 original.hide_render=variant!='before';core.hide_render=variant=='before';mask.hide_render=variant!='selection'
 for o in parts:o.hide_render=variant!='after'
 S.render.filepath=str(path);bpy.ops.render.render(write_still=True)
finally:
 for o,hidden in saved.items():o.hide_render=hidden
record={'view':view,'variant':variant,'image':str(path),'position':p,'target':t,'lens':lens,'resolution':[S.render.resolution_x,S.render.resolution_y],'samples':S.cycles.samples,'exposure':S.view_settings.exposure,'method':'Before is unchanged complete core; selection reconstructs original using retained core plus orange removed source faces; after replaces only that region. Service geometry and lights are unchanged.','sourceAccepted':False,'nativeAccepted':False};path.with_suffix('.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
