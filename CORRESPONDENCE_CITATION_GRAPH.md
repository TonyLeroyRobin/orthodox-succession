# CORRESPONDENCE_CITATION_GRAPH.md — The Succession of Ideas (Post-Freeze Module)

**Instruction to Claude Code:** `KICKOFF.md`, `CLAUDE.md`, and all prior specs
bind. **GATE: do not begin this module until Q-final (v0.1.0 + Zenodo + governance
docs) is signed off and the maintainer explicitly initiates it.** Plan Mode
discipline: plan → maintainer approval → execute, one milestone at a time. IDs are
permanent. Everything stays $0 and static.

Concept: the database already models the succession of hands (consecrations) and
the succession of formation (tonsured/teacher/spiritual-father relationships).
This module adds the succession of IDEAS — documented correspondence and
citation between Fathers and their works — as a third network, rendered on its
own graph page and NEVER blended with the consecration graph or the formation
relationships. Three networks, three meanings.

## COMPLETION VERIFICATION PROTOCOL (applies to every milestone here)

After executing any milestone: (1) requirements audit — line-by-line checklist,
every item done (with evidence: paths, counts, rendered pages) / partial /
not-done; bare "done" prohibited. (2) Full validation + build, summary included.
(3) Local render inspection of every touched page type; state observations.
(4) Coverage statement for data milestones ("seed list enumerates N edges; N
created; K deferred with reasons; 0 silently missing"). (5) Honest gaps.
(6) Present report and STOP for maintainer sign-off.

## C1 — Schema (derive, don't duplicate)

1. **`addressee: [person-id]`** on Works of genre `letter` (and encyclicals
   where addressed). Correspondence edges are DERIVED from letter-works at
   build time — never stored as separate relationship records. One fact, one
   home: the letter is the evidence; the edge falls out of it.
2. **`cites`** on Work: list of `{work: work-id, locator: "", sources: []}` —
   a documented naming/quoting of one work by another; locator and source
   REQUIRED per entry (validator, error level).
3. **`responds_to: [work-id]`** on Work — for polemical/responsive works
   (e.g., Theodoret's Eranistes; Origen's Contra Celsum).
4. **External works** (targets of responds_to/cites whose authors are outside
   the admission rule, e.g., Celsus's True Word): permit minimal Work records
   with `external: true` and `author_name` as plain text — NO Person record is
   created for out-of-scope authors. External works are excluded from Library
   counts/index by default (visible on the graph and on the citing work's
   page), carry survival status like any work (True Word: lost, substantially
   preserved via quotation in Contra Celsum — `preserved_in` applies).
5. `preserved_in` (existing) remains the heavy special case of citation;
   validator: a work may not both `cites` and `preserved_in` the same target
   redundantly — preserved_in implies citation.
6. **Epistemic tiers (STRICT):**
   - Tier 1, documented correspondence: surviving letters with addressees.
   - Tier 2, documented citation/response: passage-sourced cites/responds_to.
   - Tier 3, inferred influence: stays EXCLUSIVELY in the existing
     `influenced` relationship (scholarly-source-required, never inferred);
     renders on this graph only with a visually distinct style and only when
     it passes its validator. No edge ever appears because "surely X read Y."
   The graph must be smaller than the truth and never larger.

## C2 — Seed data (curated; no mass mining)

Standing scope rule (add to CLAUDE.md): citation/correspondence edges are
entered opportunistically WITH locators during other verification work, plus
the curated famous-correspondence list below. Systematic mining of PG/PL is
prohibited.

Seed list (a floor; propose additions by name in the plan):
1. **Jerome ↔ Augustine** — both sides survive. Jerome enters under the
   admission rule (priest-monk, never a bishop; role: monastic; admitted via
   works; veneration block sourced — he is venerated in Orthodoxy).
2. **Basil ↔ Athanasius**; **the Cappadocians among themselves** (Basil,
   Gregory the Theologian, Gregory of Nyssa — with Macrina's documented place
   via existing relationship records).
3. **Cyril ↔ Nestorius** (Third Letter already in the library; add the
   counterpart correspondence with honest attribution/survival data).
4. **Leo ↔ Flavian** (Tome of Leo already carries the addressee implicitly —
   make it explicit).
5. **Chrysostom ↔ Olympias** — and model the LOST half: create Olympias's
   letters as a Work with `survival: lost`, sourced to the evidence of
   Chrysostom's surviving side. Lost voices are information.
6. **Origen's Contra Celsum ↔ Celsus's True Word** (external, lost,
   preserved_in Contra Celsum) — the exemplar external-work case.

## C3 — Site views

1. **Ideas graph page**: documented edges only by default (Tier 1 solid /
   Tier 2 dashed; Tier 3 influence as a distinct optional overlay, off by
   default); node = person, edge tooltip shows the evidencing work/locator;
   click-through to work and person pages; legend states the tiers plainly.
   Separate page from the consecration graph with an explanatory line
   distinguishing the three successions.
2. **Works timeline page**: all dated works on a time axis; lanes by genre (or
   region toggle); color by controversy tag where tagged; context era-bands
   behind (reuse the timeline machinery). Pure rendering — no new data
   required beyond existing dates.
3. Person pages: a "Correspondence" line within Works when addressee edges
   exist ("Letters to/from …").
4. Optional analytics output (info-level build report, not a page yet):
   citation in-degree ranking ("most-cited works/authors") — the works-layer
   sibling of the lineage-convergence question; page deferred to backlog.

## C4 — Boundaries

- No mass bibliography mining; locator-and-source or the edge does not exist.
- No influence edges outside the gated `influenced` relationship.
- External (out-of-scope-author) works never create Person records and never
  inflate the Library.
- This graph is never merged with, or rendered on, the consecration graph.

Ordering: C1 → C2 → C3. Recommended as the FIRST post-freeze module (it is
mostly derivation from existing library data).
