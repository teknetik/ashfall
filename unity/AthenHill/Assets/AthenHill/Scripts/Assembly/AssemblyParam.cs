using UnityEngine;
namespace AthenHill
{
    /// A mechanism posed by one 0-1 value (ANYMACHINE.md section 2): vise jaw, cell latch, tool roll, press lever.
    /// With real art it samples the family's `*_param` clip (a one-second linear action) at the value, never by time.
    /// The greybox form moves and turns one transform between two poses and can switch objects on and off.
    [DisallowMultipleComponent]
    public class AssemblyParam : MonoBehaviour
    {
        public string id = "";
        [Tooltip("The value the mechanism has as found")] [Range(0, 1)] public float asFound;
        [Header("Clip form (real families)")]
        public AnimationClip clip;
        [Tooltip("The object the clip's paths start from (the rig root)")] public GameObject clipRoot;
        [Header("Greybox form")]
        public Transform target;
        public Vector3 basePosition, baseEuler;
        [Tooltip("Added to the base pose at value 1")] public Vector3 move, turn;
        [Tooltip("Shown at or above Switch At / below it")] public GameObject[] shownHigh = new GameObject[0], shownLow = new GameObject[0];
        [Tooltip("Renderers drawn only below / only at or above Switch At (the rolled tool roll gives way to the open one)")] public Renderer[] meshLow = new Renderer[0], meshHigh = new Renderer[0];
        [Range(0, 1)] public float switchAt = .5f;
        [Header("Spin form (continuous params: the drill's crank and spindle)")]
        [Tooltip("The value is in turns, not 0-1, and turns Spin Bone about Spin Axis")] public bool continuous;
        public Transform spinBone; public Vector3 spinAxis = Vector3.forward; public Quaternion spinBase = Quaternion.identity;
        [Tooltip("Turned with this one at Follow Ratio times its turns (negative: the opposite hand)")] public AssemblyParam follower; public float followRatio;
        [Header("Lamp (optional)")]
        public Renderer glow;
        [ColorUsage(false, true)] public Color glowColor = Color.black;

        float value = -1; bool warned;
        MaterialPropertyBlock block;
        static readonly int Emission = Shader.PropertyToID("_EmissionColor");
        public float Value { get => value < 0 ? asFound : value; set => Set(value); }

        /// Turns of a continuous param (0 for the others).
        public float Turns { get; private set; }
        public void Set(float v)
        {
            if (continuous)
            {
                Turns = v; value = Mathf.Repeat(v, 1);
                if (spinBone) spinBone.localRotation = spinBase * Quaternion.AngleAxis(v * 360f, spinAxis);
                if (follower && follower != this) follower.Set(v * followRatio);
                return;
            }
            v = Mathf.Clamp01(v);
            value = v;
            if (clip && clipRoot)
            {
                // a player samples only legacy clips without an Animator (the builder saves them legacy); say so once, not per frame
                if (clip.legacy || Application.isEditor) clip.SampleAnimation(clipRoot, v * clip.length);
                else if (!warned) { warned = true; Debug.LogWarning($"Assembly param {id}: clip {clip.name} is not legacy and cannot be sampled in a player; the mechanism stays still"); }
            }
            if (target) { target.localPosition = basePosition + move * v; target.localRotation = Quaternion.Euler(baseEuler + turn * v); }
            foreach (var g in shownHigh) if (g && g.activeSelf != v >= switchAt) g.SetActive(v >= switchAt);
            foreach (var g in shownLow) if (g && g.activeSelf != v < switchAt) g.SetActive(v < switchAt);
            foreach (var r in meshLow) if (r && r.enabled != v < switchAt) r.enabled = v < switchAt;
            foreach (var r in meshHigh) if (r && r.enabled != v >= switchAt) r.enabled = v >= switchAt;
            if (glow)
            {
                block ??= new MaterialPropertyBlock();
                glow.GetPropertyBlock(block); block.SetColor(Emission, glowColor * v); glow.SetPropertyBlock(block);
            }
        }
    }
}
