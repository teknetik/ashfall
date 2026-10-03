using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object=UnityEngine.Object;

namespace AthenHill.Editor
{
    /// 2 Oct 2026 "next level" combat pass. Batch entry (one Unity job, -nographics unless a capture step is present):
    ///   -executeMethod AthenHill.Editor.CombatNextLevelPass.RunBatch -quit --steps rifle,gunners,threat,trade,music,verify
    ///   -executeMethod AthenHill.Editor.CombatNextLevelPass.RunBatch -quit --steps capture:<dir>:cam_rifle_aim+cam_rifle_side
    /// Every step is idempotent: re-running replaces only the objects it owns and keeps the saved scene's other state.
    public static class CombatNextLevelPass
    {
        public const string ScenePath="Assets/AthenHill/Scenes/AthenHill.unity";
        const string Evidence="../../evidence/next-level/20261002/combat";   // relative to Assets
        const string TradeClick="Assets/AthenHill/Audio/UI/trade-click.wav";
        const string MusicFolder="Assets/AthenHill/Audio/Music";
        const string NewTrack="Oasis of Ruins.mp3";
        const string IncomingTrack="../../meshy/incoming-20261002/Oasis of Ruins.mp3";     // relative to the project
        public static readonly string[] RangedPrefabs={"Assets/AthenHill/Prefabs/OuterBerms/FeralGunnerDroid.prefab","Assets/AthenHill/Prefabs/OuterBerms/FeralLancerDrone.prefab"};
        /// DroidThreat defaults added only where the prefab has no component yet (the enemies pass owns the values).
        public static readonly (string path,int level,int experience,float armour)[] ThreatDefaults=
        {
            ("Assets/AthenHill/Prefabs/OuterBerms/FeralWorkerDroid.prefab",1,10,0),
            ("Assets/AthenHill/Prefabs/OuterBerms/FeralScrapDrone.prefab",1,8,0),
            ("Assets/AthenHill/Prefabs/OuterBerms/FeralGunnerDroid.prefab",2,18,2),
            ("Assets/AthenHill/Prefabs/OuterBerms/FeralLancerDrone.prefab",2,16,2),
            ("Assets/AthenHill/Prefabs/OuterBerms/FeralDepotForeman.prefab",2,40,4),
        };

        static string EvidenceDir(){var d=Path.GetFullPath(Path.Combine(Application.dataPath,Evidence));Directory.CreateDirectory(d);return d;}
        static UnityEngine.SceneManagement.Scene OpenScene()=>EditorSceneManager.OpenScene(ScenePath,OpenSceneMode.Single);
        static void SaveScene(){var scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene();EditorSceneManager.MarkSceneDirty(scene);EditorSceneManager.SaveScene(scene);AssetDatabase.SaveAssets();}
        static PlayerCombat Combat()=>Object.FindAnyObjectByType<PlayerCombat>(FindObjectsInactive.Include)??throw new InvalidOperationException("No PlayerCombat in the scene.");
        static CityAudio Audio()=>Object.FindAnyObjectByType<CityAudio>(FindObjectsInactive.Include)??throw new InvalidOperationException("No CityAudio in the scene.");

        // ------------------------------------------------------------------ rifle
        /// Re-mounts the held rifle with the explicit muzzle end (RifleArmourInstall.MuzzleSign) and brings the
        /// PlayerCombat fallback numbers in line with the catalog (range 30 m, 4° spread). The pistol is untouched.
        public static string Rifle()
        {
            OpenScene();
            var log=RifleArmourInstall.Rifle();
            var combat=Combat();
            Undo.RecordObject(combat,"combat fallback");combat.range=30;combat.spread=4;
            PrefabUtility.RecordPrefabInstancePropertyModifications(combat);EditorUtility.SetDirty(combat);
            SaveScene();
            File.WriteAllText(Path.Combine(EvidenceDir(),"rifle-install.txt"),log+"\n");
            return log+"; PlayerCombat fallback range 30 spread 4";
        }

