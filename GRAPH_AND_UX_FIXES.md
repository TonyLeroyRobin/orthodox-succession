# GRAPH_AND_UX_FIXES.md — Graph v2, Ideas Unfreeze, Formation Layer, Findability

**Instruction to Claude Code:** All prior specs and CLAUDE.md bind. Plan Mode:
plan → maintainer approval → execute, one milestone at a time. Completion
Verification Protocol (as in REMEDIATION_AND_POLISH.md) applies to every
milestone — evidence-mapped checklist, full build, LOCAL RENDERED INSPECTION
IN A BROWSER (these are interaction bugs; curl is not verification), coverage
statements, honest gaps, report-and-STOP. IDs permanent; $0; static.

## F1 — Ideas page unfreeze (quick; run first)

1. Debug in a real browser with the console open: identify the JS error or
   event-capture fault. Known symptoms: no click-through on nodes, page
   scroll blocked (canvas swallowing wheel events).
2. Fixes required: d3.zoom (or equivalent) scoped to the SVG only; page
   scrolls normally outside it; wheel-zoom inside the canvas must not prevent
   page scroll when the pointer is outside; node click → person page, edge
   click → work page, per the page's own legend; touch support (pinch-zoom,
   tap) for mobile.
3. **Static fallback content** (R1 rule applies to graph pages): below the
   canvas, a plain HTML table of all edges — from-person, work (with
   locator), to-person, tier badge — rendered at build time. The page must be
   fully informative with JavaScript disabled.
4. Verification: demonstrate scroll, zoom, node click, edge click, and the
   noscript table in the report.

## F2 — Consecration Graph v2 (retire the fossil)

The current /site/graph.html is the pre-R1 prototype: no site chrome, no
static content, embedded data predating the Q2 ID migration (cause of the
Bartholomew (Archontonis) 404 and any sibling 404s).

1. New page `/graph/` in the standard architecture (nav, footer, cite line,
   correction link, OpenGraph), generated from CURRENT build data with
   current path-based person URLs.
2. **Layout:** time-layered DAG (consecration date flows top→bottom; dagre-
   style layering), not force scatter. Jurisdiction encoded by color (existing
   status encoding moves to node ring/border so channels don't collide —
   one channel, one meaning). Principal vs co-consecrator edge styles
   unchanged.
3. **Lineage trace mode (signature feature):** clicking a node highlights its
   full consecration ancestry and descendants (the chain toward the Apostles
   and forward), dimming the rest; a breadcrumb panel lists the highlighted
   chain in order with dates; "clear trace" resets. Shareable: `?trace=<id>`
   pre-activates a trace (progressive enhancement over the static page).
4. Search/focus typeahead (reuse the search index); node labels use the
   display-name formula; legend updated.
5. **Static fallback:** build-time HTML summary below the canvas — counts,
   largest lineage components, and a table of consecration records (person,
   date, principal, co-consecrators) or per-jurisdiction chunked tables if
   size demands.
6. Redirect stub: /site/graph.html → /graph/. Header nav updated.

## F3 — Legacy sweep + internal-link gate

1. Audit everything remaining under /site/*: migrate to the standard
   architecture or replace with redirect stubs. Nothing links to /site/*
   afterward.
2. **Internal-link checker in the build (error level):** every internal href
   in generated output must resolve to a built page or a redirect stub; the
   build fails otherwise. 404s become unshippable.
3. Re-run the full crawl after F2; report zero internal 404s.

## F4 — People index UX (apply same pattern to Library and Saints indexes)

1. Sticky A–Z jump rail + letter section headers (alphabetized by display
   name).
2. Sticky filter bar: role, jurisdiction, century, verification status, and
   (People) a saint toggle; live result count; filters combine with the rail.
3. "Back to top" control; graceful behavior at 380px width.
4. No pagination unless render performance demands it; if introduced, it must
   not break the static-content rule (all entries present in HTML).

## F5 — Library findability (WorldCat demoted)

WorldCat rate-limits/bans repeated referred lookups — it is no longer a
primary affordance.

1. Edition rendering: ISBN shown as PLAIN COPYABLE TEXT with a copy-to-
   clipboard button (progressive enhancement; the text itself is always
   selectable).
2. Primary "find this book" link: Open Library (`openlibrary.org/isbn/<isbn>`)
   — open, no hostile rate limits. Optional secondary: Google Books. WorldCat
   becomes an unlinked mention at most.
3. Pre-ISBN works: show OCLC as copyable text where known, else the plain
   citation; never a dead affordance (Q3 rule).
4. Apply across all edition renderings (library, work pages, person Further
   Reading).
5. Data continuation: propose the next works batch (remaining P3/P4 tier
   sweeps + gated secondary-literature candidates by name) in the plan.

## F6 — Formation layer: Tier 2 institutions, associations backfill, graph

1. **Tier 2 institution candidates** (connection-rule admissions; enumerate
   final list with connecting person named, for approval; floor): Rila (John
   of Rila); Studenica and Žiča (Sava of Serbia; Hilandar already present);
   Neamț (Paisius Velichkovsky — Philokalia thread); Sakkoudion (Theodore the
   Studite); Jerome's monastery at Bethlehem; Annesi/Annisa (Macrina's
   community — sourced to the Life of Macrina); Sarov (Seraphim, if/when he
   enters scope); Kirillo-Belozersky and Ferapontov (the Sergius network, see
   3); the Sinai dependencies only if needed. Each person named must already
   pass the admission rule or enter with this batch via it.
2. **Associations backfill** for persons already in the database (floor;
   enumerate in plan): John of Damascus ↔ Mar Saba; Theodore the Studite ↔
   Sakkoudion + the Studion (hegumen); Pantaenus, Clement, Origen ↔ the
   Catechetical School (teacher/student per sources); John Chrysostom and
   Theodoret ↔ the School of Antioch; Gregory Palamas ↔ Athos (house(s) per
   sources); Nicodemus the Hagiorite ↔ Athos (house per sources); Sergius ↔
   Trinity Lavra; Peter Mohyla ↔ Kyiv-Mohyla Academy + Kyiv Caves Lavra;
   Sava ↔ Hilandar. Every association sourced; in-scope persons only (I3).
3. **`founded_from: institution-id`** added to the Institution schema
   (documented daughter-house foundations only — validator requires a
   source). Showcase: the Sergius network — Trinity Lavra's documented
   daughter foundations across the Russian North (enumerate the documented
   subset in the plan; no speculative edges).
4. **Formation graph page** `/formation/`: bipartite network — persons
   (circles) ↔ institutions (squares), edges by association role;
   founded_from edges between institutions rendered distinctly; time filter;
   static fallback table (person, role, institution, dates). Same interaction
   standards as F1. Institution pages gain a "Formed here" section
   (associations rendered); person pages already carry the Formation line.
5. Optional analytics (info-level build report): persons-formed-per-
   institution-per-century histogram; surface later on the State page if the
   maintainer approves.

## Ordering

F1 (unfreeze, quick) → F2 (Graph v2) → F3 (sweep + link gate) → F4 (index UX)
→ F5 (findability) → F6 (formation layer, data-heavy). Rationale: restore
broken things before improving working things; gate against regressions
before adding pages; data expansion last so new records land on sound
rendering.
