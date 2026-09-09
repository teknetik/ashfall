using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    // Original keyframe animation authoring for the supplied Meshy skeletons.
    // This never alters source meshes, skin weights, bind poses, locomotion clips or gameplay roots.
    public static class CharacterMotionPass
    {
        const string Folder="Assets/AthenHill/Art/CharacterMotion";
        const string Evidence="../evidence/quality/20260908/movement";
        const string PlayerPrefab="Assets/AthenHill/Prefabs/MeshyPlayer.prefab";
        const string GuardPrefab="Assets/AthenHill/Prefabs/WardGuard.prefab";
        const string ChatSource="Assets/AthenHill/Art/CharacterMotion/Source/GuardChatSource.glb";
        const string IdleSource="Assets/AthenHill/Art/CharacterMotion/Source/GuardIdleSource.glb";
        static readonly string[] clipNames={"idle","talk","jump_takeoff","jump_airborne","jump_fall","jump_landing","jump_landing_moving"};
        static readonly float[] durations={4.8f,6.4f,.12f,.22f,.18f,.24f,.24f};

        sealed class Rig
        {
            public ActorAnimation actor;
            public Transform root,hips;
            public Transform[] bones;
            public Dictionary<string,Transform> named;
            public AnimationClip rest,run;
            public Vector3 leftFoot,rightFoot;
            public Quaternion leftRotation,rightRotation;
            public Vector3 leftKnee,rightKnee;
            public void Reset(bool running=false,float time=0)
            {
                (running?run:rest).SampleAnimation(actor.animationSource.gameObject,running?time:rest.length);
                leftFoot=named["LeftFoot"].position;rightFoot=named["RightFoot"].position;
                leftRotation=named["LeftFoot"].rotation;rightRotation=named["RightFoot"].rotation;
                leftKnee=named["LeftLeg"].position;rightKnee=named["RightLeg"].position;
            }
            public void Rotate(string name,Vector3 actorAxis,float degrees)
            {
                Transform bone;
                if(named.TryGetValue(name,out bone))bone.rotation=Quaternion.AngleAxis(degrees,root.TransformDirection(actorAxis))*bone.rotation;
            }
            public void OffsetHips(Vector3 metres){hips.position+=root.TransformDirection(metres);}
            public void PlantFeet()
            {
                SolveLeg("Left",leftFoot,leftRotation,leftKnee);
                SolveLeg("Right",rightFoot,rightRotation,rightKnee);
            }
            void SolveLeg(string side,Vector3 target,Quaternion footRotation,Vector3 oldKnee)
            {
                var upper=named[side+"UpLeg"];var lower=named[side+"Leg"];var foot=named[side+"Foot"];
                float a=Vector3.Distance(upper.position,lower.position),b=Vector3.Distance(lower.position,foot.position);
                var delta=target-upper.position;
                float distance=Mathf.Clamp(delta.magnitude,Mathf.Abs(a-b)+.0001f,a+b-.0001f);
                var direction=delta.normalized;
                // Knees point forward. Preserve the original sideways knee splay of each supplied rig.
                var bend=Vector3.ProjectOnPlane(root.forward + root.right * Vector3.Dot(oldKnee-upper.position,root.right)*.7f,direction).normalized;
                float along=(a*a+distance*distance-b*b)/(2*distance);
                var knee=upper.position+direction*along+bend*Mathf.Sqrt(Mathf.Max(0,a*a-along*along));
                upper.rotation=Quaternion.FromToRotation(lower.position-upper.position,knee-upper.position)*upper.rotation;
                lower.rotation=Quaternion.FromToRotation(foot.position-lower.position,target-lower.position)*lower.rotation;
                foot.rotation=footRotation;
            }
        }

        [MenuItem("Athen Hill/Characters/Author and install grounded character motion")]
        public static void Install()
        {
            if(EditorApplication.isPlaying)throw new InvalidOperationException("Exit Play before authoring character motion.");
            var player=Object.FindAnyObjectByType<PlayerMotor>();
            var npcs=Object.FindObjectsByType<NpcAgent>().OrderBy(x=>x.name).ToArray();
            if(!player || npcs.Length!=4)throw new InvalidOperationException("Open the existing city with its player and four talking NPCs.");
            var before=CaptureIdentity(player,npcs);
            Directory.CreateDirectory(Folder);Directory.CreateDirectory(Evidence);
            ImportSourceClip(ChatSource,"talk",5);
            ImportSourceClip(IdleSource,"idle",3.9f);
            var reports=new List<object>();
            AuthorPrefab(PlayerPrefab,"Player","Assets/AthenHill/Art/Imported/Meshy/colonist.glb",true,reports);
            AuthorPrefab(GuardPrefab,"Guard","Assets/AthenHill/Art/Imported/Meshy/ward-guard.glb",false,reports);
            Configure(player.actor,"Player",true,0);
            for(int i=0;i<npcs.Length;i++)Configure(npcs[i].actor,"Guard",false,(i*.271f+.12f)%1);
            var after=CaptureIdentity(player,npcs);
            if(before!=after)throw new InvalidOperationException("Character identity or controller tuning changed unexpectedly.");
            AssetDatabase.SaveAssets();
            EditorSceneManager.MarkSceneDirty(player.gameObject.scene);
            EditorSceneManager.SaveScene(player.gameObject.scene);
            File.WriteAllText(Evidence+"/animation-authoring.json",JsonConvert.SerializeObject(new{
                method="Original Unity animation keyframes, baked at 30 Hz from supplied relaxed standing poses; world-space anatomical rotation and two-bone planted-foot constraints. No source geometry, bind pose, walk/run or controller changes.",
                clips=reports,identityPreserved=true,identity=JsonConvert.DeserializeObject(before),
                guardConversation="Meshy Stand_and_Chat action 56, task 01a082a4-2bc8-7549-8e49-5a8fdd1fc1f4, 156 frames; Idle action 0, task 01a082ab-7fe4-7301-b5c9-4cff610300dc, 121 frames. Constant grounding/anchor correction. Authored idle/talk retained as candidate recovery.",
                limitations=new[]{"Supplied 24-bone rigs have no fingers or facial blendshapes. Talking is restrained body/head/arm gesture, with no lip sync.","Source walk/run clips and their original stride speeds are preserved; captured gameplay must judge foot sliding and transition quality.","These are authored motion candidates, not independently accepted AAA animation."}
            },Formatting.Indented));
            Debug.Log("Authored and installed grounded player motion and living guard idle/talk. Meshes, materials, transforms, colliders and locomotion retained.");
        }

        static string CaptureIdentity(PlayerMotor player,NpcAgent[] npcs)
        {
            return JsonConvert.SerializeObject(new{
                player=player.visual.GetEntityId().ToString(),player.walkSpeed,player.runSpeed,player.gravity,player.jumpHeight,player.groundSnap,player.turnSpeed,
                controller=new{player.GetComponent<CharacterController>().radius,player.GetComponent<CharacterController>().height,player.GetComponent<CharacterController>().stepOffset,player.GetComponent<CharacterController>().slopeLimit},
                actors=(new[]{player.actor}).Concat(npcs.Select(n=>n.actor)).Select(a=>new{
                    id=a.GetEntityId().ToString(),position=a.transform.position.ToString("R"),rotation=a.transform.rotation.ToString("R"),scale=a.transform.localScale.ToString("R"),
                    meshes=a.GetComponentsInChildren<SkinnedMeshRenderer>().Select(s=>new{mesh=s.sharedMesh.GetEntityId().ToString(),materials=s.sharedMaterials.Select(m=>m.GetEntityId().ToString()).ToArray()}).ToArray(),
                    walk=a.walk.GetEntityId().ToString(),run=a.run.GetEntityId().ToString(),a.walkStrideSpeed,a.runStrideSpeed
                }).ToArray(),
                walkers=Object.FindObjectsByType<AmbientWalker>().OrderBy(w=>w.name).Select(w=>new{w.name,w.speed,w.phase,actor=w.actor.GetEntityId().ToString(),routes=w.waypoints.Select(t=>t.position.ToString("R")).ToArray()}).ToArray()
            });
        }

        static void AuthorPrefab(string prefabPath,string family,string sourcePath,bool jumping,List<object> reports)
        {
            var instance=PrefabUtility.LoadPrefabContents(prefabPath);
            try
            {
                var actor=instance.GetComponent<ActorAnimation>();
                var bones=actor.GetComponentsInChildren<SkinnedMeshRenderer>().SelectMany(s=>s.bones).Distinct().OrderBy(t=>Depth(t)).ToArray();
                var rig=new Rig{actor=actor,root=instance.transform,bones=bones,named=bones.ToDictionary(t=>t.name,t=>t),
                    rest=AssetDatabase.LoadAllAssetsAtPath(sourcePath).OfType<AnimationClip>().First(c=>c.name=="idle"),
                    run=AssetDatabase.LoadAllAssetsAtPath(sourcePath).OfType<AnimationClip>().First(c=>c.name=="run")};
                rig.hips=rig.named["Hips"];
                for(int i=0;i<(jumping?7:2);i++)reports.Add(Bake(rig,family,clipNames[i],durations[i]));
                Configure(actor,family,jumping,0);
                PrefabUtility.SaveAsPrefabAsset(instance,prefabPath);
            }
            finally{PrefabUtility.UnloadPrefabContents(instance);}
        }

        static int Depth(Transform t){int d=0;while(t.parent){d++;t=t.parent;}return d;}

        static void ImportSourceClip(string sourcePath,string name,float minimumDuration)
        {
            if(!File.Exists(sourcePath))throw new FileNotFoundException("Prepare the retained Meshy animation source first.",sourcePath);
            AssetDatabase.ImportAsset(sourcePath,ImportAssetOptions.ForceSynchronousImport);
            var importer=AssetImporter.GetAtPath(sourcePath);
            var settings=new SerializedObject(importer);
            var method=settings.FindProperty("importSettings.animationMethod");
            if(method==null)throw new InvalidOperationException("Expected glTFast animation import settings.");
            int legacy=Array.IndexOf(method.enumNames,"Legacy");
            if(method.enumValueIndex!=legacy)
            {
                method.enumValueIndex=legacy;settings.ApplyModifiedPropertiesWithoutUndo();importer.SaveAndReimport();
            }
            var source=AssetDatabase.LoadAllAssetsAtPath(sourcePath).OfType<AnimationClip>().FirstOrDefault(c=>c.name==name&&c.legacy);
            if(!source||source.length<minimumDuration)throw new InvalidOperationException("Expected a complete animated guard "+name+" clip.");
            var clip=Object.Instantiate(source);clip.name=name;clip.legacy=true;clip.wrapMode=WrapMode.Loop;
            string path=Folder+"/Guard/"+name+"_meshy.anim";Directory.CreateDirectory(Folder+"/Guard");
            var existing=AssetDatabase.LoadAssetAtPath<AnimationClip>(path);
            if(existing){EditorUtility.CopySerialized(clip,existing);Object.DestroyImmediate(clip);EditorUtility.SetDirty(existing);}
            else AssetDatabase.CreateAsset(clip,path);
        }

        static object Bake(Rig rig,string family,string name,float duration)
        {
            var clip=new AnimationClip{name=name,legacy=true,frameRate=30,wrapMode=name=="idle"||name=="talk"?WrapMode.Loop:WrapMode.ClampForever};
            int count=Mathf.CeilToInt(duration*30)+1;
            var rotations=rig.bones.Select(_=>new List<Quaternion>()).ToArray();
            var positions=rig.bones.Select(_=>new List<Vector3>()).ToArray();
            var scales=rig.bones.Select(_=>new List<Vector3>()).ToArray();
            float maximumFootDrift=0,maximumBoneMotion=0;
            for(int frame=0;frame<count;frame++)
            {
                float time=frame*duration/(count-1);
                rig.Reset(name=="jump_landing_moving",time);
                Pose(rig,name,time,duration);
                if(name=="idle"||name=="talk"||name=="jump_landing"||name=="jump_takeoff")
                    maximumFootDrift=Mathf.Max(maximumFootDrift,Vector3.Distance(rig.named["LeftFoot"].position,rig.leftFoot),Vector3.Distance(rig.named["RightFoot"].position,rig.rightFoot));
                for(int b=0;b<rig.bones.Length;b++)
                {
                    var q=rig.bones[b].localRotation;
                    if(frame>0 && Quaternion.Dot(rotations[b][frame-1],q)<0)q=new Quaternion(-q.x,-q.y,-q.z,-q.w);
                    rotations[b].Add(q);positions[b].Add(rig.bones[b].localPosition);scales[b].Add(rig.bones[b].localScale);
                    if(frame>0)maximumBoneMotion=Mathf.Max(maximumBoneMotion,Quaternion.Angle(rotations[b][0],q));
                }
            }
            for(int b=0;b<rig.bones.Length;b++)
            {
                string path=AnimationUtility.CalculateTransformPath(rig.bones[b],rig.actor.animationSource.transform);
                for(int c=0;c<4;c++)Curve(clip,path,"localRotation."+"xyzw"[c],rotations[b].Select(v=>v[c]).ToArray(),duration);
                for(int c=0;c<3;c++)
                {
                    Curve(clip,path,"localPosition."+"xyz"[c],positions[b].Select(v=>v[c]).ToArray(),duration);
                    Curve(clip,path,"localScale."+"xyz"[c],scales[b].Select(v=>v[c]).ToArray(),duration);
                }
            }
            clip.EnsureQuaternionContinuity();
            if(maximumFootDrift>.012f)throw new InvalidOperationException(family+" "+name+" authored foot drift exceeds 12 mm: "+maximumFootDrift);
            if(maximumBoneMotion<.4f)throw new InvalidOperationException(family+" "+name+" contains insufficient authored motion.");
            string directory=Folder+"/"+family;Directory.CreateDirectory(directory);
            string target=directory+"/"+name+".anim";
            var existing=AssetDatabase.LoadAssetAtPath<AnimationClip>(target);
            if(existing){EditorUtility.CopySerialized(clip,existing);Object.DestroyImmediate(clip);EditorUtility.SetDirty(existing);}
            else AssetDatabase.CreateAsset(clip,target);
            return new{family,name,path=target,duration,sampledFrames=count,bones=rig.bones.Length,maximumBoneMotionDegrees=maximumBoneMotion,maximumPlantedFootDriftMetres=maximumFootDrift,rootMotion=false};
        }

        static void Curve(AnimationClip clip,string path,string property,float[] values,float duration)
        {
            var keys=values.Select((value,i)=>new Keyframe(i*duration/(values.Length-1),value)).ToArray();
            var curve=new AnimationCurve(keys);
            // Dense samples use linear tangents: no quaternion or contact overshoot between authored poses.
            for(int i=0;i<keys.Length;i++)
            {
                AnimationUtility.SetKeyLeftTangentMode(curve,i,AnimationUtility.TangentMode.Linear);
                AnimationUtility.SetKeyRightTangentMode(curve,i,AnimationUtility.TangentMode.Linear);
            }
            clip.SetCurve(path,typeof(Transform),property,curve);
        }

        static void Configure(ActorAnimation actor,string family,bool jumping,float phase)
        {
            if(!actor || !actor.animationSource)throw new InvalidOperationException("Expected supplied legacy actor: "+family);
            actor.idle=AssetDatabase.LoadAssetAtPath<AnimationClip>(Folder+"/"+family+"/idle.anim");
            actor.talk=AssetDatabase.LoadAssetAtPath<AnimationClip>(Folder+"/"+family+"/talk.anim");
            if(family=="Guard")
            {
                actor.idle=AssetDatabase.LoadAssetAtPath<AnimationClip>(Folder+"/Guard/idle_meshy.anim");
                actor.talk=AssetDatabase.LoadAssetAtPath<AnimationClip>(Folder+"/Guard/talk_meshy.anim");
            }
            if(jumping)
            {
                actor.jumpTakeoff=AssetDatabase.LoadAssetAtPath<AnimationClip>(Folder+"/"+family+"/jump_takeoff.anim");
                actor.jumpAirborne=AssetDatabase.LoadAssetAtPath<AnimationClip>(Folder+"/"+family+"/jump_airborne.anim");
                actor.jumpFall=AssetDatabase.LoadAssetAtPath<AnimationClip>(Folder+"/"+family+"/jump_fall.anim");
                actor.jumpLanding=AssetDatabase.LoadAssetAtPath<AnimationClip>(Folder+"/"+family+"/jump_landing.anim");
                actor.jumpLandingMoving=AssetDatabase.LoadAssetAtPath<AnimationClip>(Folder+"/"+family+"/jump_landing_moving.anim");
            }
            actor.takeoffSeconds=.12f;actor.landingSeconds=.24f;actor.idlePhase=phase;
            EditorUtility.SetDirty(actor);
            if(PrefabUtility.IsPartOfPrefabInstance(actor))PrefabUtility.RecordPrefabInstancePropertyModifications(actor);
        }

        static float Smooth(float a,float b,float t){t=Mathf.Clamp01((t-a)/(b-a));return t*t*(3-2*t);}
        static float Pulse(float t,float a,float peak,float end){return t<peak?Smooth(a,peak,t):1-Smooth(peak,end,t);}

        static void Pose(Rig r,string name,float time,float duration)
        {
            float u=time/duration;
            if(name=="idle"||name=="talk")
            {
                float cycle=time/duration*Mathf.PI*2;
                float breath=Mathf.Sin(cycle*2),shift=Mathf.Sin(cycle);
                r.OffsetHips(new Vector3(shift*.006f,0,0));
                r.Rotate("Spine02",Vector3.forward,-shift*.5f);
                r.Rotate("Spine",Vector3.right,breath*.65f);
                r.Rotate("LeftShoulder",Vector3.forward,breath*.6f);
                r.Rotate("RightShoulder",Vector3.forward,-breath*.6f);
                r.Rotate("Head",Vector3.up,Mathf.Sin(cycle)*2.2f);
                r.Rotate("Head",Vector3.right,Mathf.Sin(cycle*2+.5f)*.65f);
                if(name=="talk")
                {
                    float gesture=Pulse(u,.08f,.26f,.48f),answer=Pulse(u,.54f,.71f,.9f);
                    float emphasis=Pulse(u,.22f,.25f,.30f)+Pulse(u,.66f,.69f,.75f);
                    r.Rotate("Spine",Vector3.up,gesture*2-answer*1.2f);
                    r.Rotate("Head",Vector3.right,emphasis*3.8f);
                    r.Rotate("RightArm",Vector3.right,gesture*27);
                    r.Rotate("RightArm",Vector3.forward,gesture*7);
                    r.Rotate("RightForeArm",Vector3.right,gesture*31);
                    r.Rotate("RightHand",Vector3.up,-gesture*12);
                    r.Rotate("LeftArm",Vector3.right,answer*16);
                    r.Rotate("LeftArm",Vector3.forward,-answer*5);
                    r.Rotate("LeftForeArm",Vector3.right,answer*27);
                    r.Rotate("LeftHand",Vector3.up,answer*8);
                }
                r.PlantFeet();return;
            }
            if(name=="jump_takeoff")
            {
                // Input stays immediate: this is a short compression/release during the first rising frames.
                float compress=Pulse(u,0,.28f,.92f),extend=Smooth(.3f,1,u);
                r.OffsetHips(Vector3.down*(compress*.055f));
                r.Rotate("Spine02",Vector3.right,compress*5-extend*2);
                r.Rotate("LeftArm",Vector3.right,-compress*9+extend*20);
                r.Rotate("RightArm",Vector3.right,-compress*8+extend*17);
                r.Rotate("LeftForeArm",Vector3.right,extend*19);
                r.Rotate("RightForeArm",Vector3.right,extend*23);
                r.PlantFeet();return;
            }
            if(name=="jump_landing"||name=="jump_landing_moving")
            {
                float compress=Pulse(u,-.18f,.26f,1);
                r.OffsetHips(Vector3.down*(compress*(name=="jump_landing_moving"?.075f:.105f)));
                r.Rotate("Spine02",Vector3.right,compress*9);
                r.Rotate("Spine",Vector3.right,-compress*3);
                r.Rotate("Head",Vector3.right,-compress*4);
                r.Rotate("LeftArm",Vector3.right,compress*21);
                r.Rotate("RightArm",Vector3.right,compress*17);
                r.Rotate("LeftForeArm",Vector3.right,compress*20);
                r.Rotate("RightForeArm",Vector3.right,compress*24);
                r.PlantFeet();return;
            }
            bool falling=name=="jump_fall";
            float settle=Smooth(0,1,u);
            float leftThigh=falling?Mathf.Lerp(25,12,settle):Mathf.Lerp(10,25,settle);
            float rightThigh=falling?Mathf.Lerp(33,17,settle):Mathf.Lerp(15,33,settle);
            float leftKnee=falling?Mathf.Lerp(47,24,settle):Mathf.Lerp(22,47,settle);
            float rightKnee=falling?Mathf.Lerp(59,30,settle):Mathf.Lerp(28,59,settle);
            r.Rotate("Spine02",Vector3.right,falling?5:2);
            r.Rotate("LeftUpLeg",Vector3.right,leftThigh);r.Rotate("RightUpLeg",Vector3.right,rightThigh);
            r.Rotate("LeftLeg",Vector3.right,-leftKnee);r.Rotate("RightLeg",Vector3.right,-rightKnee);
            r.Rotate("LeftFoot",Vector3.right,falling?8:13);r.Rotate("RightFoot",Vector3.right,falling?10:16);
            r.Rotate("LeftArm",Vector3.right,falling?23:30);r.Rotate("RightArm",Vector3.right,falling?19:26);
            r.Rotate("LeftArm",Vector3.forward,falling?-13:-7);r.Rotate("RightArm",Vector3.forward,falling?13:7);
            r.Rotate("LeftForeArm",Vector3.right,falling?18:32);r.Rotate("RightForeArm",Vector3.right,falling?23:37);
            r.Rotate("Head",Vector3.right,falling?4:-2);
        }
    }
}
