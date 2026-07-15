# PERSONS_LIBRARY_CONTROVERSIES.md — Fathers, Works Library, Thematic Layer (v2)

**Instruction to Claude Code:** `KICKOFF.md`, `CLAUDE.md`, `DATA_COMPLETION.md`,
`ROADMAP_ADDENDUM.md`, and `SITE_REFINEMENT.md` (v2) bind. Plan Mode discipline:
plan → maintainer approval → execute, one milestone at a time. IDs are permanent
(site is public); new records only. Everything stays $0 and static.

Note: static HTML generation and path-based entity URLs are specified in
SITE_REFINEMENT.md R1 and apply to all site work in this document.

---

## COMPLETION VERIFICATION PROTOCOL (applies to every milestone in this file)

A milestone is NOT complete when the work is executed; it is complete when
verified. After executing any milestone:

1. **Requirements audit:** re-read the milestone's text line by line. Produce a
   checklist mapping EVERY requirement to evidence: file paths created/changed,
   record counts, script output, or the rendered page demonstrating it. Each
   item is marked `done` (with evidence), `partial` (with what remains), or
   `not-done` (with reason). A bare "done" without evidence is prohibited.
2. **Pipeline check:** run the full validation suite and complete build
   (`make build` green); include the summary output in the report.
3. **Rendered verification:** build the site locally and inspect every page
   type the milestone touched; confirm content renders in the HTML (not an
   empty JS shell), links resolve, and required behaviors demonstrably work.
   State what was inspected and what was observed.
