"""Write a C# body (for unity_exec.py) that renders named scene cameras, or name:x,y,z:tx,ty,tz:fov specs,
through a temporary camera cloned from MainCamera (post-processing on) to 1920x1080 PNGs in an output folder.
Usage: python3 unity/tools/editor_capture.py OUTDIR cam_a "view:-60,1.7,2:-66,0,1:60" > body.cs"""
import sys
out = sys.argv[1]; names = sys.argv[2:]
L = ['var main = GameObject.Find("MainCamera").GetComponent<Camera>();',
 'var go = new GameObject("__cap"); go.hideFlags = HideFlags.DontSave; var cam = go.AddComponent<Camera>(); cam.CopyFrom(main);',
 'var src = main.GetComponent<UnityEngine.Rendering.Universal.UniversalAdditionalCameraData>(); var dst = go.AddComponent<UnityEngine.Rendering.Universal.UniversalAdditionalCameraData>();',
 'if (src) { dst.renderPostProcessing = src.renderPostProcessing; dst.antialiasing = src.antialiasing; dst.antialiasingQuality = src.antialiasingQuality; dst.renderShadows = true; dst.requiresDepthTexture = src.requiresDepthTexture; }',
 'cam.enabled = false; cam.nearClipPlane = 0.05f; cam.farClipPlane = 650;',
 'var rt = new RenderTexture(1920, 1080, 24, RenderTextureFormat.ARGB32); rt.antiAliasing = 4; var tex = new Texture2D(1920, 1080, TextureFormat.RGB24, false);',
 'var log = new System.Text.StringBuilder(); GameObject c;',
 'System.IO.Directory.CreateDirectory("%s");' % out]
for n in names:
    if ':' in n:
        nm, p, t, f = n.split(':')
        L.append(f'go.transform.position = new Vector3({p.replace(",", "f,")}f); go.transform.LookAt(new Vector3({t.replace(",", "f,")}f)); cam.fieldOfView = {f}f;')
    else:
        nm = n
        L.append(f'c = GameObject.Find("{n}"); if (!c) {{ log.AppendLine("missing {n}"); }} else {{ go.transform.SetPositionAndRotation(c.transform.position, c.transform.rotation); cam.fieldOfView = c.GetComponent<Camera>().fieldOfView; }}')
    L.append(f'cam.targetTexture = rt; cam.Render(); RenderTexture.active = rt; tex.ReadPixels(new Rect(0,0,1920,1080),0,0); tex.Apply(); System.IO.File.WriteAllBytes("{out}/{nm}.png", tex.EncodeToPNG()); log.AppendLine("{nm}");')
L.append('RenderTexture.active = null; cam.targetTexture = null; UnityEngine.Object.DestroyImmediate(go); rt.Release(); return log.ToString();')
print('\n'.join(L))
