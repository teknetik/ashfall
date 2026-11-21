using UnityEngine;
namespace AthenHill
{
    /// Steady Hands, integration Part 2 (21 November 2026): while this object is active its renderers in `hide` are not
    /// drawn. It sits on the real Stabilised grip under the pistol's `Pistol mods/grip_stabilised_pistol`, which
    /// WeaponModVisuals switches on while that grip is fitted: the rebuilt pistol's stock grip (wrap, scales) gives way to it.
    [DisallowMultipleComponent]
    public class HideWhileActive : MonoBehaviour
    {
        public Renderer[] hide = new Renderer[0];
        void OnEnable() { foreach (var r in hide) if (r) r.enabled = false; }
        void OnDisable() { foreach (var r in hide) if (r) r.enabled = true; }
    }
}
