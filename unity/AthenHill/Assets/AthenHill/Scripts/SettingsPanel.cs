using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.UIElements;

namespace AthenHill
{
    // THESIS: Tune the city from its existing field-console menu.
    // OWN-WORLD: Worn bronze frame, charcoal controls, ivory labels, cyan focus.
    // STORY: Hear volume changes immediately; try and confirm a display setup.
    // FIRST VIEWPORT: Sound/Video tabs, aligned labeled rows, fixed actions below.
    // FORM: Local extension of the supplied HUD; scroll only the settings rows.
    public sealed class SettingsPanel : IDisposable
    {
        readonly GameSettings settings;
        readonly VisualElement panel, soundPage, videoPage, confirmation, actions;
        readonly Button soundTab, videoTab, apply, discard, resetVideo, keep;
        readonly Label status, countdown, track, resolutionHelp;
        readonly ScrollView scroll;
        readonly Dictionary<string, SliderInt> sliders = new Dictionary<string, SliderInt>();
        readonly Dictionary<string, Label> percentages = new Dictionary<string, Label>();
        readonly Dictionary<string, DropdownField> choices = new Dictionary<string, DropdownField>();
        readonly Toggle mute, vsync, post;
        readonly IVisualElementScheduledItem ticker;
        List<Vector2Int> resolutions;
        bool video, updating, wasPreviewing;
        CityAudio Audio => UnityEngine.Object.FindAnyObjectByType<CityAudio>();

