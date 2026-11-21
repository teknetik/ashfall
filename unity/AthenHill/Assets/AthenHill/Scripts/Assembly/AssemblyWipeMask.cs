using UnityEngine;
namespace AthenHill
{
    /// How much of one wipe zone has been cleaned: a small grid across the zone's two wide axes (SEAM.md section 7).
    /// The bench keeps one per zone (AssemblyBench.Wipe) and the Wipe verb writes it; the wipe shader, which is the
    /// integration pass's, reads it as a texture: 0 = as found (the family's dirty set), 1 = clean.
    /// U runs along the first wide axis of the zone's box and V along the second (see <see cref="Axes"/>); the zone's
    /// marker gives the box (AssemblyMarker.size, in the marker's own space, centred on it).
    public sealed class AssemblyWipeMask
    {
        public const int N = 16;
        public readonly string zone;
        /// Row-major, v * N + u. 0 dirty, 255 clean.
        public readonly byte[] cells = new byte[N * N];
        public int Cleaned { get; private set; }
        public float Coverage => (float)Cleaned / (N * N);
        /// Goes up on every change.
        public int Version { get; private set; }
        Texture2D texture; int textureVersion = -1;
        public AssemblyWipeMask(string zone) { this.zone = zone; }

        public bool Clean(int u, int v)
        {
            if (u < 0 || v < 0 || u >= N || v >= N || cells[v * N + u] != 0) return false;
            cells[v * N + u] = 255; Cleaned++; Version++; return true;
        }
        public void Fill() { for (int i = 0; i < cells.Length; i++) cells[i] = 255; Cleaned = cells.Length; Version++; }
        /// Leaves a share of the mask clean, the rest as found, in patches (always the same ones): 1 is Fill, 0 is Clear.
        /// For what an action shows at once (a punch mark, tinning) and for a poor job found out later (the race grinds).
        public void Set(float share)
        {
            int want = Mathf.RoundToInt(Mathf.Clamp01(share) * cells.Length);
            if (want >= cells.Length) { Fill(); return; }
            if (want <= 0) { Clear(); return; }
            var order = new int[cells.Length]; var rank = new float[cells.Length];
            for (int i = 0; i < cells.Length; i++) { order[i] = i; int u = i % N, v = i / N; rank[i] = Mathf.Sin(u * .9f + 1.3f) * Mathf.Cos(v * .7f + 2.1f) + .35f * Mathf.Sin((u + v) * 1.7f); }
            System.Array.Sort(rank, order);
            for (int k = 0; k < order.Length; k++) cells[order[k]] = (byte)(k < want ? 255 : 0);
            Cleaned = want; Version++;
        }
        public void Clear() { for (int i = 0; i < cells.Length; i++) cells[i] = 0; Cleaned = 0; Version++; }

        /// An N x N single-channel texture of the mask (bilinear, clamped), brought up to date when asked for.
        public Texture2D Texture
        {
            get
            {
                if (!texture) { texture = new Texture2D(N, N, TextureFormat.R8, false, true) { name = "wipe " + zone, wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear, hideFlags = HideFlags.DontSave }; textureVersion = -1; }
                if (textureVersion != Version) { texture.SetPixelData(cells, 0); texture.Apply(false); textureVersion = Version; }
                return texture;
            }
        }

        /// The zone box's axes: u and v across the surface, n through it. The kit's zone is a box round the area, so the
        /// thinnest side is the way through.
        public static void Axes(Vector3 size, out int u, out int v, out int n)
        {
            n = size.x <= size.y && size.x <= size.z ? 0 : size.y <= size.z ? 1 : 2;
            u = n == 0 ? 2 : 0; v = n == 1 ? 2 : n == 0 ? 1 : 1;
            if (n == 2) { u = 0; v = 1; }
        }
    }
}