4. **Coverage statement (data milestones):** for roster/see/works milestones,
   state checklist-vs-database coverage explicitly (e.g., "tier checklist
   enumerates N persons; N created; K deferred with reasons; 0 silently
   missing").
5. **Honest gap statement:** list anything discovered out of scope, deferred,
   or broken elsewhere by this work.
6. **Present the report to the maintainer and STOP.** The milestone closes only
   on maintainer sign-off; the next milestone's plan may then be proposed.
   Never self-certify and continue.

---

## P1 — Person scope: roles and the admission rule (schema)

1. Person gains `role: bishop | priest | deacon | deaconess | monastic |
   layperson` (default `bishop` for existing records; set explicitly on all
   new ones).
2. **Admission rule for non-bishops** (validate.py, error level): a non-bishop
   Person must connect to the corpus via at least one of — a Work (relation
   by/about/involving), a Participation, a Relationship to an in-scope person,
   or citation as apostolic founder/evangelizer by a See, Jurisdiction, or
   Tradition record. No isolated persons.
3. Update: JSON Schema, validator, admin form, person page (role shown),
   KICKOFF.md §4.1, CLAUDE.md conventions.

## P2 — Sees fill-in: the Fathers' sees + enumerated Western promotions

1. **Eastern metropolitan/suffragan sees of the major Fathers** (starter set —
   propose additions in the plan): Caesarea in Cappadocia, Nyssa, Nazianzus,
   Sasima, Smyrna, Hierapolis (Papias), Nicomedia, Iconium, Cyrrhus
   (Theodoret), Mopsuestia (with honest disputed/condemned handling), Photike,
   Crete/Gortyna (Andrew of Crete). Each with jurisdiction_history, location,
   sources; tenures for the Fathers who held them (Basil of Caesarea, Gregory
   of Nyssa, Gregory the Theologian incl. his brief Constantinople tenure —
   reconcile with the existing Constantinople line).
2. **Western see promotions — EXHAUSTIVE list, per the standing rule that
   Western sees are promoted only by name:** Lyon (Irenaeus), Carthage
   (Cyprian), Milan (Ambrose), Hippo (Augustine — Blessed in Orthodox
   veneration; note this nuance in his veneration block), Tours (Martin).
   Pre-schism scope only; each see gets an end-of-scope note mirroring
   pre-schism-rome. Further promotions require maintainer approval by name.
3. Continue the location-discipline and gap-report coverage for all new sees.

## P3 — The Fathers roster: reconciliation method

1. Checklists (create Source records): Quasten, *Patrology* (and its Di
   Berardino continuation); the CPG author index; the Philokalia author
   roster; synaxaria for later figures. Sweep tier by tier; the plan for each
   tier enumerates candidate persons for maintainer approval BEFORE record
   creation.
2. Tiers: (i) Apostolic Fathers — audit existing (Ignatius, Clement) + add
   Polycarp, Papias; (ii) Apologists (Justin Martyr — layperson, via works);
   (iii) Nicene & Cappadocian era; (iv) desert/ascetic (Anthony via
   Athanasius's *Life*; Macrina via relationships/works; Olympias the
   deaconess via the Chrysostom correspondence); (v) Byzantine synthesis
   (Maximus the Confessor, John of Damascus, Symeon the New Theologian — with
   their Participation records: Maximus ↔ the Constantinople 662 trial ↔
   vindication at Constantinople III; John of Damascus ↔ Hieria 754
   posthumous condemnation ↔ Nicaea II); (vi) post-Byzantine (Nicodemus the
   Hagiorite, incl. his role as Pedalion editor — a Work `about` councils).
   Women of the Church are included throughout under the same admission rule,
   never as a separate category.
3. Every person: role, veneration block where applicable (sourced), works
   links, relationships where documented (Macrina `teacher` of her brothers —
   sourced to Gregory of Nyssa's *Life of Macrina*).

## P4 — Works library: survival, transmission, repositories

1. **Schema — Work gains:**
   - `survival: extant | fragmentary | lost | extant-in-translation-only`
     (+ `survival_note`; e.g., Adversus Haereses: complete only in Latin,
     Greek fragments).
   - `preserved_in: [work-id]` for fragmentary/lost works surviving as
     quotations (Papias → Eusebius's Historia Ecclesiastica, Irenaeus).
     Validator: preserved_in only on fragmentary/lost works; referenced works
     must exist.
2. **Repositories reference list** (controlled list, extensible only with
   maintainer approval): CCEL, New Advent, tertullian.org (incl. its
   additional-translations collection), earlychristianwritings.com,
   documentacatholicaomnia.eu (PG/PL scans — PG column citations link to page
   images where feasible), archive.org, HathiTrust, syri.ac (Syriac
   transmission). In-copyright series (Sources Chrétiennes, Fathers of the
   Church, Popular Patristics/SVS, Dumbarton Oaks Medieval Library) link to
   publisher/WorldCat per existing rights rules. LINK, NEVER RE-HOST.
3. **Edition links get the archive treatment**: `archived_url` required on
   edition URLs (same rule as sources).
4. **Link-rot checker** (promoted from backlog): `scripts/check_links.py` —
   validates all live URLs (sources + editions), reports dead links, suggests
   the stored archived_url as replacement; runnable via make target and
   surfaced on the admin dashboard. Reports only; never auto-replaces.
5. **Populate**: works for every P3 person, with survival status; the Papias
   fragments as the exemplar of preserved_in; audit all existing works for
   the new fields (default extant only when actually verified as such).
6. `influenced` relationship type: permitted ONLY with scholarly-grade
   sourcing; validator enforces (influenced without a scholarly source =
   error). Never inferred.

## P5 — Controversies taxonomy (thematic layer)

1. Controlled vocabulary `data/controversies/` — one small record each (id,
   neutral label, brief sourced description, variant terms, approximate
   span): target 15–20 entries, ceiling 25. Starter set: Gnosticism,
   Montanism (New Prophecy), Novatianism, Donatism, Arianism, Pneumatomachian
   controversy, Nestorian controversy, Christological controversy (Chalcedon;
   variant terms noting miaphysite/monophysite usage — see naming rule),
   Monothelitism, Iconoclasm, Photian/Filioque controversy, Bogomilism,
   Hesychast controversy, Unionism (Lyon/Florence), Old Believer schism,
   Phyletism, Calendar controversy.
2. **Naming rule (feeds docs/NAMING.md):** labels use neutral scholarly
   terminology; terms considered pejorative by living communions (e.g.,
   "monophysite" for the Oriental Orthodox position, whose own term is
   miaphysite) appear only as recorded variants with a note, never as the
   display label.
3. Taggable via `controversies: [id]` on Event, Work, and Participation.
   Optional per-tag sourced note.
4. **The database records WHERE and WHEN, never WHY**: no causal/substrate
   claims (pre-Christian religious geography → heresy receptivity) anywhere
   in data. Standing boundary; add to CLAUDE.md.

## P6 — Site additions (coordinate with SITE_REFINEMENT R-milestones)

1. **Library section**: works index filterable by author, century, genre,
   language, survival; work pages with attribution, survival + transmission
   note, preserved_in chain rendered as "survives in quotations within → …",
   editions with read-links (and archived fallbacks). Lost/fragmentary works
   display honest badges — absence is information.
2. **Controversy pages**: per controversy — description, timeline of tagged
   events, tagged persons via participations, tagged works; the assembled
   story from existing records.
3. **Controversy map layer**: optional overlay on the existing map, deriving
   geography from tagged data only (council locations, protagonists' sees,
   regions named in the controversy record) with the time slider. No
   editorialized regions: if it isn't derivable from tagged records, it
   doesn't render.
4. **Bibliography page**: browsable render of all Source records, grouped by
   type/reliability, with archive links.
5. **Glossary page**: static, maintainer-curated (placeholder + proposed term
   list in the plan: autocephaly, see, tenure, synod, glorification,
   oikonomia, etc. — Claude Code proposes definitions; the maintainer
   edits/approves before publication, consistent with the no-unreviewed-prose
   rule).
6. Reading lists: BACKLOG (capture in BACKLOG.md, do not build).

## Ordering (proposed — confirm or amend in your first plan)

P1 (schema, small) → P2 (sees) → P3 tier-by-tier with P4 works populated per
tier (so each tier lands complete: persons + roles + works + survival) → P5
(taxonomy + tagging pass over existing data) → P6 (site, merged into the
SITE_REFINEMENT sequence — propose the merged ordering with reasoning for
approval).

## Standing boundaries (additions to the rejected list)

- No causal claims about heresy origins or religious substrates in data.
- No re-hosting of texts; links + archives only.
- No unsourced `influenced` claims.
- Non-bishop persons only via the admission rule; no general clergy coverage.
- Western sees only from the enumerated promotion list (P2.2) or later
  by-name approvals.
