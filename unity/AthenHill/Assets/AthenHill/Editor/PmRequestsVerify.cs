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
    // 27 Sep 2026 pm: read-only check of requests #1-5 in the saved scene (values and measurements, nothing is changed).
    public static class PmRequestsVerify
    {
        const string Scene="Assets/AthenHill/Scenes/AthenHill.unity";

        static Transform Find(string name)=>Object.FindObjectsByType<Transform>(FindObjectsInactive.Include).FirstOrDefault(t=>t.name==name);

        static float GroundBelow(Vector3 p,Transform ignore)
        {
            var hits=Physics.RaycastAll(p+Vector3.up*3,Vector3.down,20,~0,QueryTriggerInteraction.Ignore).Where(h=>!h.transform.IsChildOf(ignore)).OrderBy(h=>h.distance).ToArray();
            return hits.Length>0?hits[0].point.y:float.NaN;
        }

        // lowest skinned vertex over 8 samples of the actor's idle clip, relative to the ground under it
        static object Feet(Transform root)
        {
            var actor=root.GetComponentInChildren<ActorAnimation>(true);
            var skins=root.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            if(skins.Length==0)return new{error="no skin"};
            var anim=actor?actor.animationSource:null;var idle=actor?actor.idle:null;
            float lowest=float.MaxValue;Vector3 at=Vector3.zero;var mesh=new Mesh();
            for(int i=0;i<8;i++)
            {
                if(anim&&idle)idle.SampleAnimation(anim.gameObject,idle.length*i/8f);
                foreach(var s in skins)
                {
                    s.BakeMesh(mesh,true);var m=s.transform.localToWorldMatrix;
                    foreach(var v in mesh.vertices){var w=m.MultiplyPoint3x4(v);if(w.y<lowest){lowest=w.y;at=w;}}
                }
            }
            float ground=GroundBelow(at,root);
            var surfaces=Object.FindObjectsByType<MeshRenderer>(FindObjectsInactive.Exclude).Where(m=>m.enabled&&!m.transform.IsChildOf(root)&&m.bounds.min.x<=at.x&&m.bounds.max.x>=at.x&&m.bounds.min.z<=at.z&&m.bounds.max.z>=at.z&&m.bounds.max.y<at.y+.3f&&m.bounds.max.y>at.y-.5f)
                .OrderByDescending(m=>m.bounds.max.y).Take(3).Select(m=>m.name+" top="+m.bounds.max.y.ToString("F3")).ToArray();
            var visual=skins[0].transform.parent;
            return new{lowestVertexY=Math.Round(lowest,4),groundY=Math.Round(ground,4),footToGroundMm=Math.Round((lowest-ground)*1000,1),idle=idle?idle.name:null,
                rootY=Math.Round(root.position.y,4),renderSurfacesUnderFoot=surfaces,visualChildren=root.Cast<Transform>().Select(c=>c.name+" y="+c.localPosition.y.ToString("F3")).ToArray()};
        }

        public static void Run()
        {
            if(EditorSceneManager.GetActiveScene().path!=Scene)EditorSceneManager.OpenScene(Scene);
            var r=new Dictionary<string,object>();
            // 1. run
            var motor=Object.FindAnyObjectByType<PlayerMotor>(FindObjectsInactive.Include);
            r["1_run"]=new{player=motor.actor.name,runStrideSpeed=motor.actor.runStrideSpeed,walkStrideSpeed=motor.actor.walkStrideSpeed,runSpeed=motor.runSpeed,walkSpeed=motor.walkSpeed,
                playbackAt6=Math.Round(motor.runSpeed/motor.actor.runStrideSpeed,3),playbackAtOldStride=Math.Round(motor.runSpeed/3.5f,3)};
            // 2. wardens and other guard-model characters
            var feet=new Dictionary<string,object>();
            foreach(var n in new[]{"Warden Ossa","Warden Rell","npc_torr","npc_mira","npc_linn","npc_vex"})
            {
                var t=Find(n)??Object.FindObjectsByType<NpcAgent>(FindObjectsInactive.Include).Select(a=>a.transform).FirstOrDefault(a=>a.name.Contains(n));
                feet[n]=t?Feet(t):new{error="not found"};
            }
            r["2_feet"]=feet;
            // 3. road tree
            var tree=Object.FindObjectsByType<Transform>(FindObjectsInactive.Include).Where(t=>t.name=="searsiasmall").Select(t=>new{
                path=PathOf(t),pos=t.position.ToString("F2"),active=t.gameObject.activeInHierarchy,
                colliders=t.GetComponentsInChildren<Collider>(true).Select(c=>c.GetType().Name+(c.enabled?" on":" off")).ToArray(),
                distFromOld=Math.Round(Vector2.Distance(new Vector2(t.position.x,t.position.z),new Vector2(-79.5f,-4.8f)),2)}).ToArray();
            r["3_tree"]=tree;
            // 4. truck and gate
            var truck=Find("Karaveen truck");
            if(truck)
            {
                var b=Bounds(truck);
                var gates=Object.FindObjectsByType<Transform>(FindObjectsInactive.Include).Where(t=>t.name.IndexOf("gate",StringComparison.OrdinalIgnoreCase)>=0&&t.GetComponentInChildren<Renderer>(true))
                    .OrderBy(t=>Vector3.Distance(t.position,truck.position)).Take(6).Select(t=>{var gb=Bounds(t);return new{path=PathOf(t),dist=Math.Round(Vector3.Distance(t.position,truck.position),1),size=gb.size.ToString("F2"),center=gb.center.ToString("F2")};}).ToArray();
                // lateral clearance: horizontal rays across the truck's width at 1 m and 3 m, 2 m in front of the nose
                r["4_truck"]=new{path=PathOf(truck),localScale=truck.localScale.ToString("F3"),lossy=truck.lossyScale.ToString("F3"),boundsSize=b.size.ToString("F2"),boundsMinY=Math.Round(b.min.y,3),
                    groundY=Math.Round(GroundBelow(b.center,truck),3),forward=truck.forward.ToString("F2"),
                    colliders=truck.GetComponentsInChildren<Collider>(true).Select(c=>c is BoxCollider bc?"Box local size x lossy "+Vector3.Scale(bc.size,bc.transform.lossyScale).ToString("F2"):c.GetType().Name).ToArray(),nearestGates=gates,
                    meshDimensions=TruckDims(truck)};
            }
            else r["4_truck"]="not found";
            // 5. dusk
            var clock=Object.FindAnyObjectByType<CityTimeOfDay>(FindObjectsInactive.Include);
            var prof=clock?clock.profile:null;
            if(prof)
            {
                var f=prof.Evaluate(17);var key=Quaternion.Euler(f.keyEuler)*Vector3.forward;
                r["5_dusk"]=new{profile=AssetDatabase.GetAssetPath(prof),prof.defaultHour,sunElevationAt17=Math.Round(Mathf.Asin(-key.y)*Mathf.Rad2Deg,1),keyIntensity=f.keyIntensity,keyColor=f.keyColor.ToString(),postExposure=f.postExposure,
                    json=JsonUtility.ToJson(prof).Length};
            }
            var outp=Path.GetFullPath(OutPath);
            File.WriteAllText(outp,JsonConvert.SerializeObject(r,Formatting.Indented,new JsonSerializerSettings{ReferenceLoopHandling=ReferenceLoopHandling.Ignore}));
            Debug.Log("PmRequestsVerify -> "+outp);
        }

        /// Output path: "-pmVerifyOut <path>" on the command line, else the 27 Sep pm evidence file.
        static string OutPath{get{var a=Environment.GetCommandLineArgs();int i=Array.IndexOf(a,"-pmVerifyOut");
            return i>=0&&i+1<a.Length?a[i+1]:"../../unity/evidence/character-feel/20260927-pm/requests-1-5-verify.json";}}

        // Evening re-measure of #4: world-space extents of the truck's own mesh along its length, width and height
        // (height = the truck axis closest to world up; length = the longer remaining one). The earlier read-back quoted
        // the world AABB/box collider, whose 3.39 m figure is the truck's height, not its width. Also reports the
        // body width without mirrors (2nd..98th percentile across the width, over the middle 60% of the length).
        static object TruckDims(Transform truck)
        {
            var axes=new[]{truck.right,truck.up,truck.forward};
            int hi=Enumerable.Range(0,3).OrderByDescending(k=>Mathf.Abs(Vector3.Dot(axes[k],Vector3.up))).First();
            var pts=new List<Vector3>();
            foreach(var mf in truck.GetComponentsInChildren<MeshFilter>(true))
            {
                if(!mf.sharedMesh)continue;var m=mf.transform.localToWorldMatrix;var vs=mf.sharedMesh.vertices;
                for(int i=0;i<vs.Length;i+=7)pts.Add(m.MultiplyPoint3x4(vs[i]));
            }
            if(pts.Count==0)return "no mesh";
            float[] Proj(Vector3 ax)=>pts.Select(p=>Vector3.Dot(p,ax)).ToArray();
            var ext=Enumerable.Range(0,3).Select(k=>{var p=Proj(axes[k]);return p.Max()-p.Min();}).ToArray();
            var rest=Enumerable.Range(0,3).Where(k=>k!=hi).OrderByDescending(k=>ext[k]).ToArray();int li=rest[0],wi=rest[1];
            var pl=Proj(axes[li]);float lmin=pl.Min(),lmax=pl.Max();
            var pw=Proj(axes[wi]);var mid=Enumerable.Range(0,pts.Count).Where(i=>pl[i]>lmin+(lmax-lmin)*.2f&&pl[i]<lmax-(lmax-lmin)*.2f).Select(i=>pw[i]).OrderBy(x=>x).ToArray();
            float body=mid.Length>10?mid[(int)(mid.Length*.98f)]-mid[(int)(mid.Length*.02f)]:float.NaN;
            return new{sampledVertices=pts.Count,lengthM=Math.Round(ext[li],2),widthOverallM=Math.Round(ext[wi],2),bodyWidthM=Math.Round(body,2),heightM=Math.Round(ext[hi],2),
                note="height axis = truck local "+"xyz"[hi]+"; width axis = local "+"xyz"[wi]};
        }

        static Bounds Bounds(Transform t)
        {
            var rs=t.GetComponentsInChildren<Renderer>(true);var b=rs[0].bounds;foreach(var x in rs)b.Encapsulate(x.bounds);return b;
        }
        static string PathOf(Transform t)=>t.parent?PathOf(t.parent)+"/"+t.name:t.name;
    }
}
