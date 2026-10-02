using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Rendering.Universal.ShaderGUI;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    // 27 Sep 2026 character-feel pass: pistol presentation. Layered ElevenLabs shot + foley, third-person upper-body
    // aim layer (PlayerWeaponPose), muzzle flash cards, and the first-person arms/pistol view model on its own layer
    // through a URP overlay camera. Idempotent: re-running rebuilds only the objects it owns.
    public static class WeaponFeelPass
    {
        public const int ViewModelLayer=9;
        const string Art="Assets/AthenHill/Art/CharacterMotion/FirstPerson/";
        const string PistolAudio="Assets/AthenHill/Audio/ElevenLabs/Combat/Pistol/";
        const string ViewModelName="First-person view model";

        [MenuItem("Athen Hill/Combat/Install pistol feel (audio, aim pose, first-person view model)")]
        public static string Install()
        {
            if(EditorApplication.isPlaying)throw new InvalidOperationException("Exit Play first.");
            var combat=Object.FindAnyObjectByType<PlayerCombat>();
            var motor=Object.FindAnyObjectByType<PlayerMotor>();
            var follow=Object.FindAnyObjectByType<FollowCamera>();
            if(!combat||!motor||!follow||!combat.heldPistol||!combat.muzzlePoint)throw new InvalidOperationException("Open the city scene with the Berms pistol installed.");
            var log=new List<string>();
            EnsureLayer();
            log.Add(Audio(combat));
            log.Add(HoldClip());
            log.Add(AimPose(combat,motor,follow));
            log.Add(MountPistolForAim(combat,motor));
            var flashMat=FlashMaterial();var flashMesh=FlashMesh();
            combat.thirdPersonFlash=Flash(combat.muzzlePoint,"Third-person muzzle flash",flashMat,flashMesh,0,null);
            log.Add(ViewModel(combat,motor,follow,flashMat,flashMesh));
            // 27 Sep pm: the dedicated two-hand grip mesh replaces the colonist-cut arms (old arms kept, renderers off)
            log.Add(FPGripPass.Attach(combat.viewModel));
            EditorUtility.SetDirty(combat);
            var scene=combat.gameObject.scene;EditorSceneManager.MarkSceneDirty(scene);EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets();
            return string.Join("\n",log);
        }

        static void EnsureLayer()
        {
            var tags=new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/TagManager.asset")[0]);
            var layer=tags.FindProperty("layers").GetArrayElementAtIndex(ViewModelLayer);
            if(layer.stringValue=="ViewModel")return;
            if(!string.IsNullOrEmpty(layer.stringValue))throw new InvalidOperationException("Layer 9 is already "+layer.stringValue);
            layer.stringValue="ViewModel";tags.ApplyModifiedProperties();
        }

        static AudioClip[] Clips(string layer)=>Directory.GetFiles(PistolAudio,"pistol-"+layer+"-*.wav").OrderBy(f=>f)
            .Select(f=>AssetDatabase.LoadAssetAtPath<AudioClip>(f.Replace('\\','/'))).Where(c=>c).ToArray();

        static string Audio(PlayerCombat combat)
        {
            foreach(var path in Directory.GetFiles(PistolAudio,"*.wav"))
            {
                var ai=(AudioImporter)AssetImporter.GetAtPath(path.Replace('\\','/'));var d=ai.defaultSampleSettings;
                if(d.loadType!=AudioClipLoadType.DecompressOnLoad||d.compressionFormat!=AudioCompressionFormat.PCM)
                {d.loadType=AudioClipLoadType.DecompressOnLoad;d.compressionFormat=AudioCompressionFormat.PCM;ai.defaultSampleSettings=d;ai.SaveAndReimport();}
            }
            Undo.RecordObject(combat,"Pistol audio");
            combat.shotMech=Clips("mech");combat.shotBody=Clips("body");combat.shotTail=Clips("tail");
            combat.emptyClips=Clips("empty");combat.drawClips=Clips("draw");combat.holsterClips=Clips("holster");
            if(combat.shotBody.Length==0)throw new InvalidOperationException("Pistol audio missing; run unity/tools/generate_pistol_audio.py");
            // From generate_pistol_audio.py: the worst-case aligned sum of the loudest variants peaks at -1.5 dBFS with these.
            combat.mechGain=.55f;combat.bodyGain=.69f;combat.tailGain=.37f;combat.closeMechScale=1.15f;combat.closeTailScale=.7f;
            var src=combat.audioSource;
            var tailT=src.transform.Find("Pistol tail");var tail=tailT?tailT.GetComponent<AudioSource>():null;
            if(!tail){var go=new GameObject("Pistol tail");Undo.RegisterCreatedObjectUndo(go,"tail");go.transform.SetParent(src.transform,false);tail=go.AddComponent<AudioSource>();}
            tail.playOnAwake=false;tail.loop=false;tail.outputAudioMixerGroup=src.outputAudioMixerGroup;tail.spatialBlend=0;tail.volume=src.volume;tail.priority=src.priority+10;
            combat.tailSource=tail;
            return "audio mech "+combat.shotMech.Length+" body "+combat.shotBody.Length+" tail "+combat.shotTail.Length+" empty "+combat.emptyClips.Length+" draw "+combat.drawClips.Length+" holster "+combat.holsterClips.Length+"; source "+src.name+" vol "+src.volume+" spatial "+src.spatialBlend+" group "+(src.outputAudioMixerGroup?src.outputAudioMixerGroup.name:"(set at runtime)");
        }

        static Transform Bone(Component root,string name)=>root.GetComponentsInChildren<Transform>(true).FirstOrDefault(t=>t.name==name)??throw new InvalidOperationException("No bone "+name+" under "+root.name);

        static string AimPose(PlayerCombat combat,PlayerMotor motor,FollowCamera follow)
        {
            var pose=combat.GetComponent<PlayerWeaponPose>();if(!pose)pose=Undo.AddComponent<PlayerWeaponPose>(combat.gameObject);
            Undo.RecordObject(pose,"Aim pose");
            pose.combat=combat;pose.actor=motor.actor;pose.view=follow.GetComponent<Camera>();
            pose.aimClip=AssetDatabase.LoadAssetAtPath<AnimationClip>(HoldPath);
            if(!pose.aimClip)throw new InvalidOperationException("Retarget the player clips first.");
            // Meshy naming runs bottom-up: Hips > Spine02 > Spine01 > Spine > neck.
            pose.mixRoot=Bone(motor.actor,"Spine02");
            pose.spine=new[]{Bone(motor.actor,"Spine02"),Bone(motor.actor,"Spine01"),Bone(motor.actor,"Spine")};
            pose.rightHand=Bone(motor.actor,"RightHand");
            EditorUtility.SetDirty(pose);
            return "aim pose "+pose.aimClip.name+" mixed from "+pose.mixRoot.name;
        }

        // The Berms pass mounted the pistol for the hanging idle hand (barrel level while the hand points down), so in any
        // aim pose the barrel tilted up. Mount it for the two-handed hold instead: grip in the palm, barrel along the
        // character's forward. At rest the pistol then hangs muzzle-down with the hand, as a held pistol does.
        static string MountPistolForAim(PlayerCombat combat,PlayerMotor motor)
        {
            var hold=AssetDatabase.LoadAssetAtPath<AnimationClip>(HoldPath);
            var root=motor.actor.animationSource.gameObject;var hand=combat.heldPistol.transform.parent;
            hold.SampleAnimation(root,0);
            var body=motor.visual;var pistol=combat.heldPistol.transform;var muzzle=combat.muzzlePoint;
            Undo.RecordObject(pistol,"Mount pistol");
            // grip point: along the hand bone (Meshy bones point down their local +Y) into the palm
            var along=(hand.rotation*Vector3.up).normalized;
            var grip=hand.position+along*.075f;
            pistol.rotation=Quaternion.LookRotation(body.forward,body.up);
            // the holder origin is the grip (the Berms pass offset the mesh so the grip sits at the holder origin)
            pistol.position=grip-body.up*.01f;
            if(motor.actor.idle)motor.actor.idle.SampleAnimation(root,0);
            EditorUtility.SetDirty(pistol);
            return "pistol mounted for aim: local "+pistol.localPosition.ToString("F3")+" / "+pistol.localEulerAngles.ToString("F0")+", muzzle "+(muzzle?muzzle.localPosition.ToString("F3"):"-");
        }

        const string HoldPath="Assets/AthenHill/Art/CharacterMotion/Player/pistol_hold.anim";
        // Two-handed pistol hold: the settled end frame of the retargeted Meshy "Gun Hold Left Turn" (action 95),
        // frozen into a static clip. Auditioned against the other library holds in first person (27 Sep): only this one
        // keeps both hands on the grip; "Walk Forward While Shooting" leaves the support hand floating.
        static string HoldClip()=>HoldClip("Assets/AthenHill/Art/CharacterMotion/Player/lib_aim_95.anim",.97f,HoldPath,"pistol_hold");
        /// A static upper-body hold frozen from a retargeted library clip at a fraction of its length, squared over the
        /// idle legs (also used for the rifle holds, 2 Oct 2026).
        public static string HoldClip(string srcPath,float fraction,string outPath,string clipName)
        {
            var src=AssetDatabase.LoadAssetAtPath<AnimationClip>(srcPath);
            if(!src)throw new InvalidOperationException("Missing retargeted clip "+srcPath);
            float t=src.length*fraction;
            var motor=Object.FindAnyObjectByType<PlayerMotor>();var root=motor.actor.animationSource.gameObject;var body=motor.visual;
            Transform B(string n)=>Bone(motor.actor,n);
            // The clip's turn lives in the hips. In game the hips and legs come from idle/walk/run, so take them from the
            // idle and keep only the upper body (Spine02 down) from the hold.
            if(motor.actor.idle)motor.actor.idle.SampleAnimation(root,0);
            var upper=B("Spine02");
            var lower=motor.actor.GetComponentsInChildren<Transform>(true).Where(x=>!x.IsChildOf(upper)).ToDictionary(x=>x,x=>(x.localPosition,x.localRotation));
            src.SampleAnimation(root,t);
            foreach(var kv in lower){kv.Key.localPosition=kv.Value.Item1;kv.Key.localRotation=kv.Value.Item2;}
            // "Gun Hold Left Turn" ends with the torso turned and hunched. Yaw the lower spine so the chest (perpendicular
            // to the shoulder line) faces the character's forward, then take out most of the forward lean, so the
            // upper-body layer sits square over the walk/run legs. The hands stay where the pose holds them.
            var spine=B("Spine02");
            var right=B("RightArm").position-B("LeftArm").position;
            var chest=Vector3.Cross(Vector3.ProjectOnPlane(right,body.up),body.up).normalized;
            float yaw=Vector3.SignedAngle(chest,body.forward,body.up);
            spine.rotation=Quaternion.AngleAxis(yaw,body.up)*spine.rotation;
            var chestUp=(B("neck").position-spine.position).normalized;
            float lean=Vector3.SignedAngle(Vector3.ProjectOnPlane(chestUp,body.right),body.up,body.right);
            spine.rotation=Quaternion.AngleAxis(lean*.8f,body.right)*spine.rotation;
            var clip=new AnimationClip{name=clipName,legacy=true,frameRate=30,wrapMode=WrapMode.Loop};
            var animRoot=motor.actor.animationSource.transform;
            foreach(var b in AnimationUtility.GetCurveBindings(src))
            {
                var t0=animRoot.Find(b.path);if(!t0)continue;
                float v;
                if(b.propertyName.Contains("Rotation")){var q=t0.localRotation;v=q["xyzw".IndexOf(b.propertyName[b.propertyName.Length-1])];}
                else{var pp=t0.localPosition;v=pp["xyz".IndexOf(b.propertyName[b.propertyName.Length-1])];}
                clip.SetCurve(b.path,typeof(Transform),b.propertyName.Replace("m_LocalRotation","localRotation").Replace("m_LocalPosition","localPosition"),AnimationCurve.Constant(0,1,v));
            }
            clip.EnsureQuaternionContinuity();
            if(motor.actor.idle)motor.actor.idle.SampleAnimation(root,0);
            var existing=AssetDatabase.LoadAssetAtPath<AnimationClip>(outPath);
            if(existing){EditorUtility.CopySerialized(clip,existing);Object.DestroyImmediate(clip);EditorUtility.SetDirty(existing);}
            else AssetDatabase.CreateAsset(clip,outPath);
            AssetDatabase.SaveAssets();
            return clipName+" from "+System.IO.Path.GetFileName(srcPath)+" at "+t.ToString("F2")+" s, lower spine yawed "+yaw.ToString("F0")+" deg, lean corrected "+(lean*.8f).ToString("F0")+" deg";
        }

        static Material FlashMaterial()
        {
            string texPath=Art+"MuzzleFlashStar.png";
            if(!File.Exists(texPath))
            {
                // Procedural star: hot core, six soft spikes, falloff. White; colour comes from the material.
                const int n=128;var tex=new Texture2D(n,n,TextureFormat.RGBA32,false);var rng=new System.Random(27);
                var spikes=Enumerable.Range(0,6).Select(i=>(a:i*Mathf.PI/3+(float)rng.NextDouble()*.3f,l:.7f+(float)rng.NextDouble()*.3f)).ToArray();
                for(int y=0;y<n;y++)for(int x=0;x<n;x++)
                {
                    float u=(x+.5f)/n*2-1,v=(y+.5f)/n*2-1,r=Mathf.Sqrt(u*u+v*v),ang=Mathf.Atan2(v,u);
                    float core=Mathf.Exp(-r*r*18),glow=Mathf.Exp(-r*r*4)*.35f,spike=0;
                    foreach(var s in spikes){float d=Mathf.Abs(Mathf.DeltaAngle(ang*Mathf.Rad2Deg,s.a*Mathf.Rad2Deg))*Mathf.Deg2Rad;spike=Mathf.Max(spike,Mathf.Exp(-d*d*120)*Mathf.Clamp01(1-r/s.l));}
                    float a=Mathf.Clamp01(core+glow+spike*.8f)*Mathf.Clamp01((1-r)*3);
                    tex.SetPixel(x,y,new Color(1,1,1,a));
                }
                tex.Apply();File.WriteAllBytes(texPath,tex.EncodeToPNG());Object.DestroyImmediate(tex);
                AssetDatabase.ImportAsset(texPath);
                var ti=(TextureImporter)AssetImporter.GetAtPath(texPath);ti.alphaIsTransparency=true;ti.wrapMode=TextureWrapMode.Clamp;ti.SaveAndReimport();
            }
            string path=Art+"MuzzleFlash.mat";
            var mat=AssetDatabase.LoadAssetAtPath<Material>(path);
            var shader=Shader.Find("Universal Render Pipeline/Particles/Unlit");
            if(!mat){mat=new Material(shader){name="MuzzleFlash"};AssetDatabase.CreateAsset(mat,path);}
            mat.shader=shader;mat.SetTexture("_BaseMap",AssetDatabase.LoadAssetAtPath<Texture2D>(texPath));
            // Nano-charge discharge: white-hot core into pale cyan, HDR so bloom catches it.
            mat.SetColor("_BaseColor",new Color(1.6f,2.1f,2.4f,1));
            mat.SetFloat("_Surface",1);mat.SetFloat("_Blend",2);mat.SetFloat("_Cull",0);
            BaseShaderGUI.SetMaterialKeywords(mat,null,ParticleGUI.SetMaterialKeywords);
            EditorUtility.SetDirty(mat);return mat;
        }

        static Mesh FlashMesh()
        {
            string path=Art+"MuzzleFlashCard.asset";
            var mesh=AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if(mesh)return mesh;
            // One card facing down the barrel (the star seen from behind) and two crossed cards along it (the streak
            // seen from the side). Local +Z is the barrel direction; unit size, scaled per shot.
            var v=new List<Vector3>();var uv=new List<Vector2>();var tri=new List<int>();
            void Quad(Vector3 a,Vector3 b,Vector3 c,Vector3 d){int i=v.Count;v.AddRange(new[]{a,b,c,d});uv.AddRange(new[]{new Vector2(0,0),new Vector2(1,0),new Vector2(1,1),new Vector2(0,1)});tri.AddRange(new[]{i,i+1,i+2,i,i+2,i+3});}
            Quad(new Vector3(-.5f,-.5f,.05f),new Vector3(.5f,-.5f,.05f),new Vector3(.5f,.5f,.05f),new Vector3(-.5f,.5f,.05f));
            Quad(new Vector3(0,-.35f,-.1f),new Vector3(0,-.35f,1),new Vector3(0,.35f,1),new Vector3(0,.35f,-.1f));
            Quad(new Vector3(-.35f,0,-.1f),new Vector3(-.35f,0,1),new Vector3(.35f,0,1),new Vector3(.35f,0,-.1f));
            mesh=new Mesh{name="MuzzleFlashCard"};mesh.SetVertices(v);mesh.SetUVs(0,uv);mesh.SetTriangles(tri,0);mesh.RecalculateBounds();
            AssetDatabase.CreateAsset(mesh,path);return mesh;
        }

        static MuzzleFlash Flash(Transform muzzle,string name,Material mat,Mesh mesh,int layer,Light light)
        {
            var existing=muzzle.Find(name);if(existing)Object.DestroyImmediate(existing.gameObject);
            var go=new GameObject(name,typeof(MuzzleFlash));go.layer=layer;go.transform.SetParent(muzzle,false);
            var card=new GameObject("Card",typeof(MeshFilter),typeof(MeshRenderer));card.layer=layer;card.transform.SetParent(go.transform,false);
            card.GetComponent<MeshFilter>().sharedMesh=mesh;var r=card.GetComponent<MeshRenderer>();r.sharedMaterial=mat;r.shadowCastingMode=ShadowCastingMode.Off;r.receiveShadows=false;r.enabled=false;
            var f=go.GetComponent<MuzzleFlash>();f.card=r;f.flashLight=light;f.seconds=.045f;f.sizeRange=new Vector2(.09f,.13f);f.stretch=1.8f;
            return f;
        }

        static string ViewModel(PlayerCombat combat,PlayerMotor motor,FollowCamera follow,Material flashMat,Mesh flashMesh)
        {
            var cam=follow.GetComponent<Camera>();
            var old=GameObject.Find(ViewModelName);if(old)Object.DestroyImmediate(old);
            var root=new GameObject(ViewModelName,typeof(FirstPersonViewModel));
            root.transform.SetParent(combat.transform.parent,false);
            var vm=root.GetComponent<FirstPersonViewModel>();
            var visuals=new GameObject("Visuals").transform;visuals.SetParent(root.transform,false);
            var armsAsset=AssetDatabase.LoadAssetAtPath<GameObject>(Art+"PlayerFPArms.glb");
            if(!armsAsset)throw new InvalidOperationException("Import "+Art+"PlayerFPArms.glb first.");
            // glTFast makes the armature the instance root; the player clips bind "Armature/Hips/...", so the arms sit
            // under a rig root that carries the Animation, with the instance named "Armature".
            var rigRoot=new GameObject("Player forearms");rigRoot.transform.SetParent(visuals,false);
            var arms=(GameObject)PrefabUtility.InstantiatePrefab(armsAsset);arms.name="Armature";arms.transform.SetParent(rigRoot.transform,false);
            var anim=rigRoot.AddComponent<Animation>();anim.playAutomatically=false;anim.cullingType=AnimationCullingType.AlwaysAnimate;
            var hold=AssetDatabase.LoadAssetAtPath<AnimationClip>(HoldPath);
            // The arms keep the player's own materials (same UVs), so no second copy of the colonist textures ships.
            var playerSkin=motor.actor.GetComponentsInChildren<SkinnedMeshRenderer>(true).OrderByDescending(s=>s.sharedMesh?s.sharedMesh.vertexCount:0).First();
            foreach(var s in arms.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {s.sharedMaterials=playerSkin.sharedMaterials;s.updateWhenOffscreen=true;s.shadowCastingMode=ShadowCastingMode.Off;s.receiveShadows=true;}
            // Check the clip binds: its paths are relative to the player's colonist root.
            hold.SampleAnimation(rigRoot,hold.length*.3f);
            if(Bone(arms.transform,"RightForeArm").localRotation==Quaternion.identity)throw new InvalidOperationException("Hold clip did not bind to the arms rig.");
            var hand=Bone(arms.transform,"RightHand");
            var pHand=combat.heldPistol.transform.parent;
            // pose the player hand the same way, then copy the pistol's pose relative to the hand in world units
            var pRoot=motor.actor.animationSource.gameObject;hold.SampleAnimation(pRoot,hold.length*.3f);
            var pistol=Object.Instantiate(combat.heldPistol);pistol.name="View model pistol";pistol.SetActive(true);
            var relRot=Quaternion.Inverse(pHand.rotation)*combat.heldPistol.transform.rotation;
            var relPos=Quaternion.Inverse(pHand.rotation)*(combat.heldPistol.transform.position-pHand.position);
            pistol.transform.SetParent(hand,false);
            pistol.transform.rotation=hand.rotation*relRot;pistol.transform.position=hand.position+hand.rotation*relPos;
            // In first person the cupped support hand would cover the slide; seat the view-model pistol 5.5 cm higher in the
            // grip (a thumbs-forward hold) so the sights and charge light read above the hands (auditioned 27 Sep).
            pistol.transform.position+=pistol.transform.up*.055f+pistol.transform.forward*.015f;
            var ls=combat.heldPistol.transform.lossyScale;var hs=hand.lossyScale;pistol.transform.localScale=new Vector3(ls.x/hs.x,ls.y/hs.y,ls.z/hs.z);
            if(motor.actor.idle)motor.actor.idle.SampleAnimation(pRoot,0);
            foreach(var r in pistol.GetComponentsInChildren<Renderer>(true)){r.shadowCastingMode=ShadowCastingMode.Off;}
            foreach(var old2 in pistol.GetComponentsInChildren<MuzzleFlash>(true))Object.DestroyImmediate(old2.gameObject);
            var muzzle=pistol.transform.Find("Muzzle");
            foreach(var t in root.GetComponentsInChildren<Transform>(true))t.gameObject.layer=ViewModelLayer;
            var flash=Flash(muzzle,"View model muzzle flash",flashMat,flashMesh,ViewModelLayer,null);
            // overlay camera stacked on the follow camera
            var overlayT=cam.transform.Find("View model camera");var overlayGo=overlayT?overlayT.gameObject:null;
            if(!overlayGo){overlayGo=new GameObject("View model camera",typeof(Camera));overlayGo.transform.SetParent(cam.transform,false);}
            var overlay=overlayGo.GetComponent<Camera>();
            overlay.clearFlags=CameraClearFlags.Depth;overlay.cullingMask=1<<ViewModelLayer;overlay.nearClipPlane=.01f;overlay.farClipPlane=4;overlay.fieldOfView=cam.fieldOfView;overlay.allowHDR=cam.allowHDR;
            var od=overlay.GetUniversalAdditionalCameraData();od.renderType=CameraRenderType.Overlay;od.renderShadows=false;od.renderPostProcessing=false;od.requiresDepthTexture=false;
            var md=cam.GetUniversalAdditionalCameraData();md.cameraStack.RemoveAll(c=>!c||c==overlay);md.cameraStack.Add(overlay);
            cam.cullingMask&=~(1<<ViewModelLayer);
            EditorUtility.SetDirty(cam);EditorUtility.SetDirty(md);EditorUtility.SetDirty(overlay);
            vm.session=combat.session;vm.combat=combat;vm.motor=motor;vm.follow=follow;vm.viewCamera=cam;vm.overlayCamera=overlay;
            vm.rig=rigRoot.transform;
            vm.hipOffset=new Vector3(.13f,-.16f,.46f);vm.hipEuler=new Vector3(3,-5,-8);vm.aimOffset=new Vector3(0,-.085f,.42f);vm.aimEuler=Vector3.zero;vm.animationSource=anim;vm.holdClip=hold;vm.pistol=pistol.transform;vm.muzzle=muzzle;vm.flash=flash;vm.visuals=visuals.gameObject;
            visuals.gameObject.SetActive(false);
            combat.viewModel=vm;
            return "view model: arms "+arms.GetComponentsInChildren<SkinnedMeshRenderer>(true).Sum(s=>s.sharedMesh.triangles.Length/3)+" tris, pistol at "+muzzle.name+", overlay stacked on "+cam.name;
        }
    }
}
