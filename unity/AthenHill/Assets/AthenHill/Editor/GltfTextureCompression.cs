using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using GLTFast;
using GLTFast.Addons;
using Unity.Collections;
using UnityEditor;
using UnityEngine;
using UnityEngine.Experimental.Rendering;

namespace AthenHill.Editor
{
    /// <summary>
    /// 1 October 2026 texture memory pass. glTFast 6.20's editor importer decodes images embedded in .glb files with
    /// Texture2D.LoadImage, so every embedded texture became an uncompressed RGBA32/ARGB32/RGB24 sub-asset that never
    /// streams (~3.9 GB of the scene's 4.7 GB of non-streamed textures). The importer has no compression setting and no
    /// external-object remapping, but it runs glTFast's public import add-ons (GLTFast.Addons.ImportAddonRegistry), so
    /// this add-on takes over the decode of embedded PNG/JPEG images at editor import and:
    ///   * decodes exactly as glTFast does (same sRGB/linear flag, same mip chain, same orientation, same readability),
    ///   * compresses power-of-two images to BC7 (8 bpp, all four channels kept, sRGB or linear as glTFast chose; any
    ///     channel packing such as glTF ORM or RGB normals is unchanged, so materials and shaders see the same data).
    /// Sub-asset names, types and file IDs are unchanged, so materials, prefabs and scenes keep their references.
    /// NPOT images with mipmaps (Unity refuses to block-compress them) stay uncompressed. The textures are not mipmap
    /// streamed: flagging an in-memory import texture as streaming crashed Unity (TextureStreamingManager, 1 Oct).
    /// Meshes are untouched.
    ///
    /// Import results only change when a .glb is (re)imported. Rollback: set ATHEN_GLTF_COMPRESS=0 for the Unity run (or
    /// DefaultOn = false) and force-reimport the .glb files listed in unity/evidence/texture-memory/20261001.
    /// </summary>
    [InitializeOnLoad]
    public static class GltfTextureCompression
    {
        /// On since 1 Oct 16:40 (24 scene .glb files reimported and verified with it); ATHEN_GLTF_COMPRESS=0/1 overrides
        /// per Unity run. Keep it on, or a later reimport silently brings back ~2.8 GB of uncompressed textures.
        public const bool DefaultOn = true;

        public static bool Enabled
        {
            get
            {
                var e = Environment.GetEnvironmentVariable("ATHEN_GLTF_COMPRESS");
                return e == "1" || (e != "0" && DefaultOn);
            }
        }

        /// Per-domain report of what the add-on did (for batch steps): texture name, size, result.
        public static readonly List<string> Report = new List<string>();
        static bool registered;

        static GltfTextureCompression()
        {
            Register();
            // glTFast clears its add-on registry when play mode starts (RuntimeInitializeOnLoad); register again after.
            EditorApplication.playModeStateChanged += s =>
            {
                if (s == PlayModeStateChange.EnteredEditMode) { registered = false; Register(); }
            };
        }

        static void Register()
        {
            if (registered) return;
            ImportAddonRegistry.RegisterImportAddon(new Addon());
            registered = true;
        }

        class Addon : ImportAddon<Instance> { }

        class Instance : ImportAddonInstance, ITextureImageLoader
        {
            public override bool SupportsGltfExtension(string extensionName) => false;

            public override void Inject(GltfImportBase gltfImport)
            {
                if (Enabled) gltfImport.AddImportAddonInstance(this);
            }

            int compressedHere;

            public override void Inject(IInstantiator instantiator) { }

            public override void Dispose() { }

            // Per-texture override path: not used (the decision is per image, below).
            public bool IsAbleToLoad(GLTFast.Schema.TextureBase texture, out int imageIndex)
            {
                imageIndex = -1;
                return false;
            }

            // Embedded (buffer view / data URI) images reach this check before glTFast's own PNG/JPEG decode.
            public bool IsAbleToLoad(ReadOnlySpan<byte> data) => ImageFormatDetection.IsPngOrJpeg(data);

