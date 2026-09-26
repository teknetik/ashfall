import bpy,json
from pathlib import Path
S=bpy.data.scenes['hero-masonry-v3'];bpy.context.window.scene=S
S.render.engine='CYCLES';S.cycles.samples=24;S.cycles.use_denoising=True
try:
 p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='CUDA';p.get_devices()
 for d in p.devices:d.use=d.type=='CUDA'
 S.cycles.device='GPU'
except Exception:pass
S.render.resolution_x=1600;S.render.resolution_y=1100;S.render.resolution_percentage=100
bpy.ops.render.render(write_still=True)
O=Path('/home/teknetik/code/ao2/art/reference_street_20260910')
(O/'hero-masonry-v3-source-render-settings.json').write_text(json.dumps(dict(renderer=S.render.engine,device=S.cycles.device,samples=S.cycles.samples,resolution=[1600,1100],scene=S.name,loadedScenes=list(bpy.data.scenes.keys()),objects=len(S.objects),materials=len(bpy.data.materials),nativeAcceptance=False),indent=2))
print(json.dumps({'image':S.render.filepath,'complete':True}))
