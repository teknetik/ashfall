# Ring Gate — Meshy source

The user supplied the three-view concept in `references/turnaround.png` and
approved Meshy generation on 8 September 2026. The separate front, back and right
images are panel extractions, retaining the source's proportions and details.

Meshy MCP task `01a080b2-d7b6-7727-93b1-f10c1aa030a7` generated the textured
12,009-triangle asset using Meshy 7, a triangle topology target of 12,000 and 2K
PBR textures. This accepted model is `model/ring-gate.fbx` / `ring-gate.glb`.
Generation cost 30 credits.

The 5-credit remesh task `01a080bc-e9d3-71b6-8a69-d87adc1df63e` produced
`ring-gate-6k.*`. That 6,263-triangle result damaged the console, bollards and
platform silhouette and was rejected. It is retained for provenance and is not
used by the Unity scene. Total Meshy cost: 35 credits.

Unity uses the accepted FBX through an editable RingGate prefab and URP/Lit
material. It is normalized to 6.7 m high at the existing south-court location.
The model retains its open aperture, console and concave collision. One 44-triangle
authored city step supplies a wider approach tread; the complete prefab is
12,053 triangles. Source atlases and original downloads remain intact here.

The task manifest includes source options, file hashes and Unity paths. Review
evidence is in `unity/evidence/ring-gate/20260908` at the repository root.