            public Task<ImageResult> LoadImage(NativeArray<byte>.ReadOnly data, bool linear, bool readable,
                bool generateMipMaps, CancellationToken cancellationToken)
            {
                // Identical to glTFast's ImageConversionImageLoader, but kept readable until compressed.
                var flags = TextureCreationFlags.DontUploadUponCreate | TextureCreationFlags.DontInitializePixels;
                if (generateMipMaps) flags |= TextureCreationFlags.MipChain;
                var tex = new Texture2D(4, 4, linear ? GraphicsFormat.R8G8B8A8_UNorm : GraphicsFormat.R8G8B8A8_SRGB, flags);
                if (!tex.LoadImage(data.AsReadOnlySpan(), false))
                {
                    UnityEngine.Object.DestroyImmediate(tex);
                    return Task.FromResult(ImageResult.Null);
                }
                // Block compression with a mip chain needs power-of-two sizes in this Unity (EditorUtility.CompressTexture
                // refuses NPOT); those few textures stay exactly as glTFast makes them.
                string result;
                bool pot = Mathf.IsPowerOfTwo(tex.width) && Mathf.IsPowerOfTwo(tex.height);
                bool canCompress = tex.width % 4 == 0 && tex.height % 4 == 0 && (pot || tex.mipmapCount == 1);
                if (canCompress)
                {
                    var before = tex.format;
                    Color32[] src = null;
                    try { src = tex.GetPixels32(0); } catch (Exception) { }
                    EditorUtility.CompressTexture(tex, TextureFormat.BC7, TextureCompressionQuality.Normal);
                    result = before + "->" + tex.graphicsFormat;
                    if (GraphicsFormatUtility.IsCompressedFormat(tex.graphicsFormat))
                    {
                        compressedHere++;
                        try { if (src != null) result += " " + Psnr(src, tex.GetPixels32(0)); }
                        catch (Exception e) { result += " psnr n/a (" + e.GetType().Name + ")"; }
                    }
                }
                else result = "kept " + tex.format + (pot ? " (size not a multiple of 4)" : " (NPOT with mipmaps)");
                // Same end state as glTFast's own LoadImage(data, markNonReadable: !readable). No mipmap streaming flag:
                // setting m_StreamingMipmaps on an in-memory texture (SerializedObject) crashed Unity's
                // TextureStreamingManager when the import unloaded it (1 Oct 16:05 and 16:29), so these stay non-streamed.
                if (!readable) tex.Apply(false, true);
                Report.Add($"{tex.width}x{tex.height} mips {tex.mipmapCount} {(linear ? "linear" : "sRGB")} {result}");
                return Task.FromResult(new ImageResult(tex));
            }

            /// PSNR (dB) of the decoded BC7 mip 0 against the decoded source, per channel (RGB, A), plus the worst pixel error.
            static string Psnr(Color32[] a, Color32[] b)
            {
                if (a.Length != b.Length) return "psnr n/a (size)";
                double r = 0, g = 0, bl = 0, al = 0; int worst = 0;
                for (int i = 0; i < a.Length; i++)
                {
                    int dr = a[i].r - b[i].r, dg = a[i].g - b[i].g, db = a[i].b - b[i].b, da = a[i].a - b[i].a;
                    r += dr * dr; g += dg * dg; bl += db * db; al += da * da;
                    worst = Math.Max(worst, Math.Max(Math.Max(Math.Abs(dr), Math.Abs(dg)), Math.Max(Math.Abs(db), Math.Abs(da))));
                }
                double n = a.Length;
                string P(double se) => se <= 0 ? "inf" : (10 * Math.Log10(255.0 * 255.0 / (se / n))).ToString("F1");
                return $"psnr R {P(r)} G {P(g)} B {P(bl)} A {P(al)} maxerr {worst}";
            }
        }
    }
}
