# SITE_REFINEMENT.md — Public Site v2 & Council Catalog (v2)

**Instruction to Claude Code:** `KICKOFF.md`, `CLAUDE.md`, `DATA_COMPLETION.md`,
and `ROADMAP_ADDENDUM.md` bind. Plan Mode discipline: present a plan per
milestone, wait for approval. The site is PUBLIC (GitHub Pages) — the
IDs-are-permanent rule is IN EFFECT; any remaining ID corrections require an
explicit migration plan (old→new mapping + redirects) approved by the
maintainer. All work remains $0: static site, no servers, no paid APIs.

Design principle: the site graduates from "pipeline proof" to "publication" — a
stranger must be able to navigate, find, and learn without instructions.

---

## COMPLETION VERIFICATION PROTOCOL (applies to every milestone in this file)

A milestone is NOT complete when the work is executed; it is complete when
verified. After executing any milestone:

1. **Requirements audit:** re-read the milestone's text line by line. Produce a
   checklist mapping EVERY requirement to evidence: file paths created/changed,
   record counts, script output, or the URL/path of a rendered page
   demonstrating it. Each item is marked `done` (with evidence), `partial`
   (with what remains), or `not-done` (with reason). A bare "done" without
   evidence is prohibited.
2. **Pipeline check:** run the full validation suite and complete build
   (`make build` green); include the summary output in the report.
3. **Rendered verification:** build the site locally and actually open/inspect
   every page type the milestone touched; confirm content renders (not an
   empty JS shell), links resolve, and the specific behaviors required (e.g.,
   map persistence rule, search returns variants) demonstrably work. State
   what was inspected and what was observed.
4. **Honest gap statement:** list anything discovered out of scope, deferred,
   or broken elsewhere by this work.
5. **Present the report to the maintainer and STOP.** The milestone closes only
   on maintainer sign-off; the next milestone's plan may then be proposed.
   Never self-certify and continue.

---

## Milestone R1 — Information architecture, navigation, search, static HTML

1. **Static HTML generation (required):** every page is generated at build time
   with its real content in the HTML — entity data rendered statically;
   JavaScript enhances interactivity but never CREATES the content. Rationale:
   non-JS agents (search crawlers, archive.org, citation tools) currently
   receive an empty shell. Entity pages become real per-entity static files
   with path-based URLs (e.g., `/people/<id>/`), replacing query-parameter
   routing; provide redirects/fallbacks from any already-circulated
   query-parameter URLs.
2. **Page structure** (static, generated from exports):
   - Home: project intro, counts, verification progress, "commemorated today"
     placeholder (activates with ROADMAP_ADDENDUM C2), entry links.
   - Jurisdictions index → jurisdiction page (its sees, primatial timeline).
   - See page: full succession table + per-see timeline + map inset + gaps
     shown honestly (link to gap report).
   - Person page (see R4). Council index + council page (see R5).
   - Persistent header nav on every page: Home · Jurisdictions · Sees · People
     · Councils · Library · Map · Graph · About.
3. **Client-side search**: MiniSearch (or Lunr) over a generated index (people,
   sees, councils, works; includes name variants and native scripts). Search
   box in the header of every page. No server, no external service.
4. **Permalinks & citation**: stable path-based URL per entity; internal links
   use them everywhere; per-page "cite this page" line (URL + dataset
   version).
5. **Export chunking**: replace monolithic JSON with per-jurisdiction chunks +
   a small global index; pages load only what they need.
6. **Responsive pass**: all pages and visualizations usable at 380px width
   (stacked layouts, horizontal-scroll guards on tables, touch targets ≥40px).
7. **schema.org markup** on person/see/council pages (Person, historical role,
   sameAs → Wikidata/VIAF) — enabled by static generation.

## Milestone R2 — Map v2

1. **Persistence rule**: a see renders from its first attested date onward and
   NEVER disappears while it exists. States: filled = tenure active that year
   (color by status); hollow = attested, no recorded occupant that year;
   grayed/crossed = suppressed (with date). Remove any logic that unmounts
   markers year-to-year.
2. **Default viewport**: Mediterranean/Near East bounding box (not the world).
   Zoom/pan retained; "reset view" button.
3. **Era presets**: buttons for 33 · 325 · 451 · 787 · 1054 · 1204 · 1453 ·
   1917 · today, plus the slider and play.
4. **Labels & targets**: permanent labels for the five Pentarchy sees at all
   zooms; other labels on zoom or hover; minimum marker hit area 24px.
5. Click → see page (not just person profile). Legend gains the suppressed
   state.

## Milestone R3 — Timeline v2 & context layer

1. The all-sees mega-timeline becomes an **overview index**: jurisdiction
   accordions (collapsed by default except the Pentarchy), sticky time axis,
   sticky see-name column, and a "jump to see" typeahead. Detail lives on
   per-see pages (R1).
2. **Minimum bar width** (e.g., 3px) with overflow markers so short tenures
   stay visible; tooltip on hover with name/dates/status; click → person page.
