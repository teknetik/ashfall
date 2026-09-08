using UnityEngine;

namespace AthenHill
{
    // Authoring data only; the Editor bakes these into an ordinary saved Mesh asset.
    [RequireComponent(typeof(MeshFilter), typeof(MeshRenderer))]
    public class GrassPatch : MonoBehaviour
    {
        public int seed = 731;
        [Range(0, 85)] public int tuftCount = 85;
        public Vector2 minimum, maximum;
        public Vector2 widthRange = new Vector2(.55f, .95f);
        public Vector2 heightRange = new Vector2(.18f, .38f);
        public MeshFilter groundSurface, moundSurface;
        public Bounds[] exclusions;
    }
}
