using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object=UnityEngine.Object;

namespace AthenHill.Editor
{
    // Editor-only QA camera authoring. Root agent runs this in the coordinated Editor session.
    public static class MotionReviewSetup
    {
        const string Evidence="../evidence/quality/20260908/movement";
        static Vector3 V(JToken t){return new Vector3((float)t[0],(float)t[1],(float)t[2]);}
        static float[] A(Vector3 v){return new[]{v.x,v.y,v.z};}

        [MenuItem("Athen Hill/Characters/Prepare movement review cameras")]
        public static void Install()
        {
            if(EditorApplication.isPlaying)throw new InvalidOperationException("Exit Play before preparing saved review cameras.");
            var plan=JObject.Parse(File.ReadAllText(Evidence+"/capture-plan.json"));
            var player=Object.FindAnyObjectByType<PlayerMotor>();
            var bridge=Object.FindAnyObjectByType<AthenDebugBridge>();
            if(!player||!bridge)throw new InvalidOperationException("Open the saved city first.");
            foreach(var request in plan["guards"])
            {
                var npc=Object.FindObjectsByType<NpcAgent>().Single(n=>n.name==(string)request["actor"]);
                if(Vector3.Distance(npc.transform.position,V(request["position"]))>.03f)
                    throw new InvalidOperationException("Regenerate capture-plan.json from current saved placement: "+npc.name);
            }
            var parent=GameObject.Find("Movement review cameras")??new GameObject("Movement review cameras");
            foreach(var request in plan["cameras"])
            {
                string name=(string)request["name"];
                var t=parent.transform.Find(name);
                var go=t?t.gameObject:new GameObject(name);
                go.transform.SetParent(parent.transform,false);
                go.transform.SetPositionAndRotation(V(request["position"]),Quaternion.LookRotation(V(request["target"])-V(request["position"])));
                var c=go.GetComponent<Camera>();
                if(!c)c=go.AddComponent<Camera>();
                c.enabled=false;c.fieldOfView=(float)request["fov"];c.nearClipPlane=.05f;c.farClipPlane=650;c.aspect=16f/9;
                EditorUtility.SetDirty(c);
            }
            foreach(var request in plan["landmarks"])
            {
                var t=bridge.landmarks.Find((string)request["name"]);
                if(!t){t=new GameObject((string)request["name"]).transform;t.SetParent(bridge.landmarks,false);}
                t.position=V(request["position"]);EditorUtility.SetDirty(t);
            }
            var actors=Object.FindObjectsByType<ActorAnimation>().Select(a=>new{
                name=a.name,parent=a.transform.parent?a.transform.parent.name:null,position=A(a.transform.position),
                idle=a.idle?new{path=AssetDatabase.GetAssetPath(a.idle),a.idle.length}:null,
                talk=a.talk?new{path=AssetDatabase.GetAssetPath(a.talk),a.talk.length}:null,
                walk=a.walk?AssetDatabase.GetAssetPath(a.walk):null,run=a.run?AssetDatabase.GetAssetPath(a.run):null,
                jump=a.jumpTakeoff?AssetDatabase.GetAssetPath(a.jumpTakeoff):null
            }).ToArray();
            var sightlines=plan["cameras"].Select(r=>{
                RaycastHit hit;bool blocked=Physics.Linecast(V(r["position"]),V(r["target"]),out hit,player.worldMask,QueryTriggerInteraction.Ignore);
                return new{name=(string)r["name"],blocked,hit=blocked?hit.collider.name:null};
            }).ToArray();
            File.WriteAllText(Evidence+"/capture-layout.json",JsonConvert.SerializeObject(new{actors,sightlines,
                note="Sightlines are diagnostics. Inspect initial native frames; static cameras can include foreground actors/props. No acceptance implied.",
                controller=new{player.walkSpeed,player.runSpeed,player.jumpHeight,player.gravity,player.groundSnap,player.turnSpeed}},Formatting.Indented));
            EditorSceneManager.MarkSceneDirty(player.gameObject.scene);EditorSceneManager.SaveScene(player.gameObject.scene);AssetDatabase.SaveAssets();
            Debug.Log("Saved movement review cameras and two QA start markers; actor/controller/world geometry unchanged.");
        }
    }
}
