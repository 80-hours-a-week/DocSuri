# Requirements Clarification Questions

**Stage**: INCEPTION → Requirements Analysis · **Depth**: Comprehensive · **Date**: 2026-06-15

## Intent Analysis (from your Prompt 1)
- **Request type**: New Project (greenfield restart)
- **Scope**: An AI-assisted research-support application for researchers and postgraduates, spanning the research lifecycle but to be narrowed to a single-anchor MVP.
- **Complexity**: High · **Clarity of brief**: Vague (one sentence) → questions below resolve the scope.
- **One-liner**: _Build an AI tool that supports researchers and postgraduates in their research work, scoped from a one-sentence brief into a focused, demo-able MVP._

## How to answer
Fill in the letter after each `[Answer]:` tag. If no option fits, pick the **Other** letter and describe your choice after the tag. You can answer **directly in this file** or just **reply in chat** (e.g. `Q1: B, Q2: C, …`) — either works, and you don't have to answer all at once. The first four questions (goal, persona, job, magic moment) are the keystones; the rest refine from them.

When you're done (or want to answer in rounds), say so and I'll check for contradictions before writing `requirements.md`.

---

## Section A — Product & Scope

## Question 1 — Cycle goal / success bar
What is the goal and success bar for THIS cycle (what does "done" mean this time)?

_Why it matters:_ Determines how seriously compliance, auth, citation-faithfulness, and cost controls are actually built versus stubbed.

A) Throwaway demo — boots and looks convincing in a sprint review; no real users, disposable infra

B) Internal pilot — real researchers/postgrads use it on real tasks; reliable enough to trust, not publicly hardened

C) Production launch — durable, supportable service for ongoing real use, with the operational/compliance rigor that implies

D) Learning exercise — the point is practicing AI-DLC and AWS; the product itself is secondary

E) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 2 — Primary persona
Which SINGLE user must v1 delight first (others become secondary)? The brief names two divergent types.

_Why it matters:_ Picking ONE primary persona is the most scope-shaping choice — an expert PI and a beginner postgrad need almost opposite things.

A) Postgraduate / PhD student doing an early-stage literature review and checking thesis novelty (needs guidance, summaries, reading-level help)

B) Active researcher / postdoc tracking a specific subfield (needs depth, expert vocabulary, breadth, recency)

C) Supervisor / PI overseeing several students' topics and reading lists (needs to vet directions, spot overlap, curate reading)

D) Undergraduate / coursework newcomer reading papers (needs heavy translation and jargon de-jargoning)

E) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 3 — Primary job-to-be-done (MVP anchor)
Which ONE research-lifecycle stage should the MVP anchor on as its primary job (everything else becomes secondary or out-of-scope for v1)?

_Why it matters:_ The five clusters are effectively five different products with different data, UX, and eval needs — naming the anchor bounds everything downstream.

A) DISCOVERY & search — find relevant papers fast (Semantic Scholar / ResearchRabbit-style)

B) EVIDENCE SYNTHESIS / Q&A — ask a research question, get a cited, evidence-backed answer (Elicit / Consensus-style)

C) READING & COMPREHENSION — summarize and explain individual papers, chat with a PDF (Scholarcy / SciSpace-style)

D) REFERENCE & note MANAGEMENT — collect, organize, annotate, and cite a personal library (Zotero + Obsidian-style)

E) WRITING & drafting — help structure and write the manuscript with citations (Overleaf + Paperpal-style)

F) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 4 — The "magic moment" demo journey
Within that anchor, which ONE end-to-end journey is the "magic moment" the demo must absolutely nail (others can be partial)?

_Why it matters:_ One hero journey demos better than four half-built ones; this becomes the primary UI surface and the demo's success criterion.

A) Discover: type a plain-language research intent and get the most relevant papers in seconds

B) Comprehend: open a paper and get a reading-level-adapted summary plus translation of dense passages

C) Synthesize: ask a question and get an answer with inline citations, or a comparison table across many papers

D) Differentiate: paste a topic/draft and see overlap with prior work plus candidate research gaps

E) Trace: pick a paper and visually walk its citations to find foundational and follow-up work

F) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 5 — Discipline scope
What discipline scope should the v1 corpus and features target?

_Why it matters:_ Discipline scope cascades into paper source, citation coverage, and non-English / scanned-PDF handling.

A) Single field, deep (e.g. AI/ML over arXiv) — narrow corpus, fast demo, like the prior cycle

B) Broad STEM (CS, bio, physics, engineering) — wider corpus, mixed PDF quality

