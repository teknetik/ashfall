"""Author eight preserved-envelope plaster/masonry replacements in live Blender.

Execute through the existing live Blender MCP connection, never headless. This
script creates a new scene and new outputs; it does not edit Unity or delete any
existing Blender scene. The original eight meshes remain in a hidden collection.

The large failure shapes are deliberately drawn around construction joints and
water paths. There is no cell-noise colour or a population of circular cutouts.
Lime plaster is 12–20 mm above real irregular limestone courses; mortar is farther
recessed. The photo maps carry small-scale material character, geometry carries
construction. Unity world metres map to Blender (x, -z, y), preserving winding.
"""
import bpy
import bmesh
import hashlib
import json
import math
import random
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
from mathutils.geometry import tessellate_polygon

ROOT = Path('/home/teknetik/code/ao2')
OUT = ROOT / 'art/reference_street_20260910'
SOURCE = ROOT / 'art/building_weathering_20260909/unity-source.json'
CURRENT = OUT / 'building-source.json'
PHOTOS = ROOT / 'refs/quality_20260909/building-materials'
REVISION = 'hero-masonry-v3'
BLEND = OUT / (REVISION + '.blend')
assert not BLEND.exists(), 'Retain existing revisions; choose a new revision name.'
assert REVISION not in bpy.data.scenes, 'This authoring scene already exists.'

source_rows = {r['path']: r for r in json.loads(SOURCE.read_text())}
current_rows = {r['path']: r for r in json.loads(CURRENT.read_text())}
scene = bpy.data.scenes.new(REVISION)
bpy.context.window.scene = scene
scene.unit_settings.system = 'METRIC'
scene['reference'] = 'refs/reference-street/20260909/user-target.png'
scene['authoring_rule'] = 'Physical thin plaster over coursed masonry; no uniform procedural grunge.'
originals = bpy.data.collections.new('Original shells retained; hidden from export')
scene.collection.children.link(originals)
originals.hide_render = True
originals.hide_viewport = True
authored = bpy.data.collections.new('Editable thin plaster and real masonry')
scene.collection.children.link(authored)


def B(v):
    return Vector((v[0], -v[2], v[1]))


def U(v):
    return [round(v.x, 7), round(v.z, 7), round(-v.y, 7)]


def stable_seed(value):
    return int(hashlib.sha256(value.encode()).hexdigest()[:12], 16)


MATERIAL_SPECS = {
    'HeroLimePlaster': dict(asset='beige_wall_001', baseColor=[1.0, .97, .91, 1],
                            normalStrength=.7, uvScale=[1, 1], purpose='Quiet old lime plaster'),
    'HeroExposedStone': dict(asset='rock_surface', baseColor=[.94, .88, .77, 1],
                             normalStrength=.7, uvScale=[2, 2], purpose='Irregular limestone masonry'),
    'HeroMortar': dict(asset='rough_concrete', baseColor=[.66, .58, .46, 1],
                       normalStrength=.6, uvScale=[2, 2], purpose='Recessed gritty mineral joints'),
    'HeroBrokenPlaster': dict(asset='rough_concrete', baseColor=[.91, .84, .71, 1],
                               normalStrength=.6, uvScale=[2, 2], purpose='Exposed lime binder at broken edges'),
}
materials = {}
for key, spec in MATERIAL_SPECS.items():
    asset = spec['asset']
    m = bpy.data.materials.new(key + ' 20260910')
    m.use_nodes = True
    m.use_fake_user = True
    m['unity_key'] = key
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Metallic'].default_value = 0
    uv = m.node_tree.nodes.new('ShaderNodeTexCoord')
    scale = m.node_tree.nodes.new('ShaderNodeVectorMath')
    scale.operation = 'MULTIPLY'
    scale.inputs[1].default_value = (*spec['uvScale'], 1)
    m.node_tree.links.new(uv.outputs['UV'], scale.inputs[0])
    channels = {}
    for channel, suffix in [('BaseColor', 'diff'), ('Normal', 'nor_gl'), ('Roughness', 'rough')]:
        path = PHOTOS / asset / (asset + '_' + suffix + '_4k.png')
        assert path.exists(), str(path)
        n = m.node_tree.nodes.new('ShaderNodeTexImage')
        n.name = key + ' retained photographic ' + channel
        n.image = bpy.data.images.load(str(path), check_existing=True)
        n.image.colorspace_settings.name = 'sRGB' if channel == 'BaseColor' else 'Non-Color'
        n.extension = 'REPEAT'
        m.node_tree.links.new(scale.outputs['Vector'], n.inputs['Vector'])
        channels[channel] = n
    tone = m.node_tree.nodes.new('ShaderNodeMixRGB')
    tone.blend_type = 'MULTIPLY'
    tone.inputs[0].default_value = 1
    tone.inputs[2].default_value = spec['baseColor']
    m.node_tree.links.new(channels['BaseColor'].outputs['Color'], tone.inputs[1])
    m.node_tree.links.new(tone.outputs['Color'], bs.inputs['Base Color'])
    m.node_tree.links.new(channels['Roughness'].outputs['Color'], bs.inputs['Roughness'])
    normal = m.node_tree.nodes.new('ShaderNodeNormalMap')
    normal.inputs['Strength'].default_value = spec['normalStrength']
    m.node_tree.links.new(channels['Normal'].outputs['Color'], normal.inputs['Color'])
    m.node_tree.links.new(normal.outputs['Normal'], bs.inputs['Normal'])
    materials[key] = m