        // ------------------------------------------------------------------ gunners
        /// The ranged droid prefabs were built on top of a melee droid and still carry it as an active child: a whole
        /// second FeralDroid (Health, collider, rigidbody, LootSource, model) welded to every gunner and lancer, which
        /// is what "the feral gunners seem to be attached to the other droids" is. The ranged droid's voice AudioSource
        /// lives on that nested body, so it is moved to the root first; any other reference into the nested body
        /// fails the step rather than being dropped silently.
        public static string Gunners()
        {
            var log=new List<string>();
            foreach(var path in RangedPrefabs)log.Add(RemoveNestedDroids(path));
            AssetDatabase.SaveAssets();
            return string.Join("; ",log);
        }
        static string RemoveNestedDroids(string path)
        {
            var root=PrefabUtility.LoadPrefabContents(path);
            try
            {
                var rootDroid=root.GetComponent<FeralDroid>()??throw new InvalidOperationException(path+" has no FeralDroid on its root.");
                var nested=root.GetComponentsInChildren<FeralDroid>(true).Where(d=>d!=rootDroid).ToArray();
                if(nested.Length==0)return Path.GetFileNameWithoutExtension(path)+": no nested droid (already clean)";
                var removed=new List<string>();
                foreach(var n in nested)
                {
                    bool movedVoice=false;
                    if(rootDroid.voice&&rootDroid.voice.transform.IsChildOf(n.transform))
                    {
                        var copy=root.GetComponent<AudioSource>();if(!copy)copy=root.AddComponent<AudioSource>();
                        EditorUtility.CopySerialized(rootDroid.voice,copy);
                        rootDroid.voice=copy;movedVoice=true;
                    }
                    var stray=new List<string>();
                    void Check(string field,Object o){if(o is Component c&&c&&c.transform.IsChildOf(n.transform))stray.Add(field);if(o is GameObject g&&g&&g.transform.IsChildOf(n.transform))stray.Add(field);}
                    Check("animationSource",rootDroid.animationSource);Check("muzzle",rootDroid.muzzle);Check("aimLaser",rootDroid.aimLaser);Check("sparks",rootDroid.sparks);Check("smoke",rootDroid.smoke);
                    Check("eyeLight",rootDroid.eyeLight);Check("footDust",rootDroid.footDust);Check("motorLoop",rootDroid.motorLoop);Check("downwash",rootDroid.downwash);Check("voice",rootDroid.voice);
                    foreach(var r in rootDroid.glowRenderers)Check("glowRenderers",r);foreach(var f in rootDroid.feet)Check("feet",f);foreach(var r in rootDroid.rotors)Check("rotors",r);
                    if(stray.Count>0)throw new InvalidOperationException($"{path}: root droid still references the nested {n.name} through {string.Join(", ",stray)}; move those before removing it.");
                    int tris=n.GetComponentsInChildren<Renderer>(true).Length;
                    removed.Add($"{n.name} ({n.displayName}, {tris} renderers{(movedVoice?", voice moved to root":"")})");
                    Object.DestroyImmediate(n.gameObject);
                }
                PrefabUtility.SaveAsPrefabAsset(root,path);
                return Path.GetFileNameWithoutExtension(path)+": removed "+string.Join(" + ",removed);
            }
            finally{PrefabUtility.UnloadPrefabContents(root);}
        }

