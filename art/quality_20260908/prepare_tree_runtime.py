"""Technical channel packing and pinned URP shader derivation; source images are retained."""
from pathlib import Path
import hashlib, json, shutil, re
import numpy as np
from PIL import Image

ROOT=Path('/home/teknetik/code/ao2')
SRC=ROOT/'refs/quality_20260908/tree/jacaranda_tree/textures'
OUT=ROOT/'unity/AthenHill/Assets/AthenHill/Art/HeroTree'
SHADER=ROOT/'unity/AthenHill/Assets/AthenHill/Shaders/WardTree'
PACKAGE=ROOT/'unity/AthenHill/Library/PackageCache/com.unity.render-pipelines.universal@b9a66914c09e'
OUT.mkdir(parents=True,exist_ok=True);SHADER.mkdir(parents=True,exist_ok=True)
rows=[]
for part in ('trunk','branches','leaves'):
    prefix='jacaranda_tree_'+part
    albedo=Image.open(SRC/(prefix+'_diff_4k.png')).convert('RGBA')
    if part=='leaves':
        alpha=Image.open(SRC/(prefix+'_alpha_4k.png')).convert('L')
        assert alpha.size==albedo.size
        albedo.putalpha(alpha)
    albedo.save(OUT/(part+'-albedo.png'))
    rough=np.array(Image.open(SRC/(prefix+'_rough_4k.png')).convert('L'))
    mask=np.zeros((*rough.shape,4),dtype=np.uint8);mask[:,:,3]=255-rough
    Image.fromarray(mask).save(OUT/(part+'-metallic-smoothness.png'))
    shutil.copy2(SRC/(prefix+'_nor_gl_4k.png'),OUT/(part+'-normal.png'))
    rows.append({'part':part,'size':albedo.size,'albedoRGB':'unchanged original bytes per pixel','alpha':'original leaf opacity map' if part=='leaves' else 'original alpha','metallic':0,'smoothness':'255 minus original linear roughness red channel','normal':'byte-identical original OpenGL normal'})
for lod,filename in [(0,'WardTree_LOD0_repaired.fbx'),(1,'WardTree_LOD1.fbx')]:
    shutil.copy2(ROOT/'art/quality_20260908/tree'/filename,OUT/('WardTree_LOD%d.fbx'%lod))

