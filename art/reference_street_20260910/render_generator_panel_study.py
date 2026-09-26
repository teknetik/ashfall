"""STAGED one immutable matched panel render. Never launches an app.
PANEL_VARIANT=before/after, PANEL_DIAGNOSTIC=pbr/albedo/mask,
PANEL_VIEW=grille_close/front_oblique. Defaults after/pbr/grille_close.
"""
import bpy,json
from pathlib import Path
from mathutils import Vector
S=bpy.data.scenes['Generator v4 protected panel audition'];bpy.context.window.scene=S;O=Path(S['generator_panel_output']);out=O/'renders';out.mkdir(exist_ok=True)
variant=globals().get('PANEL_VARIANT','after');diagnostic=globals().get('PANEL_DIAGNOSTIC','pbr');view=globals().get('PANEL_VIEW','grille_close');assert variant in ('before','after') and diagnostic in ('pbr','albedo','mask')
views={'grille_close':((.12,-1.4,.76),(0,-.24,.60),70),'front_oblique':((2.5,-3.4,1.8),(.10,0,.53),64)};assert view in views
path=out/(view+'-'+diagnostic+'-'+variant+'.png');assert not path.exists();core=bpy.data.objects[S['generator_panel_core']];slot=core.material_slots[0];saved=slot.material;tmp=None
ma=bpy.data.materials[S['generator_panel_original_material']if variant=='before'else S['generator_panel_candidate_material']]
p,t,l=views[view];cam=S.camera;cam.location=p;cam.rotation_euler=(Vector(t)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='PERSP';cam.data.lens=l;cam.data.clip_start=.01;cam.data.dof.use_dof=False
try:
 if diagnostic!='pbr':
  tmp=ma.copy();tmp.name='Temporary panel diagnostic';n=tmp.node_tree.nodes;k=tmp.node_tree.links;pbr=n.get('Principled BSDF');e=n.new('ShaderNodeEmission');e.inputs['Strength'].default_value=1
  if diagnostic=='albedo':source=pbr.inputs['Base Color'].links[0].from_socket
  else:
   tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(O/'authored-paint-mask.png'),check_existing=True);tex.image.colorspace_settings.name='Non-Color';source=tex.outputs['Color']
  k.new(source,e.inputs['Color']);k.new(e.outputs[0],n.get('Material Output').inputs['Surface']);ma=tmp
 slot.material=ma;S.render.filepath=str(path);bpy.ops.render.render(write_still=True)
finally:
 slot.material=saved
 if tmp:bpy.data.materials.remove(tmp)
record={'image':str(path),'variant':variant,'diagnostic':diagnostic,'position':p,'target':t,'lens':l,'geometryMatchesExactly':True,'originalMaterialRestoredAfterDiagnostic':slot.material==saved,'sourceAccepted':False,'nativeAccepted':False};path.with_suffix('.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
