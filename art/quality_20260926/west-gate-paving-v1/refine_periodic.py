"""Live Blender MCP: C1 periodic edge-band repair of authored data, no albedo edits."""
from pathlib import Path
import json
import shutil
import hashlib
import bpy
import numpy as np

BASE=Path('/home/teknetik/code/ao2/art/quality_20260926/west-gate-paving-v1')
SOURCE=BASE/'clean-joints'
DESTINATION=BASE/'periodic-candidate'
if DESTINATION.exists():
    raise RuntimeError('Preserve previous candidate; choose a new output version.')
DESTINATION.mkdir()
# Reuse the original image-data writer; deliberately omit its main() invocation.
helpers=(BASE/'author_maps_v2.py').read_text().rsplit('\nmain()\n',1)[0]
exec(compile(helpers,str(BASE/'author_maps_v2.py'),'exec'))
OUT=DESTINATION
SOURCE=BASE/'clean-joints'

def read(file):
    image=bpy.data.images.load(str(SOURCE/file),check_existing=False)
    image.colorspace_settings.name='Non-Color'
    data=np.empty(N*N*4,np.float32)
    image.pixels.foreach_get(data)
    result=data.reshape(N,N,4)[::-1].copy()
    bpy.data.images.remove(image)
    return result


def hermite(t,value0,derivative0,value1,derivative1,length):
    return ((2*t**3-3*t*t+1)*value0 + (t**3-2*t*t+t)*length*derivative0
            +(-2*t**3+3*t*t)*value1+(t**3-t*t)*length*derivative1)


def periodic_axis(values,axis,band=12):
    data=np.moveaxis(values,axis,-1)
    result=data.copy()
    # The actual UV boundary lies half a texel beyond either endpoint.
    # Match value and derivative there, rather than forcing two physically
    # separated sample centers to have an identical height.
    boundary=(data[...,0]+data[...,-1])*.5
    derivative=((data[...,1]-data[...,0])+(data[...,-1]-data[...,-2]))*.5
    length=band+.5
    inner_left=data[...,band]
    inner_left_derivative=(data[...,band+1]-data[...,band-1])*.5
    inner_right=data[...,-1-band]
    inner_right_derivative=(data[...,-band]-data[...,-2-band])*.5
    for i in range(band):
        t=(i+.5)/length
        result[...,i]=hermite(t,boundary,derivative,inner_left,inner_left_derivative,length)
        t=(band-i)/length
        result[...,-1-i]=hermite(t,inner_right,inner_right_derivative,boundary,derivative,length)
    return np.moveaxis(result,-1,axis)


height=read('Height-metres.exr')[:,:,0]
roughness=read('Roughness.png')[:,:,0]
periodic_height=periodic_axis(periodic_axis(height,1),0)
periodic_roughness=np.clip(periodic_axis(periodic_axis(roughness,1),0),.70,.96)
scene=bpy.data.scenes.new('Ward Paving V1 source maps')
scene.view_settings.view_transform='Raw'
scene.view_settings.look='None'
scene.view_settings.exposure=0
scene.view_settings.gamma=1
scene.unit_settings.system='METRIC'
scene.unit_settings.scale_length=1
for name in ['Albedo-preserved.png','Joint-classification.png','Joint-review-overlay.png','Corridor-guard.png']:
    shutil.copyfile(SOURCE/name,OUT/name)
images=[save_data(scene,'Height-metres',periodic_height,depth='32',file_format='OPEN_EXR'),
        save_data(scene,'Height-normalized',(periodic_height+.008)/HEIGHT_ENCODING_METRES),
        save_data(scene,'Roughness',periodic_roughness)]
packed=np.zeros((N,N,4),np.float32)
packed[:,:,3]=1-periodic_roughness
image=bpy.data.images.new('WardPavingV1_PeriodicMetallicSmoothness',width=N,height=N,alpha=True,float_buffer=True)
image.colorspace_settings.name='Non-Color'
image.pixels.foreach_set(packed[::-1].ravel());image.update()
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.image_settings.color_depth='16'
image.save_render(str(OUT/'MetallicSmoothness.png'),scene=scene);images.append(image)
for image in images:
    image.use_fake_user=True
report=json.loads((SOURCE/'source-maps.json').read_text())
report.update(status='Periodic edge-band authoring completed; fresh normal bake pending',
              predecessor=str(SOURCE),periodicRepair='Cubic Hermite blend matching value and first derivative at actualUVboundary; original inner-band value/derivative retained',
              edgeBandPixels=12,edgeBandMetres=12*PIXEL_METRES,
              changedHeightPixels=int(np.count_nonzero(periodic_height!=height)),
              maximumHeightChangeMetres=float(np.max(np.abs(periodic_height-height))),
              albedoPreservedSha256=hashlib.sha256((OUT/'Albedo-preserved.png').read_bytes()).hexdigest(),
              sourceMaskMeaning='Joint classifier copied unchanged; physical profile blended onlywithin57.4mm periodicedge bands',
              heightRangeMetres=[float(periodic_height.min()),float(periodic_height.max())],
              roughnessRange=[float(periodic_roughness.min()),float(periodic_roughness.max())])
(OUT/'source-maps.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:report[k] for k in ['status','edgeBandPixels','edgeBandMetres','changedHeightPixels','maximumHeightChangeMetres','heightRangeMetres']},indent=2))
