using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    // 2 Oct 2026: the field rifle in hand (Meshy FieldRifle.glb, rifle holds from the retargeted library clips) and the
    // Warden plate carrier on the chest (Meshy plate carrier), plus the scene bindings of Ossa's Long Arm and Plate
    // Carrier orders. Idempotent: re-running replaces the installed objects and keeps the saved scene's other state.
    public static class RifleArmourInstall
    {
        const string RifleGlb="Assets/AthenHill/Resources/WeaponPreviews/FieldRifle.glb";       // Codex inventory pass, 2 Oct
        const string RifleGlbFallback="Assets/AthenHill/Art/Weapons/FieldRifle/FieldRifle.glb";
        const string VestGlb="Assets/AthenHill/Art/Armour/WardenPlateCarrier.glb";
        const string PlayerFolder="Assets/AthenHill/Art/CharacterMotion/Player";
        const string PlayerSource="Assets/AthenHill/Art/CharacterMotion/Source/Player";
        const string MeshyClips="../../meshy/character-feel-20260927/player-rifle";              // relative to the project
        public const string RifleHolder="Berms held rifle",VestHolder="Warden plate carrier",RifleMuzzle="Rifle muzzle";
        // Hold frames chosen from the Blender frame sheets (meshy/character-feel-20260927/player-rifle/previews/sheet.png):
        // "Rifle Turn Left" settles square with both hands on a long gun near its end; "Lower Weapon, Look, Raise" is lowered through its middle (hand at the hip).
        public static float AimFraction=.95f,CarryFraction=.5f;   // tuned 2 Oct: editor/tune/tune.png
        // Rifle mount in the hand: grip point along the hand bone, and where the grip sits on the rifle (fraction of its
        // length from the butt, fraction of its height from the bottom). Tuned from the editor captures.
        public static float GripAlong=.075f,GripFromButt=.40f,GripFromBottom=.15f,RifleLength=.9f;
        // Vest: height in metres and offsets from the chest bone frame.
        public static float VestHeight=.58f;public static Vector3 VestOffset=new Vector3(0,-.07f,.03f);   // tuned 2 Oct: editor/tune/tune.png
        public static Vector3 VestEuler=Vector3.zero;
        /// Where the review cameras expect the colonist: open range apron, feet on the ground.
        public static readonly Vector3 Stand=new Vector3(-75f,-1.3f,3f);

        [MenuItem("Athen Hill/Combat/Install field rifle and plate carrier")]
        public static void Install(){Debug.Log(InstallAll());}

        /// Batch-mode entry (-executeMethod, -nographics): opens the city scene, adds the QA landmarks and saves.
        public static void InstallLandmarksBatch()
        {
            var scene=EditorSceneManager.OpenScene("Assets/AthenHill/Scenes/AthenHill.unity",OpenSceneMode.Single);
            var log=Landmarks();
            EditorSceneManager.MarkSceneDirty(scene);EditorSceneManager.SaveScene(scene);AssetDatabase.SaveAssets();
            Debug.Log("RifleArmourInstall landmarks: "+log);
            File.WriteAllText(Path.Combine(Application.dataPath,"../../evidence/rifle-armour/20261002/landmarks-install.txt"),log+"\n");
        }

        public static string InstallAll()
        {
            var log=new System.Text.StringBuilder();
            log.AppendLine(Clips());
            log.AppendLine(Rifle());
            log.AppendLine(Vest());
            log.AppendLine(Bindings());
            log.AppendLine(Cameras());
            log.AppendLine(Landmarks());
            var scene=SceneManager();
            EditorSceneManager.MarkSceneDirty(scene);EditorSceneManager.SaveScene(scene);AssetDatabase.SaveAssets();
            log.AppendLine("scene saved");
            return log.ToString();
        }
        static UnityEngine.SceneManagement.Scene SceneManager()=>UnityEngine.SceneManagement.SceneManager.GetActiveScene();

        static PlayerCombat Combat()=>Object.FindAnyObjectByType<PlayerCombat>(FindObjectsInactive.Include)??throw new InvalidOperationException("No PlayerCombat in the scene.");
        static Transform Bone(Component root,string name)=>root.GetComponentsInChildren<Transform>(true).FirstOrDefault(t=>t.name==name)??throw new InvalidOperationException("No bone "+name+" under "+root.name);

        /// Copy the Meshy rifle clips into the project and retarget them, then freeze the two static holds.
        public static string Clips()
        {
            Directory.CreateDirectory(PlayerSource);
            var log=new System.Text.StringBuilder();
            foreach(var name in new[]{"rifleturn_573","lower_334"})
            {
                var src=Path.GetFullPath(Path.Combine(Application.dataPath,"../"+MeshyClips+"/"+name+".glb"));
                var dst=PlayerSource+"/Player_"+name+".glb";
                if(!File.Exists(src))throw new FileNotFoundException(src);
                if(!File.Exists(dst)){File.Copy(src,dst);AssetDatabase.ImportAsset(dst,ImportAssetOptions.ForceSynchronousImport);}
                log.AppendLine(CharacterFeelPass.RetargetPlayerClip(name));
            }
            log.AppendLine(WeaponFeelPass.HoldClip(PlayerFolder+"/lib_rifleturn_573.anim",AimFraction,PlayerFolder+"/rifle_hold.anim","rifle_hold"));
            log.AppendLine(WeaponFeelPass.HoldClip(PlayerFolder+"/lib_lower_334.anim",CarryFraction,PlayerFolder+"/rifle_carry.anim","rifle_carry"));
            return log.ToString().TrimEnd();
        }

        /// The rifle model in the right hand, mounted for the rifle hold, with its muzzle point; wired to the combat and
        /// pose components. Barrel axis and muzzle end are measured from the mesh (the thinner end is the muzzle).
        public static string Rifle()
        {
            var combat=Combat();var motor=combat.GetComponent<PlayerMotor>();var pose=combat.GetComponent<PlayerWeaponPose>();
            if(!pose||!pose.rightHand)throw new InvalidOperationException("PlayerWeaponPose with a right hand is required (run the pistol feel install first).");
            string glb=File.Exists(RifleGlb)?RifleGlb:RifleGlbFallback;
            var model=AssetDatabase.LoadAssetAtPath<GameObject>(glb);
            if(!model)throw new FileNotFoundException("Rifle model "+glb);
            var hand=pose.rightHand;
            foreach(var old in hand.Cast<Transform>().Where(t=>t.name==RifleHolder).ToArray())Object.DestroyImmediate(old.gameObject);
            var holder=new GameObject(RifleHolder);holder.transform.SetParent(hand,false);
            // the Meshy hand bone carries the rig's ~0.01 scale: make the holder unit-scale in the world (metres), as the pistol holder is
            var hs=hand.lossyScale;holder.transform.localScale=new Vector3(1/hs.x,1/hs.y,1/hs.z);
            var inst=(GameObject)PrefabUtility.InstantiatePrefab(model);inst.name="FieldRifle";inst.transform.SetParent(holder.transform,false);
            inst.transform.localPosition=Vector3.zero;inst.transform.localRotation=Quaternion.identity;inst.transform.localScale=Vector3.one;
            // measure the mesh in the instance's own frame
            var filters=inst.GetComponentsInChildren<MeshFilter>(true);
            if(filters.Length==0)throw new InvalidOperationException("Rifle model has no meshes.");
            var pts=filters.SelectMany(f=>f.sharedMesh.vertices.Select(v=>inst.transform.InverseTransformPoint(f.transform.TransformPoint(v)))).ToArray();
            var min=pts.Aggregate(Vector3.Min);var max=pts.Aggregate(Vector3.Max);var size=max-min;
            int axis=size.x>=size.y&&size.x>=size.z?0:size.y>=size.z?1:2;
            float len=size[axis];
            // which end is thinner: cross-section extents of the outer 12 % at each end
            float Section(bool high){var sel=pts.Where(p=>high?p[axis]>max[axis]-len*.12f:p[axis]<min[axis]+len*.12f).ToArray();if(sel.Length==0)return 0;var a=sel.Aggregate(Vector3.Min);var b=sel.Aggregate(Vector3.Max);var s=b-a;s[axis]=0;return s.magnitude;}
            bool muzzleHigh=Section(true)<Section(false);
            var barrel=Vector3.zero;barrel[axis]=muzzleHigh?1:-1;
            int upAxis=axis==1?2:1;var up=Vector3.zero;up[upAxis]=1;
            float scale=RifleLength/len;
            // grip point on the rifle: GripFromButt of the length from the butt, GripFromBottom of the height from the bottom, centred sideways
            var grip=(min+max)*.5f;
            grip[axis]=(muzzleHigh?min[axis]:max[axis])+(muzzleHigh?1:-1)*len*GripFromButt;
            grip[upAxis]=min[upAxis]+size[upAxis]*GripFromBottom;
            // rotate the mesh so the barrel runs along holder +Z and its up along +Y, then place the grip at the holder origin
            var rot=Quaternion.Inverse(Quaternion.LookRotation(barrel,up));
            inst.transform.localRotation=rot;inst.transform.localScale=Vector3.one*scale;
            inst.transform.localPosition=-(rot*(grip*scale));
            var muzzlePoint=new GameObject(RifleMuzzle).transform;muzzlePoint.SetParent(holder.transform,false);
            var tip=(min+max)*.5f;tip[axis]=muzzleHigh?max[axis]:min[axis];
            muzzlePoint.localPosition=rot*(tip*scale)+inst.transform.localPosition;
            foreach(var r in inst.GetComponentsInChildren<Renderer>(true)){r.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.On;}
            // mount for the rifle hold: grip in the palm, barrel along the colonist's forward
            var hold=AssetDatabase.LoadAssetAtPath<AnimationClip>(PlayerFolder+"/rifle_hold.anim");
            var root=motor.actor.animationSource.gameObject;var body=motor.visual;
            hold.SampleAnimation(root,0);
            var along=(hand.rotation*Vector3.up).normalized;
            holder.transform.rotation=Quaternion.LookRotation(body.forward,body.up);
            holder.transform.position=hand.position+along*GripAlong-body.up*.01f;
            if(motor.actor.idle)motor.actor.idle.SampleAnimation(root,0);
            holder.SetActive(false);
            Undo.RecordObject(combat,"rifle");combat.heldRifle=holder;combat.rifleMuzzle=muzzlePoint;
            PrefabUtility.RecordPrefabInstancePropertyModifications(combat);EditorUtility.SetDirty(combat);
            Undo.RecordObject(pose,"rifle pose");
            pose.rifleAimClip=hold;pose.rifleCarryClip=AssetDatabase.LoadAssetAtPath<AnimationClip>(PlayerFolder+"/rifle_carry.anim");
            PrefabUtility.RecordPrefabInstancePropertyModifications(pose);EditorUtility.SetDirty(pose);
            return $"rifle {glb}: length axis {axis} muzzle {(muzzleHigh?"+":"-")} scale {scale:F4} tris {filters.Sum(f=>f.sharedMesh.triangles.Length/3)} holder local {holder.transform.localPosition:F3} / {holder.transform.localEulerAngles:F0}";
        }

        /// The plate carrier under the chest bone, shown by PlayerArmourVisuals while equipped.
        public static string Vest()
        {
            var combat=Combat();var motor=combat.GetComponent<PlayerMotor>();
            var model=AssetDatabase.LoadAssetAtPath<GameObject>(VestGlb);
            if(!model)throw new FileNotFoundException("Vest model "+VestGlb);
            // Meshy naming runs bottom-up: Hips > Spine02 > Spine01 > Spine > neck; the chest is Spine (the top one).
            var chest=Bone(motor.actor,"Spine");var neck=Bone(motor.actor,"neck");var body=motor.visual;
            foreach(var old in chest.Cast<Transform>().Where(t=>t.name==VestHolder).ToArray())Object.DestroyImmediate(old.gameObject);
            if(motor.actor.idle)motor.actor.idle.SampleAnimation(motor.actor.animationSource.gameObject,0);
            var holder=new GameObject(VestHolder);holder.transform.SetParent(chest,false);
            var cs=chest.lossyScale;holder.transform.localScale=new Vector3(1/cs.x,1/cs.y,1/cs.z);
            var inst=(GameObject)PrefabUtility.InstantiatePrefab(model);inst.name="WardenPlateCarrier";inst.transform.SetParent(holder.transform,false);
            inst.transform.localPosition=Vector3.zero;inst.transform.localRotation=Quaternion.identity;inst.transform.localScale=Vector3.one;
            var rs=inst.GetComponentsInChildren<Renderer>(true);
            var vpts=inst.GetComponentsInChildren<MeshFilter>(true).SelectMany(f=>f.sharedMesh.vertices.Select(v=>inst.transform.InverseTransformPoint(f.transform.TransformPoint(v)))).ToArray();
            var vmin=vpts.Aggregate(Vector3.Min);var vmax=vpts.Aggregate(Vector3.Max);
            float scale=VestHeight/Mathf.Max(.01f,(vmax-vmin).y);
            inst.transform.localScale=Vector3.one*scale;
            var b=rs[0].bounds;foreach(var r in rs)b.Encapsulate(r.bounds);
            // the vest's own frame: glTF models face +Z after glTFast's X flip; align to the colonist and centre on the chest
            holder.transform.rotation=Quaternion.LookRotation(body.forward,body.up)*Quaternion.Euler(VestEuler);
            var chestCentre=Vector3.Lerp(chest.position,neck.position,.45f);
            holder.transform.position=chestCentre+body.right*VestOffset.x+body.up*VestOffset.y+body.forward*VestOffset.z;
            b=rs[0].bounds;foreach(var r in rs)b.Encapsulate(r.bounds);
            inst.transform.position+=holder.transform.position-b.center;
            foreach(var r in rs)r.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.On;
            holder.SetActive(false);
            var vis=combat.GetComponent<PlayerArmourVisuals>();if(!vis)vis=Undo.AddComponent<PlayerArmourVisuals>(combat.gameObject);
            Undo.RecordObject(vis,"armour");vis.combat=combat;
            vis.pieces=new[]{new PlayerArmourVisuals.Piece{itemId="warden_plate_carrier",slot="armour_chest",model=holder}};
            PrefabUtility.RecordPrefabInstancePropertyModifications(vis);EditorUtility.SetDirty(vis);
            return $"vest {VestGlb}: scale {scale:F4} size {b.size:F2} tris {inst.GetComponentsInChildren<MeshFilter>(true).Sum(f=>f.sharedMesh.triangles.Length/3)} at {holder.transform.position:F2}";
        }

        /// Field-order scene bindings: guidance targets and encounters for the two new orders, and the caravan strongbox.
        public static string Bindings()
        {
            var orders=Object.FindAnyObjectByType<FieldOrders>(FindObjectsInactive.Include)??throw new InvalidOperationException("No FieldOrders.");
            var encounters=Object.FindObjectsByType<DroidEncounter>(FindObjectsInactive.Include,FindObjectsSortMode.None);
            DroidEncounter Enc(string part)=>encounters.FirstOrDefault(e=>e.name.Contains(part))??throw new InvalidOperationException("No encounter named like "+part);
            var knoll=Enc("Gunner nest");var caravan=Enc("Caravan scavengers");
            // the strongbox: the caravan site's salvage node nearest its encounter that rolls the outer table
            var nodes=Object.FindObjectsByType<SalvageNode>(FindObjectsInactive.Include,FindObjectsSortMode.None)
                .Where(l=>l.lootTableId=="loot_berms_outer"||l.lootTableId=="loot_caravan_strongbox")
                .OrderBy(l=>(l.transform.position-caravan.transform.position).sqrMagnitude).ToArray();
            var strongbox=nodes.FirstOrDefault(l=>(l.transform.position-caravan.transform.position).magnitude<30)??throw new InvalidOperationException("No outer-table salvage node within 30 m of the caravan encounter.");
            Undo.RecordObject(strongbox,"strongbox");strongbox.lootTableId="loot_caravan_strongbox";EditorUtility.SetDirty(strongbox);
            if(!strongbox.name.Contains("strongbox")){Undo.RecordObject(strongbox.gameObject,"name");strongbox.gameObject.name="Caravan strongbox · "+strongbox.gameObject.name;}
            Undo.RecordObject(orders,"bindings");
            var targets=orders.guidanceTargets.Where(t=>t.key!="relay_knoll"&&t.key!="caravan").ToList();
            targets.Add(new FieldOrders.Target{key="relay_knoll",label="RELAY KNOLL",point=knoll.transform});
            targets.Add(new FieldOrders.Target{key="caravan",label="CARAVAN STRONGBOX",point=strongbox.transform});
            orders.guidanceTargets=targets.ToArray();
            var bindings=orders.encounters.Where(b=>b.key!="relay_knoll"&&b.key!="caravan").ToList();
            bindings.Add(new FieldOrders.EncounterBinding{key="relay_knoll",encounter=knoll});
            bindings.Add(new FieldOrders.EncounterBinding{key="caravan",encounter=caravan});
            orders.encounters=bindings.ToArray();
            EditorUtility.SetDirty(orders);
            return $"bindings: relay_knoll -> {knoll.name} at {knoll.transform.position:F0}; caravan -> {caravan.name}; strongbox {strongbox.name} at {strongbox.transform.position:F1}";
        }

        /// QA landmarks for the quest check: the review stand, the relay knoll approach (outside the gunners' aggro) and
        /// the caravan strongbox.
        public static string Landmarks()
        {
            var bridge=Object.FindAnyObjectByType<AthenDebugBridge>(FindObjectsInactive.Include);
            if(!bridge||!bridge.landmarks)throw new InvalidOperationException("No AthenDebugBridge landmarks root.");
            var orders=Object.FindAnyObjectByType<FieldOrders>(FindObjectsInactive.Include);
            Transform Point(string key)=>orders.guidanceTargets.First(t=>t.key==key).point;
            var knoll=Point("relay_knoll").position;var box=Point("caravan").position;
            var caravanEnc=orders.encounters.First(b=>b.key=="caravan").encounter.transform.position;
            void Mark(string name,Vector3 pos)
            {
                var t=bridge.landmarks.Find(name);if(!t){t=new GameObject(name).transform;t.SetParent(bridge.landmarks,false);}
                RaycastHit hit;if(Physics.Raycast(pos+Vector3.up*6,Vector3.down,out hit,30,~(1<<8),QueryTriggerInteraction.Ignore))pos.y=hit.point.y;
                t.position=pos;
            }
            Mark("rifle_stand",Stand);
            Mark("relay_knoll_approach",knoll+new Vector3(28,0,0));       // east of the nest, outside its 20-35 m engagement
            Mark("caravan_approach",caravanEnc+new Vector3(26,0,0));
            Mark("caravan_strongbox",box+new Vector3(1.4f,0,0));
            EditorUtility.SetDirty(bridge.landmarks);
            return "landmarks: rifle_stand, relay_knoll_approach, caravan_approach, caravan_strongbox";
        }

        /// Player-height review cameras at the range (the drawn rifle and the aim) and at the gate (the vest).
        public static string Cameras()
        {
            var combat=Combat();var body=combat.GetComponent<PlayerMotor>().visual;
            var scene=SceneManager();
            var rootName="Rifle armour review cameras";
            foreach(var old in scene.GetRootGameObjects().Where(g=>g.name==rootName).ToArray())Object.DestroyImmediate(old);
            var root=new GameObject(rootName);
            var template=Object.FindObjectsByType<Camera>(FindObjectsInactive.Include,FindObjectsSortMode.None).FirstOrDefault(c=>c.name=="cam_checkpoint_player");
            void Cam(string name,Vector3 pos,Vector3 look,float fov)
            {
                var go=new GameObject(name);go.transform.SetParent(root.transform,false);
                var cam=go.AddComponent<Camera>();if(template)cam.CopyFrom(template);cam.enabled=false;cam.fieldOfView=fov;
                go.transform.position=pos;go.transform.LookAt(look);
            }
            // open ground on the range apron west of the firing bays (the bays' partitions block views at the line);
            // the colonist stands at Stand facing -X (down range)
            var line=Stand;
            Cam("cam_rifle_carry",line+new Vector3(2.6f,1.2f,1.9f),line+new Vector3(0,1.0f,0),34);
            Cam("cam_rifle_aim",line+new Vector3(-2.2f,1.5f,1.6f),line+new Vector3(0,1.2f,0),38);
            Cam("cam_rifle_side",line+new Vector3(0,1.1f,2.8f),line+new Vector3(0,1.0f,0),34);
            Cam("cam_vest_front",line+new Vector3(-2.4f,1.4f,0),line+new Vector3(0,1.1f,0),36);
            Cam("cam_vest_quarter",line+new Vector3(-1.8f,1.5f,1.8f),line+new Vector3(0,1.1f,0),36);
            return "cameras: cam_rifle_carry, cam_rifle_aim, cam_rifle_side, cam_vest_front, cam_vest_quarter";
        }
    }
}
