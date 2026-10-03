using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    /// <summary>
    /// Player face pass, 3 Oct 2026 (art/player_face_20261003/README.md). The MPFB colonist gets the Meshy retexture of
    /// its own skin mesh (painted face, hair and beard, normal and roughness on the original MPFB UVs) and alpha-clipped
    /// hair/beard shells instead of the MakeHuman cards. The Blender chain (finish_body.py, fp_arms.py) writes the GLBs;
    /// the files are copied over colonist.glb (same GUID) and Art/Armour/TutorialSet/TS_FPArms.glb before Unity starts.
    /// Steps (-executeMethod AthenHill.Editor.PlayerFace20261003.RunBatch --steps a,b,c):
    ///   install  MainCharacterInstall.Install (prefab, clips, grips, weapons, armour, view models) + review cameras
    ///   cameras  cam_player_face_20261003_* at the player's spawn (the native lookbook leaves him at West Gate)
    ///   verify   -nographics: mesh/material/vertex-colour/alpha-clip checks + MainCharacterInstall.Check
    ///   hands    first-person hands only (also run by TutorialSetInstall.Attach inside install): see FirstPersonHands
    ///   capture  graphics: face/body at 13:00 and in shade beside Torr, first-person pistol and rifle (editor renders)
    ///   rollback restores the pre-pass GLBs (art/tutorial_set_20261002/blender/previous_face_20261003/out) and reinstalls with
    ///            the authored FP hands v2 on the pistol and the procedural finger curl (also: --authored-pistol-hands with install)
    /// </summary>
    public static class PlayerFace20261003
    {
        const string Scene="Assets/AthenHill/Scenes/AthenHill.unity";
        const string ModelPath="Assets/AthenHill/Art/Imported/Meshy/colonist.glb";
        const string FPArmsPath="Assets/AthenHill/Art/Armour/TutorialSet/TS_FPArms.glb";
        public const string CamRoot="Player face 20261003 cameras";
        static string ArtDir=>Path.GetFullPath(Path.Combine(Application.dataPath,"../../../art/player_face_20261003"));
        static string Previous=>Path.GetFullPath(Path.Combine(Application.dataPath,"../../../art/tutorial_set_20261002/blender/previous_face_20261003/out"));

        public static void RunBatch()
        {
            var a=Environment.GetCommandLineArgs();int i=Array.IndexOf(a,"--steps");
            var steps=(i>=0&&i+1<a.Length?a[i+1]:"verify").Split(',').Select(s=>s.Trim()).Where(s=>s.Length>0).ToArray();
            if(a.Contains("--authored-pistol-hands")||steps.Contains("rollback"))PistolOnPlayerArms=false;   // the pre-pass first-person hands
            int code=0;var log=new List<string>();
            try
            {
                if(EditorSceneManager.GetActiveScene().path!=Scene)EditorSceneManager.OpenScene(Scene,OpenSceneMode.Single);
                foreach(var s in steps)
                {
                    string r=s switch{"install"=>Install(),"cameras"=>Cameras(),"verify"=>Verify(),"capture"=>Capture(),"rollback"=>Rollback(),"hands"=>HandsStep(),
                        _=>throw new ArgumentException("unknown step "+s)};
                    log.Add("["+s+"] "+r);Debug.Log("PlayerFace20261003 "+s+"\n"+r);
                }
            }
            catch(Exception e){Debug.LogException(e);log.Add("FAILED "+e);code=1;}
            try{Directory.CreateDirectory(Path.Combine(ArtDir,"unity"));File.WriteAllText(Path.Combine(ArtDir,"unity",string.Join("_",steps)+"-result.txt"),string.Join("\n",log)+"\n");}catch(Exception e){Debug.LogException(e);}
            EditorApplication.Exit(code);
        }

        static PlayerMotor Motor(){var m=Object.FindAnyObjectByType<PlayerMotor>(FindObjectsInactive.Include);if(!m)throw new InvalidOperationException("No PlayerMotor");return m;}
        static PlayerCombat Combat(){var c=Object.FindAnyObjectByType<PlayerCombat>(FindObjectsInactive.Include);if(!c)throw new InvalidOperationException("No PlayerCombat");return c;}
        static Transform Bone(Component root,string n){var t=root.GetComponentsInChildren<Transform>(true).FirstOrDefault(x=>x.name==n);if(!t)throw new InvalidOperationException("no bone "+n+" under "+root.name);return t;}
        static void SaveAll(){var s=EditorSceneManager.GetActiveScene();EditorSceneManager.MarkSceneDirty(s);EditorSceneManager.SaveScene(s);AssetDatabase.SaveAssets();}
        static string F(Vector3 v)=>string.Format(CultureInfo.InvariantCulture,"{0:0.###},{1:0.###},{2:0.###}",v.x,v.y,v.z);

        // ------------------------------------------------------------------ install
        static string Install()
        {
            AssetDatabase.ImportAsset(ModelPath,ImportAssetOptions.ForceUpdate);
            AssetDatabase.ImportAsset(FPArmsPath,ImportAssetOptions.ForceUpdate);
            var r=MainCharacterInstall.Install();
            if(EditorSceneManager.GetActiveScene().path!=Scene)EditorSceneManager.OpenScene(Scene,OpenSceneMode.Single);
            var c=Cameras();
            File.WriteAllText(Path.Combine(ArtDir,"unity","main_character_install.json"),r);
            return "MainCharacterInstall.Install ok ("+r.Length+" chars, unity/main_character_install.json); "+c;
        }

        /// Player-height review cameras round the player's spawn (West Gate), where the native lookbook leaves him.
        static string Cameras()
        {
            var scene=EditorSceneManager.GetActiveScene();
            foreach(var old in scene.GetRootGameObjects().Where(g=>g.name==CamRoot).ToArray())Object.DestroyImmediate(old);
            var motor=Motor();var root=new GameObject(CamRoot);
            var feet=motor.transform.position;
            var fwd=Vector3.ProjectOnPlane(motor.visual?motor.visual.forward:motor.transform.forward,Vector3.up).normalized;
            if(fwd.sqrMagnitude<.5f)fwd=Vector3.forward;
            var right=Vector3.Cross(Vector3.up,fwd);
            var template=Object.FindObjectsByType<Camera>(FindObjectsInactive.Include,FindObjectsSortMode.None).FirstOrDefault(c=>c.name=="cam_character_face");
            var made=new List<string>();
            void Cam(string name,Vector3 pos,Vector3 look,float fov)
            {
                var go=new GameObject("cam_player_face_20261003_"+name);go.transform.SetParent(root.transform,false);
                var cam=go.AddComponent<Camera>();if(template)cam.CopyFrom(template);cam.enabled=false;cam.fieldOfView=fov;cam.nearClipPlane=.05f;
                go.transform.position=pos;go.transform.LookAt(look);made.Add(go.name+" @ "+F(pos));
            }
            float eye=1.66f;var head=feet+Vector3.up*eye;
            Cam("face_front",head+fwd*.85f+Vector3.up*.02f,head-Vector3.up*.03f,28);                                 // conversation distance, front
            Cam("face_quarter",head+(fwd*.62f+right*.55f)+Vector3.up*.03f,head-Vector3.up*.03f,28);                 // three-quarter
            Cam("face_side",head+(-fwd*.1f-right*.85f)+Vector3.up*.02f,head-Vector3.up*.03f,28);                     // profile (beard/hair silhouette)
            Cam("body_front",feet+fwd*2.7f+right*.9f+Vector3.up*1.25f,feet+Vector3.up*.95f,36);                       // full body three-quarter
            Cam("follow_back",feet-fwd*2.6f+right*.7f+Vector3.up*1.75f,feet+Vector3.up*1.45f,50);                     // the follow camera's view of the head
            SaveAll();
            return "cameras: "+string.Join("; ",made);
        }

        // ------------------------------------------------------------------ verify (-nographics)
        static string Verify()
        {
            var fails=new List<string>();var info=new Dictionary<string,object>();
            void Must(bool ok,string what){if(!ok)fails.Add(what);}
            var motor=Motor();var combat=Combat();
            var skin=motor.visual.GetComponentsInChildren<SkinnedMeshRenderer>(true).OrderByDescending(x=>x.sharedMesh?x.sharedMesh.vertexCount:0).FirstOrDefault();
            Must(skin&&skin.sharedMesh,"player skinned mesh");
            if(skin&&skin.sharedMesh)
            {
                var mesh=skin.sharedMesh;var mats=skin.sharedMaterials;
                info["triangles"]=mesh.triangles.Length/3;info["vertices"]=mesh.vertexCount;info["bones"]=skin.bones.Length;
                info["materials"]=mats.Select(m=>m?m.name+" ("+m.shader.name+")":"null").ToArray();
                Must(AssetDatabase.GetAssetPath(mesh)==ModelPath,"mesh from colonist.glb");
                Must(skin.bones.Length==54,"54 bones (got "+skin.bones.Length+")");
                Must(mats.Length==5,"five materials (got "+mats.Length+")");
                Must(mats.All(m=>m&&!m.shader.name.Contains("Error")),"no error shaders");
                Must(mesh.colors32!=null&&mesh.colors32.Length==mesh.vertexCount,"vertex colours imported");
                Must(mesh.tangents!=null&&mesh.tangents.Length==mesh.vertexCount,"tangents imported");
                int Sub(string n){for(int i=0;i<mats.Length;i++)if(mats[i]&&mats[i].name.StartsWith(n))return i;return -1;}
                int si=Sub("PlayerSkin"),hi=Sub("PlayerHairShell"),li=Sub("PlayerEyelashes");
                Must(si>=0&&hi>=0&&li>=0,"PlayerSkin, PlayerHairShell and PlayerEyelashes materials");
                if(si>=0){var m=mats[si];info["skin"]=m.GetTexturePropertyNames().Where(n=>m.GetTexture(n)).ToDictionary(n=>n,n=>m.GetTexture(n).name+" "+m.GetTexture(n).width);
                    Must(m.HasProperty("normalTexture")&&m.GetTexture("normalTexture"),"skin normal map");
                    Must(m.HasProperty("metallicRoughnessTexture")&&m.GetTexture("metallicRoughnessTexture"),"skin roughness map");}
                foreach(var k in new[]{hi,li}.Where(k=>k>=0))
                {
                    var m=mats[k];bool clip=m.IsKeywordEnabled("_ALPHATEST_ON")||(m.HasProperty("alphaCutoff")&&m.GetFloat("alphaCutoff")>0&&m.renderQueue<3000);
                    info[m.name+"_alpha"]=new{queue=m.renderQueue,cutoff=m.HasProperty("alphaCutoff")?m.GetFloat("alphaCutoff"):-1,keywords=m.shaderKeywords};
                    Must(clip&&m.renderQueue<3000,m.name+" alpha-clipped, not blended");
                }
                if(hi>=0)
                {   // the shell layers' vertex alpha (1, .85, .7, .55) survives the import
                    var cols=mesh.colors32;var tri=mesh.GetTriangles(hi);var alphas=new SortedSet<byte>(tri.Select(t=>cols[t].a));
                    info["shellAlpha"]=alphas.ToArray();info["shellTriangles"]=tri.Length/3;
                    Must(alphas.Count>=4&&alphas.Min<150,"shell vertex alpha layers");
                    var skinTri=mesh.GetTriangles(si);Must(skinTri.All(t=>cols[t].a==255&&cols[t].r==255),"skin vertex colour white");
                }
            }
            // view models: the rifle arms use the player's own skin material
            var rvm=combat.rifleViewModel;
            if(rvm&&rvm.rig){var r=rvm.GetComponentsInChildren<SkinnedMeshRenderer>(true).SelectMany(x=>x.sharedMaterials).Where(m=>m).Select(m=>m.name).Distinct().ToArray();info["rifleViewModelMaterials"]=r;Must(r.Contains("PlayerSkin"),"rifle view model on PlayerSkin");}
            else fails.Add("rifle view model");
            var pvm=combat.viewModel;
            if(pvm&&pvm.rig){var r=pvm.GetComponentsInChildren<Renderer>(true).Where(x=>x.enabled&&x.gameObject.activeInHierarchy||x.transform.IsChildOf(pvm.pistol)).SelectMany(x=>x.sharedMaterials).Where(m=>m).Select(m=>m.name).Distinct().ToArray();info["pistolViewModelMaterials"]=r;}
            // cameras
            var cams=Object.FindObjectsByType<Camera>(FindObjectsInactive.Include,FindObjectsSortMode.None).Where(c=>c.name.StartsWith("cam_player_face_20261003_")).Select(c=>c.name).OrderBy(n=>n).ToArray();
            info["cameras"]=cams;Must(cams.Length>=5,"review cameras");
            // the main character chain's own check (bones, clips, pistol/rifle mounts, armour bind poses, footsteps ...)
            string chk;try{chk="pass";MainCharacterInstall.Check();}catch(Exception e){chk="FAILED "+e.Message;fails.Add("MainCharacterInstall.Check failed");}
            info["mainCharacterCheck"]=chk.Length>3000?chk.Substring(0,3000):chk;
            var text=JsonConvert.SerializeObject(new{utc=DateTime.UtcNow.ToString("O"),pass=fails.Count==0,fails,info},Formatting.Indented);
            File.WriteAllText(Path.Combine(ArtDir,"unity","verify.json"),text);
            if(fails.Count>0)throw new InvalidOperationException("verify failed: "+string.Join("; ",fails)+"\n"+text);
            return text;
        }

        // ------------------------------------------------------------------ capture (graphics)
        /// Editor renders through DuskStartPass.Preview (13:00 profile). "--shots face|fp|tp" picks one set of about six
        /// cameras per Unity run (AGENTS.md machine limits); without it all sets render.
        static string Capture()
        {
            var a=Environment.GetCommandLineArgs();int ai=Array.IndexOf(a,"--shots");
            var sets=new HashSet<string>((ai>=0&&ai+1<a.Length?a[ai+1]:"face,fp,tp").Split(','));
            var outDir=Path.Combine(ArtDir,"unity","captures");Directory.CreateDirectory(outDir);
            var motor=Motor();var combat=Combat();var actor=motor.actor;var body=motor.visual;
            var log=new List<string>();
            if(combat.muzzleLight)combat.muzzleLight.enabled=false;
            if(combat.heldPistol)combat.heldPistol.SetActive(false);if(combat.heldRifle)combat.heldRifle.SetActive(false);
            foreach(var r in body.GetComponentsInChildren<SkinnedMeshRenderer>(true))r.forceMatrixRecalculationPerRender=true;
            var clock=Object.FindFirstObjectByType<CityTimeOfDay>(FindObjectsInactive.Include);
            var sun=clock.profile.Evaluate(13f).keyEuler;var sunFwd=Quaternion.Euler(sun)*Vector3.forward;   // light travel direction
            var toSun=-Vector3.ProjectOnPlane(sunFwd,Vector3.up).normalized;
            // stand: the rifle review stand, open ground
            var feet=RifleArmourInstall.Stand;
            if(Physics.Raycast(feet+Vector3.up*6,Vector3.down,out var hit,30,~(1<<8),QueryTriggerInteraction.Ignore))feet.y=hit.point.y;
            motor.transform.position=feet+Vector3.up*.015f;
            void Face(Vector3 dir){body.rotation=Quaternion.LookRotation(dir,Vector3.up);if(actor.idle)actor.idle.SampleAnimation(actor.animationSource.gameObject,.4f);}
            string Spec(string name,Vector3 pos,Vector3 look,float fov)=>string.Format(CultureInfo.InvariantCulture,"{0}:{1},{2},{3}:{4},{5},{6}:{7}",name,pos.x,pos.y,pos.z,look.x,look.y,look.z,fov);
            var head=Bone(actor,"Head");
            // warm-up (first render compiles shaders)
            Face(toSun);DuskStartPass.Preview(13,Path.Combine(outDir,"warmup"),Spec("warm",feet+toSun*3+Vector3.up*1.6f,feet+Vector3.up*1.5f,30));
            if(sets.Contains("face"))
            {
                // sunlit: he faces three-quarter toward the sun
                var lit=Quaternion.AngleAxis(35,Vector3.up)*toSun;Face(lit);
                Vector3 h=head.position+Vector3.up*.07f;var rgt=Vector3.Cross(Vector3.up,lit);
                log.Add(DuskStartPass.Preview(13,outDir,
                    Spec("player_face_sun",h+lit*.8f,h-Vector3.up*.02f,26),
                    Spec("player_face_sun_quarter",h+(lit*.6f+rgt*.55f),h-Vector3.up*.02f,26),
                    Spec("player_face_sun_side",h-rgt*.82f+lit*.08f,h-Vector3.up*.02f,26),
                    Spec("player_body_sun",feet+lit*2.7f+rgt*.9f+Vector3.up*1.25f,feet+Vector3.up*.95f,36)));
                // shade: back to the sun, the face lit by sky and bounce only
                var shade=-toSun;Face(shade);h=head.position+Vector3.up*.07f;
                log.Add(DuskStartPass.Preview(13,outDir,Spec("player_face_shade",h+shade*.8f,h-Vector3.up*.02f,26)));
                // Torr at the same distance and light, wherever he stands
                var torr=Object.FindObjectsByType<NpcAgent>(FindObjectsInactive.Include,FindObjectsSortMode.None).FirstOrDefault(n=>n.name.ToLowerInvariant().Contains("torr")||(n.definition&&n.definition.name.ToLowerInvariant().Contains("torr")));
                if(torr&&torr.actor)
                {
                    foreach(var r in torr.GetComponentsInChildren<SkinnedMeshRenderer>(true))r.forceMatrixRecalculationPerRender=true;
                    if(torr.actor.idle&&torr.actor.animationSource)torr.actor.idle.SampleAnimation(torr.actor.animationSource.gameObject,.4f);
                    var th=torr.actor.GetComponentsInChildren<Transform>(true).FirstOrDefault(t=>t.name=="Head");
                    if(th)
                    {
                        var tf=Vector3.ProjectOnPlane(torr.actor.transform.forward,Vector3.up).normalized;var tp=th.position+Vector3.up*.07f;
                        log.Add(DuskStartPass.Preview(13,outDir,Spec("torr_face",tp+tf*.8f,tp-Vector3.up*.02f,26)));
                    }
                }
                else log.Add("Torr not found");
            }
            if(sets.Contains("fp"))
            {
                // first person: both view models at the stand, looking down range (-X), hip and aim, one close orbit each
                Face(Vector3.left);
                var main=GameObject.Find("MainCamera").GetComponent<Camera>();int mask=main.cullingMask;
                try
                {
                    foreach(var vm in new[]{combat.viewModel,combat.rifleViewModel}.Where(v=>v))
                    {
                        main.cullingMask=(mask|(1<<vm.gameObject.layer))&~(1<<8);   // the body is not drawn in first person
                        var other=vm==combat.viewModel?combat.rifleViewModel:combat.viewModel;if(other&&other.visuals)other.visuals.SetActive(false);
                        if(vm.visuals)vm.visuals.SetActive(true);
                        foreach(var s in vm.GetComponentsInChildren<SkinnedMeshRenderer>(true))s.forceMatrixRecalculationPerRender=true;
                        var eye=feet+Vector3.up*1.62f;var rot=Quaternion.LookRotation(Vector3.left,Vector3.up)*Quaternion.Euler(3,0,0);
                        string tag=vm.rifle?"rifle":"pistol";
                        foreach(var (pname,aim) in new[]{("hip",0f),("aim",1f)})
                        {
                            PoseViewModel(vm,eye,rot,aim);
                            log.Add(DuskStartPass.Preview(13,outDir,Spec("fp_"+tag+"_"+pname,eye,eye+rot*Vector3.forward*10,main.fieldOfView)));
                        }
                        PoseViewModel(vm,eye,rot,0);
                        var hc=(Bone(vm,"RightHand").position+Bone(vm,"LeftHand").position)/2;
                        var cr=rot*Vector3.right;var cf=rot*Vector3.forward;var cu=rot*Vector3.up;
                        log.Add(DuskStartPass.Preview(13,outDir,vm.rifle?Spec("fp_rifle_orbit_right",hc+cr*.42f+cu*.05f-cf*.05f,hc,40):Spec("fp_pistol_orbit_left",hc-cr*.42f+cu*.05f-cf*.05f,hc,40)));
                        if(vm.visuals)vm.visuals.SetActive(false);
                    }
                }
                finally{main.cullingMask=mask;}
            }
            if(sets.Contains("tp"))
            {
                // third person: the body's holds with the solved shooting-hand grips (and the rifle support IK)
                var grip=combat.GetComponent<PlayerHandGrip>();var ik=combat.GetComponent<SupportHandIK>();
                AnimationClip Clip(string n)=>AssetDatabase.LoadAssetAtPath<AnimationClip>("Assets/AthenHill/Art/CharacterMotion/Player/"+n+".anim");
                var side=Vector3.Cross(Vector3.up,Vector3.left);
                foreach(var (held,clip,rifle) in new[]{(combat.heldPistol,"pistol_hold",false),(combat.heldRifle,"rifle_hold",true)})
                {
                    if(!held)continue;
                    Face(Vector3.left);var c=Clip(clip);if(c)c.SampleAnimation(actor.animationSource.gameObject,c.length*.3f);
                    held.SetActive(true);if(grip)grip.PreviewGrip(1,rifle?1:0,rifle);
                    if(rifle&&ik&&ik.rifleGrip)ik.Solve(ik.rifleGrip,1);
                    var rh=Bone(actor,"RightHand").position;var tag=rifle?"rifle":"pistol";
                    log.Add(DuskStartPass.Preview(13,outDir,
                        Spec("tp_"+tag+"_hands",rh+side*.55f+Vector3.up*.08f+Vector3.left*.15f,rh+Vector3.left*.12f,34),
                        Spec("tp_"+tag+"_body",feet+side*2.4f+Vector3.left*.9f+Vector3.up*1.35f,feet+Vector3.up*1.2f+Vector3.left*.3f,36)));
                    held.SetActive(false);
                }
            }
            // nothing is saved: poses and positions are capture-only state
            return string.Join("",log);
        }

        /// The view model's per-frame work in edit mode: hold clip, placement (FirstPersonViewModel.LateUpdate), finger grip, support-hand IK.
        public static void PoseViewModel(FirstPersonViewModel vm,Vector3 camPos,Quaternion camRot,float aim)
        {
            if(vm.holdClip&&vm.animationSource)vm.holdClip.SampleAnimation(vm.animationSource.gameObject,vm.holdClip.length*.3f);
            var offset=Vector3.Lerp(vm.hipOffset,vm.aimOffset,aim);var euler=Vector3.Lerp(vm.hipEuler,vm.aimEuler,aim);
            var target=Matrix4x4.TRS(camPos+camRot*offset,camRot*Quaternion.Euler(euler),Vector3.one);
            var rel=vm.rig.worldToLocalMatrix*vm.pistol.localToWorldMatrix;var place=target*rel.inverse;
            vm.rig.SetPositionAndRotation(place.GetColumn(3),place.rotation);
            var ar=vm.GetComponent<ViewModelArmsRig>();if(ar&&ar.arms&&ar.arms!=vm.rig)ar.Place(camPos,camRot);   // weapon-driven: arms at their camera anchor
            var grip=vm.GetComponentInChildren<PlayerHandGrip>(true);if(grip)grip.PreviewGrip(1,1,vm.rifle);
            foreach(var ik in vm.GetComponentsInChildren<SupportHandIK>(true)){var t=vm.rifle?ik.rifleGrip:ik.pistolGrip;if(t)ik.Solve(t,1);}
        }


        // ------------------------------------------------------------------ first-person hands
        /// The pistol view model shows the player's own MPFB arms (same skin, sleeves, gloves) instead of the authored
        /// "FP hands v2" grip mesh (kept inactive for rollback: set this false and reinstall).
        public static bool PistolOnPlayerArms=true;
        /// Camera-space point midway between the shoulders for the weapon-driven pistol arms (metres: x right, y up, z forward).
        public static Vector3 ShoulderAnchor=new Vector3(.03f,-.26f,.02f);
        /// The rifle stays clip-driven (weapon under the hand): the weapon-driven trial put the hand on the receiver, see PROGRESS.md.
        public static bool WeaponDrivenRifle=false;
        public static Vector3 RifleShoulderAnchor=new Vector3(.06f,-.25f,0f);
        /// Aim-down-sights distance of the pistol (camera space z of the pistol root): at arm's length, so the wrists stay
        /// below the line of sight (WeaponFeelPass had 0.30 m for the old clip-driven arms).
        public static float PistolAimDistance=.46f;
        const int TempLayer=31;
        static readonly string[] Digits={"index","middle","ring","pinky","thumb"};

        static string HandsStep()
        {
            var combat=Combat();var motor=Motor();var vis=combat.GetComponent<PlayerArmourVisuals>();
            var r=FirstPersonHands(combat,motor,vis);SaveAll();return r;
        }

        /// Called by TutorialSetInstall.Attach after the view models and armour pieces are rebuilt. For both view models:
        /// support-hand grip point, fingers solved against the weapon (and, for the pistol's support hand, the shooting
        /// hand), worn gloves/arm guards mirrored onto the arms; the solved right/rifle-left grips are copied to the body.
        public static string FirstPersonHands(PlayerCombat combat,PlayerMotor motor,PlayerArmourVisuals vis)
        {
            var log=new List<string>();
            var pvm=combat.viewModel;var rvm=combat.rifleViewModel;
            if(!pvm||!pvm.rig)return "first-person hands: no pistol view model";
            var pArmsRig=ArmsRigOf(pvm);if(!pArmsRig)return "first-person hands: no 'Player arms rig' under the pistol view model";
            Unmount(pvm,pArmsRig);
            if(rvm&&ArmsRigOf(rvm))Unmount(rvm,ArmsRigOf(rvm));
            var v2=pvm.pistol.Find(FPGripPass.HandsName);
            var pArms=pArmsRig.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(x=>!x.transform.IsChildOf(pvm.pistol)&&!x.name.StartsWith("FP armour")).ToArray();
            if(!PistolOnPlayerArms)
            {
                if(v2)v2.gameObject.SetActive(true);foreach(var s in pArms)s.enabled=false;
                var old=pvm.GetComponent<ViewModelArmsRig>();if(old)Object.DestroyImmediate(old);
                var bg=combat.GetComponent<PlayerHandGrip>();
                if(bg){bg.pistolRight=new Quaternion[0];bg.pistolLeft=new Quaternion[0];bg.rifleRight=new Quaternion[0];bg.rifleLeft=new Quaternion[0];EditorUtility.SetDirty(bg);}
                return "first-person hands: pistol keeps FP hands v2, procedural finger curl (PistolOnPlayerArms=false)";
            }
            if(v2)v2.gameObject.SetActive(false);
            foreach(var s in pArms)s.enabled=true;
            var bodyGrip=combat.GetComponent<PlayerHandGrip>();
            foreach(var vm in new[]{pvm,rvm}.Where(v=>v&&v.rig))
            {
                bool rifle=vm.rifle;var arms=ArmsRigOf(vm);if(!arms){log.Add((rifle?"rifle":"pistol")+": no arms rig");continue;}
                var grip=arms.GetComponent<PlayerHandGrip>();
                if(!grip)
                {   // TutorialSetInstall.ViewModels strips the pistol rig's grip while the authored hands are used
                    grip=arms.gameObject.AddComponent<PlayerHandGrip>();grip.combat=combat;
                    Transform[] Fingers(string side)=>Digits.SelectMany(d=>new[]{"01","02","03"}.Select(j=>arms.GetComponentsInChildren<Transform>(true).FirstOrDefault(x=>x.name==$"{d}_{j}_{side}"))).Where(x=>x).ToArray();
                    grip.rightFingers=Fingers("r");grip.leftFingers=Fingers("l");
                }
                var restR=grip.rightFingers.Select(t=>t.localRotation).ToArray();var restL=grip.leftFingers.Select(t=>t.localRotation).ToArray();
                void Relax(){for(int i=0;i<restR.Length;i++)grip.rightFingers[i].localRotation=restR[i];for(int i=0;i<restL.Length;i++)grip.leftFingers[i].localRotation=restL[i];}
                var temp=new GameObject("__grip colliders");
                try
                {
                    var weapon=vm.pistol;var wroot=rifle?weapon.parent:weapon;   // the rifle's vm.pistol is a pivot under the weapon
                    var hand=Bone(arms,"RightHand");var lhand=Bone(arms,"LeftHand");
                    var ik=arms.GetComponent<SupportHandIK>();if(!ik)ik=arms.gameObject.AddComponent<SupportHandIK>();
                    ik.combat=combat;ik.upper=Bone(arms,"LeftArm");ik.lower=Bone(arms,"LeftForeArm");ik.hand=lhand;
                    if(!rifle||WeaponDrivenRifle)
                    {
                        // weapon-driven: the weapon on its own mount (FirstPersonViewModel places it), the arms anchored to the
                        // camera with the shoulders under the eye, both hands IK'd onto grip points on the weapon
                        ResetMount(wroot,hand,rifle?combat.heldRifle:combat.heldPistol);
                        if(!rifle)vm.aimOffset=new Vector3(vm.aimOffset.x,vm.aimOffset.y,PistolAimDistance);
                        ik.pistolGrip=null;ik.rifleGrip=null;
                        PoseViewModel(vm,Vector3.zero,Quaternion.identity,0);Relax();
                        var anchorPos=arms.position;var anchorRot=arms.rotation;   // camera at the origin: world = camera space
                        // the hold clips put the shoulders well right of and ahead of the eye; centre them under and just behind it
                        var shoulders=(Bone(arms,"LeftArm").position+Bone(arms,"RightArm").position)/2;
                        anchorPos+=(rifle?RifleShoulderAnchor:ShoulderAnchor)-shoulders;
                        var shoot=ShootingGrip(vm,wroot,hand,grip.rightFingers,rifle,log);
                        var mount=new GameObject("Weapon mount"){layer=vm.gameObject.layer}.transform;
                        mount.SetParent(vm.visuals?vm.visuals.transform:vm.transform,false);mount.SetPositionAndRotation(wroot.position,wroot.rotation);
                        wroot.SetParent(mount,true);vm.rig=mount;
                        var ar=vm.GetComponent<ViewModelArmsRig>();if(!ar)ar=vm.gameObject.AddComponent<ViewModelArmsRig>();
                        ar.viewModel=vm;ar.arms=arms;ar.anchorPosition=anchorPos;ar.anchorRotation=anchorRot;EditorUtility.SetDirty(ar);
                        var rikGo=new GameObject("Right arm IK"){layer=vm.gameObject.layer};rikGo.transform.SetParent(arms,false);
                        var rik=rikGo.AddComponent<SupportHandIK>();rik.combat=combat;rik.upper=Bone(arms,"RightArm");rik.lower=Bone(arms,"RightForeArm");rik.hand=hand;
                        if(rifle){rik.rifleGrip=shoot;rik.rifleWeight=1;rik.pistolGrip=null;rik.pistolWeight=0;}
                        else{rik.pistolGrip=shoot;rik.pistolWeight=1;rik.rifleGrip=null;rik.rifleWeight=0;}
                        PoseViewModel(vm,Vector3.zero,Quaternion.identity,0);Relax();
                        // elbows down and out in camera space (camera at the origin, arms at their anchor), kept by the IK poles
                        rik.poleHint=rik.upper.parent.InverseTransformDirection(new Vector3(.55f,-.83f,-.05f).normalized);
                        ik.poleHint=ik.upper.parent.InverseTransformDirection(new Vector3(-.55f,-.83f,-.05f).normalized);
                        rik.Solve(shoot,1);
                        log.Add($"{(rifle?"rifle":"pistol")} weapon-driven: arms anchored at {F(anchorPos)}, shooting hand IK error {(hand.position-shoot.position).magnitude*100:0.0} cm");
                    }
                    else
                    {   // clip-driven rifle (the weapon under the hand, as TutorialSetInstall.Rig built it)
                        ResetMount(wroot,hand,combat.heldRifle);
                        var oldAr=vm.GetComponent<ViewModelArmsRig>();if(oldAr)Object.DestroyImmediate(oldAr);
                        ik.poleHint=Vector3.zero;
                        if(vm.holdClip&&vm.animationSource)vm.holdClip.SampleAnimation(vm.animationSource.gameObject,vm.holdClip.length*.3f);
                    }
                    foreach(var mf in WeaponMeshes(wroot))
                    {
                        var g=new GameObject("c "+mf.name){layer=TempLayer};g.transform.SetParent(temp.transform,false);
                        g.transform.SetPositionAndRotation(mf.transform.position,mf.transform.rotation);g.transform.localScale=mf.transform.lossyScale;
                        g.AddComponent<MeshCollider>().sharedMesh=mf.sharedMesh;
                    }
                    Physics.SyncTransforms();
                    var solvedR=SolveFingers(grip.rightFingers,restR,1<<TempLayer);
                    Transform support;
                    if(!rifle)
                    {
                        AddHandCapsules(temp.transform,hand,grip.rightFingers);Physics.SyncTransforms();   // the support hand closes round the shooting hand
                        support=PistolSupport(vm,weapon,hand,lhand,ik,grip.leftFingers,log);
                        ik.pistolGrip=support;ik.pistolWeight=1;ik.rifleGrip=null;ik.rifleWeight=0;
                    }
                    else
                    {
                        support=weapon.parent.GetComponentsInChildren<Transform>(true).FirstOrDefault(t=>t.name=="Support grip");
                        if(support)RifleSupport(vm,support,ik,hand,lhand,grip.leftFingers,combat,log);
                        ik.rifleGrip=support;ik.rifleWeight=1;ik.pistolGrip=null;ik.pistolWeight=0;
                    }
                    if(support)ik.Solve(support,1);
                    var solvedL=SolveFingers(grip.leftFingers,restL,1<<TempLayer);
                    if(rifle){grip.rifleRight=solvedR;grip.rifleLeft=solvedL;grip.pistolRight=new Quaternion[0];grip.pistolLeft=new Quaternion[0];}
                    else{grip.pistolRight=solvedR;grip.pistolLeft=solvedL;grip.rifleRight=new Quaternion[0];grip.rifleLeft=new Quaternion[0];}
                    log.Add((rifle?"rifle":"pistol")+" grip solved: right "+Curl(solvedR,restR)+" | left "+Curl(solvedL,restL));
                    {   // camera-space diagnostics (hip, camera at the origin looking +Z; x right, y up)
                        PoseViewModel(vm,Vector3.zero,Quaternion.identity,0);
                        string P(string n)=>n+" "+F(Bone(arms,n).position);
                        log.Add("cam-space hip: "+string.Join(" | ",new[]{"RightArm","RightForeArm","RightHand","LeftArm","LeftForeArm","LeftHand"}.Select(P))+" | muzzle "+(vm.muzzle?F(vm.muzzle.position):"-"));
                    }
                    // the body's rifle sits in the same hand frame as the view model's: share the support hand (the shooting
                    // hand is solved on the body itself, SolveBody)
                    if(rifle&&bodyGrip&&bodyGrip.leftFingers.Length==solvedL.Length)bodyGrip.rifleLeft=solvedL;
                    EditorUtility.SetDirty(ik);
                }
                finally{Object.DestroyImmediate(temp);Relax();}   // the saved rig keeps the relaxed rest
                PrefabUtility.RecordPrefabInstancePropertyModifications(grip);EditorUtility.SetDirty(grip);EditorUtility.SetDirty(vm);
                log.Add(ArmourMirror(vm,vis));
            }
            if(bodyGrip)
            {
                log.Add(SolveBody(combat,motor,bodyGrip));
                bodyGrip.pistolLeft=new Quaternion[0];PrefabUtility.RecordPrefabInstancePropertyModifications(bodyGrip);EditorUtility.SetDirty(bodyGrip);
            }
            return "first-person hands: "+string.Join("; ",log);
        }

        static Transform ArmsRigOf(FirstPersonViewModel vm)
        {
            var parent=vm.visuals?vm.visuals.transform:vm.transform;
            return parent.Cast<Transform>().FirstOrDefault(t=>t.name=="Player arms rig");
        }

        /// Undoes a previous run's weapon-driven setup: the pistol back under the right hand, the mount, right-arm IK and
        /// grip points removed (they are rebuilt from the third-person mount every run).
        static void Unmount(FirstPersonViewModel vm,Transform arms)
        {
            var hand=Bone(arms,"RightHand");
            var wroot=vm.rifle?vm.pistol.parent:vm.pistol;   // the rifle's vm.pistol is a pivot under the weapon
            if(vm.rig&&vm.rig!=arms&&vm.rig.name=="Weapon mount")
            {
                var mount=vm.rig;wroot.SetParent(hand,true);vm.rig=arms;Object.DestroyImmediate(mount.gameObject);
            }
            vm.rig=arms;
            foreach(var x in arms.GetComponentsInChildren<Transform>(true).Where(y=>y.name=="Right arm IK").ToArray())Object.DestroyImmediate(x.gameObject);
            // the pistol's grip points are rebuilt every run; the rifle's support grip is a copy of the held rifle's and is kept
            foreach(var x in wroot.GetComponentsInChildren<Transform>(true).Where(y=>y.name=="Shooting grip"||(!vm.rifle&&y.name=="Support grip")).ToArray())Object.DestroyImmediate(x.gameObject);
        }

        /// The view-model weapon under the hand exactly as the third-person weapon sits in the body's hand (TutorialSetInstall.Rig).
        static void ResetMount(Transform weapon,Transform rHand,GameObject held)
        {
            if(!held||!held.transform.parent)return;
            var pHand=held.transform.parent;
            var relRot=Quaternion.Inverse(pHand.rotation)*held.transform.rotation;var relPos=Quaternion.Inverse(pHand.rotation)*(held.transform.position-pHand.position);
            weapon.SetPositionAndRotation(rHand.position+rHand.rotation*relPos,rHand.rotation*relRot);
        }

        /// Weapon meshes that are really shown with the weapon: active below the weapon root (the view-model visuals may be
        /// switched off while solving), not the retired grip-hands mesh, not the muzzle flash card.
        static IEnumerable<MeshFilter> WeaponMeshes(Transform root)
        {
            bool Shown(Transform t){for(var x=t;x&&x!=root;x=x.parent)if(!x.gameObject.activeSelf||x.name==FPGripPass.HandsName)return false;return true;}
            return root.GetComponentsInChildren<MeshFilter>(true).Where(m=>m.sharedMesh&&m.GetComponent<Renderer>()&&!m.GetComponentInParent<MuzzleFlash>(true)&&Shown(m.transform));
        }

        static string Curl(Quaternion[] s,Quaternion[] rest)
        {
            var parts=new List<string>();
            for(int d=0;d<5;d++){float sum=0;for(int j=0;j<3;j++){int i=d*3+j;if(i<s.Length)sum+=Quaternion.Angle(rest[i],s[i]);}parts.Add(Digits[d].Substring(0,2)+" "+sum.ToString("0"));}
            return string.Join(",",parts);
        }


        /// Hand frame from the bones: finger direction (wrist to middle knuckle), palm normal (the side the fingers curl
        /// to), palm centre; all in the hand bone's local rotation frame (world-scaled offsets).
        static (Vector3 d,Vector3 n,Vector3 palm,Vector3 knuckle) HandFrame(Transform hand,Transform[] fingers,string side)
        {
            var mid=fingers.First(t=>t.name=="middle_01_"+side);var mid3=fingers.First(t=>t.name=="middle_03_"+side);
            var dW=(mid.position-hand.position).normalized;
            var q0=mid.localRotation;var t0=mid3.position;mid.localRotation=q0*Quaternion.Euler(30,0,0);var t1=mid3.position;mid.localRotation=q0;
            var nW=Vector3.ProjectOnPlane(t1-t0,dW).normalized;var inv=Quaternion.Inverse(hand.rotation);
            return (inv*dW,inv*nW,inv*(Vector3.Lerp(hand.position,mid.position,.55f)-hand.position),inv*(mid.position-hand.position));
        }

        /// The pistol's shooting-hand grip point: the palm on the grip's right panel, knuckles up and forward along the
        /// raked grip axis, moved in until the palm touches. (The hold clip had the palm behind the grip with the fingers
        /// over the slide: fine at third-person distance, wrong at 40 cm.) Returns the wrist target under the pistol.
        static Transform ShootingGrip(FirstPersonViewModel vm,Transform weapon,Transform rHand,Transform[] rightFingers,bool rifle,List<string> log)
        {
            var meshes=WeaponMeshes(weapon).ToArray();
            var mf=meshes.Where(m=>!m.transform.GetComponentsInParent<Transform>(true).Any(p=>p.name=="Pistol mods")).OrderByDescending(m=>m.sharedMesh.vertexCount).First();
            var c=mf.transform.TransformPoint(mf.sharedMesh.bounds.center);var sz=mf.sharedMesh.bounds.size;
            var lat=(sz.x<=sz.y&&sz.x<=sz.z?mf.transform.right:sz.y<=sz.z?mf.transform.up:mf.transform.forward).normalized;
            // barrel = the mesh's long axis towards the muzzle; down = away from the muzzle's offset above the bounds centre
            // (the grip hangs below the bore, so the centre sits below it)
            var longAx=(sz.x>=sz.y&&sz.x>=sz.z?mf.transform.right:sz.y>=sz.z?mf.transform.up:mf.transform.forward).normalized;
            var mz=vm.muzzle?vm.muzzle.position:c+weapon.forward;
            var barrel=Vector3.Dot(longAx,mz-c)>=0?longAx:-longAx;
            // the rifle's pistol grip is where the third-person hand mount is (the weapon root); the bore is above it
            var down=-Vector3.ProjectOnPlane(Vector3.ProjectOnPlane(mz-(rifle?weapon.position:c),barrel),lat).normalized;
            var gm=meshes.FirstOrDefault(m=>m.name.StartsWith("grip_"));
            // grip centre: the pistol's grip mod, else its rear lower bounds; the rifle's from the hold clip's own palm, which
            // the third-person mount (MainCharacterInstall.MeasurePalm) puts on the pistol grip
            var clipMid=rightFingers.FirstOrDefault(t=>t.name=="middle_01_r");
            var G=gm?gm.transform.TransformPoint(gm.sharedMesh.bounds.center):rifle&&clipMid?Vector3.Lerp(rHand.position,clipMid.position,.55f):c+down*.045f-barrel*.065f;
            var right=Vector3.Dot(lat,rHand.position-c)>=0?lat:-lat;
            float tilt=(rifle?22:15)*Mathf.Deg2Rad;var g=(down*Mathf.Cos(tilt)-barrel*Mathf.Sin(tilt)).normalized;   // grip axis, raked back
            var (dL,nL,palmL,midL)=HandFrame(rHand,rightFingers,"r");
            var nT=-right;var dT=Vector3.ProjectOnPlane(-g*.8f+barrel*.6f,nT).normalized;
            var Rh=Quaternion.LookRotation(dT,nT)*Quaternion.Inverse(Quaternion.LookRotation(dL,nL));
            var temp=new GameObject("__shooting grip colliders");
            try
            {
                foreach(var m in meshes)
                {
                    var go=new GameObject("c"){layer=TempLayer};go.transform.SetParent(temp.transform,false);
                    go.transform.SetPositionAndRotation(m.transform.position,m.transform.rotation);go.transform.localScale=m.transform.lossyScale;
                    go.AddComponent<MeshCollider>().sharedMesh=m.sharedMesh;
                }
                Physics.SyncTransforms();
                float found=-1;
                for(float o=.10f;o>=-.01f;o-=.002f)
                {
                    var wrist=G+right*o-g*.012f-Rh*palmL;
                    if(Physics.CheckCapsule(wrist+Rh*(midL*.3f),wrist+Rh*midL,.017f,1<<TempLayer,QueryTriggerInteraction.Collide)){found=o+.002f;break;}
                }
                if(found<0)found=.03f;
                var t=new GameObject("Shooting grip").transform;t.SetParent(weapon,true);
                t.SetPositionAndRotation(G+right*found-g*.012f-Rh*palmL,Rh);
                log.Add($"{(rifle?"rifle":"pistol")} shooting grip: palm on the grip panel {found*100:0.0} cm from the grip centre, hand turned {Quaternion.Angle(Rh,rHand.rotation):0} deg from the hold clip");
                log.Add($"shooting grip frame: c {F(c)} G {F(G)} down {F(down)} g {F(g)} right {F(right)} dT {F(dT)} nT {F(nT)} palmL {palmL.magnitude:0.000} wrist {F(t.position)} handNow {F(rHand.position)} gripMesh {(gm?gm.name:"-")}");
                return t;
            }
            finally{Object.DestroyImmediate(temp);}
        }

        /// The third-person body: shooting-hand fingers solved on the held pistol and rifle in their hold clips.
        static string SolveBody(PlayerCombat combat,PlayerMotor motor,PlayerHandGrip grip)
        {
            var actor=motor.actor;if(!actor||!actor.animationSource)return "body grip: no actor";
            var root=actor.animationSource.gameObject;var log=new List<string>();
            var rest=grip.rightFingers.Select(t=>t.localRotation).ToArray();
            foreach(var (held,clipName,rifle) in new[]{(combat.heldPistol,"pistol_hold",false),(combat.heldRifle,"rifle_hold",true)})
            {
                if(!held)continue;
                var clip=AssetDatabase.LoadAssetAtPath<AnimationClip>("Assets/AthenHill/Art/CharacterMotion/Player/"+clipName+".anim");
                if(actor.idle)actor.idle.SampleAnimation(root,0);if(clip)clip.SampleAnimation(root,clip.length*.3f);
                var temp=new GameObject("__body grip colliders");
                try
                {
                    foreach(var m in WeaponMeshes(held.transform))
                    {
                        var go=new GameObject("c"){layer=TempLayer};go.transform.SetParent(temp.transform,false);
                        go.transform.SetPositionAndRotation(m.transform.position,m.transform.rotation);go.transform.localScale=m.transform.lossyScale;
                        go.AddComponent<MeshCollider>().sharedMesh=m.sharedMesh;
                    }
                    Physics.SyncTransforms();
                    var solved=SolveFingers(grip.rightFingers,rest,1<<TempLayer);
                    if(rifle)grip.rifleRight=solved;else grip.pistolRight=solved;
                    log.Add((rifle?"rifle":"pistol")+" "+Curl(solved,rest));
                }
                finally{Object.DestroyImmediate(temp);for(int i=0;i<rest.Length;i++)grip.rightFingers[i].localRotation=rest[i];}
            }
            if(actor.idle)actor.idle.SampleAnimation(root,0);
            return "body shooting-hand grip: "+string.Join(" | ",log);
        }


        /// Pistol support hand: the shooting hand mirrored through the pistol's centre plane (palm to the left grip panel,
        /// thumb forward), lowered a little and moved out until the palm clears the grip and the shooting hand's fingers.
        static Transform PistolSupport(FirstPersonViewModel vm,Transform weapon,Transform rHand,Transform lHand,SupportHandIK ik,Transform[] leftFingers,List<string> log)
        {
            foreach(var old in weapon.GetComponentsInChildren<Transform>(true).Where(t=>t.name=="Support grip").ToArray())Object.DestroyImmediate(old.gameObject);
            var mf=WeaponMeshes(weapon).Where(m=>!m.transform.GetComponentsInParent<Transform>(true).Any(p=>p.name=="Pistol mods")).OrderByDescending(m=>m.sharedMesh.vertexCount).First();
            var c=mf.transform.TransformPoint(mf.sharedMesh.bounds.center);
            // pistol frame from the model: lateral = its thinnest bounds axis, barrel = centre to muzzle, down = towards the
            // shooting hand's wrist (the hand bone runs up the grip, wrist below the knuckles)
            var sz=mf.sharedMesh.bounds.size;
            var thin=sz.x<=sz.y&&sz.x<=sz.z?mf.transform.right:sz.y<=sz.z?mf.transform.up:mf.transform.forward;
            var lat=thin.normalized;
            var longAx=(sz.x>=sz.y&&sz.x>=sz.z?mf.transform.right:sz.y>=sz.z?mf.transform.up:mf.transform.forward).normalized;
            var mz=vm.muzzle?vm.muzzle.position:c+weapon.forward;
            var barrel=Vector3.Dot(longAx,mz-c)>=0?longAx:-longAx;
            var down=-Vector3.ProjectOnPlane(Vector3.ProjectOnPlane(mz-c,barrel),lat).normalized;   // the bore sits above the bounds centre
            // cup grip: the support palm faces up under the shooting hand, fingers pointing forward and across towards the
            // shooting-hand side, then rises until it touches the grip butt or the shooting hand's fingers
            var mid=leftFingers.FirstOrDefault(t=>t.name=="middle_01_l");var idx=leftFingers.FirstOrDefault(t=>t.name=="index_01_l");var pky=leftFingers.FirstOrDefault(t=>t.name=="pinky_01_l");
            var mid3=leftFingers.FirstOrDefault(t=>t.name=="middle_03_l");
            if(!mid||!mid3){log.Add("pistol support: no left finger bones");return null;}
            // hand frame from the bones: finger direction and palm normal (the side the fingers curl towards)
            var dW=(mid.position-lHand.position).normalized;
            var q0=mid.localRotation;var t0=mid3.position;mid.localRotation=q0*Quaternion.Euler(30,0,0);var t1=mid3.position;mid.localRotation=q0;
            var nW=Vector3.ProjectOnPlane(t1-t0,dW).normalized;
            var dL=Quaternion.Inverse(lHand.rotation)*dW;var nL=Quaternion.Inverse(lHand.rotation)*nW;
            var palmL=Quaternion.Inverse(lHand.rotation)*(Vector3.Lerp(lHand.position,mid.position,.55f)-lHand.position);
            var leftSide=Vector3.Dot(ik.upper.position-c,lat)>=0?lat:-lat;   // ik.upper = LeftArm
            var dT=(barrel*.55f-leftSide*.8f).normalized;var nT=-down;nT=Vector3.ProjectOnPlane(nT,dT).normalized;
            var rot=Quaternion.LookRotation(dT,nT)*Quaternion.Inverse(Quaternion.LookRotation(dL,nL));
            var g=new GameObject("Support grip").transform;g.SetParent(weapon,true);g.rotation=rot;
            var rMid=rHand.GetComponentsInChildren<Transform>(true).FirstOrDefault(t=>t.name=="middle_01_r");
            var rPalm=Vector3.Lerp(rHand.position,rMid?rMid.position:rHand.position,.5f);
            float found=-1,err=0;
            for(float h=.12f;h>=-.02f;h-=.002f)
            {
                var palm=rPalm+down*h+barrel*.005f;g.position=palm-rot*palmL;
                ik.Solve(g,1);ik.Solve(g,1);err=(lHand.position-g.position).magnitude;
                if(err>.01f)continue;
                if(Physics.CheckCapsule(lHand.position+(mid.position-lHand.position)*.3f,mid.position,.017f,1<<TempLayer,QueryTriggerInteraction.Collide)){found=h+.003f;break;}
            }
            if(found<0)found=.05f;
            g.position=rPalm+down*found+barrel*.005f-rot*palmL;ik.Solve(g,1);ik.Solve(g,1);
            log.Add($"pistol support grip: cup under the shooting hand, palm {found*100:0.0} cm below its palm, lateral {F(lat)}, wrist error {(lHand.position-g.position).magnitude*100:0.0} cm");
            return g;
        }

        /// Rifle support hand: the palm (not the wrist) moves up under the handguard, at the support station, until it
        /// touches; the hand keeps the hold clip's orientation.
        static void RifleSupport(FirstPersonViewModel vm,Transform support,SupportHandIK ik,Transform rHand,Transform lHand,Transform[] leftFingers,PlayerCombat combat,List<string> log)
        {
            var muzzle=vm.muzzle;if(!muzzle){log.Add("rifle support: no muzzle");return;}
            // bore direction: the rifle mesh's long axis, pointing at the muzzle
            var mfR=WeaponMeshes(support.parent).OrderByDescending(m=>m.sharedMesh.vertexCount).First();
            var bs=mfR.sharedMesh.bounds.size;var la=bs.x>=bs.y&&bs.x>=bs.z?Vector3.right:bs.y>=bs.z?Vector3.up:Vector3.forward;
            var barrel=mfR.transform.TransformDirection(la).normalized;if(Vector3.Dot(barrel,muzzle.position-mfR.transform.TransformPoint(mfR.sharedMesh.bounds.center))<0)barrel=-barrel;
            // bore line through the muzzle; down = from the bore towards the shooting hand on the pistol grip
            var station=muzzle.position+barrel*Vector3.Dot(barrel,support.position-muzzle.position);
            var down=Vector3.ProjectOnPlane(rHand.position-muzzle.position,barrel).normalized;
            var mid=leftFingers.FirstOrDefault(t=>t.name=="middle_01_l");
            if(!mid){log.Add("rifle support: no middle_01_l");return;}
            ik.Solve(support,1);ik.Solve(support,1);
            var palmLocal=Quaternion.Inverse(lHand.rotation)*(Vector3.Lerp(lHand.position,mid.position,.55f)-lHand.position);
            var rot=support.rotation;
            var gripPoint=support.parent.position;   // the rifle's mount point: the shooting hand on the pistol grip
            float found=-1,along=-1,err=0;
            for(float al=.30f;al>=.12f&&found<0;al-=.02f)
            {
                var st=muzzle.position+barrel*Vector3.Dot(barrel,gripPoint+barrel*al-muzzle.position);
                for(float below=.14f;below>=0;below-=.002f)
                {
                    var palm=st+down*below;support.position=palm-rot*palmLocal;
                    ik.Solve(support,1);ik.Solve(support,1);
                    err=(lHand.position-support.position).magnitude;
                    if(err>.01f)continue;   // out of reach at this station
                    if(Physics.CheckCapsule(lHand.position+(mid.position-lHand.position)*.3f,mid.position,.017f,1<<TempLayer,QueryTriggerInteraction.Collide)){found=below+.004f;along=al;station=st;break;}
                }
            }
            if(found<0){found=.05f;along=TutorialSetInstall.SupportAlong;}
            support.position=station+down*found-rot*palmLocal;ik.Solve(support,1);ik.Solve(support,1);
            log.Add($"rifle support station {along*100:0} cm ahead of the grip");
            // the held (third-person) rifle carries the same grip point: same model, same local frame
            var held=combat.heldRifle?combat.heldRifle.GetComponentsInChildren<Transform>(true).FirstOrDefault(t=>t.name=="Support grip"):null;
            if(held){held.localPosition=support.localPosition;EditorUtility.SetDirty(held);}
            log.Add($"rifle support grip: palm {found*100:0.0} cm below the bore at the handguard station (contact {(found!=.05f?"yes":"no")}), wrist error {(lHand.position-support.position).magnitude*100:0.0} cm, held rifle updated: {(held?"yes":"no")}");
        }

        /// Capsules on the shooting hand's palm and finger segments (the support hand closes round them, not through them).
        static void AddHandCapsules(Transform parent,Transform hand,Transform[] fingers)
        {
            void Cap(Vector3 p0,Vector3 p1,float radius)
            {
                var g=new GameObject("hand capsule"){layer=TempLayer};g.transform.SetParent(parent,false);
                var dir=p1-p0;g.transform.SetPositionAndRotation((p0+p1)/2,Quaternion.FromToRotation(Vector3.up,dir.sqrMagnitude>1e-8f?dir:Vector3.up));
                var col=g.AddComponent<CapsuleCollider>();col.direction=1;col.radius=radius;col.height=dir.magnitude+2*radius;
            }
            var mid=fingers.FirstOrDefault(t=>t.name.StartsWith("middle_01"));if(mid)Cap(hand.position,mid.position,.02f);
            for(int digit=0;digit<5;digit++)
            {
                if(digit*3+2>=fingers.Length)break;
                var f0=fingers[digit*3];var f1=fingers[digit*3+1];var f2=fingers[digit*3+2];var tip=f2.position+(f2.position-f1.position)*.85f;
                Cap(f0.position,f1.position,.009f);Cap(f1.position,f2.position,.008f);Cap(f2.position,tip,.0075f);
            }
        }

        /// Each digit (01, 02, 03 joints) curls about its local X, joint by joint from the knuckle, until the rest of the
        /// finger would touch the obstacles (2 degree steps); a finger that starts inside opens until it is free.
        static Quaternion[] SolveFingers(Transform[] f,Quaternion[] rest,int mask)
        {
            for(int i=0;i<f.Length;i++)f[i].localRotation=rest[i];
            for(int d=0;d<5;d++)
            {
                if(d*3+2>=f.Length)break;
                bool thumb=f[d*3].name.StartsWith("thumb");
                float r=thumb?.0095f:.0082f;
                float[] max=thumb?new[]{40f,60f,60f}:new[]{90f,100f,80f};
                var ch=new[]{f[d*3],f[d*3+1],f[d*3+2]};var rs=new[]{rest[d*3],rest[d*3+1],rest[d*3+2]};
                bool Hit(int k)
                {
                    var tip=ch[2].position+(ch[2].position-ch[1].position)*.85f;
                    var p=new[]{ch[0].position,ch[1].position,ch[2].position,tip};
                    for(int s=k;s<3;s++)if(Physics.CheckCapsule(p[s],p[s+1],r,mask,QueryTriggerInteraction.Collide))return true;
                    return false;
                }
                for(int k=0;k<3;k++)
                {
                    float a=0;
                    if(Hit(k)){while(a>-24&&Hit(k)){a-=2;ch[k].localRotation=rs[k]*Quaternion.Euler(a,0,0);}}
                    else
                    {
                        while(a<max[k])
                        {
                            a+=2;ch[k].localRotation=rs[k]*Quaternion.Euler(a,0,0);
                            if(Hit(k)){a-=2;ch[k].localRotation=rs[k]*Quaternion.Euler(a,0,0);break;}
                        }
                    }
                }
            }
            return f.Select(t=>t.localRotation).ToArray();
        }

        /// Worn hand/forearm armour on the view-model arms: skinned copies on the rig's bones, shown while the body's piece is.
        static string ArmourMirror(FirstPersonViewModel vm,PlayerArmourVisuals vis)
        {
            var rig=vm.rig;
            foreach(var old in rig.GetComponentsInChildren<Transform>(true).Where(t=>t.name.StartsWith("FP armour ")).ToArray())Object.DestroyImmediate(old.gameObject);
            var mirror=rig.GetComponent<ViewModelArmourMirror>();if(!mirror)mirror=rig.gameObject.AddComponent<ViewModelArmourMirror>();
            if(!vis||vis.pieces==null){mirror.sources=new GameObject[0];mirror.mirrors=new GameObject[0];return "armour mirror: no PlayerArmourVisuals";}
            var bones=rig.GetComponentsInChildren<Transform>(true).GroupBy(t=>t.name).ToDictionary(g=>g.Key,g=>g.First());
            var arms=rig.GetComponentsInChildren<SkinnedMeshRenderer>(true).FirstOrDefault(x=>!x.name.StartsWith("FP armour")&&!x.transform.IsChildOf(vm.pistol));
            var src=new List<GameObject>();var dst=new List<GameObject>();var made=new List<string>();
            foreach(var p in vis.pieces.Where(p=>p!=null&&p.model&&(p.itemId=="field_gloves"||p.itemId=="field_armguards")))
            {
                var s=p.model.GetComponent<SkinnedMeshRenderer>();if(!s||!s.sharedMesh)continue;
                var go=new GameObject("FP armour "+p.itemId){layer=vm.gameObject.layer};
                go.transform.SetParent(arms?arms.transform.parent:rig,false);
                if(arms){go.transform.localPosition=arms.transform.localPosition;go.transform.localRotation=arms.transform.localRotation;go.transform.localScale=arms.transform.localScale;}
                var smr=go.AddComponent<SkinnedMeshRenderer>();smr.sharedMesh=s.sharedMesh;smr.sharedMaterials=s.sharedMaterials;
                smr.bones=s.bones.Select(b=>b&&bones.TryGetValue(b.name,out var t)?t:(arms?arms.rootBone:rig)).ToArray();
                smr.rootBone=s.rootBone&&bones.TryGetValue(s.rootBone.name,out var rb)?rb:(arms?arms.rootBone:rig);
                smr.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;smr.receiveShadows=true;smr.updateWhenOffscreen=true;
                if(arms)smr.localBounds=arms.localBounds;
                go.SetActive(p.model.activeSelf);src.Add(p.model);dst.Add(go);made.Add(p.itemId+" "+s.sharedMesh.triangles.Length/3+" tris");
            }
            mirror.sources=src.ToArray();mirror.mirrors=dst.ToArray();EditorUtility.SetDirty(mirror);
            return (vm.rifle?"rifle":"pistol")+" armour mirror: "+(made.Count>0?string.Join(", ",made):"none");
        }

        // ------------------------------------------------------------------ rollback
        static string Rollback()
        {
            var prevModel=Path.Combine(Previous,"colonist_mpfb.glb");var prevArms=Path.Combine(Previous,"TS_FPArms.glb");
            if(!File.Exists(prevModel)||!File.Exists(prevArms))throw new FileNotFoundException("previous GLBs missing in "+Previous);
            File.Copy(prevModel,Path.GetFullPath(ModelPath),true);File.Copy(prevArms,Path.GetFullPath(FPArmsPath),true);
            AssetDatabase.ImportAsset(ModelPath,ImportAssetOptions.ForceUpdate);AssetDatabase.ImportAsset(FPArmsPath,ImportAssetOptions.ForceUpdate);
            var r=MainCharacterInstall.Install();
            if(EditorSceneManager.GetActiveScene().path!=Scene)EditorSceneManager.OpenScene(Scene,OpenSceneMode.Single);
            foreach(var old in EditorSceneManager.GetActiveScene().GetRootGameObjects().Where(g=>g.name==CamRoot).ToArray())Object.DestroyImmediate(old);
            SaveAll();
            return "restored the pre-pass colonist.glb and TS_FPArms.glb and reinstalled; review cameras removed";
        }
    }
}
