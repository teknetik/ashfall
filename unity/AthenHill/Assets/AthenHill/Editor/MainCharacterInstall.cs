using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    /// 2 Oct 2026 "next level" character pass: Carl's main_char_OK as the player colonist. The combined GLB
    /// (meshy/main-char-20261002/prepare_player.py) is written over Art/Imported/Meshy/colonist.glb (same GUID), then
    /// this installer re-runs the existing player path in one batch: ImportMeshyPlayer.Install (prefab + scene visual),
    /// 1.8 m sole normalisation measured from the skinned idle pose, the authored Player motion clips
    /// (CharacterMotionPass: idle/talk/jump family), the retargeted library clips, the Berms pistol, the pistol feel
    /// pass (hold, aim pose, first-person view model), the pistol mod visuals, the rifle and plate carrier, the
    /// breathing idle and the surface footsteps, with the player shadow proxy carried over. Idempotent: every step
    /// replaces its own objects. Batch entries exit with 0/1.
    public static class MainCharacterInstall
    {
        const string Scene="Assets/AthenHill/Scenes/AthenHill.unity";
        const string ModelPath="Assets/AthenHill/Art/Imported/Meshy/colonist.glb";
        const string PrefabPath="Assets/AthenHill/Prefabs/MeshyPlayer.prefab";
        const string PlayerFolder="Assets/AthenHill/Art/CharacterMotion/Player";
        const string ProxyName="Player shadow proxy";
        const string CamerasRoot="Character review cameras";
        const float Height=1.8f;
        static string Evidence=>Path.GetFullPath(Path.Combine(Application.dataPath,"../../evidence/next-level/20261002/character/"));
        static string Report=>Path.GetFullPath(Path.Combine(Application.dataPath,"../../../art/next_level_20261002/character/"));

        public static void InstallBatch(){Batch(Install);}
        public static void CheckBatch(){Batch(Check);}
        public static void CaptureBatch(){RifleOnly=false;Batch(Capture);}
        public static void CaptureRifleBatch(){RifleOnly=true;Batch(Capture);}
        static bool RifleOnly;
        static void Batch(Func<string> step)
        {
            int code=0;string text;
            try{text=step();Debug.Log("MainCharacterInstall OK\n"+text);}
            catch(Exception e){Debug.LogException(e);text="FAILED "+e;code=1;}
            try{Directory.CreateDirectory(Evidence);File.WriteAllText(Path.Combine(Evidence,step.Method.Name.ToLowerInvariant()+"-log.txt"),text+"\n");}catch(Exception e){Debug.LogException(e);}
            EditorApplication.Exit(code);
        }

        static object Call(Type t,string method,params object[] args)
        {
            var m=t.GetMethod(method,BindingFlags.NonPublic|BindingFlags.Public|BindingFlags.Static)??throw new MissingMethodException(t.Name,method);
            try{return m.Invoke(null,args);}catch(TargetInvocationException e){throw e.InnerException??e;}
        }
        static PlayerMotor Motor()=>Object.FindAnyObjectByType<PlayerMotor>(FindObjectsInactive.Include)??throw new InvalidOperationException("No PlayerMotor in the scene.");
        static PlayerCombat Combat()=>Object.FindAnyObjectByType<PlayerCombat>(FindObjectsInactive.Include)??throw new InvalidOperationException("No PlayerCombat in the scene.");
        static Transform Bone(Component root,string name)=>root.GetComponentsInChildren<Transform>(true).FirstOrDefault(t=>t.name==name)??throw new InvalidOperationException("No bone "+name+" under "+root.name);
        static void SaveAll(){var s=EditorSceneManager.GetActiveScene();EditorSceneManager.MarkSceneDirty(s);EditorSceneManager.SaveScene(s);AssetDatabase.SaveAssets();}

        /// Skin the largest mesh on the CPU in the current pose (bind poses x bone matrices; no BakeMesh scale ambiguity
        /// with the 0.01-scaled Meshy armature) and return its sole height and top in the visual root's space.
        static (float soles,float top) Measure(Transform visual)
        {
            var smr=visual.GetComponentsInChildren<SkinnedMeshRenderer>(true).OrderByDescending(s=>s.sharedMesh?s.sharedMesh.vertexCount:0).First();
            var mesh=smr.sharedMesh;var verts=mesh.vertices;var weights=mesh.boneWeights;var bind=mesh.bindposes;
            var toRoot=visual.worldToLocalMatrix;
            var skin=new Matrix4x4[smr.bones.Length];
            for(int i=0;i<skin.Length;i++)skin[i]=toRoot*smr.bones[i].localToWorldMatrix*bind[i];
            float min=float.MaxValue,max=float.MinValue;
            for(int v=0;v<verts.Length;v++)
            {
                var w=weights[v];var p=Vector3.zero;
                if(w.weight0>0)p+=skin[w.boneIndex0].MultiplyPoint3x4(verts[v])*w.weight0;
                if(w.weight1>0)p+=skin[w.boneIndex1].MultiplyPoint3x4(verts[v])*w.weight1;
                if(w.weight2>0)p+=skin[w.boneIndex2].MultiplyPoint3x4(verts[v])*w.weight2;
                if(w.weight3>0)p+=skin[w.boneIndex3].MultiplyPoint3x4(verts[v])*w.weight3;
                if(p.y<min)min=p.y;if(p.y>max)max=p.y;
            }
            return (min,max);
        }

        [MenuItem("Athen Hill/Characters/Install main character (next level, 2 Oct 2026)")]
        public static void InstallMenu(){Debug.Log(Install());}

        public static string Install()
        {
            if(EditorApplication.isPlaying)throw new InvalidOperationException("Exit Play first.");
            if(EditorSceneManager.GetActiveScene().path!=Scene)EditorSceneManager.OpenScene(Scene,OpenSceneMode.Single);
            var log=new List<object>();
            var motor=Motor();var combat=Combat();
            var old=motor.visual;
            var oldSkin=old.GetComponentsInChildren<SkinnedMeshRenderer>(true).FirstOrDefault();
            var oldBones=oldSkin?new HashSet<string>(oldSkin.bones.Select(b=>b.name)):new HashSet<string>();
            log.Add(new{step="before",visual=old.name,mesh=oldSkin&&oldSkin.sharedMesh?oldSkin.sharedMesh.name:"-",triangles=oldSkin&&oldSkin.sharedMesh?oldSkin.sharedMesh.triangles.Length/3:0,
                prefab=AssetDatabase.GetAssetPath(PrefabUtility.GetCorrespondingObjectFromSource(old)),
                actor=motor.actor?new{idle=N(motor.actor.idle),talk=N(motor.actor.talk),walk=N(motor.actor.walk),run=N(motor.actor.run),jump=N(motor.actor.jumpTakeoff),motor.actor.walkStrideSpeed,motor.actor.runStrideSpeed}:null,
                nonBoneChildren=old.GetComponentsInChildren<Transform>(true).Where(t=>t!=old&&!oldBones.Contains(t.name)&&!t.GetComponent<SkinnedMeshRenderer>()&&(!t.parent||oldBones.Contains(t.parent.name)||t.parent==old)).Select(t=>t.name+" < "+t.parent.name).ToArray()});
            // the shadow proxy must stay under the interpolated visual (CharacterMotionAssetTests): park it on the player while the visual is replaced
            var proxy=motor.GetComponentsInChildren<Transform>(true).FirstOrDefault(t=>t.name==ProxyName);   // under the old visual (or parked on the player by an aborted run)
            Vector3 pPos=Vector3.zero,pScale=Vector3.one;Quaternion pRot=Quaternion.identity;
            if(proxy){pPos=proxy.localPosition;pRot=proxy.localRotation;pScale=proxy.localScale;proxy.SetParent(motor.transform,false);}
            // 1. the existing import (prefab rebuilt from colonist.glb, scene visual replaced, controller/spawn kept)
            ImportMeshyPlayer.Install();
            motor=Motor();combat=Combat();
            var visual=motor.visual;var rig=visual.GetChild(0);
            // 2. normalise: soles on the controller origin, 1.8 m tall in the sampled idle (not the bind-pose bounds)
            if(motor.actor.idle)motor.actor.idle.SampleAnimation(motor.actor.animationSource.gameObject,0);
            var m0=Measure(visual);
            float k=Height/(m0.top-m0.soles);
            rig.localScale=rig.localScale*k;rig.localPosition=new Vector3(0,-m0.soles*k,0);
            var m1=Measure(visual);
            PrefabUtility.ApplyPrefabInstance(visual.gameObject,InteractionMode.AutomatedAction);
            log.Add(new{step="normalise",importHeight=m0.top-m0.soles,importSoles=m0.soles,scale=rig.localScale.x,offsetY=rig.localPosition.y,height=m1.top-m1.soles,soles=m1.soles});
            if(Mathf.Abs(m1.top-m1.soles-Height)>.002f||Mathf.Abs(m1.soles)>.002f)throw new InvalidOperationException("Normalisation failed: "+JsonConvert.SerializeObject(log));
            if(proxy){proxy.SetParent(visual,false);proxy.localPosition=pPos;proxy.localRotation=pRot;proxy.localScale=pScale;log.Add(new{step="proxy",kept=true});}
            else log.Add(new{step="proxy",kept=false});
            SaveAll();
            // 3. authored Player motion family (static idle/talk, five jump clips) rebuilt for the new rest pose; the scene actor gets the jump clips
            var reports=new List<object>();
            Call(typeof(CharacterMotionPass),"AuthorPrefab",PrefabPath,"Player",ModelPath,true,reports);
            Call(typeof(CharacterMotionPass),"Configure",motor.actor,"Player",true,0f);
            log.Add(new{step="motion",clips=reports});
            // 4. library clips retargeted onto the new skeleton (Source/Player/Player_<name>.glb -> Player/lib_<name>.anim)
            log.Add(new{step="retarget",result=CharacterFeelPass.RetargetPlayerClips()});
            // 4b. grips follow the installed hand: palm centre along the RightHand bone (MPFB palm ~0.06 m, main_char_OK 0.121 m)
            var palm=MeasurePalm();PistolGripAlong=RifleArmourInstall.GripAlong=Mathf.Max(.02f,palm.along-.011f);
            log.Add(new{step="grip",palmAlong=palm.along,palmPerp=palm.perp,gripAlong=PistolGripAlong});
            // 5. the Berms scrap pistol in the new right hand (private helper of the Berms installer; same mount rule)
            Call(typeof(OuterBermsPass),"AttachPistol",combat,motor);
            if(!combat.heldPistol||!combat.muzzlePoint)throw new InvalidOperationException("Pistol was not attached.");
            log.Add(new{step="pistol",holder=combat.heldPistol.name,parent=combat.heldPistol.transform.parent.name});
            SaveAll();
            // 6. pistol feel: hold clip from lib_aim_95, aim pose bones, pistol mount, flashes, first-person view model + grip hands
            log.Add(new{step="weaponFeel",result=WeaponFeelPass.Install()});
            log.Add(new{step="pistolRemount",result=RemountPistol()});
            SaveAll();
            // 7. pistol mod attachments on both pistols (reopens the saved scene itself)
            PistolModsInstall.Install();
            motor=Motor();combat=Combat();
            log.Add(new{step="pistolMods",held=combat.heldPistol.GetComponent<WeaponModVisuals>()?combat.heldPistol.GetComponent<WeaponModVisuals>().mods.childCount:-1});
            // 8. rifle holds, held rifle, plate carrier, order bindings, review cameras, landmarks
            log.Add(new{step="rifleArmour",result=RifleArmourInstall.InstallAll()});
            // 9. breathing idle (lib_idle_252) and the surface footsteps on the new feet
            log.Add(new{step="idle",result=CharacterFeelPass.InstallPlayerIdle()});
            log.Add(new{step="footsteps",result=CharacterFeelPass.InstallFootsteps()});
            motor=Motor();
            log.Add(new{step="cameras",result=Cameras(motor)});
            SaveAll();
            var text=JsonConvert.SerializeObject(new{utc=DateTime.UtcNow.ToString("O"),log},Formatting.Indented);
            Directory.CreateDirectory(Evidence);File.WriteAllText(Path.Combine(Evidence,"install.json"),text);
            try{Directory.CreateDirectory(Report);File.WriteAllText(Path.Combine(Report,"install.json"),text);}catch(Exception e){Debug.LogWarning(e.Message);}
            return text;
        }
        static string N(Object o)=>o?o.name:"-";

        /// Player-height review cameras for the character itself at the rifle review stand (the colonist faces -X there).
        static string Cameras(PlayerMotor motor)
        {
            var scene=EditorSceneManager.GetActiveScene();
            foreach(var old in scene.GetRootGameObjects().Where(g=>g.name==CamerasRoot).ToArray())Object.DestroyImmediate(old);
            var root=new GameObject(CamerasRoot);
            var template=Object.FindObjectsByType<Camera>(FindObjectsInactive.Include,FindObjectsSortMode.None).FirstOrDefault(c=>c.name=="cam_checkpoint_player");
            void Cam(string name,Vector3 pos,Vector3 look,float fov)
            {
                var go=new GameObject(name);go.transform.SetParent(root.transform,false);
                var cam=go.AddComponent<Camera>();if(template)cam.CopyFrom(template);cam.enabled=false;cam.fieldOfView=fov;
                go.transform.position=pos;go.transform.LookAt(look);
            }
            var s=RifleArmourInstall.Stand;
            Cam("cam_character_idle",s+new Vector3(-2.3f,1.25f,1.4f),s+new Vector3(0,1.0f,0),34);      // front three-quarter, full body
            Cam("cam_character_face",s+new Vector3(-0.95f,1.62f,0.35f),s+new Vector3(0,1.55f,0),28);   // face and hair at conversation distance
            Cam("cam_character_back",s+new Vector3(2.4f,1.3f,-1.2f),s+new Vector3(0,1.0f,0),34);       // back three-quarter (follow-camera side)
            return "cameras: cam_character_idle, cam_character_face, cam_character_back";
        }

        // ---------------------------------------------------------------- check (-nographics)
        public static string Check()
        {
            if(EditorSceneManager.GetActiveScene().path!=Scene)EditorSceneManager.OpenScene(Scene,OpenSceneMode.Single);
            var fails=new List<string>();var info=new Dictionary<string,object>();
            void Must(bool ok,string what){if(!ok)fails.Add(what);}
            var motor=Motor();var combat=Combat();var visual=motor.visual;
            Must(visual&&visual.parent==motor.transform,"visual under the player");
            Must(AssetDatabase.GetAssetPath(PrefabUtility.GetCorrespondingObjectFromSource(visual))==PrefabPath,"visual is a MeshyPlayer prefab instance");
            var skin=visual.GetComponentsInChildren<SkinnedMeshRenderer>(true).OrderByDescending(x=>x.sharedMesh?x.sharedMesh.vertexCount:0).FirstOrDefault();
            Must(skin&&skin.sharedMesh,"skinned mesh");
            if(skin&&skin.sharedMesh)
            {
                int tris=skin.sharedMesh.triangles.Length/3;info["triangles"]=tris;info["vertices"]=skin.sharedMesh.vertexCount;info["bones"]=skin.bones.Length;
                info["mesh"]=skin.sharedMesh.name;info["meshAsset"]=AssetDatabase.GetAssetPath(skin.sharedMesh);
                Must(AssetDatabase.GetAssetPath(skin.sharedMesh)==ModelPath,"mesh comes from "+ModelPath);
                Must(tris>40000&&tris<90000,"LOD0 triangles 40k-90k (got "+tris+")");
                Must(skin.bones.Length>=24,"at least the 24 game bones (MPFB rig adds fingers)");
                foreach(var b in new[]{"Hips","Spine02","Spine01","Spine","neck","Head","LeftHand","RightHand","LeftFoot","RightFoot"})Must(skin.bones.Any(x=>x.name==b),"bone "+b);
                var mats=skin.sharedMaterials;info["materials"]=mats.Select(m=>m?m.name+" ("+m.shader.name+")":"null").ToArray();
                Must(mats.All(m=>m&&!m.shader.name.Contains("Error")),"materials import");
                if(mats.Length>0&&mats[0]){var m=mats.FirstOrDefault(x=>x&&((x.HasProperty("normalTexture")&&x.GetTexture("normalTexture"))||(x.HasProperty("_BumpMap")&&x.GetTexture("_BumpMap"))))??mats[0];info["textures"]=m.GetTexturePropertyNames().Where(n=>m.GetTexture(n)).ToDictionary(n=>n,n=>{var t=m.GetTexture(n);return t.name+" "+t.width+"x"+t.height+" "+(t is Texture2D t2?t2.format.ToString():"");});
                    bool Has(params string[] names)=>names.Any(n=>m.HasProperty(n)&&m.GetTexture(n));
                    Must(Has("_BaseMap","baseColorTexture")&&Has("_BumpMap","normalTexture"),"base and normal maps bound");}
                Must(skin.shadowCastingMode==ShadowCastingMode.On,"body casts shadows");
                Must(skin.gameObject.layer==8,"player layer 8");
            }
            var actor=motor.actor;Must(actor&&actor.animationSource,"ActorAnimation with Animation");
            if(actor)
            {
                info["actor"]=new{idle=N(actor.idle),talk=N(actor.talk),walk=N(actor.walk),run=N(actor.run),jumpTakeoff=N(actor.jumpTakeoff),jumpLanding=N(actor.jumpLanding),actor.walkStrideSpeed,actor.runStrideSpeed};
                Must(actor.idle&&actor.idle.name=="lib_idle_252","breathing idle lib_idle_252");
                Must(actor.walk&&actor.walk.legacy&&AssetDatabase.GetAssetPath(actor.walk)==ModelPath,"walk from the GLB");
                Must(actor.run&&actor.run.legacy&&AssetDatabase.GetAssetPath(actor.run)==ModelPath,"run from the GLB");
                Must(actor.jumpTakeoff&&actor.jumpAirborne&&actor.jumpFall&&actor.jumpLanding&&actor.jumpLandingMoving,"jump clips");
                if(actor.idle&&actor.animationSource)
                {
                    actor.idle.SampleAnimation(actor.animationSource.gameObject,0);
                    var m=Measure(visual);info["idleHeight"]=m.top-m.soles;info["idleSoles"]=m.soles;
                    Must(Mathf.Abs(m.top-m.soles-Height)<.01f,"idle height 1.8 m (got "+(m.top-m.soles).ToString("F3")+")");
                    Must(Mathf.Abs(m.soles)<.01f,"soles at the controller origin (got "+m.soles.ToString("F3")+")");
                    // the idle must animate: the largest bone rotation across four instants of the clip
                    var bones=skin.bones;var rest=bones.Select(b=>b.localRotation).ToArray();float maxDeg=0;
                    foreach(var f in new[]{.25f,.5f,.75f}){actor.idle.SampleAnimation(actor.animationSource.gameObject,actor.idle.length*f);for(int i=0;i<bones.Length;i++)maxDeg=Mathf.Max(maxDeg,Quaternion.Angle(rest[i],bones[i].localRotation));}
                    info["idleMaxBoneDegrees"]=maxDeg;Must(maxDeg>.2f,"idle animates (max bone motion "+maxDeg.ToString("F2")+" deg)");
                    actor.idle.SampleAnimation(actor.animationSource.gameObject,0);
                }
            }
            bool Under(Transform t)=>t&&t.IsChildOf(visual);
            Must(combat.heldPistol&&Under(combat.heldPistol.transform)&&combat.heldPistol.transform.parent.name=="RightHand","held pistol under the new RightHand");
            Must(combat.muzzlePoint&&Under(combat.muzzlePoint),"pistol muzzle");
            Must(combat.heldRifle&&Under(combat.heldRifle.transform)&&combat.heldRifle.transform.parent.name=="RightHand","held rifle under the new RightHand");
            Must(combat.rifleMuzzle&&Under(combat.rifleMuzzle),"rifle muzzle");
            Must(combat.thirdPersonFlash&&Under(combat.thirdPersonFlash.transform),"third-person flash");
            var mods=combat.heldPistol?combat.heldPistol.GetComponent<WeaponModVisuals>():null;
            Must(mods&&mods.mods&&mods.mods.childCount>=6,"pistol mod visuals on the held pistol");
            var pose=combat.GetComponent<PlayerWeaponPose>();Must(pose,"PlayerWeaponPose");
            if(pose)
            {
                Must(pose.mixRoot&&pose.mixRoot.name=="Spine02"&&Under(pose.mixRoot),"mixRoot Spine02 on the new rig");
                Must(pose.spine.Length==3&&pose.spine.All(Under)&&pose.spine.Select(x=>x.name).SequenceEqual(new[]{"Spine02","Spine01","Spine"}),"spine list");
                Must(pose.rightHand&&pose.rightHand.name=="RightHand"&&Under(pose.rightHand),"rightHand on the new rig");
                Must(pose.aimClip&&pose.aimClip.name=="pistol_hold","pistol_hold clip");
                Must(pose.rifleAimClip&&pose.rifleAimClip.name=="rifle_hold"&&pose.rifleCarryClip&&pose.rifleCarryClip.name=="rifle_carry","rifle clips");
                Must(pose.actor==actor&&pose.combat==combat,"pose wiring");
                // the hold clips must bind to the installed rig
                foreach(var c in new[]{pose.aimClip,pose.rifleAimClip,pose.rifleCarryClip})if(c)
                {
                    var paths=AnimationUtility.GetCurveBindings(c).Select(b=>b.path).Distinct().ToArray();
                    int bound=paths.Count(p=>actor.animationSource.transform.Find(p));
                    info["bind_"+c.name]=bound+"/"+paths.Length;Must(bound==paths.Length&&bound>0,c.name+" binds to the rig ("+bound+"/"+paths.Length+")");
                }
            }
            var armour=combat.GetComponent<PlayerArmourVisuals>();Must(armour&&armour.pieces.Length>0&&armour.pieces.All(p=>p.model&&Under(p.model.transform)),"plate carrier under the new chest");
            // rigid pieces hang under the chest bone; skinned tutorial-set pieces (TutorialSetInstall) sit beside the body renderer on the same bones
            if(armour!=null)foreach(var p in armour.pieces.Where(p=>p.model))
                Must(p.model.name.StartsWith(TutorialSetInstall.Prefix)?p.model.GetComponent<SkinnedMeshRenderer>()&&p.model.GetComponent<SkinnedMeshRenderer>().bones.All(b=>b&&Under(b)):p.model.transform.parent.name=="Spine",p.itemId+" mounted on the new rig");
            var steps=motor.GetComponent<FootstepAudio>();Must(steps&&Under(steps.leftFoot)&&Under(steps.rightFoot),"footstep feet on the new rig");
            // the scene holds two FirstPersonViewModel components; check the one combat drives (grip hands can sit below the arms rig)
            var vm=combat.viewModel;Must(vm,"combat.viewModel");
            Must(vm&&vm.pistol&&vm.pistol.GetComponentsInChildren<Transform>(true).Any(t=>t.name=="FP hands v2"),"first-person view model with the grip hands");
            var proxy=visual.GetComponentsInChildren<MeshRenderer>(true).FirstOrDefault(r=>r.name==ProxyName);Must(proxy&&proxy.shadowCastingMode==ShadowCastingMode.ShadowsOnly,"shadow proxy under the visual");
            foreach(var cam in new[]{"cam_character_idle","cam_character_face","cam_character_back","cam_rifle_carry","cam_rifle_side","cam_vest_front","cam_checkpoint_player"})
                Must(Object.FindObjectsByType<Camera>(FindObjectsInactive.Include,FindObjectsSortMode.None).Any(c=>c.name==cam),"camera "+cam);
            // missing references on the player, its view model and the review cameras
            var missing=new List<string>();
            var roots=new List<GameObject>{motor.gameObject};if(vm)roots.Add(vm.gameObject);
            foreach(var root in roots)foreach(var c in root.GetComponentsInChildren<Component>(true))
            {
                if(!c){missing.Add("missing script under "+root.name);continue;}
                var so=new SerializedObject(c);var p=so.GetIterator();
                while(p.NextVisible(true))if(p.propertyType==SerializedPropertyType.ObjectReference&&p.objectReferenceValue==null&&!p.objectReferenceEntityIdValue.Equals(default(UnityEngine.EntityId)))missing.Add(c.name+"."+c.GetType().Name+"."+p.propertyPath);
            }
            info["missingReferences"]=missing;Must(missing.Count==0,"no missing references ("+missing.Count+")");
            var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            var pActor=prefab.GetComponent<ActorAnimation>();info["prefabActor"]=new{idle=N(pActor.idle),walk=N(pActor.walk),run=N(pActor.run),jump=N(pActor.jumpTakeoff)};
            var text=JsonConvert.SerializeObject(new{utc=DateTime.UtcNow.ToString("O"),pass=fails.Count==0,fails,info},Formatting.Indented);
            Directory.CreateDirectory(Evidence);File.WriteAllText(Path.Combine(Evidence,"check.json"),text);
            if(fails.Count>0)throw new InvalidOperationException("Check failed: "+string.Join("; ",fails)+"\n"+text);
            return text;
        }

        // ---------------------------------------------------------------- capture (graphics batch, <= 6 cameras)
        public static string Capture()
        {
            EditorSceneManager.OpenScene(Scene,OpenSceneMode.Single);
            var outDir=Path.Combine(Evidence,"captures");Directory.CreateDirectory(outDir);
            var motor=Motor();var combat=Combat();var actor=motor.actor;var animRoot=actor.animationSource.gameObject;var body=motor.visual;
            // 13:00 lighting frame, as the lookbook does
            var clock=Object.FindFirstObjectByType<CityTimeOfDay>(FindObjectsInactive.Include);
            if(clock&&clock.profile)
            {
                var f=clock.profile.Evaluate(13f);
                clock.keyLight.transform.rotation=Quaternion.Euler(f.keyEuler);clock.keyLight.color=f.keyColor;clock.keyLight.intensity=f.keyIntensity;
                if(clock.skyFill){clock.skyFill.color=f.fillColor;clock.skyFill.intensity=f.fillIntensity;}
                RenderSettings.ambientMode=AmbientMode.Trilight;RenderSettings.ambientSkyColor=f.ambientSky;RenderSettings.ambientEquatorColor=f.ambientEquator;RenderSettings.ambientGroundColor=f.ambientGround;RenderSettings.fogColor=f.fogColor;
                var sky=new Material(clock.timeAwareSky);
                sky.SetColor("_Zenith",f.skyZenith);sky.SetColor("_Middle",f.skyMiddle);sky.SetColor("_Horizon",f.skyHorizon);sky.SetColor("_CloudLight",f.cloudLight);sky.SetColor("_CloudShade",f.cloudShade);
                sky.SetFloat("_Exposure",f.skyExposure);sky.SetFloat("_SunVisibility",f.sunVisibility);sky.SetVector("_SunDirection",-clock.keyLight.transform.forward);
                RenderSettings.skybox=sky;RenderSettings.sun=clock.keyLight;
                if(clock.gradingVolume&&clock.gradingVolume.sharedProfile.TryGet<ColorAdjustments>(out var ca))ca.postExposure.value=f.postExposure;
            }
            var cams=Object.FindObjectsByType<Camera>(FindObjectsInactive.Include,FindObjectsSortMode.None).ToDictionary(c=>c.name,c=>c);
            var pistol=combat.heldPistol;var rifle=combat.heldRifle;var vest=combat.GetComponent<PlayerArmourVisuals>().pieces[0].model;
            var pose=combat.GetComponent<PlayerWeaponPose>();
            AnimationClip Clip(string n)=>AssetDatabase.LoadAssetAtPath<AnimationClip>(PlayerFolder+"/"+n+".anim");
            void Stand(Vector3 feet,Vector3 facing)
            {
                if(Physics.Raycast(feet+Vector3.up*6,Vector3.down,out var hit,30,~(1<<8),QueryTriggerInteraction.Ignore))feet.y=hit.point.y;
                motor.transform.position=feet+Vector3.up*.015f;body.rotation=Quaternion.LookRotation(Vector3.ProjectOnPlane(facing,Vector3.up).normalized,Vector3.up);
            }
            void Pose(string clipName,float t,bool showPistol,bool showRifle,bool showVest,float pistolCarryPitch=-1)
            {
                actor.idle.SampleAnimation(animRoot,0.4f);
                if(clipName!=null){var c=Clip(clipName);if(c)c.SampleAnimation(animRoot,t);}
                pistol.SetActive(showPistol);rifle.SetActive(showRifle);vest.SetActive(showVest);
                if(showPistol&&pistolCarryPitch>=0)
                {   // the carry turn PlayerWeaponPose applies in LateUpdate when the pistol is drawn but not raised
                    var w=pistol.transform;var carry=Quaternion.FromToRotation(w.forward,PlayerWeaponPose.CarryDirection(body,pistolCarryPitch));w.rotation=carry*w.rotation;
                }
            }
            var log=new List<string>();
            if(combat.muzzleLight)combat.muzzleLight.enabled=false;   // the Berms flash point light is lit in edit mode (cyan tint on the first capture round)
            string Diag()=>$"forward {body.forward:F2} feet {motor.transform.position:F2} head {Bone(actor,"Head").position:F2} rHand {Bone(actor,"RightHand").position:F2} lHand {Bone(actor,"LeftHand").position:F2} pistol {pistol.activeSelf} rifle {rifle.activeSelf} vest {vest.activeSelf}";
            var rt=new RenderTexture(1600,900,24,RenderTextureFormat.ARGB32){antiAliasing=1};var tex=new Texture2D(1600,900,TextureFormat.RGB24,false);
            // In a batch method nothing ticks the player loop between a pose change and cam.Render(), so the skinned mesh
            // keeps the matrices of its last skinning (the idle) while the bones, and the holders under them, are posed.
            // Render a CPU-baked copy of the body in the current pose instead (BakeMesh gives world-scale vertices in the
            // renderer's frame on this version; see the Measure note).
            var smrs=body.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(x=>x.enabled&&x.gameObject.activeInHierarchy).ToArray();
            var baked=new List<GameObject>();
            void BakeBody()
            {
                foreach(var g in baked)Object.DestroyImmediate(g);baked.Clear();
                foreach(var x in smrs)
                {
                    var mesh=new Mesh();x.BakeMesh(mesh,false);
                    var g=new GameObject("__baked "+x.name,typeof(MeshFilter),typeof(MeshRenderer));g.layer=x.gameObject.layer;
                    g.transform.SetPositionAndRotation(x.transform.position,x.transform.rotation);
                    g.GetComponent<MeshFilter>().sharedMesh=mesh;var mr=g.GetComponent<MeshRenderer>();mr.sharedMaterials=x.sharedMaterials;mr.shadowCastingMode=x.shadowCastingMode;mr.receiveShadows=x.receiveShadows;
                    x.enabled=false;baked.Add(g);
                }
            }
            void Shot(string camName,string file)
            {
                BakeBody();
                if(!cams.TryGetValue(camName,out var src)){log.Add("missing camera "+camName);return;}
                var go=new GameObject("__cap");var cam=go.AddComponent<Camera>();cam.CopyFrom(src);cam.enabled=false;cam.nearClipPlane=.05f;cam.farClipPlane=650;
                var d=go.AddComponent<UniversalAdditionalCameraData>();var sd=src.GetComponent<UniversalAdditionalCameraData>();
                d.renderPostProcessing=true;d.antialiasing=AntialiasingMode.SubpixelMorphologicalAntiAliasing;d.renderShadows=true;d.volumeLayerMask=~0;d.volumeTrigger=go.transform;
                if(sd){cam.cullingMask=src.cullingMask;}
                go.transform.SetPositionAndRotation(src.transform.position,src.transform.rotation);
                cam.targetTexture=rt;for(int i=0;i<3;i++)cam.Render();
                RenderTexture.active=rt;tex.ReadPixels(new Rect(0,0,1600,900),0,0);tex.Apply();File.WriteAllBytes(Path.Combine(outDir,file+".png"),tex.EncodeToPNG());
                RenderTexture.active=null;cam.targetTexture=null;Object.DestroyImmediate(go);log.Add(file+" from "+camName+" at "+src.transform.position.ToString("F2")+": "+Diag());
            }
            var stand=RifleArmourInstall.Stand;
            Stand(stand,Vector3.left);
            if(RifleOnly)
            {   // the rifle re-tune round: hold and carry at the three rifle cameras (captures/rifle/)
                outDir=Path.Combine(Evidence,"captures-rifle");Directory.CreateDirectory(outDir);
                foreach(var (clip,label) in new[]{("rifle_hold","hold"),("rifle_carry","carry")})
                    foreach(var cam in new[]{"cam_rifle_aim","cam_rifle_side","cam_rifle_carry"})
                    {Pose(clip,0,false,true,false);Shot(cam,label+"_"+cam);}
                rt.Release();Object.DestroyImmediate(tex);foreach(var g in baked)Object.DestroyImmediate(g);foreach(var x in smrs)x.enabled=true;
                var t2=string.Join("\n",log);File.WriteAllText(Path.Combine(outDir,"captures.txt"),t2+"\n");return t2;
            }
            Pose(null,0,false,false,false);Shot("cam_character_idle","01_idle_cam_character_idle");
            Pose(null,0,false,false,false);Shot("cam_character_face","02_face_cam_character_face");
            Pose(null,0,true,false,false,pose?pose.carryPitch:60);Shot("cam_character_back","03_pistol_carry_cam_character_back");   // back-right quarter: the right hand is on the camera side
            Pose("rifle_hold",0,false,true,false);Shot("cam_rifle_aim","04_rifle_hold_cam_rifle_aim");                                 // front-left quarter: both hands on the rifle
            Pose(null,0,false,false,true);Shot("cam_vest_front","05_vest_cam_vest_front");
            // the checkpoint camera: put the colonist where it looks, facing it
            if(cams.TryGetValue("cam_checkpoint_player",out var cp))
            {
                var t=cp.transform;Vector3 feet=t.position+t.forward*3f;
                if(Physics.Raycast(t.position,t.forward,out var hit,40,~(1<<8),QueryTriggerInteraction.Ignore))feet=hit.point;
                Stand(feet,t.position-feet);Pose(null,0,false,false,false);Shot("cam_checkpoint_player","06_idle_cam_checkpoint_player");
            }
            rt.Release();Object.DestroyImmediate(tex);foreach(var g in baked)Object.DestroyImmediate(g);foreach(var x in smrs)x.enabled=true;
            // the scene is not saved: poses, holders and the player position are capture-only state
            var text=string.Join("\n",log);File.WriteAllText(Path.Combine(outDir,"captures.txt"),text+"\n");
            return text;
        }

        // ---------------------------------------------------------------- debug: where the hold clips put the hands on the installed rig
        public static void DebugHoldBatch(){Batch(DebugHold);}
        public static string DebugHold()
        {
            if(EditorSceneManager.GetActiveScene().path!=Scene)EditorSceneManager.OpenScene(Scene,OpenSceneMode.Single);
            var motor=Motor();var actor=motor.actor;var root=actor.animationSource.gameObject;var body=motor.visual;
            var sb=new System.Text.StringBuilder();
            string P(string n){var t=Bone(actor,n);var l=body.InverseTransformPoint(t.position);return n+" "+l.ToString("F2");}
            void Row(string label){sb.AppendLine(label+": "+P("Head")+" | "+P("LeftArm")+" | "+P("LeftHand")+" | "+P("RightArm")+" | "+P("RightHand")+" | "+P("Hips"));}
            foreach(var (name,frac) in new[]{("lib_idle_252",0f),("lib_rifleturn_573",.95f),("lib_aim_95",.97f),("lib_lower_334",.5f),("rifle_hold",0f),("pistol_hold",0f),("rifle_carry",0f)})
            {
                var c=AssetDatabase.LoadAssetAtPath<AnimationClip>(PlayerFolder+"/"+name+".anim");
                if(!c){sb.AppendLine(name+": missing");continue;}
                actor.idle.SampleAnimation(root,0);c.SampleAnimation(root,c.length*frac);
                var paths=AnimationUtility.GetCurveBindings(c).GroupBy(b=>b.path).ToDictionary(g=>g.Key,g=>g.Count());
                Row(name+" @"+(c.length*frac).ToString("F2")+"s, "+paths.Count+" paths, left arm curves "+paths.Where(k=>k.Key.EndsWith("LeftArm")||k.Key.EndsWith("LeftForeArm")||k.Key.EndsWith("LeftHand")).Sum(k=>k.Value)+", unbound "+string.Join(",",paths.Keys.Where(k=>!actor.animationSource.transform.Find(k))));
            }
            // the Meshy source clip as imported (glTFast legacy) for comparison
            var src=AssetDatabase.LoadAllAssetsAtPath("Assets/AthenHill/Art/CharacterMotion/Source/Player/Player_rifleturn_573.glb").OfType<AnimationClip>().FirstOrDefault();
            if(src)sb.AppendLine("source Player_rifleturn_573 clip "+src.name+" legacy "+src.legacy+" "+src.length.ToString("F2")+"s paths "+string.Join(" ",AnimationUtility.GetCurveBindings(src).Select(b=>b.path).Distinct().Take(6)));
            actor.idle.SampleAnimation(root,0);
            return sb.ToString();
        }

        // ---------------------------------------------------------------- grip measurement: palm centroids vs holder origins
        public static void MeasureGripsBatch(){Batch(MeasureGrips);}
        /// CPU-skinned centroid of the vertices dominated by a bone, in world space (the open hand's palm/back centre).
        static Vector3 BoneCentroid(SkinnedMeshRenderer smr,string bone,float minWeight)
        {
            var mesh=smr.sharedMesh;var verts=mesh.vertices;var weights=mesh.boneWeights;var bind=mesh.bindposes;
            int bi=Array.FindIndex(smr.bones,b=>b.name==bone);var skin=new Matrix4x4[smr.bones.Length];
            for(int i=0;i<skin.Length;i++)skin[i]=smr.bones[i].localToWorldMatrix*bind[i];
            var sum=Vector3.zero;int n=0;
            for(int v=0;v<verts.Length;v++)
            {
                var w=weights[v];float wb=(w.boneIndex0==bi?w.weight0:0)+(w.boneIndex1==bi?w.weight1:0)+(w.boneIndex2==bi?w.weight2:0)+(w.boneIndex3==bi?w.weight3:0);
                if(wb<minWeight)continue;
                var p=Vector3.zero;
                if(w.weight0>0)p+=skin[w.boneIndex0].MultiplyPoint3x4(verts[v])*w.weight0;if(w.weight1>0)p+=skin[w.boneIndex1].MultiplyPoint3x4(verts[v])*w.weight1;
                if(w.weight2>0)p+=skin[w.boneIndex2].MultiplyPoint3x4(verts[v])*w.weight2;if(w.weight3>0)p+=skin[w.boneIndex3].MultiplyPoint3x4(verts[v])*w.weight3;
                sum+=p;n++;
            }
            return n>0?sum/n:Vector3.zero;
        }
        /// Palm centre of the installed right hand: CPU-skinned centroid of the vertices dominated by RightHand, as distance
        /// along the hand bone (its local +Y) and off it.
        static (float along,float perp) MeasurePalm()
        {
            var motor=Motor();var actor=motor.actor;
            if(actor.idle)actor.idle.SampleAnimation(actor.animationSource.gameObject,0);
            var smr=motor.visual.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(r=>!r.name.StartsWith(TutorialSetInstall.Prefix)).OrderByDescending(x=>x.sharedMesh?x.sharedMesh.vertexCount:0).First();
            var hand=Bone(actor,"RightHand");var palm=BoneCentroid(smr,"RightHand",.7f);
            var along=(hand.rotation*Vector3.up).normalized;var d=palm-hand.position;
            return (Vector3.Dot(d,along),Vector3.ProjectOnPlane(d,along).magnitude);
        }
        public static string MeasureGrips()
        {
            if(EditorSceneManager.GetActiveScene().path!=Scene)EditorSceneManager.OpenScene(Scene,OpenSceneMode.Single);
            var motor=Motor();var combat=Combat();var actor=motor.actor;var root=actor.animationSource.gameObject;var body=motor.visual;
            var smr=body.GetComponentsInChildren<SkinnedMeshRenderer>(true).OrderByDescending(x=>x.sharedMesh?x.sharedMesh.vertexCount:0).First();
            var hand=Bone(actor,"RightHand");var left=Bone(actor,"LeftHand");
            var sb=new System.Text.StringBuilder();
            void Row(string clipName,GameObject holder)
            {
                var c=AssetDatabase.LoadAssetAtPath<AnimationClip>(PlayerFolder+"/"+clipName+".anim");
                actor.idle.SampleAnimation(root,0);c.SampleAnimation(root,0);
                var palm=BoneCentroid(smr,"RightHand",.7f);var lpalm=BoneCentroid(smr,"LeftHand",.7f);
                var h=holder.transform;var d=palm-h.position;
                var along=(hand.rotation*Vector3.up).normalized;
                var inHolder=Quaternion.Inverse(h.rotation)*d;
                var inBody=new Vector3(Vector3.Dot(d,body.right),Vector3.Dot(d,body.up),Vector3.Dot(d,body.forward));
                sb.AppendLine($"{clipName} / {holder.name}: holder {h.position:F3} palm {palm:F3} delta {d.magnitude:F3} m; in holder frame (x right, y up, z barrel) {inHolder:F3}; in body frame {inBody:F3}; along hand bone {Vector3.Dot(d,along):F3}; hand bone pos {hand.position:F3} bone->palm along {Vector3.Dot(palm-hand.position,along):F3} perp {(Vector3.ProjectOnPlane(palm-hand.position,along)).magnitude:F3}; left palm {lpalm:F3} left palm in holder frame {Quaternion.Inverse(h.rotation)*(lpalm-h.position):F3}");
            }
            Row("rifle_hold",combat.heldRifle);Row("rifle_carry",combat.heldRifle);Row("pistol_hold",combat.heldPistol);Row("lib_idle_252",combat.heldPistol);
            actor.idle.SampleAnimation(root,0);
            sb.AppendLine($"RifleArmourInstall GripAlong {RifleArmourInstall.GripAlong} GripFromButt {RifleArmourInstall.GripFromButt} GripFromBottom {RifleArmourInstall.GripFromBottom} RifleLength {RifleArmourInstall.RifleLength} MuzzleSign {RifleArmourInstall.MuzzleSign}");
            return sb.ToString();
        }

        // ---------------------------------------------------------------- pistol remount for the new hand (WeaponFeelPass keeps its 0.075 m rule and the first-person view model)
        public static float PistolGripAlong=.11f;   // palm centre 0.121 m along the main_char_OK RightHand bone; since the MPFB player (2 Oct 2026) measured per install by MeasurePalm (grip 0.011 m short of the palm centre)
        public static void RemountPistolBatch(){Batch(()=>{if(EditorSceneManager.GetActiveScene().path!=Scene)EditorSceneManager.OpenScene(Scene,OpenSceneMode.Single);var r=RemountPistol();SaveAll();return r;});}
        public static string RemountPistol()
        {
            var combat=Combat();var motor=Motor();var hand=combat.heldPistol.transform.parent;var root=motor.actor.animationSource.gameObject;var body=motor.visual;
            var hold=AssetDatabase.LoadAssetAtPath<AnimationClip>(PlayerFolder+"/pistol_hold.anim");
            hold.SampleAnimation(root,0);
            var pistol=combat.heldPistol.transform;var before=pistol.localPosition;
            var along=(hand.rotation*Vector3.up).normalized;
            pistol.rotation=Quaternion.LookRotation(body.forward,body.up);
            pistol.position=hand.position+along*PistolGripAlong-body.up*.01f;
            if(motor.actor.idle)motor.actor.idle.SampleAnimation(root,0);
            EditorUtility.SetDirty(pistol);
            return "pistol remounted: grip "+PistolGripAlong.ToString("F3")+" m along the hand; local "+before.ToString("F3")+" -> "+pistol.localPosition.ToString("F3");
        }
    }
}