C) Humanities & social sciences — book/chapter citations, more non-English, fewer preprints

D) Discipline-agnostic / broad — works across any field the user searches

E) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 6 — Primary paper source
What should be the PRIMARY source of papers at launch? (Each implies a very different integration and discipline coverage.)

_Why it matters:_ The data source is the deepest architecture fork — it sets integration effort, discipline coverage, and whether full text even exists.

A) The researcher's own PDF library, uploaded or synced (no external API, any field, paywall-proof)

B) arXiv API (free, full-text preprints, but STEM/CS/physics/math-heavy)

C) PubMed / PMC E-utilities (free, biomedical & life-sciences focused)

D) Crossref + OpenAlex / Semantic Scholar (broad cross-discipline metadata + citation graph, mostly abstracts not full text)

E) Sync with an existing reference manager (Zotero / Mendeley, with ORCID identity)

F) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 7 — What the AI reads + AI strategy + synthesis scale
What should the AI actually read and reason over, and via which AI strategy and at what synthesis scale? (Sets ingestion, grounding fidelity, latency, and cost.)

_Why it matters:_ This couples document input + AI approach + single-vs-many-paper scale into one decision that defines the ingestion pipeline and hallucination posture.

A) Metadata + abstracts only, with extractive/non-generative assist (summaries, dedup, citation-graph nav) — cheapest, lowest hallucination, no vector DB

B) Per-document full text — chat with / summarize ONE uploaded PDF at a time (parsing/OCR needed, exact-quote grounding, no vector store)

C) RAG over a persistent personal corpus — multi-paper synthesis or "ask my whole library" across MANY documents (vector store, e.g. Bedrock KB + S3 Vectors, as the prior cycle)

D) Agentic live search — an agent queries external scholarly APIs and chains steps on demand (most capable, highest cost/latency/complexity)

E) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 8 — Delivery platform
What is the primary delivery platform? (Decides auth model, offline story, and whether local files are first-class.)

_Why it matters:_ Platform dictates auth, offline/local-file needs, and the ingestion path.

A) Responsive web application (browser-based, nothing to install) — matches the team's prior Amplify/Next.js experience

B) Installable desktop app (Zotero/Mendeley-style) — reads local PDF folders, works offline

C) Mobile-first app for reading and querying on the go

D) Browser extension overlaying publisher pages and Google Scholar (the only practical way to ride on Scholar, which has no API)

E) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 9 — Solo vs collaborative
Is v1 a solo tool or collaboration-aware? (Major architecture fork for auth and data model — costly to retrofit.)

_Why it matters:_ Solo vs collaborative decides multi-tenancy and auth, which are expensive to add later.

A) Solo, anonymous — no login, no saved state across sessions (fastest demo, like the prior cycle)

B) Solo with personal accounts — login, private saved searches/library, history

C) Small-group shared — a lab or reading group shares one library, lists, and annotations

D) Supervisor-student linked — advisor curates/reviews, student consumes, with handoff between them

E) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 10 — Audience / reach & access
Who is the intended audience/reach this cycle, and how do they get access?

_Why it matters:_ Reach drives auth, tenant isolation, GDPR exposure, abuse controls, and the cost ceiling.

A) A single lab or our own team — a handful of known users, minimal access control

B) A department or institution — many users behind SSO, with shared and per-user corpora and data isolation

C) Public / open self-signup — anyone can register, like Elicit / Consensus / Perplexity

D) Invite-only external pilot — a curated set of outside researchers onboarded manually

E) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 11 — AI-writing / academic-integrity stance
Where on the spectrum from evidence-grounded assistance to AI-generated WRITING should the product sit, given academic-integrity and journal AI-authorship policies?

_Why it matters:_ The integrity / AI-authorship stance sets product positioning and legal/reputational exposure; many journals and universities restrict undisclosed AI-generated writing.

A) Read-only evidence assistant — finds, summarizes, compares papers with citations; never drafts prose for the user's own paper

B) Drafting aid with mandatory citations & AI-use disclosure — can produce text, but every claim is sourced and AI involvement is flagged

C) Full writing assistant — drafts manuscript sections / literature reviews as polished prose; integrity compliance left to the user

D) Defer — ship only retrieval/summarization now and decide the writing stance later

E) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 12 — Source-access & copyright posture
What is the source-access and copyright posture for the papers/PDFs the system ingests?

_Why it matters:_ Copyright posture (open-access vs user-upload vs full-text) is a hard constraint on the ingestion pipeline and the legal-risk profile.

A) Open-access only — restrict to arXiv, PubMed Central, DOAJ, OpenAlex and similar redistributable sources

