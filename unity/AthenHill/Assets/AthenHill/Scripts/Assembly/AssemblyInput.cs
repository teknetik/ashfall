using UnityEngine;
using UnityEngine.InputSystem;
namespace AthenHill
{
    /// One frame of bench input, already reduced to what the verbs need. The pointer is a world ray, so the same frame
    /// can be made by the mouse, by the keyboard focus ring, or by a test, and nothing below this needs a camera.
    public struct AssemblyInputFrame
    {
        /// True while the mouse is driving (it moved or clicked last); false while the keyboard focus ring is.
        public bool pointer;
        public Ray ray;
        /// Pointer position and motion in pixels (bottom-left origin), for tap detection and orbiting.
        public Vector2 screen, delta;
        /// Pick up / put down / use / tool action: left button, or Space / Enter.
        public bool primaryDown, primaryHeld, primaryUp;
        /// The primary press came from the keyboard (hold-and-time forms).
        public bool keyboard;
        /// Wheel notches this frame (+ away from the player).
        public float scroll;
        /// Q / E: -1 to 1.
        public float rotate;
        public bool flip, putBack, hint;
        /// WASD / arrows as a held vector, and its edges as one step per press.
        public Vector2 navigate; public Vector2Int navStep;
        public bool next, previous;
        /// Look around: right button held, or Left Shift (then the arrows orbit).
        public bool lookHeld, lookKey, lookClick;
        public float zoom;
        public bool abandonHeld;
    }

    /// Reads the Bench action map (Data/Controls.inputactions, DESIGN.md section 5) into frames.
    public sealed class AssemblyInput
    {
        readonly GameInput input;
        Vector2 lastNav, lookStart; float lookDownTime; bool lookMoved;
        public bool PointerActive { get; private set; } = true;
        public AssemblyInput(GameInput input) { this.input = input; }

        bool Held(string a) => input.BenchAction(a)?.IsPressed() == true;
        bool Down(string a) => input.BenchAction(a)?.WasPressedThisFrame() == true;
        bool Up(string a) => input.BenchAction(a)?.WasReleasedThisFrame() == true;
        float Axis(string a) { var x = input.BenchAction(a); return x != null ? x.ReadValue<float>() : 0; }
        Vector2 Vec(string a) { var x = input.BenchAction(a); return x != null ? x.ReadValue<Vector2>() : Vector2.zero; }

        public AssemblyInputFrame Read(Camera camera, float tapSeconds, float tapPixels)
        {
            var f = new AssemblyInputFrame();
            if (!input || !input.BenchEnabled) return f;
            f.screen = Vec("Pointer"); f.delta = Vec("Delta");
            f.navigate = Vec("Navigate");
            var nav = new Vector2(Mathf.Abs(f.navigate.x) > .5f ? Mathf.Sign(f.navigate.x) : 0, Mathf.Abs(f.navigate.y) > .5f ? Mathf.Sign(f.navigate.y) : 0);
            f.navStep = new Vector2Int(nav.x != 0 && nav.x != lastNav.x ? (int)nav.x : 0, nav.y != 0 && nav.y != lastNav.y ? (int)nav.y : 0);
            lastNav = nav;
            bool mouseDown = Down("Primary"), keyDown = Down("PrimaryKey");
            f.primaryDown = mouseDown || keyDown;
            f.primaryHeld = Held("Primary") || Held("PrimaryKey");
            f.primaryUp = (Up("Primary") || Up("PrimaryKey")) && !f.primaryHeld;
            // one notch reads as 1 on this platform and Input System version; some report 120
            float raw = Axis("Scroll"); f.scroll = Mathf.Abs(raw) >= 20 ? Mathf.Clamp(raw / 120f, -3, 3) : Mathf.Clamp(raw, -3, 3);
            f.rotate = Axis("Rotate");
            f.flip = Down("Flip"); f.putBack = Down("PutBack"); f.hint = Down("Hint");
            f.lookKey = Held("LookKey");
            f.next = Down("Next") && !f.lookKey; f.previous = Down("Next") && f.lookKey;
            // right button: a short still click puts the tool back, a hold looks around
            if (Down("Look")) { lookStart = f.screen; lookDownTime = Time.unscaledTime; lookMoved = false; }
            if (Held("Look") && (f.screen - lookStart).sqrMagnitude > tapPixels * tapPixels) lookMoved = true;
            f.lookHeld = Held("Look") && (lookMoved || Time.unscaledTime - lookDownTime > tapSeconds);
            f.lookClick = Up("Look") && !lookMoved && Time.unscaledTime - lookDownTime <= tapSeconds;
            if (f.lookClick) f.putBack = true;
            f.zoom = Axis("Zoom");
            f.abandonHeld = Held("Abandon");
            // who is driving: the mouse once it moves or clicks, the keyboard once a focus or action key is used
            if (f.delta.sqrMagnitude > 1 || mouseDown || Held("Look") || f.scroll != 0) PointerActive = true;
            else if (f.navStep != Vector2Int.zero || keyDown || f.next || f.previous) PointerActive = false;
            f.pointer = PointerActive;
            f.keyboard = !PointerActive || Held("PrimaryKey") || keyDown || Up("PrimaryKey");
            if (camera) f.ray = camera.ScreenPointToRay(new Vector3(f.screen.x, f.screen.y, 0));
            return f;
        }
    }
}