def area(poly):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1])) / 2


def clean(poly):
    result = []
    for p in poly:
        p = (float(p[0]), float(p[1]))
        if not result or math.dist(result[-1], p) > 1e-7:
            result.append(p)
    if len(result) > 1 and math.dist(result[0], result[-1]) < 1e-7:
        result.pop()
    return result if area(result) >= 0 else list(reversed(result))


def clip(poly, convex):
    """Clip an arbitrary drawn fracture against a convex original wall envelope."""
    result = clean(poly)
    for a, b in zip(clean(convex), clean(convex)[1:] + clean(convex)[:1]):
        previous, result = result, []
        if not previous:
            break
        signed = lambda p: (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
        for p, q in zip(previous, previous[1:] + previous[:1]):
            dp, dq = signed(p), signed(q)
            if dp >= -1e-8:
                result.append(p)
            if (dp >= -1e-8) != (dq >= -1e-8):
                t = dp / (dp - dq)
                result.append((p[0] + t*(q[0]-p[0]), p[1] + t*(q[1]-p[1])))
    return clean(result) if len(result) >= 3 else []


def inside(p, poly):
    yes = False
    for a, b in zip(poly, poly[1:] + poly[:1]):
        if (a[1] > p[1]) != (b[1] > p[1]):
            if p[0] < (b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0]:
                yes = not yes
    return yes


def intersect_boxes(a, b):
    return min(max(p[0] for p in a), max(p[0] for p in b)) >= max(min(p[0] for p in a), min(p[0] for p in b)) and min(max(p[1] for p in a), max(p[1] for p in b)) >= max(min(p[1] for p in a), min(p[1] for p in b))


def rough_outline(points, seed, amplitude=.017, spacing=.065):
    """Small fracture chips along an art-directed outline, never radial blobs."""
    rr = random.Random(seed)
    result = []
    for a, b in zip(points, points[1:] + points[:1]):
        length = math.dist(a, b)
        tangent = ((b[0]-a[0])/length, (b[1]-a[1])/length)
        count = max(1, math.ceil(length/spacing))
        for i in range(count):
            t = i/count
            displacement = 0 if i == 0 else rr.uniform(-amplitude, amplitude)
            result.append((a[0] + t*(b[0]-a[0])-tangent[1]*displacement,
                           a[1] + t*(b[1]-a[1])+tangent[0]*displacement))
    return clean(result)


def crack_ribbon(points, width):
    sides = [[], []]
    for i, p in enumerate(points):
        a, b = points[max(0, i-1)], points[min(len(points)-1, i+1)]
        length = math.dist(a, b)
        w = width * (1-.86*i/(len(points)-1)) / 2
        d = (-(b[1]-a[1])/length*w, (b[0]-a[0])/length*w)
        sides[0].append((p[0]+d[0], p[1]+d[1]))
        sides[1].append((p[0]-d[0], p[1]-d[1]))
    return clean(sides[0] + list(reversed(sides[1])))


# Horizontal coordinate is -Unity Z on west-facing walls and Unity X on north.
# The Field Supply network crosses the three existing module seams continuously.
field_network = rough_outline([
    (12.75,.42),(11.04,.42),(11.17,.69),(11.63,.86),(11.77,1.10),
    (11.84,1.35),(12.12,1.56),(12.02,1.84),(12.30,2.02),(12.15,2.26),
    (12.26,2.57),(12.06,2.84),(12.17,3.14),(11.91,3.48),(12.00,3.73),
    (11.79,3.92),(11.94,4.14),(11.59,4.33),(11.72,4.57),(11.38,4.91),
    (12.75,4.91)
], 1003)
field_branch = rough_outline([
    (11.66,4.28),(11.45,4.06),(11.27,4.01),(11.11,3.79),(10.77,3.68),
    (10.71,3.87),(11.03,3.96),(11.18,4.19),(11.42,4.22),(11.57,4.46)
], 1004, .009, .05)
gable_network = rough_outline([
    (5.18,4.77),(12.82,4.77),(12.82,4.91),(12.21,4.95),(11.84,4.90),
    (11.51,5.08),(11.16,5.03),(10.84,5.24),(10.53,5.19),(10.18,5.33),
    (9.99,5.19),(9.64,5.26),(9.46,5.10),(8.95,5.06),(8.74,5.15),
    (8.34,5.10),(8.14,5.22),(7.73,5.26),(7.52,5.12),(7.03,5.11),
    (6.74,4.99),(6.28,5.06),(5.75,4.94),(5.18,4.94)
], 1005, .014, .067)
north_corner_network = rough_outline([
    (16.74,.42),(17.90,.42),(17.74,.74),(17.90,1.03),(17.69,1.30),
    (17.90,1.54),(17.78,1.78),(18.00,2.06),(17.88,2.27),(18.14,2.53),
    (18.03,2.76),(18.34,3.01),(18.26,3.37),(18.54,3.63),(18.36,3.98),
    (18.67,4.16),(18.50,4.48),(18.83,4.82),(18.68,5.05),(18.94,5.31),
    (18.78,5.59),(19.08,5.88),(18.90,6.14),(19.20,6.52),(19.26,6.88),
    (18.85,6.88),(18.52,6.53),(18.51,6.21),(18.29,5.91),(18.41,5.65),
    (18.15,5.38),(18.25,5.12),(17.98,4.86),(18.10,4.58),(17.79,4.33),
    (17.90,4.12),(17.56,3.93),(17.67,3.66),(17.47,3.44),(17.53,3.08),
    (17.24,2.85),(17.39,2.58),(17.13,2.31),(17.24,2.06),(17.03,1.82),
    (17.11,1.55),(16.91,1.39),(16.74,1.53)
], 1101, .019, .075)
north_roof_network = rough_outline([
    (18.90,6.91),(22.10,6.91),(22.01,6.56),(21.74,6.57),(21.49,6.38),
    (21.21,6.47),(20.98,6.25),(20.64,6.35),(20.45,6.13),(20.13,6.29),
    (19.94,6.25),(19.65,6.47),(19.37,6.42),(19.08,6.63)
], 1102, .016, .071)

def pier_outline(a, b, seed, from_left):
    if from_left:
        points = [(a-.1,5.21),(a+.22,5.21),(a+.26,5.47),(a+.15,5.63),
                  (a+.32,5.84),(a+.23,6.02),(a+.45,6.28),(a+.35,6.40),
                  (a+.65,6.72),(a-.1,6.72)]
    else:
        points = [(b+.1,5.21),(b-.39,5.21),(b-.50,5.44),(b-.34,5.64),
                  (b-.48,5.82),(b-.25,6.04),(b-.36,6.23),(b-.12,6.45),
                  (b-.22,6.72),(b+.1,6.72)]
    return rough_outline(points, seed, .011, .05)

parapet_network = rough_outline([
    (14.10,7.83),(21.88,7.83),(21.88,7.60),(21.39,7.66),(21.05,7.57),
    (20.85,7.44),(20.51,7.52),(20.26,7.34),(20.00,7.48),(19.54,7.58),
    (19.20,7.50),(18.84,7.67),(18.36,7.62),(18.00,7.51),(17.78,7.33),
    (17.52,7.44),(17.38,7.25),(17.15,7.37),(16.95,7.56),(16.50,7.62),
    (16.16,7.57),(15.74,7.70),(15.39,7.59),(15.04,7.68),(14.68,7.59),
    (14.10,7.68)
], 1105, .01, .06)

FIELD_BASE = 'Ward shop architecture/field_supply/Masonry shell/field_supply Front masonry segment 4 '
REGIONS = [
    dict(path=FIELD_BASE+str(i), normal=(-1,0,0), horizontal=(0,0,-1),
         patches=[field_network, field_branch], seed=71, family='field_supply',
         cracks=[[(11.54,4.35),(11.46,4.57),(11.21,4.68),(11.24,4.82)],
                 [(12.05,2.85),(11.92,2.99),(11.89,3.17),(11.66,3.33)]])
    for i in range(3)
] + [
    dict(path='Ward shop architecture/field_supply/Pitched metal roof/field_supply Front gable',
         normal=(-1,0,0), horizontal=(0,0,-1), patches=[gable_network], seed=79,
         family='field_supply', cracks=[[(10.20,5.30),(10.07,5.42),(9.84,5.40),(9.71,5.50)],
                                       [(7.82,5.23),(7.89,5.35),(8.06,5.39)]]),
    dict(path='Phase 1 Finery frontage/Structure/North wall core', normal=(0,0,1),
         horizontal=(1,0,0), patches=[north_corner_network,north_roof_network],
         seed=83, family='finery',
         cracks=[[(18.48,4.47),(18.88,4.30),(19.08,4.05),(19.17,3.75),(19.47,3.59),
                  (19.40,3.24),(19.72,2.96)],
                 [(18.78,5.34),(19.13,5.19),(19.30,4.98),(19.62,4.86)],
                 [(20.46,6.20),(20.62,5.98),(20.50,5.76),(20.71,5.55)]]),
    dict(path='Phase 1 Finery frontage/Structure/Upper wall pier 1', normal=(-1,0,0),
         horizontal=(0,0,-1), patches=[pier_outline(18.82,19.905,1103,False)],
         seed=89, family='finery', cracks=[[(19.44,5.75),(19.14,5.86),(19.08,6.06),(18.88,6.22)]]),
    dict(path='Phase 1 Finery frontage/Structure/Upper wall pier 2', normal=(-1,0,0),
         horizontal=(0,0,-1), patches=[pier_outline(16.095,17.18,1104,True)],
         seed=97, family='finery', cracks=[[(16.43,5.87),(16.61,6.02),(16.62,6.23),(16.83,6.44)]]),
    dict(path='Phase 1 Finery frontage/Roof/Roof parapet end 16.84', normal=(-1,0,0),
         horizontal=(0,0,-1), patches=[parapet_network], seed=101, family='finery',
         cracks=[[(17.37,7.28),(17.56,7.19),(17.68,7.13)],
                 [(20.30,7.39),(20.47,7.27),(20.74,7.19)]])
]


def mesh_object(name, positions, faces, key, collection=authored):
    me = bpy.data.meshes.new(name)
    me.from_pydata([B(p) for p in positions], [], faces)
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-5)
    # Unity world-space export duplicates beveled seams within float precision.
    # Reconnect them before any normal orientation or solid Boolean operation.
    # Adaptive stone face triangles additionally meet unsplit chamfer edges:
    # split those exact T-junctions before welding, without moving the shape.
    if ' limestone ' in name:
        bm.verts.ensure_lookup_table()
        original_vertices=list(bm.verts)
        tree=KDTree(len(original_vertices))
        for i,v in enumerate(original_vertices):tree.insert(v.co,i)
        tree.balance()
        for edge in [e for e in bm.edges if e.is_boundary]:
            if not edge.is_valid:continue
            start,end=edge.verts
            a,b=start.co.copy(),end.co.copy();delta=b-a;length=delta.length
            if length<2e-5:continue
            hits=[]
            for co,index,distance in tree.find_range((a+b)*.5,length*.5+1e-5):
                v=original_vertices[index]
                if v==start or v==end:continue
                t=(co-a).dot(delta)/(length*length)
                if 1e-5/length<t<1-1e-5/length and (a+delta*t-co).length<1e-5:
                    hits.append((t,co.copy()))
            previous=1.0
            for t,co in sorted(hits,key=lambda hit:hit[0],reverse=True):
                if previous-t<1e-5/length:continue
                new_edge,new_vert=bmesh.utils.edge_split(edge,start,t/previous)
                new_vert.co=co
                edge=next(e for e in start.link_edges if new_vert in e.verts)
                previous=t
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    me.materials.append(materials[key])
    ob['material_key'] = key
    return ob