B) User-uploaded only — operate solely on documents the user already has lawful access to; store nothing they don't supply

C) Metadata + abstracts only — index titles/abstracts/citations without storing full paywalled text

D) Fetch and store full text broadly, including paywalled PDFs — accept the copyright exposure for richer answers

E) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 13 — Citation-faithfulness / hallucination control
What level of citation-faithfulness / hallucination control must outputs meet this cycle (the core correctness/trust attribute)?

_Why it matters:_ Fabricated citations are the signature failure mode of LLM research tools — grounding strictness decides whether we need a retrieval-grounded architecture with refusal behavior.

A) Strict — every factual claim links to a specific retrieved passage; refuse to answer when no supporting source exists

B) Cited-but-lenient — show sources where available but allow unsourced synthesis, with a visible "verify before citing" warning

C) Best-effort for demo — plausible citations acceptable now; rigorous grounding deferred to a later cycle

D) Human-in-the-loop — surface sources and expect the researcher to verify every claim themselves

E) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 14 — Quality acceptance (how we'll know it works)
Beyond citation grounding, which quality attribute must the MVP demonstrably meet, and how will we know it passed?

_Why it matters:_ Defines the acceptance mechanism (eval set / accessibility / graceful degradation) — how we KNOW it works, not just that it boots.

A) Output quality verified by an eval set — a held-out set of questions/papers with expected answers the demo must score against (testability over a fixed gold set)

B) Accessibility & multilingual readability — WCAG-conformant UI and non-English / reading-level support for international postgrads (institutional accessibility duty)

C) Reliability & graceful degradation — clear handling of ingestion failures, scanned/garbled PDFs, empty-retrieval, and API outages rather than silent wrong answers

D) Demo-only spot-check — a human eyeballs a few outputs before the sprint review; no formal acceptance gate

E) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 15 — Cost vs richness ceiling
Where should the MVP sit on the cost-vs-richness spectrum, and at what scale?

_Why it matters:_ Fixes the cost/model/concurrency ceiling and the privacy/self-host axis before design (mirrors the prior cycle's CostGuard hard-stop).

A) Thin demo on a hard cost cap — cheapest model (e.g. Haiku), abstracts only, internal pilot, strict monthly budget guardrail

B) Mid-tier — full-text RAG on a moderate model, a single lab/group (tens of users)

C) Rich experience — frontier model, full-text + citation graph, public/campus beta (hundreds+ concurrent), per-query cost accepted

D) Privacy-first / self-hostable — keep papers and queries on infrastructure the institution controls, even at higher engineering cost

E) Other (please describe after [Answer]: tag below)

[Answer]: 

---

## Section B — AI-DLC Extension Opt-Ins

_These three decide which extra rule sets the workflow enforces for the rest of the project. They're recorded in `aidlc-state.md`; opting out means those rules are never loaded._

## Question: Security Extensions
Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)

B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question: Resiliency Extensions
Should the resiliency baseline be applied to this project?

**What this extension is.** Enabling it applies a set of **directional, design-time best practices** for building resilient systems, derived from the **AWS Well-Architected Framework (Reliability Pillar)** and resilience-review guidance. It steers requirements, design, and code toward fault tolerance, high availability, observability, and recoverability — covering 15 practice areas across business goals, change management, observability, high availability, disaster recovery, and continuous improvement.

**What this extension is NOT.** Enabling it does **not** make your workload production-ready, nor does it certify or guarantee any availability, RTO, or RPO target. It is a **starting point** that scaffolds good resiliency decisions early — it is not a substitute for a formal **AWS Well-Architected Review** of the built system.

Treat the output as a well-grounded **first draft of your resiliency posture** to build on and validate — not a finished, production-certified result.

A) Yes — apply the resiliency baseline as directional best practices and design-time guidance (recommended for business-critical workloads, as an informed starting point that you can validate and harden before go-live)

B) No — skip the resiliency baseline (suitable for PoCs, prototypes, and experimental projects where rapid iteration matters more than reliability)

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question: Property-Based Testing Extension
Should property-based testing (PBT) rules be enforced for this project?

A) Yes — enforce all PBT rules as blocking constraints (recommended for projects with business logic, data transformations, serialization, or stateful components)

B) Partial — enforce PBT rules only for pure functions and serialization round-trips (suitable for projects with limited algorithmic complexity)

C) No — skip all PBT rules (suitable for simple CRUD applications, UI-only projects, or thin integration layers with no significant business logic)

X) Other (please describe after [Answer]: tag below)

[Answer]: 
