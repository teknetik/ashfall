using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    /// Tutorial set (2 Oct 2026, art/tutorial_set_20261002): wearable armour as skinned meshes on the player's own
    /// skeleton. Each GLB in Art/Armour/TutorialSet was fitted in Blender to the MPFB2 player body and exported on the same
    /// armature (game_engine rig renamed to the game's bone names), so its bind poses match the body's. The installer
    /// copies each piece's SkinnedMeshRenderer next to the body renderer, rebinds its bones by name to the player's bones and
    /// registers it with PlayerArmourVisuals (shown while its item is equipped in its slot). Called at the end of
    /// RifleArmourInstall.Vest(), so the MainCharacterInstall chain keeps it; idempotent.
    public static class TutorialSetInstall
    {
        public const string Folder="Assets/AthenHill/Art/Armour/TutorialSet/";
        public const string Prefix="Armour ";
        /// glb file, catalog item, equipment slot. Pieces whose GLB is missing are skipped (the set is delivered piecewise).
        public static readonly (string file,string itemId,string slot)[] Pieces=
        {
            ("TS_Helmet.glb","field_helmet","armour_head"),
            ("TS_FieldVest.glb","field_vest","armour_chest"),
            ("TS_ArmGuards.glb","field_armguards","armour_arms"),
            ("TS_Gloves.glb","field_gloves","armour_hands"),
            ("TS_LegArmour.glb","field_leggings","armour_legs"),
            ("TS_Boots.glb","field_boots","armour_feet"),
            ("TS_WardenCarrier.glb","warden_plate_carrier","armour_chest"),
            ("TS_FPArms.glb",FPArmsId,""),   // the colonist's arms for the first-person view models (pistol + rifle), not an equipment piece
        };
        public const string FPArmsId="fp_arms";

        [MenuItem("Athen Hill/Characters/Install tutorial armour set")]
        public static void InstallMenu(){Debug.Log(Install());}

        /// Batch entry (-executeMethod, -nographics): opens the city scene, attaches the pieces, saves.
        public static void InstallBatch()
        {
            int code=0;string text;
            try{text=Install();Debug.Log("TutorialSetInstall OK\n"+text);}
            catch(Exception e){Debug.LogException(e);text="FAILED "+e;code=1;}
            try{var dir=Path.GetFullPath(Path.Combine(Application.dataPath,"../../../art/tutorial_set_20261002/unity"));Directory.CreateDirectory(dir);File.WriteAllText(Path.Combine(dir,"install-log.txt"),text+"\n");}catch(Exception e){Debug.LogException(e);}
            EditorApplication.Exit(code);
        }

        public static string Install()
        {
            const string scenePath="Assets/AthenHill/Scenes/AthenHill.unity";
            if(EditorSceneManager.GetActiveScene().path!=scenePath)EditorSceneManager.OpenScene(scenePath,OpenSceneMode.Single);
            var combat=Object.FindAnyObjectByType<PlayerCombat>(FindObjectsInactive.Include)??throw new InvalidOperationException("No PlayerCombat.");
            var vis=combat.GetComponent<PlayerArmourVisuals>();if(!vis)vis=Undo.AddComponent<PlayerArmourVisuals>(combat.gameObject);
            var log=Attach(combat,vis);
            var s=EditorSceneManager.GetActiveScene();EditorSceneManager.MarkSceneDirty(s);EditorSceneManager.SaveScene(s);AssetDatabase.SaveAssets();
            return log;
        }

        /// Adds the skinned pieces to vis.pieces (replacing earlier copies). A skinned Warden carrier replaces the rigid
        /// one RifleArmourInstall mounts on the chest bone.
        public static string Attach(PlayerCombat combat,PlayerArmourVisuals vis)
        {
            var motor=combat.GetComponent<PlayerMotor>()??throw new InvalidOperationException("No PlayerMotor beside PlayerCombat.");
            var body=motor.visual.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(r=>!r.name.StartsWith(Prefix))
                .OrderByDescending(r=>r.sharedMesh?r.sharedMesh.vertexCount:0).FirstOrDefault()??throw new InvalidOperationException("No body SkinnedMeshRenderer.");
            var bones=new Dictionary<string,Transform>();
            foreach(var t in body.rootBone?body.rootBone.GetComponentsInChildren<Transform>(true):body.bones)if(!bones.ContainsKey(t.name))bones[t.name]=t;
            foreach(var t in body.bones)if(t&&!bones.ContainsKey(t.name))bones[t.name]=t;
            var bodyBind=new Dictionary<string,Matrix4x4>();
            for(int i=0;i<body.bones.Length;i++)if(body.bones[i])bodyBind[body.bones[i].name]=body.sharedMesh.bindposes[i];
            foreach(var old in body.transform.parent.Cast<Transform>().Where(t=>t.name.StartsWith(Prefix)).ToArray())Object.DestroyImmediate(old.gameObject);
            var list=(vis.pieces??new PlayerArmourVisuals.Piece[0]).Where(p=>p!=null&&p.model&&!Pieces.Any(q=>q.itemId==p.itemId&&File.Exists(Folder+q.file))).ToList();
            var log=new List<string>();GameObject fpArmsAsset=null;
            foreach(var (file,itemId,slot) in Pieces)
            {
                var path=Folder+file;
                var asset=AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if(!asset){log.Add(file+": not delivered");continue;}
                if(itemId==FPArmsId){fpArmsAsset=asset;continue;}   // feeds the first-person view models, not the body
                var inst=Object.Instantiate(asset);
                try
                {
                    var src=inst.GetComponentInChildren<SkinnedMeshRenderer>(true)??throw new InvalidOperationException(file+" has no SkinnedMeshRenderer");
                    var go=new GameObject(Prefix+itemId);
                    go.transform.SetParent(body.transform.parent,false);
                    go.transform.localPosition=body.transform.localPosition;go.transform.localRotation=body.transform.localRotation;go.transform.localScale=body.transform.localScale;
                    go.layer=body.gameObject.layer;
                    var smr=go.AddComponent<SkinnedMeshRenderer>();
                    smr.sharedMesh=src.sharedMesh;smr.sharedMaterials=src.sharedMaterials;
                    var missing=new List<string>();
                    smr.bones=src.bones.Select(b=>{if(b&&bones.TryGetValue(b.name,out var t))return t;missing.Add(b?b.name:"null");return body.rootBone;}).ToArray();
                    smr.rootBone=src.rootBone&&bones.TryGetValue(src.rootBone.name,out var rb)?rb:body.rootBone;
                    smr.shadowCastingMode=ShadowCastingMode.On;smr.receiveShadows=true;smr.updateWhenOffscreen=true;
                    smr.localBounds=body.localBounds;
                    // bind-pose agreement with the body (same armature in Blender, so the matrices should match closely)
                    float worst=0;string worstBone="-";
                    for(int i=0;i<src.bones.Length;i++)
                    {
                        if(!src.bones[i]||!bodyBind.TryGetValue(src.bones[i].name,out var bb))continue;
                        var a=src.sharedMesh.bindposes[i];float d=0;
                        for(int k=0;k<16;k++)d=Mathf.Max(d,Mathf.Abs(a[k]-bb[k]));
                        if(d>worst){worst=d;worstBone=src.bones[i].name;}
                    }
                    if(missing.Count>0)throw new InvalidOperationException(file+": bones missing on the player: "+string.Join(",",missing));
                    if(worst>.01f)throw new InvalidOperationException($"{file}: bind poses differ from the body (max {worst:F4} at {worstBone}); re-export it on the current player armature");
                    go.SetActive(false);
                    list.RemoveAll(p=>p.itemId==itemId);
                    list.Add(new PlayerArmourVisuals.Piece{itemId=itemId,slot=slot,model=go});
                    log.Add($"{file}: {itemId} in {slot}, {src.sharedMesh.triangles.Length/3} tris, {smr.bones.Length} bones, bind max diff {worst:F5}");
                }
                finally{Object.DestroyImmediate(inst);}
            }
            // the rigid carrier holder is redundant once the skinned carrier is present
            if(list.Any(p=>p.itemId=="warden_plate_carrier"&&p.model&&p.model.name.StartsWith(Prefix)))
                foreach(var t in motor.visual.GetComponentsInChildren<Transform>(true).Where(t=>t.name==RifleArmourInstall.VestHolder).ToArray()){log.Add("rigid carrier holder removed");Object.DestroyImmediate(t.gameObject);}
            // finger grip on drawn weapons (MPFB rig fingers; none on a rig without them)
            var grip=combat.GetComponent<PlayerHandGrip>();if(!grip)grip=Undo.AddComponent<PlayerHandGrip>(combat.gameObject);
            string[] digits={"index","middle","ring","pinky","thumb"};
            Transform[] Fingers(string side)=>digits.SelectMany(d=>new[]{"01","02","03"}.Select(j=>bones.TryGetValue($"{d}_{j}_{side}",out var t)?t:null)).Where(t=>t).ToArray();
            grip.combat=combat;grip.rightFingers=Fingers("r");grip.leftFingers=Fingers("l");
            PrefabUtility.RecordPrefabInstancePropertyModifications(grip);EditorUtility.SetDirty(grip);
            log.Add($"hand grip: {grip.rightFingers.Length} right / {grip.leftFingers.Length} left finger joints");
            // first-person view models on the MPFB arms: the pistol's rebuilt in place, the rifle's built beside it
            log.Add(SupportGrips(combat,motor,bones));   // before the view models, which copy the held rifle with its grip point
            if(fpArmsAsset)log.Add(ViewModels(combat,motor,body,fpArmsAsset));else log.Add("view models: TS_FPArms.glb not delivered");
            Undo.RecordObject(vis,"tutorial set");vis.combat=combat;vis.pieces=list.ToArray();
            PrefabUtility.RecordPrefabInstancePropertyModifications(vis);EditorUtility.SetDirty(vis);
            // 3 Oct 2026 (player_face_20261003): both view models on the player's arms, solved finger grips, worn gloves/arm guards mirrored
            if(fpArmsAsset)log.Add(PlayerFace20261003.FirstPersonHands(combat,motor,vis));
            return "tutorial set: "+string.Join("; ",log);
        }
            public static float SupportAlong=.30f,SupportBelow=.035f;   // handguard point: metres forward of the grip along the barrel, below its axis
        /// Support-grip point on the held rifle's handguard and the left-arm IK on the colonist. The grip frame keeps the
        /// rifle hold clip's own left-hand orientation relative to the rifle; only the position moves onto the handguard.
        static string SupportGrips(PlayerCombat combat,PlayerMotor motor,Dictionary<string,Transform> bones)
        {
            if(!combat.heldRifle||!combat.rifleMuzzle)return "support grip: no held rifle";
            var hold=AssetDatabase.LoadAssetAtPath<AnimationClip>(HoldFolder+"rifle_hold.anim");
            var pRoot=motor.actor.animationSource.gameObject;
            bool was=combat.heldRifle.activeSelf;combat.heldRifle.SetActive(true);
            if(hold)hold.SampleAnimation(pRoot,hold.length*.3f);
            var rifle=combat.heldRifle.transform;
            foreach(var old in rifle.GetComponentsInChildren<Transform>(true).Where(t=>t.name=="Support grip").ToArray())Object.DestroyImmediate(old.gameObject);
            var barrel=(combat.rifleMuzzle.position-rifle.position).normalized;var up=Vector3.ProjectOnPlane(rifle.up,barrel).normalized;
            var grip=new GameObject("Support grip").transform;grip.SetParent(rifle,true);
            grip.position=rifle.position+barrel*SupportAlong-up*SupportBelow;
            grip.rotation=bones["LeftHand"].rotation;   // the clip's hand orientation relative to the rifle
            combat.heldRifle.SetActive(was);
            if(motor.actor.idle)motor.actor.idle.SampleAnimation(pRoot,0);
            var ik=combat.GetComponent<SupportHandIK>();if(!ik)ik=Undo.AddComponent<SupportHandIK>(combat.gameObject);
            ik.combat=combat;ik.upper=bones["LeftArm"];ik.lower=bones["LeftForeArm"];ik.hand=bones["LeftHand"];ik.rifleGrip=grip;ik.pistolGrip=null;ik.pistolWeight=0;ik.scaleByAim=combat.GetComponent<PlayerWeaponPose>();
            PrefabUtility.RecordPrefabInstancePropertyModifications(ik);EditorUtility.SetDirty(ik);
            return $"support grip on the rifle handguard {SupportAlong} m ahead of the grip; left-arm IK on the colonist";
        }

        const string HoldFolder="Assets/AthenHill/Art/CharacterMotion/Player/";
        /// Rebuilds the pistol view model's rig on the MPFB arms (the old one used the previous colonist's arms, whose rest
        /// pose no longer matches the retargeted hold clip) and builds a matching field-rifle view model.
        static string ViewModels(PlayerCombat combat,PlayerMotor motor,SkinnedMeshRenderer body,GameObject armsAsset)
        {
            var log=new List<string>();
            var pvm=combat.viewModel;if(!pvm)throw new InvalidOperationException("No pistol view model (run WeaponFeelPass first).");
            var mats=body.sharedMaterials.Where(m=>m).GroupBy(m=>m.name).ToDictionary(g=>g.Key,g=>g.First());
            var pRoot=motor.actor.animationSource.gameObject;
            // muzzle flash template: the pistol view model's existing flash, kept aside while its rig is rebuilt
            var flashTemplate=pvm.flash?pvm.flash.gameObject:null;
            if(flashTemplate)flashTemplate.transform.SetParent(pvm.transform,false);
            log.Add(Rig(pvm,combat.heldPistol,combat.muzzlePoint,AssetDatabase.LoadAssetAtPath<AnimationClip>(HoldFolder+"pistol_hold.anim"),false,armsAsset,mats,pRoot,flashTemplate,combat));
            // the pistol keeps its authored two-hand grip mesh (FP hands v2, shaped round this pistol); the arms rig only drives the pose
            log.Add("pistol grip hands: "+FPGripPass.Attach(pvm));
            foreach(var s in pvm.rig.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(x=>!x.transform.IsChildOf(pvm.pistol)))s.enabled=false;
            foreach(var c in pvm.rig.GetComponents<SupportHandIK>())Object.DestroyImmediate(c);
            foreach(var c in pvm.rig.GetComponents<PlayerHandGrip>())Object.DestroyImmediate(c);
            // rifle view model: same settings, own root and rig
            const string rifleName="First-person rifle view model";
            var siblings=pvm.transform.parent?pvm.transform.parent.Cast<Transform>():pvm.gameObject.scene.GetRootGameObjects().Select(g=>g.transform);
            foreach(var old in siblings.Where(t=>t.name==rifleName).ToArray())Object.DestroyImmediate(old.gameObject);
            var rroot=new GameObject(rifleName,typeof(FirstPersonViewModel));rroot.transform.SetParent(pvm.transform.parent,false);rroot.layer=WeaponFeelPass.ViewModelLayer;
            var rvm=rroot.GetComponent<FirstPersonViewModel>();
            rvm.session=pvm.session;rvm.combat=combat;rvm.motor=pvm.motor;rvm.follow=pvm.follow;rvm.viewCamera=pvm.viewCamera;rvm.overlayCamera=pvm.overlayCamera;rvm.rifle=true;
            rvm.hipOffset=new Vector3(.13f,-.19f,.40f);rvm.hipEuler=new Vector3(2,-4,-5);rvm.aimOffset=new Vector3(0,-.118f,.34f);rvm.aimEuler=Vector3.zero;
            rvm.drawSeconds=.35f;rvm.recoilBack=.035f;rvm.recoilPitch=3.5f;
            var visuals=new GameObject("Visuals");visuals.transform.SetParent(rroot.transform,false);rvm.visuals=visuals;
            log.Add(Rig(rvm,combat.heldRifle,combat.rifleMuzzle,AssetDatabase.LoadAssetAtPath<AnimationClip>(HoldFolder+"rifle_hold.anim"),true,armsAsset,mats,pRoot,flashTemplate,combat));
            visuals.SetActive(false);
            combat.rifleViewModel=rvm;PrefabUtility.RecordPrefabInstancePropertyModifications(combat);EditorUtility.SetDirty(combat);
            if(motor.actor.idle)motor.actor.idle.SampleAnimation(pRoot,0);
            return string.Join("; ",log);
        }

        static string Rig(FirstPersonViewModel vm,GameObject held,Transform heldMuzzle,AnimationClip hold,bool rifle,GameObject armsAsset,Dictionary<string,Material> mats,GameObject pRoot,GameObject flashTemplate,PlayerCombat combat)
        {
            if(!held||!hold)throw new InvalidOperationException((rifle?"rifle":"pistol")+": held weapon or hold clip missing");
            var visuals=vm.visuals?vm.visuals.transform:vm.transform;
            foreach(var c in visuals.Cast<Transform>().ToArray())Object.DestroyImmediate(c.gameObject);
            // clips bind "Armature/Hips/...": glTFast may make the armature the instance root, so wrap it under a rig root
            var inst=(GameObject)PrefabUtility.InstantiatePrefab(armsAsset);
            GameObject rig;
            if(inst.transform.Find("Armature")){rig=inst;rig.transform.SetParent(visuals,false);}
            else{rig=new GameObject("Player arms rig");rig.transform.SetParent(visuals,false);inst.name="Armature";inst.transform.SetParent(rig.transform,false);}
            rig.name="Player arms rig";
            rig.transform.localScale=pRoot.transform.lossyScale;   // same size as the colonist, so the copied weapon pose lands in the same hands
            if(!rig.transform.Find("Armature/Hips"))throw new InvalidOperationException("TS_FPArms: no Armature/Hips under the rig root");
            var anim=rig.GetComponent<Animation>();if(!anim)anim=rig.AddComponent<Animation>();anim.playAutomatically=false;anim.cullingType=AnimationCullingType.AlwaysAnimate;
            foreach(var smr in rig.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                smr.sharedMaterials=smr.sharedMaterials.Select(m=>m&&mats.TryGetValue(m.name,out var pm)?pm:m).ToArray();   // the player's own materials, no second texture set
                smr.updateWhenOffscreen=true;smr.shadowCastingMode=ShadowCastingMode.Off;smr.receiveShadows=true;
            }
            Transform B(Transform root,string n)=>root.GetComponentsInChildren<Transform>(true).FirstOrDefault(t=>t.name==n)??throw new InvalidOperationException("no bone "+n);
            float t0=hold.length*.3f;hold.SampleAnimation(rig,t0);hold.SampleAnimation(pRoot,t0);
            var hand=B(rig.transform,"RightHand");var pHand=held.transform.parent;
            var w=Object.Instantiate(held);w.name=rifle?"View model rifle":"View model pistol";w.SetActive(true);
            var relRot=Quaternion.Inverse(pHand.rotation)*held.transform.rotation;var relPos=Quaternion.Inverse(pHand.rotation)*(held.transform.position-pHand.position);
            w.transform.SetParent(hand,false);w.transform.rotation=hand.rotation*relRot;w.transform.position=hand.position+hand.rotation*relPos;
            var ls=held.transform.lossyScale;var hs=hand.lossyScale;w.transform.localScale=new Vector3(ls.x/hs.x,ls.y/hs.y,ls.z/hs.z);
            foreach(var r in w.GetComponentsInChildren<Renderer>(true))r.shadowCastingMode=ShadowCastingMode.Off;
            foreach(var f in w.GetComponentsInChildren<MuzzleFlash>(true))Object.DestroyImmediate(f.gameObject);
            var muzzle=heldMuzzle?w.GetComponentsInChildren<Transform>(true).FirstOrDefault(t=>t.name==heldMuzzle.name):null;
            if(!muzzle&&heldMuzzle){muzzle=new GameObject(heldMuzzle.name).transform;muzzle.SetParent(w.transform,false);muzzle.position=w.transform.TransformPoint(held.transform.InverseTransformPoint(heldMuzzle.position));}
            // placement pivot: the pistol itself; for the rifle a grip-point frame looking down the barrel
            Transform pivot=w.transform;
            if(rifle&&muzzle)
            {
                pivot=new GameObject("View model pivot").transform;pivot.SetParent(w.transform,false);
                var barrel=(muzzle.position-w.transform.position).normalized;
                pivot.rotation=Quaternion.LookRotation(barrel,Vector3.ProjectOnPlane(w.transform.up,barrel));
            }
            GameObject flash=null;
            if(flashTemplate&&muzzle){flash=rifle?Object.Instantiate(flashTemplate):flashTemplate;flash.name="View model muzzle flash";flash.transform.SetParent(muzzle,false);flash.transform.localPosition=Vector3.zero;flash.transform.localRotation=Quaternion.identity;}
            foreach(var t in vm.GetComponentsInChildren<Transform>(true))t.gameObject.layer=WeaponFeelPass.ViewModelLayer;
            // fingers round the grip (the rig has the MPFB finger bones)
            var grip=rig.AddComponent<PlayerHandGrip>();grip.combat=combat;grip.fingerCurl=new Vector3(68,82,55);grip.thumbCurl=new Vector3(18,28,22);
            string[] digits={"index","middle","ring","pinky","thumb"};
            Transform[] Fingers(string side)=>digits.SelectMany(d=>new[]{"01","02","03"}.Select(j=>rig.GetComponentsInChildren<Transform>(true).FirstOrDefault(x=>x.name==$"{d}_{j}_{side}"))).Where(x=>x).ToArray();
            grip.rightFingers=Fingers("r");grip.leftFingers=Fingers("l");
            var support=w.GetComponentsInChildren<Transform>(true).FirstOrDefault(x=>x.name=="Support grip");
            if(support)
            {
                var ik=rig.AddComponent<SupportHandIK>();ik.combat=combat;ik.upper=B(rig.transform,"LeftArm");ik.lower=B(rig.transform,"LeftForeArm");ik.hand=B(rig.transform,"LeftHand");
                if(rifle){ik.rifleGrip=support;ik.pistolWeight=0;}else{ik.pistolGrip=support;ik.rifleWeight=0;}
            }
            vm.rig=rig.transform;vm.animationSource=anim;vm.holdClip=hold;vm.pistol=pivot;vm.muzzle=muzzle;vm.flash=flash?flash.GetComponent<MuzzleFlash>():null;
            PrefabUtility.RecordPrefabInstancePropertyModifications(vm);EditorUtility.SetDirty(vm);
            return $"{(rifle?"rifle":"pistol")} view model: MPFB arms {rig.GetComponentsInChildren<SkinnedMeshRenderer>(true).Sum(x=>x.sharedMesh.triangles.Length/3)} tris, {grip.rightFingers.Length}+{grip.leftFingers.Length} finger joints, muzzle {(muzzle?muzzle.name:"none")}, flash {(flash?"yes":"no")}";
        }

        /// Batch capture (graphics): the player at the rifle review stand, 13:00 light, three player-height views, first in
        /// the suit alone, then wearing every delivered piece. art/tutorial_set_20261002/unity/captures/*.png
        public static void CaptureBatch()
        {
            int code=0;string text;
            try{text=Capture();Debug.Log("TutorialSetInstall capture OK\n"+text);}
            catch(Exception e){Debug.LogException(e);text="FAILED "+e;code=1;}
            EditorApplication.Exit(code);
        }

        static string Capture()
        {
            EditorSceneManager.OpenScene("Assets/AthenHill/Scenes/AthenHill.unity",OpenSceneMode.Single);
            var outDir=Path.GetFullPath(Path.Combine(Application.dataPath,"../../../art/tutorial_set_20261002/unity/captures"));Directory.CreateDirectory(outDir);
            var combat=Object.FindAnyObjectByType<PlayerCombat>(FindObjectsInactive.Include);var motor=combat.GetComponent<PlayerMotor>();
            var vis=combat.GetComponent<PlayerArmourVisuals>();var actor=motor.actor;var body=motor.visual;
            var clock=Object.FindFirstObjectByType<CityTimeOfDay>(FindObjectsInactive.Include);
            if(clock&&clock.profile)
            {
                var f=clock.profile.Evaluate(13f);
                clock.keyLight.transform.rotation=Quaternion.Euler(f.keyEuler);clock.keyLight.color=f.keyColor;clock.keyLight.intensity=f.keyIntensity;
                if(clock.skyFill){clock.skyFill.color=f.fillColor;clock.skyFill.intensity=f.fillIntensity;}
                RenderSettings.ambientMode=AmbientMode.Trilight;RenderSettings.ambientSkyColor=f.ambientSky;RenderSettings.ambientEquatorColor=f.ambientEquator;RenderSettings.ambientGroundColor=f.ambientGround;
            }
            if(combat.muzzleLight)combat.muzzleLight.enabled=false;
            if(combat.heldPistol)combat.heldPistol.SetActive(false);if(combat.heldRifle)combat.heldRifle.SetActive(false);
            var feet=RifleArmourInstall.Stand;
            if(Physics.Raycast(feet+Vector3.up*6,Vector3.down,out var hit,30,~(1<<8),QueryTriggerInteraction.Ignore))feet.y=hit.point.y;
            motor.transform.position=feet+Vector3.up*.015f;body.rotation=Quaternion.LookRotation(Vector3.left,Vector3.up);
            if(actor.idle)actor.idle.SampleAnimation(actor.animationSource.gameObject,0.4f);
            foreach(var r in body.GetComponentsInChildren<SkinnedMeshRenderer>(true))r.forceMatrixRecalculationPerRender=true;
            var template=Object.FindObjectsByType<Camera>(FindObjectsInactive.Include,FindObjectsSortMode.None).FirstOrDefault(c=>c.name=="cam_checkpoint_player");
            var go=new GameObject("ts capture cam");var cam=go.AddComponent<Camera>();if(template)cam.CopyFrom(template);cam.enabled=false;
            var rt=new RenderTexture(1200,1200,24,RenderTextureFormat.ARGB32);var tex=new Texture2D(1200,1200,TextureFormat.RGB24,false);
            var front=("front",feet+new Vector3(-2.6f,1.2f,0.9f),feet+new Vector3(0,0.95f,0),36f);
            var face=("face",feet+new Vector3(-0.85f,1.66f,0.3f),feet+new Vector3(0,1.58f,0),30f);
            var back=("back",feet+new Vector3(2.4f,1.35f,-1.0f),feet+new Vector3(0,1.0f,0),36f);
            var side=("side",feet+new Vector3(-0.55f,1.45f,1.9f),feet+new Vector3(-0.45f,1.3f,0),34f);
            var shoulder=("shoulder",feet+new Vector3(0.75f,1.75f,-0.55f),feet+new Vector3(-1.2f,1.3f,0.1f),40f);
            var log=new List<string>();
            var grip=combat.GetComponent<PlayerHandGrip>();var pose=combat.GetComponent<PlayerWeaponPose>();
            AnimationClip Clip(string n)=>AssetDatabase.LoadAssetAtPath<AnimationClip>("Assets/AthenHill/Art/CharacterMotion/Player/"+n+".anim");
            void Shot(string state,(string name,Vector3 pos,Vector3 look,float fov) v)
            {
                go.transform.position=v.pos;go.transform.LookAt(v.look);cam.fieldOfView=v.fov;
                cam.targetTexture=rt;cam.Render();RenderTexture.active=rt;tex.ReadPixels(new Rect(0,0,1200,1200),0,0);tex.Apply();RenderTexture.active=null;cam.targetTexture=null;
                var file=Path.Combine(outDir,state+"_"+v.name+".png");File.WriteAllBytes(file,tex.EncodeToPNG());log.Add(file);
            }
            void Wear(bool worn){foreach(var p in vis.pieces)if(p.model)p.model.SetActive(worn&&p.itemId!="warden_plate_carrier");}
            Wear(false);Shot("warmup",front);Shot("suit",front);   // the first render compiles shaders (cyan placeholder)
            Wear(true);Shot("armour",front);Shot("armour",face);Shot("armour",back);
            // weapons in hand: the hold clips on top of the idle, the measured grip mount, fingers curled
            var idleRoot=actor.animationSource.gameObject;
            if(combat.heldPistol){actor.idle.SampleAnimation(idleRoot,0.4f);var c=Clip("pistol_hold");if(c)c.SampleAnimation(idleRoot,0);combat.heldPistol.SetActive(true);if(grip)grip.PreviewGrip(1,0);Shot("pistol",side);Shot("pistol",shoulder);combat.heldPistol.SetActive(false);}
            if(combat.heldRifle){actor.idle.SampleAnimation(idleRoot,0.4f);var c=Clip("rifle_hold");if(c)c.SampleAnimation(idleRoot,0);combat.heldRifle.SetActive(true);if(grip)grip.PreviewGrip(1,1);Shot("rifle",side);Shot("rifle",shoulder);combat.heldRifle.SetActive(false);}
            Object.DestroyImmediate(go);
            return string.Join("\n",log);
        }
    }
}