def uv_project(ob, horizontal=None, shift=(0,0)):
    me = ob.data
    uv = me.uv_layers.get('UV0 four metre source') or me.uv_layers.new(name='UV0 four metre source')
    for f in me.polygons:
        axis = max(range(3), key=lambda i: abs(f.normal[i]))
        for li in f.loop_indices:
            p = U(me.vertices[me.loops[li].vertex_index].co)
            # Front coordinates already match the dominant-face mapping below.
            # Perpendicular bevel/edge faces need their own metric projection.
            if False:
                u = sum(p[i]*horizontal[i] for i in range(3))
                v = p[1]
            elif axis == 0:
                u, v = -p[2], p[1]
            elif axis == 1:
                u, v = p[0], p[1]
            else:
                u, v = p[0], -p[2]
            uv.data[li].uv = (u/4+shift[0], v/4+shift[1])


def world(region, point, depth):
    return Vector(region['origin']) + Vector(region['horizontal'])*point[0] + Vector((0,point[1],0)) + Vector(region['normal'])*depth


def prism(name, region, polygon, front, back, key):
    polygon = clean(polygon)
    n = len(polygon)
    positions = [world(region,p,d) for d in (front,back) for p in polygon]
    faces = [tuple(range(n)), tuple(reversed(range(n,2*n)))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    ob = mesh_object(name, positions, faces, key)
    uv_project(ob, region['horizontal'])
    return ob


solid_records=[]
def solid_stats(ob):
    bm=bmesh.new();bm.from_mesh(ob.data)
    result=dict(name=ob.name,vertices=len(bm.verts),faces=len(bm.faces),
        boundaryEdges=sum(e.is_boundary for e in bm.edges),
        nonManifoldEdges=sum(not e.is_manifold for e in bm.edges),
        nonContiguousEdges=sum(e.is_manifold and not e.is_contiguous for e in bm.edges),
        signedVolume=bm.calc_volume(signed=True),
        min=[min(v.co[i] for v in bm.verts) for i in range(3)],
        max=[max(v.co[i] for v in bm.verts) for i in range(3)])
    bm.free();return result

def require_solid(ob):
    result=solid_stats(ob)
    assert result['boundaryEdges']==0 and result['nonManifoldEdges']==0 and result['nonContiguousEdges']==0 and result['signedVolume']>0, json.dumps(result)
    return result

def boolean(ob, cutter):
    before=require_solid(ob);tool=require_solid(cutter)
    bpy.context.view_layer.objects.active = ob
    modifier = ob.modifiers.new('Verified closed thin missing plaster', 'BOOLEAN')
    modifier.operation = 'DIFFERENCE'
    modifier.solver = 'EXACT'
    modifier.object = cutter
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    after=require_solid(ob)
    assert after['signedVolume']<=before['signedVolume']+1e-5,'Difference unexpectedly adds volume'
    assert all(after['min'][i]>=before['min'][i]-1e-5 and after['max'][i]<=before['max'][i]+1e-5 for i in range(3)),'Difference escapes original bounds'
    solid_records.append(dict(operation='DIFFERENCE',source=ob.get('source_path'),before=before,cutter=tool,after=after))
    bpy.data.objects.remove(cutter, do_unlink=True)


def build_stone(region, polygon, rng, stone_index):
    """Hand-cut edges and a subtly uneven face, all behind original plaster plane."""
    polygon = clean(polygon)
    centroid = (sum(p[0] for p in polygon)/len(polygon), sum(p[1] for p in polygon)/len(polygon))
    inset = rng.uniform(.005,.011)
    inner = []
    for p in polygon:
        distance = max(math.dist(p,centroid),1e-6)
        amount = min(inset/distance,.2)
        inner.append((p[0]+(centroid[0]-p[0])*amount,p[1]+(centroid[1]-p[1])*amount))
    front = -rng.uniform(.014,.020)
    n = len(polygon)
    positions = [world(region,p,front-.007) for p in polygon]
    positions += [world(region,p,front) for p in inner]
    positions += [world(region,p,-.058) for p in polygon]
    faces = []
    for i in range(n):
        j=(i+1)%n
        faces += [(i,j,n+j,n+i),(i,2*n+i,2*n+j,j)]
    faces.append(tuple(reversed(range(2*n,3*n))))
    # Subdivide the visible face into 4–6 cm facets with continuous millimetre relief.
    # This is geometric surface irregularity; colour comes only from the photo map.
    phase = rng.uniform(0,math.tau)
    def segment_distance(p,a,b):
        length_squared=(b[0]-a[0])**2+(b[1]-a[1])**2
        t=max(0,min(1,((p[0]-a[0])*(b[0]-a[0])+(p[1]-a[1])*(b[1]-a[1]))/max(length_squared,1e-15)))
        return math.dist(p,(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t))
    def relief(p):
        edge = min(segment_distance(p,a,b) for a,b in zip(inner,inner[1:]+inner[:1]))
        amp = min(1,edge/.035)*.0018
        return amp*(math.sin(p[0]*20.7+phase)*math.cos(p[1]*23.3-phase)
                    +.38*math.sin(p[0]*57.1+p[1]*43.2+phase))
    def subdivide(a,b,c,depth=0):
        sides=[math.dist(a,b),math.dist(b,c),math.dist(c,a)]
        if max(sides)>.062 and depth<10:
            k=sides.index(max(sides))
            q=[a,b,c];x=q[k];y=q[(k+1)%3];z=q[(k+2)%3]
            midpoint=((x[0]+y[0])/2,(x[1]+y[1])/2)
            subdivide(x,midpoint,z,depth+1);subdivide(midpoint,y,z,depth+1)
        else:
            index=len(positions)
            positions.extend(world(region,p,front+relief(p)) for p in (a,b,c))
            faces.append((index,index+1,index+2))
    for a,b in zip(inner,inner[1:]+inner[:1]):
        subdivide(centroid,a,b)
    ob=mesh_object(region['label']+' limestone '+str(stone_index),positions,faces,'HeroExposedStone')
    shift=(rng.uniform(-1,1),rng.uniform(-1,1))
    uv_project(ob,region['horizontal'],shift)
    ob['stone_front_below_plaster_m']=-front
    ob['block_texture_offset_uv']=shift
    ob['family']=region['family']
    # Face normals use weighted shared vertices; chamfer ring remains a sharp edge.
    for f in ob.data.polygons:
        f.use_smooth = f.index > 2*n
    return ob


replacements=[]
additions=[]
region_records=[]
for region in REGIONS:
    path=region['path']
    assert path in source_rows and path in current_rows, path
    row=source_rows[path]
    region['label']=row['name']
    normal=Vector(region['normal'])
    horizontal=Vector(region['horizontal'])
    plane=max(Vector(p).dot(normal) for p in row['positions'])
    region['origin']=normal*plane
    projected=[(Vector(p).dot(horizontal),p[1]) for p in row['positions']]
    lo=(min(p[0] for p in projected),min(p[1] for p in projected))
    hi=(max(p[0] for p in projected),max(p[1] for p in projected))
    boundary=clean([(lo[0],lo[1]),(hi[0],lo[1]),((lo[0]+hi[0])/2,hi[1])]) if 'gable' in path else [(lo[0],lo[1]),(hi[0],lo[1]),(hi[0],hi[1]),(lo[0],hi[1])]
    indices=row['indices']
    faces=[tuple(indices[i:i+3]) for i in range(0,len(indices),3)]
    original=mesh_object('ORIGINAL '+row['name'],row['positions'],faces,'HeroLimePlaster',originals)
    original['source_path']=path
    ob=mesh_object(row['name']+' thin layered plaster',row['positions'],faces,'HeroLimePlaster')
    ob['source_path']=path
    ob['family']=region['family']
    ob['preserved_shell_envelope']=True
    uv_project(ob)
    patches=[clip(p,boundary) for p in region['patches']]
    patches=[p for p in patches if len(p)>=3 and abs(area(p))>.0001]
    cracks=[clip(crack_ribbon(p,.0045),boundary) for p in region['cracks']]
    cracks=[p for p in cracks if len(p)>=3 and abs(area(p))>1e-6]
    for i,patch in enumerate(patches+cracks):
        cutter=prism('TEMP exact thin plaster cutter',region,patch,.016,-.043,'HeroMortar')
        boolean(ob,cutter)
        mortar=prism(row['name']+' recessed mortar '+str(i),region,patch,-.036,-.048,'HeroMortar')
        mortar['family']=region['family']
        additions.append(mortar)
    uv_project(ob)
    # Retain crisp broken perimeter without a thick bevel modifier.
    replacements.append(ob)

    # Courses follow continuous physical heights across the three Field modules.
    # Stones have staggered joints and deliberate asymmetric clipped corners.
    stone_count=0
    y=.38
    course=0
    while y<hi[1]+.5:
        rr=random.Random(region['seed']*10000+course)
        height=rr.uniform(.255,.405)
        if y+height>=lo[1] and y<=hi[1]:
            u=math.floor(lo[0])-1 + (.28 if course%2 else 0)
            stone=0
            while u<hi[0]+.8:
                width=rr.uniform(.40,.83)
                gap=rr.uniform(.014,.027)
                left,right=u+gap/2,u+width-gap/2
                bottom,top=y+gap/2,y+height-gap/2
                ch=[rr.uniform(.011,.037) for _ in range(8)]
                poly=[(left+ch[0],bottom),(right-ch[1],bottom+rr.uniform(-.004,.004)),
                      (right,bottom+ch[2]),(right-rr.uniform(0,.012),top-ch[3]),
                      (right-ch[4],top),(left+ch[5],top+rr.uniform(-.004,.004)),
                      (left,top-ch[6]),(left+rr.uniform(0,.012),bottom+ch[7])]
                poly=clip(poly,boundary)
                if len(poly)>=3 and abs(area(poly))>.001 and any(intersect_boxes(poly,p) for p in patches+cracks):
                    stone_ob=build_stone(region,poly,rr,stone_count)
                    additions.append(stone_ob);stone_count+=1
                u+=width;stone+=1
        y+=height;course+=1

    # Adhered flakes remain attached to the break edge. They never float in the
    # centre of a patch or project beyond the old wall envelope.
    flakes=0
    rr=random.Random(stable_seed(path))
    for patch in patches:
        for i,(a,b) in enumerate(zip(patch,patch[1:]+patch[:1])):
            if i%7!=3 or math.dist(a,b)<.018:
                continue
            mid=((a[0]+b[0])/2,(a[1]+b[1])/2)
            if min(mid[0]-lo[0],hi[0]-mid[0],mid[1]-lo[1],hi[1]-mid[1])<.065:
                continue
            length=math.dist(a,b)
            normal2=(-(b[1]-a[1])/length,(b[0]-a[0])/length)
            reach=rr.uniform(.011,.028)
            tip=(mid[0]+normal2[0]*reach,mid[1]+normal2[1]*reach)
            flake=prism(row['name']+' attached lime flake '+str(flakes),region,[a,b,tip],-.001,-rr.uniform(.010,.016),'HeroBrokenPlaster')
            flake['family']=region['family']
            additions.append(flake);flakes+=1
    region_records.append(dict(sourcePath=path,expectedCurrentMeshPath=current_rows[path]['meshPath'],
        originalEnvelope=row['bounds'],patchAreaM2=sum(abs(area(p)) for p in patches),
        originalFrontAreaM2=abs(area(boundary)),limestoneBlocks=stone_count,attachedFlakes=flakes,
        patches=patches,cracks=cracks,plasterThicknessM=[.012,.020],mortarRecessM=.036))
    print(json.dumps({'completedRegion':path,'stones':stone_count,'flakes':flakes}),flush=True)


def export(ob,source=None):
    me=ob.data
    me.calc_loop_triangles()
    uv=me.uv_layers.active
    positions=[];normals=[];uvs=[];indices=[]
    for triangle in me.loop_triangles:
        base=len(positions)
        for li in triangle.loops:
            loop=me.loops[li]
            positions.append(U(ob.matrix_world@me.vertices[loop.vertex_index].co))
            normals.append(U(me.corner_normals[li].vector.normalized()))
            uvs.append([round(float(v),7) for v in uv.data[li].uv])
        indices.extend((base,base+1,base+2))
    assert all(math.isfinite(v) for p in positions+normals+uvs for v in p),ob.name
    return dict(name=ob.name,sourcePath=source,family=ob.get('family',''),
                material=ob['material_key'],positions=positions,normals=normals,uv=uvs,
                indices=indices,castsShadow=True)


def uv_proof(ob):
    me=ob.data;me.calc_loop_triangles();uv=me.uv_layers.active.data;bad=[]
    for t in me.loop_triangles:
        if t.area<1e-10:continue
        a,b,c=[uv[li].uv for li in t.loops]
        area2=abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))*.5
        if area2/t.area<1e-4:bad.append(t.index)
    assert not bad,ob.name+' has degenerate material UV triangles '+str(bad[:10])
    return dict(name=ob.name,triangles=len(me.loop_triangles),degenerateUvTriangles=len(bad))
