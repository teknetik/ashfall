"""Texture-aware quadric decimation with boundary preservation (pymeshlab), for the re-fitted armour pieces.
Run: ~/.local/state/ward-programme/heavy.sh uv run --with pymeshlab python art/colonist_back_20261120/decimate.py <piece> <faces>
Reads work/<piece>_fit.obj, writes work/<piece>_dec.obj."""
import sys, pymeshlab
H = '/home/teknetik/code/ao2/art/colonist_back_20261120/work/'
piece, faces = sys.argv[1], int(sys.argv[2])
ms = pymeshlab.MeshSet(); ms.load_new_mesh(H + f'{piece}_fit.obj')
m = ms.current_mesh(); print('IN', m.vertex_number(), m.face_number())
ms.meshing_decimation_quadric_edge_collapse_with_texture(targetfacenum=faces, qualitythr=0.5, extratcoordw=1.0,
    preserveboundary=True, boundaryweight=2.0, optimalplacement=True, preservenormal=True, planarquadric=True)
m = ms.current_mesh(); print('OUT', m.vertex_number(), m.face_number())
ms.save_current_mesh(H + f'{piece}_dec.obj', save_wedge_texcoord=True, save_vertex_normal=False, save_textures=False)
