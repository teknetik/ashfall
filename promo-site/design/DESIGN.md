# Ashfall — promotional & early-tester website: design specification

Owner: designer (Kanban t_daeaf5d1, 1 Oct 2026). Consumers: coder (t_96803b8f), QA, security.
Inputs read in full: `PROJECT_BRIEF.md`; all six notes under `/home/teknetik/Documents/teknetik/AI/Ashfall/`
(`# Ashfall - Core Narrative and Gameplay Vision.md`, `# Death - Recovery and Robot Companion Systems.md`,
`Concept - Ashfall Protocol.md`, `Core Content.md`, `Improvements.md`, `Phase 3 improvs.md`);
`/home/teknetik/code/ao2/lore.md`; `/home/teknetik/code/ao2/AGENTS.md`.
Art: `../assets/manifest.json` (11 assets, alt text, labels, provenance, web variants) and `../assets/README.md`.

This document specifies look, structure, components and behaviour. It does not contain final public copy;
copy comes from `content/WEBSITE_COPY.md`. Where this file gives example lines, they illustrate tone and length only.

---

## 1. What the site must do

1. Make a visitor *feel* Tir in five seconds: a surviving oasis city, warm stone, salvaged metal, oasis green,
   one restrained thread of cyan technology. Survival and rebuilding, not a robot war.
2. Let a curious reader go deep: world, story premise, the Lattice, modular progression, crafting, robot companions,
   recovery instead of death, the wider atlas. Long-form, readable, illustrated — not a grid of thin cards.
3. Be honest. Three kinds of material are visually distinct everywhere they appear:
   - **Concept** — art and design intent (badge: `CONCEPT`).
   - **Planned** — systems/regions in the design notes that do not exist in the build (badge: `PLANNED`).
   - **In the build today** — things verifiably present in the 1 Oct 2026 development build (badge: `IN BUILD · 1 OCT 2026`).
   No launch dates, testimonials, player counts, multiplayer, downloads, or "coming soon" promises.
4. Invite friends and early testers into **topic discussions** (likes / ideas / feedback, replies) with a lightweight
   username + password account. Reading never requires an account.
5. Keep the mystery intact (see §9 Spoiler policy).

Audience: Carl's friends, early testers and interested sci-fi RPG players (Anarchy Online veterans are a natural
core). They read on phones as much as desktops.

---

## 2. Creative direction

**Mood words:** sun-warmed, lived-in, salvaged, patient, quietly uncanny, hopeful.
**Reference grammar (adopted, not copied):** cinematic game key-art landing pages and long-form editorial features —
full-bleed art with type set over calm sky, generous measure, chapter rhythm, metadata rails, sparing UI chrome.
**Rejected:** neon cyberpunk, gunmetal-and-red "war" palettes, glitch overload, fake terminal noise everywhere,
countdown timers, social-proof strips, Discord-style gamer clutter.

**The diegetic thread.** The Lattice is the game's in-fiction HUD. The site borrows a *small* amount of that
language — mono diagnostic lines (`LATTICE ONLINE`, `MODULE NOT INSTALLED`) — as section kickers, the boot
sequence in the hero, and form/status feedback. Use it as seasoning: never for body text, never more than one
diagnostic block per viewport.

---

## 3. Design tokens

### 3.1 Colour

Dark-first site (art reads best on deep warm shadow), with light "parchment" reading panels for long-form chapters.

