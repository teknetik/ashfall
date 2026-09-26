"""Schedule review renders inside the live Blender MCP session."""
import bpy,json,traceback
from pathlib import Path
OUT=Path('/home/teknetik/code/ao2/art/karaveen_artisan_20260910')
scene=bpy.data.scenes['KA_Artisan_Stall_v01'];bpy.context.window.scene=scene
jobs=[('Hero','artisan-stall-hero-v01.png',1440,1080),('Front','artisan-stall-front-v01.png',1280,1080),('Right','artisan-stall-right-v01.png',1280,1080),('Back','artisan-stall-back-v01.png',1280,1080),('Detail','artisan-stall-detail-v01.png',1200,1200),('Rig','artisan-stall-rig-preview-v01.png',1440,1080)]
state={'status':'running','completed':[],'pending':[j[0] for j in jobs]}
def save_state(): (OUT/'render-status-v01.json').write_text(json.dumps(state,indent=2)+'\n')
def render_next():
    try:
        if not jobs:
            rig=bpy.data.objects['KA_Artisan_Rig'];rig['left_door_open']=0.;rig['right_door_open']=0.;rig['canopy_billow']=0.;rig.update_tag(refresh={'OBJECT'});scene.frame_set(1)
            scene.camera=bpy.data.objects['KA_Camera_Hero'];scene.render.resolution_x=1440;scene.render.resolution_y=1080
            scene.render.filepath=str(OUT/'artisan-stall-hero-v01.png')
            bpy.data.objects['KA_Studio_ground'].hide_render=False
            bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'karaveen-artisan-stall-v01.blend'))
            state['status']='complete';save_state();return None
        camera,file,w,h=jobs.pop(0)
        bpy.data.objects['KA_Studio_ground'].hide_render=camera not in ('Hero','Rig')
        if camera=='Rig':
            rig=bpy.data.objects['KA_Artisan_Rig'];rig['left_door_open']=80.;rig['right_door_open']=95.;rig['canopy_billow']=.8;rig.update_tag(refresh={'OBJECT'});scene.frame_set(1);bpy.context.view_layer.update();camera='Hero'
        scene.cycles.samples=96 if camera=='Detail' else 48
        scene.camera=bpy.data.objects['KA_Camera_'+camera];scene.render.resolution_x=w;scene.render.resolution_y=h;scene.render.filepath=str(OUT/file)
        bpy.ops.render.render(write_still=True)
        state['completed'].append(file);state['pending']=[j[0] for j in jobs];save_state()
        return .2
    except Exception:
        state['status']='error';state['error']=traceback.format_exc();save_state();return None
save_state();bpy.app.timers.register(render_next,first_interval=1.0)
print('Queued six native Blender renders; progress: '+str(OUT/'render-status-v01.json'))
