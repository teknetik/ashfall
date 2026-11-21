using UnityEngine;
namespace AthenHill
{
    /// The one place the bench system touches the crafting system (CONTRACT.md section B: CraftingSession's assembly
    /// surface in Scripts/Crafting/AssemblyHost.cs). Everything else in Scripts/Assembly goes through this class.
    /// It also has a detached form for QA and tests: when the crafting system cannot start the job (no ticket, no
    /// crafting session) and the caller allows it, the job runs with nothing reserved and nothing granted, and its blob
    /// is kept in memory so stepping back and returning still works.
    public sealed class AssemblyCraftLink
    {
        readonly GameSession session; readonly CraftingSession craft;
        AssemblyTicket ticket; static string detachedBlob;
        public bool Detached { get; private set; }
        public AssemblyTicket Ticket => ticket;
        public CraftingSession Craft => craft;

        public AssemblyCraftLink(GameSession session)
        {
            this.session = session;
            craft = session ? session.GetComponent<CraftingSession>() : null;
        }

        /// The open ticket for the recipe, or a new one (inputs reserved, weapon taken to the bench). Null with a reason
        /// when the crafting system refuses and a detached job is not allowed.
        public AssemblyTicket Begin(string recipeId, bool allowDetached, out string reason)
        {
            reason = "no_crafting";
            if (craft && craft.Model != null)
            {
                var open = craft.OpenTicket;
                if (open != null && open.recipeId == recipeId) { reason = "ok"; return ticket = open; }
                if (open == null && craft.CanBeginAssembly(recipeId, out reason))
                {
                    var made = craft.BeginAssembly(recipeId, out reason);
                    if (made != null) return ticket = made;
                }
                else if (open != null) reason = "bench_busy";
            }
            if (!allowDetached) return null;
            Detached = true;
            return ticket = new AssemblyTicket { recipeId = recipeId, stationId = session ? session.ActiveStationId : null, weaponId = "weapon_scrap_pistol", inputs = new ItemStack[0], resumed = !string.IsNullOrEmpty(detachedBlob) };
        }

        /// Words for a refusal, from the crafting system's own text where it has them.
        public string ReasonText(string recipeId, string reason)
        {
            if (craft && craft.Model != null)
            {
                var recipe = craft.Model.Recipe(recipeId);
                if (recipe != null) return CraftingText.Reason(reason, craft.Model, recipe);
            }
            return reason == "bench_busy" ? "Another job is laid out on the bench." : "The bench is not ready for this job.";
        }

        public string Blob
        {
            get => Detached ? detachedBlob : craft ? craft.AssemblyBlob : null;
            set { if (Detached) detachedBlob = value; else if (craft) craft.AssemblyBlob = value; }
        }
        public void ReportStage(string stageId, string label) { if (!Detached && craft) craft.ReportAssemblyStage(stageId, label); }

        public bool Complete(AssemblyResult result, out string reason)
        {
            if (Detached || !craft) { detachedBlob = null; ticket = null; reason = "detached"; return false; }
            bool ok = craft.CompleteAssembly(result, out reason);
            if (ok) ticket = null;
            return ok;
        }
        /// spentItems: item ids or tags used up by the job so far. Every reserved unit of such an item counts as spent (the
        /// crafting system wants one entry per unit). False with a reason when the pack cannot take the rest back.
        public bool Abandon(string[] spentItems, out string reason)
        {
            if (Detached || !craft) { detachedBlob = null; ticket = null; reason = "detached"; return true; }
            var units = new System.Collections.Generic.List<string>();
            // by what the ticket actually reserved: a spent entry is an item id or a tag (component:servo, nanite:tier1), so
            // whichever item filled a tagged input counts
            foreach (var stack in ticket?.inputs ?? new ItemStack[0])
            {
                if (stack == null) continue;
                var spec = craft.Model != null ? craft.Model.Item(stack.itemId) : null; bool spent = false;
                foreach (var s in spentItems ?? new string[0]) if (s == stack.itemId || spec != null && spec.HasTag(s)) { spent = true; break; }
                if (spent) for (int i = 0; i < stack.quantity; i++) units.Add(stack.itemId);
            }
            bool ok = craft.AbandonAssembly(units.ToArray(), out reason);
            if (ok) ticket = null;
            return ok;
        }

        /// Handling numbers for the test cards: the weapon as it came to the bench, or with the mod at a quality.
        public WeaponHandling Handling(string modItemId, CraftQuality quality, bool fitted)
        {
            string weapon = ticket != null && !string.IsNullOrEmpty(ticket.weaponId) ? ticket.weaponId : "weapon_scrap_pistol";
            if (!Detached && craft && craft.Model != null)
            {
                var mod = craft.Model.Loadout != null ? craft.Model.Loadout.Modifier(modItemId) : null;
                var h = fitted ? craft.HandlingFor(weapon, modItemId, quality) : mod != null ? craft.HandlingWithout(weapon, mod.slot) : craft.HandlingFor(weapon);
                if (h.sway > 0 || h.kick > 0 || h.recovery > 0) return h;
            }
            // detached, or a crafting build without handling numbers yet: the design's before and after (DESIGN.md section 10)
            float q = quality == CraftQuality.Fine ? .75f : quality == CraftQuality.Rough ? 1.3f : 1;
            return fitted ? new WeaponHandling { sway = .55f * q, kick = 1.2f * q, sideStep = .12f * q, recovery = .16f * q, scatterGrowth = .1f * q }
                          : new WeaponHandling { sway = 1.5f, kick = 1.9f, sideStep = .8f, recovery = .5f, scatterGrowth = .35f };
        }
        public static void ForgetDetached() { detachedBlob = null; }
    }
}
