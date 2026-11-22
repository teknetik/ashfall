using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill
{
    /// What little interface the bench has (DESIGN.md decision 11: no panels for the core work). Built in code with its
    /// own stylesheet (Data/Assembly/AssemblyHud.uss), as the world map is: a key legend on first use, a hold-to-abandon
    /// control, the way out, and a stage line that only shows when the journal cannot carry it (a detached QA job).
    /// Brann's captions use the existing bark strip (BenchVoice). While the bench is open the class `assembly-open` on
    /// the root hides the play HUD's other panels through the stylesheet.
    public sealed class AssemblyHud
    {
        public const string SeenKey = "athen.assembly.legendSeen";
        /// The interface the bench keeps on screen, as rectangles of the 1920 x 1080 reference panel (x, y from the top left):
        /// what the camera must not put the work under. The stylesheet (AssemblyHud.uss) and the play HUD's Field Notes hold
        /// the same places; AssemblySightCheck tests every action against them.
        public static readonly Vector2 Reference = new Vector2(1920, 1080);
        public static readonly (string name, Rect rect)[] Covered =
        {
            ("the stage line", new Rect(28, 24, 470, 40)),
            ("the action line", new Rect(28, 66, 552, 88)),   // left of the caption band (x 580 on); two lines of 21 px at most
            ("Field Notes", new Rect(1448, 16, 456, 132)),
            ("Brann's captions", new Rect(580, 68, 760, 84)),
            ("the way out", new Rect(28, 1010, 760, 44)),
            ("the pack-it-in control", new Rect(1588, 1010, 308, 44)),
        };
        /// The name of the panel a reference-panel point is under, or null.
        public static string CoveredBy(Vector2 panelPoint) { foreach (var c in Covered) if (c.rect.Contains(panelPoint)) return c.name; return null; }
        readonly VisualElement root, panel, legend, abandon, abandonFill, bit, target; readonly Label stage, action, leave, abandonLabel, bitState, bitDo, targetLabel;
        float legendLeft; bool shown;
        /// The pointer is holding the on-screen abandon control.
        public bool AbandonPressed { get; private set; }
        public bool LegendShown => legend.resolvedStyle.display == DisplayStyle.Flex;
        public string StageText => stage.text;
        public string ActionText => action.text;

        public AssemblyHud(VisualElement root, StyleSheet style)
        {
            this.root = root;
            if (style && !root.styleSheets.Contains(style)) root.styleSheets.Add(style);
            panel = new VisualElement { name = "assembly-hud", pickingMode = PickingMode.Ignore }; panel.AddToClassList("assembly-hud");
            panel.style.position = Position.Absolute; panel.style.left = 0; panel.style.top = 0; panel.style.right = 0; panel.style.bottom = 0;
            panel.style.display = DisplayStyle.None;
            stage = new Label { name = "assembly-stage", pickingMode = PickingMode.Ignore }; stage.AddToClassList("assembly-stage"); panel.Add(stage);
            action = new Label { name = "assembly-action", pickingMode = PickingMode.Ignore }; action.AddToClassList("assembly-action"); action.style.display = DisplayStyle.None; panel.Add(action);
            legend = new VisualElement { name = "assembly-legend", pickingMode = PickingMode.Ignore }; legend.AddToClassList("assembly-legend"); panel.Add(legend);
            var title = new Label("AT THE BENCH") { pickingMode = PickingMode.Ignore }; title.AddToClassList("assembly-legend-title"); legend.Add(title);
            foreach (var (keys, what) in new[]
            {
                ("Left button · Space", "pick up, put down, use"), ("Hold, and move", "work a tool"), ("Wheel · Q, Shift+Q", "turn what you hold"),
                ("Middle button · R", "flip it, or change the bit"), ("Right click · X", "put the tool back"), ("Hold right · Shift + arrows", "look round"), ("A · E", "step sideways along the bench"), ("G", "square up the view and the vise"),
                ("Drag it · V + mouse", "turn the vise, any time"),
                ("Wheel · Z C", "move in on the work"), ("Arrows · Tab", "move between things"), ("H", "a hint"), ("Esc", "step back, the job keeps"),
            })
            {
                var row = new VisualElement { pickingMode = PickingMode.Ignore }; row.AddToClassList("assembly-legend-row");
                var k = new Label(keys) { pickingMode = PickingMode.Ignore }; k.AddToClassList("assembly-legend-keys"); row.Add(k);
                var w = new Label(what) { pickingMode = PickingMode.Ignore }; w.AddToClassList("assembly-legend-what"); row.Add(w);
                legend.Add(row);
            }
            leave = new Label("A / E · Side-step  |  V · Turn vise  |  G · Reset view  |  H · Hint  |  Esc · Step back") { name = "assembly-leave", pickingMode = PickingMode.Ignore }; leave.AddToClassList("assembly-leave"); panel.Add(leave);
            abandon = new VisualElement { name = "assembly-abandon" }; abandon.AddToClassList("assembly-abandon"); panel.Add(abandon);
            abandonFill = new VisualElement { name = "assembly-abandon-fill", pickingMode = PickingMode.Ignore }; abandonFill.AddToClassList("assembly-abandon-fill"); abandon.Add(abandonFill);
            abandonLabel = new Label("Hold Backspace · Pack it in") { name = "assembly-abandon-label", pickingMode = PickingMode.Ignore }; abandonLabel.AddToClassList("assembly-abandon-label"); abandon.Add(abandonLabel);
            abandon.RegisterCallback<PointerDownEvent>(e => { AbandonPressed = true; abandon.CapturePointer(e.pointerId); e.StopPropagation(); });
            abandon.RegisterCallback<PointerUpEvent>(e => { AbandonPressed = false; if (abandon.HasPointerCapture(e.pointerId)) abandon.ReleasePointer(e.pointerId); });
            abandon.RegisterCallback<PointerCaptureOutEvent>(_ => AbandonPressed = false);
            bit = new VisualElement { name = "assembly-bit", pickingMode = PickingMode.Ignore }; bit.AddToClassList("assembly-bit"); bit.style.display = DisplayStyle.None; panel.Add(bit);
            bitState = new Label { name = "assembly-bit-state", pickingMode = PickingMode.Ignore }; bitState.AddToClassList("assembly-bit-state"); bit.Add(bitState);
            bitDo = new Label { name = "assembly-bit-do", pickingMode = PickingMode.Ignore }; bitDo.AddToClassList("assembly-bit-do"); bit.Add(bitDo);
            target = new VisualElement { name = "assembly-target", pickingMode = PickingMode.Ignore }; target.AddToClassList("assembly-target"); target.style.display = DisplayStyle.None; panel.Add(target);
            targetLabel = new Label { name = "assembly-target-label", pickingMode = PickingMode.Ignore }; targetLabel.AddToClassList("assembly-target-label"); target.Add(targetLabel);
            root.Add(panel);
        }

        /// The bit button: what is fitted and, when it is the wrong one, how to change it. Null state hides it.
        public void SetBit(string state, string change)
        {
            bit.style.display = state == null ? DisplayStyle.None : DisplayStyle.Flex;
            if (state == null) return;
            bitState.text = state; bitDo.text = change ?? "";
            bitDo.style.display = change == null ? DisplayStyle.None : DisplayStyle.Flex;
            bit.EnableInClassList("assembly-bit--fitted", change == null);
        }
        public bool PointerOnBitButton(Vector2 screen)
        {
            if (!shown || root.panel == null || bit.resolvedStyle.display != DisplayStyle.Flex || bitDo.resolvedStyle.display != DisplayStyle.Flex) return false;
            return bit.worldBound.Contains(RuntimePanelUtils.ScreenToPanel(root.panel, new Vector2(screen.x, Screen.height - screen.y)));
        }
        /// A ring round a target too small to find, at a screen point (bottom-left origin).
        public void SetTarget(Vector2 screen, string text, bool still)
        {
            if (root.panel == null) return;
            var at = panel.WorldToLocal(RuntimePanelUtils.ScreenToPanel(root.panel, new Vector2(screen.x, Screen.height - screen.y)));
            float size = still ? 64 : 64 + 7 * Mathf.Sin(Time.unscaledTime * 5);
            target.style.width = target.style.height = size;
            target.style.left = at.x - size * .5f; target.style.top = at.y - size * .5f;
            targetLabel.text = text;
            target.style.display = DisplayStyle.Flex;
        }
        public void ClearTarget() { target.style.display = DisplayStyle.None; }

        public void Show(bool on, bool firstUse = false)
        {
            shown = on; AbandonPressed = false;
            panel.style.display = on ? DisplayStyle.Flex : DisplayStyle.None;
            root.EnableInClassList("assembly-open", on);
            if (on) { legendLeft = firstUse ? 30 : 0; legend.style.display = legendLeft > 0 ? DisplayStyle.Flex : DisplayStyle.None; SetAbandon(0); }
        }
        public void ShowLegend(float seconds) { legendLeft = Mathf.Max(legendLeft, seconds); if (shown) legend.style.display = DisplayStyle.Flex; }
        /// The first-use legend has done its work once something has been done: it goes at once (H brings it back).
        public void HideLegend() { legendLeft = 0; legend.style.display = DisplayStyle.None; }
        /// The stage line; empty hides it (the journal's Field Notes line carries the stage in a real job).
        public void SetStage(string text) { stage.text = text ?? ""; stage.style.display = string.IsNullOrEmpty(text) ? DisplayStyle.None : DisplayStyle.Flex; }
        /// The action line: what to do now, where the bench cannot show it ("Fire three test pulses at the card · 2 left"); empty hides it.
        public void SetAction(string text) { if (action.text == (text ?? "") && (action.style.display == DisplayStyle.Flex) == !string.IsNullOrEmpty(text)) return; action.text = text ?? ""; action.style.display = string.IsNullOrEmpty(text) ? DisplayStyle.None : DisplayStyle.Flex; }
        public void SetAbandon(float progress01)
        {
            abandonFill.style.width = Length.Percent(Mathf.Clamp01(progress01) * 100);
            abandon.EnableInClassList("assembly-abandon--held", progress01 > 0);
        }
        public void Tick(float dt)
        {
            if (!shown || legendLeft <= 0) return;
            legendLeft -= dt;
            if (legendLeft <= 0) legend.style.display = DisplayStyle.None;
        }
        /// True when the pointer is over the abandon control (the bench must not take that click).
        public bool PointerOnControl(Vector2 screen)
        {
            if (!shown || root.panel == null) return false;
            var p = RuntimePanelUtils.ScreenToPanel(root.panel, new Vector2(screen.x, Screen.height - screen.y));
            return abandon.worldBound.Contains(p);
        }
        public void Dispose() { Show(false); panel.RemoveFromHierarchy(); }
    }
}
