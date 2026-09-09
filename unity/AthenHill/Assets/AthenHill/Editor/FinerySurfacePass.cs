using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace AthenHill.Editor
{
    // Material-only repair of the existing hand-authored building; original meshes stay linked.
    public static class FinerySurfacePass
    {
        const string Folder = WardBuildingMaterials.Folder + "/Finery";
        const string Evidence = "../evidence/quality/20260909/finery";

        [MenuItem("Athen Hill/Quality/Repair Finery material scale")]
        public static void Install()
        {
            if (EditorApplication.isPlaying) throw new InvalidOperationException("Exit Play before surface repair.");
            if (EditorSceneManager.GetActiveScene().path != ImportBaseline.ScenePath) throw new InvalidOperationException("Open the existing saved city.");
            if (File.Exists(Evidence + "/surface-install.json")) throw new InvalidOperationException("Finery surface pass already recorded; preserve later Inspector changes.");
            var root = GameObject.Find("Phase 1 Finery frontage");
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (!root || !chunks) throw new InvalidOperationException("Expected saved Finery and render chunks.");
            var source = root.GetComponentsInChildren<MeshRenderer>(true).Where(r => !r.transform.IsChildOf(root.transform.Find("Entrance light"))).ToArray();
            var sourcePath = Path.GetFullPath(Path.Combine(Application.dataPath,"../../../art/phase1_20260908/finery-mesh-data.json"));
            var expectedNames = JArray.Parse(File.ReadAllText(sourcePath)).Select(p=>(string)p["name"]).OrderBy(n=>n).ToArray();
            if (!source.Select(r=>r.name).OrderBy(n=>n).SequenceEqual(expectedNames)) throw new InvalidOperationException("Finery parts differ from retained authored source; inspect before changing materials.");
            var before = source.Select(r => new { path = PathOf(r.transform), material = AssetDatabase.GetAssetPath(r.sharedMaterial), mesh = AssetDatabase.GetAssetPath(r.GetComponent<MeshFilter>().sharedMesh) }).ToArray();
            var gameplay = DistrictCityPass.GameplaySignature();
            var colliderState = ColliderState(root);
            Directory.CreateDirectory(Folder); Directory.CreateDirectory(Evidence);
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var plaster = Variant("Finery mineral plaster", Shared("WardPlaster"), 1f / (3f * .65f), new Color(.98f,.97f,.94f));
            var stone = Variant("Finery cut stone", Shared("WardStone"), 1f / (2f * .65f), Color.white);
            var concrete = Variant("Finery mortar and soffit", Shared("WardConcrete"), 1f / (1.23f * .65f), new Color(.87f,.83f,.75f));
            var painted = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/Quality/Lamps/Materials/WardLampPaint.mat");
            var steel = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/Quality/Lamps/Materials/WardLampSteel.mat");
            var bronze = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/Quality/Lamps/Materials/WardLampBronze.mat");
            var rubber = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/Quality/Lamps/Materials/WardLampRubber.mat");
            if (!painted || !steel || !bronze || !rubber) throw new InvalidOperationException("Expected retained utility hardware PBR materials.");
            var door = Variant("Finery coated door", painted, 1f/.75f, new Color(.82f,.86f,.84f));
            var metal = Variant("Finery hardware steel", steel, 1f/.75f, Color.white);
            var brass = Variant("Finery hardware bronze", bronze, 1f/.75f, Color.white);
            var tank = Variant("Finery repaired service sheet", Shared("WardWornSteel"), .5f, Color.white);
            var membrane = Variant("Finery sealed roof membrane", rubber, 1f/.75f, Color.white);
            var shutters = new Dictionary<string,Material>();
            for (int i = 0; i < 5; i++)
            {
                string key = i<2 ? "Lower shutter " + i : "Upper shutter " + (i-2);
                var m = Variant("Finery shutter " + i, painted, 1f/.75f, new Color(.81f+i*.022f,.88f+i*.012f,.84f+i*.014f));
                m.SetTextureOffset("_BaseMap", new Vector2(.137f*i,.283f*i)); EditorUtility.SetDirty(m); shutters.Add(key,m);
            }
            // Everything needed has been checked before assigning source materials.
            chunks.ShowSources(true);
            foreach (var renderer in source)
            {
                var n = renderer.name; Material material;
                if (n.Contains("shaded recess")) material = door;
                else if (n.Contains("louvre") || n.Contains("mullion")) material = shutters.First(p=>n.StartsWith(p.Key,StringComparison.Ordinal)).Value;
                else if (n.StartsWith("Door handle") || n.StartsWith("Door hinge") || n.StartsWith("Service pipe strap")) material = brass;
                else if (n.StartsWith("Door kickplate") || n.StartsWith("Tank band") || n.StartsWith("Tank feed pipe") || n.Contains("vent fin")) material = metal;
                else if (n.StartsWith("Door leaf") || n.StartsWith("Door inset")) material = door;
                else if (n.StartsWith("Rooftop water") || n.Contains("vent hood")) material = tank;
                else if (n.Contains("membrane")) material = membrane;
                else if (n.Contains("soffit")) material = concrete;
                else if (n.Contains("wall core") || n.Contains("wall pier") || n.Contains("infill") || n == "Sign fascia" || n.Contains("parapet")) material = plaster;
                else material = stone;
                renderer.sharedMaterial = material; EditorUtility.SetDirty(renderer); PrefabUtility.RecordPrefabInstancePropertyModifications(renderer);
            }
            if (gameplay != DistrictCityPass.GameplaySignature() || colliderState != ColliderState(root)) throw new InvalidOperationException("Unexpected gameplay/collider change.");
            AssetDatabase.SaveAssets(); StaticRenderChunksEditor.Rebuild(chunks);
            EditorSceneManager.MarkSceneDirty(root.scene); EditorSceneManager.SaveOpenScenes();
            File.WriteAllText(Evidence + "/surface-install.json", JsonConvert.SerializeObject(new { utc = DateTime.UtcNow, before, after = source.Select(r=>new { path=PathOf(r.transform), material=AssetDatabase.GetAssetPath(r.sharedMaterial) }), gameplayPreserved=true, collidersPreserved=true, meshesPreserved=true, acceptance="Native matched front/door/back/sides/material close views pending; geometry and rear service articulation still open" }, Formatting.Indented));
        }

        static Material Shared(string slot)
        {
            var material = AssetDatabase.LoadAssetAtPath<Material>(WardBuildingMaterials.Folder + "/" + slot + "/" + slot + ".mat");
            if (!material) throw new InvalidOperationException("Prepare shared building material: " + slot);
            return material;
        }
        static Material Variant(string name, Material source, float scale, Color tint)
        {
            string path=Folder+"/"+name+".mat";
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material) return material;
            material = new Material(source) { name=name }; material.SetTextureScale("_BaseMap",Vector2.one*scale); material.SetColor("_BaseColor",tint);
            AssetDatabase.CreateAsset(material,path); return material;
        }
        static string ColliderState(GameObject root) => JsonConvert.SerializeObject(root.GetComponentsInChildren<Collider>(true).Select(c=>new{path=PathOf(c.transform),c.enabled,center=new[]{c.bounds.center.x,c.bounds.center.y,c.bounds.center.z},size=new[]{c.bounds.size.x,c.bounds.size.y,c.bounds.size.z}}));
        static string PathOf(Transform t) => t.parent ? PathOf(t.parent)+"/"+t.name : t.name;
    }
}