shader=(PACKAGE/'Shaders/Lit.shader').read_text().replace('Shader "Universal Render Pipeline/Lit"','Shader "Athen Hill/Ward Tree"',1)
shader=shader.replace('    Properties\n    {','    Properties\n    {\n        _WardWindStrength("Crown sway in metres", Range(0, .3)) = .07\n        _WardLeafFlutter("Leaf flutter in metres", Range(0, .04)) = 0\n        _WardTranslucency("Leaf light transmission", Range(0, .5)) = 0',1)
files=['LitInput.hlsl','LitForwardPass.hlsl','LitGBufferPass.hlsl','ShadowCasterPass.hlsl','DepthOnlyPass.hlsl','LitDepthNormalsPass.hlsl']
functions={'LitForwardPass.hlsl':'LitPassVertex','LitGBufferPass.hlsl':'LitGBufferPassVertex','ShadowCasterPass.hlsl':'ShadowPassVertex','DepthOnlyPass.hlsl':'DepthOnlyVertex','LitDepthNormalsPass.hlsl':'DepthNormalsVertex'}
wind='''
// Wind uses the existing reduced-motion-aware city clock in every geometry pass.
float _AthenAtmosphereTime;
float _AthenAtmospherePreviousTime;
float3 WardTreeWind(float3 positionOS, float windTime)
{
    float3 p = TransformObjectToWorld(positionOS);
    float bend = smoothstep(4.5, 16.5, p.y);
    float phase = windTime * .73 + p.x * .12 + p.z * .09;
    float broad = sin(phase) * .7 + sin(phase * .47 + 1.8) * .3;
    float flutter = sin(windTime * 2.4 + p.x * 1.7 + p.z * 1.3) * _WardLeafFlutter;
    p.xz += float2(.82, .57) * (broad * _WardWindStrength * bend + flutter * bend);
    return TransformWorldToObject(p);
}
'''
for name in files:
    text=(PACKAGE/'Shaders'/name).read_text()
    if name=='LitInput.hlsl':
        text=text.replace('CBUFFER_END','half _WardWindStrength;\nhalf _WardLeafFlutter;\nhalf _WardTranslucency;\nCBUFFER_END',1)
        at=text.rfind('#endif')
        text=text[:at]+wind+'\n'+text[at:]
    else:
        start=text.index('Varyings '+functions[name]+'(')
        marker='UNITY_SETUP_INSTANCE_ID(input);'
        at=text.index(marker,start)+len(marker)
        position='position' if name=='DepthOnlyPass.hlsl' else 'positionOS'
        text=text[:at]+f'\n    input.{position}.xyz = WardTreeWind(input.{position}.xyz, _AthenAtmosphereTime);'+text[at:]
    if name=='LitForwardPass.hlsl':
        text=text.replace('    Varyings input\n    , out half4 outColor','    Varyings input\n    , FRONT_FACE_TYPE face : FRONT_FACE_SEMANTIC\n    , out half4 outColor',1)
        marker='InitializeInputData(input, surfaceData.normalTS, inputData);'
        text=text.replace(marker,marker+'\n    if (_WardTranslucency > 0) inputData.normalWS *= IS_FRONT_VFACE(face, 1.0h, -1.0h);',1)
        marker='half4 color = UniversalFragmentPBR(inputData, surfaceData);'
        text=text.replace(marker,marker+'''\n    if (_WardTranslucency > 0)
    {
        Light canopySun = GetMainLight(TransformWorldToShadowCoord(inputData.positionWS));
        half backLight = saturate(dot(-canopySun.direction, inputData.normalWS));
        color.rgb += surfaceData.albedo * canopySun.color * backLight * canopySun.shadowAttenuation * _WardTranslucency;
    }''',1)
    if name=='LitDepthNormalsPass.hlsl':
        text=text.replace('    Varyings input\n    , out half4 outNormalWS','    Varyings input\n    , FRONT_FACE_TYPE face : FRONT_FACE_SEMANTIC\n    , out half4 outNormalWS',1)
        marker='float3 normalWS = normalize(input.normalWS);'
        text=text.replace(marker,marker+'\n        if (_WardTranslucency > 0) normalWS *= IS_FRONT_VFACE(face, 1.0, -1.0);',1)
        marker='outNormalWS = half4(NormalizeNormalPerPixel(normalWS), 0.0);'
        text=text.replace(marker,'if (_WardTranslucency > 0) normalWS *= IS_FRONT_VFACE(face, 1.0, -1.0);\n        '+marker,1)
    for other in files:
        text=text.replace('"Packages/com.unity.render-pipelines.universal/Shaders/'+other+'"','"'+other+'"')
    (SHADER/name).write_text('// Derived from Unity URP 17.6.0; Unity Companion License. See THIRD_PARTY_LICENSES.txt.\n'+text)
    shader=shader.replace('"Packages/com.unity.render-pipelines.universal/Shaders/'+name+'"','"'+name+'"')
motion=(PACKAGE/'ShaderLibrary/ObjectMotionVectors.hlsl').read_text()
marker='const VertexPositionInputs vertexInput = GetVertexPositionInputs(input.position.xyz);'
motion=motion.replace(marker,'float4 unmodifiedPosition = input.position;\n    input.position.xyz = WardTreeWind(input.position.xyz, _AthenAtmosphereTime);\n    '+marker,1)
motion=motion.replace('float4(input.positionOld, 1) : input.position','float4(input.positionOld, 1) : unmodifiedPosition',1)
marker='output.previousPositionCSNoJitter = mul('
motion=motion.replace(marker,'prevPos.xyz = WardTreeWind(prevPos.xyz, _AthenAtmospherePreviousTime);\n    '+marker,1)
(SHADER/'ObjectMotionVectors.hlsl').write_text(motion)
shader=shader.replace('"Packages/com.unity.render-pipelines.universal/ShaderLibrary/ObjectMotionVectors.hlsl"','"ObjectMotionVectors.hlsl"')
(SHADER/'WardTree.shader').write_text('// Derived from URP 17.6.0 Lit; retains all standard rendering passes.\n'+shader)
report={'textures':rows,'shaderBase':'Unity URP17.6.0 installed Lit','sourceSha256':hashlib.sha256((PACKAGE/'Shaders/Lit.shader').read_bytes()).hexdigest(),'wind':'world-space canopy flex, small leaf flutter, matching shadow/depth/motion passes; existing reduced-motion-aware clock','geometry':'full original LOD0 and LOD1; only exact duplicate LOD0 trunk removed'}
(ROOT/'art/quality_20260908/tree/runtime-preparation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