        // ------------------------------------------------------------------ threat
        /// Adds DroidThreat with the pass defaults to prefabs that have none (the enemies pass sets its own values and
        /// is not overwritten here).
        public static string Threat()
        {
            var log=new List<string>();
            foreach(var (path,level,experience,armour) in ThreatDefaults)
            {
                if(!File.Exists(path)){log.Add(Path.GetFileNameWithoutExtension(path)+": missing");continue;}
                var root=PrefabUtility.LoadPrefabContents(path);
                try
                {
                    var t=root.GetComponent<DroidThreat>();
                    // a prefab variant (the Foreman on the worker) inherits the base's component: give it its own values
                    // only while they are still the base defaults, so the enemies pass's numbers are never overwritten
                    bool variant=PrefabUtility.GetPrefabAssetType(AssetDatabase.LoadAssetAtPath<GameObject>(path))==PrefabAssetType.Variant;
                    bool inheritedDefaults=t&&variant&&t.level==1&&t.experience==10&&t.armour==0&&(level!=1||experience!=10||armour!=0);
                    if(t&&!inheritedDefaults){log.Add($"{Path.GetFileNameWithoutExtension(path)}: kept L{t.level} {t.experience} XP armour {t.armour}");continue;}
                    if(!t)t=root.AddComponent<DroidThreat>();
                    t.level=level;t.experience=experience;t.armour=armour;
                    PrefabUtility.SaveAsPrefabAsset(root,path);
                    log.Add($"{Path.GetFileNameWithoutExtension(path)}: added L{level} {experience} XP armour {armour}");
                }
                finally{PrefabUtility.UnloadPrefabContents(root);}
            }
            AssetDatabase.SaveAssets();
            return string.Join("; ",log);
        }

        // ------------------------------------------------------------------ trade click
        /// Points CityAudio.tradeConfirm at the synthesized digital click (Audio/UI/trade-click.wav, made by
        /// art/next_level_20261002/combat/make_trade_click.py). The old ElevenLabs clip asset stays for rollback.
        public static string Trade()
        {
            if(!File.Exists(TradeClick))throw new FileNotFoundException(TradeClick+" (run make_trade_click.py first)");
            AssetDatabase.ImportAsset(TradeClick,ImportAssetOptions.ForceSynchronousImport);
            var clip=AssetDatabase.LoadAssetAtPath<AudioClip>(TradeClick)??throw new InvalidOperationException("Trade click did not import as an AudioClip.");
            OpenScene();
            var audio=Audio();
            string old=audio.tradeConfirm?AssetDatabase.GetAssetPath(audio.tradeConfirm):"(none)";
            Undo.RecordObject(audio,"trade click");audio.tradeConfirm=clip;
            PrefabUtility.RecordPrefabInstancePropertyModifications(audio);EditorUtility.SetDirty(audio);
            SaveScene();
            return $"tradeConfirm {old} -> {TradeClick} ({clip.length:F3} s, {clip.frequency} Hz, {clip.channels} ch)";
        }

        // ------------------------------------------------------------------ music
        /// Copies the supplied "Oasis of Ruins" into Audio/Music (its .meta with the streaming import settings is
        /// committed beside it) and makes it the first track of the playlist; the two supplied 8 Sep tracks follow.
        public static string Music()
        {
            var dst=MusicFolder+"/"+NewTrack;
            if(!File.Exists(dst))
            {
                var src=Path.GetFullPath(Path.Combine(Application.dataPath,"../"+IncomingTrack));
                if(!File.Exists(src))throw new FileNotFoundException(src);
                File.Copy(src,dst);
            }
            AssetDatabase.ImportAsset(dst,ImportAssetOptions.ForceSynchronousImport);
            var clip=AssetDatabase.LoadAssetAtPath<AudioClip>(dst)??throw new InvalidOperationException("Music track did not import.");
            OpenScene();
            var audio=Audio();
            var rest=(audio.musicPlaylist??new AudioClip[0]).Where(c=>c&&c!=clip).Distinct().ToList();
            Undo.RecordObject(audio,"playlist");
            audio.musicPlaylist=new[]{clip}.Concat(rest).ToArray();
            PrefabUtility.RecordPrefabInstancePropertyModifications(audio);EditorUtility.SetDirty(audio);
            SaveScene();
            return "playlist: "+string.Join(" > ",audio.musicPlaylist.Select(c=>c.name+" ("+c.length.ToString("F0")+" s)"));
        }