3. **Context layer redesign**: replace point-dots with labeled ERA BANDS
   derived from context events with durations (Persecutions, Byzantine, Arab
   conquests, Crusader states, Ottoman, Synodal Russia, Soviet period, …),
   plus discrete event markers with hover labels. Scope-filter the layer to
   the jurisdictions currently expanded. If existing context data lacks
   durations, propose the ~15–25 era-band records (scoped, sourced per the
   context-layer rules) in the plan for approval — they count toward the 300
   ceiling.

## Milestone R4 — Person page completion

Sections, in order (render only when data exists, with honest absence lines as
already established): Identity · Role · Veneration (titles, feasts,
per-recognizer) · Sees held · Consecration · **Works** (grouped by relation:
by / about / involving; per work: title, date, attribution flag with note,
survival badge, editions with read-links and rights) · **Councils** (from
Participation: role badge, date, link to council page) · Relationships (when
present) · Sources.

Data additions in this milestone (unverified until maintainer verifies):
- `work/epistle-of-james` — author: James the Just; attribution: disputed,
  with a note recording both the traditional ascription and modern scholarly
  dispute, each sourced; genre: letter; editions: public-domain text link.
- Audit: every person from DATA_COMPLETION §4 (works backfill) renders their
  works; every person with Participation records renders their councils.

## Milestone R5 — Council catalog (data + pages)

### Schema addition (Event, council types only)
`canonical_reception: received-universally | received-locally |
historical-only | condemned` + `reception_note` (e.g., "canons received via
Quinisext canon 2"). Update schema, validate.py, admin form, KICKOFF.md §4.8.

### Catalog buildout — tiered; exhaustive within each tier before moving on:
1. **Tier 1 — the Ecumenical seven** (audit/complete existing records) + the
   councils Orthodoxy treats with near-ecumenical authority (879–880 Photian;
   1341/1347/1351 hesychast; 1672 Jerusalem/Dositheus; note reception nuances
   honestly in `reception_note`).
2. **Tier 2 — received local councils** (Quinisext canon 2 enumeration):
   Ancyra 314, Neocaesarea, Gangra, Antioch 341, Laodicea, Sardica 343,
   Carthage 419 (and the received African corpus), Constantinople 394 — each
   with date, place, outcomes, sources, and participants where subscription
   lists survive.
3. **Tier 3 — historically significant synods** (historical-only or
   received-locally), incl.: the Synod of the Oak 403 (deposition of John
   Chrysostom), 448/449 Constantinople & Ephesus II (449: condemned), 754
   Hieria (condemned), 861 First-Second, 867, the Comnenian-era synods
   (Italos etc.), 1156–57 and 1166 Constantinople, 1285 Blachernae, 1484,
   Jassy 1642, Moscow 1666–67, Constantinople 1755/56, 1872 (phyletism),
   Moscow 1917–18, Constantinople 1923, Crete 2016 (per-recognizer
   recognition). This list is a FLOOR, not a ceiling: sweep Hefele
   volume-by-volume and propose additions in each plan — the maintainer
   explicitly wants synods he has never heard of surfaced.
4. **Tier 4 — jurisdiction-local synods**, ongoing/opportunistic (backlog
   after Tier 3).

### COUNCIL_LEADS.md capture rule (standing, add to CLAUDE.md): any synod
named in ANY source during ANY work gets logged (name, date-guess, where
encountered); the build reports leads not yet cataloged.

### Sources to seed: Hefele, *History of the Councils of the Church* (public
domain, archive.org); Mansi; Percival, *The Seven Ecumenical Councils* (NPNF
II.14); the *Pedalion/Rudder* (Cummings tr.); Tanner, *Decrees of the
Ecumenical Councils* (in-copyright; WorldCat link). Every web source archived.

### Pages: council index (grouped by tier, filterable by type/scope/century)
and council detail page (dates, place, type, reception tier + note, outcomes,
participant table with roles linking to person pages, related works — e.g.,
Tome of Leo ↔ Chalcedon — and sources).

## Milestone R6 — Public-release housekeeping (now due; site is live)

1. Tag `v0.1.0`; connect Zenodo; DOI badge + "How to cite" in README and site
   About page; CHANGELOG.md begins.
2. Governance docs from placeholders — CONTENT DRAFTED WITH THE MAINTAINER (he
   brings text from chat): docs/NEUTRALITY.md, docs/NAMING.md,
   CONTRIBUTING.md. Link all three from the About page. Do not author these
   unilaterally.
3. About page: project scope, methodology (grading, verification,
   corroboration), the two-succession-models explanation, license, contact
   via GitHub issues.

## Order & boundaries

Recommended order: R1 → R4 → R5 → R2 → R3 → R6 (R6 can run parallel any
time; navigation and static generation first because every other milestone's
output needs somewhere to live). This order may be merged/re-sequenced with
the P-milestones of PERSONS_LIBRARY_CONTROVERSIES.md — propose the merged
ordering, with reasoning, for approval. Standing boundaries from
ROADMAP_ADDENDUM §D unchanged; additionally out of scope here: hosting full
texts of works (link out only) and interactive canon-text readers (link to
sources).
