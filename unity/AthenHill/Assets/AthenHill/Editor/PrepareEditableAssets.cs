using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
namespace AthenHill.Editor
{
    public static class PrepareEditableAssets
    {
        public static ActorAnimation ConfigureActor(GameObject root,string source)
        {
            var actor=root.GetComponent<ActorAnimation>()??root.AddComponent<ActorAnimation>();
            actor.animationSource=root.GetComponentInChildren<Animation>();
            var clips=AssetDatabase.LoadAllAssetsAtPath(ImportBaseline.Art+source).OfType<AnimationClip>().ToArray();
            actor.idle=clips.First(c=>c.name=="idle");actor.walk=clips.First(c=>c.name=="walk");actor.run=clips.First(c=>c.name=="run");actor.talk=clips.First(c=>c.name=="talk");
            if(source=="npcs.glb") { actor.walkStrideSpeed=1.2f;actor.runStrideSpeed=3.5f; }
            return actor;
        }
        [MenuItem("Athen Hill/U1/Create editable actor variants and paving")]
        public static void Prepare()
        {
            if(EditorApplication.isPlaying) throw new System.Exception("Exit Play first.");
            Directory.CreateDirectory("Assets/AthenHill/Prefabs");Directory.CreateDirectory("Assets/AthenHill/Materials");
            foreach(var pair in new[]{("PlayerCandidate","player-candidate.glb"),("NpcImportAudition","npcs.glb")})
            {
                var root=GameObject.Find(pair.Item1);ConfigureActor(root,pair.Item2);
                string path="Assets/AthenHill/Prefabs/"+pair.Item1+".prefab";
                if(!File.Exists(path)) PrefabUtility.SaveAsPrefabAssetAndConnect(root,path,InteractionMode.AutomatedAction);
            }
            if(!GameObject.Find("Paving"))
            {
                var paving=GameObject.CreatePrimitive(PrimitiveType.Cube);paving.name="Paving";paving.transform.position=new Vector3(0,-.3f,0);paving.transform.localScale=new Vector3(120,.6f,90);Object.DestroyImmediate(paving.GetComponent<Collider>());
                var material=new Material(Shader.Find("Universal Render Pipeline/Lit"));material.name="Paving";material.color=new Color(.77f,.68f,.53f);material.SetFloat("_Smoothness",.08f);AssetDatabase.CreateAsset(material,"Assets/AthenHill/Materials/Paving.mat");paving.GetComponent<Renderer>().sharedMaterial=material;
                var joints=new GameObject("Paving Joints");
                var jointMat=new Material(material);jointMat.name="PavingJoint";jointMat.color=new Color(.54f,.48f,.39f);AssetDatabase.CreateAsset(jointMat,"Assets/AthenHill/Materials/PavingJoint.mat");
                for(int x=-56;x<=56;x+=4) Joint(joints.transform,jointMat,new Vector3(x,.006f,0),new Vector3(.035f,.01f,86));
                for(int z=-40;z<=40;z+=4) Joint(joints.transform,jointMat,new Vector3(0,.007f,z),new Vector3(116,.01f,.035f));
            }
            AssetDatabase.SaveAssets();EditorSceneManager.SaveOpenScenes();
        }
        static void Joint(Transform parent,Material mat,Vector3 p,Vector3 scale)
        {
            var go=GameObject.CreatePrimitive(PrimitiveType.Cube);go.name="Paving joint";go.transform.SetParent(parent);go.transform.position=p;go.transform.localScale=scale;go.GetComponent<Renderer>().sharedMaterial=mat;Object.DestroyImmediate(go.GetComponent<Collider>());
        }
    }
}
