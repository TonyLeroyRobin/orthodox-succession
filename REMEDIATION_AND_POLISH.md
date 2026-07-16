# REMEDIATION_AND_POLISH.md — Review Findings, Canons, Saints View, Final Polish

**Instruction to Claude Code:** `KICKOFF.md`, `CLAUDE.md`, and all prior spec
documents bind. Plan Mode discipline: plan → maintainer approval → execute, one
milestone at a time. Everything stays $0 and static. This document responds to a
full external review of the live site; its ordering is deliberate and ends with
the v0.1.0 release freeze — do not reorder the freeze earlier.

## COMPLETION VERIFICATION PROTOCOL (applies to every milestone here)

After executing any milestone: (1) re-read its text line by line and produce an
evidence-mapped checklist — every requirement marked done (with file paths,
counts, or rendered-page proof), partial, or not-done; bare "done" is
prohibited. (2) Run full validation and build; include summary output.
(3) Build the site locally and inspect every page type touched; state what was
observed. (4) For data milestones, state coverage explicitly ("audit found N
issues; N resolved; K deferred with reasons; 0 silently skipped"). (5) List
gaps and side-effects honestly. (6) Present the report and STOP for maintainer
sign-off before the next milestone.

---

## Q1 — Data integrity: deduplication and name hygiene

1. **Person dedup audit.** Known duplicate pairs (resolve via the admin
   merge/deprecate wizard; unpublished-never-verified drafts may be
   hard-deleted): Gennadios II Scholarios / Gennadius Scholarius; the two
   Constantine Leichoudes; the two Atticus of Constantinople; the two Andrew
   the Apostle; Dositheus duplicated across Constantinople and Jerusalem;
   Eustathius/Eustatius of Alexandria. Then a FULL sweep: new validator —
   person near-duplicate detection (similar normalized name + same see +
   overlapping dates → warning report), run across the whole dataset; resolve
   every hit or record why it is a genuine distinct person.
2. **Work dedup:** the Panarion exists twice (`panarion` and
   `panarion-epiphanius`) — merge; re-run the work duplicate detector across
   the library.
3. **Name hygiene pass:** add optional `epithet` field to Person (the Great,
   the Confessor, the Theologian, Chrysostom, the Dialogist…), sourced like
   any claim. Fix leaked data-notes in name fields (e.g., John of Damascus
   rendering as nested parenthetical commentary), residual foreign-language
   labels (e.g., "Kyrill I" for Cyril of Jerusalem), and honorific prefixes in
   display names.
4. **Display-name formula** (build-time, used on every index/list/link):
   epithet if present, else primary see; all list entries render
   "Name — see/epithet, dates". No bare ambiguous names anywhere on list
   pages.
5. Fix the century-ordinal bug ("21th" → "21st"; correct 1st/2nd/3rd
   generally).
6. Classification checks (verify, don't assume): Cappadocian-see persons filed
   under the Constantinople jurisdiction folder; Hilary of Poitiers's route of
   admission (Poitiers is NOT on the Western promotion list — if he entered
   via tenure, propose the see for by-name sanction or re-route his admission
   via works); ensure Origen and Theodore of Mopsuestia carry their
   conciliar-condemnation Participation records (553) so their inclusion is
   visibly honest.

## Q2 — ID migration (the one sanctioned window) + redirect infrastructure

The site is public but NOT yet released (no v0.1.0, no DOI). This milestone is
the single sanctioned ID-correction window; after the Q-final freeze, IDs are
permanent forever.

1. Build a redirect/alias mechanism for static pages (alias file → generated
   redirect stubs at old paths).
2. Migration plan (present the full old→new mapping for approval before
   executing): eliminate `-0000` placeholder years (use earliest attested
   year per convention); re-slug foreign-language IDs (abrame-ier-de-…,
   cyrille-iii-d-…, athanasios-iv-de-…); strip honorific prefixes
   (patriarch-…, archbishop-…, ecumenical-patriarch-…) from ID slugs.
3. Every migrated ID: redirect stub at the old URL; all internal references
   re-pointed; validation green; sitemap.xml regenerated.

## Q3 — Link integrity

1. **Placeholder-link ban:** validator error for any source/edition URL
   matching search-query patterns (e.g., `search?query=`); links must target
   concrete documents/items.
2. **Render-guard:** sources without a resolvable URL render as plain print
   citations plus a WorldCat "find in a library" link — never a dead or fake
   anchor.
3. **Remediation pass:** pin real archive.org item URLs for the public-domain
   staples (Hefele volumes, the Pedalion scan, Mansi where available,
   Percival/NPNF), with proper archived_url snapshots of the item pages.
4. Wire `check_links.py` into the build report.

## Q4 — Library upgrades

1. Editions gain `identifiers: {isbn?, oclc?, worldcat?}`; render "find this
   edition" via WorldCat/ISBN on work pages.
2. **Secondary literature (relation: about) — gated inclusion:** admitted when
   (a) already used as a cited Source, or (b) maintainer-approved landmark
   studies, max ~5 per person, proposed in plans by name. Person pages gain a
   "Further reading" subsection rendering about-relation works. Never
   auto-import bibliographies.
3. Library index: author column uses the Q1 display-name formula.

## Q5 — Canons layer (ecumenical + Quinisext-received scope)

1. New record type `canon/<council-suffix>/<number>`: number, full English
   text, brief note, cross-references (`cites: [canon-id]`), sources, status.
2. **Text/rights rule (STRICT):** full canon texts ONLY from public-domain
   translations (Percival, NPNF II.14 — already a Source). The Pedalion's
   English translation (Cummings, 1957) is IN COPYRIGHT: cite it by page for
   the received interpretation, quote at most brief phrases, and NEVER copy
   its text into records — even if provided as a PDF for reference and
   verification.
3. Cross-reference the corpus's own structure (e.g., Quinisext canon 2's
   enumeration links to the councils and canons it receives).
4. Council pages render their canons; canon numbering discrepancies between
   traditions (e.g., Sardica) recorded in notes.
5. Boundary amendment (record in CLAUDE.md): the no-re-hosting rule carves out
   public-domain canon TEXTS as data records; books and treatises remain
   link-only.

## Q6 — Saints view + liturgical calendar

1. **Saints index page:** derived entirely from existing data — all persons
   with `veneration.status: saint`, filterable by jurisdiction/century,
   sortable by feast day. No new data class; no mass hagiographic import
   (standing rule: the admission rule governs who can ever appear).
2. **"Commemorated today" on the home page** (activates ROADMAP_ADDENDUM C2):
   persons whose feast_days match today's date, Julian/Gregorian toggle.
3. Create Source record: Makarios of Simonos Petra, *The Synaxarion* (in
   copyright; cite by volume/page) — the preferred checklist source for
   veneration blocks going forward. OrthodoxWiki remains leads-only, never a
   citation.

## Q7 — Map encoding (merge with R2 if not yet executed)

One visual channel, one meaning: fill color = verification status (unchanged);
apostolic-foundation sees get a distinct ring/shape; add highlight toggles
(Pentarchy / apostolic foundations / active today) that dim non-matching
markers; the "today" era preset shows living successions as filled markers.
Legend updated accordingly.

## Q8 — Public polish

1. **State of the database page:** per-jurisdiction verification progress,
   counts, known-gap summary (from gap_report), honest and current on every
   build.
2. **For researchers page:** documented download links for JSON/SQLite exports
   per release, schema overview, citation format.
3. **Report a correction:** GitHub issue templates (error report requires:
   what's wrong / what's correct / your source) + a per-page footer link
   prefilled with the page's entity ID.
4. **OpenGraph/social cards** on entity pages (name, see/epithet, dates).
5. **Accessibility pass:** alt text, contrast, keyboard navigation on
   interactive views, table semantics.
6. **Living-data currency policy** (add to CLAUDE.md): quarterly sweep of
   current primates/open tenures against official announcements; deaths,
   elections, and enthronements enter as normal sourced edits.

## Q-final — Release freeze (was R6; runs LAST)

Only after Q1–Q3 (minimum) are signed off: tag v0.1.0; connect Zenodo; DOI
badge + "How to cite" on README/About (replacing "Database unreleased");
CHANGELOG.md begins; governance docs (NEUTRALITY, NAMING, CONTRIBUTING)
published — their content comes from the maintainer (drafted in chat), never
authored unilaterally. From this point IDs are permanent with no further
migration windows.

## Ordering

Q1 → Q2 → Q3 → (Q4, Q5, Q6, Q7 in any approved order) → Q8 → Q-final.
Rationale: integrity before identity (dedup before ID freeze), identity before
citability (migration before DOI), everything before the freeze.
