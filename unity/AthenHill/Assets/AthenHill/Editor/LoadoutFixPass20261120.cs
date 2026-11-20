using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEngine;

namespace AthenHill.Editor
{
    /// <summary>
    /// 20 November 2026, Carl's playtest note "Implants need a eye slot": adds the EYE implant slot
    /// (id implant_eye, label Eye, section IMPLANTS) to Resources/CharacterCatalog.asset, directly after implant_head.
    /// No implant item is moved to it: the catalog has no eye or optic implant (the Neural Targeting Implant is a neural
    /// lattice and stays in HEAD), so the slot starts empty and its inspector says nothing made in Ward fits it yet.
    /// Saves need nothing: equipment is saved per slot id, so a save from before the slot loads with the eye empty.
    ///
    /// The body-map anchors, the hotbar reordering and the drag-label fix are code and USS (AnatomyLayout.cs,
    /// CharacterLoadoutPanel.cs, PackPanel.cs, UI/CityHUD.uss) and need no installer. No scene change.
    ///
    /// Batch: -executeMethod AthenHill.Editor.LoadoutFixPass20261120.RunBatch --steps install,verify[,rollback]
    /// install is idempotent; rollback removes the slot again (refused while any catalog item names it).
    /// Record: art/loadout_fix_20261120/README.md. Evidence: unity/evidence/showcase_phase2/20261120/loadout_fix/.
    /// </summary>
    public static class LoadoutFixPass20261120
    {
        const string CatalogPath = "Assets/AthenHill/Resources/CharacterCatalog.asset";
        const string Evidence = "../evidence/showcase_phase2/20261120/loadout_fix/";
        const string Previous = "../../art/loadout_fix_20261120/previous/character-slots.json";
        public const string EyeSlot = "implant_eye";

        static CharacterCatalog Catalog()
        {
            var c = AssetDatabase.LoadAssetAtPath<CharacterCatalog>(CatalogPath);
            if (!c) throw new Exception("CharacterCatalog missing: " + CatalogPath);
            return c;
        }

        static string Install()
        {
            var c = Catalog();
            if (!File.Exists(Previous))
            {
                Directory.CreateDirectory(Path.GetDirectoryName(Previous));
                File.WriteAllText(Previous, JsonConvert.SerializeObject(c.slots.Select(s => new { s.id, s.label, s.section }), Formatting.Indented));
            }
            if (c.slots.Any(s => s != null && s.id == EyeSlot)) return "already installed";
            var list = c.slots.ToList();
            int head = list.FindIndex(s => s != null && s.id == "implant_head");
            list.Insert(head >= 0 ? head + 1 : list.Count, new CharacterSlot { id = EyeSlot, label = "Eye", section = "IMPLANTS" });
            Undo.RecordObject(c, "Add eye implant slot");
            c.slots = list.ToArray();
            EditorUtility.SetDirty(c);
            AssetDatabase.SaveAssets();
            return "eye slot added after implant_head";
        }

        static string Rollback()
        {
            var c = Catalog();
            if (!c.slots.Any(s => s != null && s.id == EyeSlot)) return "nothing to roll back";
            var users = c.equipment.Where(e => e?.slots != null && e.slots.Contains(EyeSlot)).Select(e => e.itemId)
                .Concat(c.modifications.Where(m => m?.slots != null && m.slots.Contains(EyeSlot)).Select(m => m.itemId)).ToArray();
            if (users.Length > 0) throw new Exception("refused: these items fit the eye slot: " + string.Join(", ", users));
            c.slots = c.slots.Where(s => s == null || s.id != EyeSlot).ToArray();
            EditorUtility.SetDirty(c);
            AssetDatabase.SaveAssets();
            return "eye slot removed";
        }

        static string Verify()
        {
            var c = Catalog();
            var problems = new List<string>();
            var eye = c.slots.Where(s => s != null && s.id == EyeSlot).ToArray();
            if (eye.Length != 1) problems.Add("eye slot count " + eye.Length);
            else if (eye[0].label != "Eye" || eye[0].section != "IMPLANTS") problems.Add("eye slot label/section " + eye[0].label + "/" + eye[0].section);
            int headIndex = Array.FindIndex(c.slots, s => s?.id == "implant_head"), eyeIndex = Array.FindIndex(c.slots, s => s?.id == EyeSlot);
            if (eyeIndex != headIndex + 1) problems.Add("eye slot is not directly after implant_head");
            var duplicates = c.slots.Where(s => s != null).GroupBy(s => s.id).Where(g => g.Count() > 1).Select(g => g.Key).ToArray();
            if (duplicates.Length > 0) problems.Add("duplicate slot ids " + string.Join(",", duplicates));
            // Every slot on the body map has a measured anchor (the fallback spreads unknown slots down the spine).
            var mapped = new List<object>();
            foreach (var s in c.slots.Where(s => s != null && (s.section == "IMPLANTS" || s.section == "ARMOUR" || s.section == "STORAGE")))
            {
                bool implants = s.section == "IMPLANTS";
                bool known = AnatomyLayout.TryAnchor(implants, s.id, out var a);
                if (!known) problems.Add("no anatomy anchor for " + s.id);
                mapped.Add(new { s.id, s.label, s.section, anchor = known ? new[] { a.uv.x, a.uv.y } : null, right = known && a.right });
            }
            var eyeItems = c.equipment.Where(e => e?.slots != null && e.slots.Contains(EyeSlot)).Select(e => e.itemId).ToArray();
            var report = new
            {
                pass = "LoadoutFixPass20261120",
                utc = DateTime.UtcNow.ToString("o"),
                ok = problems.Count == 0,
                problems,
                slots = c.slots.Select(s => s?.id).ToArray(),
                bodyMap = mapped,
                eyeSlotItems = eyeItems,
                headImplants = c.equipment.Where(e => e?.slots != null && e.slots.Contains("implant_head")).Select(e => e.itemId).ToArray(),
                sceneChanged = false,
            };
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "verify.json", JsonConvert.SerializeObject(report, Formatting.Indented));
            if (problems.Count > 0) throw new Exception("verify failed: " + string.Join("; ", problems));
            return "ok (" + mapped.Count + " body-map slots, eye slot items: " + eyeItems.Length + ")";
        }

        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string k, string d) { int i = Array.IndexOf(args, k); return i >= 0 && i + 1 < args.Length ? args[i + 1] : d; }
            try
            {
                foreach (var st in Arg("--steps", "verify").Split(','))
                {
                    string result = st switch
                    {
                        "install" => Install(),
                        "verify" => Verify(),
                        "rollback" => Rollback(),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("LoadoutFixPass20261120 " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
