using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    /// <summary>
    /// Character arms, 20 Nov 2026 (art/character_arms_20261120/README.md). Carl after the 19 Nov playtest: "All the
    /// character have their arms in very strange positions", then "more the main character ... in-natural and kinda camp".
    /// Adds an ArmPoseCorrector (runtime, LateUpdate order 20) to every active ActorAnimation in the saved scene, wired to
    /// the rig's arm, collarbone and finger bones, with per-state limits read from art/character_arms_20261120/characters.json
    /// (a default profile for any character not named there, so new residents are covered by re-running install).
    /// Steps (-executeMethod AthenHill.Editor.CharacterArmsPass20261120.RunBatch --steps a,b,c):
    ///   survey   samples every clip of every actor and measures both arms before and after the correction (nothing saved);
    ///            survey.json + survey.md in the evidence folder
    ///   install  idempotent: adds or rewires the correctors (json values overwrite the Inspector values), review cameras
    ///   verify   -nographics: installed, bound, prefab links intact, no missing scripts, idle limits met; verify.json
    ///   rollback removes the correctors and the review cameras (records in art/character_arms_20261120/installed.json)
    ///   dump     poses every actor (before/after, idle/talk/walk/run) and writes the skinned meshes to OBJ for
    ///            art/character_arms_20261120/render_dump.py (Blender); nothing saved
    /// </summary>
    public static class CharacterArmsPass20261120
    {
        const string Scene="Assets/AthenHill/Scenes/AthenHill.unity";
        public const string CamRootName="Character arms review cameras";
        static string Root=>Path.GetFullPath(Path.Combine(Application.dataPath,"../../.."));
        static string ArtDir=>Path.Combine(Root,"art/character_arms_20261120");
        static string EvDir=>Path.Combine(Root,"unity/evidence/showcase_phase2/20261120/character_arms");
        static string ConfigPath=>Path.Combine(ArtDir,"characters.json");
        static string RecordPath=>Path.Combine(ArtDir,"installed.json");
        static readonly string[] States={"idle","walk","run","talk","air"};
        static readonly string[] Digits={"Thumb","Index","Middle","Ring","Pinky"};

        public static void RunBatch()
        {
            var a=Environment.GetCommandLineArgs();
            string Arg(string k,string def){int i=Array.IndexOf(a,k);return i>=0&&i+1<a.Length?a[i+1]:def;}
            var steps=Arg("--steps","verify").Split(',').Select(s=>s.Trim()).Where(s=>s.Length>0).ToArray();
            int code=0;var log=new List<string>();
            try
            {
                Directory.CreateDirectory(ArtDir);Directory.CreateDirectory(EvDir);
                if(EditorSceneManager.GetActiveScene().path!=Scene)EditorSceneManager.OpenScene(Scene,OpenSceneMode.Single);
                foreach(var s in steps)
                {
                    string r=s switch{"survey"=>Survey(Arg("--tag","survey"),Arg("--only",null)),"install"=>Install(),"verify"=>Verify(),"rollback"=>Rollback(),"dump"=>Dump(Arg("--tag","dump"),Arg("--only",null),!a.Contains("--no-pistol")),
                        _=>throw new ArgumentException("unknown step "+s)};
                    log.Add("["+s+"] "+r);Debug.Log("CharacterArmsPass20261120 "+s+"\n"+r);
                }
            }
            catch(Exception e){Debug.LogException(e);log.Add("FAILED "+e);code=1;}
            try{File.WriteAllText(Path.Combine(EvDir,string.Join("_",steps)+"-result.txt"),string.Join("\n",log)+"\n");}catch(Exception e){Debug.LogException(e);}
            EditorApplication.Exit(code);
        }

        // ------------------------------------------------------------------ actors, rigs and config
        public class Actor{public string key,label,profile;public ActorAnimation anim;public GameObject go;public Transform leftUpLeg,rightUpLeg;}

        /// Every active ActorAnimation in the scene with a stable key: "player", or the NPC/walker/actor object name.
        static List<Actor> Actors()
        {
            var cfg=Config();var list=new List<Actor>();
            var motor=Object.FindAnyObjectByType<PlayerMotor>(FindObjectsInactive.Include);
            foreach(var anim in Object.FindObjectsByType<ActorAnimation>(FindObjectsInactive.Exclude,FindObjectsSortMode.None).OrderBy(x=>PathOf(x.transform)))
            {
                string key;
                if(motor&&motor.actor==anim)key="player";
                else
                {
                    var npc=anim.GetComponentInParent<NpcAgent>();var walker=anim.GetComponentInParent<AmbientWalker>();
                    key=npc?npc.name:walker?walker.name:anim.name;
                }
                var entry=(cfg["characters"] as JArray)?.FirstOrDefault(c=>System.Text.RegularExpressions.Regex.IsMatch(key,(string)c["match"]));
                list.Add(new Actor{key=key,anim=anim,go=anim.gameObject,label=(string)entry?["label"]??System.Text.RegularExpressions.Regex.Replace(key,"^(npc_|Warden )",""),profile=(string)entry?["profile"]??(string)cfg["defaultProfile"]});
            }
            // the same name twice (a Warden at the gate and again in the Berms): number the later ones
            foreach(var g in list.GroupBy(x=>x.key).Where(g=>g.Count()>1))
            {int i=0;foreach(var x in g){if(i>0){x.key+="_"+(i+1);x.label+="_"+(i+1);}i++;}}
            return list;
        }
        static JObject Config()=>JObject.Parse(File.ReadAllText(ConfigPath));
        static string PathOf(Transform t){var p=new List<string>();for(var x=t;x;x=x.parent)p.Add(x.name);p.Reverse();return string.Join("/",p);}

        /// Wires the bones of the actor's rig into the corrector (legacy Meshy/MPFB names or a Humanoid Animator).
        static bool Wire(ArmPoseCorrector c,Actor a,List<string> notes)
        {
            c.actor=a.anim;
            var root=a.anim.animationSource?a.anim.animationSource.transform:a.anim.transform;
            Transform N(params string[] names){foreach(var n in names){var t=root.GetComponentsInChildren<Transform>(true).FirstOrDefault(x=>x.name==n);if(t)return t;}return null;}
            var h=a.anim.humanoidAnimator;
            if(h&&h.isHuman)
            {
                Transform B(HumanBodyBones b)=>h.GetBoneTransform(b);
                c.leftShoulder=B(HumanBodyBones.LeftShoulder);c.leftArm=B(HumanBodyBones.LeftUpperArm);c.leftForeArm=B(HumanBodyBones.LeftLowerArm);c.leftHand=B(HumanBodyBones.LeftHand);
                c.rightShoulder=B(HumanBodyBones.RightShoulder);c.rightArm=B(HumanBodyBones.RightUpperArm);c.rightForeArm=B(HumanBodyBones.RightLowerArm);c.rightHand=B(HumanBodyBones.RightHand);
                c.chest=B(HumanBodyBones.UpperChest)??B(HumanBodyBones.Chest)??B(HumanBodyBones.Spine);
                Transform[] F(bool left){var r=new Transform[15];for(int d=0;d<5;d++)for(int j=0;j<3;j++)r[d*3+j]=B((HumanBodyBones)((left?(int)HumanBodyBones.LeftThumbProximal:(int)HumanBodyBones.RightThumbProximal)+d*3+j));return r.All(x=>x)?r:new Transform[0];}
                c.leftFingers=F(true);c.rightFingers=F(false);
                a.leftUpLeg=B(HumanBodyBones.LeftUpperLeg);a.rightUpLeg=B(HumanBodyBones.RightUpperLeg);
            }
            else
            {
                c.leftShoulder=N("LeftShoulder","clavicle_l");c.leftArm=N("LeftArm","upperarm_l");c.leftForeArm=N("LeftForeArm","lowerarm_l");c.leftHand=N("LeftHand","hand_l");
                c.rightShoulder=N("RightShoulder","clavicle_r");c.rightArm=N("RightArm","upperarm_r");c.rightForeArm=N("RightForeArm","lowerarm_r");c.rightHand=N("RightHand","hand_r");
                c.chest=c.leftShoulder?c.leftShoulder.parent:c.leftArm?c.leftArm.parent:null;
                Transform[] F(bool left)
                {
                    var r=new Transform[15];string side=left?"Left":"Right",s=left?"l":"r";
                    for(int d=0;d<5;d++)for(int j=0;j<3;j++)
                        r[d*3+j]=N($"{Digits[d].ToLowerInvariant()}_0{j+1}_{s}",$"{side}Hand{Digits[d]}{j+1}",$"mixamorig:{side}Hand{Digits[d]}{j+1}");
                    return r.All(x=>x)?r:new Transform[0];
                }
                c.leftFingers=F(true);c.rightFingers=F(false);
                a.leftUpLeg=N("LeftUpLeg","thigh_l");a.rightUpLeg=N("RightUpLeg","thigh_r");
            }
            if(a.key=="player")
            {
                c.combat=Object.FindAnyObjectByType<PlayerCombat>(FindObjectsInactive.Include);
                c.weaponPose=Object.FindAnyObjectByType<PlayerWeaponPose>(FindObjectsInactive.Include);
                c.handGrip=BodyGrip(a);
            }
            bool ok=c.Bind();
            if(!ok)notes.Add(a.key+": bind failed (chest "+(c.chest?c.chest.name:"none")+", arms "+(c.leftArm&&c.rightArm)+")");
            return ok;
        }

        /// The PlayerHandGrip on the third-person body (its finger bones are under the actor), not a view model's.
        static PlayerHandGrip BodyGrip(Actor a)=>Object.FindObjectsByType<PlayerHandGrip>(FindObjectsInactive.Include,FindObjectsSortMode.None)
            .FirstOrDefault(g=>g.rightFingers!=null&&g.rightFingers.Length>0&&g.rightFingers[0]&&g.rightFingers[0].IsChildOf(a.anim.transform));

        /// Fills the corrector's five state profiles: the json profile, then the character's overrides.
        static void ApplyConfig(ArmPoseCorrector c,Actor a,JObject cfg)
        {
            var prof=cfg["profiles"]?[a.profile] as JObject??throw new InvalidOperationException("no profile "+a.profile);
            var over=(cfg["characters"] as JArray)?.FirstOrDefault(x=>System.Text.RegularExpressions.Regex.IsMatch(a.key,(string)x["match"]))?["overrides"] as JObject;
            foreach(var st in States)
            {
                var p=new ArmPoseProfile();
                if(prof["all"] is JObject all)JsonConvert.PopulateObject(all.ToString(),p);
                if(prof[st] is JObject s)JsonConvert.PopulateObject(s.ToString(),p);
                if(over?["all"] is JObject oa)JsonConvert.PopulateObject(oa.ToString(),p);
                if(over?[st] is JObject os)JsonConvert.PopulateObject(os.ToString(),p);
                switch(st){case "idle":c.idle=p;break;case "walk":c.walk=p;break;case "run":c.run=p;break;case "talk":c.talk=p;break;default:c.air=p;break;}
            }
            if(over?["weight"]!=null)c.weight=(float)over["weight"];else if(prof["weight"]!=null)c.weight=(float)prof["weight"];else c.weight=1;
            if(over?["corrector"] is JObject cf)SetFields(c,cf);
        }

        /// Sets public fields by name from json (float, bool, Vector2/3, arrays); returns the previous values as json.
        static JObject SetFields(object target,JObject values)
        {
            var prev=new JObject();
            foreach(var kv in values)
            {
                var f=target.GetType().GetField(kv.Key);if(f==null)throw new InvalidOperationException(target.GetType().Name+" has no field "+kv.Key);
                prev[kv.Key]=Tok(f.GetValue(target));
                f.SetValue(target,FromTok(kv.Value,f.FieldType));
            }
            return prev;
        }
        static JToken Tok(object v)=>v switch{Vector2 a=>new JArray(a.x,a.y),Vector3 a=>new JArray(a.x,a.y,a.z),Quaternion[] q=>new JArray(q.Select(x=>new JArray(x.x,x.y,x.z,x.w))),_=>JToken.FromObject(v)};
        static object FromTok(JToken t,Type type)
        {
            if(type==typeof(Vector2))return new Vector2((float)t[0],(float)t[1]);
            if(type==typeof(Vector3))return new Vector3((float)t[0],(float)t[1],(float)t[2]);
            if(type==typeof(Quaternion[]))return t.Select(x=>new Quaternion((float)x[0],(float)x[1],(float)x[2],(float)x[3])).ToArray();
            return t.ToObject(type);
        }
        /// The player's weapon settings from the json ("playerWeapon" on PlayerWeaponPose, "playerGrip" on the body's
        /// PlayerHandGrip). Returns the previous values (for the record / to put back after a preview).
        static (JObject weapon,JObject grip) ApplyPlayerWeapon(Actor a,JObject cfg)
        {
            var pose=Object.FindAnyObjectByType<PlayerWeaponPose>(FindObjectsInactive.Include);var grip=BodyGrip(a);
            JObject w=null,g=null;
            if(pose&&cfg["playerWeapon"] is JObject pw)w=SetFields(pose,pw);
            if(grip&&cfg["playerGrip"] is JObject pg)g=SetFields(grip,pg);
            return (w,g);
        }
        static void RestorePlayerWeapon(Actor a,(JObject weapon,JObject grip) prev)
        {
            var pose=Object.FindAnyObjectByType<PlayerWeaponPose>(FindObjectsInactive.Include);var grip=BodyGrip(a);
            if(pose&&prev.weapon!=null)SetFields(pose,prev.weapon);
            if(grip&&prev.grip!=null)SetFields(grip,prev.grip);
        }

        // ------------------------------------------------------------------ clips and sampling
        static List<(string state,string slot,AnimationClip clip)> Clips(Actor a)
        {
            var r=new List<(string,string,AnimationClip)>();var an=a.anim;
            void Add(string st,string slot,AnimationClip c){if(c&&!r.Any(x=>x.Item3==c&&x.Item2==slot))r.Add((st,slot,c));}
            if(an.humanoidAnimator&&an.humanoidAnimator.runtimeAnimatorController)
            {
                foreach(var c in an.humanoidAnimator.runtimeAnimatorController.animationClips)
                    Add(c.name.ToLowerInvariant().Contains("run")?"run":c.name.ToLowerInvariant().Contains("walk")?"walk":"idle",c.name,c);
                return r;
            }
            Add("idle","idle",an.idle);if(an.walk!=an.idle)Add("walk","walk",an.walk);if(an.run!=an.walk&&an.run!=an.idle)Add("run","run",an.run);
            if(an.talk!=an.idle)Add("talk","talk",an.talk);
            Add("air","jumpTakeoff",an.jumpTakeoff);Add("air","jumpAirborne",an.jumpAirborne);Add("air","jumpFall",an.jumpFall);Add("air","jumpLanding",an.jumpLanding);Add("air","jumpLandingMoving",an.jumpLandingMoving);
            if(a.key=="player")
            {
                var pose=Object.FindAnyObjectByType<PlayerWeaponPose>(FindObjectsInactive.Include);
                if(pose){Add("weapon","pistol_hold",pose.aimClip);Add("weapon","rifle_hold",pose.rifleAimClip);Add("weapon","rifle_carry",pose.rifleCarryClip);}
            }
            return r;
        }
        static GameObject SampleHost(Actor a)=>a.anim.humanoidAnimator?a.anim.humanoidAnimator.gameObject:a.anim.animationSource?a.anim.animationSource.gameObject:a.anim.gameObject;
        /// Snapshot of every transform under the actor (sampling a clip leaves bones it does not key where they were).
        static Dictionary<Transform,(Vector3,Quaternion,Vector3)> Snap(GameObject go)=>go.GetComponentsInChildren<Transform>(true).ToDictionary(t=>t,t=>(t.localPosition,t.localRotation,t.localScale));
        static void Restore(Dictionary<Transform,(Vector3,Quaternion,Vector3)> s){foreach(var kv in s)if(kv.Key){kv.Key.localPosition=kv.Value.Item1;kv.Key.localRotation=kv.Value.Item2;kv.Key.localScale=kv.Value.Item3;}}
        static void Sample(Actor a,string state,AnimationClip clip,float t01)
        {
            var host=SampleHost(a);
            if(state=="weapon"&&a.anim.idle){a.anim.idle.SampleAnimation(host,0);}
            clip.SampleAnimation(host,t01*clip.length);
        }

        // ------------------------------------------------------------------ measures
        public static readonly string[] Metrics={"abduction","forward","elbowFlex","elbowOut","palm","wrist","shoulderLift","handOut","fingerSpread","fingerCurl"};
        static Dictionary<string,float> Measure(ArmPoseCorrector c,Actor a,bool right)
        {
            var (tr,tu,tf)=c.Torso();float side=right?1:-1;var lat=side*tr;
            Transform up=right?c.rightArm:c.leftArm,fo=right?c.rightForeArm:c.leftForeArm,ha=right?c.rightHand:c.leftHand;
            var d=(fo.position-up.position).normalized;var fd=(ha.position-fo.position).normalized;
            var m=new Dictionary<string,float>
            {
                ["abduction"]=ArmPoseMath.Abduction(d,lat),["forward"]=ArmPoseMath.Forward(d,tf),["elbowFlex"]=ArmPoseMath.ElbowFlex(d,fd),
                ["elbowOut"]=ArmPoseMath.ElbowFlex(d,fd)>10?ArmPoseMath.ElbowOut(d,ArmPoseMath.BendDirection(d,fd),tf,tu,lat):float.NaN,
                ["palm"]=ArmPoseMath.PalmFacing(fd,c.PalmNormal(right),lat,side),["wrist"]=Vector3.Angle(fd,c.HandDirection(right)),
                ["shoulderLift"]=c.ShoulderLift(right),
            };
            var leg=right?a.rightUpLeg:a.leftUpLeg;
            m["handOut"]=leg?Vector3.Dot(ha.position-leg.position,lat)*100:float.NaN;
            var f=right?c.rightFingers:c.leftFingers;
            if(f!=null&&f.Length==15)
            {
                Vector3 Dir(int dg,int j){var b=ArmPoseCorrector.Finger(f,dg,j);var n=ArmPoseCorrector.Finger(f,dg,j+1);return (n.position-b.position).normalized;}
                m["fingerSpread"]=Vector3.Angle(Dir(1,0),Dir(4,0));
                float curl=0;for(int dg=1;dg<5;dg++){var hd=c.HandDirection(right);curl+=Vector3.Angle(hd,Dir(dg,0))+Vector3.Angle(Dir(dg,0),Dir(dg,1));}
                m["fingerCurl"]=curl/4;
            }
            else{m["fingerSpread"]=float.NaN;m["fingerCurl"]=float.NaN;}
            return m;
        }
        /// Forward swing of a limb's upper bone relative to the torso (deg), for the gait phase check.
        static float Swing(Transform upper,Transform lower,Vector3 fwd,Vector3 upAxis){var d=(lower.position-upper.position).normalized;return Mathf.Atan2(Vector3.Dot(d,fwd),-Vector3.Dot(d,upAxis))*Mathf.Rad2Deg;}

        /// A temporary corrector configured from the json (removed afterwards when the actor had none).
        static ArmPoseCorrector Corrector(Actor a,JObject cfg,List<string> notes,out bool temporary)
        {
            var c=a.go.GetComponent<ArmPoseCorrector>();temporary=!c;
            if(!c)c=a.go.AddComponent<ArmPoseCorrector>();
            if(!Wire(c,a,notes)){if(temporary)Object.DestroyImmediate(c);return null;}
            ApplyConfig(c,a,cfg);return c;
        }

        // ------------------------------------------------------------------ the player's pistol (third person)
        public static readonly (string name,string slot,string state,float t,float raise)[] PistolPoses=
        {
            ("pistol_carry_idle","idle","idle",.3f,0),("pistol_carry_walk00","walk","walk",0,0),("pistol_carry_walk50","walk","walk",.5f,0),
            ("pistol_carry_run25","run","run",.25f,0),("pistol_raise50","idle","idle",.3f,.5f),("pistol_aim_idle","idle","idle",.3f,1),("pistol_aim_walk25","walk","walk",.25f,1),
        };
        /// Poses the player with the pistol drawn as the runtime does: locomotion clip, the hold clip mixed over the upper
        /// body by raise, (after: the corrector at -20), PlayerWeaponPose (carry turn / barrel on the aim line), the grips,
        /// (after: the finger pass). before = the shipped behaviour (support hand always gripping).
        static (Transform weapon,Quaternion mount) PosePistol(Actor a,ArmPoseCorrector c,AnimationClip baseClip,string state,float t,float raise,bool after)
        {
            var combat=Object.FindAnyObjectByType<PlayerCombat>(FindObjectsInactive.Include);var pose=Object.FindAnyObjectByType<PlayerWeaponPose>(FindObjectsInactive.Include);
            var grip=BodyGrip(a);var host=SampleHost(a);
            baseClip.SampleAnimation(host,t*baseClip.length);
            if(raise>0&&pose&&pose.aimClip&&pose.mixRoot)
            {
                var mix=pose.mixRoot.GetComponentsInChildren<Transform>(true);
                var lower=a.go.GetComponentsInChildren<Transform>(true).Except(mix).ToDictionary(x=>x,x=>(x.localPosition,x.localRotation));
                var baseRot=mix.ToDictionary(x=>x,x=>x.localRotation);
                pose.aimClip.SampleAnimation(host,t*pose.aimClip.length);
                foreach(var kv in lower){kv.Key.localPosition=kv.Value.Item1;kv.Key.localRotation=kv.Value.Item2;}
                foreach(var x in mix)x.localRotation=Quaternion.Slerp(baseRot[x],x.localRotation,raise);
            }
            (JObject,JObject) prev=(null,null);
            if(after)prev=ApplyPlayerWeapon(a,Config());
            try{
            if(after)c.ApplyNow(state,raise,false,false);
            var weapon=combat.heldPistol?combat.heldPistol.transform:null;
            if(weapon&&!mounts.ContainsKey(weapon))mounts[weapon]=weapon.localRotation;
            if(weapon)weapon.localRotation=mounts[weapon];
            if(combat.heldPistol)combat.heldPistol.SetActive(true);
            if(pose)pose.PreviewPose(raise,a.anim.transform.forward);
            float left=after?(raise>=.3f?1:0):1;
            if(grip)grip.PreviewGrip(1,left,false);
            if(after){c.PistolAim(a.anim.transform.forward,raise*c.pistolAimWeight);c.FingersNow(state,left,1);}
            return (weapon,weapon?mounts[weapon]:Quaternion.identity);
            }
            finally{if(after)RestorePlayerWeapon(a,prev);}
        }
        static readonly Dictionary<Transform,Quaternion> mounts=new Dictionary<Transform,Quaternion>();
        /// Pistol measures: barrel pitch below the horizon and yaw from the body forward, how far the pistol has turned
        /// inside the hand away from its gripped mount, the right wrist bend and elbow, the right hand's height.
        static Dictionary<string,float> PistolMeasure(ArmPoseCorrector c,Actor a,Transform weapon,Quaternion mount)
        {
            var m=Measure(c,a,true);
            var f=weapon.forward;var body=a.anim.transform;
            m["barrelPitchDown"]=-Mathf.Asin(Mathf.Clamp(f.y,-1,1))*Mathf.Rad2Deg;
            m["barrelYaw"]=Vector3.SignedAngle(Vector3.ProjectOnPlane(body.forward,Vector3.up),Vector3.ProjectOnPlane(f,Vector3.up),Vector3.up);
            m["turnInHand"]=Quaternion.Angle(weapon.localRotation,mount);
            m["handHeight"]=(c.rightHand.position.y-body.position.y)*100;
            return m;
        }
        static string PistolSurvey(Actor a,ArmPoseCorrector c,StringBuilder md,List<string> notes)
        {
            var combat=Object.FindAnyObjectByType<PlayerCombat>(FindObjectsInactive.Include);
            if(!combat||!combat.heldPistol)return "no pistol";
            bool was=combat.heldPistol.activeSelf;var snap=Snap(a.go);var wsnap=Snap(combat.heldPistol);
            var keys=new[]{"abduction","forward","elbowFlex","elbowOut","palm","wrist","barrelPitchDown","barrelYaw","turnInHand","handHeight"};
            md.Append("### Pistol (third person), right arm\n\nbarrelPitchDown: muzzle below the horizon; barrelYaw: from the body forward (+ = right); turnInHand: how far the pistol is turned inside the hand away from its gripped mount (the grip leaves the palm as this grows); handHeight: above the feet (cm).\n\n");
            md.Append("| pose | version | ").Append(string.Join(" | ",keys)).Append(" |\n|").Append(string.Concat(Enumerable.Repeat("---|",keys.Length+2))).Append("\n");
            var clips=Clips(a);
            foreach(var (name,slot,state,t,raise) in PistolPoses)
            {
                var clip=clips.FirstOrDefault(x=>x.slot==slot).clip;if(!clip)continue;
                foreach(var after in new[]{false,true})
                {
                    var vals=new List<Dictionary<string,float>>();
                    // the carry and walk poses are sampled across the cycle; the named t is the dump frame
                    var ts=state=="idle"?new[]{t}:Enumerable.Range(0,12).Select(i=>(i+.5f)/12).ToArray();
                    foreach(var tt in ts)
                    {
                        Restore(snap);Restore(wsnap);
                        var (w,mount)=PosePistol(a,c,clip,state,tt,raise,after);
                        vals.Add(PistolMeasure(c,a,w,mount));
                    }
                    md.Append("| ").Append(name).Append(" | ").Append(after?"after":"before").Append(" | ")
                      .Append(string.Join(" | ",keys.Select(k=>{var v=vals.Select(x=>x[k]).Where(x=>!float.IsNaN(x)).ToArray();return v.Length==0?"-":v.Length==1?$"{v[0]:0}":$"{v.Average():0} ({v.Min():0}..{v.Max():0})";}))).Append(" |\n");
                }
            }
            Restore(snap);Restore(wsnap);combat.heldPistol.SetActive(was);
            md.Append('\n');
            return "ok";
        }

        // ------------------------------------------------------------------ survey
        static string Survey(string tag,string only)
        {
            var cfg=Config();var notes=new List<string>();var outDir=Path.Combine(EvDir,tag);Directory.CreateDirectory(outDir);
            var all=new List<object>();var md=new StringBuilder();
            md.Append("# Arm survey ").Append(tag).Append(" (").Append(DateTime.Now.ToString("yyyy-MM-dd HH:mm")).Append(")\n\n");
            md.Append("Mean (min..max) over 24 samples per clip, both arms pooled; after = with the ArmPoseCorrector state profile. Degrees, cm.\n");
            md.Append("abduction: upper arm out of the body; forward: upper arm reach; elbowOut: elbow turned out (0 = forearm bends forward); palm: 0 = palm to thigh, + = palm back; wrist: total wrist bend; shoulderLift: shoulder height over bind (cm); handOut: hand's lateral distance outside the hip joint (cm).\n\n");
            foreach(var a in Actors())
            {
                if(only!=null&&!System.Text.RegularExpressions.Regex.IsMatch(a.key,only))continue;
                var c=Corrector(a,cfg,notes,out bool temp);if(!c)continue;
                var snap=Snap(a.go);
                var rig=new{a.key,a.label,a.profile,path=PathOf(a.go.transform),humanoid=a.anim.humanoidAnimator!=null,fingers=c.rightFingers.Length==15,
                    bones=new[]{c.chest,c.leftShoulder,c.leftArm,c.leftForeArm,c.leftHand,c.rightShoulder,c.rightArm,c.rightForeArm,c.rightHand}.Select(t=>t?t.name:null)};
                var clips=new List<object>();
                md.Append("## ").Append(a.label).Append(" (`").Append(a.key).Append("`, profile ").Append(a.profile).Append(rig.fingers?", fingers":"").Append(")\n\n");
                md.Append("| clip | state | ").Append(string.Join(" | ",Metrics.Take(8))).Append(" |\n|").Append(string.Concat(Enumerable.Repeat("---|",10))).Append("\n");
                foreach(var (state,slot,clip) in Clips(a))
                {
                    var before=new List<Dictionary<string,float>>();var after=new List<Dictionary<string,float>>();var gait=new List<float[]>();var gaitBefore=new List<float[]>();var gaitAfter=new List<float[]>();
                    var extremes=new List<string>();
                    const int N=24;
                    for(int i=0;i<N;i++)
                    {
                        float t=(i+.5f)/N;
                        Restore(snap);Sample(a,state,clip,t);
                        var mb=new[]{Measure(c,a,false),Measure(c,a,true)};before.AddRange(mb);
                        var (tr,tu,tf)=c.Torso();
                        if(a.leftUpLeg&&a.rightUpLeg&&(state=="walk"||state=="run"))
                        {
                            var ll=a.leftUpLeg.GetChild(0);var rl=a.rightUpLeg.GetChild(0);
                            gait.Add(new[]{Swing(c.leftArm,c.leftForeArm,tf,tu),Swing(c.rightArm,c.rightForeArm,tf,tu),Swing(a.leftUpLeg,ll,tf,tu),Swing(a.rightUpLeg,rl,tf,tu)});
                            gaitBefore.Add(new[]{Swing(c.leftArm,c.leftForeArm,tf,tu),Swing(c.rightArm,c.rightForeArm,tf,tu),HandSwing(c,false,tf),HandSwing(c,true,tf),ArmPoseMath.ElbowFlex(c.leftForeArm.position-c.leftArm.position,c.leftHand.position-c.leftForeArm.position),ArmPoseMath.ElbowFlex(c.rightForeArm.position-c.rightArm.position,c.rightHand.position-c.rightForeArm.position)});
                        }
                        foreach(var (m,sd) in new[]{(mb[0],"L"),(mb[1],"R")})
                        {
                            if(!float.IsNaN(m["elbowOut"])&&Mathf.Abs(m["elbowOut"])>120)extremes.Add($"t{t:0.00}{sd} elbow bends backward/outward ({m["elbowOut"]:0})");
                            if(m["wrist"]>65)extremes.Add($"t{t:0.00}{sd} wrist {m["wrist"]:0}");
                            if(Mathf.Abs(m["palm"])>150)extremes.Add($"t{t:0.00}{sd} palm faces out ({m["palm"]:0})");
                        }
                        if(state!="weapon")
                        {
                            c.ApplyNow(state);after.Add(Measure(c,a,false));after.Add(Measure(c,a,true));
                            if(a.leftUpLeg&&a.rightUpLeg&&(state=="walk"||state=="run"))
                            {
                                var (tr2,tu2,tf2)=c.Torso();
                                gaitAfter.Add(new[]{Swing(c.leftArm,c.leftForeArm,tf2,tu2),Swing(c.rightArm,c.rightForeArm,tf2,tu2),HandSwing(c,false,tf2),HandSwing(c,true,tf2),ArmPoseMath.ElbowFlex(c.leftForeArm.position-c.leftArm.position,c.leftHand.position-c.leftForeArm.position),ArmPoseMath.ElbowFlex(c.rightForeArm.position-c.rightArm.position,c.rightHand.position-c.rightForeArm.position)});
                            }
                        }
                    }
                    Restore(snap);
                    object Stat(List<Dictionary<string,float>> l)=>Metrics.ToDictionary(k=>k,k=>{var v=l.Select(x=>x[k]).Where(x=>!float.IsNaN(x)).ToArray();return v.Length==0?null:(object)new{mean=R(v.Average()),min=R(v.Min()),max=R(v.Max())};});
                    string Cell(List<Dictionary<string,float>> l,string k){var v=l.Select(x=>x[k]).Where(x=>!float.IsNaN(x)).ToArray();return v.Length==0?"-":$"{v.Average():0} ({v.Min():0}..{v.Max():0})";}
                    float? phase=null;
                    if(gait.Count>4)
                    {
                        // left arm should swing with the right leg: correlation of the two forward swings
                        float Corr(Func<float[],float> x,Func<float[],float> y){var xs=gait.Select(x).ToArray();var ys=gait.Select(y).ToArray();float mx=xs.Average(),my=ys.Average();float sxy=0,sxx=0,syy=0;for(int i=0;i<xs.Length;i++){sxy+=(xs[i]-mx)*(ys[i]-my);sxx+=(xs[i]-mx)*(xs[i]-mx);syy+=(ys[i]-my)*(ys[i]-my);}return sxy/Mathf.Sqrt(Mathf.Max(1e-6f,sxx*syy));}
                        phase=(Corr(g=>g[0],g=>g[3])+Corr(g=>g[1],g=>g[2]))/2;
                    }
                    clips.Add(new{slot,state,clip=clip.name,length=R(clip.length),before=Stat(before),after=after.Count>0?Stat(after):null,armLegPhase=phase.HasValue?R(phase.Value):(float?)null,
                        armSwingRange=gait.Count>0?new[]{R(gait.Max(g=>g[0])-gait.Min(g=>g[0])),R(gait.Max(g=>g[1])-gait.Min(g=>g[1]))}:null,
                        swing=gaitBefore.Count>0?new{before=GaitStats(gaitBefore),after=GaitStats(gaitAfter)}:null,extremes=extremes.Take(12)});
                    if(gaitBefore.Count>0)notes.Add($"{a.key} {slot}: swing before {GaitText(gaitBefore)} | after {GaitText(gaitAfter)}");
                    md.Append("| ").Append(slot).Append(" before | ").Append(state).Append(" | ").Append(string.Join(" | ",Metrics.Take(8).Select(k=>Cell(before,k)))).Append(" |\n");
                    if(after.Count>0)md.Append("| ").Append(slot).Append(" after | ").Append(state).Append(" | ").Append(string.Join(" | ",Metrics.Take(8).Select(k=>Cell(after,k)))).Append(" |\n");
                    if(rig.fingers)notes.Add($"{a.key} {slot}: finger spread {Cell(before,"fingerSpread")} -> {(after.Count>0?Cell(after,"fingerSpread"):"-")}, curl {Cell(before,"fingerCurl")} -> {(after.Count>0?Cell(after,"fingerCurl"):"-")}");
                    if(phase.HasValue)notes.Add($"{a.key} {slot}: arm/opposite-leg swing correlation {phase:0.00} (1 = in phase), arm swing range L/R {gait.Max(g=>g[0])-gait.Min(g=>g[0]):0}/{gait.Max(g=>g[1])-gait.Min(g=>g[1]):0} deg");
                    if(extremes.Count>0)notes.Add($"{a.key} {slot}: {extremes.Count} extreme samples, e.g. {string.Join("; ",extremes.Take(4))}");
                }
                if(a.key=="player")notes.Add("player pistol survey: "+PistolSurvey(a,c,md,notes));
                md.Append('\n');
                all.Add(new{rig,clips});
                if(temp)Object.DestroyImmediate(c);
            }
            md.Append("## Notes\n\n").Append(string.Join("\n",notes.Select(n=>"- "+n))).Append('\n');
            File.WriteAllText(Path.Combine(outDir,"survey.json"),JsonConvert.SerializeObject(new{actors=all,notes},Formatting.Indented));
            File.WriteAllText(Path.Combine(outDir,"survey.md"),md.ToString());
            return $"{all.Count} actors surveyed -> {outDir}; {notes.Count} notes";
        }
        static float R(float v)=>(float)Math.Round(v,1);
        /// The hand's fore-aft position relative to the shoulder joint (cm), for the swing range.
        static float HandSwing(ArmPoseCorrector c,bool right,Vector3 fwd)=>Vector3.Dot((right?c.rightHand:c.leftHand).position-(right?c.rightArm:c.leftArm).position,fwd)*100;
        static object GaitStats(List<float[]> g)
        {
            if(g.Count==0)return null;
            float Rg(int i)=>R(g.Max(x=>x[i])-g.Min(x=>x[i]));
            return new{upperArmSwingDeg=new[]{Rg(0),Rg(1)},handSwingCm=new[]{Rg(2),Rg(3)},elbowFlexMin=new[]{R(g.Min(x=>x[4])),R(g.Min(x=>x[5]))},elbowFlexMax=new[]{R(g.Max(x=>x[4])),R(g.Max(x=>x[5]))}};
        }
        static string GaitText(List<float[]> g)
        {
            if(g.Count==0)return "-";
            float Rg(int i)=>g.Max(x=>x[i])-g.Min(x=>x[i]);
            return $"upper-arm swing L/R {Rg(0):0}/{Rg(1):0} deg, hand fore-aft L/R {Rg(2):0}/{Rg(3):0} cm, elbow L {g.Min(x=>x[4]):0}..{g.Max(x=>x[4]):0} R {g.Min(x=>x[5]):0}..{g.Max(x=>x[5]):0} deg";
        }

        // ------------------------------------------------------------------ install / verify / rollback
        static string Install()
        {
            var cfg=Config();var notes=new List<string>();var record=new List<object>();
            var prev=File.Exists(RecordPath)?JObject.Parse(File.ReadAllText(RecordPath)):null;
            var preexisting=new HashSet<string>((prev?["preexisting"] as JArray)?.Select(x=>(string)x)??new string[0]);
            foreach(var a in Actors())
            {
                var c=a.go.GetComponent<ArmPoseCorrector>();
                bool added=!c;
                if(!c)c=Undo.AddComponent<ArmPoseCorrector>(a.go);
                else if(prev==null)preexisting.Add(PathOf(a.go.transform));
                if(!Wire(c,a,notes)){notes.Add(a.key+": not installed");if(added)Object.DestroyImmediate(c);continue;}
                ApplyConfig(c,a,cfg);
                EditorUtility.SetDirty(c);
                if(c.handGrip&&c.weaponPose&&c.handGrip.weaponPose!=c.weaponPose)
                {
                    Undo.RecordObject(c.handGrip,"grip");c.handGrip.weaponPose=c.weaponPose;EditorUtility.SetDirty(c.handGrip);
                    if(PrefabUtility.IsPartOfPrefabInstance(c.handGrip))PrefabUtility.RecordPrefabInstancePropertyModifications(c.handGrip);
                    notes.Add("player: PlayerHandGrip.weaponPose wired (support hand relaxed while the pistol is lowered)");
                }
                if(PrefabUtility.IsPartOfPrefabInstance(c))PrefabUtility.RecordPrefabInstancePropertyModifications(c);
                if(a.key=="player")
                {
                    var origPath=Path.Combine(ArtDir,"player_weapon_original.json");
                    var prevW=ApplyPlayerWeapon(a,cfg);
                    // keep the first recorded originals (a re-install sees our own values)
                    if(!File.Exists(origPath))File.WriteAllText(origPath,new JObject{["playerWeapon"]=prevW.weapon,["playerGrip"]=prevW.grip}.ToString());
                    var pose=Object.FindAnyObjectByType<PlayerWeaponPose>(FindObjectsInactive.Include);var grip=BodyGrip(a);
                    foreach(var o in new Object[]{pose,grip})if(o){EditorUtility.SetDirty(o);if(PrefabUtility.IsPartOfPrefabInstance(o))PrefabUtility.RecordPrefabInstancePropertyModifications(o);}
                    notes.Add("player: PlayerWeaponPose/PlayerHandGrip values from characters.json (originals in player_weapon_original.json)");
                }
                record.Add(new{a.key,a.label,a.profile,path=PathOf(a.go.transform),fingers=c.rightFingers.Length==15});
            }
            int cams=Cameras(Actors());
            File.WriteAllText(RecordPath,JsonConvert.SerializeObject(new{utc=DateTime.UtcNow.ToString("O"),installed=record,preexisting},Formatting.Indented));
            var s=EditorSceneManager.GetActiveScene();EditorSceneManager.MarkSceneDirty(s);EditorSceneManager.SaveScene(s);
            return $"{record.Count} correctors installed ({string.Join(", ",record.Select(r=>JObject.FromObject(r)["key"]))}); {cams} review cameras; {string.Join("; ",notes)}";
        }

        /// cam_arms_<label>: full body, front three-quarter, player height. cam_arms_talk_<label>: the conversation framing
        /// (over the player's right shoulder, 2 m out) for each talking colonist.
        static int Cameras(List<Actor> actors)
        {
            var scene=EditorSceneManager.GetActiveScene();
            var old=scene.GetRootGameObjects().FirstOrDefault(g=>g.name==CamRootName);if(old)Object.DestroyImmediate(old);
            var root=new GameObject(CamRootName);int n=0;var specs=new List<object>();
            void Cam(string name,Vector3 pos,Vector3 look,float fov)
            {
                specs.Add(new{name,pos=new[]{R(pos.x),R(pos.y),R(pos.z)},target=new[]{R(look.x),R(look.y),R(look.z)},fov});
                var go=new GameObject(name);go.transform.SetParent(root.transform,false);
                go.transform.SetPositionAndRotation(pos,Quaternion.LookRotation(look-pos,Vector3.up));
                var k=go.AddComponent<Camera>();k.enabled=false;k.fieldOfView=fov;k.nearClipPlane=.05f;k.farClipPlane=400;n++;
            }
            // riding review views for native QA (ArmsReviewRig, development builds; switched on with setActive)
            foreach(var (name,off) in new[]{("front",new Vector3(0,1,3.4f)),("right",new Vector3(3.4f,1,0)),("left",new Vector3(-3.4f,1,0)),
                ("frontright",new Vector3(2.4f,1,2.4f)),("frontleft",new Vector3(-2.4f,1,2.4f)),("behind",new Vector3(0,1.1f,-3.4f)),("backright",new Vector3(2.4f,1.1f,-2.4f))})
            {
                var go=new GameObject("Arms review rig ["+name+"]");go.transform.SetParent(root.transform,false);
                var rig=go.AddComponent<ArmsReviewRig>();rig.offset=off;go.SetActive(false);
            }
            foreach(var a in actors)
            {
                var t=a.anim.transform;var f=Vector3.ProjectOnPlane(t.forward,Vector3.up).normalized;var r=Vector3.Cross(Vector3.up,f);
                var feet=t.position;string label=Safe(a.label);
                // front three-quarter, 3.4 m out, camera at 1.6 m looking at the hips/chest
                var dir=(f*.85f+r*.53f).normalized;
                Cam("cam_arms_"+label,feet+dir*3.4f+Vector3.up*1.6f,feet+Vector3.up*1.0f,40);
                if(a.go.GetComponentInParent<NpcAgent>())
                    Cam("cam_arms_talk_"+label,feet+f*2.0f-r*.45f+Vector3.up*1.62f,feet+Vector3.up*1.35f+r*.1f,38);
            }
            File.WriteAllText(Path.Combine(ArtDir,"review_cameras.json"),JsonConvert.SerializeObject(specs,Formatting.Indented));
            return n;
        }
        static string Safe(string s)=>new string(s.ToLowerInvariant().Select(ch=>char.IsLetterOrDigit(ch)?ch:'_').ToArray()).Trim('_');

        static string Verify()
        {
            var cfg=Config();var problems=new List<string>();var rows=new List<object>();
            foreach(var a in Actors())
            {
                var c=a.go.GetComponent<ArmPoseCorrector>();
                if(!c)
                {
                    var probe=a.go.AddComponent<ArmPoseCorrector>();bool humanoid=Wire(probe,a,new List<string>());Object.DestroyImmediate(probe);
                    if(humanoid)problems.Add(a.key+": no ArmPoseCorrector");else rows.Add(new{a.key,a.label,skipped="no arm bones (not a humanoid rig)"});
                    continue;
                }
                bool bound=c.Bind();if(!bound)problems.Add(a.key+": does not bind");
                if(!c.actor)problems.Add(a.key+": actor not wired");
                if(a.key=="player"&&!c.combat)problems.Add("player: combat not wired");
                var go=a.go;
                if(go.GetComponents<Component>().Any(x=>x==null))problems.Add(a.key+": missing script");
                string prefab=PrefabUtility.IsPartOfPrefabInstance(go)?(PrefabUtility.IsPrefabAssetMissing(go)?"MISSING":"ok"):"none";
                if(prefab=="MISSING")problems.Add(a.key+": prefab asset missing");
                // idle check: after correction the idle arms meet the profile's abduction ceiling (target + slack)
                float worst=float.NaN;
                if(bound&&a.anim.idle)
                {
                    // each idle sample: the arm's lean after the correction is within 2 degrees of what the profile asks for
                    var snap=Snap(go);float excess=0;
                    for(int i=0;i<8;i++)
                    {
                        Restore(snap);a.anim.idle.SampleAnimation(SampleHost(a),(i+.5f)/8*a.anim.idle.length);
                        var b=new[]{Measure(c,a,false)["abduction"],Measure(c,a,true)["abduction"]};
                        c.ApplyNow("idle");
                        var af=new[]{Measure(c,a,false)["abduction"],Measure(c,a,true)["abduction"]};
                        for(int k=0;k<2;k++)
                        {
                            float want=Mathf.Max(ArmPoseMath.PullDown(b[k],c.idle.abductionTarget,c.idle.abductionPull),Mathf.Min(b[k],c.idle.abductionMin));
                            excess=Mathf.Max(excess,af[k]-want);worst=float.IsNaN(worst)?af[k]:Mathf.Max(worst,af[k]);
                        }
                    }
                    Restore(snap);
                    if(c.weight>.5f&&excess>2)problems.Add($"{a.key}: idle arm lean {excess:0.0} deg over the profile");
                }
                rows.Add(new{a.key,a.label,bound,prefab,fingers=c.rightFingers.Length==15,weight=c.weight,idleAbductionWorst=R(worst)});
            }
            var root=EditorSceneManager.GetActiveScene().GetRootGameObjects().FirstOrDefault(g=>g.name==CamRootName);
            int cams=root?root.GetComponentsInChildren<Camera>(true).Count(k=>k.name.StartsWith("cam_arms_")):0;
            if(cams==0)problems.Add("no review cameras");
            int rigs=root?root.GetComponentsInChildren<ArmsReviewRig>(true).Length:0;
            if(rigs!=7)problems.Add($"{rigs} riding review rigs (want 7)");
            if(root&&root.GetComponentsInChildren<ArmsReviewRig>(true).Any(r=>r.gameObject.activeSelf))problems.Add("a riding review rig is left active");
            var res=new{pass=problems.Count==0,actors=rows.Count,cameras=cams,problems,rows};
            File.WriteAllText(Path.Combine(EvDir,"verify.json"),JsonConvert.SerializeObject(res,Formatting.Indented));
            return (problems.Count==0?"PASS":"FAIL")+$" {rows.Count} actors, {cams} cameras; "+string.Join("; ",problems);
        }

        static string Rollback()
        {
            var prev=File.Exists(RecordPath)?JObject.Parse(File.ReadAllText(RecordPath)):null;
            var keep=new HashSet<string>((prev?["preexisting"] as JArray)?.Select(x=>(string)x)??new string[0]);
            int n=0;
            foreach(var c in Object.FindObjectsByType<ArmPoseCorrector>(FindObjectsInactive.Include,FindObjectsSortMode.None))
            {
                if(keep.Contains(PathOf(c.transform)))continue;
                Object.DestroyImmediate(c,true);n++;
            }
            var origPath=Path.Combine(ArtDir,"player_weapon_original.json");
            var player=Actors().FirstOrDefault(x=>x.key=="player");
            if(player!=null&&File.Exists(origPath))
            {
                var o=JObject.Parse(File.ReadAllText(origPath));
                RestorePlayerWeapon(player,(o["playerWeapon"] as JObject,o["playerGrip"] as JObject));
                var pose=Object.FindAnyObjectByType<PlayerWeaponPose>(FindObjectsInactive.Include);var bg=BodyGrip(player);
                foreach(var x in new Object[]{pose,bg})if(x){EditorUtility.SetDirty(x);if(PrefabUtility.IsPartOfPrefabInstance(x))PrefabUtility.RecordPrefabInstancePropertyModifications(x);}
                File.Delete(origPath);
            }
            foreach(var g in Object.FindObjectsByType<PlayerHandGrip>(FindObjectsInactive.Include,FindObjectsSortMode.None))
                if(g.weaponPose){Undo.RecordObject(g,"grip");g.weaponPose=null;EditorUtility.SetDirty(g);if(PrefabUtility.IsPartOfPrefabInstance(g))PrefabUtility.RecordPrefabInstancePropertyModifications(g);}
            var root=EditorSceneManager.GetActiveScene().GetRootGameObjects().FirstOrDefault(g=>g.name==CamRootName);if(root)Object.DestroyImmediate(root);
            var s=EditorSceneManager.GetActiveScene();EditorSceneManager.MarkSceneDirty(s);EditorSceneManager.SaveScene(s);
            return $"{n} correctors removed, PlayerHandGrip.weaponPose cleared, cameras removed";
        }

        // ------------------------------------------------------------------ dump (-nographics review geometry)
        /// OBJ per actor, state and version (before/after) in the actor's own frame (feet at the origin, facing +Z),
        /// all skinned meshes and mesh renderers under the actor. Nothing is saved.
        static string Dump(string tag,string only,bool pistols)
        {
            var cfg=Config();var notes=new List<string>();var outDir=Path.Combine(EvDir,"dump",tag);Directory.CreateDirectory(outDir);
            var log=new List<string>();var index=new List<object>();
            foreach(var a in Actors())
            {
                if(only!=null&&!System.Text.RegularExpressions.Regex.IsMatch(a.key,only))continue;
                var c=Corrector(a,cfg,notes,out bool temp);if(!c)continue;
                var snap=Snap(a.go);var frame=a.anim.transform.worldToLocalMatrix;
                var poses=new List<(string name,string state,AnimationClip clip,float t)>();
                var clips=Clips(a);
                AnimationClip Of(string slot)=>clips.FirstOrDefault(x=>x.slot==slot).clip;
                if(Of("idle"))poses.Add(("idle","idle",Of("idle"),.3f));
                if(Of("talk"))foreach(var t in new[]{.15f,.45f,.75f})poses.Add(($"talk{t*100:00}","talk",Of("talk"),t));
                if(Of("walk"))foreach(var t in new[]{.0f,.25f,.5f})poses.Add(($"walk{t*100:00}","walk",Of("walk"),t));
                if(Of("run"))foreach(var t in new[]{.0f,.25f})poses.Add(($"run{t*100:00}","run",Of("run"),t));
                if(a.anim.humanoidAnimator)foreach(var x in clips)poses.Add((Safe(x.slot),x.state,x.clip,.3f));
                var combat=a.key=="player"?Object.FindAnyObjectByType<PlayerCombat>(FindObjectsInactive.Include):null;
                var wsnap=combat&&combat.heldPistol?Snap(combat.heldPistol):null;bool pistolWas=combat&&combat.heldPistol&&combat.heldPistol.activeSelf;
                if(combat&&combat.heldPistol&&(pistols||only!=null))foreach(var pp in PistolPoses){var pc=Of(pp.slot);if(pc)poses.Add((pp.name,pp.state,pc,pp.t));}
                foreach(var (name,state,clip,t) in poses)
                    foreach(var after in new[]{false,true})
                    {
                        Restore(snap);if(wsnap!=null){Restore(wsnap);combat.heldPistol.SetActive(false);}
                        var pistol=PistolPoses.FirstOrDefault(x=>x.name==name);
                        if(pistol.name!=null)PosePistol(a,c,clip,state,t,pistol.raise,after);
                        else{Sample(a,state,clip,t);if(after)c.ApplyNow(state);}
                        var sb=new StringBuilder();int baseIndex=1;var inv=CultureInfo.InvariantCulture;
                        void Add(string obj,Mesh mesh,Matrix4x4 m)
                        {
                            var v=mesh.vertices;sb.Append("o ").Append(obj).Append('\n');
                            foreach(var x in v){var p=m.MultiplyPoint3x4(x);sb.Append(string.Format(inv,"v {0:0.####} {1:0.####} {2:0.####}\n",p.x,p.y,p.z));}
                            for(int sm=0;sm<mesh.subMeshCount;sm++){if(mesh.GetTopology(sm)!=MeshTopology.Triangles)continue;var tr=mesh.GetTriangles(sm);for(int i=0;i<tr.Length;i+=3)sb.Append("f ").Append(tr[i]+baseIndex).Append(' ').Append(tr[i+1]+baseIndex).Append(' ').Append(tr[i+2]+baseIndex).Append('\n');}
                            baseIndex+=v.Length;
                        }
                        int k=0;
                        foreach(var smr in a.go.GetComponentsInChildren<SkinnedMeshRenderer>(false).Where(x=>x.enabled&&x.sharedMesh&&!IsLowLod(x)&&x.shadowCastingMode!=UnityEngine.Rendering.ShadowCastingMode.ShadowsOnly))
                        {
                            var baked=new Mesh();smr.BakeMesh(baked,true);
                            Add("body_"+(k++),baked,frame*smr.transform.localToWorldMatrix);Object.DestroyImmediate(baked);
                        }
                        foreach(var mr in a.go.GetComponentsInChildren<MeshRenderer>(false).Where(x=>x.enabled&&!IsLowLod(x)&&x.shadowCastingMode!=UnityEngine.Rendering.ShadowCastingMode.ShadowsOnly))
                        {
                            var mf=mr.GetComponent<MeshFilter>();if(!mf||!mf.sharedMesh||!mf.sharedMesh.isReadable&&false)continue;
                            Add("prop_"+(k++),mf.sharedMesh,frame*mr.transform.localToWorldMatrix);
                        }
                        var file=$"{Safe(a.label)}__{name}__{(after?"after":"before")}.obj";
                        File.WriteAllText(Path.Combine(outDir,file),sb.ToString());
                        index.Add(new{actor=Safe(a.label),pose=name,version=after?"after":"before",file});
                    }
                Restore(snap);if(wsnap!=null){Restore(wsnap);combat.heldPistol.SetActive(pistolWas);}
                log.Add($"{a.key}: {poses.Count} poses");
                if(temp)Object.DestroyImmediate(c);
            }
            File.WriteAllText(Path.Combine(outDir,"index.json"),JsonConvert.SerializeObject(index,Formatting.Indented));
            return string.Join("; ",log)+(notes.Count>0?" | "+string.Join("; ",notes):"");
        }
        /// Renderers that belong to a LODGroup's lower levels (only LOD0 is dumped).
        static bool IsLowLod(Renderer r)
        {
            var g=r.GetComponentInParent<LODGroup>();if(!g)return false;
            var lods=g.GetLODs();for(int i=1;i<lods.Length;i++)if(lods[i].renderers.Contains(r)&&!lods[0].renderers.Contains(r))return true;
            return false;
        }
    }
}