        public SettingsPanel(VisualElement panel, GameSettings settings)
        {
            this.panel = panel; this.settings = settings;
            var tabs = new VisualElement { name = "settings-tabs" }; tabs.AddToClassList("settings-tabs"); panel.Add(tabs);
            soundTab = Button(tabs, "sound-tab", "Sound", () => SelectTab(false));
            videoTab = Button(tabs, "video-tab", "Video", () => SelectTab(true));
            scroll = new ScrollView { name = "settings-scroll", horizontalScrollerVisibility = ScrollerVisibility.Hidden };
            panel.Add(scroll);
            soundPage = new VisualElement { name = "sound-page" }; scroll.Add(soundPage);
            videoPage = new VisualElement { name = "video-page" }; scroll.Add(videoPage);
            Heading(soundPage, "Volume");
            Slider(soundPage, "master-volume", "Master", 0, 100, value => { settings.Sound.master = value / 100f; settings.SaveSound(); });
            mute = Toggle(soundPage, "mute-all", "Mute all audio", value => { settings.Sound.muted = value; settings.SaveSound(); });
            Slider(soundPage, "music-volume", "Music", 0, 100, value => { settings.Sound.music = value / 100f; settings.SaveSound(); });
            Slider(soundPage, "ambience-volume", "Ambience", 0, 100, value => { settings.Sound.ambience = value / 100f; settings.SaveSound(); });
            Slider(soundPage, "effects-volume", "Effects", 0, 100, value => { settings.Sound.effects = value / 100f; settings.SaveSound(); });
            Note(soundPage, "Ambience includes wind, market voices and terminal hums. Effects includes footsteps and interface sounds.");
            Heading(soundPage, "City soundtrack");
            track = Note(soundPage, ""); track.name = "current-track";
            Note(soundPage, "Dust of the Giants  /  Dust of Alshain");
            var audioActions = new VisualElement(); audioActions.AddToClassList("settings-actions"); soundPage.Add(audioActions);
            Button(audioActions, "next-track", "Next track", () => Audio?.NextMusic());
            Button(audioActions, "test-effect", "Test effects", () => Audio?.PreviewEffect());
            Button(audioActions, "reset-sound", "Reset sound", settings.ResetSound);

            Heading(videoPage, "Display");
            Choice(videoPage, "resolution", "Resolution", new List<string>(), index =>
                settings.Edit(v => { v.width = resolutions[index].x; v.height = resolutions[index].y; }));
            Choice(videoPage, "window-mode", "Window mode", new List<string> { "Windowed", "Fullscreen (borderless)" }, index => settings.Edit(v => v.windowMode = index));
            resolutionHelp = Note(videoPage, "");
            Heading(videoPage, "Graphics quality");
            Choice(videoPage, "graphics-preset", "Preset", new List<string> { "Low", "Medium", "High", "Custom" }, index => settings.Edit(v => { if (index < 3) v.UsePreset(index); else v.preset = 3; }));
            Slider(videoPage, "render-scale", "Render scale", 50, 100, value => settings.Edit(v => v.renderPercent = value, true));
            Choice(videoPage, "shadow-quality", "Shadows", new List<string> { "Off", "Low", "Medium", "High" }, index => settings.Edit(v => v.shadows = index, true));
            Choice(videoPage, "anti-aliasing", "Anti-aliasing", new List<string> { "Off", "2× MSAA", "4× MSAA", "8× MSAA" }, index => settings.Edit(v => v.antiAliasing = 1 << index, true));
            Choice(videoPage, "texture-quality", "Textures", new List<string> { "Full resolution", "Half resolution", "Quarter resolution" }, index => settings.Edit(v => v.textureLimit = index, true));
            post = Toggle(videoPage, "post-processing", "Post-processing", value => settings.Edit(v => v.postProcessing = value, true));
            Note(videoPage, "Lower render scale improves performance while keeping the interface sharp. Post-processing controls the city’s bloom and colour grading.");
            Heading(videoPage, "Frame rate");
            vsync = Toggle(videoPage, "v-sync", "VSync", value => settings.Edit(v => v.vSync = value));
            Choice(videoPage, "frame-limit", "Frame limit", GameSettings.FrameLimits.Select(f => f == 0 ? "Unlimited" : f + " fps").ToList(), index => settings.Edit(v => v.frameLimit = GameSettings.FrameLimits[index]));
            Note(videoPage, "VSync follows your monitor’s refresh rate and takes priority over the frame limit.");

            status = Note(panel, ""); status.name = "settings-status";
            actions = new VisualElement { name = "video-actions" }; actions.AddToClassList("settings-actions"); panel.Add(actions);
            resetVideo = Button(actions, "reset-video", "Reset video", settings.ResetVideo);
            discard = Button(actions, "discard-video", "Discard", settings.DiscardVideo);
            apply = Button(actions, "apply-video", "Apply video", settings.ApplyVideo); apply.AddToClassList("primary-setting-action");
            confirmation = new VisualElement { name = "video-confirmation" }; panel.Add(confirmation);
            countdown = Note(confirmation, ""); countdown.name = "video-countdown";
            var confirmActions = new VisualElement(); confirmActions.AddToClassList("settings-actions"); confirmation.Add(confirmActions);
            Button(confirmActions, "revert-video", "Revert · Esc", settings.RevertVideo);
            keep = Button(confirmActions, "keep-video", "Keep changes", settings.KeepVideo); keep.AddToClassList("primary-setting-action");
            settings.Changed += Refresh;
            ticker = panel.schedule.Execute(Tick).Every(100);
            Refresh();
        }
        static Button Button(VisualElement parent, string name, string text, Action action)
        { var button = new Button(action) { name = name, text = text }; parent.Add(button); return button; }
        static void Heading(VisualElement parent, string text)
        { var label = new Label(text); label.AddToClassList("settings-heading"); parent.Add(label); }
        static Label Note(VisualElement parent, string text)
        { var label = new Label(text); label.AddToClassList("settings-note"); parent.Add(label); return label; }
        void Slider(VisualElement parent, string name, string label, int low, int high, Action<int> change)
        {
            var row = new VisualElement(); row.AddToClassList("settings-row"); parent.Add(row);
            var slider = new SliderInt(label, low, high) { name = name }; slider.AddToClassList("settings-field"); row.Add(slider);
            var percent = new Label { name = name + "-value" }; percent.AddToClassList("setting-percent"); row.Add(percent);
            sliders.Add(name, slider); percentages.Add(name, percent);
            slider.RegisterValueChangedCallback(e => { if (!updating) change(e.newValue); });
        }
        Toggle Toggle(VisualElement parent, string name, string label, Action<bool> change)
        {
            var field = new Toggle(label) { name = name }; field.AddToClassList("settings-field"); field.AddToClassList("settings-toggle"); parent.Add(field);
            field.RegisterValueChangedCallback(e => { if (!updating) change(e.newValue); }); return field;
        }
        void Choice(VisualElement parent, string name, string label, List<string> values, Action<int> change)
        {
            var field = new DropdownField(label, values, values.Count == 0 ? -1 : 0) { name = name };
            field.AddToClassList("settings-field"); parent.Add(field); choices.Add(name, field);
            field.RegisterValueChangedCallback(_ => { if (!updating && field.index >= 0) change(field.index); });
        }
        void SelectTab(bool showVideo)
        {
            if (settings.Previewing) return;
            video = showVideo; scroll.scrollOffset = Vector2.zero; Refresh();
        }
        static void Show(VisualElement element, bool value) => element.style.display = value ? DisplayStyle.Flex : DisplayStyle.None;
        void Value(string name, float value) { int n = Mathf.RoundToInt(value); sliders[name].SetValueWithoutNotify(n); percentages[name].text = n + "%"; }
        void ChoiceValue(string name, int index) => choices[name].SetValueWithoutNotify(choices[name].choices[Mathf.Clamp(index, 0, choices[name].choices.Count - 1)]);
        public void Refresh()
        {
            updating = true;
            Show(soundPage, !video); Show(videoPage, video);
            soundTab.EnableInClassList("active-tab", !video); videoTab.EnableInClassList("active-tab", video);
            var s = settings.Sound; var v = settings.Draft;
            Value("master-volume", s.master * 100); Value("music-volume", s.music * 100); Value("ambience-volume", s.ambience * 100); Value("effects-volume", s.effects * 100);
            mute.SetValueWithoutNotify(s.muted);
            resolutions = settings.Resolutions(); choices["resolution"].choices = resolutions.Select(r => r.x + " × " + r.y).ToList();
            ChoiceValue("resolution", resolutions.IndexOf(new Vector2Int(v.width, v.height)));
            ChoiceValue("window-mode", v.windowMode); ChoiceValue("graphics-preset", v.preset);
            Value("render-scale", v.renderPercent); ChoiceValue("shadow-quality", v.shadows);
            ChoiceValue("anti-aliasing", v.antiAliasing == 8 ? 3 : v.antiAliasing == 4 ? 2 : v.antiAliasing == 2 ? 1 : 0);
            ChoiceValue("texture-quality", v.textureLimit); ChoiceValue("frame-limit", Array.IndexOf(GameSettings.FrameLimits, v.frameLimit));
            post.SetValueWithoutNotify(v.postProcessing); vsync.SetValueWithoutNotify(v.vSync);
            choices["frame-limit"].SetEnabled(!v.vSync);
            resolutionHelp.text = Application.isEditor ? "Display changes take effect in the Linux player." : v.windowMode == 1 ? "Fullscreen fills the desktop; the chosen resolution controls the game image." : "Resolution sets the size of the game window.";
            bool preview = settings.Previewing;
            scroll.SetEnabled(!preview); soundTab.SetEnabled(!preview); videoTab.SetEnabled(!preview);
            Show(actions, video && !preview); Show(confirmation, preview); Show(status, !preview);
            apply.SetEnabled(settings.HasChanges); discard.SetEnabled(settings.HasChanges);
            status.text = video ? settings.HasChanges ? "Unapplied changes · Apply to try them for 15 seconds." : settings.VideoMessage == "" ? "Video settings are up to date." : settings.VideoMessage : s.muted ? "All audio is muted. Uncheck Mute all audio to listen." : "Volume changes are heard immediately and saved automatically.";
            if (preview && !wasPreviewing) panel.schedule.Execute(() => keep.Focus());
            if (!preview && wasPreviewing) panel.schedule.Execute(() => videoTab.Focus());
            wasPreviewing = preview; updating = false; Tick();
        }
        void Tick()
        {
            if (panel.resolvedStyle.display == DisplayStyle.None) return;
            if (settings.Previewing) countdown.text = "Keep these video settings? Reverting in " + settings.SecondsRemaining + " seconds.";
            if (!video) track.text = "Now playing · " + (Audio ? Audio.CurrentTrack : "Music unavailable");
        }
        public void Dispose() { ticker.Pause(); settings.Changed -= Refresh; }
    }
}
