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
    /// First-person rifle hands, 20 Nov 2026 (art/rifle_hands_20261120/README.md). The field rifle's view model was
    /// clip-driven: the weapon hung under the hold clip's right hand, which the third-person mount had put on the
    /// magazine well (RifleArmourInstall.GripFromButt 0.35 of the length from the butt is the magazine; the pistol grip
    /// is at about 0.20). This pass makes it weapon-driven like the pistol (PlayerFace20261003): the rifle on its own
    /// mount, the arms at camera-space anchors (hip and aim, ViewModelArmsRig), both arms IK'd (SupportHandIK with elbow
    /// poles) onto grip points measured on the rifle mesh (palm on the pistol grip, palm under the handguard), the
    /// fingers solved against the weapon into PlayerHandGrip.rifleRight/rifleLeft on the view-model arms.
    /// Nothing on the third-person body, the held rifle or the pistol view model is changed.
    /// Steps (-executeMethod AthenHill.Editor.RifleHandsPass20261120.RunBatch --steps a,b,c [--dry-run]):
    ///   install  (idempotent; restores the recorded clip-driven state first if already installed) previous.json is
    ///            written only from the clip-driven state
    ///   verify   -nographics: placement errors, wrist bend, finger penetration, unchanged reference values; verify.json
    ///   rollback restores the clip-driven rifle view model from art/rifle_hands_20261120/previous.json
    ///   capture  graphics: first-person frames (--shots rifle|rifle_armour|pistol|pistol_armour|orbit, --tag NAME)
    ///   report   logs the state and the rifle measurement, saves nothing
    /// </summary>
    public static class RifleHandsPass20261120
    {
        const string Scene="Assets/AthenHill/Scenes/AthenHill.unity";
        public const string MountName="RH weapon mount",ShootName="RH shooting grip",SupportName="RH support grip",RightIkName="RH right arm IK";
        static string Root=>Path.GetFullPath(Path.Combine(Application.dataPath,"../../.."));
        static string ArtDir=>Path.Combine(Root,"art/rifle_hands_20261120");
        static string EvDir=>Path.Combine(Root,"unity/evidence/showcase_phase2/20261120/rifle_hands");
        static string RecordPath=>Path.Combine(ArtDir,"previous.json");
        static bool dry;
        /// Install trace (kept when a step throws).
        static readonly List<string> trace=new List<string>();
        /// The view-model visuals are inactive in the saved scene; colliders, skinning and bounds need them active while measuring.
        static T WithVisuals<T>(FirstPersonViewModel vm,Func<T> f){var v=vm&&vm.visuals?vm.visuals:null;bool was=v&&v.activeSelf;if(v)v.SetActive(true);try{return f();}finally{if(v)v.SetActive(was);}}

        // ------------------------------------------------------------------ tunables (measured, see README)
        /// Pistol grip of FieldRifle.glb (art/rifle_hands_20261120/rifle_profile.py): centred 0.795 of the length from the
        /// muzzle end, from 5 to 35 % of the rifle's height (the magazine hangs at 0.55-0.68 from the muzzle).
        public static float GripFromMuzzle=.795f,GripBand=.03f;
        /// Palm centre on the grip: fraction of the rifle's height from the bottom, and metres behind the grip axis.
        public static float PalmHeight=.18f,PalmBack=.006f;
        /// Shooting-hand frame searched: finger direction pitched up from square-on to the grip (deg), roll about it (deg).
        public static float[] ShootPitches={0,10,20,30};
        public static float[] ShootRolls={0,15,30,45};
        /// Support hand: stations (fraction of the length from the muzzle) under the front receiver/handguard, fingers
        /// turned towards the right side (deg) and the palm rolled to face up-and-right (deg).
        public static float SupportFrom=.53f,SupportTo=.43f;
        public static float[] SupportYaws={45,60,75,90};
        public static float[] SupportRolls={0,15,30};
        /// Degrees of wrist score traded for 1 % of rifle length further forward.
        public static float SupportForwardBias=2.5f;
        /// Camera-space mid-shoulder points (x right, y up, z forward) and the torso blade (left shoulder forward).
        public static Vector3 HipShoulders=new Vector3(.07f,-.25f,-.04f),AimShoulders=new Vector3(.04f,-.22f,-.15f);
        public static float BladeYaw=25f,AimBladeYaw=30f;
        /// Searched jointly with the grips: torso blade (deg), mid-shoulder depth at the hip (m, the aim anchor keeps
        /// AimShoulders.z - HipShoulders.z behind it) and the right elbow direction.
        public static float[] BladeYaws={40};
        public static float[] HipMidZs={.06f,.10f,.14f};
        /// Aim anchor's mid-shoulder depth relative to the hip one (searched).
        public static float[] AimDzs={-.17f,-.23f};
        public static Vector3[] RightPoles={new Vector3(.3f,-.95f,-.1f)};
        /// Wrist-score penalty when an elbow shows on screen.
        public static float ElbowInViewPenalty=60f,StumpPenalty=150f;
        static float viewTanV=.577f;
        /// Elbow directions in camera space.
        public static Vector3 RightPole=new Vector3(.3f,-.95f,-.1f),LeftPole=new Vector3(-.45f,-.88f,-.15f);
        /// The arms follow this share of the weapon's sway/bob/recoil/draw (ViewModelArmsRig.followWeapon).
        public static float FollowWeapon=.6f;
        /// Share of the wrist twist moved into the forearm (SupportHandIK.twistShare) on both rifle arms.
        public static float TwistShare=.6f,LeftTwistShare=.6f;
        /// Hip mid-shoulder heights searched (m below the eye).
        public static float[] HipShoulderYs={-.25f,-.30f,-.34f};
        public static float[] HipShoulderXs={.12f,.17f,.22f};
        public static Vector3[] LeftPoles={new Vector3(-.75f,-.6f,-.2f),new Vector3(-.9f,-.3f,-.3f)};   // hero base (20 Nov 2026): the thicker forearm filled the lower centre with the elbow under the view (-.45,-.88,-.15 dropped)
        /// Aim-down-sights from the rifle's own sights (the old pose had the eye 5 cm below the top rail, so the sights sat
        /// well above the crosshair, and the butt plate 2.5 cm in front of the eye filled the lower view): the top rail
        /// levelled with the line of sight, the front sight post's tip on it, the butt this far behind the eye (cheek weld).
        public static float AimButtBehindEye=.015f;
        /// Hip framing (fix round, 21:33): the weapon origin (old grip point) in camera space, the bore converging on the
        /// crosshair this far ahead, and the cant (deg, negative = top to the left). The old hip pose had the rifle low and
        /// close (origin 0.13, -0.19, 0.40 with yaw -4), filling the lower right with the receiver, the hands out of frame.
        public static bool HipFromAim=true;
        public static Vector3 HipWeapon=new Vector3(.26f,-.24f,.58f);   // 20 Nov 13:30 (Carl: "we show too much of the gun"); was .17,-.15,.56
        public static float HipConverge=12f,HipCant=-6f;
        /// Arms follow while lowered in the draw slide (ViewModelArmsRig.drawFollow).
        public static float DrawFollow=1f;
        /// Front sight post and top rail of FieldRifle.glb (fractions of the length from the muzzle; rifle_profile.py).
        public static float PostFrom=.06f,PostTo=.11f,RailFrom=.55f,RailTo=.78f;
        /// Wrist-score penalty per finger that already overlaps the weapon with the hand open (it would have to bend backwards).
        public static float FingerInsidePenalty=60f;
        /// Finger capsule radii for the solve: the MPFB finger plus a 2 mm glove allowance.
        public static float FingerRadius=.0145f,ThumbRadius=.0165f;   // hero base hands + 2 mm (20 Nov 2026); MPFB: .0102 / .0115
        const int TempLayer=31;
        static readonly string[] Digits={"index","middle","ring","pinky","thumb"};

        public static void RunBatch()
        {
            var a=Environment.GetCommandLineArgs();
            string Arg(string k,string def){int i=Array.IndexOf(a,k);return i>=0&&i+1<a.Length?a[i+1]:def;}
            var steps=Arg("--steps","verify").Split(',').Select(s=>s.Trim()).Where(s=>s.Length>0).ToArray();
            dry=a.Contains("--dry-run");
            Vector3? Vec(string k){var t=Arg(k,null);if(t==null)return null;var v=t.Split(',').Select(x=>float.Parse(x,CultureInfo.InvariantCulture)).ToArray();return new Vector3(v[0],v[1],v[2]);}
            if(Vec("--hipw") is Vector3 hw)HipWeapon=hw;
            if(Arg("--hipcant",null) is string hc)HipCant=float.Parse(hc,CultureInfo.InvariantCulture);
            int code=0;var log=new List<string>();
            try
            {
                Directory.CreateDirectory(ArtDir);Directory.CreateDirectory(EvDir);
                if(EditorSceneManager.GetActiveScene().path!=Scene)EditorSceneManager.OpenScene(Scene,OpenSceneMode.Single);
                foreach(var s in steps)
                {
                    string r=s switch{"install"=>Install(),"verify"=>Verify(),"rollback"=>Rollback(),"capture"=>Capture(Arg("--shots","rifle"),Arg("--tag","after")),"report"=>Report(),"rebaseline"=>Rebaseline(Arg("--keys",null)),"dump"=>Dump(Arg("--tag","dump")),
                        _=>throw new ArgumentException("unknown step "+s)};
                    log.Add("["+s+"] "+r);Debug.Log("RifleHandsPass20261120 "+s+"\n"+r);
                }
            }
            catch(Exception e){Debug.LogException(e);log.Add("FAILED "+e);if(trace.Count>0)log.Add("trace:\n"+string.Join("\n",trace));code=1;}
            try{File.WriteAllText(Path.Combine(EvDir,string.Join("_",steps)+(dry?"-dry":"")+"-result.txt"),string.Join("\n",log)+"\n");}catch(Exception e){Debug.LogException(e);}
            EditorApplication.Exit(code);
        }

        // ------------------------------------------------------------------ helpers
        static PlayerCombat Combat(){var c=Object.FindAnyObjectByType<PlayerCombat>(FindObjectsInactive.Include);if(!c)throw new InvalidOperationException("No PlayerCombat");return c;}
        static PlayerMotor Motor(){var m=Object.FindAnyObjectByType<PlayerMotor>(FindObjectsInactive.Include);if(!m)throw new InvalidOperationException("No PlayerMotor");return m;}
        static FirstPersonViewModel Rvm(PlayerCombat c){var vm=c.rifleViewModel;if(!vm||!vm.rifle||!vm.pistol)throw new InvalidOperationException("No rifle view model");return vm;}
        static Transform ArmsOf(FirstPersonViewModel vm){var parent=vm.visuals?vm.visuals.transform:vm.transform;return parent.Cast<Transform>().FirstOrDefault(t=>t.name=="Player arms rig")??throw new InvalidOperationException("no Player arms rig under "+vm.name);}
        /// The rifle's vm.pistol is a pivot under the weapon root ("View model rifle").
        static Transform WeaponOf(FirstPersonViewModel vm)=>vm.rifle?vm.pistol.parent:vm.pistol;
        static Transform Bone(Transform root,string n)=>root.GetComponentsInChildren<Transform>(true).FirstOrDefault(x=>x.name==n)??throw new InvalidOperationException("no bone "+n+" under "+root.name);
        static bool Installed(FirstPersonViewModel vm)=>vm.rig&&vm.rig.name==MountName;
        static string F(Vector3 v)=>string.Format(CultureInfo.InvariantCulture,"{0:0.####},{1:0.####},{2:0.####}",v.x,v.y,v.z);
        static string F(Quaternion q)=>string.Format(CultureInfo.InvariantCulture,"{0:0.#####},{1:0.#####},{2:0.#####},{3:0.#####}",q.x,q.y,q.z,q.w);
        static float[] A(Vector3 v)=>new[]{v.x,v.y,v.z};
        static float[] A(Quaternion q)=>new[]{q.x,q.y,q.z,q.w};
        static Vector3 V(float[] a)=>new Vector3(a[0],a[1],a[2]);
        static Quaternion Q(float[] a)=>new Quaternion(a[0],a[1],a[2],a[3]);
        static string PathOf(Transform t,Transform root){if(!t)return null;var parts=new List<string>();for(var x=t;x&&x!=root;x=x.parent)parts.Add(x.name);parts.Reverse();return string.Join("/",parts);}
        static Transform Find(Transform root,string path)=>string.IsNullOrEmpty(path)?root:root.Find(path);
        static void SaveAll(){if(dry)return;var s=EditorSceneManager.GetActiveScene();EditorSceneManager.MarkSceneDirty(s);EditorSceneManager.SaveScene(s);AssetDatabase.SaveAssets();}
        static IEnumerable<MeshFilter> WeaponMeshes(Transform root)
        {
            bool Shown(Transform t){for(var x=t;x&&x!=root;x=x.parent)if(!x.gameObject.activeSelf||x.name==FPGripPass.HandsName)return false;return true;}
            return root.GetComponentsInChildren<MeshFilter>(true).Where(m=>m.sharedMesh&&m.GetComponent<Renderer>()&&!m.GetComponentInParent<MuzzleFlash>(true)&&Shown(m.transform));
        }

        // ------------------------------------------------------------------ record (rollback)
        class Rec
        {
            public string utc,weaponParent,vmRig,ikRifleGrip,ikPistolGrip;
            public float[] weaponLocalPos,weaponLocalRot,weaponLocalScale,aimOffset,aimEuler,hipOffset,hipEuler,ikPole;
            public float ikRifleWeight,ikPistolWeight,ikTwistShare;
            public float[] ikRestHandLocal;
            public float[][] rifleRight,rifleLeft;
            public bool hadArmsRig;
            /// Every transform under the view model (path -> local position, rotation, scale): the arms rig and its bones are
            /// posed by the install (hold clip, IK), so rollback puts them back exactly.
            public Dictionary<string,float[]> locals;
        }
        static Rec RecordOf(FirstPersonViewModel vm)
        {
            var arms=ArmsOf(vm);var w=WeaponOf(vm);var ik=arms.GetComponent<SupportHandIK>();var g=arms.GetComponent<PlayerHandGrip>();
            return new Rec{utc=DateTime.UtcNow.ToString("O"),weaponParent=PathOf(w.parent,vm.transform),vmRig=PathOf(vm.rig,vm.transform),
                weaponLocalPos=A(w.localPosition),weaponLocalRot=A(w.localRotation),weaponLocalScale=A(w.localScale),aimOffset=A(vm.aimOffset),aimEuler=A(vm.aimEuler),hipOffset=A(vm.hipOffset),hipEuler=A(vm.hipEuler),
                ikRifleGrip=ik?PathOf(ik.rifleGrip,vm.transform):null,ikPistolGrip=ik?PathOf(ik.pistolGrip,vm.transform):null,ikRifleWeight=ik?ik.rifleWeight:0,ikPistolWeight=ik?ik.pistolWeight:0,ikPole=ik?A(ik.poleHint):null,ikTwistShare=ik?ik.twistShare:0,ikRestHandLocal=ik?A(ik.restHandLocal):null,
                rifleRight=g?g.rifleRight.Select(A).ToArray():null,rifleLeft=g?g.rifleLeft.Select(A).ToArray():null,hadArmsRig=vm.GetComponent<ViewModelArmsRig>(),
                locals=vm.GetComponentsInChildren<Transform>(true).Where(t=>t!=vm.transform).GroupBy(t=>PathOf(t,vm.transform)).ToDictionary(x=>x.Key,x=>{var t=x.First();return A(t.localPosition).Concat(A(t.localRotation)).Concat(A(t.localScale)).ToArray();})};
        }
        static void Restore(FirstPersonViewModel vm,Rec r)
        {
            if(r.hadArmsRig)throw new InvalidOperationException("record says the rifle view model already had a ViewModelArmsRig: not a clip-driven record");
            var arms=ArmsOf(vm);var w=WeaponOf(vm);
            var parent=Find(vm.transform,r.weaponParent)??throw new InvalidOperationException("recorded weapon parent missing: "+r.weaponParent);
            var mount=Installed(vm)?vm.rig:null;
            w.SetParent(parent,false);w.localPosition=V(r.weaponLocalPos);w.localRotation=Q(r.weaponLocalRot);w.localScale=V(r.weaponLocalScale);
            vm.rig=Find(vm.transform,r.vmRig)??throw new InvalidOperationException("recorded rig missing: "+r.vmRig);
            if(mount&&mount!=vm.rig)Object.DestroyImmediate(mount.gameObject);
            vm.aimOffset=V(r.aimOffset);if(r.aimEuler!=null)vm.aimEuler=V(r.aimEuler);if(r.hipOffset!=null)vm.hipOffset=V(r.hipOffset);if(r.hipEuler!=null)vm.hipEuler=V(r.hipEuler);
            foreach(var x in arms.GetComponentsInChildren<Transform>(true).Where(y=>y.name==RightIkName).ToArray())Object.DestroyImmediate(x.gameObject);
            foreach(var x in w.GetComponentsInChildren<Transform>(true).Where(y=>y.name==ShootName||y.name==SupportName).ToArray())Object.DestroyImmediate(x.gameObject);
            var ar=vm.GetComponent<ViewModelArmsRig>();if(ar)Object.DestroyImmediate(ar);
            var ik=arms.GetComponent<SupportHandIK>();
            if(ik)
            {
                ik.rifleGrip=r.ikRifleGrip==null?null:Find(vm.transform,r.ikRifleGrip);ik.pistolGrip=r.ikPistolGrip==null?null:Find(vm.transform,r.ikPistolGrip);
                ik.rifleWeight=r.ikRifleWeight;ik.pistolWeight=r.ikPistolWeight;ik.poleHint=r.ikPole!=null?V(r.ikPole):Vector3.zero;ik.twistShare=r.ikTwistShare;ik.restHandLocal=r.ikRestHandLocal!=null?Q(r.ikRestHandLocal):Quaternion.identity;EditorUtility.SetDirty(ik);
            }
            var g=arms.GetComponent<PlayerHandGrip>();
            if(g&&r.rifleRight!=null){g.rifleRight=r.rifleRight.Select(Q).ToArray();g.rifleLeft=r.rifleLeft.Select(Q).ToArray();EditorUtility.SetDirty(g);}
            if(r.locals!=null)foreach(var kv in r.locals)
            {
                var t=vm.transform.Find(kv.Key);if(!t)continue;var v=kv.Value;
                t.localPosition=new Vector3(v[0],v[1],v[2]);t.localRotation=new Quaternion(v[3],v[4],v[5],v[6]);t.localScale=new Vector3(v[7],v[8],v[9]);
            }
            EditorUtility.SetDirty(vm);
        }

        /// Values this pass must not change (the pistol view model, the body, the held rifle, ballistics and pose
        /// settings), as text, compared before and after install.
        static Dictionary<string,string> Reference(PlayerCombat combat)
        {
            var d=new Dictionary<string,string>();var inv=CultureInfo.InvariantCulture;
            void T(string k,Transform t){if(t){d[k+".localPos"]=F(t.localPosition);d[k+".localRot"]=F(t.localRotation);d[k+".localScale"]=F(t.localScale);}else d[k]="null";}
            string Arr(Quaternion[] q)=>q==null?"null":q.Length+":"+string.Join(";",q.Select(F));
            var pvm=combat.viewModel;
            if(pvm)
            {
                d["pvm.offsets"]=$"{F(pvm.hipOffset)}|{F(pvm.hipEuler)}|{F(pvm.aimOffset)}|{F(pvm.aimEuler)}|{F(pvm.holsterOffset)}|{F(pvm.holsterEuler)}";
                d["pvm.motion"]=string.Format(inv,"{0}|{1}|{2}|{3}|{4}|{5}|{6}|{7}|{8}",pvm.swayAmount,pvm.swayRotation,pvm.swaySmoothing,pvm.bobAmount,pvm.recoilBack,pvm.recoilPitch,pvm.recoilReturn,pvm.drawSeconds,pvm.aimSeconds);
                var ar=pvm.GetComponent<ViewModelArmsRig>();d["pvm.armsRig"]=ar?$"{F(ar.anchorPosition)}|{F(ar.anchorRotation)}|{ar.aimAnchor}|{ar.followWeapon}":"none";
                T("pvm.rig",pvm.rig);T("pvm.pistol",pvm.pistol);T("pvm.muzzle",pvm.muzzle);
                foreach(var ik in pvm.GetComponentsInChildren<SupportHandIK>(true))d["pvm.ik."+ik.name+"."+(ik.upper?ik.upper.name:"")]=$"{(ik.pistolGrip?F(ik.pistolGrip.localPosition)+F(ik.pistolGrip.localRotation):"-")}|{F(ik.poleHint)}|{ik.pistolWeight}|{ik.rifleWeight}";
                var pg=pvm.GetComponentInChildren<PlayerHandGrip>(true);if(pg){d["pvm.grip.pistolRight"]=Arr(pg.pistolRight);d["pvm.grip.pistolLeft"]=Arr(pg.pistolLeft);}
                var pm=pvm.GetComponentInChildren<ViewModelArmourMirror>(true);d["pvm.mirror"]=pm?pm.mirrors.Length+":"+string.Join(",",pm.mirrors.Select(m=>m?m.name:"null")):"none";
            }
            var rvm=combat.rifleViewModel;
            if(rvm)
            {
                d["rvm.offsets.unchanged"]=$"{F(rvm.holsterOffset)}|{F(rvm.holsterEuler)}";
                d["rvm.motion"]=string.Format(inv,"{0}|{1}|{2}|{3}|{4}|{5}|{6}|{7}|{8}",rvm.swayAmount,rvm.swayRotation,rvm.swaySmoothing,rvm.bobAmount,rvm.recoilBack,rvm.recoilPitch,rvm.recoilReturn,rvm.drawSeconds,rvm.aimSeconds);
                var w=WeaponOf(rvm);
                d["rvm.muzzleInWeapon"]=rvm.muzzle?F(w.InverseTransformPoint(rvm.muzzle.position)):"null";
                d["rvm.pivotInWeapon"]=F(w.InverseTransformPoint(rvm.pistol.position))+"|"+F(Quaternion.Inverse(w.rotation)*rvm.pistol.rotation);
                d["rvm.flashInWeapon"]=rvm.flash?PathOf(rvm.flash.transform,w):"null";
                var rm=rvm.GetComponentInChildren<ViewModelArmourMirror>(true);d["rvm.mirror"]=rm?rm.mirrors.Length+":"+string.Join(",",rm.mirrors.Select(m=>m?m.name:"null"))+" on "+rm.name:"none";
                d["rvm.holdClip"]=rvm.holdClip?rvm.holdClip.name:"null";
            }
            T("body.heldRifle",combat.heldRifle?combat.heldRifle.transform:null);T("body.rifleMuzzle",combat.rifleMuzzle);
            var hs=combat.heldRifle?combat.heldRifle.GetComponentsInChildren<Transform>(true).FirstOrDefault(t=>t.name=="Support grip"):null;T("body.heldRifle.SupportGrip",hs);
            T("body.heldPistol",combat.heldPistol?combat.heldPistol.transform:null);T("body.muzzlePoint",combat.muzzlePoint);
            var bg=combat.GetComponent<PlayerHandGrip>();if(bg){d["body.grip.rifleRight"]=Arr(bg.rifleRight);d["body.grip.rifleLeft"]=Arr(bg.rifleLeft);d["body.grip.pistolRight"]=Arr(bg.pistolRight);}
            var bik=combat.GetComponent<SupportHandIK>();if(bik)d["body.ik"]=$"{(bik.rifleGrip?bik.rifleGrip.name:"-")}|{bik.rifleWeight}|{F(bik.poleHint)}|{(bik.scaleByAim?"aim":"-")}";
            var pose=combat.GetComponent<PlayerWeaponPose>();
            if(pose)d["body.pose"]=string.Format(inv,"{0}|{1}|{2}|{3}|{4}|{5}|{6}|{7}|{8}",pose.carryPitch,pose.carryAlign,pose.rifleCarryPitch,pose.rifleCarryAlign,pose.rifleBarrelAlign,pose.barrelAlign,pose.recoilPitch,pose.recoilReturn,pose.rifleAimClip?pose.rifleAimClip.name:"-");
            return d;
        }

        // ------------------------------------------------------------------ posing
        public struct Frame
        {
            public float aim,draw,recoil,bob,bobPhase;public Vector2 sway;
            public static Frame Hip=>new Frame{draw=1};
        }
        /// FirstPersonViewModel.LateUpdate's placement (pose, bob, sway, recoil, draw) with explicit inputs, then the arms
        /// (ViewModelArmsRig), finger grips and both arm IKs: the per-frame work of the view model, in edit mode.
        public static void Pose(FirstPersonViewModel vm,Vector3 camPos,Quaternion camRot,Frame f)
        {
            if(vm.holdClip&&vm.animationSource)vm.holdClip.SampleAnimation(vm.animationSource.gameObject,vm.holdClip.length*.3f);
            var bobOffset=new Vector3(Mathf.Cos(f.bobPhase)*f.bob,Mathf.Abs(Mathf.Sin(f.bobPhase))*-f.bob,0);
            float r=f.recoil*f.recoil*(3-2*f.recoil);
            var offset=Vector3.Lerp(vm.hipOffset,vm.aimOffset,f.aim)+bobOffset+new Vector3(f.sway.x*vm.swayAmount,f.sway.y*vm.swayAmount,0)+Vector3.back*vm.recoilBack*r;
            var euler=Vector3.Lerp(vm.hipEuler,vm.aimEuler,f.aim)+new Vector3(-vm.recoilPitch*r+f.sway.y*vm.swayRotation,f.sway.x*vm.swayRotation,f.sway.x*vm.swayRotation*.5f);
            float d=f.draw*f.draw*(3-2*f.draw);
            offset=Vector3.Lerp(vm.holsterOffset,offset,d);euler=Vector3.Lerp(vm.holsterEuler,euler,d);
            var target=Matrix4x4.TRS(camPos+camRot*offset,camRot*Quaternion.Euler(euler),Vector3.one);
            var rel=vm.rig.worldToLocalMatrix*vm.pistol.localToWorldMatrix;var place=target*rel.inverse;
            vm.rig.SetPositionAndRotation(place.GetColumn(3),place.rotation);
            var ar=vm.GetComponent<ViewModelArmsRig>();if(ar&&ar.arms&&ar.arms!=vm.rig)ar.Place(camPos,camRot,f.aim,f.draw);
            var grip=vm.GetComponentInChildren<PlayerHandGrip>(true);if(grip)grip.PreviewGrip(1,1,vm.rifle);
            foreach(var ik in vm.GetComponentsInChildren<SupportHandIK>(true)){var t=vm.rifle?ik.rifleGrip:ik.pistolGrip;if(t)ik.Solve(t,1);}   // once, as SupportHandIK.LateUpdate does
        }

        // ------------------------------------------------------------------ wrist measure
        /// Wrist deviation from the arms' bind pose: swing (bend) and twist about the forearm axis, degrees.
        class Wrist
        {
            readonly Quaternion restRel;readonly Vector3 axis;
            public Quaternion RestRel=>restRel;
            public Wrist(SkinnedMeshRenderer smr,string lowerName,string handName)
            {
                var bones=smr.bones;var bp=smr.sharedMesh.bindposes;
                int li=Array.FindIndex(bones,b=>b&&b.name==lowerName),hi=Array.FindIndex(bones,b=>b&&b.name==handName);
                if(li<0||hi<0)throw new InvalidOperationException("bind pose: no "+lowerName+"/"+handName);
                var ml=bp[li].inverse;var mh=bp[hi].inverse;
                var rl=ml.rotation;var rh=mh.rotation;
                restRel=Quaternion.Inverse(rl)*rh;axis=(Quaternion.Inverse(rl)*((Vector3)mh.GetColumn(3)-(Vector3)ml.GetColumn(3))).normalized;
            }
            public (float swing,float twist) Measure(Transform lower,Transform hand)
            {
                var q=(Quaternion.Inverse(lower.rotation)*hand.rotation)*Quaternion.Inverse(restRel);
                var v=new Vector3(q.x,q.y,q.z);var p=Vector3.Dot(v,axis)*axis;
                var tw=new Quaternion(p.x,p.y,p.z,q.w);float n=Mathf.Sqrt(tw.x*tw.x+tw.y*tw.y+tw.z*tw.z+tw.w*tw.w);
                if(n<1e-6f)tw=Quaternion.identity;else tw=new Quaternion(tw.x/n,tw.y/n,tw.z/n,tw.w/n);
                var sw=q*Quaternion.Inverse(tw);
                return (Quaternion.Angle(Quaternion.identity,sw),Quaternion.Angle(Quaternion.identity,tw));
            }
        }
        static SkinnedMeshRenderer ArmsMesh(Transform arms)=>arms.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(s=>!s.name.StartsWith("FP armour")&&s.bones.Any(b=>b&&b.name=="RightHand")).OrderByDescending(s=>s.sharedMesh?s.sharedMesh.vertexCount:0).FirstOrDefault()??throw new InvalidOperationException("no arms mesh");

        /// Hand frame from the bones (PlayerFace20261003.HandFrame): finger direction, palm normal, palm centre, middle
        /// knuckle, in the hand bone's rotation frame (world-scaled offsets). Fingers must be at rest.
        static (Vector3 d,Vector3 n,Vector3 palm,Vector3 knuckle) HandFrame(Transform hand,Transform[] fingers,string side)
        {
            var mid=fingers.First(t=>t.name=="middle_01_"+side);var mid3=fingers.First(t=>t.name=="middle_03_"+side);
            var dW=(mid.position-hand.position).normalized;
            var q0=mid.localRotation;var t0=mid3.position;mid.localRotation=q0*Quaternion.Euler(30,0,0);var t1=mid3.position;mid.localRotation=q0;
            var nW=Vector3.ProjectOnPlane(t1-t0,dW).normalized;var inv=Quaternion.Inverse(hand.rotation);
            return (inv*dW,inv*nW,inv*(Vector3.Lerp(hand.position,mid.position,.55f)-hand.position),inv*(mid.position-hand.position));
        }

        /// Each digit curls about its local X joint by joint until the finger touches the colliders (PlayerFace20261003.SolveFingers,
        /// with the glove allowance in the radii).
        static Quaternion[] SolveFingers(Transform[] f,Quaternion[] rest,int mask)=>SolveFingers(f,rest,mask,null);
        /// With a thumb target (world point), the thumb's joints turn about whichever local axis (of the six) brings the
        /// thumb tip towards it fastest, until it touches or stops getting closer (the thumb opposes; the other fingers
        /// only curl about X).
        static Quaternion[] SolveFingers(Transform[] f,Quaternion[] rest,int mask,Vector3? thumbTarget)
        {
            for(int i=0;i<f.Length;i++)f[i].localRotation=rest[i];
            for(int d=0;d<5;d++)
            {
                if(d*3+2>=f.Length)break;
                bool thumb=f[d*3].name.StartsWith("thumb");
                float r=thumb?ThumbRadius:FingerRadius;
                float[] max=thumb?new[]{40f,60f,60f}:new[]{90f,100f,80f};
                var ch=new[]{f[d*3],f[d*3+1],f[d*3+2]};var rs=new[]{rest[d*3],rest[d*3+1],rest[d*3+2]};
                bool Hit(int k)
                {
                    Physics.SyncTransforms();
                    var tip=ch[2].position+(ch[2].position-ch[1].position)*.85f;
                    var p=new[]{ch[0].position,ch[1].position,ch[2].position,tip};
                    for(int s=k;s<3;s++)if(Physics.CheckCapsule(p[s],p[s+1],r,mask,QueryTriggerInteraction.Collide))return true;
                    return false;
                }
                if(thumb&&thumbTarget.HasValue)
                {
                    var tgt=thumbTarget.Value;Vector3[] axes={Vector3.right,Vector3.left,Vector3.up,Vector3.down,Vector3.forward,Vector3.back};
                    float TipDist(){var tip=ch[2].position+(ch[2].position-ch[1].position)*.85f;return (tip-tgt).magnitude;}
                    for(int k=0;k<3;k++)
                    {
                        var q0=ch[k].localRotation;bool inside=Hit(k);
                        Vector3 best=Vector3.right;float bestScore=float.MaxValue;
                        foreach(var ax in axes)
                        {
                            ch[k].localRotation=q0*Quaternion.AngleAxis(6,ax);
                            float sc=inside?(Hit(k)?1:0)*10-TipDist():TipDist();   // inside: an axis that frees it (and moves away); else: towards the target
                            if(sc<bestScore){bestScore=sc;best=ax;}
                        }
                        ch[k].localRotation=q0;float a=0,lim=inside?40:(k==0?70:60),last=TipDist();
                        while(a<lim)
                        {
                            a+=2;ch[k].localRotation=q0*Quaternion.AngleAxis(a,best);
                            if(inside){if(!Hit(k))break;continue;}
                            float dd=TipDist();
                            if(Hit(k)||dd>last-1e-4f){a-=2;ch[k].localRotation=q0*Quaternion.AngleAxis(a,best);break;}
                            last=dd;
                        }
                    }
                    continue;
                }
                for(int k=0;k<3;k++)
                {
                    float a=0;
                    if(Hit(k)){while(a>-40&&Hit(k)){a-=2;ch[k].localRotation=rs[k]*Quaternion.Euler(a,0,0);}}
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

        /// Fingers (not the thumb) whose open rest pose already overlaps the weapon colliders.
        static int FingersInside(Transform[] f,int mask)
        {
            Physics.SyncTransforms();int n=0;
            for(int d=0;d*3+2<f.Length;d++)
            {
                if(f[d*3].name.StartsWith("thumb"))continue;
                var ch=new[]{f[d*3],f[d*3+1],f[d*3+2]};var tip=ch[2].position+(ch[2].position-ch[1].position)*.85f;
                var p=new[]{ch[0].position,ch[1].position,ch[2].position,tip};
                for(int s=0;s<3;s++)if(Physics.CheckCapsule(p[s],p[s+1],.008f,mask,QueryTriggerInteraction.Collide)){n++;break;}
            }
            return n;
        }

        /// Finger segments overlapping the weapon by more than (radius) at the current pose, as "finger_joint" names.
        static List<string> Penetrations(Transform[] f,float radius,int mask)
        {
            Physics.SyncTransforms();var hits=new List<string>();
            for(int d=0;d*3+2<f.Length;d++)
            {
                var ch=new[]{f[d*3],f[d*3+1],f[d*3+2]};var tip=ch[2].position+(ch[2].position-ch[1].position)*.85f;
                var p=new[]{ch[0].position,ch[1].position,ch[2].position,tip};
                for(int s=0;s<3;s++)if(Physics.CheckCapsule(p[s],p[s+1],radius,mask,QueryTriggerInteraction.Collide))hits.Add(ch[s].name);
            }
            return hits;
        }

        /// Temporary mesh colliders on the weapon meshes (children, so they follow the weapon); destroy the returned list.
        static List<GameObject> WeaponColliders(Transform weapon)
        {
            var list=new List<GameObject>();
            foreach(var mf in WeaponMeshes(weapon).ToArray())
            {
                var g=new GameObject("__rh collider"){layer=TempLayer,hideFlags=HideFlags.DontSave};g.transform.SetParent(mf.transform,false);
                g.AddComponent<MeshCollider>().sharedMesh=mf.sharedMesh;list.Add(g);
            }
            Physics.SyncTransforms();return list;
        }

        // ------------------------------------------------------------------ rifle measurement (weapon-root local frame: +Z barrel, +Y up, +X right)
        class RifleShape
        {
            public Vector3 min,max;public float len,height;
            public Vector3 gripTop,gripBottom,gripAxisDown;public float gripDepth,gripWidth;public int gripCount;
            public Vector3[] pts;
            public float FromMuzzle(Vector3 p)=>(max.z-p.z)/len;
            public float H(Vector3 p)=>(p.y-min.y)/height;
            public float Z(float fromMuzzle)=>max.z-fromMuzzle*len;
        }
        static RifleShape Measure(Transform weapon,FirstPersonViewModel vm)
        {
            var s=new RifleShape();
            s.pts=WeaponMeshes(weapon).SelectMany(mf=>mf.sharedMesh.vertices.Select(v=>weapon.InverseTransformPoint(mf.transform.TransformPoint(v)))).ToArray();
            s.min=s.pts.Aggregate(Vector3.Min);s.max=s.pts.Aggregate(Vector3.Max);s.len=s.max.z-s.min.z;s.height=s.max.y-s.min.y;
            if(vm.muzzle){var mz=weapon.InverseTransformPoint(vm.muzzle.position);if(mz.z<s.max.z-.05f*s.len)throw new InvalidOperationException("muzzle not at the +Z end of the weapon frame: "+F(mz)+" bounds "+F(s.min)+".."+F(s.max));}
            Vector3 Centre(float h0,float h1,out int n,out float depth,out float width)
            {
                var sel=s.pts.Where(p=>Mathf.Abs(s.FromMuzzle(p)-GripFromMuzzle)<GripBand&&s.H(p)>=h0&&s.H(p)<h1).ToArray();n=sel.Length;
                if(n==0){depth=width=0;return Vector3.zero;}
                var a=sel.Aggregate(Vector3.Min);var b=sel.Aggregate(Vector3.Max);depth=b.z-a.z;width=b.x-a.x;return (a+b)/2;
            }
            s.gripBottom=Centre(.05f,.18f,out var n0,out _,out _);s.gripTop=Centre(.22f,.35f,out var n1,out s.gripDepth,out s.gripWidth);
            s.gripCount=n0+n1;
            if(n0<20||n1<20)throw new InvalidOperationException($"no pistol grip found at {GripFromMuzzle} of the length from the muzzle ({n0}/{n1} vertices): re-measure with rifle_profile.py");
            s.gripAxisDown=(s.gripBottom-s.gripTop).normalized;
            if(s.gripAxisDown.y>-.7f)throw new InvalidOperationException("pistol grip axis not downward: "+F(s.gripAxisDown));
            return s;
        }

        // ------------------------------------------------------------------ install
        static string Install()
        {
            var combat=Combat();var vm=Rvm(combat);var log=new List<string>();
            Rec rec=null;
            if(Installed(vm))
            {
                if(!File.Exists(RecordPath))throw new InvalidOperationException("installed but no "+RecordPath);
                rec=JsonConvert.DeserializeObject<Rec>(File.ReadAllText(RecordPath));Restore(vm,rec);log.Add("previous install undone from previous.json");
            }
            else
            {
                if(vm.GetComponent<ViewModelArmsRig>())throw new InvalidOperationException("rifle view model has a ViewModelArmsRig but no "+MountName+": unknown state, not touching it");
                rec=RecordOf(vm);
                if(!dry)File.WriteAllText(RecordPath,JsonConvert.SerializeObject(rec,Formatting.Indented));
                log.Add("clip-driven state recorded"+(dry?" (dry run: not written)":" in previous.json"));
            }
            var before=Reference(combat);
            var applied=WithVisuals(vm,()=>Apply(combat,vm));log.Add(applied);File.WriteAllText(Path.Combine(EvDir,"install-trace"+(dry?"-dry":"")+".txt"),applied+"\n");
            var after=Reference(combat);
            var changed=before.Keys.Union(after.Keys).Where(k=>!before.TryGetValue(k,out var x)||!after.TryGetValue(k,out var y)||x!=y).ToArray();
            if(changed.Length>0)throw new InvalidOperationException("install changed reference values it must not touch: "+string.Join(", ",changed.Select(k=>k+" "+(before.TryGetValue(k,out var x)?x:"-")+" -> "+(after.TryGetValue(k,out var y)?y:"-"))));
            File.WriteAllText(Path.Combine(EvDir,"reference.json"),JsonConvert.SerializeObject(after,Formatting.Indented));
            log.Add($"reference values unchanged ({after.Count} keys, reference.json)");
            if(combat.viewModel)log.Add(FixPistolMirror(combat.viewModel));
            SaveAll();
            return string.Join("\n",log);
        }

        // ------------------------------------------------------------------ pistol armour mirror
        /// Found 20 Nov 2026: PlayerFace20261003.ArmourMirror built the pistol's glove/arm-guard copies under vm.rig, which
        /// for the weapon-driven pistol is its Weapon mount, so every bone fell back to the mount: worn gloves or arm guards
        /// showed as a rigid bind-pose shell on the pistol in first person. Re-skins those copies onto the pistol arms'
        /// bones (same as the rifle's copies). The broken state is recorded in previous_pistol_mirror.json for rollback.
        static string PistolMirrorPath=>Path.Combine(ArtDir,"previous_pistol_mirror.json");
        class MirrorRec{public string name,parent,root;public float[] lp,lr,ls;public string[] bones;public float[] boundsC,boundsS;}
        static string FixPistolMirror(FirstPersonViewModel pvm)
        {
            var mirror=pvm.GetComponentInChildren<ViewModelArmourMirror>(true);if(!mirror)return "pistol mirror: none";
            var arms=ArmsOf(pvm);var am=ArmsMesh(arms);
            var bones=arms.GetComponentsInChildren<Transform>(true).GroupBy(t=>t.name).ToDictionary(g=>g.Key,g=>g.First());
            var smrs=mirror.mirrors.Where(m=>m).Select(m=>m.GetComponent<SkinnedMeshRenderer>()).Where(x=>x).ToArray();
            bool broken=smrs.Any(x=>x.bones.Any(b=>!b||!b.IsChildOf(arms)));
            if(broken&&!File.Exists(PistolMirrorPath)&&!dry)
                File.WriteAllText(PistolMirrorPath,JsonConvert.SerializeObject(smrs.Select(x=>new MirrorRec{name=x.name,parent=PathOf(x.transform.parent,pvm.transform),root=PathOf(x.rootBone,pvm.transform),
                    lp=A(x.transform.localPosition),lr=A(x.transform.localRotation),ls=A(x.transform.localScale),bones=x.bones.Select(b=>PathOf(b,pvm.transform)).ToArray(),boundsC=A(x.localBounds.center),boundsS=A(x.localBounds.size)}).ToArray(),Formatting.Indented));
            var made=new List<string>();
            for(int i=0;i<mirror.mirrors.Length&&i<mirror.sources.Length;i++)
            {
                var m=mirror.mirrors[i];var src=mirror.sources[i]?mirror.sources[i].GetComponent<SkinnedMeshRenderer>():null;var sm=m?m.GetComponent<SkinnedMeshRenderer>():null;
                if(!sm||!src)continue;
                m.transform.SetParent(am.transform.parent,false);m.transform.localPosition=am.transform.localPosition;m.transform.localRotation=am.transform.localRotation;m.transform.localScale=am.transform.localScale;
                sm.bones=src.bones.Select(b=>b&&bones.TryGetValue(b.name,out var t)?t:am.rootBone).ToArray();
                sm.rootBone=src.rootBone&&bones.TryGetValue(src.rootBone.name,out var rb)?rb:am.rootBone;sm.localBounds=am.localBounds;
                EditorUtility.SetDirty(sm);made.Add($"{m.name} ({sm.bones.Count(b=>b.IsChildOf(arms))}/{sm.bones.Length} bones on the arms)");
            }
            return "pistol armour mirror "+(broken?"re-skinned onto the pistol arms: ":"already on the pistol arms, re-applied: ")+string.Join(", ",made);
        }
        static string RollbackPistolMirror(FirstPersonViewModel pvm)
        {
            if(!File.Exists(PistolMirrorPath))return "pistol mirror: no record";
            var recs=JsonConvert.DeserializeObject<MirrorRec[]>(File.ReadAllText(PistolMirrorPath));
            var all=pvm.GetComponentsInChildren<SkinnedMeshRenderer>(true);var n=0;
            foreach(var r in recs)
            {
                var sm=all.FirstOrDefault(x=>x.name==r.name);if(!sm)continue;
                sm.transform.SetParent(Find(pvm.transform,r.parent),false);sm.transform.localPosition=V(r.lp);sm.transform.localRotation=Q(r.lr);sm.transform.localScale=V(r.ls);
                sm.bones=r.bones.Select(b=>Find(pvm.transform,b)).ToArray();sm.rootBone=Find(pvm.transform,r.root);sm.localBounds=new Bounds(V(r.boundsC),V(r.boundsS));EditorUtility.SetDirty(sm);n++;
            }
            return $"pistol mirror: {n} copies restored to the recorded (pre-pass) skinning";
        }

        static string Apply(PlayerCombat combat,FirstPersonViewModel vm)
        {
            trace.Clear();var log=trace;
            var arms=ArmsOf(vm);var weapon=WeaponOf(vm);
            var hand=Bone(arms,"RightHand");var lhand=Bone(arms,"LeftHand");
            var ik=arms.GetComponent<SupportHandIK>()??throw new InvalidOperationException("no support-hand IK on the rifle arms");
            var grip=arms.GetComponent<PlayerHandGrip>()??throw new InvalidOperationException("no PlayerHandGrip on the rifle arms");
            var restR=grip.rightFingers.Select(t=>t.localRotation).ToArray();var restL=grip.leftFingers.Select(t=>t.localRotation).ToArray();
            void Relax(){for(int i=0;i<restR.Length;i++)grip.rightFingers[i].localRotation=restR[i];for(int i=0;i<restL.Length;i++)grip.leftFingers[i].localRotation=restL[i];}
            var smr=ArmsMesh(arms);var wristR=new Wrist(smr,"RightForeArm","RightHand");var wristL=new Wrist(smr,"LeftForeArm","LeftHand");
            var cam=Vector3.zero;var camRot=Quaternion.identity;   // camera at the origin: world = camera space
            // 1. the clip-driven hip pose (weapon under the right hand): the arms' orientation and shoulder spread
            Pose(vm,cam,camRot,Frame.Hip);Relax();
            var R0=arms.rotation;
            Vector3 Mid()=>(Bone(arms,"LeftArm").position+Bone(arms,"RightArm").position)/2;
            log.Add($"clip-driven hip: shoulders L {F(Bone(arms,"LeftArm").position)} R {F(Bone(arms,"RightArm").position)}, right hand {F(hand.position)}, left hand {F(lhand.position)}, weapon root {F(weapon.position)}, muzzle {(vm.muzzle?F(vm.muzzle.position):"-")}");
            float upperLen=(Bone(arms,"RightForeArm").position-Bone(arms,"RightArm").position).magnitude,lowerLen=(hand.position-Bone(arms,"RightForeArm").position).magnitude;
            log.Add($"arm lengths: upper {upperLen:0.000} fore {lowerLen:0.000} m; weapon lossy scale {F(weapon.lossyScale)}");
            // 2. weapon on its own mount; FirstPersonViewModel now moves the mount, the weapon stays where it was on screen
            var mount=new GameObject(MountName){layer=vm.gameObject.layer}.transform;
            mount.SetParent(vm.visuals?vm.visuals.transform:vm.transform,false);mount.SetPositionAndRotation(weapon.position,weapon.rotation);
            weapon.SetParent(mount,true);vm.rig=mount;
            {
                var sh=Measure(weapon,vm);
                var post=sh.pts.Where(p=>{float f=sh.FromMuzzle(p);return f>=PostFrom&&f<=PostTo;}).ToArray();
                var postTop=post.OrderByDescending(p=>p.y).Take(12).Aggregate(Vector3.zero,(a,b)=>a+b)/12f;
                float railTop=sh.pts.Where(p=>{float f=sh.FromMuzzle(p);return f>=RailFrom&&f<=RailTo;}).Max(p=>p.y);
                // at ADS the weapon frame is the camera frame: pivot rotation = camera * (weapon in pivot)^-1
                var q=Quaternion.Inverse(vm.pistol.rotation)*weapon.rotation;var e=Quaternion.Inverse(q).eulerAngles;
                e=new Vector3(Mathf.DeltaAngle(0,e.x),Mathf.DeltaAngle(0,e.y),Mathf.DeltaAngle(0,e.z));
                var pivotLocal=weapon.InverseTransformPoint(vm.pistol.position);
                var w=new Vector3(-postTop.x,-postTop.y,AimButtBehindEye-sh.min.z);   // weapon origin in camera space
                var ao=vm.aimOffset;var ae=vm.aimEuler;vm.aimOffset=w+pivotLocal;vm.aimEuler=e;
                log.Add($"ADS from the sights: post tip {F(postTop)}, rail top y {railTop:0.000} ({(railTop-postTop.y)*100:0.0} cm under the line of sight), butt {AimButtBehindEye*100:0.0} cm behind the eye; aim offset {F(ao)} -> {F(vm.aimOffset)}, aim euler {F(ae)} -> {F(vm.aimEuler)}");
                if(HipFromAim)
                {
                    // hip: weapon origin at HipWeapon, bore through the muzzle onto the view axis HipConverge ahead, canted
                    var muz=vm.muzzle?weapon.InverseTransformPoint(vm.muzzle.position):new Vector3(0,0,sh.max.z);
                    var Rw=Quaternion.identity;
                    for(int it=0;it<4;it++)
                    {
                        var mzCam=HipWeapon+Rw*muz;var dir=(new Vector3(0,0,HipConverge)-mzCam).normalized;
                        Rw=Quaternion.LookRotation(dir,Vector3.up)*Quaternion.Euler(0,0,HipCant);
                    }
                    var pr=Rw*Quaternion.Inverse(q);var he=pr.eulerAngles;he=new Vector3(Mathf.DeltaAngle(0,he.x),Mathf.DeltaAngle(0,he.y),Mathf.DeltaAngle(0,he.z));
                    var ho=vm.hipOffset;var hE=vm.hipEuler;vm.hipOffset=HipWeapon+Rw*pivotLocal;vm.hipEuler=he;
                    log.Add($"hip framing: weapon origin {F(HipWeapon)}, bore onto the crosshair {HipConverge} m ahead, cant {HipCant}; hip offset {F(ho)} -> {F(vm.hipOffset)}, hip euler {F(hE)} -> {F(vm.hipEuler)}");
                }
            }
            // 3. arms rig, right-arm IK and the two grip points (filled in below)
            var ar=vm.gameObject.AddComponent<ViewModelArmsRig>();
            ar.viewModel=vm;ar.arms=arms;ar.aimAnchor=true;ar.followWeapon=FollowWeapon;ar.drawFollow=DrawFollow;
            var rikGo=new GameObject(RightIkName){layer=vm.gameObject.layer};rikGo.transform.SetParent(arms,false);
            var rik=rikGo.AddComponent<SupportHandIK>();rik.combat=combat;rik.upper=Bone(arms,"RightArm");rik.lower=Bone(arms,"RightForeArm");rik.hand=hand;
            rik.pistolGrip=null;rik.pistolWeight=0;rik.rifleWeight=1;
            var shoot=new GameObject(ShootName){layer=vm.gameObject.layer}.transform;shoot.SetParent(weapon,false);
            var support=new GameObject(SupportName){layer=vm.gameObject.layer}.transform;support.SetParent(weapon,false);
            rik.rifleGrip=shoot;ik.rifleGrip=support;ik.rifleWeight=1;
            rik.twistShare=TwistShare;rik.restHandLocal=wristR.RestRel;ik.twistShare=LeftTwistShare;ik.restHandLocal=wristL.RestRel;
            var mainCam=GameObject.Find("MainCamera")?.GetComponent<Camera>();viewTanV=Mathf.Tan((mainCam?mainCam.fieldOfView:60f)*.5f*Mathf.Deg2Rad);
            // arms anchors: shoulders under and behind the eye, torso bladed (left shoulder forward); poles in camera space at the hip anchor
            void SetConfig(float yaw,float midZ,Vector3 rightPole,float aimDz,float midY,float midX,Vector3 leftPole)
            {
                Pose(vm,Vector3.zero,Quaternion.identity,Frame.Hip);
                arms.rotation=Quaternion.Euler(0,yaw,0)*R0;arms.position+=new Vector3(midX,midY,midZ)-Mid();
                ar.anchorPosition=arms.position;ar.anchorRotation=arms.rotation;
                rik.poleHint=rik.upper.parent.InverseTransformDirection(rightPole.normalized);
                ik.poleHint=ik.upper.parent.InverseTransformDirection(leftPole.normalized);
                arms.rotation=Quaternion.Euler(0,yaw+AimBladeYaw-BladeYaw,0)*R0;arms.position+=new Vector3(AimShoulders.x+midX-HipShoulders.x,AimShoulders.y,midZ+aimDz)-Mid();
                ar.aimAnchorPosition=arms.position;ar.aimAnchorRotation=arms.rotation;
            }
            // 4. the rifle's shape in the weapon frame
            var s=Measure(weapon,vm);
            log.Add($"rifle (weapon frame): bounds {F(s.min)}..{F(s.max)}, length {s.len:0.000} m; pistol grip top {F(s.gripTop)} bottom {F(s.gripBottom)} axis {F(s.gripAxisDown)} (rake {Vector3.Angle(s.gripAxisDown,Vector3.down):0} deg), depth {s.gripDepth*100:0.0} cm width {s.gripWidth*100:0.0} cm; old grip point (weapon origin) {s.FromMuzzle(Vector3.zero):0.000} of the length from the muzzle, {s.H(Vector3.zero):0.00} of the height");
            var cols=WeaponColliders(weapon);
            try
            {
                Pose(vm,cam,camRot,Frame.Hip);Relax();
                var (dL,nL,palmL,midL)=HandFrame(hand,grip.rightFingers,"r");
                var (dLl,nLl,palmLl,midLl)=HandFrame(lhand,grip.leftFingers,"l");
                var down=s.gripAxisDown;var fwdG=Vector3.ProjectOnPlane(Vector3.forward,down).normalized;
                float tTop=(PalmHeight*s.height+s.min.y-s.gripTop.y)/(s.gripBottom.y-s.gripTop.y);
                var palmCentre=Vector3.LerpUnclamped(s.gripTop,s.gripBottom,tTop)-fwdG*PalmBack;   // weapon frame
                // 5. shooting hand: palm on the grip's right panel, fingers forward round the front strap, thumb over the top
                (float score,Vector3 pos,Quaternion rot,string desc) SearchShoot(List<string> table)
                {
                    var best=(score:float.MaxValue,pos:Vector3.zero,rot:Quaternion.identity,desc:"");
                    foreach(var pitch in ShootPitches)foreach(var roll in ShootRolls)
                    {
                        var dT=(fwdG*Mathf.Cos(pitch*Mathf.Deg2Rad)-down*Mathf.Sin(pitch*Mathf.Deg2Rad)).normalized;
                        var nT=Quaternion.AngleAxis(roll,dT)*Vector3.left;nT=Vector3.ProjectOnPlane(nT,dT).normalized;
                        var Rl=Quaternion.LookRotation(dT,nT)*Quaternion.Inverse(Quaternion.LookRotation(dL,nL));   // weapon-frame hand rotation
                        // move in from the right until the palm touches the grip (world, hip pose)
                        Pose(vm,cam,camRot,Frame.Hip);Relax();Physics.SyncTransforms();
                        float found=-1;
                        for(float o=.10f;o>=-.01f;o-=.002f)
                        {
                            var wristW=weapon.TransformPoint(palmCentre+Vector3.right*o)-weapon.rotation*Rl*palmL;var Rw=weapon.rotation*Rl;
                            if(Physics.CheckCapsule(wristW+Rw*(midL*.3f),wristW+Rw*midL,.017f,1<<TempLayer,QueryTriggerInteraction.Collide)){found=o+.002f;break;}
                        }
                        if(found<0){table?.Add($"p{pitch} r{roll}: no contact");continue;}
                        shoot.localPosition=palmCentre+Vector3.right*found-Rl*palmL;shoot.localRotation=Rl;
                        var (sc,desc)=Score(vm,cam,camRot,rik,wristR,Relax);
                        Pose(vm,cam,camRot,Frame.Hip);Relax();int inside=FingersInside(grip.rightFingers,1<<TempLayer);sc+=FingerInsidePenalty*inside;desc+=$" inside {inside} -> {sc:0}";
                        table?.Add($"p{pitch} r{roll} lat {found*100:0.0}cm: {desc}");
                        if(sc<best.score)best=(sc,shoot.localPosition,shoot.localRotation,$"pitch {pitch} roll {roll} lateral {found*100:0.0} cm: {desc}");
                    }
                    return best;
                }
                // 6. support hand: palm under the front receiver/handguard, fingers across to the right side, thumb up the left
                (float score,Vector3 pos,Quaternion rot,string desc) SearchSupport(List<string> table)
                {
                    var sbest=(score:float.MaxValue,pos:Vector3.zero,rot:Quaternion.identity,desc:"");
                    for(float st=SupportTo;st<=SupportFrom+1e-4f;st+=table==null?.02f:.01f)
                    {
                        var slice=s.pts.Where(p=>Mathf.Abs(s.FromMuzzle(p)-st)<.012f&&s.H(p)<.95f).ToArray();
                        if(slice.Length<10){table?.Add($"st {st:0.00}: empty");continue;}
                        float ybot=slice.Min(p=>p.y);float xc=(slice.Min(p=>p.x)+slice.Max(p=>p.x))/2;float z=s.Z(st);
                        foreach(var yaw in SupportYaws)foreach(var roll in SupportRolls)
                        {
                            var dT=(Vector3.forward*Mathf.Cos(yaw*Mathf.Deg2Rad)+Vector3.right*Mathf.Sin(yaw*Mathf.Deg2Rad)).normalized;
                            var nT=Vector3.ProjectOnPlane(Quaternion.AngleAxis(-roll,dT)*Vector3.up,dT).normalized;
                            var Rl=Quaternion.LookRotation(dT,nT)*Quaternion.Inverse(Quaternion.LookRotation(dLl,nLl));
                            Pose(vm,cam,camRot,Frame.Hip);Relax();Physics.SyncTransforms();
                            float found=-1;
                            for(float below=.06f;below>=-.01f;below-=.002f)
                            {
                                var palmW=weapon.TransformPoint(new Vector3(xc,ybot-below,z));var Rw=weapon.rotation*Rl;var wristW=palmW-Rw*palmLl;
                                if(Physics.CheckCapsule(wristW+Rw*(midLl*.3f),wristW+Rw*midLl,.017f,1<<TempLayer,QueryTriggerInteraction.Collide)){found=below+.002f;break;}
                            }
                            if(found<0)continue;
                            support.localPosition=new Vector3(xc,ybot-found,z)-Rl*palmLl;support.localRotation=Rl;
                            var (sc,desc)=Score(vm,cam,camRot,ik,wristL,Relax);
                            Pose(vm,cam,camRot,Frame.Hip);Relax();int inside=FingersInside(grip.leftFingers,1<<TempLayer);sc+=FingerInsidePenalty*inside;desc+=$" inside {inside}";
                            sc+=SupportForwardBias*100*(st-SupportTo);
                            table?.Add($"st {st:0.00} yaw {yaw} roll {roll} below {found*100:0.0}cm: {desc} -> {sc:0}");
                            if(sc<sbest.score)sbest=(sc,support.localPosition,support.localRotation,$"station {st:0.00} of the length from the muzzle ({(s.Z(GripFromMuzzle)-z)*-100:0} cm ahead of the grip), yaw {yaw} roll {roll}: {desc}");
                        }
                    }
                    return sbest;
                }
                // 7. the arms configuration (blade, shoulder depth, right elbow) searched jointly with both grips
                var cfgTable=new List<string>();var bestCfg=(score:float.MaxValue,yaw:0f,midZ:0f,pole:Vector3.zero,aimDz:0f,midY:0f,midX:0f,lpole:Vector3.zero);
                foreach(var yaw in BladeYaws)foreach(var midZ in HipMidZs)foreach(var pole in RightPoles)foreach(var aimDz in AimDzs)foreach(var midY in HipShoulderYs)foreach(var midX in HipShoulderXs)foreach(var lpole in LeftPoles)
                {
                    SetConfig(yaw,midZ,pole,aimDz,midY,midX,lpole);
                    var a1=SearchShoot(null);var a2=SearchSupport(null);float tot=a1.score+a2.score;
                    cfgTable.Add($"blade {yaw} midX {midX} midY {midY} lpole {F(lpole)} midZ {midZ} aimDz {aimDz} pole {F(pole)}: shoot {a1.score:0} ({a1.desc}) | support {a2.score:0} ({a2.desc}) => {tot:0}");
                    if(tot<bestCfg.score)bestCfg=(tot,yaw,midZ,pole,aimDz,midY,midX,lpole);
                }
                File.WriteAllText(Path.Combine(EvDir,"config_candidates.txt"),string.Join("\n",cfgTable)+"\n");
                SetConfig(bestCfg.yaw,bestCfg.midZ,bestCfg.pole,bestCfg.aimDz,bestCfg.midY,bestCfg.midX,bestCfg.lpole);
                log.Add($"arms configuration chosen of {cfgTable.Count} (config_candidates.txt): blade {bestCfg.yaw} deg, mid-shoulder x {bestCfg.midX} y {bestCfg.midY} z {bestCfg.midZ} (aim {bestCfg.midZ+bestCfg.aimDz}), right pole {F(bestCfg.pole)}, left pole {F(bestCfg.lpole)}; anchors hip {F(ar.anchorPosition)} / {F(ar.anchorRotation)}, aim {F(ar.aimAnchorPosition)} / {F(ar.aimAnchorRotation)}, follow {FollowWeapon}");
                var table=new List<string>();var best=SearchShoot(table);
                if(best.score==float.MaxValue)throw new InvalidOperationException("no shooting-grip candidate touched the grip:\n"+string.Join("\n",table));
                shoot.localPosition=best.pos;shoot.localRotation=best.rot;
                log.Add("shooting grip candidates:\n  "+string.Join("\n  ",table));log.Add("shooting grip chosen: "+best.desc+$" local {F(best.pos)} / {F(best.rot)}");
                var stable=new List<string>();var sbest=SearchSupport(stable);
                if(sbest.score==float.MaxValue)throw new InvalidOperationException("no support-grip candidate:\n"+string.Join("\n",stable));
                support.localPosition=sbest.pos;support.localRotation=sbest.rot;
                File.WriteAllText(Path.Combine(EvDir,"support_candidates.txt"),string.Join("\n",stable)+"\n");
                log.Add($"support grip candidates: {stable.Count} (support_candidates.txt); chosen: {sbest.desc} local {F(sbest.pos)} / {F(sbest.rot)}");
                // 8. fingers, solved at the hip pose with both hands on their grips
                Pose(vm,cam,camRot,Frame.Hip);Relax();
                // thumbs: the shooting thumb over the top of the grip to its left side, the support thumb forward along the
                // left side of the handguard
                var thumbR=weapon.TransformPoint(s.gripTop+new Vector3(-.035f,.02f,.01f));
                var palmS=support.localPosition+support.localRotation*palmLl;var thumbL=weapon.TransformPoint(palmS+new Vector3(-.03f,.035f,.06f));
                var solvedR=SolveFingers(grip.rightFingers,restR,1<<TempLayer,thumbR);
                var solvedL=SolveFingers(grip.leftFingers,restL,1<<TempLayer,thumbL);
                grip.rifleRight=solvedR;grip.rifleLeft=solvedL;
                string Curl(Quaternion[] q,Quaternion[] rest){var parts=new List<string>();for(int d=0;d<5;d++){float sum=0;for(int j=0;j<3;j++){int i=d*3+j;if(i<q.Length)sum+=Quaternion.Angle(rest[i],q[i]);}parts.Add(Digits[d].Substring(0,2)+" "+sum.ToString("0"));}return string.Join(",",parts);}
                log.Add("fingers solved: right "+Curl(solvedR,restR)+" | left "+Curl(solvedL,restL));
            }
            finally{foreach(var c in cols)if(c)Object.DestroyImmediate(c);Relax();}
            Pose(vm,cam,camRot,Frame.Hip);Relax();   // leave the saved transforms at the hip pose, fingers relaxed
            foreach(var o in new Object[]{vm,ar,rik,ik,grip})EditorUtility.SetDirty(o);
            log.Add(Metrics(vm,"after install"));
            var text=string.Join("\n",log);trace.Clear();return text;
        }

        /// IK error and wrist bend/twist at the hip and aim poses for one arm onto its current target.
        static (float,string) Score(FirstPersonViewModel vm,Vector3 cam,Quaternion camRot,SupportHandIK k,Wrist w,Action relax)
        {
            float sc=0;var parts=new List<string>();
            foreach(var (name,f) in new[]{("hip",Frame.Hip),("aim",new Frame{aim=1,draw=1})})
            {
                Pose(vm,cam,camRot,f);relax();
                float err=(k.hand.position-k.rifleGrip.position).magnitude*100;var (swing,twist)=w.Measure(k.lower,k.hand);
                var e=k.lower.position;   // elbow, camera space
                sc+=swing+1.5f*twist+(err>.5f?100*err:0);
                bool Near(Vector3 p,float m)=>p.z>.01f&&Mathf.Abs(p.y/(p.z*viewTanV))<m&&Mathf.Abs(p.x/(p.z*viewTanV*16f/9f))<m;
                bool inView=Near(e,1.1f);if(inView)sc+=ElbowInViewPenalty;
                // the arms mesh is cut on the upper arm: the shoulder and the upper arm's middle must stay well out of frame
                var um=Vector3.Lerp(e,k.upper.position,.5f);bool stump=Near(k.upper.position,1.4f)||Near(um,1.25f);if(stump)sc+=StumpPenalty;
                parts.Add($"{name} err {err:0.0}cm swing {swing:0} twist {twist:0} elbow {F(e)}{(inView?" IN VIEW":"")}{(stump?" UPPER ARM NEAR VIEW":"")}");
            }
            return (sc,string.Join("; ",parts)+$" => {sc:0}");
        }

        // ------------------------------------------------------------------ metrics (install log, verify)
        static readonly (string name,Frame f)[] States={
            ("hip",Frame.Hip),("ads",new Frame{aim=1,draw=1}),("burst",new Frame{draw=1,recoil=1}),("ads_burst",new Frame{aim=1,draw=1,recoil=1}),
            ("walk",new Frame{draw=1,bob=.008f,bobPhase=Mathf.PI/2,sway=new Vector2(.4f,-.2f)}),("sprint",new Frame{draw=1,bob=.008f,bobPhase=0,sway=new Vector2(-.8f,.3f)}),
            ("lowered",new Frame{draw=.45f})};
        static string Metrics(FirstPersonViewModel vm,string title)=>JsonConvert.SerializeObject(WithVisuals(vm,()=>MetricsData(vm)),Formatting.Indented).Insert(0,title+": ");
        static Dictionary<string,object> MetricsData(FirstPersonViewModel vm)
        {
            var arms=ArmsOf(vm);var weapon=WeaponOf(vm);var smr=ArmsMesh(arms);
            var wr=new Wrist(smr,"RightForeArm","RightHand");var wl=new Wrist(smr,"LeftForeArm","LeftHand");var el=new Wrist(smr,"LeftArm","LeftForeArm");var er=new Wrist(smr,"RightArm","RightForeArm");
            var grip=arms.GetComponent<PlayerHandGrip>();
            var iks=vm.GetComponentsInChildren<SupportHandIK>(true);
            var rik=iks.FirstOrDefault(k=>k.upper&&k.upper.name=="RightArm");var lik=iks.FirstOrDefault(k=>k.upper&&k.upper.name=="LeftArm");
            var cam=Vector3.zero;var camRot=Quaternion.identity;
            var main=GameObject.Find("MainCamera")?.GetComponent<Camera>();float vfov=main?main.fieldOfView:60;float tanV=Mathf.Tan(vfov*.5f*Mathf.Deg2Rad),tanH=tanV*16f/9f;
            string Vp(Vector3 p)=>p.z<=.01f?"behind":string.Format(CultureInfo.InvariantCulture,"{0:0.00},{1:0.00}",p.x/(p.z*tanH),p.y/(p.z*tanV));   // -1..1 = on screen
            var data=new Dictionary<string,object>();
            Quaternion[] restR=grip?grip.rightFingers.Select(t=>t.localRotation).ToArray():null,restL=grip?grip.leftFingers.Select(t=>t.localRotation).ToArray():null;
            var cols=WeaponColliders(weapon);
            try
            {
                foreach(var (name,f) in States)
                {
                    Pose(vm,cam,camRot,f);
                    var st=new Dictionary<string,object>();
                    if(rik&&(vm.rifle?rik.rifleGrip:rik.pistolGrip)){var t=vm.rifle?rik.rifleGrip:rik.pistolGrip;st["rightErrCm"]=Math.Round((rik.hand.position-t.position).magnitude*100,2);var (a,b)=wr.Measure(rik.lower,rik.hand);st["rightWrist"]=$"swing {a:0} twist {b:0}";st["rightElbowVp"]=Vp(rik.lower.position);st["rightElbow"]=F(rik.lower.position);}
                    if(lik&&(vm.rifle?lik.rifleGrip:lik.pistolGrip)){var t=vm.rifle?lik.rifleGrip:lik.pistolGrip;st["leftErrCm"]=Math.Round((lik.hand.position-t.position).magnitude*100,2);var (a,b)=wl.Measure(lik.lower,lik.hand);st["leftWrist"]=$"swing {a:0} twist {b:0}";st["leftElbowVp"]=Vp(lik.lower.position);{var (es,et)=el.Measure(lik.upper,lik.lower);st["leftElbowJoint"]=$"flex {es:0} twist {et:0} angle {Vector3.Angle(lik.upper.position-lik.lower.position,lik.hand.position-lik.lower.position):0}";}st["leftElbow"]=F(lik.lower.position);}
                    if(grip){st["rightFingerHits"]=Penetrations(grip.rightFingers,.006f,1<<TempLayer);st["leftFingerHits"]=Penetrations(grip.leftFingers,.006f,1<<TempLayer);}
                    var b0=WeaponMeshes(weapon).SelectMany(m=>{var bb=m.sharedMesh.bounds;var c=bb.center;var e=bb.extents;return new[]{-1,1}.SelectMany(x=>new[]{-1,1}.SelectMany(y=>new[]{-1,1}.Select(z=>m.transform.TransformPoint(c+Vector3.Scale(e,new Vector3(x,y,z))))));}).ToArray();
                    st["weaponNearestZ"]=Math.Round(b0.Min(p=>p.z),3);
                    var rk=arms.GetComponentsInChildren<Transform>(true).FirstOrDefault(t=>t.name=="index_01_r");var lk=arms.GetComponentsInChildren<Transform>(true).FirstOrDefault(t=>t.name=="middle_01_l");
                    if(rk)st["rightKnuckleVp"]=Vp(rk.position);if(lk)st["leftKnuckleVp"]=Vp(lk.position);
                    if(vm.muzzle){var m=vm.muzzle.position;var fw=vm.muzzle.parent?vm.pistol.forward:Vector3.forward;st["boreAtCrosshairM"]=Math.Round(Mathf.Abs(fw.x)>1e-4f?-m.x/fw.x*fw.z+m.z:-1,2);}
                    if(vm.muzzle)st["muzzle"]=F(vm.muzzle.position);
                    data[name]=st;
                }
            }
            finally
            {
                foreach(var c in cols)if(c)Object.DestroyImmediate(c);
                if(grip){for(int i=0;i<restR.Length;i++)grip.rightFingers[i].localRotation=restR[i];for(int i=0;i<restL.Length;i++)grip.leftFingers[i].localRotation=restL[i];}
            }
            return data;
        }

        // ------------------------------------------------------------------ verify (-nographics)
        static string Verify()
        {
            var combat=Combat();var vm=Rvm(combat);var fails=new List<string>();var info=new Dictionary<string,object>();
            void Must(bool ok,string what){if(!ok)fails.Add(what);}
            Must(Installed(vm),"rifle view model on "+MountName);
            var arms=ArmsOf(vm);var weapon=WeaponOf(vm);
            var ar=vm.GetComponent<ViewModelArmsRig>();Must(ar&&ar.arms==arms&&ar.aimAnchor&&ar.viewModel==vm,"ViewModelArmsRig with hip and aim anchors on the rifle view model");
            var shoot=weapon.GetComponentsInChildren<Transform>(true).Where(t=>t.name==ShootName).ToArray();var sup=weapon.GetComponentsInChildren<Transform>(true).Where(t=>t.name==SupportName).ToArray();
            Must(shoot.Length==1&&sup.Length==1,"one shooting grip and one support grip under the view-model rifle");
            var rik=arms.GetComponentsInChildren<SupportHandIK>(true).Where(k=>k.name==RightIkName).ToArray();Must(rik.Length==1&&rik[0].rifleGrip==shoot.FirstOrDefault()&&rik[0].upper&&rik[0].upper.name=="RightArm","right-arm IK onto the shooting grip");
            var lik=arms.GetComponent<SupportHandIK>();Must(lik&&lik.rifleGrip==sup.FirstOrDefault()&&lik.upper&&lik.upper.name=="LeftArm","left-arm IK onto the support grip");
            var grip=arms.GetComponent<PlayerHandGrip>();Must(grip&&grip.rifleRight.Length==grip.rightFingers.Length&&grip.rifleLeft.Length==grip.leftFingers.Length&&grip.rightFingers.Length==15,"solved rifle finger grips (15+15)");
            Must(arms.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(x=>!x.name.StartsWith("FP armour")).All(x=>x.sharedMaterials.All(m=>m)),"no missing materials on the arms");
            Must(vm.GetComponentsInChildren<Component>(true).All(c=>c!=null),"no missing scripts under the rifle view model");
            Must(!vm.GetComponentsInChildren<Transform>(true).Any(t=>t.name=="__rh collider"),"no temporary colliders left");
            // shooting grip on the pistol grip: the palm is within the grip's band, not on the magazine
            if(shoot.Length==1)
            {
                var s=Measure(weapon,vm);var g=shoot[0];
                var (_,_,palmL,_)=HandFrame(Bone(arms,"RightHand"),grip.rightFingers,"r");
                var palm=g.localPosition+g.localRotation*palmL;   // weapon frame (the target's frame is the hand's)
                info["shootPalmFromMuzzle"]=Math.Round(s.FromMuzzle(palm),3);info["shootPalmHeight"]=Math.Round(s.H(palm),3);
                Must(Mathf.Abs(s.FromMuzzle(palm)-GripFromMuzzle)<.04f,$"shooting palm on the pistol grip ({s.FromMuzzle(palm):0.000} of the length from the muzzle, grip {GripFromMuzzle})");
                var sp=sup.Length==1?sup[0].localPosition:Vector3.zero;info["supportFromMuzzle"]=Math.Round(s.FromMuzzle(sp),3);
            }
            // armour mirror on the view-model arms
            var mirror=vm.GetComponentInChildren<ViewModelArmourMirror>(true);
            Must(mirror&&mirror.mirrors.Length==mirror.sources.Length,"armour mirror on the rifle arms");
            if(mirror){info["mirrors"]=mirror.mirrors.Select(m=>m?m.name:"null").ToArray();
                foreach(var m in mirror.mirrors.Where(m=>m)){var sm=m.GetComponent<SkinnedMeshRenderer>();Must(sm&&sm.bones.All(b=>b&&b.IsChildOf(arms)),"mirror "+m.name+" skinned to the view-model arms");}}
            var pmirror=combat.viewModel?combat.viewModel.GetComponentInChildren<ViewModelArmourMirror>(true):null;
            if(pmirror){var parms=ArmsOf(combat.viewModel);foreach(var m in pmirror.mirrors.Where(m=>m)){var sm=m.GetComponent<SkinnedMeshRenderer>();Must(sm&&sm.bones.All(b=>b&&b.IsChildOf(parms)),"pistol mirror "+m.name+" skinned to the pistol arms");}}
            // per-state placement
            var metrics=WithVisuals(vm,()=>MetricsData(vm));info["states"]=metrics;
            foreach(var kv in metrics)
            {
                var st=(Dictionary<string,object>)kv.Value;
                if(kv.Key=="lowered")continue;   // mid-draw: the weapon is sliding out of reach by design
                foreach(var side in new[]{"rightErrCm","leftErrCm"})if(st.TryGetValue(side,out var e))Must(Convert.ToDouble(e)<=1.5,$"{kv.Key} {side} {e} <= 1.5 cm");
            }
            // reference values against install time
            var refPath=Path.Combine(EvDir,"reference.json");
            if(File.Exists(refPath))
            {
                var was=JsonConvert.DeserializeObject<Dictionary<string,string>>(File.ReadAllText(refPath));var now=Reference(combat);
                var diff=was.Keys.Where(k=>!now.TryGetValue(k,out var v)||v!=was[k]).ToArray();info["referenceDiff"]=diff;
                Must(diff.Length==0,"reference values unchanged since install: "+string.Join(",",diff));
            }
            else fails.Add("no reference.json (run install)");
            // the pistol view model is untouched by this pass and keeps its own metrics
            if(combat.viewModel)info["pistol"]=WithVisuals(combat.viewModel,()=>MetricsData(combat.viewModel));
            var text=JsonConvert.SerializeObject(new{utc=DateTime.UtcNow.ToString("O"),pass=fails.Count==0,fails,info},Formatting.Indented);
            File.WriteAllText(Path.Combine(EvDir,"verify.json"),text);
            if(fails.Count>0)throw new InvalidOperationException("verify failed: "+string.Join("; ",fails)+"\n"+text);
            return text;
        }

        // ------------------------------------------------------------------ rebaseline
        /// Re-records the reference values verify compares against (reference.json) from the saved scene as it is now,
        /// for a later pass that deliberately changes one of them (for example PlayerWeaponPose). With --keys k1,k2 only
        /// those keys are taken over; every other differing key is reported and left as recorded, so verify keeps
        /// failing on it. Reads only: the scene and prefabs are not modified or saved.
        static string Rebaseline(string keys)
        {
            var refPath=Path.Combine(EvDir,"reference.json");
            var was=File.Exists(refPath)?JsonConvert.DeserializeObject<Dictionary<string,string>>(File.ReadAllText(refPath)):new Dictionary<string,string>();
            var now=Reference(Combat());
            var differing=was.Keys.Union(now.Keys).Where(k=>!was.TryGetValue(k,out var a)||!now.TryGetValue(k,out var b)||a!=b).OrderBy(k=>k).ToArray();
            var wanted=keys==null?differing:keys.Split(',').Select(k=>k.Trim()).Where(k=>k.Length>0).ToArray();
            var log=new List<string>();var next=new Dictionary<string,string>(was);
            foreach(var k in differing)
            {
                string from=was.TryGetValue(k,out var a)?a:"(absent)",to=now.TryGetValue(k,out var b)?b:"(absent)";
                bool take=wanted.Contains(k);
                if(take){if(now.ContainsKey(k))next[k]=to;else next.Remove(k);}
                log.Add($"{(take?"REBASELINED":"KEPT (still differs)")} {k}: {from} -> {to}");
            }
            if(differing.Length==0)log.Add("no reference value differs from reference.json");
            if(File.Exists(refPath))File.Copy(refPath,Path.Combine(EvDir,"reference-before-rebaseline-"+DateTime.Now.ToString("yyyyMMdd-HHmmss")+".json"),true);
            File.WriteAllText(refPath,JsonConvert.SerializeObject(next,Formatting.Indented));
            File.WriteAllText(Path.Combine(EvDir,"rebaseline.txt"),DateTime.UtcNow.ToString("O")+"\n"+string.Join("\n",log)+"\n");
            return string.Join("\n",log);   // nothing saved: no SaveAll here
        }

        // ------------------------------------------------------------------ rollback
        static string Rollback()
        {
            var combat=Combat();var vm=Rvm(combat);
            if(!Installed(vm))return "not installed: nothing to roll back";
            if(!File.Exists(RecordPath))throw new FileNotFoundException(RecordPath);
            var rec=JsonConvert.DeserializeObject<Rec>(File.ReadAllText(RecordPath));
            Restore(vm,rec);var pm=combat.viewModel?RollbackPistolMirror(combat.viewModel):"";SaveAll();
            return "rifle view model restored to the clip-driven state recorded "+rec.utc+"; "+pm;
        }

        // ------------------------------------------------------------------ report
        static string Report()
        {
            var combat=Combat();var vm=Rvm(combat);var log=new List<string>();
            log.Add("installed: "+Installed(vm));
            void Tree(Transform t,int depth,int max){log.Add(new string(' ',depth*2)+t.name+" ["+string.Join(",",t.GetComponents<Component>().Where(c=>c&&!(c is Transform)).Select(c=>c.GetType().Name))+"] lp "+F(t.localPosition)+" ls "+F(t.localScale)+(t.gameObject.activeSelf?"":" (inactive)"));if(depth<max)foreach(Transform c in t)if(!c.name.Contains("_0")&&!c.name.EndsWith("_l")&&!c.name.EndsWith("_r"))Tree(c,depth+1,max);}
            Tree(vm.transform,0,5);
            log.Add($"vm: rig {PathOf(vm.rig,vm.transform)} pistol {PathOf(vm.pistol,vm.transform)} muzzle {PathOf(vm.muzzle,vm.transform)} hip {F(vm.hipOffset)} {F(vm.hipEuler)} aim {F(vm.aimOffset)} {F(vm.aimEuler)} holster {F(vm.holsterOffset)} {F(vm.holsterEuler)} recoil {vm.recoilBack} {vm.recoilPitch} clip {(vm.holdClip?vm.holdClip.name:"-")}");
            foreach(var ik in vm.GetComponentsInChildren<SupportHandIK>(true))log.Add($"ik {ik.name}: upper {(ik.upper?ik.upper.name:"-")} rifleGrip {PathOf(ik.rifleGrip,vm.transform)} w {ik.rifleWeight} pistolGrip {PathOf(ik.pistolGrip,vm.transform)} pole {F(ik.poleHint)}");
            var weapon=WeaponOf(vm);var s=Measure(weapon,vm);
            log.Add($"rifle shape: bounds {F(s.min)}..{F(s.max)}; grip top {F(s.gripTop)} bottom {F(s.gripBottom)} depth {s.gripDepth:0.000} width {s.gripWidth:0.000}; weapon origin {s.FromMuzzle(Vector3.zero):0.000} from the muzzle, {s.H(Vector3.zero):0.00} high");
            foreach(var v in new[]{combat.viewModel,combat.rifleViewModel}.Where(x=>x))
            {
                var mm=v.GetComponentInChildren<ViewModelArmourMirror>(true);if(!mm){log.Add((v.rifle?"rifle":"pistol")+" mirror: none");continue;}
                var armsRoot=ArmsOf(v);
                foreach(var m in mm.mirrors.Where(m=>m))
                {
                    var sm=m.GetComponent<SkinnedMeshRenderer>();
                    log.Add($"{(v.rifle?"rifle":"pistol")} mirror {m.name} active {m.activeSelf} parent {PathOf(m.transform.parent,v.transform)} lp {F(m.transform.localPosition)} ls {F(m.transform.localScale)} root {PathOf(sm.rootBone,v.transform)} bones {sm.bones.Length} under arms {sm.bones.Count(b=>b&&b.IsChildOf(armsRoot))} mesh {sm.sharedMesh.name} bounds {F(sm.localBounds.center)}/{F(sm.localBounds.size)} first bones {string.Join(",",sm.bones.Take(4).Select(b=>b?b.name:"null"))}");
                }
                var arm=ArmsMesh(armsRoot);log.Add($"{(v.rifle?"rifle":"pistol")} arms mesh {arm.name} parent {PathOf(arm.transform.parent,v.transform)} lp {F(arm.transform.localPosition)} ls {F(arm.transform.localScale)} root {PathOf(arm.rootBone,v.transform)}");
            }
            log.Add(Metrics(vm,"rifle metrics"));
            if(combat.viewModel)log.Add(Metrics(combat.viewModel,"pistol metrics"));
            return string.Join("\n",log);
        }

        // ------------------------------------------------------------------ dump (-nographics review geometry)
        /// Bakes the posed view models (arms, worn glove/arm-guard copies, weapon) in camera space (camera at the origin,
        /// looking +Z) to OBJ files per state, with and without the armour copies, for a Blender review render
        /// (art/rifle_hands_20261120/render_dump.py). Used when graphics-mode Unity cannot run. Nothing is saved.
        static string Dump(string tag)
        {
            var combat=Combat();var outDir=Path.Combine(EvDir,"dump",tag);Directory.CreateDirectory(outDir);var log=new List<string>();
            var main=GameObject.Find("MainCamera")?.GetComponent<Camera>();
            File.WriteAllText(Path.Combine(outDir,"camera.json"),JsonConvert.SerializeObject(new{vfov=main?main.fieldOfView:60f,aspect=16f/9f,near=.01f}));
            foreach(var vm in new[]{combat.rifleViewModel,combat.viewModel}.Where(v=>v))
            {
                string w=vm.rifle?"rifle":"pistol";
                WithVisuals(vm,()=>
                {
                    var mirror=vm.GetComponentInChildren<ViewModelArmourMirror>(true);
                    var was=mirror?mirror.mirrors.Select(m=>m&&m.activeSelf).ToArray():new bool[0];
                    try
                    {
                        foreach(var (name,f) in States)
                        {
                            Pose(vm,Vector3.zero,Quaternion.identity,f);
                            if(mirror)foreach(var m in mirror.mirrors.Where(m=>m))m.SetActive(true);
                            var sb=new System.Text.StringBuilder();int baseIndex=1;
                            void Add(string obj,Mesh mesh,Matrix4x4 m)
                            {
                                var v=mesh.vertices;var inv=CultureInfo.InvariantCulture;
                                sb.Append("o ").Append(obj).Append('\n');
                                foreach(var x in v){var p=m.MultiplyPoint3x4(x);sb.Append(string.Format(inv,"v {0:0.#####} {1:0.#####} {2:0.#####}\n",p.x,p.y,p.z));}
                                for(int sm=0;sm<mesh.subMeshCount;sm++){var t=mesh.GetTriangles(sm);for(int i=0;i<t.Length;i+=3)sb.Append("f ").Append(t[i]+baseIndex).Append(' ').Append(t[i+1]+baseIndex).Append(' ').Append(t[i+2]+baseIndex).Append('\n');}
                                baseIndex+=v.Length;
                            }
                            int k=0;
                            foreach(var smr in vm.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(x=>x.enabled&&x.gameObject.activeInHierarchy&&x.sharedMesh))
                            {
                                var baked=new Mesh();smr.BakeMesh(baked,true);
                                Add((smr.name.StartsWith("FP armour")?"armour_":"arms_")+(k++),baked,smr.transform.localToWorldMatrix);Object.DestroyImmediate(baked);
                            }
                            foreach(var mf in WeaponMeshes(WeaponOf(vm)))Add("weapon_"+(k++),mf.sharedMesh,mf.transform.localToWorldMatrix);
                            File.WriteAllText(Path.Combine(outDir,$"{w}_{name}.obj"),sb.ToString());
                            if(mirror)for(int i=0;i<mirror.mirrors.Length;i++)if(mirror.mirrors[i])mirror.mirrors[i].SetActive(was[i]);
                            log.Add($"{w}_{name}: {k} objects");
                        }
                    }
                    finally{if(mirror)for(int i=0;i<mirror.mirrors.Length;i++)if(mirror.mirrors[i])mirror.mirrors[i].SetActive(was[i]);}
                    return 0;
                });
            }
            return string.Join("; ",log);
        }

        // ------------------------------------------------------------------ capture (graphics)
        /// First-person frames through the main camera's settings (DuskStartPass.Preview, 13:00) at the rifle review stand,
        /// looking down range. One set of six per Unity run (AGENTS.md machine limits). Nothing is saved.
        static string Capture(string shots,string tag)
        {
            var outDir=Path.Combine(EvDir,"captures",tag);Directory.CreateDirectory(outDir);
            var combat=Combat();var motor=Motor();var log=new List<string>();
            if(combat.muzzleLight)combat.muzzleLight.enabled=false;
            var feet=RifleArmourInstall.Stand;
            if(Physics.Raycast(feet+Vector3.up*6,Vector3.down,out var hit,30,~(1<<8),QueryTriggerInteraction.Ignore))feet.y=hit.point.y;
            motor.transform.position=feet+Vector3.up*.015f;
            var main=GameObject.Find("MainCamera").GetComponent<Camera>();int mask=main.cullingMask;
            var eye=feet+Vector3.up*1.62f;var rot=Quaternion.LookRotation(Vector3.left,Vector3.up)*Quaternion.Euler(3,0,0);
            string Spec(string name,Vector3 pos,Vector3 look,float fov)=>string.Format(CultureInfo.InvariantCulture,"{0}:{1},{2},{3}:{4},{5},{6}:{7}",name,pos.x,pos.y,pos.z,look.x,look.y,look.z,fov);
            DuskStartPass.Preview(13,Path.Combine(outDir,"warmup"),Spec("warm",eye,eye+rot*Vector3.forward*10,main.fieldOfView));
            bool rifle=!shots.StartsWith("pistol");bool armour=shots.EndsWith("_armour");
            try
            {
                var vm=rifle?combat.rifleViewModel:combat.viewModel;var other=rifle?combat.viewModel:combat.rifleViewModel;
                main.cullingMask=(mask|(1<<vm.gameObject.layer))&~(1<<8);   // the body is not drawn in first person
                if(other&&other.visuals)other.visuals.SetActive(false);
                if(vm.visuals)vm.visuals.SetActive(true);
                foreach(var smr in vm.GetComponentsInChildren<SkinnedMeshRenderer>(true))smr.forceMatrixRecalculationPerRender=true;
                var mirror=vm.GetComponentInChildren<ViewModelArmourMirror>(true);
                if(mirror)foreach(var m in mirror.mirrors.Where(m=>m))m.SetActive(armour);
                string tagW=rifle?"rifle":"pistol";
                if(shots=="orbit")
                {
                    var r=combat.rifleViewModel;if(r.visuals)r.visuals.SetActive(true);
                    main.cullingMask=(mask|(1<<r.gameObject.layer))&~(1<<8);if(combat.viewModel.visuals)combat.viewModel.visuals.SetActive(false);
                    var arms=ArmsOf(r);
                    Pose(r,eye,rot,Frame.Hip);
                    var rh=Bone(arms,"RightHand").position;var lh=Bone(arms,"LeftHand").position;var cr=rot*Vector3.right;var cf=rot*Vector3.forward;var cu=rot*Vector3.up;
                    log.Add(DuskStartPass.Preview(13,outDir,
                        Spec("orbit_rifle_right_hand",rh+cr*.38f+cu*.06f+cf*.02f,rh,40),
                        Spec("orbit_rifle_right_hand_front",rh+cf*.30f+cr*.18f+cu*.04f,rh,40),
                        Spec("orbit_rifle_support_left",lh-cr*.36f+cu*.04f,lh,40),
                        Spec("orbit_rifle_support_under",lh-cu*.32f+cr*.05f-cf*.05f,lh,40),
                        Spec("orbit_rifle_top",(rh+lh)/2+cu*.55f+cr*.05f,(rh+lh)/2,45)));
                    Pose(r,eye,rot,new Frame{aim=1,draw=1});
                    var mid=(Bone(arms,"RightHand").position+Bone(arms,"LeftHand").position)/2;
                    log.Add(DuskStartPass.Preview(13,outDir,Spec("orbit_rifle_ads_side",mid+cr*.55f+cu*.05f-cf*.1f,mid-cf*.1f,50)));
                }
                else
                {
                    var specs=new List<string>();
                    foreach(var (name,f) in States.Where(x=>x.name!="ads_burst"))
                    {
                        Pose(vm,eye,rot,f);
                        log.Add(DuskStartPass.Preview(13,outDir,Spec($"fp_{tagW}_{name}{(armour?"_armour":"")}",eye,eye+rot*Vector3.forward*10,main.fieldOfView)));
                    }
                }
            }
            finally{main.cullingMask=mask;}
            return string.Join("",log);
        }
    }
}
