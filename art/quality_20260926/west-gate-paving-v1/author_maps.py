"""Run through live Blender MCP. Author technical maps, preserving source albedo.

Coordinates below are manually traced joint-center corridors in the retained
1254-pixel source, in top-left image coordinates. Albedo values classify material
only inside these corridors; they never determine height amplitude.
"""
from pathlib import Path
import hashlib
import json
import math
import shutil
import bpy
import numpy as np

ROOT = Path('/home/teknetik/code/ao2')
OUT = ROOT / 'art/quality_20260926/west-gate-paving-v1'
SOURCE = ROOT / 'unity/AthenHill/Assets/AthenHill/Art/Textures/AAA/Paving_Albedo.png'
N = 1254
EXTENT_METRES = 6.0
PIXEL_METRES = EXTENT_METRES / N
JOINT_DEPTH = .006
BEVEL_METRES = .019
HEIGHT_ENCODING_METRES = .016

# Corridors delimit the semantic joint network; darker mineral patches outside
# it cannot become cracks or craters. The short end segments continue across
# the repeating image edges.
CORRIDORS = [
    [(0,168),(208,163),(443,166),(842,164),(1073,166),(1254,168)],
    [(0,594),(108,596),(432,594),(532,596)],
    [(532,308),(653,309),(808,308),(1001,309)],
    [(0,726),(106,726)],
    [(432,742),(645,741),(808,742)],
    [(808,724),(1000,723),(1181,724),(1254,724)],
    [(0,928),(105,927),(432,928)],
    [(1181,927),(1254,927)],
    [(0,1180),(208,1182),(435,1183),(808,1181),(1073,1180),(1254,1180)],
    [(208,0),(205,60),(210,120),(208,165)],
    [(443,0),(439,55),(445,102),(443,166)],
    [(842,0),(841,80),(843,164)],
    [(1073,0),(1072,80),(1073,166)],
    [(8,168),(6,320),(11,480),(10,593),(15,725)],
    [(532,168),(530,310),(531,480),(530,596),(532,742)],
    [(653,168),(653,309)],
    [(1001,167),(1000,309),(998,510),(1000,723)],
    [(808,309),(806,525),(808,742),(808,950),(808,1181)],
    [(107,595),(105,726),(106,927)],
    [(432,596),(434,742),(431,928),(434,1182)],
    [(1181,724),(1180,927),(1181,1080),(1180,1254)],
    [(207,928),(208,1060),(207,1180),(209,1254)],
    [(435,1182),(439,1254)],
    [(1073,1180),(1072,1254)],
]


def smoothstep(low, high, value):
    t = np.clip((value-low)/(high-low), 0, 1)
    return t*t*(3-2*t)


def blur_periodic(array, sigma):
    fy = np.fft.fftfreq(array.shape[0])[:, None]
    fx = np.fft.fftfreq(array.shape[1])[None, :]
    kernel = np.exp(-2*np.pi*np.pi*sigma*sigma*(fx*fx+fy*fy))
    return np.fft.ifft2(np.fft.fft2(array)*kernel).real.astype(np.float32)


def dilate(array):
    return np.maximum.reduce([np.roll(np.roll(array, y, 0), x, 1)
                              for y in (-1,0,1) for x in (-1,0,1)])


def erode(array):
    return np.minimum.reduce([np.roll(np.roll(array, y, 0), x, 1)
                              for y in (-1,0,1) for x in (-1,0,1)])


def save_data(scene, name, values, depth='16', file_format='PNG'):
    if values.ndim == 2:
        values = np.repeat(values[:, :, None], 3, axis=2)
    rgba = np.ones((N,N,4), dtype=np.float32)
    rgba[:,:,:3] = values[:,:,:3]
    image = bpy.data.images.new('WardPavingV1_' + name, width=N, height=N,
                                alpha=True, float_buffer=True)
    image.colorspace_settings.name = 'Non-Color'
    image.pixels.foreach_set(rgba[::-1].ravel())
    image.update()
    scene.render.image_settings.file_format = file_format
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.color_depth = depth
    extension = '.exr' if file_format == 'OPEN_EXR' else '.png'
    image.save_render(str(OUT / (name+extension)), scene=scene)
    return image


