using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    /// <summary>
    /// 3 October 2026: distinct characters for the six actors that shared the supplied Ward Guard
    /// (Carl: "Might be worth replacing the npc ward guards too and rebuilding their armour"; "make sure the weapons work
    /// with the new models"). Mira, Torr, Vex and Linn (city) and Wardens Ossa and Rell (Outer Berms) each get their own
    /// Meshy character from a Codex concept sheet (art/ward_npcs_20261003, meshy/ward-npcs-20261003): multi-image-to-3D,
    /// Meshy rig (24 bones, the names every actor uses) and library idle/talk clips fetched on that rig.
    ///
    /// Visuals only. Every NpcAgent root, NpcDefinition, dialogue node, voice, collider, route and save reference is
    /// kept. The old Ward Guard visual is deactivated, never deleted (rollback: <see cref="Rollback"/>):
    ///  * colonists: the child <c>npc_x/WardGuard</c> prefab instance is set inactive and the new prefab instance is added
    ///    beside it with the old child's local position/rotation;
    ///  * Wardens: <c>Warden Ossa</c>/<c>Warden Rell</c> ARE WardGuard prefab instances carrying the NpcAgent, so the
    ///    guard rig child is deactivated by an override and the root's own ActorAnimation/ActorLookAt are disabled.
    /// NpcAgent.actor is repointed to the new prefab's ActorAnimation. The old "Warden secured sidearm" (scrap pistol hung
    /// from the old rig's open hand) goes inactive with the old rig; the new prefabs carry measured weapon mounts:
    /// Ossa's scrap pistol sits in the drop-leg holster of her mesh (RightUpLeg), Rell's field rifle is slung on his back
    /// (Spine). Meshy rigs have no finger bones, so no NPC holds a weapon in an open hand.
    ///
    /// Batch: unity.sh LOG AthenHill.Editor.WardNpcInstall.RunBatch -nographics --steps import,prefab,install,verify
    ///        unity.sh LOG AthenHill.Editor.WardNpcInstall.RunBatch --steps capture --npcs mira,torr,vex   (graphics)
    /// </summary>
    public static class WardNpcInstall
    {
        const string Record = "../../meshy/ward-npcs-20261003/";
        const string ArtRoot = "Assets/AthenHill/Art/Imported/Meshy/WardNpcs";
        const string PrefabRoot = "Assets/AthenHill/Prefabs/WardNpcs";
        const string GuardPrefab = "Assets/AthenHill/Prefabs/WardGuard.prefab";
        const string PistolGlb = "Assets/AthenHill/Art/OuterBerms/ScrapPistol.glb";
        const string RifleGlb = "Assets/AthenHill/Art/Weapons/FieldRifle/FieldRifle.glb";
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Evidence = "../evidence/ward-npcs/20261003/";
        const string CameraRoot = "Ward NPC review cameras";
        public const string PistolMount = "Warden holstered sidearm", RifleMount = "Warden slung rifle";

        public enum Mount { None, ThighHolsterPistol, BackRifle }
        public class Spec
        {
            public string key, title, npcId, idle, talk, materialFrom; public float height; public Mount mount;
            public string Instance => "WardNpc " + title;
            public string Prefab => PrefabRoot + "/WardNpc_" + title + ".prefab";
            public string Folder => ArtRoot + "/" + title;
            public string Model => Folder + "/" + title + ".glb";
            public string Material => Folder + "/" + title + ".mat";
        }
        // Standing heights chosen per character (the guard made everyone 1.80 m); clips are each NPC's own Meshy clips.
        public static readonly Spec[] Specs = {
            new Spec{key="mira", title="Mira", npcId="npc_mira", height=1.68f, idle="idle_244", talk="talk_313"},
            new Spec{key="torr", title="Torr", npcId="npc_torr", height=1.76f, idle="idle_246", talk="talk_309"},
            new Spec{key="vex",  title="Vex",  npcId="npc_vex",  height=1.80f, idle="idle_243", talk="talk_314"},
            // Linn (history): Meshy's rig output lost the PBR set (base colour also wired as full emission, no normal/metal-roughness, so
            // metallic defaulted to 1). Its UVs and base colour equal the pre-rig model.glb (RMSE 0.6 %), so the material is
            // built from that file's import instead.
            new Spec{key="linn", title="Linn", npcId="npc_linn", height=1.63f, idle="idle_252", talk="talk_310"},   // rigged_fixed.glb already carries model.glb's PBR set (linn_material.py)
            new Spec{key="ossa", title="Ossa", npcId="npc_ossa", height=1.75f, idle="idle_243", talk="talk_313", mount=Mount.ThighHolsterPistol},
            new Spec{key="rell", title="Rell", npcId="npc_rell", height=1.88f, idle="idle_252", talk="talk_314", mount=Mount.BackRifle},
        };

        // Weapon mount tunables (metres / degrees, prefab space: the character faces +Z, its right side is +X in Unity's left-handed frame).
        // Holster: the outermost band of the right thigh between these height fractions is the holster's outer face.
        public static float HolsterLow = .40f, HolsterHigh = .58f, HolsterInset = .03f, GripAboveHolster = .025f, PistolLength = .26f;
        // Rifle: across the back, muzzle up behind the right shoulder.
        public static float RifleLength = .9f, RifleTilt = 32f, RifleHeight = .66f, RifleStandOff = .06f;

        // LOD switch points (relative screen height of the LODGroup bounds; ~1.9 m tall character, 60 deg vertical FOV):
        // LOD0 inside ~11 m, LOD1 to ~120 m, culled beyond.
        public static float LodSwitch0 = .14f, LodCull = .012f;

        /// Renderer-local bounds (the renderer's root bone frame) covering the skinned mesh over every clip, padded 12 %.
        static Bounds PoseBounds(SkinnedMeshRenderer r, GameObject host, AnimationClip[] clips)
        {
            var space = r.rootBone ? r.rootBone : r.transform; bool any = false; var b = new Bounds();
            foreach (var c in clips)
                for (int k = 0; k < 16; k++)
                {
                    c.SampleAnimation(host, c.length * k / 16f);
                    foreach (var p in Skin(r, space)) { if (!any) { b = new Bounds(p, Vector3.zero); any = true; } else b.Encapsulate(p); }
                }
            b.Expand(b.size * .12f);
            return b;
        }

        static float R(float v, int d = 4) => (float)Math.Round(v, d);
        static float[] V(Vector3 v) => new[] { R(v.x), R(v.y), R(v.z) };
        static string Clip(Spec s, string clip) => s.Folder + "/Clips/" + s.key + "_" + clip + ".anim";
        static IEnumerable<string> ClipNames(Spec s) => new[] { s.idle, s.talk };

        // ------------------------------------------------------------------ import
        public static object Import()
        {
            var report = new List<object>();
            foreach (var s in Specs)
            {
                Directory.CreateDirectory(s.Folder + "/Source"); Directory.CreateDirectory(s.Folder + "/Clips");
                var copied = new List<string>();
                void Copy(string from, string to)
                {
                    if (!File.Exists(from)) throw new FileNotFoundException("Missing Meshy record file " + from);
                    if (File.Exists(to) && File.ReadAllBytes(to).SequenceEqual(File.ReadAllBytes(from))) return;
                    File.Copy(from, to, true); copied.Add(to);
                }
                Copy(Record + s.key + "/rigged_fixed.glb", s.Model);   // built by meshy/ward-npcs-20261003/prepare_unity.sh: smooth normals, normal map re-baked against them, MikkTSpace tangents
                if (s.materialFrom != null) Copy(Record + s.key + "/" + s.materialFrom, s.Folder + "/" + s.title + "_Material.glb");
                foreach (var c in ClipNames(s)) Copy(Record + s.key + "/anim_only/" + c + ".glb", s.Folder + "/Source/" + c + ".glb");
                AssetDatabase.Refresh();
                foreach (var path in new[] { s.Model }.Concat(ClipNames(s).Select(c => s.Folder + "/Source/" + c + ".glb")))
                {
                    AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
                    var importer = AssetImporter.GetAtPath(path); if (!importer) throw new Exception("No importer for " + path);
                    var so = new SerializedObject(importer);
                    var method = so.FindProperty("importSettings.animationMethod") ?? throw new Exception("Expected glTFast import settings on " + path);
                    int legacy = Array.IndexOf(method.enumNames, "Legacy");
                    if (method.enumValueIndex != legacy) { method.enumValueIndex = legacy; so.ApplyModifiedPropertiesWithoutUndo(); importer.SaveAndReimport(); }
                    if (path != s.Model && !AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>().Any(c => c.legacy)) throw new Exception("No legacy clip in " + path);
                }
                if (!AssetDatabase.LoadAssetAtPath<GameObject>(s.Model)) throw new Exception("Model failed to import: " + s.Model);
                var tex = AssetDatabase.LoadAllAssetsAtPath(s.Model).OfType<Texture2D>().Select(t => new { t.name, t.width, t.height, format = t.format.ToString() }).ToArray();
                report.Add(new { s.key, copied, tex });
            }
            return report;
        }

        // ------------------------------------------------------------------ helpers
        /// Skinned vertex positions in <paramref name="space"/> (bone matrices x bind poses, as ImportWardGuard/ImportSalvageDealer).
        public static Vector3[] Skin(SkinnedMeshRenderer r, Transform space)
        {
            var mesh = r.sharedMesh; var bones = r.bones; var bind = mesh.bindposes;
            var m = new Matrix4x4[bones.Length];
            for (int i = 0; i < m.Length; i++) m[i] = space.worldToLocalMatrix * bones[i].localToWorldMatrix * bind[i];
            var v = mesh.vertices; var w = mesh.boneWeights; var p = new Vector3[v.Length];
            for (int i = 0; i < v.Length; i++)
            {
                var b = w[i];
                p[i] = m[b.boneIndex0].MultiplyPoint3x4(v[i]) * b.weight0 + m[b.boneIndex1].MultiplyPoint3x4(v[i]) * b.weight1
                     + m[b.boneIndex2].MultiplyPoint3x4(v[i]) * b.weight2 + m[b.boneIndex3].MultiplyPoint3x4(v[i]) * b.weight3;
            }
            return p;
        }

        static AnimationClip SourceClip(Spec s, string name)
        {
            var clip = AssetDatabase.LoadAllAssetsAtPath(s.Folder + "/Source/" + name + ".glb").OfType<AnimationClip>().FirstOrDefault(c => c && c.legacy);
            if (!clip) throw new Exception("No legacy source clip " + s.key + "/" + name);
            return clip;
        }

        static Transform ResolveHost(GameObject rig, Transform wrapper, AnimationClip clip, List<string> log)
        {
            var paths = AnimationUtility.GetCurveBindings(clip).Select(b => b.path).Distinct().ToArray();
            bool All(Transform t) => paths.All(p => p.Length == 0 || t.Find(p) != null);
            foreach (var t in rig.GetComponentsInChildren<Transform>(true).Prepend(wrapper))
                if (All(t)) { log.Add("clip paths resolve from '" + t.name + "'"); return t; }
            var first = paths.Select(p => p.Split('/')[0]).Distinct().ToArray();
            if (first.Length == 1 && rig.name != first[0])
            {
                log.Add("instance root renamed '" + rig.name + "' -> '" + first[0] + "'");
                rig.name = first[0];
                if (All(wrapper)) return wrapper;
            }
            throw new Exception("Clip paths do not resolve on the rig: " + string.Join(", ", paths.Take(5)));
        }

        static float CloseLoop(AnimationCurve curve, float seconds)
        {
            var keys = curve.keys; float end = keys[keys.Length - 1].time, start = keys[0].time;
            float seam = Mathf.Abs(keys[keys.Length - 1].value - keys[0].value);
            seconds = Mathf.Min(seconds, (end - start) * .25f);
            for (int i = 0; i < keys.Length; i++)
            {
                float w = Mathf.InverseLerp(end - seconds, end, keys[i].time);
                if (w <= 0) continue;
                w = w * w * (3 - 2 * w);
                keys[i].value = Mathf.Lerp(keys[i].value, keys[0].value, w);
            }
            curve.keys = keys;
            for (int i = 0; i < curve.length; i++) { AnimationUtility.SetKeyLeftTangentMode(curve, i, AnimationUtility.TangentMode.ClampedAuto); AnimationUtility.SetKeyRightTangentMode(curve, i, AnimationUtility.TangentMode.ClampedAuto); }
            return seam;
        }

        static float LowestSole(AnimationClip clip, GameObject host, SkinnedMeshRenderer smr, Transform space, int samples)
        {
            float low = float.MaxValue;
            for (int k = 0; k < samples; k++) { clip.SampleAnimation(host, clip.length * k / samples); low = Mathf.Min(low, Skin(smr, space).Min(p => p.y)); }
            return low;
        }

        static object DeriveClip(AnimationClip source, string target, Vector3 hipsOffset)
        {
            var clip = new AnimationClip { name = Path.GetFileNameWithoutExtension(target), legacy = true, frameRate = source.frameRate, wrapMode = WrapMode.Loop };
            int kept = 0, dropped = 0, hips = 0; float seam = 0;
            foreach (var binding in AnimationUtility.GetCurveBindings(source))
            {
                string prop = binding.propertyName;
                bool rotation = prop.StartsWith("m_LocalRotation") || prop.StartsWith("localRotation");
                bool hipsPosition = (prop.StartsWith("m_LocalPosition") || prop.StartsWith("localPosition")) && (binding.path == "Hips" || binding.path.EndsWith("/Hips"));
                if (!rotation && !hipsPosition) { dropped++; continue; }
                var curve = AnimationUtility.GetEditorCurve(source, binding);
                if (hipsPosition)
                {
                    float add = prop.EndsWith(".x") ? hipsOffset.x : prop.EndsWith(".y") ? hipsOffset.y : hipsOffset.z;
                    var keys = curve.keys; for (int i = 0; i < keys.Length; i++) keys[i].value += add; curve.keys = keys; hips++;
                }
                if (curve.length > 2) seam = Mathf.Max(seam, CloseLoop(curve, .3f));
                clip.SetCurve(binding.path, typeof(Transform), prop.Replace("m_LocalRotation", "localRotation").Replace("m_LocalPosition", "localPosition"), curve);
                kept++;
            }
            if (hips != 3) throw new Exception("Expected Hips x/y/z translation curves in " + source.name + ", found " + hips);
            clip.EnsureQuaternionContinuity();
            var existing = AssetDatabase.LoadAssetAtPath<AnimationClip>(target);
            if (existing) { EditorUtility.CopySerialized(clip, existing); Object.DestroyImmediate(clip); EditorUtility.SetDirty(existing); }
            else AssetDatabase.CreateAsset(clip, target);
            return new { target, length = R(source.length, 3), curvesKept = kept, curvesDropped = dropped, loopSeam = R(seam) };
        }

        static Transform Bone(Component root, string name) => root.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == name) ?? throw new Exception("No bone " + name + " under " + root.name);

        /// A unit-scale holder under <paramref name="bone"/> carrying a weapon model, posed in <paramref name="space"/>.
        /// The weapon's longest axis is its barrel (muzzle sign given), its up is +Y of the glTF; <paramref name="pivot"/>
        /// chooses the holder origin on the weapon: "grip" = average of the lower vertices (pistol), "centre" = bounds centre.
        static Transform MountWeapon(string glb, string holderName, Transform bone, float length, int muzzleSign, string pivot,
            Vector3 position, Vector3 barrelDir, Vector3 upDir, Transform space, List<string> log)
        {
            foreach (var old in bone.Cast<Transform>().Where(t => t.name == holderName).ToArray()) Object.DestroyImmediate(old.gameObject);
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(glb) ?? throw new FileNotFoundException(glb);
            var holder = new GameObject(holderName).transform; holder.SetParent(bone, false);
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(model); inst.transform.SetParent(holder, false);
            inst.transform.localPosition = Vector3.zero; inst.transform.localRotation = Quaternion.identity; inst.transform.localScale = Vector3.one;
            var pts = inst.GetComponentsInChildren<MeshFilter>(true).SelectMany(f => f.sharedMesh.vertices.Select(v => inst.transform.InverseTransformPoint(f.transform.TransformPoint(v)))).ToArray();
            if (pts.Length == 0) throw new Exception(glb + " has no meshes");
            var min = pts.Aggregate(Vector3.Min); var max = pts.Aggregate(Vector3.Max); var size = max - min;
            int axis = size.x >= size.z ? 0 : 2;   // barrel runs horizontally in both weapon GLBs
            if (muzzleSign == 0)
            {   // pistol: the grip hangs below the slide toward the rear, so the rear is where the low vertices sit
                var lower = pts.Where(p => p.y < min.y + size.y * .35f).ToArray();
                float rear = lower.Length > 0 ? lower.Average(p => p[axis]) - (min[axis] + max[axis]) * .5f : 0;
                muzzleSign = rear > 0 ? -1 : 1;
            }
            var barrel = Vector3.zero; barrel[axis] = muzzleSign;
            Vector3 origin;
            if (pivot == "grip")
            {
                var lower = pts.Where(p => p.y < min.y + size.y * .35f).ToArray();
                origin = lower.Length > 0 ? new Vector3(lower.Average(p => p.x), (min.y + max.y) * .5f, lower.Average(p => p.z)) : (min + max) * .5f;
            }
            else origin = (min + max) * .5f;
            float scale = length / size[axis];
            var rot = Quaternion.Inverse(Quaternion.LookRotation(barrel, Vector3.up));
            inst.transform.localRotation = rot; inst.transform.localScale = Vector3.one * scale;
            inst.transform.localPosition = -(rot * (origin * scale));
            // place the holder in prefab space, then keep it unit-scale in metres under the bone
            holder.SetPositionAndRotation(space.TransformPoint(position), space.rotation * Quaternion.LookRotation(barrelDir, upDir));
            var ls = holder.lossyScale; var sp = space.lossyScale;
            holder.localScale = new Vector3(holder.localScale.x / ls.x * sp.x, holder.localScale.y / ls.y * sp.y, holder.localScale.z / ls.z * sp.z);
            foreach (var r in inst.GetComponentsInChildren<Renderer>(true)) { r.shadowCastingMode = ShadowCastingMode.On; r.receiveShadows = true; }
            log.Add($"{holderName}: {Path.GetFileName(glb)} on {bone.name}, barrel axis {axis} sign {muzzleSign}, scale {scale:F4}, prefab-space position {position:F3}, barrel {barrelDir:F2}, up {upDir:F2}");
            return holder;
        }

        /// Measured on the skinned mesh in the idle's first frame (prefab space): returns the holder pose for the mount.
        static object PlaceMount(Spec s, Transform root, Transform host, SkinnedMeshRenderer smr, List<string> log)
        {
            if (s.mount == Mount.None) return null;
            var p = Skin(smr, root); var w = smr.sharedMesh.boneWeights; var bones = smr.bones;
            float H = p.Max(v => v.y) - p.Min(v => v.y);
            int[] Dominant(params string[] names)
            {
                var idx = names.Select(n => Array.FindIndex(bones, b => b.name == n)).Where(i => i >= 0).ToArray();
                return Enumerable.Range(0, p.Length).Where(i => idx.Contains(w[i].boneIndex0) && w[i].weight0 >= .5f).ToArray();
            }
            if (s.mount == Mount.ThighHolsterPistol)
            {
                // right thigh = +X side; outer face of the holster = the outermost vertices of the thigh band
                var thigh = Dominant("RightUpLeg").Where(i => p[i].y > H * HolsterLow && p[i].y < H * HolsterHigh).ToArray();
                if (thigh.Length < 50) throw new Exception("Too few right-thigh vertices for the holster: " + thigh.Length);
                float xmax = thigh.Max(i => p[i].x);
                if (xmax < .08f) throw new Exception("Right thigh is not on +X (outermost x " + xmax + "): check the facing");
                var face = thigh.Where(i => p[i].x > xmax - .03f).ToArray();
                var c = new Vector3(face.Average(i => p[i].x), face.Average(i => p[i].y), face.Average(i => p[i].z));
                var mouth = Dominant("RightUpLeg", "Hips").Where(i => p[i].x > xmax - .045f && Mathf.Abs(p[i].z - c.z) < .06f && p[i].y < H * .66f).ToArray();
                float top = mouth.Length > 0 ? mouth.Max(i => p[i].y) : c.y + .08f;
                top = Mathf.Min(top, c.y + .14f);
                var pos = new Vector3(c.x - HolsterInset, top + GripAboveHolster, c.z - .01f);
                // barrel down, slide top toward the front (+Z), grip to the rear
                MountWeapon(PistolGlb, PistolMount, Bone(host, "RightUpLeg"), PistolLength, 0, "grip", pos, Vector3.down, Vector3.forward, root, log);
                return new { holsterFaceCentre = V(c), holsterFaceVertices = face.Length, holsterTopY = R(top), holderPosition = V(pos), heightFractions = new[] { HolsterLow, HolsterHigh } };
            }
            else
            {
                var torso = Dominant("Spine", "Spine01", "Spine02", "neck").Where(i => p[i].y > H * (RifleHeight - .08f) && p[i].y < H * (RifleHeight + .08f) && Mathf.Abs(p[i].x) < .16f).ToArray();
                if (torso.Length < 50) throw new Exception("Too few back vertices for the rifle: " + torso.Length);
                float back = torso.Min(i => p[i].z);
                var pos = new Vector3(0, H * RifleHeight, back - RifleStandOff);
                float t = RifleTilt * Mathf.Deg2Rad;
                var muzzle = new Vector3(Mathf.Sin(t), Mathf.Cos(t), 0);   // up and toward the character's right shoulder
                // flat against the back like a slung rifle: its flank on the back, so its thin axis runs front-back; magazine down and
                // to the character's right, perpendicular to the barrel inside the back plane
                var flank = new Vector3(-Mathf.Cos(t), Mathf.Sin(t), 0);
                MountWeapon(RifleGlb, RifleMount, Bone(host, "Spine"), RifleLength, RifleArmourInstall.MuzzleSign, "centre", pos, muzzle, flank, root, log);
                return new { backSurfaceZ = R(back), backVertices = torso.Length, holderPosition = V(pos), tilt = RifleTilt };
            }
        }

        // ------------------------------------------------------------------ prefab
        public static object BuildPrefabs()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play first.");
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);   // the city scene is not touched here
            Directory.CreateDirectory(PrefabRoot);
            var all = new Dictionary<string, object>();
            foreach (var s in Specs)
            {
                var log = new List<string>();
                var model = AssetDatabase.LoadAssetAtPath<GameObject>(s.Model) ?? throw new Exception("Run the import step first: " + s.Model);
                var root = new GameObject("WardNpc_" + s.title);
                try
                {
                    var visual = new GameObject("Visual").transform; visual.SetParent(root.transform, false);
                    var rig = (GameObject)PrefabUtility.InstantiatePrefab(model); rig.transform.SetParent(visual, false);
                    var smrs = rig.GetComponentsInChildren<SkinnedMeshRenderer>(true);
                    // LOD0 (char1, ~20k) and LOD1 (char1_lod1, ~6-9k) from prepare_unity.sh, sharing one skin
                    var smr = smrs.FirstOrDefault(r => r.name == "char1") ?? throw new Exception(s.key + ": no char1 (LOD0) renderer");
                    var lod1 = smrs.FirstOrDefault(r => r.name == "char1_lod1") ?? throw new Exception(s.key + ": no char1_lod1 (LOD1) renderer");
                    if (smrs.Length != 2) throw new Exception(s.key + ": expected LOD0 + LOD1, found " + smrs.Length);
                    var sources = ClipNames(s).ToDictionary(c => c, c => SourceClip(s, c));
                    var host = ResolveHost(rig, visual, sources[s.idle], log);
                    foreach (var c in sources.Keys) if (ResolveHost(rig, visual, sources[c], new List<string>()) != host) throw new Exception(s.key + "/" + c + " binds to a different root");
                    var anim = host.GetComponent<Animation>(); if (!anim) anim = host.gameObject.AddComponent<Animation>();
                    foreach (var other in rig.GetComponentsInChildren<Animation>(true).Concat(visual.GetComponents<Animation>()).ToArray()) if (other != anim) Object.DestroyImmediate(other);

                    sources[s.idle].SampleAnimation(host.gameObject, 0);
                    var pts = Skin(smr, root.transform);
                    float standing = pts.Max(p => p.y) - pts.Min(p => p.y), scale = s.height / standing;
                    visual.localScale = Vector3.one * scale;
                    log.Add($"standing idle height {standing:F4} at import scale; uniform scale {scale:F4} -> {s.height} m");
                    var head = Bone(host, "Head"); var neck = Bone(host, "neck");
                    var front = host.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == "headfront");
                    if (front)
                    {
                        var d = root.transform.InverseTransformPoint(front.position) - root.transform.InverseTransformPoint(head.position);
                        if (d.z < 0) { visual.localRotation = Quaternion.Euler(0, 180, 0); log.Add("visual turned 180 degrees to face +Z"); }
                    }
                    var hipsT = Bone(host, "Hips");
                    var derived = new Dictionary<string, object>();
                    foreach (var c in sources.Keys)
                    {
                        float low = LowestSole(sources[c], host.gameObject, smr, root.transform, 24);
                        var offset = hipsT.parent.InverseTransformVector(new Vector3(0, -low, 0));
                        derived[c] = new { liftMetres = R(-low), clip = DeriveClip(sources[c], Clip(s, c), offset) };
                    }
                    AssetDatabase.SaveAssets();
                    var idle = AssetDatabase.LoadAssetAtPath<AnimationClip>(Clip(s, s.idle));
                    var talk = AssetDatabase.LoadAssetAtPath<AnimationClip>(Clip(s, s.talk));

                    var source = smr.sharedMaterial;
                    if (s.materialFrom != null)
                        source = AssetDatabase.LoadAllAssetsAtPath(s.Folder + "/" + s.title + "_Material.glb").OfType<Material>().FirstOrDefault() ?? throw new Exception(s.key + ": no material in " + s.materialFrom);
                    if (!source || !source.shader || source.shader.name.Contains("Error")) throw new Exception(s.key + ": material failed to import");
                    var mat = AssetDatabase.LoadAssetAtPath<Material>(s.Material);
                    if (!mat) { mat = new Material(source) { name = s.title }; AssetDatabase.CreateAsset(mat, s.Material); log.Add("material created from " + source.shader.name); }
                    else if (s.materialFrom != null && mat.GetTexture("normalTexture") == null) { EditorUtility.CopySerialized(source, mat); mat.name = s.title; EditorUtility.SetDirty(mat); log.Add("material rebuilt from " + s.materialFrom); }
                    // Cost (native bisect 3 Oct: six 60k always-skinned NPCs = 8.6 ms at cam_hill): skin only when visible, with
                    // fixed bounds that cover every sampled idle/talk pose, and stop animating off-screen.
                    var boundsInfo = new List<object>();
                    foreach (var r in new[] { smr, lod1 })
                    {
                        r.sharedMaterial = mat;
                        r.shadowCastingMode = ShadowCastingMode.On; r.receiveShadows = true; r.updateWhenOffscreen = false;
                        r.localBounds = PoseBounds(r, host.gameObject, sources.Values.ToArray());
                        boundsInfo.Add(new { r.name, centre = V(r.localBounds.center), size = V(r.localBounds.size), space = r.rootBone ? r.rootBone.name : r.name });
                    }
                    var lodGroup = visual.gameObject.AddComponent<LODGroup>();
                    lodGroup.SetLODs(new[] { new LOD(LodSwitch0, new Renderer[] { smr }), new LOD(LodCull, new Renderer[] { lod1 }) });
                    lodGroup.RecalculateBounds();
                    log.Add($"LODGroup: LOD0 {smr.sharedMesh.triangles.Length / 3} tris above {LodSwitch0} screen height, LOD1 {lod1.sharedMesh.triangles.Length / 3} tris above {LodCull}, culled below");

                    anim.playAutomatically = false; anim.clip = idle; anim.cullingType = AnimationCullingType.BasedOnRenderers;
                    AnimationUtility.SetAnimationClips(anim, new[] { idle, talk });
                    var actor = root.AddComponent<ActorAnimation>();
                    actor.animationSource = anim; actor.idle = idle; actor.walk = idle; actor.run = idle; actor.talk = talk;   // talking NPCs stand
                    actor.randomIdlePhase = true; actor.idleSpeedJitter = .08f;
                    var look = root.AddComponent<ActorLookAt>(); look.actor = actor; look.head = head; look.neck = neck;
                    idle.SampleAnimation(host.gameObject, 0);
                    var mount = PlaceMount(s, root.transform, host, smr, log);
                    var prefab = PrefabUtility.SaveAsPrefabAsset(root, s.Prefab, out bool ok);
                    if (!ok || !prefab) throw new Exception("Prefab save failed: " + s.Prefab);
                    all[s.key] = new { prefab = s.Prefab, scale = R(scale), host = host.name, log, clips = derived, mount, bounds = boundsInfo };
                }
                finally { Object.DestroyImmediate(root); }
            }
            AssetDatabase.SaveAssets();
            return all;
        }

        // ------------------------------------------------------------------ scene install
        static NpcAgent Npc(Spec s) => Object.FindObjectsByType<NpcAgent>(FindObjectsInactive.Include, FindObjectsSortMode.None)
            .SingleOrDefault(n => n.definition && n.definition.id == s.npcId) ?? throw new Exception("No NpcAgent with definition " + s.npcId);

        static bool IsGuardRoot(GameObject go) => PrefabUtility.IsAnyPrefabInstanceRoot(go) && PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(go) == GuardPrefab;

        /// The old guard visual of an NPC: (objects to deactivate, local pose of the new visual).
        static (GameObject[] old, Vector3 pos, Quaternion rot) OldVisual(NpcAgent npc)
        {
            if (IsGuardRoot(npc.gameObject))
            {
                var kids = npc.transform.Cast<Transform>().Where(t => !PrefabUtility.IsAddedGameObjectOverride(t.gameObject) && PrefabUtility.IsPartOfPrefabInstance(t.gameObject)).Select(t => t.gameObject).ToArray();
                return (kids, Vector3.zero, Quaternion.identity);
            }
            var guard = npc.transform.Cast<Transform>().FirstOrDefault(t => t.name == "WardGuard" && PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(t.gameObject) == GuardPrefab)
                ?? throw new Exception(npc.name + ": no WardGuard child visual");
            return (new[] { guard.gameObject }, guard.localPosition, guard.localRotation);
        }

        public static object Install()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play first.");
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            Directory.CreateDirectory(Evidence);
            var report = new Dictionary<string, object>();
            // Snapshot of gameplay data before the first install (kept; later runs compare against it in Verify).
            string beforeFile = Evidence + "before.json";
            if (!File.Exists(beforeFile)) File.WriteAllText(beforeFile, JsonConvert.SerializeObject(Snapshot(), Formatting.Indented));
            foreach (var s in Specs)
            {
                var npc = Npc(s);
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(s.Prefab) ?? throw new Exception("Run the prefab step first: " + s.Prefab);
                var (old, pos, rot) = OldVisual(npc);
                foreach (var go in old) if (go.activeSelf) { go.SetActive(false); EditorUtility.SetDirty(go); }
                if (IsGuardRoot(npc.gameObject))
                {
                    var oldActor = npc.GetComponent<ActorAnimation>(); if (oldActor && oldActor.enabled) oldActor.enabled = false;
                    var oldLook = npc.GetComponent<ActorLookAt>(); if (oldLook && oldLook.enabled) oldLook.enabled = false;
                    if (oldActor) PrefabUtility.RecordPrefabInstancePropertyModifications(oldActor);
                    if (oldLook) PrefabUtility.RecordPrefabInstancePropertyModifications(oldLook);
                    foreach (var go in old) PrefabUtility.RecordPrefabInstancePropertyModifications(go);
                }
                var inst = npc.transform.Cast<Transform>().FirstOrDefault(t => t.name == s.Instance)?.gameObject;
                if (inst && PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(inst) != s.Prefab) { Object.DestroyImmediate(inst); inst = null; }
                bool created = !inst;
                if (!inst) { inst = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene); inst.name = s.Instance; inst.transform.SetParent(npc.transform, false); }
                inst.SetActive(true);
                inst.transform.localPosition = pos; inst.transform.localRotation = rot;
                var ps = npc.transform.lossyScale; inst.transform.localScale = new Vector3(1 / ps.x, 1 / ps.y, 1 / ps.z);
                var actor = inst.GetComponent<ActorAnimation>();
                Undo.RecordObject(npc, "Ward NPC visual"); npc.actor = actor; EditorUtility.SetDirty(npc);
                if (PrefabUtility.IsPartOfPrefabInstance(npc)) PrefabUtility.RecordPrefabInstancePropertyModifications(npc);
                actor.idle.SampleAnimation(actor.animationSource.gameObject, 0);
                report[s.key] = new { npc = PathOf(npc.transform), created, deactivated = old.Select(o => o.name).ToArray(), visual = PathOf(inst.transform), localScale = V(inst.transform.localScale), guardRoot = IsGuardRoot(npc.gameObject) };
            }
            report["cameras"] = Cameras();
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene); AssetDatabase.SaveAssets();
            return report;
        }

        static string PathOf(Transform t) { var s = t.name; while (t.parent) { t = t.parent; s = t.name + "/" + s; } return s; }

        static object Snapshot() => Specs.Select(s =>
        {
            var n = Npc(s); var d = n.definition;
            return new
            {
                s.npcId, path = PathOf(n.transform), position = V(n.transform.position), rotation = V(n.transform.eulerAngles), d.displayName, d.role,
                definition = AssetDatabase.GetAssetPath(d), nodes = d.nodes.Select(x => new { x.id, voice = x.voice ? AssetDatabase.GetAssetPath(x.voice) : null, choices = x.choices.Select(c => c.id + ">" + c.next + ":" + c.action).ToArray() }).ToArray(),
                n.countsForCityVisit, colliders = n.GetComponentsInChildren<Collider>(true).Where(c => c.enabled).Select(c => c.GetType().Name + "@" + c.name).OrderBy(x => x).ToArray(),
            };
        }).ToArray();

        // ------------------------------------------------------------------ review cameras
        static string Cameras()
        {
            var scene = EditorSceneManager.GetActiveScene(); Physics.SyncTransforms();
            foreach (var old in scene.GetRootGameObjects().Where(g => g.name == CameraRoot).ToArray()) Object.DestroyImmediate(old);
            var root = new GameObject(CameraRoot);
            var template = Object.FindObjectsByType<Camera>(FindObjectsInactive.Include, FindObjectsSortMode.None).FirstOrDefault(c => c.name == "cam_checkpoint_player");
            var names = new List<string>();
            void Cam(string name, Vector3 pos, Vector3 look, float fov)
            {
                var go = new GameObject(name); go.transform.SetParent(root.transform, false);
                var cam = go.AddComponent<Camera>(); if (template) cam.CopyFrom(template); cam.enabled = false; cam.fieldOfView = fov; cam.nearClipPlane = .05f;
                // keep the lens clear of walls/props: pull the camera in front of the first collider between it and the subject
                var dir = pos - look; var npcRoot = Specs.Select(Npc).Select(n => n.transform).ToArray();
                foreach (var hit in Physics.RaycastAll(look, dir.normalized, dir.magnitude, ~0, QueryTriggerInteraction.Ignore).OrderBy(h => h.distance))
                {
                    if (npcRoot.Any(r => hit.transform.IsChildOf(r))) continue;
                    pos = look + dir.normalized * Mathf.Max(.45f, hit.distance - .15f); break;
                }
                go.transform.position = pos; go.transform.LookAt(look); names.Add(name);
            }
            foreach (var s in Specs)
            {
                var npc = Npc(s); var vis = npc.transform.Find(s.Instance); var f = Vector3.ProjectOnPlane(vis.forward, Vector3.up).normalized; var right = Vector3.Cross(Vector3.up, f);
                var feet = vis.position; float h = s.height;
                Cam("cam_npcs_" + s.key + "_face", feet + f * 1.05f + right * .18f + Vector3.up * (h * .93f), feet + Vector3.up * (h * .925f), 30);
                Cam("cam_npcs_" + s.key + "_body", feet + f * 3.0f + right * .9f + Vector3.up * 1.55f, feet + Vector3.up * (h * .5f), 42);
                if (s.mount == Mount.ThighHolsterPistol) Cam("cam_npcs_" + s.key + "_holster", feet + right * 1.3f + f * .7f + Vector3.up * 1.0f, feet + right * .15f + Vector3.up * (h * .5f), 34);
                if (s.mount == Mount.BackRifle) Cam("cam_npcs_" + s.key + "_back", feet - f * .9f + right * 2.1f + Vector3.up * 1.75f, feet - f * .2f + Vector3.up * (h * .66f), 40);
            }
            return string.Join(", ", names);
        }

        // ------------------------------------------------------------------ verify (-nographics)
        public static object Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var failures = new List<string>(); var report = new Dictionary<string, object>();
            foreach (var s in Specs)
            {
                var npc = Npc(s); var inst = npc.transform.Find(s.Instance);
                if (!inst) { failures.Add(s.key + ": visual missing"); continue; }
                var linked = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(inst.gameObject) == s.Prefab && PrefabUtility.IsAnyPrefabInstanceRoot(inst.gameObject);
                if (!linked) failures.Add(s.key + ": prefab link broken");
                if (!inst.gameObject.activeInHierarchy) failures.Add(s.key + ": visual inactive");
                if (npc.actor != inst.GetComponent<ActorAnimation>()) failures.Add(s.key + ": NpcAgent.actor not the new visual");
                var (old, _, _) = OldVisual(npc);
                if (old.Any(o => o.activeSelf)) failures.Add(s.key + ": old guard visual still active");
                if (IsGuardRoot(npc.gameObject) && npc.GetComponent<ActorAnimation>().enabled) failures.Add(s.key + ": old root ActorAnimation still enabled");
                var smr = inst.GetComponentsInChildren<SkinnedMeshRenderer>(true).OrderByDescending(r => r.sharedMesh.triangles.Length).ToArray();
                if (smr.Any(r => r.updateWhenOffscreen)) failures.Add(s.key + ": updateWhenOffscreen still on");
                if (!inst.GetComponentInChildren<LODGroup>()) failures.Add(s.key + ": no LODGroup");
                if (inst.GetComponent<ActorAnimation>().animationSource.cullingType != AnimationCullingType.BasedOnRenderers) failures.Add(s.key + ": Animation culling not BasedOnRenderers");
                foreach (var r in inst.GetComponentsInChildren<Renderer>(true))
                    foreach (var m in r.sharedMaterials)
                        if (!m || !m.shader || m.shader.name.Contains("Error") || m.shader.name == "Hidden/InternalErrorShader") failures.Add(s.key + ": missing/broken material on " + r.name);
                var missingScripts = inst.GetComponentsInChildren<Component>(true).Count(c => c == null);
                if (missingScripts > 0) failures.Add(s.key + ": " + missingScripts + " missing scripts");
                var actor = inst.GetComponent<ActorAnimation>(); var anim = actor ? actor.animationSource : null;
                int unresolved = 0;
                foreach (var clip in new[] { actor.idle, actor.talk }) unresolved += AnimationUtility.GetCurveBindings(clip).Count(b => b.path.Length > 0 && !anim.transform.Find(b.path));
                if (unresolved > 0) failures.Add(s.key + ": " + unresolved + " unresolved clip paths");
                actor.idle.SampleAnimation(anim.gameObject, 0);
                var pts = Skin(smr[0], inst); float h = pts.Max(p => p.y) - pts.Min(p => p.y), sole = pts.Min(p => p.y);
                if (Mathf.Abs(h - s.height) > .04f) failures.Add(s.key + ": height " + h);
                if (Mathf.Abs(sole) > .025f) failures.Add(s.key + ": sole off the ground " + sole);
                // talk must actually move
                var rest = smr[0].bones.ToDictionary(b => b, b => b.localRotation); float motion = 0;
                for (int k = 1; k < 12; k++) { actor.talk.SampleAnimation(anim.gameObject, actor.talk.length * k / 12f); motion = Mathf.Max(motion, smr[0].bones.Max(b => Quaternion.Angle(rest[b], b.localRotation))); }
                if (motion < 8) failures.Add(s.key + ": talk barely moves (" + motion + " deg)");
                actor.idle.SampleAnimation(anim.gameObject, 0);
                string mountName = s.mount == Mount.ThighHolsterPistol ? PistolMount : s.mount == Mount.BackRifle ? RifleMount : null;
                Transform mount = mountName == null ? null : inst.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == mountName);
                if (mountName != null && (!mount || !mount.gameObject.activeInHierarchy)) failures.Add(s.key + ": weapon mount " + mountName + " missing");
                report[s.key] = new
                {
                    visual = PathOf(inst), linked, height = R(h), sole = R(sole), triangles = smr[0].sharedMesh.triangles.Length / 3, lod1Triangles = smr.Length > 1 ? smr[1].sharedMesh.triangles.Length / 3 : 0, bones = smr[0].bones.Length,
                    idle = actor.idle.name, talk = actor.talk.name, talkMaxBoneDeg = R(motion, 1),
                    material = smr[0].sharedMaterial.name + " / " + smr[0].sharedMaterial.shader.name,
                    mount = mount ? new { name = mount.name, bone = mount.parent.name, worldPos = V(mount.position), lossyScale = V(mount.lossyScale),
                        overlapping = Overlaps(mount, npc.transform) } : null,
                };
            }
            // gameplay data unchanged since before the first install
            var before = File.Exists(Evidence + "before.json") ? JToken.Parse(File.ReadAllText(Evidence + "before.json")) : null;
            var now = JToken.Parse(JsonConvert.SerializeObject(Snapshot()));   // same float formatting as before.json
            File.WriteAllText(Evidence + "after.json", now.ToString(Formatting.Indented));
            bool same = before != null && JToken.DeepEquals(before, now);
            if (!same) failures.Add("gameplay snapshot differs from before.json (roots, definitions, dialogue, voices, colliders)");
            var cams = Object.FindObjectsByType<Camera>(FindObjectsInactive.Include, FindObjectsSortMode.None).Where(c => c.name.StartsWith("cam_npcs_")).Select(c => c.name).OrderBy(x => x).ToArray();
            if (cams.Length < Specs.Length * 2) failures.Add("review cameras missing: " + cams.Length);
            var guards = Object.FindObjectsByType<ActorLookAt>(FindObjectsInactive.Exclude, FindObjectsSortMode.None).Where(l => l.enabled && l.gameObject.activeInHierarchy).Select(l => PathOf(l.transform)).OrderBy(x => x).ToArray();
            var result = new { ok = failures.Count == 0, failures, npcs = report, gameplaySnapshotUnchanged = same, cameras = cams, activeLookAts = guards };
            Directory.CreateDirectory(Evidence); File.WriteAllText(Evidence + "verify.json", JsonConvert.SerializeObject(result, Formatting.Indented));
            if (failures.Count > 0) throw new Exception("Verify failed: " + string.Join("; ", failures));
            return result;
        }

        /// Scene colliders (not the NPC's own) inside the weapon's renderer bounds in the idle pose, shrunk 1 cm.
        static string[] Overlaps(Transform mount, Transform npc)
        {
            Physics.SyncTransforms();
            var rs = mount.GetComponentsInChildren<Renderer>(true); if (rs.Length == 0) return new string[0];
            var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
            return Physics.OverlapBox(b.center, b.extents - Vector3.one * .01f, Quaternion.identity, ~0, QueryTriggerInteraction.Ignore)
                .Where(c => !c.transform.IsChildOf(npc)).Select(c => PathOf(c.transform)).Distinct().ToArray();
        }

        // ------------------------------------------------------------------ rollback
        /// Restores the Ward Guard visuals: deactivates the new instances, reactivates the guard objects and repoints
        /// NpcAgent.actor at the guard ActorAnimation. The new prefabs stay in the project.
        public static object Rollback()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var log = new List<string>();
            foreach (var s in Specs)
            {
                var npc = Npc(s); var (old, _, _) = OldVisual(npc);
                foreach (var go in old) go.SetActive(true);
                var inst = npc.transform.Find(s.Instance); if (inst) inst.gameObject.SetActive(false);
                ActorAnimation guardActor;
                if (IsGuardRoot(npc.gameObject))
                {
                    guardActor = npc.GetComponent<ActorAnimation>(); guardActor.enabled = true;
                    var look = npc.GetComponent<ActorLookAt>(); if (look) look.enabled = true;
                }
                else guardActor = old[0].GetComponent<ActorAnimation>();
                npc.actor = guardActor; EditorUtility.SetDirty(npc);
                log.Add(s.key + " -> " + PathOf(guardActor.transform));
            }
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return log;
        }

        // ------------------------------------------------------------------ editor captures (graphics)
        /// Capture-only diagnostic: renders the baked bodies with this normal-map strength (temporary material copies).
        public static float NormalScaleOverride = -1; public static bool PlainLit, PlainNormal;
        public static object Capture(string[] keys)
        {
            var argv = Environment.GetCommandLineArgs(); int ni = Array.IndexOf(argv, "--normalscale"); if (ni >= 0) NormalScaleOverride = float.Parse(argv[ni + 1], System.Globalization.CultureInfo.InvariantCulture);
            int mb = Array.IndexOf(argv, "--mipbias"); float mipBias = mb >= 0 ? float.Parse(argv[mb + 1], System.Globalization.CultureInfo.InvariantCulture) : 0;
            if (mb >= 0) foreach (var sp in Specs) { var m = AssetDatabase.LoadAssetAtPath<Material>(sp.Material); if (m) foreach (var n in m.GetTexturePropertyNames()) { var t = m.GetTexture(n); if (t) t.mipMapBias = mipBias; } }
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            PlainLit = Environment.GetCommandLineArgs().Contains("--plainlit"); PlainNormal = Environment.GetCommandLineArgs().Contains("--plainnormal");
            var outDir = PlainLit ? Evidence + (PlainNormal ? "captures-plainnormal" : "captures-plainlit") : Evidence + (NormalScaleOverride >= 0 ? "captures-normal" + NormalScaleOverride : Array.IndexOf(Environment.GetCommandLineArgs(), "--mipbias") >= 0 ? "captures-mipbias" : "captures"); Directory.CreateDirectory(outDir);
            var clock = Object.FindFirstObjectByType<CityTimeOfDay>(FindObjectsInactive.Include);
            if (clock && clock.profile)
            {
                var f = clock.profile.Evaluate(13f);
                clock.keyLight.transform.rotation = Quaternion.Euler(f.keyEuler); clock.keyLight.color = f.keyColor; clock.keyLight.intensity = f.keyIntensity;
                if (clock.skyFill) { clock.skyFill.color = f.fillColor; clock.skyFill.intensity = f.fillIntensity; }
                RenderSettings.ambientMode = AmbientMode.Trilight; RenderSettings.ambientSkyColor = f.ambientSky; RenderSettings.ambientEquatorColor = f.ambientEquator; RenderSettings.ambientGroundColor = f.ambientGround; RenderSettings.fogColor = f.fogColor;
                var sky = new Material(clock.timeAwareSky);
                sky.SetColor("_Zenith", f.skyZenith); sky.SetColor("_Middle", f.skyMiddle); sky.SetColor("_Horizon", f.skyHorizon); sky.SetColor("_CloudLight", f.cloudLight); sky.SetColor("_CloudShade", f.cloudShade);
                sky.SetFloat("_Exposure", f.skyExposure); sky.SetFloat("_SunVisibility", f.sunVisibility); sky.SetVector("_SunDirection", -clock.keyLight.transform.forward);
                RenderSettings.skybox = sky; RenderSettings.sun = clock.keyLight;
                if (clock.gradingVolume && clock.gradingVolume.sharedProfile.TryGet<ColorAdjustments>(out var ca)) ca.postExposure.value = f.postExposure;
            }
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>();
            var cams = Object.FindObjectsByType<Camera>(FindObjectsInactive.Include, FindObjectsSortMode.None).GroupBy(c => c.name).ToDictionary(g => g.Key, g => g.First());
            var rt = new RenderTexture(1280, 960, 24, RenderTextureFormat.ARGB32) { antiAliasing = 1 }; var tex = new Texture2D(1280, 960, TextureFormat.RGB24, false);
            var log = new List<string>(); var baked = new List<GameObject>(); var hidden = new List<SkinnedMeshRenderer>();
            bool live = !Environment.GetCommandLineArgs().Contains("--bake");
            void Bake(GameObject vis)
            {
                // Live skinning (default): BakeMesh copies carry no tangents, which silently disables the normal map and
                // shows Meshy's near-flat base normals as facets. forceMatrixRecalculationPerRender makes an off-screen
                // Camera.Render() skin the current pose (unity-editor-pitfalls).
                if (live) { foreach (var x in vis.GetComponentsInChildren<SkinnedMeshRenderer>(true)) x.forceMatrixRecalculationPerRender = true; return; }   // nothing ticks the player loop in a batch method: render a CPU-baked copy of the posed body
                foreach (var x in vis.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                {
                    var mesh = new Mesh(); x.BakeMesh(mesh, false);
                    var g = new GameObject("__baked " + x.name, typeof(MeshFilter), typeof(MeshRenderer)); g.layer = x.gameObject.layer;
                    g.transform.SetPositionAndRotation(x.transform.position, x.transform.rotation);
                    g.GetComponent<MeshFilter>().sharedMesh = mesh; var mr = g.GetComponent<MeshRenderer>(); mr.sharedMaterials = x.sharedMaterials; mr.shadowCastingMode = x.shadowCastingMode;
                    if (PlainLit) mr.sharedMaterials = x.sharedMaterials.Select(m => { var c = new Material(Shader.Find("Universal Render Pipeline/Lit")); c.SetTexture("_BaseMap", m.GetTexture("baseColorTexture")); c.SetFloat("_Smoothness", .3f); c.SetFloat("_Metallic", 0); if (PlainNormal) { c.SetTexture("_BumpMap", m.GetTexture("normalTexture")); c.EnableKeyword("_NORMALMAP"); } return c; }).ToArray();
                    if (NormalScaleOverride >= 0) mr.sharedMaterials = x.sharedMaterials.Select(m => { var c = new Material(m); c.SetFloat("normalTexture_scale", NormalScaleOverride); return c; }).ToArray();
                    x.enabled = false; baked.Add(g); hidden.Add(x);
                }
            }
            void Shot(string camName, string file)
            {
                if (!cams.TryGetValue(camName, out var src)) { log.Add("missing camera " + camName); return; }
                var go = new GameObject("__cap"); var cam = go.AddComponent<Camera>(); cam.CopyFrom(src); cam.enabled = false; cam.nearClipPlane = .05f; cam.farClipPlane = 650;
                var d = go.AddComponent<UniversalAdditionalCameraData>(); d.renderPostProcessing = true; d.antialiasing = AntialiasingMode.SubpixelMorphologicalAntiAliasing; d.renderShadows = true; d.volumeLayerMask = ~0; d.volumeTrigger = go.transform;
                go.transform.SetPositionAndRotation(src.transform.position, src.transform.rotation);
                cam.targetTexture = rt; for (int i = 0; i < 3; i++) cam.Render();
                RenderTexture.active = rt; tex.ReadPixels(new Rect(0, 0, 1280, 960), 0, 0); tex.Apply(); File.WriteAllBytes(System.IO.Path.Combine(outDir, file + ".png"), tex.EncodeToPNG());
                RenderTexture.active = null; cam.targetTexture = null; Object.DestroyImmediate(go); log.Add(file + " from " + camName);
            }
            foreach (var s in Specs.Where(x => keys.Length == 0 || keys.Contains(x.key)))
            {
                var npc = Npc(s); var inst = npc.transform.Find(s.Instance).gameObject; var actor = inst.GetComponent<ActorAnimation>();
                foreach (var g in baked) Object.DestroyImmediate(g); baked.Clear(); foreach (var x in hidden) x.enabled = true; hidden.Clear();
                actor.idle.SampleAnimation(actor.animationSource.gameObject, actor.idle.length * .3f); Bake(inst);
                Shot("cam_npcs_" + s.key + "_face", s.key + "_face_idle");
                foreach (var g in baked) Object.DestroyImmediate(g); baked.Clear(); foreach (var x in hidden) x.enabled = true; hidden.Clear();
                actor.talk.SampleAnimation(actor.animationSource.gameObject, actor.talk.length * .45f); Bake(inst);
                Shot(s.mount == Mount.ThighHolsterPistol ? "cam_npcs_" + s.key + "_holster" : s.mount == Mount.BackRifle ? "cam_npcs_" + s.key + "_back" : "cam_npcs_" + s.key + "_body", s.key + (s.mount == Mount.None ? "_body_talk" : "_weapon_talk"));
                if (s.mount == Mount.None) continue;
                foreach (var g in baked) Object.DestroyImmediate(g); baked.Clear(); foreach (var x in hidden) x.enabled = true; hidden.Clear();
                actor.idle.SampleAnimation(actor.animationSource.gameObject, actor.idle.length * .3f); Bake(inst);
                Shot("cam_npcs_" + s.key + "_body", s.key + "_body_idle");
            }
            foreach (var g in baked) Object.DestroyImmediate(g); foreach (var x in hidden) x.enabled = true;
            rt.Release(); Object.DestroyImmediate(tex);
            File.WriteAllText(outDir + "/captures.txt", string.Join("\n", log) + "\n");
            return log;   // scene not saved
        }

        // ------------------------------------------------------------------ batch
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "--steps"); int k = Array.IndexOf(args, "--npcs");
            var steps = i >= 0 ? args[i + 1].Split(',') : new[] { "import", "prefab", "install", "verify" };
            var keys = k >= 0 ? args[k + 1].Split(',') : new string[0];
            try
            {
                var results = new Dictionary<string, object>();
                foreach (var st in steps)
                {
                    object result = st switch
                    {
                        "import" => Import(),
                        "prefab" => BuildPrefabs(),
                        "install" => Install(),
                        "verify" => Verify(),
                        "capture" => Capture(keys),
                        "rollback" => Rollback(),
                        "texinfo" => Specs.ToDictionary(sp => sp.key, sp => { var m = AssetDatabase.LoadAssetAtPath<Material>(sp.Material); return m.GetTexturePropertyNames().Select(n => (n, t: m.GetTexture(n) as Texture2D)).Where(x => x.t).Select(x => x.n + ": " + x.t.name + " " + x.t.width + " " + x.t.graphicsFormat + " srgb=" + x.t.isDataSRGB + " mips=" + x.t.mipmapCount + " streaming=" + x.t.streamingMipmaps).ToArray(); }),
                        _ => throw new Exception("unknown step " + st),
                    };
                    results[st] = result;
                    Debug.Log("WardNpcInstall " + st + ": " + JsonConvert.SerializeObject(result));
                }
                Directory.CreateDirectory(Evidence);
                string file = Evidence + "install-log.json";
                var all = File.Exists(file) ? JObject.Parse(File.ReadAllText(file)) : new JObject();
                foreach (var kv in results) all[kv.Key] = JToken.FromObject(kv.Value);
                File.WriteAllText(file, all.ToString(Formatting.Indented));
                Debug.Log("WardNpcInstall OK");
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); Debug.Log("WardNpcInstall FAILED: " + e.Message); EditorApplication.Exit(1); }
        }
    }
}
