using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthenHill.Editor
{
    /// Puts the six pistol mod attachments (art/pistol_mods_20260930, Art/Weapons/PistolMods/PistolMods.glb; one node per
    /// mod item id, authored in ScrapPistol.glb's own space) on the first-person view-model pistol and the held third-person
    /// pistol, and adds WeaponModVisuals so fitted mods appear and barrel mods move the muzzle. Refuses to run twice.
    public static class PistolModsInstall
    {
        const string ModelPath = "Assets/AthenHill/Art/Weapons/PistolMods/PistolMods.glb";
        const string PistolPath = "Assets/AthenHill/Art/OuterBerms/ScrapPistol.glb";
        // Muzzle points on the bore at the end of each barrel attachment, in glTF units/axes (art README).
        static readonly Dictionary<string, Vector3> GltfMuzzles = new Dictionary<string, Vector3>
        {
            ["barrel_bored_alloy"] = new Vector3(-1.28346f, .43038f, -.00548f),
            ["barrel_lattice_focused"] = new Vector3(-1.63083f, .43038f, -.00548f),
        };

        public static void InstallBatch()
        {
            int code = 0;
            try { Install(); } catch (Exception e) { Debug.LogException(e); code = 1; }
            EditorApplication.Exit(code);
        }

        [MenuItem("Athen Hill/Combat/Install pistol mod visuals")]
        public static void Install()
        {
            var modsAsset = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
            if (!modsAsset) throw new InvalidOperationException("Missing " + ModelPath);
            var pistolMeshes = AssetDatabase.LoadAllAssetsAtPath(PistolPath).OfType<Mesh>().ToArray();
            var scene = EditorSceneManager.OpenScene(ImportBaseline.ScenePath, OpenSceneMode.Single);
            if (UnityEngine.Object.FindAnyObjectByType<WeaponModVisuals>(FindObjectsInactive.Include)) throw new InvalidOperationException("Pistol mod visuals are already installed.");
            var session = UnityEngine.Object.FindAnyObjectByType<GameSession>();
            var combat = UnityEngine.Object.FindAnyObjectByType<PlayerCombat>(FindObjectsInactive.Include);
            var vm = UnityEngine.Object.FindAnyObjectByType<FirstPersonViewModel>(FindObjectsInactive.Include);
            var log = new List<object>();
            if (combat && combat.heldPistol) log.Add(Fit("held", combat.heldPistol.transform, combat.muzzlePoint, modsAsset, pistolMeshes, session, ShadowCastingMode.On));
            if (vm && vm.pistol) log.Add(Fit("first-person", vm.pistol, vm.muzzle, modsAsset, pistolMeshes, session, ShadowCastingMode.Off));
            if (log.Count == 0) throw new InvalidOperationException("No pistol found (PlayerCombat.heldPistol / FirstPersonViewModel.pistol).");
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            File.WriteAllText(Path.GetFullPath("../evidence/rendering/20260930/pistol-mods-install.json"), JsonConvert.SerializeObject(new { utc = DateTime.UtcNow.ToString("O"), log }, Formatting.Indented));
            Debug.Log("PISTOL_MODS installed: " + JsonConvert.SerializeObject(log));
        }

        static object Fit(string label, Transform holder, Transform muzzle, GameObject modsAsset, Mesh[] pistolMeshes, GameSession session, ShadowCastingMode shadows)
        {
            var pistolNode = holder.GetComponentsInChildren<MeshFilter>(true).FirstOrDefault(f => pistolMeshes.Contains(f.sharedMesh));
            if (!pistolNode) throw new InvalidOperationException(label + ": no ScrapPistol mesh under " + holder.name);
            var mods = (GameObject)PrefabUtility.InstantiatePrefab(modsAsset);
            mods.name = "Pistol mods"; mods.transform.SetParent(pistolNode.transform, false);
            mods.transform.localPosition = Vector3.zero; mods.transform.localRotation = Quaternion.identity; mods.transform.localScale = Vector3.one;
            int layer = pistolNode.gameObject.layer;
            foreach (var t in mods.GetComponentsInChildren<Transform>(true)) t.gameObject.layer = layer;
            foreach (var r in mods.GetComponentsInChildren<Renderer>(true)) { r.shadowCastingMode = shadows; r.receiveShadows = true; }
            // The item-id nodes may sit one level below the imported root.
            var parent = mods.transform;
            if (!parent.Find("barrel_bored_alloy")) parent = mods.GetComponentsInChildren<Transform>(true).First(t => t.name == "barrel_bored_alloy").parent;
            foreach (Transform c in parent) c.gameObject.SetActive(false);

            // Detect how the importer mapped glTF axes: the barrel extends to |x| ~ 1.28 in glTF units.
            var bored = parent.Find("barrel_bored_alloy");
            var mf = bored.GetComponentInChildren<MeshFilter>(true);
            var b = mf.sharedMesh.bounds; bool flipX = b.max.x > 1.0f;
            var overrides = new List<WeaponModVisuals.MuzzleOverride>();
            var muzzles = new Dictionary<string, object>();
            if (muzzle)
            {
                foreach (var kv in GltfMuzzles)
                {
                    var node = parent.Find(kv.Key); if (!node) continue;
                    var g = kv.Value; var local = flipX ? new Vector3(-g.x, g.y, g.z) : new Vector3(g.x, g.y, -g.z);
                    var world = mf.transform.TransformPoint(local);
                    var inMuzzleParent = muzzle.parent.InverseTransformPoint(world);
                    overrides.Add(new WeaponModVisuals.MuzzleOverride { itemId = kv.Key, localPosition = inMuzzleParent });
                    muzzles[kv.Key] = new[] { inMuzzleParent.x, inMuzzleParent.y, inMuzzleParent.z };
                }
            }
            var visuals = holder.gameObject.AddComponent<WeaponModVisuals>();
            visuals.session = session; visuals.mods = parent; visuals.muzzle = muzzle;
            visuals.defaultMuzzle = muzzle ? muzzle.localPosition : Vector3.zero; visuals.barrelMuzzles = overrides.ToArray();
            EditorUtility.SetDirty(visuals);
            return new { label, holder = holder.name, pistolNode = pistolNode.name, layer = LayerMask.LayerToName(layer), flipX, children = parent.Cast<Transform>().Select(t => t.name).ToArray(), defaultMuzzle = muzzle ? new[] { muzzle.localPosition.x, muzzle.localPosition.y, muzzle.localPosition.z } : null, muzzles };
        }
    }
}