uv_records=[uv_proof(ob) for ob in replacements+additions]
(OUT/(REVISION+'-uv-proof.json')).write_text(json.dumps(uv_records,indent=2))
geometry_proof=[dict(kind='replacement',**require_solid(ob)) for ob in replacements]
geometry_proof += [dict(kind='addition',**require_solid(ob)) for ob in additions]
(OUT/(REVISION+'-geometry-proof.json')).write_text(json.dumps(dict(cuts=solid_records,allParts=geometry_proof),indent=2))
parts=[export(ob,ob['source_path']) for ob in replacements]
addition_parts=[export(ob) for ob in additions]
(OUT/(REVISION+'-replacements.json')).write_text(json.dumps(parts,separators=(',',':')))
(OUT/(REVISION+'-additions.json')).write_text(json.dumps(addition_parts,separators=(',',':')))
disabled=[]
for region in REGIONS:
    label=source_rows[region['path']]['name']
    for path,row in current_rows.items():
        if row['active'] and row['name'].startswith(label+' exposed substrate '):
            disabled.append(dict(path=path,expectedMeshPath=row['meshPath'],reason='Old 45 mm single flat substrate replaced by real coursed masonry'))
quiet_targets=[dict(path=path,expectedMeshPath=row['meshPath'],expectedMaterialPaths=[m['path'] for m in row['materials']])
               for path,row in current_rows.items()
               if row['active'] and any(m['name']=='ReferencePlaster' for m in row['materials'])]
