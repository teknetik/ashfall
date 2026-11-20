"""Texture-aware quadric decimation with boundary preservation (pymeshlab), as art/colonist_back_20261120/decimate.py.
Run: ~/.local/state/ward-programme/heavy.sh uv run --with pymeshlab python decimate.py IN.obj OUT.obj FACES"""
import sys, pymeshlab
src, dst, faces = sys.argv[1], sys.argv[2], int(sys.argv[3])
ms = pymeshlab.MeshSet(); ms.load_new_mesh(src)
m = ms.current_mesh(); print('DECIMATE IN', m.vertex_number(), m.face_number())
if m.face_number() > faces:
    ms.meshing_decimation_quadric_edge_collapse_with_texture(targetfacenum=faces, qualitythr=0.5, extratcoordw=1.0,
        preserveboundary=True, boundaryweight=2.0, optimalplacement=True, preservenormal=True, planarquadric=True)
m = ms.current_mesh(); print('DECIMATE OUT', m.vertex_number(), m.face_number())
ms.save_current_mesh(dst, save_wedge_texcoord=True, save_vertex_normal=False, save_textures=False)
