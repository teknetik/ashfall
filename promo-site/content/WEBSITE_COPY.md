# Ashfall — public website copy

Prepared 1 October 2026 (Kanban t_ecf7e316). Spoiler-safe, publishable copy for the Ashfall friends &
early-tester site. Structure follows `design/DESIGN.md` §4 (home chapters 0–10 plus routes). Conflicts,
precedence, the spoiler register and the build-vs-vision ledger are in `SOURCE_INVENTORY.md` (internal).

## Conventions for the implementer

- Lines beginning `> src:` are editorial source references. Do NOT render them, and do not put them in HTML
  comments either. Source keys: **CN** = `# Ashfall - Core Narrative and Gameplay Vision.md`, **DR** =
  `# Death - Recovery and Robot Companion Systems.md`, **CP** = `Concept - Ashfall Protocol.md`, **CC** =
  `Core Content.md`, **P3** = `Phase 3 improvs.md`, **IM** = `Improvements.md`, **LORE** = `ao2/lore.md`,
  **AG** = `ao2/AGENTS.md`. Line numbers refer to the versions hashed in the inventory.
- Status tags map to DESIGN.md §6.3 badges: `[IN BUILD]`, `[IN BUILD — partial]`, `[PLANNED]`,
  `[EXPLORING]`, `[CONCEPT ART]`. Anything not tagged IN BUILD is design intent.