assert len(quiet_targets)==35,'Saved source plaster roster changed; inspect before proceeding.'
material_contract={}
for key,spec in MATERIAL_SPECS.items():
    asset=spec['asset']
    material_contract[key]=dict(spec,uv0PhysicalTileM=4,metallic=0,
        shader='Universal Render Pipeline/Lit',sRGBBaseColor=True,linearNormalAndPacked=True,
        normalConvention='OpenGL +Y; Unity TextureImporterType.NormalMap',maxTextureSize=4096,
        normalMap= str((PHOTOS/asset/(asset+'_nor_gl_4k.png')).relative_to(ROOT)),
        baseMap= str((PHOTOS/asset/(asset+'_diff_4k.png')).relative_to(ROOT)),
        roughnessMap= str((PHOTOS/asset/(asset+'_rough_4k.png')).relative_to(ROOT)),
        packedConvention='MetallicGlossMap R=0 A=1-roughness; _Smoothness=1',
        sourceProvenance=str((PHOTOS/asset/'download-manifest.json').relative_to(ROOT)))
manifest=dict(revision=REVISION,blender=bpy.app.version_string,
    reference='refs/reference-street/20260909/user-target.png',
    currentSourceSha256=hashlib.sha256(CURRENT.read_bytes()).hexdigest(),
    originalSourceSha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    replacementsFile=REVISION+'-replacements.json',additionsFile=REVISION+'-additions.json',
    replacementCount=len(parts),additionCount=len(addition_parts),
    triangles=sum(len(p['indices'])//3 for p in parts+addition_parts),
    regions=region_records,disableOldSubstrates=disabled,
    quietPlasterMaterialTargets=quiet_targets,materials=material_contract,
    preserve=['All original source files and meshes','All source transform paths and transforms',
              'All colliders and controller openings','Doors, window openings, signs and gameplay roots'],
    geometryNotes=['V3 additionally projects each material face along its dominant axis, preserving existing front UVs while giving perpendicular edges a non-degenerate metric UV area.', 'V2 repair: weld original float seams at10micrometres before orientation, close stone/chamfer T-junctions without changing surface positions, assert closed outward topology and nonincreasing volume/bounds for every difference.', 'Original exterior shell envelopes retained; shallow missing plaster only.',
                   'Irregular blocks are clipped to the wall envelope and occluded by surviving plaster.',
                   'Masonry courses continue across existing Field Supply segment boundaries.',
                   'No mesh subdivision is used to claim new source detail; exposed stone faces receive actual millimetre relief.',
                   'Large colour wear comes from retained photographs, not procedural pale spots.'],
    requiresNativeReview=True,qualityAccepted=False)
(OUT/(REVISION+'-manifest.json')).write_text(json.dumps(manifest,indent=2))

scene.render.engine='BLENDER_EEVEE_NEXT'
scene.render.resolution_x=1600;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.world=bpy.data.worlds.new(REVISION+' review sky')
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.33,.43,.55,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.45
light_data=bpy.data.lights.new(REVISION+' review sunlight','SUN')
light_data.energy=2.2;light_data.angle=.06
light=bpy.data.objects.new(REVISION+' review sunlight',light_data)
scene.collection.objects.link(light);light.rotation_euler=(.55,-.6,-.7)
camera_data=bpy.data.cameras.new(REVISION+' review camera')
camera=bpy.data.objects.new(REVISION+' review camera',camera_data)
scene.collection.objects.link(camera);scene.camera=camera;camera_data.lens=46
camera.location=B((9.4,4.0,-7.8))
camera.rotation_euler=(B((18.2,3.7,-13.8))-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(OUT/(REVISION+'-source-review.png'))
bpy.data.libraries.write(str(BLEND),{scene},fake_user=True)
print(json.dumps({'complete':True,'revision':REVISION,'replacements':len(parts),
                  'additions':len(addition_parts),'triangles':manifest['triangles'],
                  'manifest':str(OUT/(REVISION+'-manifest.json'))}),flush=True)