        // ------------------------------------------------------------------ verify
        public static string Verify()
        {
            OpenScene();
            var lines=new List<string>();var fail=new List<string>();
            void Check(bool ok,string what){lines.Add((ok?"PASS ":"FAIL ")+what);if(!ok)fail.Add(what);}
            var combat=Combat();
            Check(combat.heldRifle&&combat.heldRifle.name==RifleArmourInstall.RifleHolder,"held rifle holder bound: "+(combat.heldRifle?combat.heldRifle.name:"null"));
            Check(combat.rifleMuzzle&&combat.rifleMuzzle.name==RifleArmourInstall.RifleMuzzle,"rifle muzzle bound: "+(combat.rifleMuzzle?combat.rifleMuzzle.name:"null"));
            if(combat.heldRifle&&combat.rifleMuzzle)
            {
                var holder=combat.heldRifle.transform;
                var rifle=holder.Find("FieldRifle");
                var filters=rifle?rifle.GetComponentsInChildren<MeshFilter>(true):new MeshFilter[0];
                var pts=filters.SelectMany(f=>f.sharedMesh.vertices.Select(v=>holder.InverseTransformPoint(f.transform.TransformPoint(v)))).ToArray();
                float zMin=pts.Min(p=>p.z),zMax=pts.Max(p=>p.z);
                var m=holder.InverseTransformPoint(combat.rifleMuzzle.position);
                lines.Add($"rifle in holder frame: z {zMin:F3}..{zMax:F3} (holder +Z = colonist forward), muzzle point z {m.z:F3} xy ({m.x:F3},{m.y:F3})");
                Check(m.z>zMax-.03f&&m.z>0,"muzzle point at the forward (+Z) end of the rifle");
                // the thin barrel band sits just behind the muzzle, the receiver behind the butt
                float Band(float a,float b){var sel=pts.Where(p=>{float t=(zMax-p.z)/(zMax-zMin);return t>=a&&t<=b;}).ToArray();if(sel.Length==0)return 0;var mn=sel.Aggregate(Vector3.Min);var mx=sel.Aggregate(Vector3.Max);var s=mx-mn;s.z=0;return s.magnitude;}
                float barrel=Band(.2f,.4f),receiver=Band(.6f,.8f);
                Check(barrel<receiver*.5f,$"thin barrel band in front ({barrel:F3} m) and the receiver behind ({receiver:F3} m)");
                Check(combat.heldPistol&&combat.muzzlePoint,"pistol holder and muzzle untouched: "+(combat.heldPistol?combat.heldPistol.name:"null"));
            }
            Check(Mathf.Approximately(combat.range,30)&&Mathf.Approximately(combat.spread,4),$"PlayerCombat fallback range {combat.range} spread {combat.spread}");
            foreach(var path in RangedPrefabs)
            {
                var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(path);
                var droids=prefab.GetComponentsInChildren<FeralDroid>(true);
                Check(droids.Length==1,$"{Path.GetFileNameWithoutExtension(path)}: one FeralDroid ({droids.Length}), healths {prefab.GetComponentsInChildren<Health>(true).Length}");
                var d=prefab.GetComponent<FeralDroid>();
                Check(d.voice&&d.voice.transform==prefab.transform,$"{Path.GetFileNameWithoutExtension(path)}: voice on the root");
                Check(d.muzzle&&d.animationSource||d.kind==DroidKind.Hover,$"{Path.GetFileNameWithoutExtension(path)}: muzzle/animation references intact");
            }
            foreach(var (path,_,_,_) in ThreatDefaults)
            {
                var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(path);if(!prefab)continue;
                var t=prefab.GetComponent<DroidThreat>();
                Check(t,$"{Path.GetFileNameWithoutExtension(path)}: DroidThreat"+(t?$" L{t.level} {t.experience} XP armour {t.armour}":" missing"));
            }
            var audio=Audio();
            Check(audio.tradeConfirm&&AssetDatabase.GetAssetPath(audio.tradeConfirm)==TradeClick,"tradeConfirm = "+(audio.tradeConfirm?AssetDatabase.GetAssetPath(audio.tradeConfirm):"null"));
            Check(audio.musicPlaylist!=null&&audio.musicPlaylist.Length==3&&audio.musicPlaylist[0]&&audio.musicPlaylist[0].name=="Oasis of Ruins","playlist: "+string.Join(" > ",(audio.musicPlaylist??new AudioClip[0]).Select(c=>c?c.name:"null")));
            var catalog=AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
            var pistol=catalog.weapons.First(w=>w.id=="weapon_scrap_pistol");var rifleDef=catalog.weapons.First(w=>w.id=="weapon_field_rifle");
            Check(pistol.stats.range==30&&pistol.stats.spread==4,$"pistol range {pistol.stats.range} spread {pistol.stats.spread}");
            Check(rifleDef.stats.range==95&&Mathf.Approximately(rifleDef.stats.spread,1.8f),$"rifle range {rifleDef.stats.range} spread {rifleDef.stats.spread}");
            Check(catalog.Stat("spread")!=null&&catalog.Stat("accuracy")!=null,"stat labels for spread and accuracy");
            var text=string.Join("\n",lines)+"\n"+(fail.Count==0?"ALL PASS":fail.Count+" FAILED")+"\n";
            File.WriteAllText(Path.Combine(EvidenceDir(),"verify.txt"),text);
            if(fail.Count>0)throw new InvalidOperationException("verify failed: "+string.Join(" | ",fail));
            return lines.Count+" checks, all pass";
        }