- Diegetic blocks (monospace, cyan) are fenced with ```` ```lattice ````. They are fiction from the design
  notes, not screenshots.
- British spelling throughout. Second person ("you") for the protagonist; no gender.
- Do not add launch dates, platforms, prices, multiplayer, testimonials, download links or "request access"
  promises. Do not add the spoiler items listed in SOURCE_INVENTORY §5 anywhere (copy, alt, meta, OG, comments).

---

## Site meta

- **Title tag:** Ashfall — survive, rebuild and remember on the forgotten world of Tir
- **Meta description:** Ashfall is a first-person sci-fi RPG in development, set on Tir, a corporate
  manufacturing world left behind by the galaxy. Explore the world, the Lattice, robot companions and the
  survival systems — and tell us what you think.
- **OG title:** Ashfall — a world left behind
- **OG description:** A first-person sci-fi RPG in development about survival, repair and machines that
  remember. Read about Tir and join the early-tester discussion.
- **Footer status line:** Ashfall is in early development. Art on this site is concept art unless marked
  as a build capture. Systems marked "Planned" are design goals, not finished features.

---

## 0. Hero

**Kicker:** A first-person science-fiction RPG in development

**Title:** Ashfall

**Premise line:** Your ship came down on Tir, a factory world the galaxy left behind. The people who pulled
you from the wreck saved your life the only way they could — with salvaged machines wired into your mind.

**Boot line (diegetic, types once):**
```lattice
LATTICE INTERFACE DETECTED … LINKING … LATTICE ONLINE
```

**CTA primary:** Enter Tir
**CTA secondary:** Join the early-tester discussion

**Image badge:** Concept art

> src: CN L4–22, L34–76, L128–146; hero art per DESIGN §4.

---

## 1. Tir: a company world, left behind

**Kicker:** The world

**Title:** A company world, left behind

**Standfirst:** Tir was never a jewel of the galaxy. It was a balance sheet with an atmosphere.

Tir was claimed and built by an interstellar conglomerate for two practical reasons. Beneath its deserts lay
rich, shallow mineral deposits ideal for industrial nanotechnology. And its unusually stable, quantum-quiet
geology allowed something rare: a planet-wide Quantum Tube network, moving matter between factories, depots and
orbital loading yards almost instantly.

For generations, Tir did one job. Raw material came out of the ground, was refined and fabricated on-world, and
left for markets the people who made it would never see. Its prosperity was real, but it was the narrow
prosperity of a company world — tightly managed, heavily automated, and dependent on everything that arrived
from somewhere else. Its factories needed interstellar trade. Its settlements needed corporate logistics. Its
machines needed command systems that lived far beyond the planet's control.

Tir was never meant to look after itself.

Then the corporation disappeared.

The accepted history is simple. A wider galactic crisis took the parent conglomerate down with it. The supply
ships stopped coming. Orbital infrastructure was abandoned. The Tube connections failed, the grid browned out,
and Tir was left with fully working factories, a vast industrial machine population — and no customers, no
spare parts and no one in charge.

The machines did what machines do without instructions. Some kept working, carving deserts to schedules no one
would ever read. Some shut down. Others reinterpreted their purpose until it no longer had room for people,
treating settlements, roads and even other machines as obstacles or raw material. Factory complexes failed one
after another. Cities emptied. Survivors who could not hold an oasis scattered into the wastes.

The people of Tir call that era **the Fall**. The long, stubborn work that followed — patching pumps, restarting
furnaces, coaxing dead Tube nodes back to life one by one — is **the Great Rebuild**.

Why the galaxy never came back is a question every survivor has an answer to. The galaxy forgot. The galaxy was
afraid of what Tir's machines had become. The galaxy had bigger fires of its own. Most people have stopped
asking. Tir has enough problems on the ground.

You are about to become one of them.

**Pull quote:** "Tir was never intended to be self-sufficient."

**Status rail:** World history and setting — `[PLANNED]` story content · `[IN BUILD]` the setting of the
current district build.

> src: CN L4–22; CP L6–12; LORE L16–22. Deliberately stops at the accepted history (inventory C1).
> "Why the galaxy never came back" alternatives are taken from CP L12 / LORE L22, which leave it uncertain.

---

## 2. Ward

**Kicker:** The oasis city

**Title:** Ward, the wall that never fell

**Standfirst:** One of the last reliable water sources for hundreds of kilometres — and everyone knows it.

Ward sits in a rare natural depression above deep aquifers. In the corporate era it was a minor cog: a mining and
nanofabrication outpost feeding components into the Tube network. When the surrounding complexes failed, Ward
did not. Its water held. Its people held. A handful of machines that never turned stayed loyal.

What grew there is rough, precarious and alive. A partially intact hydroponics complex keeps the city fed and
stocks the markets and street-food stalls. A single working nanofab still turns out low-to-mid tier nanites,
smart materials and modular weapon parts — the most valuable building on the hill. Old mining droids, rebuilt
by local smiths and scavengers, dig, haul and stand guard. Food stalls trade beside half-collapsed factory
shells. Nanite workshops hum next to scrap forges. Watchtowers scan the dunes for wildlife and for the machines
that never stopped being dangerous.

**The Wardens.** Ward is held by its own militia. What began as volunteers taking turns on the walls hardened,
over generations, into a standing force: the Wardens. Their history is measured in stands at the edge of the
Berms, in night actions against machine swarms, and in the unglamorous, unbroken duty of keeping the aquifers and
markets safe. Most are heavily augmented — implants, reinforced skeletons, synthetic muscle, integrated nanite
systems — and fight with whatever works, from scavenged ballistics to the newest nanotech. They are not a
conquering army. They are the wall that has never been allowed to fall. Families that have given generations to
the Wardens are spoken of with respect, and Warden banners still hang in the old districts beside the faded
sigils of the company that came before.

**The Karaveen.** After the Fall, many survivors took to the road. The Karaveen made that life a culture:
caravans hauling raw materials, then food, then art and luxuries between isolated outposts, kept moving by
salvaged droids, desert beasts and engines held together with patience. They are scavengers, repairers, traders
and, when they must, rescuers. When the Tubes returned, much of their trade was no longer strictly necessary. They
kept travelling anyway. It had become who they were — and they remain the lifeline for every settlement the Tubes
do not reach.

**The Tubes.** Restoring the Quantum Tube network was one of the first great projects of the Great Rebuild. The
Tubes work by controlled molecular disassembly and reassembly, moving goods along quantum-stabilised vacuum
channels between linked nodes. The first successful delivery after the Fall changed everything. As the network's
core came back, many dormant branch nodes woke up on their own, out in the wastes and in the middle of towns.
Nobody fully knows why. Engineers who repaired others often found they had founded a settlement in the process.

Ward is where your story begins. It is also where it keeps coming back to: its nano-infirmary is the most
capable medical facility you will know for a long time, and the only place that really understands what has been
put inside you.

**In the build today (framed aside, beside `build-ward-hill-20261001`):** The current development build is a
single, walkable Ward district in a native Linux Unity build: the West Gate, the market avenue, the hill stairs
and its great oasis tree, Vanguard Hall and a row of working shops. You can talk to four townspeople, take on
their objectives and trade at the general store. Much of the stonework and street dressing you see here was
rebuilt at the end of September and is still being reviewed — this is a work in progress, not final art.

**Status rail:** Ward district, talking NPCs, trading `[IN BUILD]` · 30 Sep art passes `[IN BUILD — under
review]` · Settlement rebuilding and expansion `[PLANNED]` · Wardens and Karaveen as playable factions
`[PLANNED]`.

> src: CP L17–27 (Ward), L34–36 (Tubes), L42–44 (Karaveen), L51–57 (Wardens); LORE L28–66; CN L20, L448
> ("Karaveen settlement known as The Ward" — see inventory C3); DR L359–376 (nano-infirmary); AG §2–§3
> (build contents, "Not yet accepted by Carl").

---

## 3. Waking on Tir

**Kicker:** The opening

**Title:** You don't remember the landing

**Standfirst:** Metal tearing. Alarms. Fire. A glimpse of a planet. Then nothing.

Ashfall begins with a crash. Who you are, why you were travelling to Tir and what happened in the minutes before
your ship came down are all gone. What's left are fragments: the scream of a hull failing, emergency klaxons, heat,
a curve of desert seen through a breaking viewport. Then darkness.

The Karaveen find the wreck. Among the debris they find one survivor.

You are not in good shape. Severe head trauma has damaged parts of your brain and your visual system, and
ordinary medicine on Tir cannot fix that. So they take you to the nano-infirmary at Ward — a place of astonishing
technology that nobody fully understands, much of it salvaged, centuries old and repaired by trial and error.

The doctors make a desperate call. They install a recovered neural implant in your brain. A salvaged ocular
implant replaces what your eyes can no longer do. And to hold the two together they connect them to an old
wrist-mounted computational device, pulled out of Tir's ancient infrastructure.

Your nervous system stabilises. You survive.

When you open your eyes for the first time, you aren't just seeing a ceiling. You're watching something boot.

```lattice
OPTICAL INTERFACE DETECTED
NEURAL LINK: DEGRADED
EXTERNAL PROCESSOR: SEARCHING
LATTICE INTERFACE DETECTED
LINKING...
LATTICE ONLINE
```

That moment is the first time you see the game's interface — because in Ashfall, the interface is you. Your
health, your inventory, your map and your warnings are information drawn by implants onto your damaged sight.
At first, much of it is broken, missing or simply reports:

```lattice
MODULE NOT INSTALLED
```

The doctors saved your life with experimental technology. In return they would like you to keep reporting in:
neural telemetry, biological readings, what your implants are doing. You are, after all, their most interesting
patient. It seems a fair trade. You have nowhere else to go.

**Status rail:** Crash opening, nano-infirmary sequence, diegetic Lattice boot `[PLANNED]` · Ward's
nano-infirmary as a location `[PLANNED]`.

> src: CN L34–76 (opening), L128–164 (boot, MODULE NOT INSTALLED); DR L699–709 (telemetry agreement),
> L359–376. Final line of CN L76 ("Nobody realises what they have just connected") intentionally omitted.

---

## 4. The Lattice

**Kicker:** Your interface, your build

**Title:** The Lattice

**Standfirst:** A wrist device, a neural implant and an artificial eye. Together they keep you alive — and they
are how you see the world.

The Neural Lattice Interface — everyone just calls it **the Lattice** — has three parts. The wrist unit provides
computation, storage, communications and connections to external hardware. The neural implant ties it directly
into your nervous system. The ocular implant draws information over what you see.

Everything a game normally floats in front of you lives inside the fiction: health, stamina, nano reserves,
weapon condition, target data, navigation, objectives, environmental readings, crafting information,
communications and warnings. When the Lattice is damaged, your interface is damaged. When it grows, your
interface grows with it.

**Lattice Capacity.** The Lattice has a finite amount of computation and neural bandwidth — its **Lattice
Capacity**. Every module you run spends some. Early on you might afford simple mapping, basic crafting help and
item information. Later modules could add threat analysis, environmental scanning, advanced fabrication support,
network intrusion, the ability to talk to machines and, eventually, direct access to whatever of Tir's planetary
infrastructure still answers. You raise capacity by finding or building better processors, neural buffers, signal
amplifiers, memory units and interface hardware.

Capacity is a build decision, not a progress bar. A top-end combat analysis suite might use the bandwidth that
could otherwise keep a robot companion linked. The Lattice is part of your character, and you decide what it is
for. Long-time Anarchy Online players will recognise the idea: think of it as Tir's answer to NCU.

**[Component: Lattice capacity explainer — DESIGN §6.6]** Suggested labels (illustrative only, no numbers
implied as final): Mapping · Item analysis · Crafting assistant · Threat analysis · Environmental scanner ·
Machine communication · Companion link. Caption: "Illustrative. Module names, costs and capacity are design
examples, not final values."

**An assistant that only knows what you know.** There's an intelligence running inside the Lattice. At first it
seems like an old embedded helper, and a useful one. Ask it what you can make from what you're carrying and it
checks your inventory, the schematics you know, your skills and the equipment around you. Ask it where to find
something and it answers honestly — from your own experience:

```lattice
> I need copper filament. Where can I find some?

