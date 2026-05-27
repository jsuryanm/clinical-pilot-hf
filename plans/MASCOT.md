# CliniqAI — Mascot Brief

## 1. Does CliniqAI need a mascot?

**Yes.** Three reasons specific to this product:

1. **Trust in clinical AI is the #1 sales blocker.** Doctors and nurses adopt tools they feel friendly toward faster than tools that feel like cold software. A mascot personifies "an assistant that helps, never decides" — exactly the human-in-the-loop ethos the README commits to.
2. **The product spans seven agents.** Without a single character, the brand fragments. One mascot ties Documentation, Appointments, Roster, Handover, Discharge, Clerical, and Wiki into one familiar face on every screen.
3. **WhatsApp is the patient channel.** Patients receive reminders, post-visit summaries, and 72-hour check-ins in their personal messaging app. A small avatar at the top of those messages drops the "robot spam" feel.

The mascot should never appear on a clinical recommendation surface (e.g., a SOAP note draft) — only on supporting / orchestration / communication surfaces, so it never undermines the seriousness of clinical content.

---

## 2. Recommended mascot: **"Asha"**

### 2.1. Why this name

**Asha** (आशा) means "hope" in Hindi and Sanskrit. It is also the official name of India's **Accredited Social Health Activist** programme — the community health workers who are the trusted, non-clinical face of public healthcare in rural India. Borrowing this name signals:

- A **helper, not a decider** — Asha workers assist nurses and doctors; they do not diagnose.
- A **culturally Indian product**, not a US import dressed in saffron.
- Warmth and approachability that "CliniqAI" alone does not carry.

The name is short, gendered-neutral in modern use, easy to type in chat, and unique enough to trademark.

### 2.2. Visual concept: the origami crane formed from a folded medical chart

A **friendly origami-paper crane** whose body is recognisably folded from a medical record (you can see a faint EKG line and a pulse trace along one wing). The crane shape carries three meanings that all fit CliniqAI:

- **Paperwork transformed.** Literal metaphor — the burden of paper folds itself into something graceful that flies away. This is the elevator pitch of the product, made visual.
- **Cranes are messengers** across South Asian, Japanese, and Western iconography — fitting for an agent that delivers reminders, briefs, and follow-ups.
- **Origami is precise, structured, and reversible.** Mirrors the "structured Pydantic outputs, full audit trail, human can always unfold the decision" architecture.

### 2.3. Design specification

| Attribute | Spec |
|---|---|
| Form | Stylised origami crane, ~3 visible folds, semi-flat shading (not photoreal) |
| Material texture | Subtle paper grain; one wing shows a faint EKG trace, the other a faint Devanagari character "आ" (the first letter of "Asha") |
| Primary colour | **Soft teal #2BB6A6** — clinical, calm, not corporate blue |
| Accent colour | **Marigold #F4B45A** — a small triangular fold near the head; ties to Indian iconography without being literal |
| Eye | Single small dot, friendly, slightly upturned |
| Default pose | Mid-flight, slight forward lean, wings extended but relaxed |
| Optional poses | Holding a tiny clipboard (Documentation), perched on a calendar (Appointments), carrying a small WhatsApp envelope (Communication), standing next to a chart (Handover) |
| What to avoid | Stethoscopes, doctor coats, hospital crosses, sirens — these read "I am the doctor" and break the human-in-the-loop promise |
| Backgrounds | Cream paper or off-white; never a hospital scene |

### 2.4. Where Asha appears

| Surface | Asha's role |
|---|---|
| Splash screen / loader | Folding animation: paper → crane in 1.5s |
| Doctor approval queue (empty state) | "Nothing waiting for you. Asha is folding the next one." |
| WhatsApp avatar for patient messages | Small circular Asha headshot |
| Nurse handover brief header | Asha holding a small clipboard |
| 404 / error pages | Asha looking puzzled, one wing slightly off-fold |
| Pitch deck cover, hoodie, stickers | The full crane |
| **Never on:** SOAP draft body, discharge summary body, lab result rendering | Clinical content stays clinical |

### 2.5. Personality and voice (for microcopy)

- **Tone:** quietly helpful, never cute-aggressive. Closer to "your sharp colleague who's already prepared the file" than a chatty consumer assistant.
- **First-person?** No. Asha never says "I" or signs messages. The mascot is a **face**, not a voice — the system speaks plainly without anthropomorphising itself, which preserves clinical seriousness.
- **Loading copy examples:** "Folding your brief…", "Reading the chart…", "Almost ready for your review."

---

## 3. Claude-generated design prompt

Paste this into Claude (image-capable) or Claude.design to generate the first mascot pass. Iterate from here.

```
Design a friendly mascot called "Asha" for an Indian clinical-operations AI product
called CliniqAI. The mascot is a stylised origami paper crane folded from a sheet of
a medical chart. Show one wing carrying a faint, soft EKG pulse line and the other
wing carrying a single small Devanagari character "आ" (light brushstroke style).

Style: soft semi-flat illustration, 3–5 visible paper folds, subtle paper grain
texture, no hard outlines. Cream off-white background. The crane is mid-flight,
slight forward lean, wings extended but relaxed, a single friendly upturned-dot
eye. Soft drop shadow underneath.

Palette: primary teal #2BB6A6, accent marigold #F4B45A on a small triangular
fold near the head, paper white #FAF7EF body, charcoal #2A2E33 for the eye and
EKG line, faint warm grey #C8C0B3 for paper folds.

The mascot must feel calm, competent, and warm — like a quiet helper. Avoid:
stethoscopes, doctor coats, medical crosses, hospital settings, robots, screens,
chatbubbles, or anything that suggests the mascot makes decisions on its own.

Deliver four variations:
1. Hero pose — mid-flight, three-quarter view, full body
2. Circular avatar crop — for WhatsApp profile, head and upper wings only
3. Working pose — perched, holding a tiny clipboard (Documentation agent)
4. Loading pose — partially unfolded paper, mid-transformation, used for splash screen

Output should be transparent PNG, vector-friendly so it can be redrawn in SVG later.
```

---

## 4. Quick alternatives, ranked

If the team rejects the crane, in order of preference:

| Option | Rationale | Why not first choice |
|---|---|---|
| **Vidya the owl** | Owl = wisdom, scholarly; "Vidya" = knowledge | Closer to a generic "knowledge assistant"; loses the "paperwork transformed" metaphor |
| **A tea-cup spirit (Chai)** | Warm, ubiquitous in Indian hospital break-rooms; signals "your colleague over chai" | Risks being too casual for clinical buyers; harder to scale across agent surfaces |
| **A peacock feather (not a peacock)** | Indian, elegant, recognisable; abstract enough to never overshadow clinical UI | Less narratively rich — hard to give it poses or moods |
| **An abstract logomark only, no character** | Lowest brand risk | Loses every reason a mascot exists in the first place |

---

## 5. Recommendation

Adopt **Asha the origami-paper crane** as the official CliniqAI mascot. Generate the four design variations above with Claude, refine to SVG, and roll it out on the splash screen and WhatsApp avatar first — those are the two surfaces where trust gain per pixel is highest.