        // ------------------------------------------------------------------ capture
        /// Graphics run: the colonist at the review stand in the rifle hold with the rifle shown, a red sphere on
        /// PlayerCombat.rifleMuzzle and a cyan line 1.2 m out of it along the holder's forward, rendered from the named
        /// cameras (at most six). Nothing is saved.
        public static string Capture(string outDir,string views)
        {
            var scene=OpenScene();
            var combat=Combat();var motor=combat.GetComponent<PlayerMotor>();var pose=combat.GetComponent<PlayerWeaponPose>();
            if(!combat.heldRifle||!combat.rifleMuzzle||!pose||!pose.rifleAimClip)throw new InvalidOperationException("Rifle not installed (run the rifle step first).");
            var stand=RifleArmourInstall.Stand;
            combat.transform.position=stand;
            if(motor.visual)motor.visual.rotation=Quaternion.LookRotation(Vector3.left,Vector3.up);
            var root=motor.actor.animationSource.gameObject;
            pose.rifleAimClip.SampleAnimation(root,0);
            if(combat.heldPistol)combat.heldPistol.SetActive(false);
            combat.heldRifle.SetActive(true);
            var marker=new GameObject("__muzzle_marker"){hideFlags=HideFlags.DontSave};
            var sphere=GameObject.CreatePrimitive(PrimitiveType.Sphere);sphere.name="muzzle";sphere.transform.SetParent(marker.transform,false);
            Object.DestroyImmediate(sphere.GetComponent<Collider>());
            sphere.transform.position=combat.rifleMuzzle.position;sphere.transform.localScale=Vector3.one*.05f;
            var unlit=Shader.Find("Universal Render Pipeline/Unlit");
            var red=new Material(unlit){color=new Color(1,.1f,.05f)};sphere.GetComponent<Renderer>().sharedMaterial=red;
            var line=marker.AddComponent<LineRenderer>();line.useWorldSpace=true;line.positionCount=2;line.widthMultiplier=.012f;
            var forward=combat.heldRifle.transform.forward;
            line.SetPosition(0,combat.rifleMuzzle.position);line.SetPosition(1,combat.rifleMuzzle.position+forward*1.2f);
            line.sharedMaterial=new Material(unlit){color=new Color(.2f,1,1)};
            // a second, white sphere on the butt end so the two ends are unmistakable in the capture
            var rifle=combat.heldRifle.transform.Find("FieldRifle");
            var filters=rifle.GetComponentsInChildren<MeshFilter>(true);
            var holder=combat.heldRifle.transform;
            var pts=filters.SelectMany(f=>f.sharedMesh.vertices.Select(v=>holder.InverseTransformPoint(f.transform.TransformPoint(v))));
            var butt=pts.OrderBy(p=>p.z).First();
            var white=GameObject.CreatePrimitive(PrimitiveType.Sphere);white.name="butt";white.transform.SetParent(marker.transform,false);Object.DestroyImmediate(white.GetComponent<Collider>());
            white.transform.position=holder.TransformPoint(new Vector3(0,butt.y,butt.z));white.transform.localScale=Vector3.one*.04f;
            white.GetComponent<Renderer>().sharedMaterial=new Material(unlit){color=Color.white};
            var camsByName=scene.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<Camera>(true)).GroupBy(c=>c.name).ToDictionary(g=>g.Key,g=>g.First());
            var list=new List<(string name,Vector3 pos,Vector3 target,float fov)>();
            foreach(var n in views.Split('+'))
            {
                if(n=="cam_rifle_muzzle")
                {
                    // close-up of the muzzle from the colonist's left, looking along the barrel end
                    var mp=combat.rifleMuzzle.position;
                    list.Add((n,mp+new Vector3(.25f,.25f,.9f),mp,32));continue;
                }
                if(!camsByName.TryGetValue(n,out var c))throw new Exception("camera not found: "+n);
                list.Add((n,c.transform.position,c.transform.position+c.transform.forward*5f,c.fieldOfView));
            }
            if(list.Count>6)throw new Exception($"{list.Count} views in one run; capture at most 6 per Unity run");
            var done=StreetDressingPass.Capture(outDir,list);
            Object.DestroyImmediate(marker);
            var info=$"stand {stand} muzzle world {combat.rifleMuzzle.position:F3} holder forward {forward:F3} butt local z {butt.z:F3}";
            File.WriteAllText(Path.Combine(outDir,"capture.txt"),info+"\n"+string.Join("\n",done)+"\n");
            return info+" -> "+string.Join(",",done);
        }

