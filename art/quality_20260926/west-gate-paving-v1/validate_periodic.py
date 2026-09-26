"""Live Blender readback validation of authored physical-height and baked normals."""
from pathlib import Path
import bpy
import numpy as np
import json
import hashlib
BASE=Path('/home/teknetik/code/ao2/art/quality_20260926/west-gate-paving-v1')
OUT=BASE/'periodic-v2'
N=1254
PITCH=6/N

def pixels(path):
    im=bpy.data.images.load(str(path),check_existing=False)
    im.colorspace_settings.name='Non-Color'
    a=np.empty(N*N*4,np.float32);im.pixels.foreach_get(a)
    bpy.data.images.remove(im)
    return a.reshape(N,N,4)

height=pixels(OUT/'Height-metres.exr')[:,:,0]
normal_rgb=pixels(OUT/'Normal-OpenGL.png')[:,:,:3]
normal=normal_rgb*2-1
length=np.linalg.norm(normal,axis=2,keepdims=True)
normal=normal/length
expected=np.stack([-(np.roll(height,-1,1)-np.roll(height,1,1))/(2*PITCH),
                   -(np.roll(height,-1,0)-np.roll(height,1,0))/(2*PITCH),np.ones_like(height)],axis=2)
expected/=np.linalg.norm(expected,axis=2,keepdims=True)
error=np.degrees(np.arccos(np.clip(np.sum(expected*normal,axis=2),-1,1)))
percentiles=[50,95,99,100]

def angles(a,b):
    return np.degrees(np.arccos(np.clip(np.sum(a*b,axis=-1),-1,1)))

def continuity(array,axis):
    a=np.moveaxis(array,axis,0)
    last_first=np.abs(a[0]-a[-1])
    # Quadratic extrapolation to the true boundary, half a sample outside each
    # raster end. These are numerical estimates, not claims of exact bake C1.
    value_left=(15*a[0]-10*a[1]+3*a[2])/8
    value_right=(15*a[-1]-10*a[-2]+3*a[-3])/8
    slope_left=-2*a[0]+3*a[1]-a[2]
    slope_right=2*a[-1]-3*a[-2]+a[-3]
    return dict(firstLastSampleDifferencePercentilesMetres=np.percentile(last_first,percentiles).tolist(),
                extrapolatedBoundaryValueErrorPercentilesMetres=np.percentile(np.abs(value_left-value_right),percentiles).tolist(),
                extrapolatedBoundarySlopeErrorPercentilesMetresPerMetre=np.percentile(np.abs(slope_left-slope_right)/PITCH,percentiles).tolist())

phase=[]
for dy,dx in [(0,-1),(0,0),(0,1),(-1,0),(1,0)]:
    comparison=np.roll(np.roll(expected,dy,0),dx,1)
    phase.append(dict(expectedShiftPixels=[dy,dx],xCorrelation=float(np.corrcoef(normal[:,:,0].ravel(),comparison[:,:,0].ravel())[0,1]),
                      yCorrelation=float(np.corrcoef(normal[:,:,1].ravel(),comparison[:,:,1].ravel())[0,1])))
report=dict(status='Technical bake checks only; native normal orientation, mip behavior and appearance remain pending',
            dimensions=[N,N],pixelMetres=PITCH,percentiles=percentiles,
            albedoSha256=hashlib.sha256((OUT/'Albedo-preserved.png').read_bytes()).hexdigest(),
            normalUnitLengthRange=[float(length.min()),float(length.max())],
            centralDifferenceErrorPercentilesDegrees=np.percentile(error,percentiles).tolist(),gradientPhaseCheck=phase,
            opposingColumnsNormalDifferencePercentilesDegrees=np.percentile(angles(normal[:,0],normal[:,-1]),percentiles).tolist(),
            opposingRowsNormalDifferencePercentilesDegrees=np.percentile(angles(normal[0],normal[-1]),percentiles).tolist(),
            edgeHeightX=continuity(height,1),edgeHeightY=continuity(height,0))
with bpy.data.libraries.load(str(OUT/'Paving-authoring.blend'),link=False) as (data_from,data_to):
    report['savedBlendScenes']=list(data_from.scenes)
    report['savedBlendMaterials']=list(data_from.materials)
(OUT/'normal-physical-validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
# Exact repeated data inspection image, not a relighting or native-game capture.
preview=np.tile(normal_rgb,(2,2,1))
im=bpy.data.images.new('Ward Paving V2 exact repeated normal inspection',width=2*N,height=2*N,alpha=False,float_buffer=True)
im.colorspace_settings.name='Non-Color'
rgba=np.ones((2*N,2*N,4),np.float32);rgba[:,:,:3]=preview
im.pixels.foreach_set(rgba.ravel());im.update()
scene=bpy.data.scenes.new('Ward Paving technical inspection export')
scene.view_settings.view_transform='Raw';scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.image_settings.color_depth='8'
im.save_render(str(OUT/'Repeat-normal-inspection.png'),scene=scene)
bpy.data.images.remove(im);bpy.data.scenes.remove(scene)
