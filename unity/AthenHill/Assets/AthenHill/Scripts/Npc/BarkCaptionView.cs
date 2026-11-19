using UnityEngine.UIElements;
namespace AthenHill
{
    /// The bark subtitle: the speaker's name in small bronze capitals over the line, on a dark enamel strip above the
    /// interaction prompt (low centre). Kept apart from the radio panel under the compass and the notice banner, and
    /// never written to the event log (DESIGN.md: the log must not read like a chat channel). Uses the "bark-caption"
    /// element from CityHUD.uxml; builds an identical one under #hud when an older layout lacks it.
    public sealed class BarkCaptionView
    {
        readonly VisualElement box;
        readonly Label speaker, line;
        BarkCaptionView(VisualElement box, Label speaker, Label line) { this.box = box; this.speaker = speaker; this.line = line; }
        public static BarkCaptionView Bind(VisualElement root)
        {
            if (root == null) return null;
            var box = root.Q("bark-caption");
            if (box == null)
            {
                var hud = root.Q("hud"); if (hud == null) return null;
                box = new VisualElement { name = "bark-caption", pickingMode = PickingMode.Ignore };
                box.Add(new Label { name = "bark-speaker", pickingMode = PickingMode.Ignore });
                box.Add(new Label { name = "bark-text", pickingMode = PickingMode.Ignore });
                hud.Add(box);
            }
            var who = box.Q<Label>("bark-speaker"); var what = box.Q<Label>("bark-text");
            if (who == null || what == null) return null;
            box.pickingMode = PickingMode.Ignore; who.AddToClassList("bark-speaker"); what.AddToClassList("bark-text");
            box.style.display = DisplayStyle.None;
            return new BarkCaptionView(box, who, what);
        }
        public bool Visible => box.resolvedStyle.display == DisplayStyle.Flex;
        public string Text => box.style.display == DisplayStyle.Flex ? line.text : null;
        public void Show(string who, string text)
        {
            speaker.text = (who ?? "").ToUpperInvariant(); line.text = text ?? "";
            box.style.display = DisplayStyle.Flex;
        }
        public void Hide() { if (box.style.display != DisplayStyle.None) box.style.display = DisplayStyle.None; }
    }
}
