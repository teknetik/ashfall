using System;
using System.Linq;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace AthenHill.Tests
{
    public class NativeTreeShadowReviewTests
    {
        GameObject tree;
        Mesh mesh;
        Material bark, leaves;
        NativeTreeShadowReview review;
        MeshRenderer[] near, far;

        [SetUp]
        public void SetUp()
        {
            tree = new GameObject("tree shadow review test");
            tree.transform.SetPositionAndRotation(new Vector3(5, 7, -3), Quaternion.Euler(0, 27, 0));
            tree.transform.localScale = new Vector3(2, 3, 1);
            mesh = new Mesh { name = "preserved test source" };
            mesh.vertices = new[] { Vector3.zero, Vector3.right, Vector3.up };
            mesh.triangles = new[] { 0, 1, 2 };
            var shader = Shader.Find("Athen Hill/Ward Tree");
            Assert.That(shader, Is.Not.Null);
            bark = new Material(shader);
            leaves = new Material(shader);
            leaves.SetFloat("_Cull", 0);
            leaves.EnableKeyword("_ALPHATEST_ON");
            near = MakeLod(0);
            far = MakeLod(1);
            tree.AddComponent<LODGroup>().SetLODs(new[] { new LOD(.5f, near), new LOD(.015f, far) });
            var collision = new GameObject("preserved independent collision");
            collision.transform.SetParent(tree.transform, false);
            collision.AddComponent<BoxCollider>();
            review = new NativeTreeShadowReview();
        }

        MeshRenderer[] MakeLod(int index)
        {
            var container = new GameObject("Source LOD " + index);
            container.transform.SetParent(tree.transform, false);
            container.transform.SetLocalPositionAndRotation(new Vector3(.1f, .2f, -.1f), Quaternion.Euler(-90, 15, 0));
            container.transform.localScale = Vector3.one * .9998f;
            return new[] { "trunk", "branches", "leaves" }.Select((part, i) =>
            {
                var child = new GameObject("WardTree_LOD" + index + "_" + part);
                child.transform.SetParent(container.transform, false);
                child.transform.localPosition = new Vector3(i, i * .1f, -i);
                child.AddComponent<MeshFilter>().sharedMesh = mesh;
                var renderer = child.AddComponent<MeshRenderer>();
                renderer.sharedMaterial = part == "leaves" ? leaves : bark;
                renderer.shadowCastingMode = part == "leaves" ? ShadowCastingMode.TwoSided : ShadowCastingMode.On;
                return renderer;
            }).ToArray();
        }

        [TearDown]
        public void TearDown()
        {
            review?.Restore();
            Object.DestroyImmediate(tree);
            Object.DestroyImmediate(mesh);
            Object.DestroyImmediate(bark);
            Object.DestroyImmediate(leaves);
        }

        [Test]
        public void ShadowCandidatePreservesVisibleMeshesLodsCollisionAndExactWorldTransforms()
        {
            var originalLods = tree.GetComponent<LODGroup>().GetLODs();
            var sources = near.Concat(far).ToArray();
            var enabled = sources.Select(r => r.enabled).ToArray();
            var matrices = sources.Select(r => r.localToWorldMatrix).ToArray();
            review.Begin(tree);
            Assert.That(review.Active, Is.True);
            var candidate = tree.transform.Find(NativeTreeShadowReview.CandidateName);
            Assert.That(candidate, Is.Not.Null);
            var shadows = candidate.GetComponentsInChildren<MeshRenderer>();
            Assert.That(shadows.Length, Is.EqualTo(3));
            Assert.That(candidate.GetComponentsInChildren<Collider>().Length, Is.Zero);
            Assert.That(tree.GetComponentsInChildren<Collider>().Length, Is.EqualTo(1));
            for (int i = 0; i < sources.Length; i++)
            {
                Assert.That(sources[i].shadowCastingMode, Is.EqualTo(ShadowCastingMode.Off));
                Assert.That(sources[i].enabled, Is.EqualTo(enabled[i]));
                Assert.That(sources[i].GetComponent<MeshFilter>().sharedMesh, Is.SameAs(mesh));
                Assert.That(sources[i].localToWorldMatrix, Is.EqualTo(matrices[i]));
            }
            foreach (var shadow in shadows)
            {
                var source = far.Single(r => r.name == shadow.name);
                Assert.That(shadow.shadowCastingMode, Is.EqualTo(ShadowCastingMode.ShadowsOnly));
                Assert.That(shadow.sharedMaterial, Is.SameAs(source.sharedMaterial));
                Assert.That(shadow.GetComponent<MeshFilter>().sharedMesh, Is.SameAs(source.GetComponent<MeshFilter>().sharedMesh));
                for (int i = 0; i < 16; i++) Assert.That(shadow.localToWorldMatrix[i], Is.EqualTo(source.localToWorldMatrix[i]).Within(.00001f));
            }
            var currentLods = tree.GetComponent<LODGroup>().GetLODs();
            for (int i = 0; i < originalLods.Length; i++)
            {
                CollectionAssert.AreEqual(originalLods[i].renderers, currentLods[i].renderers);
                Assert.That(currentLods[i].screenRelativeTransitionHeight, Is.EqualTo(originalLods[i].screenRelativeTransitionHeight));
            }
        }

        [Test]
        public void RestoreRecoversAllCastingFlagsAndRemovesOnlyOwnedCandidate()
        {
            near[0].shadowCastingMode = ShadowCastingMode.Off;
            var sources = near.Concat(far).ToArray();
            var flags = sources.Select(r => r.shadowCastingMode).ToArray();
            review.Begin(tree);
            review.Begin(tree); // Idempotent; do not duplicate casters.
            Assert.That(tree.GetComponentsInChildren<MeshRenderer>().Length, Is.EqualTo(9));
            review.Restore();
            review.Restore();
            Assert.That(review.Active, Is.False);
            Assert.That(tree.transform.Find(NativeTreeShadowReview.CandidateName), Is.Null);
            Assert.That(tree.GetComponentsInChildren<MeshRenderer>().Length, Is.EqualTo(6));
            CollectionAssert.AreEqual(flags, sources.Select(r => r.shadowCastingMode).ToArray());
            Assert.That(tree.GetComponentsInChildren<Collider>().Single().enabled, Is.True);
        }

        [Test]
        public void UnexpectedColliderInSourceContainerRejectsBeforeSourceFlagsChange()
        {
            far[0].gameObject.AddComponent<BoxCollider>();
            Assert.That(() => review.Begin(tree), Throws.TypeOf<InvalidOperationException>());
            Assert.That(review.Active, Is.False);
            Assert.That(near[0].shadowCastingMode, Is.EqualTo(ShadowCastingMode.On));
            Assert.That(far[2].shadowCastingMode, Is.EqualTo(ShadowCastingMode.TwoSided));
            Assert.That(tree.transform.Find(NativeTreeShadowReview.CandidateName), Is.Null);
        }

        [Test]
        public void UnexpectedPartTopologyRejectsBeforeCloningOrChangingSources()
        {
            far[1].name = "unrecognized part";
            Assert.That(() => review.Begin(tree), Throws.TypeOf<InvalidOperationException>());
            Assert.That(tree.GetComponentsInChildren<MeshRenderer>().Length, Is.EqualTo(6));
            Assert.That(near[0].shadowCastingMode, Is.EqualTo(ShadowCastingMode.On));
        }
    }
}