        public static void RunBatch()
        {
            var args=Environment.GetCommandLineArgs();
            int i=Array.IndexOf(args,"--steps");
            var steps=i>=0?args[i+1].Split(','):new[]{"verify"};
            var log=new List<string>();
            try
            {
                foreach(var st in steps)
                {
                    var parts=st.Split(':');
                    string result=parts[0] switch
                    {
                        "rifle"=>Rifle(),
                        "gunners"=>Gunners(),
                        "threat"=>Threat(),
                        "trade"=>Trade(),
                        "music"=>Music(),
                        "verify"=>Verify(),
                        "capture"=>Capture(parts[1],parts[2]),
                        _=>throw new Exception("unknown step "+st),
                    };
                    Debug.Log("CombatNextLevelPass "+st+": "+result);log.Add(st+": "+result);
                }
                File.AppendAllText(Path.Combine(EvidenceDir(),"batch-log.txt"),DateTime.Now.ToString("HH:mm:ss")+"\n"+string.Join("\n",log)+"\n\n");
                EditorApplication.Exit(0);
            }
            catch(Exception e){Debug.LogException(e);File.AppendAllText(Path.Combine(EvidenceDir(),"batch-log.txt"),DateTime.Now.ToString("HH:mm:ss")+" FAILED "+string.Join("\n",log)+"\n"+e+"\n\n");EditorApplication.Exit(1);}
        }
    }
}
