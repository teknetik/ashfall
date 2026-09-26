#if UNITY_EDITOR || DEBUG
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace AthenHill
{
    // Explicit development audition only. Source meshes, materials, LODs and
    // collision stay intact; this class never saves an asset or scene.
    public sealed class NativeTreeShadowReview
    {
        public const string CandidateName = "__QA tree LOD1 shadow casters";
        static readonly string[] Parts = { "branches", "leaves", "trunk" };
        readonly Dictionary<Renderer, ShadowCastingMode> originals = new Dictionary<Renderer, ShadowCastingMode>();
        GameObject candidate;
        GameObject sourceTree;
        long sourceLod0Triangles, candidateTriangles;
        public bool Active => candidate;

        public void Begin(GameObject tree)
        {
            if (Active)
            {
                if (tree != sourceTree) throw new InvalidOperationException("Restore the current tree shadow audition first.");
                return;
            }
            if (!tree) throw new ArgumentNullException(nameof(tree));
            var group = tree.GetComponent<LODGroup>();
            var lods = group ? group.GetLODs() : Array.Empty<LOD>();
            if (lods.Length != 2) throw new InvalidOperationException("Expected the two preserved source tree LODs.");
            var near = ValidateParts(lods[0].renderers, "LOD0");
            var far = ValidateParts(lods[1].renderers, "LOD1");
            var all = near.Concat(far).ToArray();
            if (all.Distinct().Count() != 6 || !new HashSet<Renderer>(all).SetEquals(tree.GetComponentsInChildren<Renderer>(true)))
                throw new InvalidOperationException("Unexpected tree renderer topology; inspect before auditioning.");
            var container = tree.transform.Find("Source LOD 1");
            if (!container || !new HashSet<Renderer>(far).SetEquals(container.GetComponentsInChildren<Renderer>(true)))
                throw new InvalidOperationException("Expected exactly three renderers under Source LOD 1.");
            // Validate before Instantiate, so an unexpected script cannot execute
            // Awake and a collider cannot briefly enter the physics scene.
            ValidateComponents(container.gameObject);
            var leaf = far.Single(r => Part(r.name) == "leaves");
            var leafMaterial = leaf.sharedMaterial;
            if (leaf.shadowCastingMode != ShadowCastingMode.TwoSided || !leafMaterial.HasProperty("_Cull")
                || leafMaterial.GetFloat("_Cull") != 0 || !leafMaterial.IsKeywordEnabled("_ALPHATEST_ON"))
                throw new InvalidOperationException("Leaf ShadowsOnly requires the existing two-sided alpha-clipped material.");
            try
            {
                sourceTree = tree;
                sourceLod0Triangles = near.Sum(Triangles);
                candidateTriangles = far.Sum(Triangles);
                foreach (var renderer in all) originals.Add(renderer, renderer.shadowCastingMode);
                // Cloning the complete, component-validated container preserves
                // its local hierarchy even under rotated/non-uniform ancestors.
                candidate = Object.Instantiate(container.gameObject, tree.transform, false);
                candidate.name = CandidateName;
                ValidateComponents(candidate);
                // Unity requires a GameObject's DontSave flags before applying
                // them to its Transform; reversing this order emits warnings.
                foreach (var transform in candidate.GetComponentsInChildren<Transform>(true))
                    transform.gameObject.hideFlags |= HideFlags.DontSave;
                foreach (var component in candidate.GetComponentsInChildren<Component>(true))
                    component.hideFlags |= HideFlags.DontSave;
                foreach (var renderer in candidate.GetComponentsInChildren<MeshRenderer>(true))
                {
                    renderer.shadowCastingMode = ShadowCastingMode.ShadowsOnly;
                    renderer.enabled = true;
                    renderer.gameObject.SetActive(true);
                }
                candidate.SetActive(true);
                foreach (var renderer in all) renderer.shadowCastingMode = ShadowCastingMode.Off;
            }
            catch
            {
                Restore();
                throw;
            }
        }

        static MeshRenderer[] ValidateParts(Renderer[] renderers, string label)
        {
            if (renderers == null || renderers.Length != 3 || renderers.Any(r => !(r is MeshRenderer)))
                throw new InvalidOperationException(label + " must contain three mesh renderers.");
            var meshes = renderers.Cast<MeshRenderer>().ToArray();
            if (!new HashSet<string>(meshes.Select(r => Part(r.name))).SetEquals(Parts))
                throw new InvalidOperationException(label + " must retain trunk, branches and leaves exactly once.");
            foreach (var renderer in meshes)
            {
                var filter = renderer.GetComponent<MeshFilter>();
                if (!filter || !filter.sharedMesh || renderer.sharedMaterials.Length != 1 || !renderer.sharedMaterial)
                    throw new InvalidOperationException(label + " has missing or unexpected mesh/material slots.");
            }
            return meshes;
        }

        static string Part(string name) => Parts.SingleOrDefault(part => name.EndsWith("_" + part, StringComparison.Ordinal));

        static void ValidateComponents(GameObject container)
        {
            foreach (var component in container.GetComponentsInChildren<Component>(true))
                if (!(component is Transform) && !(component is MeshFilter) && !(component is MeshRenderer))
                    throw new InvalidOperationException("Shadow source container contains a script, collider or unexpected component.");
        }

        static long Triangles(MeshRenderer renderer)
        {
            var mesh = renderer.GetComponent<MeshFilter>().sharedMesh;
            long total = 0;
            for (int submesh = 0; submesh < mesh.subMeshCount; submesh++) total += (long)mesh.GetIndexCount(submesh) / 3;
            return total;
        }

        public object Snapshot() => new
        {
            enabled = Active,
            purpose = "Transient LOD1 shadow-only geometry audition; visible source LODs unchanged",
            sourceLod0Triangles = Active ? (long?)sourceLod0Triangles : null,
            shadowTrianglesPerDraw = Active ? (long?)candidateTriangles : null,
            shadowRendererCount = Active ? candidate.GetComponentsInChildren<MeshRenderer>(true).Length : 0,
            sourceCasting = originals.Select(p => new { renderer = p.Key ? p.Key.name : "removed", original = p.Value.ToString(), current = p.Key ? p.Key.shadowCastingMode.ToString() : "removed" }).ToArray()
        };

        public void Restore()
        {
            // Disable immediately, including when Destroy is deferred until frame
            // end; detach so another audition in the same frame sees clean sources.
            if (candidate)
            {
                candidate.SetActive(false);
                candidate.transform.SetParent(null, true);
                if (Application.isPlaying) Object.Destroy(candidate);
                else Object.DestroyImmediate(candidate);
            }
            candidate = null;
            foreach (var pair in originals) if (pair.Key) pair.Key.shadowCastingMode = pair.Value;
            originals.Clear();
            sourceTree = null;
        }
    }
}
#endif