def main():
    if (OUT/'source-maps.json').exists():
        raise RuntimeError('Preserve existing version; author a new version for changes.')
    original_scene = bpy.context.scene
    original_objects = [(o.name, o.as_pointer()) for o in original_scene.objects]
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if source_hash != '9d8a4d78479096af5c1e33f98ccffbb5be8336cf232646a2cac25b022d22bc0c':
        raise RuntimeError('Source changed; re-audit before authoring.')
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE, OUT/'Albedo-preserved.png')
    source_image = bpy.data.images.load(str(SOURCE), check_existing=False)
    source_image.colorspace_settings.name = 'Non-Color'
    pixels = np.empty(N*N*4, dtype=np.float32)
    source_image.pixels.foreach_get(pixels)
    rgb = pixels.reshape(N,N,4)[::-1,:,:3].copy()
    bpy.data.images.remove(source_image)

    yy, xx = np.mgrid[:N,:N].astype(np.float32)
    distance = np.full((N,N), np.inf, np.float32)
    for points in CORRIDORS:
        for a,b in zip(points, points[1:]):
            ax,ay=a; bx,by=b
            # Copies near an edge ensure the classifier is periodic.
            shifts_x = [-N,0,N] if min(ax,bx)<14 or max(ax,bx)>N-14 else [0]
            shifts_y = [-N,0,N] if min(ay,by)<14 or max(ay,by)>N-14 else [0]
            vx,vy=bx-ax,by-ay
            for sx in shifts_x:
                for sy in shifts_y:
                    t=np.clip(((xx-ax-sx)*vx+(yy-ay-sy)*vy)/(vx*vx+vy*vy),0,1)
                    d=np.sqrt((xx-(ax+sx+t*vx))**2+(yy-(ay+sy+t*vy))**2)
                    distance=np.minimum(distance,d)
    corridor = distance <= 10
    luma = rgb @ np.array([.2126,.7152,.0722],np.float32)
    raw_joint = corridor & (luma < .56)
    # Closing removes tiny bright grit gaps, rather than interpreting each
    # albedo speck as a tiny height spike. The wider corridor remains a guard.
    joint = erode(dilate(raw_joint)) & corridor
    joint_soft = smoothstep(.18,.82,blur_periodic(joint.astype(np.float32),.65))
    # Chamfer distance in actual texture pixels creates an eased, metre-scaled
    # edge. The 6mm depth does not depend on source brightness.
    outer = np.where(joint,0,1000).astype(np.float32)
    for _ in range(8):
        outer=np.minimum.reduce([outer]+[np.roll(np.roll(outer,y,0),x,1)+math.hypot(x,y)
                                         for x,y in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]])
    groove = 1-smoothstep(0,BEVEL_METRES/PIXEL_METRES,outer)
    groove = blur_periodic(groove,.5)
    rng = np.random.default_rng(20260926)
    noise = blur_periodic(rng.normal(size=(N,N)).astype(np.float32),2.2)
    noise /= noise.std()
    broad = blur_periodic(rng.normal(size=(N,N)).astype(np.float32),14)
    broad /= broad.std()
    # Sub-millimetre top relief, with narrower amplitude in filled dusty joints.
    top_relief = np.clip(noise*.000075 + broad*.00009,-.0003,.0003)
    height = -JOINT_DEPTH*groove + top_relief*(1-.8*groove)
    roughness = np.clip(.76 + .009*broad + .07*groove + .10*joint_soft,.70,.96)

    scene = bpy.data.scenes.new('Ward Paving V1 source maps')
    scene.view_settings.view_transform = 'Raw'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    scene.render.image_settings.color_mode = 'RGB'
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    images = [save_data(scene,'Height-metres',height,depth='32',file_format='OPEN_EXR'),
              save_data(scene,'Height-normalized',(height+.008)/HEIGHT_ENCODING_METRES),
              save_data(scene,'Joint-classification',joint_soft),
              save_data(scene,'Roughness',roughness),
              save_data(scene,'Corridor-guard',corridor.astype(np.float32))]
    packed=np.zeros((N,N,4),np.float32)
    packed[:,:,3]=1-roughness
    packed_image=bpy.data.images.new('WardPavingV1_MetallicSmoothness',width=N,height=N,alpha=True,float_buffer=True)
    packed_image.colorspace_settings.name='Non-Color'
    packed_image.pixels.foreach_set(packed[::-1].ravel());packed_image.update()
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.image_settings.color_depth='16'
    packed_image.save_render(str(OUT/'MetallicSmoothness.png'),scene=scene);images.append(packed_image)
    # Inspection data: green shows accepted joints, magenta is the corridor
    # perimeter. The unchanged source albedo is separately preserved byte-for-byte.
    overlay=rgb.copy();overlay[joint]=overlay[joint]*.25+np.array([.1,.9,.15])*.75
    border=corridor & ~erode(corridor);overlay[border]=np.array([1,.1,.8])
    images.append(save_data(scene,'Joint-review-overlay',overlay,depth='8'))
    bpy.data.libraries.write(str(OUT/'paving-source-maps.blend'),{scene,*images},fake_user=True)
    report=dict(status='Technical source maps authored; normal bake and Unity audition pending',
                blender=bpy.app.version_string,source=str(SOURCE),sourceSha256=source_hash,
                width=N,height=N,repeatMetres=EXTENT_METRES,sourceTexelsPerMetre=N/EXTENT_METRES,
                albedoPreservedSha256=hashlib.sha256((OUT/'Albedo-preserved.png').read_bytes()).hexdigest(),
                jointCorridorsTopLeftPixels=CORRIDORS,corridorHalfWidthPixels=10,
                classification='Encoded RGB luminance <0.56 only within manually traced corridors; morphological closing',
                jointDepthMetres=JOINT_DEPTH,bevelWidthMetres=BEVEL_METRES,
                topReliefRmsMetres=float(np.sqrt(np.mean(top_relief**2))),topReliefMaxMetres=float(np.max(np.abs(top_relief))),
                normalizedHeightScaleMetres=HEIGHT_ENCODING_METRES,normalizedHeightOffsetMetres=-.008,
                jointPixels=int(joint.sum()),jointCoverage=float(joint.mean()),
                excludedDarkPixelsOutsideCorridors=int(((luma<.56)&~corridor).sum()),
                roughnessRange=[float(roughness.min()),float(roughness.max())],
                normalBake='Not yet baked; intended Cycles tangent bake from physical-height Bump on6m plane',
                originalScene=original_scene.name,originalObjectsUnchanged=original_objects==[(o.name,o.as_pointer()) for o in original_scene.objects],
                activeSceneUnchanged=bpy.context.scene==original_scene)
    (OUT/'source-maps.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='jointCorridorsTopLeftPixels'},indent=2))


main()
