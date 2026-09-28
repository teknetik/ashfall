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
    // 27 Sep 2026 character-feel pass: calm Warden idles from the Meshy animation library.
    // The Sep 2026 guard rig task has expired, so the same Meshy model was re-rigged (meshy/character-feel-20260927).
    // Its skeleton matches the installed ward-guard.glb (same 24 bones and names, rest rotations within ~1 degree,
    // joint offsets within ~3 mm), so clips keep only bone rotations plus the Hips translation; the installed rig's
    // bone lengths are never overwritten. Sources stay in Art/CharacterMotion/Source; clips are written to
    // Art/CharacterMotion/Guard/idle_calm_<action>.anim. Nothing here touches meshes, prefabs or scene objects.
    public static class CharacterFeelPass
    {
        const string SourceFolder="Assets/AthenHill/Art/CharacterMotion/Source";
        const string GuardFolder="Assets/AthenHill/Art/CharacterMotion/Guard";
        public static readonly int[] CalmIdleActions={243,244,246,249,251,252};
        public static readonly int[] TalkActions={309,313,314,47};

        [MenuItem("Athen Hill/Characters/Import calm Warden idle candidates")]
        public static void ImportCalmIdles()
        {
            var report=new List<object>();
            foreach(int action in CalmIdleActions)
                report.Add(ImportLegacyClip(SourceFolder+"/GuardIdle"+action+".glb",GuardFolder+"/idle_calm_"+action+".anim",true));
            foreach(int action in TalkActions)
                report.Add(ImportLegacyClip(SourceFolder+"/GuardTalk"+action+".glb",GuardFolder+"/talk_calm_"+action+".anim",true));
            AssetDatabase.SaveAssets();
            Debug.Log("Calm Warden idle candidates: "+JsonConvert.SerializeObject(report));
        }

        // Per-character calm idle/talk so the six guard-model characters never share a loop (with the per-placement
        // phase and speed jitter in ActorAnimation on top). Previous clips (idle_meshy/talk_meshy) stay in the project.
        static readonly Dictionary<string,string[]> Assignments=new Dictionary<string,string[]>{
            {"Warden Ossa",new[]{"idle_calm_243","talk_calm_313"}},
            {"Warden Rell",new[]{"idle_calm_252","talk_calm_314"}},
            {"npc_torr",new[]{"idle_calm_244","talk_calm_313"}},
            {"npc_mira",new[]{"idle_calm_246","talk_calm_314"}},
            {"npc_linn",new[]{"idle_calm_252","talk_calm_313"}},
            {"npc_vex",new[]{"idle_calm_243","talk_calm_314"}}};

        [MenuItem("Athen Hill/Characters/Install calm Warden and colonist idles")]
        public static string InstallCalmGuards()
        {
            if(EditorApplication.isPlaying)throw new InvalidOperationException("Exit Play first.");
            const string prefabPath="Assets/AthenHill/Prefabs/WardGuard.prefab";
            var root=PrefabUtility.LoadPrefabContents(prefabPath);
            var log=new List<string>();
            try
            {
                var actor=root.GetComponent<ActorAnimation>();
                actor.idle=Clip("idle_calm_252");actor.talk=Clip("talk_calm_313");
                actor.randomIdlePhase=true;actor.idleSpeedJitter=.08f;
                var look=root.GetComponent<ActorLookAt>();if(!look)look=root.AddComponent<ActorLookAt>();
                look.actor=actor;
                foreach(var t in root.GetComponentsInChildren<Transform>(true)){if(t.name=="Head")look.head=t;if(t.name=="neck")look.neck=t;}
                if(!look.head||!look.neck)throw new InvalidOperationException("WardGuard prefab has no Head/neck bones.");
                PrefabUtility.SaveAsPrefabAsset(root,prefabPath);
                log.Add("prefab idle_calm_252/talk_calm_313 + ActorLookAt");
            }
            finally{PrefabUtility.UnloadPrefabContents(root);}
            foreach(var actor in Object.FindObjectsByType<ActorAnimation>(FindObjectsInactive.Include))
            {
                string key=Assignments.Keys.FirstOrDefault(k=>actor.name==k||actor.transform.parent&&actor.transform.parent.name==k);
                if(key==null)continue;
                Undo.RecordObject(actor,"Calm guard idle");
                actor.idle=Clip(Assignments[key][0]);actor.talk=Clip(Assignments[key][1]);
                actor.randomIdlePhase=true;actor.idleSpeedJitter=.08f;
                PrefabUtility.RecordPrefabInstancePropertyModifications(actor);
                if(!actor.GetComponent<ActorLookAt>())throw new InvalidOperationException(key+" is not a WardGuard prefab instance (no ActorLookAt).");
                if(actor.idle&&actor.animationSource)actor.idle.SampleAnimation(actor.animationSource.gameObject,0);
                log.Add(key+": "+Assignments[key][0]+" / "+Assignments[key][1]);
            }
            if(log.Count!=7)throw new InvalidOperationException("Expected the prefab and six guard-model characters: "+string.Join("; ",log));
            var scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene();
            UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(scene);
            UnityEditor.SceneManagement.EditorSceneManager.SaveScene(scene);
            return string.Join("\n",log);
        }

        const string FootstepFolder="Assets/AthenHill/Audio/ElevenLabs/Footsteps";
        static readonly (string,FootSurface)[] SurfaceRules={
            ("yard apron",FootSurface.Concrete),("concrete apron",FootSurface.Concrete),("apron",FootSurface.Concrete),
            ("jersey",FootSurface.Concrete),("dp_plinth",FootSurface.Concrete),
            ("karaveen",FootSurface.Metal),("container",FootSurface.Metal),("cradle",FootSurface.Metal),("carcass",FootSurface.Metal),
            ("drone",FootSurface.Metal),("debris",FootSurface.Metal),("scrap",FootSurface.Metal),("conveyor",FootSurface.Metal),
            ("mining droid",FootSurface.Metal),("gantry",FootSurface.Metal),("generator",FootSurface.Metal),
            ("crate",FootSurface.Wood),("bench",FootSurface.Wood),("cart",FootSurface.Wood),
            ("rubble",FootSurface.Gravel),("hesco",FootSurface.Sand),("hill_surface",FootSurface.Sand),
            ("boulder",FootSurface.Stone),("plinth",FootSurface.Stone),("porch",FootSurface.Stone)};

        [MenuItem("Athen Hill/Audio/Install surface footsteps")]
        public static string InstallFootsteps()
        {
            if(EditorApplication.isPlaying)throw new InvalidOperationException("Exit Play first.");
            var player=Object.FindAnyObjectByType<PlayerMotor>();
            var city=Object.FindAnyObjectByType<CityAudio>();
            if(!player||!city||!city.steps)throw new InvalidOperationException("Open the city scene (player, City Audio with its footstep source).");
            foreach(var path in Directory.GetFiles(FootstepFolder,"*.wav"))
            {
                var ai=(AudioImporter)AssetImporter.GetAtPath(path.Replace('\\','/'));
                var d=ai.defaultSampleSettings;
                if(d.loadType!=AudioClipLoadType.DecompressOnLoad||d.compressionFormat!=AudioCompressionFormat.PCM||!ai.forceToMono)
                {d.loadType=AudioClipLoadType.DecompressOnLoad;d.compressionFormat=AudioCompressionFormat.PCM;ai.defaultSampleSettings=d;ai.forceToMono=true;ai.SaveAndReimport();}
            }
            var fa=player.GetComponent<FootstepAudio>();if(!fa)fa=Undo.AddComponent<FootstepAudio>(player.gameObject);
            Undo.RecordObject(fa,"Footsteps");
            fa.session=city.session;fa.motor=player;fa.source=city.steps;
            fa.follow=Object.FindAnyObjectByType<FollowCamera>();fa.combat=player.GetComponent<PlayerCombat>();if(!fa.combat)fa.combat=Object.FindAnyObjectByType<PlayerCombat>();
            foreach(var t in player.GetComponentsInChildren<Transform>(true)){if(t.name=="LeftFoot")fa.leftFoot=t;if(t.name=="RightFoot")fa.rightFoot=t;}
            if(!fa.leftFoot||!fa.rightFoot)throw new InvalidOperationException("Player rig has no LeftFoot/RightFoot.");
            // Planted foot bones sit ~0.14 m above the player's feet in the Meshy walk/run (measured 27 Sep 2026:
            // walk 0.136-0.328 m, run 0.128-0.783 m); the contact fires as the swinging foot comes back down.
            fa.contactHeight=.165f;fa.liftHeight=.21f;fa.minInterval=.18f;
            var sets=new List<FootstepSet>();var counts=new List<string>();
            foreach(FootSurface surface in Enum.GetValues(typeof(FootSurface)))
            {
                string key=surface.ToString().ToLowerInvariant();
                AudioClip[] Load(string gait)=>Directory.GetFiles(FootstepFolder,key+"-"+gait+"-*.wav").OrderBy(f=>f).Select(f=>AssetDatabase.LoadAssetAtPath<AudioClip>(f.Replace('\\','/'))).Where(c=>c).ToArray();
                var set=new FootstepSet{surface=surface,walk=Load("walk"),run=Load("run"),land=Load("land")};
                if(set.walk.Length==0)throw new InvalidOperationException("No walk steps for "+surface);
                sets.Add(set);counts.Add(key+" "+set.walk.Length+"/"+set.run.Length+"/"+set.land.Length);
            }
            fa.sets=sets.ToArray();
            fa.colliderRules=SurfaceRules.Select(r=>new FootSurfaceRule{nameContains=r.Item1,surface=r.Item2}).ToArray();
            fa.defaultSurface=FootSurface.Stone;fa.bermsGroundName="berms ground";
            // Mix: the new sets are ~7 dB quieter than the old stone steps before this trim (-30 vs -23.3 LUFS).
            fa.volume=.5f;fa.runVolume=.6f;fa.landVolume=.7f;fa.pitchJitter=.05f;fa.volumeJitterDb=2;fa.firstPersonScale=.7f;fa.aimingScale=.75f;
            var ground=Object.FindObjectsByType<Renderer>(FindObjectsInactive.Include,FindObjectsSortMode.None).FirstOrDefault(r=>r.name=="Berms ground");
            if(!ground)throw new InvalidOperationException("Berms ground renderer not found.");
            var rect=ground.sharedMaterial.GetVector("_SplatRect");fa.bermsRect=rect;
            var png=new Texture2D(2,2);png.LoadImage(File.ReadAllBytes("Assets/AthenHill/Art/WestGate/Ground/BermsGroundSplat.png"));
            // One cell per ~0.5 m: R gravel road, G sand, B crust (crunchy, heard as fine gravel).
            int w=Mathf.RoundToInt(2/rect.z),h=Mathf.RoundToInt(2/rect.w);var grid=new byte[w*h];var tally=new int[6];
            for(int y=0;y<h;y++)for(int x=0;x<w;x++)
            {
                var c=png.GetPixelBilinear((x+.5f)/w,(y+.5f)/h);
                var sfc=c.g>=c.r&&c.g>=c.b||Mathf.Max(c.r,c.g,c.b)<.15f?FootSurface.Sand:FootSurface.Gravel;
                grid[y*w+x]=(byte)sfc;tally[(int)sfc]++;
            }
            Object.DestroyImmediate(png);
            fa.bermsWidth=w;fa.bermsHeight=h;fa.bermsSurfaces=grid;
            EditorUtility.SetDirty(fa);
            Undo.RecordObject(city,"Footsteps");city.footsteps=fa;EditorUtility.SetDirty(city);
            var scene=player.gameObject.scene;UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(scene);UnityEditor.SceneManagement.EditorSceneManager.SaveScene(scene);
            return "sets "+string.Join(", ",counts)+"; berms grid "+w+"x"+h+" sand "+tally[(int)FootSurface.Sand]+" gravel "+tally[(int)FootSurface.Gravel]
                +"; source "+city.steps.name+" vol "+city.steps.volume+" spatial "+city.steps.spatialBlend+" group "+(city.steps.outputAudioMixerGroup?city.steps.outputAudioMixerGroup.name:"-");
        }

        // ---- Player: Meshy library clips retargeted from a fresh Meshy rig of the same colonist model ----
        // The fresh rig's joint frames differ from the installed player skeleton (hips/chest ~110 degrees), so clips are
        // retargeted by bind-pose deltas: for every bone, its rotation relative to its own skin bind pose (in the rig
        // root's space) is carried over to the same-named player bone. Both rigs bind in Meshy's A-pose. The Hips
        // displacement from bind is scaled by the hip-height ratio. Output: Art/CharacterMotion/Player/<name>.anim.
        const string PlayerSource="Assets/AthenHill/Art/CharacterMotion/Source/Player";
        const string PlayerFolder="Assets/AthenHill/Art/CharacterMotion/Player";
        static readonly string[] PlayerClips={"aim_95","draw_222","back_233","fwd_234","left_528","aimturn_585","idle_243","idle_252","turnl_576","turnr_586"};

        [MenuItem("Athen Hill/Characters/Retarget player weapon and idle clips")]
        public static string RetargetPlayerClips()
        {
            var prefab=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/MeshyPlayer.prefab");
            var target=(GameObject)Object.Instantiate(prefab);target.hideFlags=HideFlags.HideAndDontSave;
            var log=new List<string>();
            try
            {
                var tActor=target.GetComponent<ActorAnimation>();
                var tRoot=tActor.animationSource.transform;
                target.transform.SetPositionAndRotation(Vector3.zero,Quaternion.identity);
                foreach(var name in PlayerClips)
                    log.Add(Retarget(PlayerSource+"/Player_"+name+".glb",tRoot,PlayerFolder+"/lib_"+name+".anim"));
            }
            finally{Object.DestroyImmediate(target);}
            AssetDatabase.SaveAssets();
            return string.Join("\n",log);
        }

        static Dictionary<string,Quaternion> BindRotations(Transform root,out Dictionary<string,Vector3> bindPositions)
        {
            var rot=new Dictionary<string,Quaternion>();bindPositions=new Dictionary<string,Vector3>();
            var inv=Quaternion.Inverse(root.rotation);
            foreach(var skin in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                var bp=skin.sharedMesh.bindposes;
                for(int i=0;i<skin.bones.Length&&i<bp.Length;i++)
                {
                    if(!skin.bones[i]||rot.ContainsKey(skin.bones[i].name))continue;
                    var world=skin.transform.localToWorldMatrix*bp[i].inverse;
                    rot[skin.bones[i].name]=inv*world.rotation;
                    bindPositions[skin.bones[i].name]=root.InverseTransformPoint(world.GetColumn(3));
                }
            }
            return rot;
        }

        static string Retarget(string sourcePath,Transform tRoot,string targetPath)
        {
            AssetDatabase.ImportAsset(sourcePath,ImportAssetOptions.ForceSynchronousImport);
            var importer=AssetImporter.GetAtPath(sourcePath);
            var settings=new SerializedObject(importer);var method=settings.FindProperty("importSettings.animationMethod");
            int legacy=Array.IndexOf(method.enumNames,"Legacy");
            if(method.enumValueIndex!=legacy){method.enumValueIndex=legacy;settings.ApplyModifiedPropertiesWithoutUndo();importer.SaveAndReimport();}
            var clipSrc=AssetDatabase.LoadAllAssetsAtPath(sourcePath).OfType<AnimationClip>().First(c=>c.legacy);
            var model=AssetDatabase.LoadAssetAtPath<GameObject>(sourcePath);
            var src=(GameObject)Object.Instantiate(model);src.hideFlags=HideFlags.HideAndDontSave;
            try
            {
                src.transform.SetPositionAndRotation(Vector3.zero,Quaternion.identity);
                var sRoot=src.transform;
                var sBind=BindRotations(sRoot,out var sBindPos);var tBind=BindRotations(tRoot,out var tBindPos);
                var sBones=sRoot.GetComponentsInChildren<Transform>(true).Where(t=>sBind.ContainsKey(t.name)).ToDictionary(t=>t.name);
                var tBones=tRoot.GetComponentsInChildren<Transform>(true).Where(t=>tBind.ContainsKey(t.name)&&sBones.ContainsKey(t.name)).OrderBy(Depth).ToArray();
                float hipScale=tBindPos["Hips"].y/Mathf.Max(.01f,sBindPos["Hips"].y);
                var tHipsParent=tBones.First(t=>t.name=="Hips").parent;
                int frames=Mathf.Max(2,Mathf.RoundToInt(clipSrc.length*30)+1);
                var rotKeys=tBones.ToDictionary(t=>t.name,t=>new List<Quaternion>());var hips=new List<Vector3>();
                var saved=tBones.ToDictionary(t=>t,t=>(t.localRotation,t.localPosition));
                var sAnimRoot=src.GetComponentInChildren<Animation>()?src.GetComponentInChildren<Animation>().gameObject:src;
                for(int f=0;f<frames;f++)
                {
                    float time=clipSrc.length*f/(frames-1);
                    clipSrc.SampleAnimation(sAnimRoot,time);
                    // parents first, so each child's world rotation is known when it is converted to local
                    foreach(var tb in tBones)
                    {
                        var sb=sBones[tb.name];
                        var sNow=Quaternion.Inverse(sRoot.rotation)*sb.rotation;
                        var delta=sNow*Quaternion.Inverse(sBind[tb.name]);
                        var world=tRoot.rotation*(delta*tBind[tb.name]);
                        tb.rotation=world;
                        var q=tb.localRotation;var list=rotKeys[tb.name];
                        if(list.Count>0&&Quaternion.Dot(list[list.Count-1],q)<0)q=new Quaternion(-q.x,-q.y,-q.z,-q.w);
                        list.Add(q);
                    }
                    var sh=sRoot.InverseTransformPoint(sBones["Hips"].position)-sBindPos["Hips"];
                    var th=tRoot.TransformPoint(tBindPos["Hips"]+sh*hipScale);
                    hips.Add(tHipsParent.InverseTransformPoint(th));
                }
                foreach(var kv in saved){kv.Key.localRotation=kv.Value.Item1;kv.Key.localPosition=kv.Value.Item2;}
                var clip=new AnimationClip{name=Path.GetFileNameWithoutExtension(targetPath),legacy=true,frameRate=30,wrapMode=WrapMode.Loop};
                foreach(var tb in tBones)
                {
                    string path=AnimationUtility.CalculateTransformPath(tb,tRoot);var q=rotKeys[tb.name];
                    for(int c=0;c<4;c++){var curve=new AnimationCurve(q.Select((v,k)=>new Keyframe(clipSrc.length*k/(frames-1),v[c])).ToArray());clip.SetCurve(path,typeof(Transform),"localRotation."+"xyzw"[c],curve);}
                    if(tb.name=="Hips")for(int c=0;c<3;c++){var curve=new AnimationCurve(hips.Select((v,k)=>new Keyframe(clipSrc.length*k/(frames-1),v[c])).ToArray());clip.SetCurve(path,typeof(Transform),"localPosition."+"xyz"[c],curve);}
                }
                clip.EnsureQuaternionContinuity();
                Directory.CreateDirectory(PlayerFolder);
                var existing=AssetDatabase.LoadAssetAtPath<AnimationClip>(targetPath);
                if(existing){EditorUtility.CopySerialized(clip,existing);Object.DestroyImmediate(clip);EditorUtility.SetDirty(existing);}
                else AssetDatabase.CreateAsset(clip,targetPath);
                return targetPath+" "+clipSrc.length.ToString("F2")+"s bones "+tBones.Length+" hipScale "+hipScale.ToString("F3");
            }
            finally{Object.DestroyImmediate(src);}
        }

        static int Depth(Transform t){int d=0;while(t.parent){d++;t=t.parent;}return d;}

        // The player's previous idle/talk was a single static frame (Player/idle.anim, kept for rollback). The retargeted
        // Meshy library "Idle 13" (action 252) is a calm, planted breathing idle.
        [MenuItem("Athen Hill/Characters/Install player breathing idle")]
        public static string InstallPlayerIdle()
        {
            var motor=Object.FindAnyObjectByType<PlayerMotor>();
            var clip=AssetDatabase.LoadAssetAtPath<AnimationClip>(PlayerFolder+"/lib_idle_252.anim");
            if(!motor||!motor.actor||!clip)throw new InvalidOperationException("Player or retargeted idle missing.");
            Undo.RecordObject(motor.actor,"Player idle");
            string before=motor.actor.idle?motor.actor.idle.name:"-";
            motor.actor.idle=clip;motor.actor.talk=clip;motor.actor.randomIdlePhase=false;motor.actor.idleSpeedJitter=0;
            PrefabUtility.RecordPrefabInstancePropertyModifications(motor.actor);EditorUtility.SetDirty(motor.actor);
            clip.SampleAnimation(motor.actor.animationSource.gameObject,0);
            EditorSceneManager.MarkSceneDirty(motor.gameObject.scene);EditorSceneManager.SaveScene(motor.gameObject.scene);
            return "player idle "+before+" -> "+clip.name;
        }

        static AnimationClip Clip(string name)
        {
            var c=AssetDatabase.LoadAssetAtPath<AnimationClip>(GuardFolder+"/"+name+".anim");
            if(!c)throw new FileNotFoundException(name);return c;
        }

        /// Import a glTFast legacy clip, keep rotations (all bones) and the Hips translation, and close the loop seam.
        public static object ImportLegacyClip(string sourcePath,string targetPath,bool loop)
        {
            AssetDatabase.ImportAsset(sourcePath,ImportAssetOptions.ForceSynchronousImport);
            var importer=AssetImporter.GetAtPath(sourcePath);
            if(importer==null)throw new FileNotFoundException(sourcePath);
            var settings=new SerializedObject(importer);
            var method=settings.FindProperty("importSettings.animationMethod");
            if(method==null)throw new InvalidOperationException("Expected glTFast animation import settings: "+sourcePath);
            int legacy=Array.IndexOf(method.enumNames,"Legacy");
            if(method.enumValueIndex!=legacy){method.enumValueIndex=legacy;settings.ApplyModifiedPropertiesWithoutUndo();importer.SaveAndReimport();}
            var source=AssetDatabase.LoadAllAssetsAtPath(sourcePath).OfType<AnimationClip>().FirstOrDefault(c=>c.legacy);
            if(!source)throw new InvalidOperationException("No legacy clip in "+sourcePath);
            var clip=new AnimationClip{name=Path.GetFileNameWithoutExtension(targetPath),legacy=true,frameRate=source.frameRate,wrapMode=loop?WrapMode.Loop:WrapMode.ClampForever};
            int kept=0,dropped=0;float seam=0;
            foreach(var binding in AnimationUtility.GetCurveBindings(source))
            {
                bool rotation=binding.propertyName.StartsWith("m_LocalRotation")||binding.propertyName.StartsWith("localRotation");
                bool hipsPosition=(binding.propertyName.StartsWith("m_LocalPosition")||binding.propertyName.StartsWith("localPosition"))&&binding.path.EndsWith("/Hips");
                if(!rotation&&!hipsPosition){dropped++;continue;}
                var curve=AnimationUtility.GetEditorCurve(source,binding);
                if(loop&&curve.length>2)seam=Mathf.Max(seam,CloseLoop(curve,binding.propertyName.Contains("Position")?.3f:.3f));
                clip.SetCurve(binding.path,typeof(Transform),binding.propertyName.Replace("m_LocalRotation","localRotation").Replace("m_LocalPosition","localPosition"),curve);
                kept++;
            }
            clip.EnsureQuaternionContinuity();
            var existing=AssetDatabase.LoadAssetAtPath<AnimationClip>(targetPath);
            if(existing){EditorUtility.CopySerialized(clip,existing);Object.DestroyImmediate(clip);EditorUtility.SetDirty(existing);}
            else AssetDatabase.CreateAsset(clip,targetPath);
            return new{source=sourcePath,target=targetPath,length=source.length,curvesKept=kept,curvesDropped=dropped,loopSeamCorrection=seam};
        }

        /// Blend the last `seconds` of a curve toward its first value so the loop is seamless. Returns the seam size.
        static float CloseLoop(AnimationCurve curve,float seconds)
        {
            var keys=curve.keys;float end=keys[keys.Length-1].time,start=keys[0].time;
            float seam=Mathf.Abs(keys[keys.Length-1].value-keys[0].value);
            seconds=Mathf.Min(seconds,(end-start)*.25f);
            for(int i=0;i<keys.Length;i++)
            {
                float w=Mathf.InverseLerp(end-seconds,end,keys[i].time);
                if(w<=0)continue;
                w=w*w*(3-2*w);
                keys[i].value=Mathf.Lerp(keys[i].value,keys[0].value,w);
            }
            curve.keys=keys;
            for(int i=0;i<curve.length;i++)AnimationUtility.SetKeyLeftTangentMode(curve,i,AnimationUtility.TangentMode.ClampedAuto);
            for(int i=0;i<curve.length;i++)AnimationUtility.SetKeyRightTangentMode(curve,i,AnimationUtility.TangentMode.ClampedAuto);
            return seam;
        }
    }
}