Two previously encountered sources match.
Scrap-processing droids in the eastern Outer Berms have produced
copper filament during previous salvage.
Merchant Kess displayed copper filament during your last visit
to The Ward.
```

It is not an all-seeing quest compass. It knows nothing you haven't found. Scanning machines teaches it. So do
reaching new settlements, reading terminals, talking to people, exploring ruins and pulling old corporate
databases off dead servers. That makes **information a kind of loot**: one recovered manufacturing archive might
suddenly tell it where dozens of components can be found.

It also makes a dense RPG readable. Ask it what you'd need to use a rifle you've just found:

```lattice
> What would let me equip this rifle?

15 Rifle required.
Available options:
  Optical Targeting Implant ........ +8 Rifle
  Wrist Stabiliser upgrade ......... +4 Rifle
  Increase Perception 13 → 14 ...... +3 Rifle
Combined improvement: +15
Requirements satisfied.
```

The complexity stays. The guesswork goes.

**Status rail:** The Lattice as concept and fiction `[PLANNED]` · Lattice Capacity and modules `[PLANNED]` ·
Knowledge-aware assistant `[PLANNED]` · An early Lattice transition and sector overlay exist in the district
build `[IN BUILD — partial]`.

> src: CN L80–190 (Lattice, capacity), L194–250 (assistant, knowledge as loot), L306–328 (rifle example);
> IM L38 ("Implement Ashfall version of NCU" — intent only); AG §2 (Lattice transition/sector overlay).
> "Merchant Kess" is the note's illustrative name (inventory C11).

---

## 5. Survive & build

**Kicker:** Progression, implants, crafting and weapons

**Title:** No classes. Just what you've become.

**Standfirst:** You are not a soldier, an engineer or a medic. You are whatever your body, your gear, your
implants and your machines add up to.

**Attributes that matter everywhere.** Ashfall has no permanent class choice. Your build emerges from six core
attributes, your skills, and everything you wear, carry and install:

| Attribute | Shapes |
|---|---|
| Strength | Carrying capacity, heavy equipment, physical combat |
| Agility | Mobility, weapon handling, stealth |
| Endurance | Health, stamina, resistance |
| Intellect | Engineering, medicine, fabrication, advanced technology |
| Perception | Accuracy, detection, scavenging, tracking |
| Resolve | Mental resilience, neural stability, resistance to hostile effects |

(A seventh, Presence, is being considered if social play needs it.)

Skills run on a larger scale — Rifle, Pistol, Heavy Weapons, Engineering, Electronics, Hacking, Nanotechnology,
Robotics, Medicine, Scavenging, Fabrication and more — and attributes feed **trickle-down bonuses** into the skills
they relate to. The result is the thing many of us loved about Anarchy Online: a requirement is a puzzle, not a
wall. Fifteen points short on a weapon? You might raise an attribute, install an implant, upgrade a stabiliser,
change armour, take a temporary enhancement — or lean on a robot companion. There's usually more than one way up.

**Implants: a body you can rebuild.** You were implanted because you would otherwise have died. Over time,
augmentation becomes a choice. Implant locations are planned for the **head, arms, wrist, hand, chest, waist, legs
and feet**, each directly modifying attributes, skills and derived stats. A neural targeting implant might sharpen
Perception, Rifle skill and critical chance. A reinforced myofibre implant might add Strength, melee power and
carrying capacity. A neural processor might lift Intellect, Engineering and Hacking. Quality ranges from improvised,
to civilian and industrial, up to rare corporate, military and experimental hardware. Some advanced implants can
themselves be upgraded or carry modification sockets.

**Equipment that is the system, not a picture of it.** The planned equipment screen is built around five tabs —
**Primary Weapon, Secondary Weapon, Stats, Implants, Armour** — with armour on the head, arms, hands, chest, legs
and feet. Items drag between inventory and compatible slots, and every change immediately recalculates who you are.

**Modular weapons.** Weapons are platforms. Each design carries its own set of modification slots, defined by the
weapon's recipe rather than by a global rule. A crude scrap pistol might take just a barrel and a grip. A corporate
pistol might add an optic, power cell and internal mod. An advanced plasma rifle might offer emitter, stock, optic,
power cell, cooling unit, core and internal slots. Mods can change damage, recoil, accuracy, rate of fire, heat,
reload speed, power draw, armour penetration or add special effects — so an "older" weapon with an unusual slot
layout can stay worth carrying instead of being made obsolete by the next drop.

**Crafting: knowing versus being able.** To build something you may need a schematic, the materials, enough skill,
the right tools and a suitable workstation. Knowing how and being able to are different things: one player might
have the skill but no schematic, another the schematic but not the skill. Both are progress. Schematics turn up in
laboratories, machines, settlements, abandoned corporate installations, missions, vendor stock and recovered
databases. In time, reverse engineering may let you strip items for materials, learn how their modifications work,
and sometimes recover the schematic itself.

The intended first steps are deliberately small: find a weapon, find supplies, learn to repair, and walk into a
workshop to build your first gun.

**In build today (framed aside, beside `build-field-pack-20261001`):** The current development build already has an
early version of this loop out in the Outer Berms: a scrap pistol with swappable grip, barrel and power-cell mods;
salvage that refines into components; seeded loot with protection against long bad-luck streaks; salvage caches and
scrap heaps; a tough depot elite; a short set of field orders; buying parts and selling salvage at the general
store; and a versioned save you can Continue from. It is a first slice, not the full system described above.

**Status rail:** Modular scrap pistol, salvage and refined components, field orders, versioned save `[IN BUILD]` ·
Early character sheet: six attributes, skills, implant and armour slots, five-tab equipment screen, carry weight
`[IN BUILD]` · The full trickle-down progression and implant effects described here `[PLANNED]` · Plasma and
corporate weapon recipes `[PLANNED]` · Schematics and reverse engineering `[PLANNED]` · Walk-in crafting tutorial
`[EXPLORING]`.

> src: CN L254–328 (attributes/skills/trickle-down), L332–366 (implants), L370–396 (equipment UI), L400–420
> (modular weapons), L424–442 (crafting), L904–916 (early questions); P3 (walk-in crafting building); IM L37–40
> (drag/drop, secondary slot — intent only); AG §3 "Outer Berms loop" (build facts; cell mod per inventory C10).

---

## 6. Machines that remember

**Kicker:** The machines of Tir

**Title:** Machines that remember

**Standfirst:** They were built to work. Nobody ever told them to stop.

Beyond Ward's walls, Tir's machine population lives on in pieces. Old industrial robots gather in small,
disconnected groups around ruined plants, power sources and maintenance yards. They look feral. Some guard work
sites that closed generations ago. Some defend territories that mean nothing to anyone else. Many are still
performing jobs whose purpose disappeared long before anyone now alive was born. They repair one another where they
can, strip the broken for parts, and attack whatever they read as a threat.

Different populations kept different habits. Mining machines still defend mineral seams. Transport systems guard
roads that go nowhere. Security units enforce the rules of governments and companies that no longer exist.
Factories keep filling orders for customers who died centuries ago. Maintenance crews endlessly repair
infrastructure nobody uses. They are not one robot army with one plan. They are what's left — and every population
carries a little of the history of what happened to Tir.

Wardens call them feral machines. Whether that's genuine adaptation or centuries of corrupted code is an old
argument in Ward's bars.

Then, one day, out in the Berms, one of them stops.

```lattice
REMOTE NODE DETECTED
LEGACY NETWORK RESPONSE
AUTHENTICATION ATTEMPT...
```

The machine turns and looks straight at you. Your vision tears with static.

```lattice
IDENTITY CONFLICT
```

And then it attacks again, as if nothing happened.

Your Lattice isn't only detecting Tir's machines. **Tir's machines are detecting your Lattice.** As you travel
further, it keeps happening. Some machines attack on sight. Some hesitate. Some just watch. A few follow you at a
distance and never explain why.

What they want, and what they see when they look at you, is the question Ashfall is built around. We're not going to
answer it here.

**Pull quote:** "The Lattice isn't merely detecting Tir's machines. The machines are detecting the Lattice."

**Status rail:** Feral machine enemies, depot elite `[IN BUILD — partial]` (Outer Berms loop) · Machine
signal encounters and the wider machine story `[PLANNED]`.

> src: CN L456–464, L486–516 (first signal), L522–532 (hesitate/watch/follow), L546–562 (fragment behaviours —
> used as flavour only, without stating the network survives); CP L65–67 (feral clusters, "debated"); AG §3
> (depot elite). Spoiler cut-off per DESIGN §9 / inventory §5.

---

## 7. Companions & recovery

**Kicker:** Robot companions, the Anchor and why death isn't the end

**Title:** You won't survive Tir alone

**Standfirst:** A machine saved your life. Sooner or later, another one will have to do it again.

### Companions you earn, not command

As your Lattice grows more capable, you'll be able to form stable links with certain machines — Tir's version of
taming a creature or recruiting a follower. But you don't hack a robot into obedience. You make contact. A damaged
maintenance unit might be frightened, hostile or simply confused. You may need to repair it, replace corrupted
hardware, or complete a successful neural handshake before it accepts you as a trusted node. Then it comes with you.

Normally you'll run one major companion at a time, and each costs Lattice Capacity: a small maintenance drone
very little, a reconnaissance unit more, an industrial fabrication robot a lot, a heavy military platform an
enormous amount. Every companion is a trade against the modules you could have run instead.

### Robots are builds too

Companions are full RPG characters with their own chassis, processors, power, armour, sensors, tools, weapons,
software and skills — and you can repair and upgrade all of it. A construction robot might start as a superb
engineer with no fight in it. One player turns it into a master fabricator. Another bolts on armour, hydraulics and
industrial weapons and turns the same chassis into a brute. What a robot is comes from what's installed, not from a
class. Medical, salvage, reconnaissance, combat, fabrication and exploration roles emerge naturally.

That means you don't have to master everything yourself. A combat-heavy character with poor Engineering can still
build top-tier gear if their companion has the skill:

```lattice
PLASMA RECEIVER MK III
Engineering required: 380
Player Engineering: 124
IND-44 Engineering: 412
ASSISTED FABRICATION AVAILABLE
```

You're not levelling a hero. You're building a small team.

### Incapacitated, not dead

Ashfall avoids traditional video game death wherever it can. At zero health you are **critically
incapacitated**, and what happens next depends on your injuries, where you are, what you're carrying, how
recently your Lattice synchronised, what medical help is nearby, whether the Karaveen can reach you — and above
all, on your companion.

Watching over your body is **the Anchor**, an emergency system that tracks your heart rate, oxygen, blood loss,
neural stability, implant condition, exposure, location and equipment. When catastrophic trauma hits, it goes into
emergency mode:

```lattice
CRITICAL TRAUMA DETECTED
CARDIAC FUNCTION UNSTABLE
NEURAL LINK DEGRADING
EMERGENCY BEACON ACTIVATED
```

If you can't recover on your own, it calls for help. You might catch a scrap of distorted radio — RECOVERY
CONTRACT BROADCASTING … SIGNAL ACKNOWLEDGED — before everything goes dark.

**[Component: Recovery outcomes ladder — DESIGN §6.8]** Your companion assesses the situation and does what its
hardware, software and condition allow. Possible outcomes, from best to worst:

1. **Field resuscitation** — you wake where you fell, badly hurt.
2. **Stabilise and evacuate** — patched up enough to be moved.
3. **Karaveen recovery** — a recovery team brings you in.
4. **Emergency retreat** — your companion gets you to the nearest outpost.
5. **Protection until help arrives** — it stands over you and fights.
6. **Partial equipment recovery** — it saves what it can carry.
7. **Companion failure** — sometimes your machine can't save you.

Being revived is not the same as being well:

```lattice
FIELD RESUSCITATION SUCCESSFUL
Health: 14%
Blood volume: LOW
Internal bleeding: CONTROLLED
Left arm function: IMPAIRED
Neural stability: 42%
SEEK MEDICAL FACILITY
```

A lost fight can turn into a new one: reach the settlement five kilometres away before your condition gets worse.

### Injuries that follow you home

Serious injuries stick until they're properly treated — fractures, concussion, blood loss, internal bleeding,
burns, neural shock, implant damage, infection, nanite contamination, toxins — but they're meant to be readable,
not a medical simulator. An injured arm means more weapon sway, slower reloads and weaker melee. A bad leg means
slower movement, shorter sprints and more stamina drain. Neural shock makes your interface unstable, weakens the
Lattice and can cut your control over linked machines. A damaged ocular implant brings interference, thinner
targeting data and unreliable scans. A medically capable companion can blunt the worst of it in the field:

```lattice
LEFT LEG MOTOR RESPONSE: 61%
EMERGENCY SPLINT APPLIED
MOVEMENT PENALTY REDUCED
```

Where you get treated matters. **Field treatment** (medkits, your own skills, your companion) stops bleeding and
buys time but can't fix severe trauma. A **remote outpost clinic** handles moderate wounds, minor fractures,
infection, dehydration and simple poisoning, and may only stabilise worse. A **town or city hospital** handles
major trauma, organ damage, implant servicing and serious toxins — for a price, or the right standing. And the
**Ward nano-infirmary** can do what nowhere else nearby can: major reconstruction, Lattice calibration, implant
repair, neurological treatment and experimental procedures. Ward never stops being home base.

### What happens to your gear

Your companion can only carry what its cargo space allows, and it decides what to save using priorities you set
through the Anchor:

```lattice
EMERGENCY SALVAGE PRIORITY
1. Equipped weapons
2. Unique items
3. Mission items
4. Armour
5. Rare resources
6. Consumables
7. Common materials
```

Whatever it can't carry, Karaveen recovery teams may collect later. Your own rescue is covered — the doctors'
research arrangement sees to that. Your equipment is not, and recovery teams charge a salvage fee to bring it back
(illustrative example: recovered gear worth 12,840 credits, fee 642). It's a cost, not a deletion.

Which makes companion design a kind of insurance. With no companion, the Karaveen find you, and your gear is
expensive to reclaim. A **basic** companion transmits your exact location, guards you and saves a little. A
**cargo** build hauls much more and slashes salvage costs. A **medical** build stabilises severe injuries and can
prevent some trauma altogether. An **advanced trauma** companion may revive you without anyone else's help. You
can't max everything: a heavily armed bodyguard may have almost no medical skill, a dedicated medic little combat
value, and a hauler might save you thousands of credits but not your life.

At the top end, a companion might even be able to share its own processing to keep your failing nervous system
running — at a cost to its battery, its combat ability and how far it can move from you — while the two of you race
for a hospital before either of you gives out:

```lattice
NEURAL SHUTDOWN IMMINENT
COMPANION REQUESTING EMERGENCY LATTICE ACCESS
AUTHORISE?
```

**Pull quote:** "Outside. That thing dragged you nearly four kilometres. Burned out half its servos doing it."
Beside the clinic, your robot sits scorched and limping, and reports only:

```lattice
RECOVERY OBJECTIVE COMPLETED
```

It doesn't understand why that matters to you. You do.

### Saving, the Tir way

The Anchor records your condition constantly, but large uploads of medical and neural data need surviving network
infrastructure. Those **Lattice sync points** are where your recovery state is updated — Ashfall's in-world
explanation of saving (quiet autosaves still exist, because usability matters).

```lattice
LATTICE SYNC POINT DETECTED
PATIENT DATA UPLOAD
Neural telemetry ......... COMPLETE
Biological telemetry ..... COMPLETE
Equipment manifest ....... COMPLETE
Research package ......... TRANSMITTED
RECOVERY STATE UPDATED
```

### Recovery Mode or Permadeath

At your first sync, the game will step outside the fiction — once — to ask how much risk you want.

**Recovery Mode** is the default and the intended experience. When something should have killed you, the Anchor,
your companion, the Karaveen and Tir's medical network give the story a believable way to continue: revived in the
field, carried to an outpost, brought back to Ward, with medical bills, lost equipment or lasting injuries as the
price. Not every situation is survivable in story terms; Recovery Mode assumes your disasters happened where rescue
was still possible.

**Permadeath** keeps all of those systems — they'll still save you often — but some situations are simply beyond
them: trauma no one could survive, places no one can reach, a beacon that fails, help that arrives too late. Then
it's over: that character's story ends with them.

On normal settings, a dangerous ruin asks, "What will this cost me if it goes wrong?" On Permadeath it asks, "Can I
afford to go in at all?" Fifty hours in, wounded and kilometres from help, your robot dragging you home is no longer
saving you a recovery fee. It's trying to keep your whole story alive.

**Status rail:** Entire chapter `[PLANNED]` — companions, the Anchor, incapacitation outcomes, injuries, medical
hierarchy, salvage priorities and fees, sync points and the Recovery/Permadeath choice are design goals. The current
build has a versioned save with Continue `[IN BUILD]`.

> src: CN L566–642 (companions, robot progression, assisted fabrication); DR L1–129 (core concept, Anchor,
> companion role), L133–202 (emergency outcomes, resuscitation), L206–285 (injuries), L289–376 (facility
> hierarchy), L380–466 (equipment recovery, priorities, fee), L470–625 (insurance tiers, specialisations, mixed
> builds), L629–655 (four kilometres), L659–689 (neural support), L695–727 (sync points), L894–1051 (Recovery vs
> Permadeath). Pronoun normalised (inventory C7). Credits example labelled illustrative (inventory C13).

---

## 7b. Lattice Jacks (sub-section of Chapter 7 or its own short block)

**Title:** Fast travel you rebuild yourself

Tir once had a vast Quantum Tube transport system. Most of its old terminals have been dormant for decades —
ruins, monuments, industrial curiosities children dare each other to climb. Your implants can wake some of them.

```lattice
LEGACY TRANSPORT NODE DETECTED
NODE STATUS: DORMANT
NETWORK AUTHENTICATION: FAILED
ATTEMPT LATTICE INTERFACE?
```

Bring a node back and it joins your personal network: a **Lattice Jack**. Fast travel in Ashfall isn't a menu you
unlock — it's infrastructure you physically restore, node by node, across the planet. Deeper upgrades open deeper
layers of the old network, roughly in this order: local routes around Ward and the Outer Berms; regional routes;
industrial freight lines; restricted corporate routes; military transit; and, eventually, destinations the old
network doesn't seem to want to name.

**Status rail:** Lattice Jack network `[PLANNED]` · A ring gate stands in the current district build but is
offline `[IN BUILD — inactive]`.

> src: DR L731–801 (Jacks, six stages; Route 00-Ω block omitted as spoiler-adjacent), L805–836 omitted (hidden
> function); AG §2 (Ring Gate offline). Passenger-vs-goods tension: inventory C4.

---

## 8. Atlas of Tir

**Kicker:** The wider world

**Title:** Atlas of Tir

**Intro:** Ward is one small oasis on a big, strange planet. Beyond the Outer Berms lie salt seas without water,
cities that never went dark, factories that ate each other, and oceans that keep their secrets. Everything below
the Outer Berms is world design for the future — **planned regions, not places you can visit in the current
build.**

**Map caption:** Map of Tir — concept art. Region placement is indicative.

Per-region fields for the atlas component (DESIGN §6.5): name · area group · status · one-line hook · body.

### Home ground

**Ward** — `[IN BUILD — one district]`
*Hook:* The last reliable water for hundreds of kilometres.
An oasis city in a natural basin over deep aquifers, kept alive by hydroponics, one working nanofab, rebuilt mining
droids and the Wardens on its walls. Street food beside collapsed factories; nanite workshops beside scrap forges.
> src: CP L17–27; AG §3.

**The Outer Berms** — `[IN BUILD — partial]`
*Hook:* Ward claims it on old maps. Nobody claims it in practice.
A broad ring of broken wasteland between the oasis and the deep desert, and the game's early survival and combat
region. Half-buried processing plants, collapsed storage yards, rusted conveyor lines, shattered service roads and
abandoned machine depots break through the sand — some picked clean for generations, some still too dangerous to
explore. Feral machines hold small territories around old power and maintenance sites. Native wildlife looks
almost familiar — lean pack hunters like dogs, long-eared burrowers like rabbits, venomous sand-serpents under warm
scrap — but evolved entirely apart from Earth life, with toxins and habits to match. Raiders hide beyond the Warden
patrol routes and ambush scavengers and Karaveen caravans on the old industrial roads; experienced Karaveen rarely
cross alone. It is where scavengers find scrap, hunters track game and young Wardens walk their first patrols.
Beyond it, Tir becomes far less forgiving.
> src: CP L59–77; CN L446–472; LORE L72–74; AG §3 (Outer Berms loop; wildlife and raiders are not listed there —
> keep them as setting, not build claims).

### The Central Wastes `[PLANNED]`

**The Salt Expanse**
*Hook:* An inland sea that was drunk dry.
West and north of Ward lies one of the largest unbroken deserts on Tir, the floor of a vanished inland sea — salt
flats, desert and vast dunes, emptied by geology and centuries of industrial water extraction. Corporate surveys
found huge mineral deposits under the old seabed, and generations of mining complexes now lie buried there. Storms
sometimes uncover buildings that haven't seen daylight since the Fall. Karaveen stories speak of whole pre-Fall
towns preserved under the dunes, and of enormous creatures moving beneath the sand. Most people dismiss them. Most
people have never crossed the Salt Expanse.
> src: CP L83–101.

**The Dune Wastes**
*Hook:* Control one working well and you have a town. Lose it, and you don't.
The southern central desert: ever-shifting dunes broken by rock, ruined roads and isolated settlements. Nomadic
communities live here, some descended from early Karaveen families who never settled during the Great Rebuild. Old
atmospheric collectors, underground cisterns and forgotten industrial wells can be worth more than whole towns.
> src: CP L105–119.

**The Ariden Plateau**
*Hook:* Here, data is worth more than metal.
A vast canyon-cut plateau to the west, where pre-Fall administrators built towns into the canyon walls to escape the
lowland heat. Some are ruins; others are living vertical settlements in the rock. The plateau is threaded with old
communications infrastructure and buried corporate data centres, drawing archaeologists, data scavengers,
mercenaries and corporate recovery teams — who do not always arrive peacefully.
> src: CP L123–141.

**The Bleached Flats**
*Hook:* A graveyard for falling stars.
South-west of Ward, blinding white mineral plains and shallow salt lakes became a dumping ground for damaged orbital
hardware in the last decades before the Fall. Satellites, cargo platforms and pieces of stations lie scattered for
hundreds of kilometres. Its landmark is the **Fallen Spire**, thought to be part of an unfinished orbital elevator:
it rises kilometres into the sky and simply stops. No one knows how much of it lies underground.
*Banner art:* `ashfall-bleached-flats-caravan` (concept art).
> src: CP L145–157.

### The Western Wilds `[PLANNED]`

**The Verdant Fold**
*Hook:* Tir as it was before anyone arrived.
Beyond the western plateaus lies one of the planet's great surprises: subtropical jungle, river systems and huge
wetlands, largely spared industry because the corporation set it aside for biological research. Tir's native life
thrives here, including several animals that use tools, hunt together and communicate in complex ways — whether any
are truly sapient is one of Tir's oldest scientific arguments. Deep in the jungle, research stations hold centuries
of data. Some are sealed. Some appear to still be running.
*Banner art:* `ashfall-verdant-fold-station` (concept art).
> src: CP L163–185.

**The Blooming Keys**
*Hook:* Paradise, until you leave the beach.
A chain of tropical islands off the Fold's southern coast, famous for forests of enormous flowering plants whose
seasonal blooms colour whole islands. Rebuild-era communities fish, farm and research here. The islands are calm.
The water isn't: large marine predators migrate through, and several Karaveen crews have vanished on the sea routes.
> src: CP L189–203.

**The Glass Coast**
*Hook:* Cliffs that glitter, storms that pay the bills.
North of the Fold, immense cliffs studded with dark crystal meet the Stormreach Sea and glitter in direct sun.
Pre-Fall energy stations harvest its constant storms, and some still work. Its people live in sheltered valleys and
old maintenance ports and keep a maritime culture rare on Tir: fishing boats, storm craft and salvage ships.
> src: CP L207–221.

### The Northern Territories `[PLANNED]`

**The Shattered Spine**
*Hook:* The drills never got the order to stop.
A colossal mountain range dividing the north from the central continent, with some of Tir's highest peaks — hollowed
by mining tunnels, abandoned railways and automated extraction plants. Deep inside, mining drones still cut rock to
schedules set centuries ago. Sometimes they break into something unexpected: ruins beneath several mines hint that
an advanced civilisation may have lived on Tir long before humans arrived. The corporate records on those finds are
oddly incomplete.
> src: CP L227–245.

**Frostbite Reach**
*Hook:* Some guards never heard the company was gone.
Tir's frozen north: glaciers, with permanent settlements clustered around geothermal zones and surviving research
sites. In the corporate era it hosted laboratories, weapons ranges and observatories, and its isolation let several
survive the Fall almost untouched — valuable, and dangerous. Automated security still defends some installations
as if the corporation were in charge; others have invented new interpretations of their mission. Some northern
communities have learned to live alongside these systems rather than destroy them.
> src: CP L249–267.

### The Industrial North-East `[PLANNED]`

**The Iron Grave**
*Hook:* The factories kept going — and started eating each other.
Thousands of factories once formed a continuous manufacturing belt here. When logistics collapsed they did not stop.
Warehouses overflowed, transport failed, and machines began dismantling neighbouring plants for raw material. Over
centuries the region became an ecosystem of machinery: some factories locked in meaningless production loops, others
merged into semi-autonomous machine communities. Scavengers can find technology here that exists nowhere else. Few
go far inside.
> src: CP L273–297.

**Ashfall Basin**
*Hook:* The mountain is waking up. Officially, it isn't.
East of the Iron Grave, volcanoes, lava fields and geothermal vents dominate one of Tir's most active regions.
Enormous automated mines built for extreme conditions survived the Fall, and modern settlements cluster around
geothermal power stations, making the basin one of the most energy-rich places outside corporate territory. Its
largest volcano, **Ember Crown**, is still active and reshapes the land when it erupts. Locals believe it is slowly
waking after centuries of calm. Corporate geologists call that superstition. Their evacuation plans suggest
otherwise.
> src: CP L301–321. Title/region link not asserted (inventory C15).

### The Corporate East `[PLANNED]`

**The Neon Dominion**
*Hook:* The lights never went out. Neither did the company.
Along the eastern coast runs a continuous band of arcologies, industrial ports, artificial islands and corporate
cities where the collapse was far milder. Corporate government survived; factories were repaired; security stayed
on. Automated transit crosses spotless streets; medical nanotech is routine; synthetic food, climate-controlled
districts and virtual entertainment are ordinary life — standards almost unimaginable from Ward. And almost
everything is still run by corporate authority: citizens carry employment classifications, productivity ratings and
contractual social status inherited from before the Fall. To outsiders the Dominion looks like civilisation
restored. To many who live there, the Fall never ended. It just got organised.
> src: CP L327–357.

**Nexus Prime**
*Hook:* It remembers the rest of Tir. That's the problem.
The heart of the Dominion and the largest functioning city on Tir, once the corporation's planetary headquarters.
Its arcologies house millions, and orbital communications, advanced nanofabrication and high-capacity Tubes run here
at levels seen nowhere else. Its rulers claim legal ownership of much of Tir under pre-Fall colonial charters. Most
independent settlements ignore that claim. Nexus Prime does not. As the Great Rebuild reconnects the planet, its
survey teams, diplomats and security forces are turning up further and further from home.
> src: CP L361–381.

**The Shimmer Isles**
*Hook:* Officially, just resorts.
Warm islands south of the Dominion, once retreats for senior corporate staff. Many resorts survived; several islands
became private research centres, exclusive settlements and estates. Access is tightly controlled, and rumours persist
of laboratories beneath the islands doing research banned elsewhere. Officially there's nothing there but resorts and
marine science. Very few outsiders are invited to check.
> src: CP L385–401.

### The Eastern and Southern Seas `[PLANNED]`

**The Fractured Isles**
*Hook:* Where the strangest tech on the black market comes from.
A violent archipelago north-east of the Dominion: jagged islands, deep channels, frequent storms. During the Fall,
ships and orbital cargo craft crashed here trying to reach the eastern cities, and their wreckage covers land and
seabed. Salvagers, smugglers and treasure hunters come for it, alongside communities that want nothing to do with any
government, corporate or otherwise.
> src: CP L407–421.

**The Broken Teeth**
*Hook:* Lawless on paper. Open for business.
A chain of narrow rocky islands along the south-east coast, ringed by shallow reefs and thousands of wrecks.
Smugglers, pirates and independent trading clans hold it through shifting alliances of trade, family and mutual
defence. The Dominion officially calls it lawless. Unofficially, corporate goods move through its markets every day.
> src: CP L425–441.

**The Sundered Delta**
*Hook:* Something built here before anyone we know.
Where several great rivers meet the southern ocean they form a maze of wetlands, mangroves and flooded plains. Its
agricultural and environmental projects were abandoned when flood control failed, and nature took them back. The
result is extraordinarily rich and extremely dangerous: predators big enough to attack vehicles in the deep channels,
amphibious species with signs of social organisation and territory. Explorers report structures beneath the swamps
that look neither human nor corporate.
> src: CP L445–465.

### The Southern Interior `[PLANNED]`

**Sunscar Reach**
*Hook:* Fortified against an enemy no record names.
Dry, wind-scoured highlands between the central deserts and the southern wetlands, once one of Tir's great
renewable-energy zones. Thousands of turbines still line the ridges and many still turn, powering some of the most
prosperous independent communities outside the east. The region is also full of abandoned military positions built
in the last years before the Fall. No surviving record clearly says what they were expecting to fight.
> src: CP L471–487.

### The Oceans `[PLANNED]`

**Stormreach Sea**
*Hook:* Older sailors don't believe it's whales.
The cold, unpredictable western ocean: violent weather, huge waves and strong currents, over a seabed rich in minerals
and corporate-era wrecks. Deep-water salvage crews tell of enormous things moving beneath their hulls. Scientists say
native megafauna. Older sailors disagree.
> src: CP L493–507.

**Viridian Sea**
*Hook:* Islands that drift, trenches no one has reached.
The warm southern ocean around the Verdant Fold, among Tir's richest marine ecosystems: floating colonies of native
organisms form temporary islands kilometres wide, and species migrate between here and the Sundered Delta. Just
before the collapse, research vessels logged unusual energy readings from several unexplored deep trenches. No
expedition has reached their source.
> src: CP L511–523.

**The Cobalt Deep**
*Hook:* Structures far deeper than anyone should have been able to build.
East of the continent, the seabed drops into one of Tir's deepest basins. Quantum navigation behaves unpredictably
here, frustrating automated exploration, and ships occasionally detect structures at depths early colonists could not
plausibly have built at. The Dominion keeps research vessels nearby. It publishes almost nothing they find.
> src: CP L527–539.

### The world between regions

The restored Tube network has begun to reconnect Tir, but unevenly. Major cities may be minutes apart while towns a
few hundred kilometres away still rely on caravans and battered vehicles. Connected regions get rich; unconnected
ones risk being left behind. The Karaveen move between both worlds, carrying goods, news and people where the tubes
still can't reach. Abandoned Tube nodes remain among the most valuable things an explorer can find — repairing a
single one can turn an isolated settlement into a regional power. And somewhere beneath Tir's deserts, jungles,
mountains and oceans, thousands of dormant nodes may still be waiting to wake.

> src: CP L543–561.

---

## 9. Early testing

**Kicker:** Where Ashfall is today

**Title:** Early testing: honest status

Ashfall is early. Most of what you've read on this site is the design vision — the game we are working towards.
Here is what exists today, and what it doesn't.

**What exists now.** A native Linux development build made in Unity, covering one walkable district of Ward and an
early Outer Berms survival-and-salvage loop:
- Walk the West Gate, market avenue, hill stairs and the great oasis tree; Vanguard Hall and a row of shops.
- Talk to four townspeople with branching dialogue and objectives.
- Trade at the general store; sell salvage, buy parts and supplies.
- Learn the scrap pistol at the Warden training range, then head into the Berms with it. Fit grip, barrel and
  power-cell mods, break open salvage caches and scrap heaps, refine what you find, take on a handful of field orders
  and face a tough depot elite.
- An early character sheet: attributes, skills, implant and armour slots, weapon loadouts and carry weight.
- Save and Continue.
- An early version of the in-world HUD, hotbar, music, ambience and accessibility options such as reduced motion.

**What doesn't exist yet.** The crash opening, Lattice Capacity and modules (the build has only simple implant
slots so far), the knowledge-aware
assistant, robot companions, the Anchor and recovery systems, injuries, Lattice Jacks, the regions beyond the Outer
Berms, wildlife and raiders as systems, settlement rebuilding. Those are planned, and their details will change as
we build and test them.

**What we're not offering (yet).** There's no public download, release date, store page or sign-up for build access
on this site. Accounts here are only for joining the discussion.

**Known rough edges.** The district's buildings, street dressing and planting were rebuilt at the end of September
and are still under review. Character models and animation are early. Some names in the build are placeholders and
will change. Screenshots labelled as build captures show a development build and may carry development markings.

**How you can help right now.**
- Tell us which ideas excite you, and which don't. Every chapter has its own discussion thread.
- Share ideas — for companions, implants, regions, injuries, weapons, anything.
- Push back. If a system sounds like a chore, say so. That's more useful than polite enthusiasm.
- If you've played Anarchy Online or similar RPGs, tell us what made their builds memorable to you.

**How feedback is used.** The development team reads posts here and uses them to decide what to try, keep, change
or drop. We can't promise to adopt any particular idea, and we won't pretend we have.

> src: AG §2–§3 (build contents, unaccepted 30 Sep passes, names not final), §2 (multiplayer/accounts/vehicles/regions
> not current tasks); PROJECT_BRIEF "no downloadable build"; DESIGN §4 item 9.

---

## 10. Discussion teaser & topics

**Teaser heading:** What testers are saying
**Teaser empty state:** No posts yet. Be the first to tell us what you think.
**CTA:** Browse all topics

**Topic list (slug · title · prompt):**

| Slug | Title | Prompt |
|---|---|---|
| `world` | Tir & the Fall | What do you want to discover about Tir's past? What makes a ruined world feel lived-in? |
| `ward` | Ward | What should Ward's streets, markets and people feel like? What would make you care about defending it? |
| `opening` | Waking on Tir | How should the crash and the first Lattice boot feel to play? |
| `lattice` | The Lattice | Which modules would you spend capacity on first? How should the assistant talk to you? |
| `build` | Survive & build | Attributes, implants, crafting, modular weapons — what makes a build satisfying for you? |
| `machines` | Machines that remember | What kinds of machine populations would you want to meet out in the wastes? |
| `companions` | Companions & recovery | Medical, cargo, combat or engineering — what would your first companion be? Recovery Mode or Permadeath? |
| `atlas` | Atlas of Tir | Which region would you most want to explore, and why? |
| `testing` | Early testing | Feedback on the current district build and this site. |
| `general` | General feedback | Anything else. |

**Feedback types:** Like · Idea · Feedback (labels as in DESIGN §7).

---

## Gallery captions (supplements `assets/manifest.json`; manifest captions win on conflict)

- **Concept art** filter intro: Paintings made to explore Ashfall's look and mood. They are not screenshots, and
  the game will not necessarily look like this.
- **Planned regions** filter intro: Concepts for places beyond the current build.
- **In build** filter intro: Captures from the current native development build, dated. Work in progress.

---

## /about

**Title:** About Ashfall

Ashfall is a first-person science-fiction RPG in early development, built in Unity by Teknetik. It grew out of a love
for the deep, build-driven character systems of games like Anarchy Online, and a desire to set them in a world about
survival, repair and the long aftermath of a collapse rather than another robot war.

Today the project is a native Linux development build of one district and its surrounding wasteland. This site exists
so friends and early testers can follow the ideas behind it and help shape what comes next.

Nothing on this site is a promise of a release date, platform or feature list. Systems and regions are labelled by
status: **In build** means it exists in the current development build; **Planned** means it's a design goal;
**Exploring** means we're still deciding whether and how to do it; **Concept art** is illustration, not gameplay.

> src: AG §2 (native Linux Unity build; future scope not implemented); CN L170, L286 (AO inspiration); PROJECT_BRIEF.
> Team size/names not stated in sources — do not add.

---

## /privacy (content for the implementer to adapt to the actual data model)

**Title:** Privacy

Reading this site does not require an account.

**If you create an account, we store:** your chosen username; a securely hashed version of your password (we never
store or see the password itself); the date you joined; and a session cookie that keeps you signed in. We don't ask
for your email address or real name.

**If you post, we store:** what you wrote, the topic and type you chose, when you posted, and replies linked to it.
Posts are public.

**Operational data:** to protect the site from abuse we may keep short-lived technical records such as rate-limit
counters. [Implementer: state actual log contents and retention; never log passwords.]

**Cookies:** one essential session cookie (and a security token used to protect forms). No advertising or tracking
cookies, no third-party analytics. [Implementer: confirm.]

**Deleting your data:** you can delete your own posts at any time, and delete your account from your account page.
[Implementer: state what happens to posts on account deletion.] Moderators may remove posts that break the
discussion rules.

**Contact:** [Implementer/ops: insert real contact route, or omit — do not invent one.]

---

## Discussion rules (short, shown on /discuss)

Be kind, be specific, and keep it about Ashfall. No harassment, spam or personal information. Please don't post
spoilers for other games without warning. Moderators may remove posts that break these rules.

---

## FAQ (early testers)

**What is Ashfall?**
A first-person science-fiction RPG in early development, set on Tir, a corporate manufacturing world cut off from
the rest of the galaxy. It's about surviving in the ruins, rebuilding, growing your character through implants,
gear and machine companions — and finding out what really happened to Tir.

**Is it out? When does it come out?**
No, and we don't have a release date. Ashfall exists today as a development build of one district and its nearby
wasteland.

**Can I download a build?**
Not from this site. There's no public build or access sign-up here.

**What platform is it on?**
The current development build is a native Linux build made in Unity. We haven't announced platforms for release.

**Is it multiplayer?**
The design follows one protagonist and their machine companions. Multiplayer is not part of current development,
and we're not promising it.

**Is it a shooter or an RPG?**
Both, in the sense of first-person combat inside a deep RPG. Your build — attributes, skills, implants, weapons,
mods and companions — decides what you can do, but you aim and fight in first person. The full combat system is
still to come; the current build has an early scrap pistol loop.

**What's the Lattice?**
The implant system that saved your life after the crash: a wrist computer, a neural implant and an artificial eye.
It is your interface, your progression system and your link to Tir's machines. See the Lattice chapter.

**Are there classes?**
No. There are six attributes, many skills, and everything you wear, install and bring with you. Your build is what
you make it.

**Can my character die?**
By default, no — not in the usual way. In Recovery Mode, being taken down leads to rescue, treatment and
consequences: injuries, bills, lost gear. There is a planned optional Permadeath mode for people who want real stakes.
Both are design goals and not in the current build.

**Do robot companions fight for me?**
They can, but that's only one option. Companions are full RPG builds: medics, haulers, engineers, bodyguards or a mix.
They can help you craft things you couldn't make alone and can keep you alive when things go wrong. Planned, not yet
in the build.

**How does fast travel work?**
The plan is that you rebuild it: your implants can wake dormant transport nodes called Lattice Jacks, and every node
you restore extends your network. Planned.

**Is there an in-game currency or economy?**
There are credits in the current build's trading. A fuller economy — including how nanites and Tube transport might
fit in — is something we're still exploring.

**Is this based on Anarchy Online?**
It's an original game, but it's openly inspired by what made Anarchy Online's character building so memorable —
trickle-down attributes, implants and creative ways to meet requirements. The Lattice's capacity is our take on its
NCU idea.

**Is the art on this site from the game?**
Mostly no. Images marked Concept art are illustrations made to explore the look and mood. Images marked In build are
from the development build and are labelled with their date.

**Why do I need an account to comment?**
So posts have an author and you can edit or delete your own. We only store a username and a hashed password — no
email. See the privacy page.

**Will my idea end up in the game?**
Maybe. We read the discussions and they influence what we try, but we can't promise any particular idea will be used.

**Where's the story going?**
Somewhere we're not going to spoil here.

> src: CN L4, L254–260, L566–642; DR L894–1051, L731–801; CC L11–13 (currency exploring); AG §2 (single native
> Linux build; multiplayer/accounts not current); PROJECT_BRIEF (no download/date/multiplayer). Single-player
> statement: CN describes a single protagonist and companion system and never mentions multiplayer; AG lists
> multiplayer as not a current task — phrase kept non-committal ("being designed as single-player… not promising").
