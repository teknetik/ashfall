using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    // 27 Sep 2026 pm, request #6: first-person two-hand cup grip. The player skeleton has no finger bones, so the old
    // view-model arms (cut from the colonist) cannot close a grip. PlayerFPHands_v2.glb is a dedicated static hands and
    // forearms mesh authored in Blender around the view-model pistol, in the pistol's own frame (metres, unit scale); it is
    // parented to the view-model pistol, so FirstPersonViewModel's placement, sway, bob, recoil and draw move it unchanged.
    // The old arms stay in the rig with their renderers off, for rollback (UseOldArms).
    public static class FPGripPass
    {
        const string Scene="Assets/AthenHill/Scenes/AthenHill.unity";
        const string Art="Assets/AthenHill/Art/CharacterMotion/FirstPerson/";
        public const string HandsName="FP hands v2";
        /// "-fpEvidence <dir>" overrides the evidence root (v5 review round writes to 20260927-eve without touching pm evidence)
        static string Evidence{get{var a=Environment.GetCommandLineArgs();int i=Array.IndexOf(a,"-fpEvidence");
            return Path.GetFullPath(i>=0&&i+1<a.Length?a[i+1]:"../../unity/evidence/character-feel/20260927-pm/");}}
        static string Scratch=>Path.GetFullPath("../../art/character_feel_20260927/fp_arms/");

        static FirstPersonViewModel OpenVm()
        {
            if(SceneManager()!=Scene)EditorSceneManager.OpenScene(Scene);
            // 3 Oct 2026: two view models in the scene (pistol, field rifle): the pistol's is the one PlayerCombat drives
            var combat=Object.FindAnyObjectByType<PlayerCombat>(FindObjectsInactive.Include);
            var vm=combat&&combat.viewModel?combat.viewModel:Object.FindObjectsByType<FirstPersonViewModel>(FindObjectsInactive.Include,FindObjectsSortMode.None).FirstOrDefault(v=>!v.rifle);
            if(!vm)throw new InvalidOperationException("No FirstPersonViewModel in scene");
            return vm;
        }
        static string SceneManager()=>EditorSceneManager.GetActiveScene().path;

        static Matrix4x4 PistolFrame(Transform p)=>Matrix4x4.TRS(p.position,p.rotation,Vector3.one);

        static void PoseRig(FirstPersonViewModel vm)
        {
            vm.visuals.SetActive(true);
            if(vm.holdClip)vm.holdClip.SampleAnimation(vm.animationSource.gameObject,vm.holdClip.length*.3f);
        }

        static void WriteObj(StringBuilder sb,string name,Mesh m,Matrix4x4 toFrame,ref int vbase)
        {
            sb.AppendLine("o "+name);
            foreach(var v in m.vertices){var w=toFrame.MultiplyPoint3x4(v);sb.AppendLine(string.Format(CultureInfo.InvariantCulture,"v {0:F5} {1:F5} {2:F5}",w.x,w.y,w.z));}
            var t=m.triangles;
            for(int i=0;i<t.Length;i+=3)sb.AppendLine("f "+(t[i]+vbase)+" "+(t[i+1]+vbase)+" "+(t[i+2]+vbase));
            vbase+=m.vertexCount;
        }

        // Writes fp_arms/pistol_frame.obj (view-model pistol and old arms, in the pistol frame, Unity axes) and
        // pistol_frame.json (camera poses at hip/ADS in the same frame, FOV, scales, material info).
        public static void Dump()
        {
            var vm=OpenVm();PoseRig(vm);
            var frame=PistolFrame(vm.pistol).inverse;
            var sb=new StringBuilder();int vbase=1;
            foreach(var mf in vm.pistol.GetComponentsInChildren<MeshFilter>(true))
                if(mf.sharedMesh&&!mf.GetComponentInParent<MuzzleFlash>(true))WriteObj(sb,"pistol_"+mf.name,mf.sharedMesh,frame*mf.transform.localToWorldMatrix,ref vbase);
            var armInfo=new List<object>();
            foreach(var s in vm.rig.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if(s.transform.IsChildOf(vm.pistol))continue;
                var baked=new Mesh();s.BakeMesh(baked,true);
                WriteObj(sb,"oldarms_"+s.name,baked,frame*s.transform.localToWorldMatrix,ref vbase);
                armInfo.Add(new{s.name,mats=s.sharedMaterials.Select(m=>m?m.name+" / "+m.shader.name+" / "+(m.HasProperty("_BaseMap")&&m.GetTexture("_BaseMap")?AssetDatabase.GetAssetPath(m.GetTexture("_BaseMap")):"")+" / "+(m.HasProperty("_BaseColor")?m.GetColor("_BaseColor").ToString():"")+" / "+string.Join(",",m.shaderKeywords):"null").ToArray()});
            }
            File.WriteAllText(Scratch+"pistol_frame.obj",sb.ToString());
            object Cam(Vector3 off,Vector3 eul){var t=Matrix4x4.TRS(off,Quaternion.Euler(eul),Vector3.one).inverse;return new{pos=V(t.GetColumn(3)),rot=Q(t.rotation)};}
            var muzzle=vm.muzzle?frame.MultiplyPoint3x4(vm.muzzle.position):Vector3.zero;
            var info=new{
                pistolLossy=V(vm.pistol.lossyScale),pistolLocalScale=V(vm.pistol.localScale),pistolParent=vm.pistol.parent.name,
                hip=Cam(vm.hipOffset,vm.hipEuler),ads=Cam(vm.aimOffset,vm.aimEuler),hipOffset=V(vm.hipOffset),hipEuler=V(vm.hipEuler),aimOffset=V(vm.aimOffset),
                fov=vm.viewCamera.fieldOfView,near=vm.overlayCamera?vm.overlayCamera.nearClipPlane:0,muzzle=V(muzzle),arms=armInfo,
                pistolChildren=vm.pistol.GetComponentsInChildren<Transform>(true).Select(t=>t.name+" lp="+V(t.localPosition)+" ls="+V(t.localScale)).ToArray()};
            File.WriteAllText(Scratch+"pistol_frame.json",JsonConvert.SerializeObject(info,Formatting.Indented));
            Debug.Log("FPGripPass.Dump ok");
        }

        // ---------------------------------------------------------------- install
        static readonly (string name,Color srgb,float smooth,float metal,Color emit)[] Mats={
            // sRGB albedo sampled from the colonist texture (fingertip skin, glove, bracer, sleeve); no lighting baked in
            ("FPHandsSkin",new Color(.63f,.44f,.37f),.46f,0,Color.black),
            ("FPHandsGlove",new Color(.40f,.33f,.25f),.38f,0,Color.black),   // v3: worn tan leather (v2 .26/.255/.235 read as a black blob at dusk)
            ("FPHandsBracer",new Color(.27f,.27f,.19f),.5f,.15f,Color.black),
            ("FPHandsSleeve",new Color(.14f,.145f,.14f),.15f,0,Color.black),
            ("FPHandsNail",new Color(.70f,.55f,.50f),.6f,0,Color.black),
            ("FPHandsGlow",new Color(.05f,.25f,.30f),.6f,0,new Color(.25f,.85f,1f)*.8f)};

        static Material HandMaterial((string name,Color srgb,float smooth,float metal,Color emit) m)
        {
            string path=Art+"FPHands/"+m.name+".mat";
            Directory.CreateDirectory(Art+"FPHands");
            var mat=AssetDatabase.LoadAssetAtPath<Material>(path);
            var shader=Shader.Find("Universal Render Pipeline/Lit");
            if(!mat){mat=new Material(shader){name=m.name};AssetDatabase.CreateAsset(mat,path);}
            mat.shader=shader;mat.SetColor("_BaseColor",m.srgb);mat.SetFloat("_Smoothness",m.smooth);mat.SetFloat("_Metallic",m.metal);
            if(m.emit.maxColorComponent>0){mat.EnableKeyword("_EMISSION");mat.SetColor("_EmissionColor",m.emit);mat.globalIlluminationFlags=MaterialGlobalIlluminationFlags.None;}
            else{mat.DisableKeyword("_EMISSION");mat.SetColor("_EmissionColor",Color.black);}
            V5Maps(mat);
            EditorUtility.SetDirty(mat);return mat;
        }

        /// v3 (thumbs-forward rework, tan glove) when present, else v2. Both glbs stay in the project for rollback.
        /// v5 (CC0 MakeHuman hand, collision-fitted cup grip, baked normal/AO) supersedes v3; v2/v3 stay for rollback.
        static string HandsAsset=>File.Exists(Art+"PlayerFPHands_v5.glb")?Art+"PlayerFPHands_v5.glb":File.Exists(Art+"PlayerFPHands_v3.glb")?Art+"PlayerFPHands_v3.glb":Art+"PlayerFPHands_v2.glb";
        static bool IsV5=>HandsAsset.EndsWith("_v5.glb");

        /// v5 baked maps (Blender, 2048, UV0): tangent-space normal (OpenGL +Y, as Unity expects) and AO, linear.
        static void V5Maps(Material mat)
        {
            string n=Art+"FPHands/FPHands_v5_normal.png",ao=Art+"FPHands/FPHands_v5_ao.png";
            bool use=IsV5&&(mat.name=="FPHandsGlove"||mat.name=="FPHandsSkin"||mat.name=="FPHandsNail");
            if(!use){mat.SetTexture("_BumpMap",null);mat.DisableKeyword("_NORMALMAP");mat.SetTexture("_OcclusionMap",null);mat.DisableKeyword("_OCCLUSIONMAP");return;}
            foreach(var (path,normal) in new[]{(n,true),(ao,false)})
            {
                var ti=(TextureImporter)AssetImporter.GetAtPath(path);if(!ti)continue;
                bool dirty=false;
                if(normal&&ti.textureType!=TextureImporterType.NormalMap){ti.textureType=TextureImporterType.NormalMap;dirty=true;}
                if(!normal&&ti.sRGBTexture){ti.sRGBTexture=false;dirty=true;}
                if(ti.anisoLevel<4){ti.anisoLevel=4;dirty=true;}
                if(dirty)ti.SaveAndReimport();
            }
            mat.SetTexture("_BumpMap",AssetDatabase.LoadAssetAtPath<Texture2D>(n));mat.SetFloat("_BumpScale",1);mat.EnableKeyword("_NORMALMAP");
            mat.SetTexture("_OcclusionMap",AssetDatabase.LoadAssetAtPath<Texture2D>(ao));mat.SetFloat("_OcclusionStrength",1);mat.EnableKeyword("_OCCLUSIONMAP");
        }

        /// Attaches the FP hands mesh under the view-model pistol and hides the old cut-out arms (kept for rollback).
        /// Called by WeaponFeelPass.Install() after it rebuilds the view model, and by Install() below.
        public static string Attach(FirstPersonViewModel vm)
        {
            var asset=AssetDatabase.LoadAssetAtPath<GameObject>(HandsAsset);
            if(!asset)return "FP hands v2 not imported; old arms kept";
            var old=vm.pistol.Find(HandsName);if(old)Object.DestroyImmediate(old.gameObject);
            var go=(GameObject)PrefabUtility.InstantiatePrefab(asset);go.name=HandsName;
            go.transform.SetParent(vm.pistol,false);
            // authored in the pistol frame in metres: identity pose, unit world scale
            go.transform.localPosition=Vector3.zero;go.transform.localRotation=Quaternion.identity;
            var ls=vm.pistol.lossyScale;go.transform.localScale=new Vector3(1/ls.x,1/ls.y,1/ls.z);
            var byName=Mats.ToDictionary(m=>m.name,HandMaterial);
            int tris=0;
            foreach(var r in go.GetComponentsInChildren<Renderer>(true))
            {
                r.sharedMaterials=r.sharedMaterials.Select(m=>m&&byName.TryGetValue(m.name.Replace(" (Instance)",""),out var x)?x:m).ToArray();
                r.shadowCastingMode=ShadowCastingMode.Off;r.receiveShadows=true;
                var mf=r.GetComponent<MeshFilter>();if(mf&&mf.sharedMesh)tris+=mf.sharedMesh.triangles.Length/3;
            }
            foreach(var t in go.GetComponentsInChildren<Transform>(true))t.gameObject.layer=vm.pistol.gameObject.layer;
            UseOldArms(vm,false);
            return "FP hands v2: "+tris+" tris, materials "+string.Join(",",go.GetComponentsInChildren<Renderer>(true).SelectMany(r=>r.sharedMaterials).Select(m=>m?m.name:"null").Distinct());
        }

        /// Rollback switch: true shows the old colonist-cut arms and hides v2, false the reverse.
        public static void UseOldArms(FirstPersonViewModel vm,bool old)
        {
            foreach(var s in vm.rig.GetComponentsInChildren<SkinnedMeshRenderer>(true))if(!s.transform.IsChildOf(vm.pistol))s.enabled=old;
            var v2=vm.pistol.Find(HandsName);if(v2)v2.gameObject.SetActive(!old);
        }

        [MenuItem("Athen Hill/Combat/Install first-person hands v2")]
        public static void Install()
        {
            var vm=OpenVm();
            AssetDatabase.ImportAsset(HandsAsset,ImportAssetOptions.ForceUpdate);
            var log=Attach(vm);
            EditorUtility.SetDirty(vm);EditorSceneManager.MarkSceneDirty(vm.gameObject.scene);EditorSceneManager.SaveScene(vm.gameObject.scene);AssetDatabase.SaveAssets();
            Debug.Log("FPGripPass.Install "+log);
        }

        // ---------------------------------------------------------------- Editor renders
        struct Pose{public string name;public float aim,draw,recoil;public Vector2 sway;public float fov;}
        static void PlaceRig(FirstPersonViewModel vm,Vector3 camPos,Quaternion camRot,Pose p)
        {
            float r=p.recoil*p.recoil*(3-2*p.recoil);
            var offset=Vector3.Lerp(vm.hipOffset,vm.aimOffset,p.aim)+new Vector3(p.sway.x*vm.swayAmount,p.sway.y*vm.swayAmount,0)+Vector3.back*vm.recoilBack*r;
            var euler=Vector3.Lerp(vm.hipEuler,vm.aimEuler,p.aim)+new Vector3(-vm.recoilPitch*r+p.sway.y*vm.swayRotation,p.sway.x*vm.swayRotation,p.sway.x*vm.swayRotation*.5f);
            float d=p.draw*p.draw*(3-2*p.draw);
            offset=Vector3.Lerp(vm.holsterOffset,offset,d);euler=Vector3.Lerp(vm.holsterEuler,euler,d);
            var target=Matrix4x4.TRS(camPos+camRot*offset,camRot*Quaternion.Euler(euler),Vector3.one);
            var rel=vm.rig.worldToLocalMatrix*vm.pistol.localToWorldMatrix;
            var place=target*rel.inverse;
            vm.rig.SetPositionAndRotation(place.GetColumn(3),place.rotation);
        }

        /// Off-screen renders of the view model at the Berms range under the 17:00 dusk frame (DuskStartPass.Preview
        /// lighting), for hip, ADS and motion extremes. Pass "old" to render the previous arms for comparison.
        public static void Render()=>Render(Environment.GetCommandLineArgs().Contains("-fpOld"));
        public static void RenderBoth(){Render(true);Render(false);}
        /// Batch entry: re-import and attach v2, render before/after, verify requests #1-5.
        public static void Pass2(){Install();Render(true);Render(false);PmRequestsVerify.Run();}
        /// Batch entry for the final pass: attach, final renders, verify #1-5, then development and release builds.
        public static void FinalAndBuild()
        {
            Install();Render(false);PmRequestsVerify.Run();
            var cap=Path.GetFullPath("../../unity/evidence/character-feel/20260927-pm/");
            LinuxBuild.Development();File.Copy("Captures/linux-build.json",cap+"linux-build-dev.json",true);
            LinuxBuild.Release();File.Copy("Captures/linux-build.json",cap+"linux-build-release.json",true);
            Debug.Log("FPGripPass.FinalAndBuild done");
        }
        /// v5 review round: attach v5, before (old arms)/after renders, #1-5 re-read, then dev and release builds.
        /// Run with -fpEvidence <dir> -pmVerifyOut <file> so the pm evidence stays untouched.
        public static void V5AndBuild()
        {
            Install();Render(true);Render(false);PmRequestsVerify.Run();
            LinuxBuild.Development();File.Copy("Captures/linux-build.json",Evidence+"linux-build-dev.json",true);
            LinuxBuild.Release();File.Copy("Captures/linux-build.json",Evidence+"linux-build-release.json",true);
            Debug.Log("FPGripPass.V5AndBuild done");
        }
        /// Review round 2: hip view hid the cup grip below the frame edge. Renders hip candidates (not saved) to
        /// <evidence>/fp-grip/hip-tune so a pose that shows both hands can be chosen; ADS is untouched.
        public static void HipTune()
        {
            var vm=OpenVm();Attach(vm);PoseRig(vm);
            foreach(var s in vm.rig.GetComponentsInChildren<SkinnedMeshRenderer>(true))s.forceMatrixRecalculationPerRender=true;
            var main=GameObject.Find("MainCamera").GetComponent<Camera>();main.cullingMask|=1<<vm.pistol.gameObject.layer;
            var rc=GameObject.Find("cam_berms_range").transform;var pos=rc.position;
            if(Physics.Raycast(pos+Vector3.up*50,Vector3.down,out var hit,200,~(1<<vm.pistol.gameObject.layer),QueryTriggerInteraction.Ignore))pos.y=hit.point.y+1.62f;
            var fwd=Vector3.ProjectOnPlane(rc.forward,Vector3.up).normalized;var rot=Quaternion.LookRotation(fwd,Vector3.up)*Quaternion.Euler(3,0,0);
            var cands=new (string n,Vector3 o,Vector3 e)[]{
                ("h0_current",vm.hipOffset,vm.hipEuler),
                ("h1",new Vector3(.13f,-.13f,.44f),new Vector3(3,-5,-8)),
                ("h2",new Vector3(.12f,-.115f,.42f),new Vector3(0,-5,-6)),
                ("h3",new Vector3(.12f,-.12f,.42f),new Vector3(8,-5,-6)),
                ("h4",new Vector3(.10f,-.105f,.40f),new Vector3(6,-4,-4)),
                ("h5",new Vector3(.11f,-.10f,.43f),new Vector3(12,-4,-5))};
            var outDir=Evidence+"fp-grip/hip-tune";var log=new StringBuilder();
            DuskStartPass.Preview(17,Path.GetTempPath()+"fpgrip-warmup",string.Format(CultureInfo.InvariantCulture,"warm:{0},{1},{2}:{3},{4},{5}:50",pos.x,pos.y,pos.z,pos.x+fwd.x,pos.y,pos.z+fwd.z));
            var o0=vm.hipOffset;var e0=vm.hipEuler;
            foreach(var c in cands)
            {
                vm.hipOffset=c.o;vm.hipEuler=c.e;
                PlaceRig(vm,pos,rot,new Pose{name=c.n,aim=0,draw=1});
                var look=pos+rot*Vector3.forward*10;
                log.Append(c.n+" off "+V(c.o)+" eul "+V(c.e)+" ");
                log.Append(DuskStartPass.Preview(17,outDir,string.Format(CultureInfo.InvariantCulture,"{0}:{1},{2},{3}:{4},{5},{6}:{7}",c.n,pos.x,pos.y,pos.z,look.x,look.y,look.z,main.fieldOfView))).Append('\n');
            }
            vm.hipOffset=o0;vm.hipEuler=e0;
            File.WriteAllText(outDir+"/hip-tune.txt",log.ToString());
            Debug.Log("FPGripPass.HipTune -> "+outDir);
        }

        /// Applies "-fpHip ox,oy,oz,ex,ey,ez" to the saved view model (hip pose only), then runs V5AndBuild.
        public static void HipApplyAndBuild()
        {
            var a=Environment.GetCommandLineArgs();int i=Array.IndexOf(a,"-fpHip");
            if(i>=0&&i+1<a.Length)
            {
                var f=a[i+1].Split(',').Select(s=>float.Parse(s,CultureInfo.InvariantCulture)).ToArray();
                var vm=OpenVm();
                Debug.Log("FPGripPass.HipApply "+V(vm.hipOffset)+"/"+V(vm.hipEuler)+" -> "+a[i+1]);
                vm.hipOffset=new Vector3(f[0],f[1],f[2]);vm.hipEuler=new Vector3(f[3],f[4],f[5]);
                EditorUtility.SetDirty(vm);EditorSceneManager.MarkSceneDirty(vm.gameObject.scene);EditorSceneManager.SaveScene(vm.gameObject.scene);
            }
            V5AndBuild();
        }

        static void Render(bool old)
        {
            string tag=old?"before":"after";
            var vm=OpenVm();
            if(!old)Attach(vm);else UseOldArms(vm,true);
            PoseRig(vm);
            foreach(var s in vm.rig.GetComponentsInChildren<SkinnedMeshRenderer>(true))s.forceMatrixRecalculationPerRender=true;
            var main=GameObject.Find("MainCamera").GetComponent<Camera>();int mask=main.cullingMask;main.cullingMask|=1<<vm.pistol.gameObject.layer;
            // eye at the Berms range: cam_berms_range's position and yaw, dropped to 1.62 m above the ground, level
            var rc=GameObject.Find("cam_berms_range").transform;var pos=rc.position;
            if(Physics.Raycast(pos+Vector3.up*50,Vector3.down,out var hit,200,~(1<<vm.pistol.gameObject.layer),QueryTriggerInteraction.Ignore))pos.y=hit.point.y+1.62f;
            var fwd=Vector3.ProjectOnPlane(rc.forward,Vector3.up).normalized;var rot=Quaternion.LookRotation(fwd,Vector3.up)*Quaternion.Euler(3,0,0);
            var poses=new[]{
                new Pose{name="hip",aim=0,draw=1},new Pose{name="ads",aim=1,draw=1},
                new Pose{name="ads_recoil",aim=1,draw=1,recoil=1},new Pose{name="hip_recoil",aim=0,draw=1,recoil=1},
                new Pose{name="hip_sway_ul",aim=0,draw=1,sway=new Vector2(-1,1)},new Pose{name="hip_sway_dr",aim=0,draw=1,sway=new Vector2(1,-1)},
                new Pose{name="draw_half",aim=0,draw=.5f},new Pose{name="ads_sway",aim=1,draw=1,sway=new Vector2(.3f,.3f)}};
            var outDir=Evidence+"fp-grip/editor-"+tag;var log=new StringBuilder();
            try
            {
                // warm-up render: the first off-screen render of a batch session shows unloaded (black) materials
                DuskStartPass.Preview(17,Path.GetTempPath()+"fpgrip-warmup",string.Format(CultureInfo.InvariantCulture,"warm:{0},{1},{2}:{3},{4},{5}:50",pos.x,pos.y,pos.z,pos.x+fwd.x,pos.y,pos.z+fwd.z));
                foreach(var p in poses)
                {
                    PlaceRig(vm,pos,rot,p);
                    var look=pos+rot*Vector3.forward*10;
                    string spec=string.Format(CultureInfo.InvariantCulture,"{0}:{1},{2},{3}:{4},{5},{6}:{7}",p.name,pos.x,pos.y,pos.z,look.x,look.y,look.z,main.fieldOfView);
                    // LookAt(look) reproduces rot (no roll) so the rig placement matches the render camera
                    log.Append(DuskStartPass.Preview(17,outDir,spec));
                }
                // the same ADS and hip with the low sun behind the player (the hands' lit side)
                var back=rot*Quaternion.Euler(0,180,0);
                foreach(var p in new[]{new Pose{name="ads_sunbehind",aim=1,draw=1},new Pose{name="hip_sunbehind",aim=0,draw=1}})
                {
                    PlaceRig(vm,pos,back,p);var look=pos+back*Vector3.forward*10;
                    log.Append(DuskStartPass.Preview(17,outDir,string.Format(CultureInfo.InvariantCulture,"{0}:{1},{2},{3}:{4},{5},{6}:{7}",p.name,pos.x,pos.y,pos.z,look.x,look.y,look.z,main.fieldOfView)));
                }
            }
            finally{main.cullingMask=mask;}
            File.WriteAllText(outDir+"/renders.txt","eye "+pos+" fov "+main.fieldOfView+" near 0.05 (Preview camera)\n"+log);
            Debug.Log("FPGripPass.Render "+tag+" -> "+outDir);
        }

        static string V(Vector3 v)=>v.x.ToString("F5",CultureInfo.InvariantCulture)+","+v.y.ToString("F5",CultureInfo.InvariantCulture)+","+v.z.ToString("F5",CultureInfo.InvariantCulture);
        static string Q(Quaternion q)=>q.x.ToString("F6",CultureInfo.InvariantCulture)+","+q.y.ToString("F6",CultureInfo.InvariantCulture)+","+q.z.ToString("F6",CultureInfo.InvariantCulture)+","+q.w.ToString("F6",CultureInfo.InvariantCulture);
    }
}