| Token | Hex | Role |
| --- | --- | --- |
| `--night-900` | `#14110E` | Page background (warm near-black, never pure #000) |
| `--night-800` | `#1D1915` | Raised surfaces, nav backdrop |
| `--night-700` | `#2A241E` | Cards, inputs on dark |
| `--rule-dark` | `#3B332A` | Hairlines on dark |
| `--stone-100` | `#F3EBDD` | Parchment reading panel background |
| `--stone-200` | `#E6D9C3` | Panel alt / table stripes |
| `--stone-400` | `#C9B08A` | Sandstone accent, decorative rules |
| `--sand-500` | `#B9844B` | Primary accent (sun-baked ochre): links on light, active nav underline |
| `--rust-600` | `#9A4A2B` | Warden banner red; destructive/moderation actions |
| `--brass-400` | `#C8A15A` | Focus ring on dark, badges, numerals |
| `--oasis-500` | `#5E8B5A` | Positive state, "In build" badge, liked state |
| `--oasis-700` | `#3D5E3E` | Hover for oasis |
| `--cyan-400` | `#5FD3D0` | Lattice accent ONLY: diagnostic text, the hero boot line, focus glow in Lattice section |
| `--ink-900` | `#1E1A16` | Body text on parchment |
| `--ink-600` | `#5A5046` | Secondary text on parchment |
| `--fog-100` | `#EDE6DA` | Body text on dark |
| `--fog-400` | `#B3A898` | Secondary text on dark (≥ 4.5:1 on `--night-900`) |

Rules: cyan covers < 2 % of any viewport. Rust is for Wardens and destructive actions only. Verify every text pair
with a contrast checker (WCAG 2.2 AA: 4.5:1 body, 3:1 large text and UI boundaries); `--sand-500` on parchment is for
large text/underlines only — use `#8A5A26` for small link text on parchment.

### 3.2 Typography (all SIL OFL, self-hosted woff2 via the app build; no third-party font CDN)

| Role | Family | Use |
| --- | --- | --- |
| Display | **Fraunces** (variable, opsz 72–144, wght 300–700, slight SOFT) | Hero title, chapter titles, pull quotes |
| Body/UI | **Source Sans 3** (variable) | Body copy, navigation, forms, discussion |
| Diegetic/meta | **JetBrains Mono** (400/500) | Lattice lines, badges, metadata rails, captions' label prefix |

Scale (fluid, `clamp()`), 1.25 ratio on mobile → 1.333 on desktop:
- Hero title `clamp(3rem, 7vw, 6.5rem)`/0.95, Fraunces 600, tracking −0.01em.
- H2 chapter `clamp(2.1rem, 4.2vw, 3.6rem)`/1.05. H3 `clamp(1.4rem, 2.2vw, 1.9rem)`/1.2.
- Body 1.0625rem (17px) → 1.125rem (18px) desktop, line-height 1.65, measure 62–72ch.
- Kicker/meta: JetBrains Mono 0.75–0.8125rem, uppercase, tracking 0.12em.
Never set body in Fraunces or mono. Keep `body` out of any `font: inherit` reset selector (known pitfall).

### 3.3 Space, shape, depth

- 4 px base; section padding `clamp(4rem, 10vw, 9rem)` vertical. Shell max 1280 px; reading column 720 px;
  wide figures break out to 1120 px; full-bleed figures to viewport.
- Radii: 2 px (inputs, badges), 6 px (panels). Architecture-inspired: mostly square, chamfered corner motif
  (`clip-path` 10 px corner cut) for badges, buttons and the lightbox frame — echo of the in-game bronze UI.
- Shadows: soft warm (`0 20px 60px -20px rgb(0 0 0 / .6)`) on dark only. No glassmorphism over art except the nav.
- Texture: optional 3 % noise/grain overlay on dark surfaces (CSS background, < 10 KB). No parallax on text.

### 3.4 Motion

- Easing `cubic-bezier(.2,.7,.2,1)`; durations 180 ms (UI), 600–900 ms (reveal).
- Hero: slow 18 s Ken-Burns drift (scale 1.0 → 1.06) and a one-time Lattice boot line typed in ~1.4 s.
- Section reveal: fade+8 px rise once, on intersection.
- `prefers-reduced-motion: reduce` → no drift, no typing (show final line), no reveal transforms, instant lightbox.

---

## 4. Information architecture

Single long-scroll **home** for the story (chapters with anchor nav) plus a few dedicated routes. Every chapter has a
stable anchor id and its own discussion topic.

| Route | Purpose |
| --- | --- |
| `/` | Home: hero → chapters 1–8 → early testing → discussion teaser → footer |
| `/world` (optional split if home > ~12 screens) | Atlas in depth |
| `/gallery` | All art with filters `Concept` / `Planned regions` / `In build`; lightbox |
| `/discuss` | Topic index (one topic per chapter + General feedback) |
| `/discuss/:topic` | Topic thread: likes, ideas, feedback, replies |
| `/join`, `/login` | Account forms; `/account` (my posts, delete account) |
| `/privacy` | What is stored, why, retention, deletion |
| `/about` | Who's making it, honest project status, contact path |

Primary nav (desktop, left→right): wordmark · The World · Story · The Lattice · Survive & Build · Companions ·
Atlas · Early testing · **Discuss** (button) · Sign in / username menu.
Mobile: wordmark + "Menu" button → full-viewport overlay (see §6.2).

### Home chapter order and content depth

Each chapter = kicker + title + 400–900 words of real copy in the reading column, interleaved with one wide figure,
optional pull quote, a "status rail" (Concept/Planned/In build items) and a "Discuss this" link with live counts.

0. **Hero** — `ashfall-ward-hero`. Title "Ashfall", one-line premise, Lattice boot line, two CTAs:
   "Enter Tir" (scroll to Ch.1) and "Join the early-tester discussion" (→ `/discuss`). Small `CONCEPT ART` badge
   bottom-right of the image.
1. **Tir: a company world, left behind** — planet history, the Fall, the Great Rebuild. Uses accepted history
   framing ("the accepted history says…") without confirming or denying it. Figure: `tir-world-map` teaser crop.
2. **Ward** — the oasis city: aquifers, hydroponics, the last nanofab, adapted droids, Wardens, Karaveen,
   Quantum Tubes. Figure: `ward-vanguard-hall-concept`; secondary inline `build-ward-hill-20261001` in a framed
   "In the build today" aside (this is where the real current city appears, honestly labelled).
3. **Waking on Tir (the opening)** — crash fragments, Karaveen rescue, the nano-infirmary, the implants, the first
   boot. Figure: `ashfall-nano-infirmary-awakening` full-bleed with caption. Diegetic block:
   `OPTICAL INTERFACE DETECTED / NEURAL LINK: DEGRADED / … / LATTICE ONLINE` (mono, cyan, typed once on reveal).
4. **The Lattice** — capacity as a build resource; modules; HUD that grows with you; knowledge as loot;
   the assistant only knows what you have discovered. Component: **Lattice capacity explainer** (§6.6).
5. **Survive & build: progression, implants, crafting, modular weapons** — six attributes with trickle-down,
   implant slots, schematic vs skill, recipe-owned weapon slots. Components: attribute table, weapon-slot
   comparison (§6.7). Inline `build-field-pack-20261001` as "In build today: salvage, the field pack and the
   modular scrap pistol". Status rail must show: modular scrap pistol, salvage/refined components, field orders,
   versioned save = IN BUILD; implants, plasma rifle, 5-tab equipment UI, Lattice Capacity = PLANNED.
6. **Machines that remember** — feral fragments of a shattered network, the first signal moment as a teaser.
   Figure: `ashfall-first-signal-node`. Second figure: `outer-berms-depot-concept`. Copy stops at
   "the machines are detecting the Lattice" level (see §9).
7. **Companions & recovery** — robot companions as build partners (assisted fabrication), no traditional death,
   Anchor emergency, salvage priorities, Karaveen recovery fee, persistent injuries, optional permadeath.
   Figure: `ashfall-companion-recovery` full-bleed; pull quote: the medic's "dragged you nearly four kilometres"
   line (it is from the notes and spoiler-free). Component: **Recovery outcomes ladder** (§6.8). Entire chapter PLANNED.
8. **Atlas of Tir** — interactive region list beside the map (§6.5). Region banners: `ashfall-bleached-flats-caravan`,
   `ashfall-verdant-fold-station`. Every region except Ward and the Outer Berms is `PLANNED`; Outer Berms is
   `IN BUILD (partial)`.
9. **Early testing** — what exists today, honestly: native Linux Unity build of one district + Outer Berms loop;
   what testers can help with; how feedback is used. No download link, no sign-up-for-access promise unless content
   says so. Lists "known rough edges" candidly.
10. **Discussion teaser** — top 3 recent ideas/feedback across topics (escaped text, author, relative date) +
    "Browse all topics".

Footer: wordmark, short honest status line, links (Privacy, About, Discuss, Gallery), "Art on this site is concept
art unless marked In build", © Teknetik. No social icons unless real accounts exist.

---

## 5. Layout & responsive behaviour

Breakpoints: `sm 480`, `md 768`, `lg 1024`, `xl 1280`, `2xl 1600`. Mobile-first.

- **Hero** — `min-height: 100svh` (fallback 100vh), art `object-fit: cover`.
  Desktop `object-position: 68% 50%`; ≤ md `object-position: 72% 50%` (keeps the hill tree and market lane).
  Text block bottom-left on desktop (max 34rem, in the calm sky/dune third), bottom-anchored full-width on mobile.
  Overlays: horizontal gradient `linear-gradient(90deg, rgb(20 17 14 / .78) 0%, rgb(20 17 14 / .35) 38%, transparent 62%)`
  plus vertical `linear-gradient(0deg, rgb(20 17 14 / .85) 0%, transparent 40%)`. Art must stay clearly visible
  on the right; verify rendered crop at 1440×900, 1280×720, 390×844 and 360×740.
  Load the hero with `fetchpriority="high"`, AVIF/WebP/JPEG `<picture>`, `sizes="100vw"`.
- **Chapter** — 12-col grid on ≥ lg: reading column cols 3–9, status rail cols 10–12 (sticky, top 6rem).
  ≤ md: rail collapses into a disclosure below the chapter intro.
- **Full-bleed figure** — edge to edge, max-height 88svh, caption below in a 720 px column, label badge overlaid
  top-left of the image (not hidden in caption only).
- **Parchment panels** — chapters 4, 5 and 7 (mechanics-heavy) render text on `--stone-100` panels for
  readability; story chapters stay on dark. Alternate to create rhythm.
- **Gallery** — CSS grid `repeat(auto-fill, minmax(18rem, 1fr))`, 3:2 thumbnails, map spans 2 cols on ≥ lg.
- Touch targets ≥ 44×44 px. No horizontal scroll at 320 px.

---

## 6. Components

### 6.1 Header / nav
Transparent over hero, becomes `--night-800 / 92 %` with `backdrop-filter: blur(8px)` after 80 px scroll.
Active section underline in `--sand-500` via IntersectionObserver. Skip link "Skip to content" first in DOM.
**Pitfall:** do not nest the mobile overlay inside the blurred header (backdrop-filter creates a containing block
for `position: fixed`); portal it to `body`, then verify `getBoundingClientRect()` equals the viewport.

### 6.2 Mobile menu overlay
Full viewport, `--night-900`, large Fraunces links staggered 40 ms (decorative only). `aria-expanded`,
`aria-controls`, labelled close button, Escape closes, focus trapped, body scroll locked, closed menu removed from
tab order (`inert` or unmounted). Shows auth state and Discuss CTA at the bottom.

### 6.3 Status badges & rail
Mono, uppercase, chamfered 2 px border:
- `CONCEPT` — brass outline on dark.
- `PLANNED` — sand outline, dashed.
- `IN BUILD · 1 OCT 2026` — oasis fill with dark text.
Status rail = titled list ("In the build today" / "Planned") of short items, each with a badge. Data comes from
content; the component never infers status.

### 6.4 Figure + lightbox
`<figure>` with `<picture>` (AVIF → WebP → JPEG from manifest), explicit `width`/`height`, `loading="lazy"`
except hero, `alt` from manifest, `<figcaption>` = manifest `caption` + label. Click/Enter opens lightbox:
`role="dialog" aria-modal="true"`, labelled by the title, focus moves to close button, Escape/close/backdrop
closes and returns focus to the trigger, ←/→ cycle within the current set, swipe on touch, counter "3 / 11",
label badge and caption always visible inside the lightbox, largest variant loaded on open. Reduced motion: no
zoom animation. The map lightbox allows pinch/zoom (native image at 1448 px + CSS `touch-action: pinch-zoom`).

### 6.5 Atlas
Left: map figure. Right (≥ lg) / below (mobile): accordion of regions grouped as in the notes (Central Wastes,
Western Wilds, Northern Territories, Industrial North-East, Corporate East, Eastern & Southern Seas, Southern
Interior, Oceans). Each region: name, 2–4 sentence spoiler-safe summary, badge (Ward = IN BUILD; Outer Berms =
IN BUILD partial; all others PLANNED), banner image where available. Optional: hovering/focusing a region
highlights a hotspot on the map (percent-positioned buttons, keyboard reachable). Accordion uses native
`<details>/<summary>` or proper button + `aria-expanded`.

### 6.6 Lattice capacity explainer
A horizontal capacity bar (e.g. 100 units, illustrative) with toggleable chips — Mapping 10, Crafting assist 15,
Threat analysis 30, Machine link 20, Companion: maintenance drone 15 / recon unit 30 / industrial fabricator 55.
Selecting chips fills the bar; exceeding capacity shows `CAPACITY EXCEEDED` in mono rust. Labelled
"Illustrative — numbers are not final". Pure client-side, no persistence, fully keyboard operable
(`role="switch"`/checkbox chips), with a text summary for screen readers (`aria-live="polite"`).

### 6.7 Mechanics blocks
- Attribute table: Strength, Agility, Endurance, Intellect, Perception, Resolve → what each feeds.
- "Many routes to 15 Rifle" worked example rendered as a diegetic Lattice readout (mono on dark inset).
- Weapon slots comparison: scrap pistol (barrel, grip) vs corporate pistol vs plasma rifle as slot diagrams
  (simple SVG/CSS boxes), with the scrap pistol marked IN BUILD (it has grip/barrel/cell mods in the build) and
  the others PLANNED.

### 6.8 Recovery outcomes ladder
Vertical stepper: Field resuscitation → Stabilise & evacuate → Karaveen recovery → Retreat to outpost →
Protect until help → Partial equipment recovery → Companion failure, with a side panel showing how companion
builds (Medical / Cargo / Combat / Engineering) shift the odds. Diegetic sample: `RECOVERY OBJECTIVE COMPLETED`.
Permadeath shown as a clearly optional mode. Whole block badge PLANNED.

### 6.9 Diegetic block
`<pre>`-like mono block, cyan text on `--night-800`, 1 px `--rule-dark` border, small brass corner ticks.
`aria-label` describing it; typing animation is decorative (full text present in DOM from the start).

### 6.10 Discussion UI (see §7)

### 6.11 Forms
Labels above fields, 1 px `--rule-dark` border, 2 px brass focus ring (`outline`, never removed), inline errors
below fields in rust with icon + text, `aria-describedby`, `autocomplete="username"` / `new-password` /
`current-password`, password show/hide toggle, password guidance text (length-based, no composition rules).
Server status messages appear in a polite live region styled as a Lattice line (`SIGNAL ACKNOWLEDGED` for success
is allowed as a flourish beside plain-English text, never instead of it).

---

## 7. Community: genuine tester discussion

Goal: a calm, readable forum-lite that feels like a field notebook, not a social feed.

**Topics** (one per chapter + general): `world`, `ward`, `opening`, `lattice`, `progression-crafting`,
`machines`, `companions-recovery`, `atlas`, `early-build`, `general`. Topic header shows title, short prompt
question, the chapter image thumbnail and counts (likes, ideas, feedback).

**Post types** — segmented control at the composer top:
- **Like** — one per user per topic, a toggle (heart-free: use a small "sun" / oasis-leaf glyph + "I like this
  direction"), count shown.
- **Idea** — "What would you add or change?" (body 10–2000 chars).
- **Feedback** — "What works or doesn't?" (body 10–2000 chars), optional tag: Story / Mechanics / Art / Build.
Each post card: type badge, author username, relative date with `<time datetime>` absolute tooltip, body
(plain text, escaped, line breaks preserved, URLs not auto-linked or linked with `rel="nofollow ugc noopener"`),
reply button (one nesting level), owner "Delete", moderator "Remove" with reason. Removed posts show
"Removed by moderator" placeholder to keep threads coherent.

Sort: Newest (default) / Most liked ideas. Pagination: "Load more" (20 per page) — no infinite scroll.
Empty state: an inviting prompt + the chapter image, never fake seed posts.

Signed-out readers see everything; composer is replaced by "Sign in or create an account to post" with both buttons.
Signup: username (3–24, `[a-z0-9_-]`), password, confirm, checkbox "I've read the privacy notice". No email.
Account page: my posts, delete my account (with confirmation dialog explaining what is removed).

Moderator affordances (role assigned server-side, never via a default password): queue of reported/recent posts,
remove/restore, lock topic, suspend user. A simple "Report" link on each post for signed-in users.

Privacy notice (layout spec; wording from content): what is stored (username, password hash, posts, likes,
timestamps, session cookie, short-lived rate-limit/security logs), what is not (no email, no tracking/analytics
cookies unless later added and disclosed), retention, how to delete, contact.

Visual: posts on `--night-700` cards with 3 px left border coloured by type (Idea = brass, Feedback = sand,
Reply = rule). Max 72ch. Composer sticky at the bottom on mobile only when focused.

---

## 8. Art system & usage rules

Source of truth: `assets/manifest.json` (filenames, sizes, SHA-256, alt, caption, label, provenance, role).
Web files: `assets/web/<id>-<width>.{avif,webp,jpg}`; originals in `assets/originals/` (never served by default).

| Asset id | Kind | Placement |
| --- | --- | --- |
| `ashfall-ward-hero` | Generated concept (Codex ImageGen, 1 Oct) | Home hero; og:image (crop 1200×630 from it) |
| `ashfall-nano-infirmary-awakening` | Generated concept | Ch.3 Opening |
| `ashfall-first-signal-node` | Generated concept | Ch.6 Machines |
| `ashfall-companion-recovery` | Generated concept | Ch.7 Companions & recovery |
| `ashfall-bleached-flats-caravan` | Generated concept, planned region | Ch.8 Atlas |
| `ashfall-verdant-fold-station` | Generated concept, planned region | Ch.8 Atlas |
| `tir-world-map` | Existing concept map | Ch.1 teaser, Ch.8 Atlas lead, gallery |
| `ward-vanguard-hall-concept` | Existing accepted target image | Ch.2 Ward |
| `outer-berms-depot-concept` | Existing concept | Ch.6 secondary |
| `build-ward-hill-20261001` | Native build capture, 1 Oct | Ch.2 aside + Ch.9 Early testing |
| `build-field-pack-20261001` | Build capture, 1 Oct | Ch.5 aside + Ch.9 Early testing |

Rules:
- Every rendered image shows its manifest `label` as a visible badge; captions add, never replace, the badge.
- Build captures show legacy working names (Free Column, Athen Hill) and a "Development Build" mark; captions
  must say place names are working labels. Never crop out the dev mark to pass them off as final.
- Never place build captures in the hero, og:image or a concept carousel without the IN BUILD badge.
- Do not add text over faces/focal subjects; use captions.
- Image treatment: optional `filter: saturate(.95) contrast(1.03)` site-wide; no colour-grading that changes the art's
  story (e.g. turning dusk to night).

---

## 9. Spoiler & honesty policy (layout-enforced)

Public pages may reveal: crash, Karaveen rescue, nano-infirmary, implants, the Lattice and its assistant, capacity,
knowledge-as-loot, feral machines, "the machines are detecting the Lattice", robot companions, recovery systems,
Lattice Jacks as fast travel the player rebuilds, the accepted history of the Fall.

Public pages must NOT reveal or strongly imply: that Tir was deliberately disconnected/quarantined; that the
assistant is a fragment of the planetary machine intelligence; "authority node"; machines trying to *rejoin*;
the Jacks rebuilding a nervous system; the ending question. Do not quote those lines anywhere, including alt
text, captions, meta descriptions, og tags or HTML comments.

Optional **"Designer's notes (spoilers)"** disclosure is permitted only if content supplies it: collapsed by default,
behind a clear warning and an explicit button, excluded from og/meta and search snippets (`data-nosnippet`), never on
the home page. Default recommendation: omit entirely.

Honesty: currency/nanite economy and Quantum Tube node tiers are tentative — label "Exploring" or omit. Checklist
items in `Improvements.md` are not proof of the current build. Planned regions, multiplayer, accounts in-game,
vehicles and settlement building are not presented as implemented.

---

## 10. Accessibility & performance acceptance

- WCAG 2.2 AA: contrast, visible focus, keyboard path for nav, menu, lightbox, atlas, capacity explainer, forms,
  discussion actions; landmarks (`header`, `nav`, `main`, `footer`), one `h1` per page, logical heading order,
  `lang="en-GB"`, descriptive link text, form errors announced.
- Motion respects `prefers-reduced-motion`; no autoplaying video or sound.
- Performance budget (home, mobile 4G emulation): LCP < 2.5 s, CLS < 0.05, total JS < 150 KB gz on home,
  hero AVIF at 768 w ≈ 50 KB, 1536 w ≈ 160 KB. Lazy-load below-fold images; preload hero + Fraunces display subset.
- Metadata: title, description (spoiler-safe), og:image from hero crop with alt, canonical `https://ashfall.teknetik.co`.
- Verify rendered result: desktop 1440×900 and mobile 390×844 screenshots inspected; hero crop/overlay check via
  `currentSrc`, `naturalWidth`, computed overlay; mobile menu rect = viewport; zero console errors.

---

## 11. Handoff checklist for the coder

1. Read `assets/manifest.json`; build `<picture>` sources from `web_variants`; use `width`/`height` from it.
2. Implement tokens (§3) as CSS custom properties; self-host the three OFL fonts.
3. Build home chapters (§4) with content from `content/WEBSITE_COPY.md`; status rails from content, not inferred.
4. Components §6 with the a11y behaviour listed; lightbox shows label + caption.
5. Discussion per §7; privacy page; no fake seed posts.
6. Enforce §9 in copy review; grep built output for banned spoiler phrases as a test.
7. Run the §10 checks and record screenshots.

Open questions (non-blocking, decide in content/QA): whether to split `/world`; whether a spoiler disclosure exists at
all (recommend no); exact discussion topic list if content renames chapters.
