"""Create an auditable URP 17.6 Lit derivative and original editable sign artwork.

Run with: uv run --with cairosvg python unity/tools/prepare_weathering_assets.py
The generated ImageGen atlas remains unmodified, including its source alpha.
"""
from pathlib import Path
import json, shutil
import cairosvg

REPO = Path(__file__).resolve().parents[2]
PROJECT = REPO / 'unity/AthenHill'
OUT = PROJECT / 'Assets/AthenHill/Art/Weathering'
REF = REPO / 'refs/weathering_20260908'
PACKAGE = next((PROJECT / 'Library/PackageCache').glob('com.unity.render-pipelines.universal@*'))
assert json.loads((PACKAGE / 'package.json').read_text())['version'] == '17.6.0'
OUT.mkdir(parents=True, exist_ok=True)
REF.mkdir(parents=True, exist_ok=True)

# Retain Unity's complete Lit lighting, normal maps, shadow and depth passes.
# This pass changes albedo/smoothness only, in the project's Forward renderer.
shader = (PACKAGE / 'Shaders/Lit.shader').read_text()
shader = shader.replace('Shader "Universal Render Pipeline/Lit"', 'Shader "Athen Hill/Weathered Lit"')
shader = shader.replace('    Properties\n    {', '''    Properties
    {
        _WearStrength("Broad dust variation", Range(0,1)) = 0.42
        _WearScale("Variation per metre", Float) = 0.22
        _BaseWear("Sheltered wall base dirt", Range(0,1)) = 0
        _WearTint("Dust stain multiplier", Color) = (0.57,0.52,0.44,1)''')
shader = shader.replace('Packages/com.unity.render-pipelines.universal/Shaders/LitInput.hlsl', 'WardLitInput.hlsl')
shader = shader.replace('Packages/com.unity.render-pipelines.universal/Shaders/LitForwardPass.hlsl', 'WardLitForwardPass.hlsl')
# Use ordinary property inspector so wear controls remain visible and editable.
shader = shader.replace('CustomEditor "UnityEditor.Rendering.Universal.ShaderGUI.LitShader"', '')
(OUT / 'WeatheredLit.shader').write_text(shader)
inputs = (PACKAGE / 'Shaders/LitInput.hlsl').read_text().replace('CBUFFER_END', 'half _WearStrength, _WearScale, _BaseWear;\nhalf4 _WearTint;\nCBUFFER_END', 1)
(OUT / 'WardLitInput.hlsl').write_text(inputs)
forward = (PACKAGE / 'Shaders/LitForwardPass.hlsl').read_text().replace('#include "LitInput.hlsl"', '#include "WardLitInput.hlsl"\n#define REQUIRES_WORLD_SPACE_POS_INTERPOLATOR')
noise = '''
// Original world-space scalar mask: broad accumulations stay independent of tile UVs.
float WardHash(float3 p) { p = frac(p * .1031); p += dot(p,p.yzx + 33.33); return frac((p.x+p.y)*p.z); }
float WardNoise(float3 p)
{
    float3 a=floor(p), f=frac(p); f=f*f*(3-2*f);
    return lerp(lerp(lerp(WardHash(a),WardHash(a+float3(1,0,0)),f.x),lerp(WardHash(a+float3(0,1,0)),WardHash(a+float3(1,1,0)),f.x),f.y),
                lerp(lerp(WardHash(a+float3(0,0,1)),WardHash(a+float3(1,0,1)),f.x),lerp(WardHash(a+float3(0,1,1)),WardHash(a+1),f.x),f.y),f.z);
}
'''
forward = forward.replace('// keep this file in sync', noise + '\n// keep this file in sync', 1)
forward = forward.replace('    InitializeStandardLitSurfaceData(input.uv, surfaceData);', '''    InitializeStandardLitSurfaceData(input.uv, surfaceData);
    float3 wardP = input.positionWS * _WearScale;
    float broad = WardNoise(wardP + float3(8.2,1.1,3.7));
    float broken = WardNoise(wardP*3.17 + float3(1.2,7.1,2.3));
    float stain = smoothstep(.24,.78,broad*.74+broken*.26)*_WearStrength;
    float baseDirt = (1-smoothstep(.08,1.35,input.positionWS.y)) * _BaseWear * smoothstep(.25,.7,broken);
    float wear = saturate(stain+baseDirt);
    surfaceData.albedo *= lerp(half3(1,1,1),_WearTint.rgb,wear);
    surfaceData.smoothness *= 1-wear*.55;''')
(OUT / 'WardLitForwardPass.hlsl').write_text(forward)
graph = (PACKAGE / 'Shaders/Decal.shadergraph').read_text().replace('"affectsNormalBlend": true','"affectsNormalBlend": false').replace('"affectsNormal": true','"affectsNormal": false')
(OUT / 'WardDecal.shadergraph').write_text(graph)
shutil.copy2(PACKAGE / 'LICENSE.md', OUT / 'Unity-LICENSE.md')

# Authored vector sources keep all text exact and editable. Wear is a fixed mask,
# not rasterized fake type from image generation.
def sign(name, lines, ink, paper=None, subtitle=''):
    background = f'<path d="M34 28 L984 22 L999 696 L948 702 L914 739 L48 750 L20 684 Z" fill="{paper}"/>' if paper else ''
    line_size = 70 if len(lines)>2 else 95
    texts = ''.join(f'<text x="512" y="{180+i*line_size*1.15}" font-size="{line_size}" text-anchor="middle">{t}</text>' for i,t in enumerate(lines))
    # Deliberate edge tears and discrete chips; actual letters remain readable.
    chips = ''.join(f'<rect x="{(i*137+29)%1010}" y="{(i*83+71)%750}" width="{3+i%7}" height="{2+i%3}" fill="black"/>' for i in range(320))
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="768" viewBox="0 0 1024 768">
<defs><mask id="wear"><rect width="1024" height="768" fill="white"/>{chips}</mask></defs>
<g mask="url(#wear)">{background}<g fill="{ink}" font-family="DejaVu Sans" font-weight="bold">{texts}<text x="512" y="650" font-size="30" letter-spacing="5" text-anchor="middle">{subtitle}</text></g>
<path d="M ninety 80" fill="none"/></g></svg>'''.replace('<path d="M ninety 80" fill="none"/>','')
    (REF / (name+'.svg')).write_text(svg)
    cairosvg.svg2png(bytestring=svg.encode(),write_to=str(OUT/(name+'.png')))
sign('TubeStencil',['QUANTUM TUBE','AUTHORITY','KEEP ACCESS CLEAR'],'#4a4536',subtitle='CARGO TRANSFER')
sign('WardenPoster',['WARD HOLDS.','TAKE YOUR','WATCH.'],'#463c2c','#bfa77a',subtitle='WARDENS')
sign('KaraveenNotice',['NO TUBE?','WE STILL','DELIVER.'],'#413d32','#b6ad8f',subtitle='KARAVEEN')
sign('FactoryGraffiti',['THE FACTORIES','NEVER HEARD','THE ORDERS STOPPED.'],'#5c4d3c')
sign('AquiferNotice',['AQUIFER ACCESS','REPORT ALL','LEAKS'],'#38554e','#b9b59a',subtitle='WATER MAINTENANCE')
print('Prepared URP derivative, unmodified atlas and five original vector notices.')
