# Orthodox Apostolic Succession Database — Project Kickoff Specification

**Instruction to Claude Code:** Read this entire document, then build the repository it
describes. Work through the milestones in order. Ask the user before deviating from any
convention defined here. A `CLAUDE.md` file accompanies this document — place it in the
repository root so every future session inherits these rules.

---

## 1. Project Definition

A structured, sourced, machine-readable database of **Eastern Orthodox apostolic
succession**, strictly **Chalcedonian** in scope, covering the canonical autocephalous
churches and their historical antecedents, tracing episcopal succession back toward the
Apostles.

Two deliverables, in order:

1. **The dataset** — version-controlled, citation-backed, publicly reviewable.
2. **The dashboard** — an interactive public explorer (succession graphs, timelines,
   bishop profiles, readable-works links, click-through citations) generated from the
   dataset and hostable as a static site (e.g., GitHub Pages). The dataset is the
   foundation; the dashboard is the product.

### Scope rules (hard)

- Canonical Chalcedonian Eastern Orthodox jurisdictions only. No vagante or
  independent-lineage bodies.
- Genuinely contested canonical cases (OCA, OCU) are IN scope, handled via
  per-recognizer recognition status — the data records the dispute, it does not
  adjudicate it.
- Apostolic claims without a surviving Chalcedonian lineage (e.g., the St. Thomas /
  Pantaenus traditions in India; the pre-schism British Isles) are recorded as sourced
  **tradition/mission entries**, never as succession chains.
- Oriental Orthodox, Church of the East, Eastern Catholic: out of scope.

### The two succession models (core design decision)

Both are modeled, as separate relationship types, and the UI must distinguish them:

- **Succession of sees** — ordered occupancy of a throne (derived from Tenure records).
  This is what ancient records preserve; it extends to the apostolic era.
- **Succession of consecrations** — who laid hands on whom (Consecration records),
  forming a directed acyclic graph with principal and co-consecrator edge types.
  Reliably documentable mostly from the 15th–17th centuries onward.

Never silently blend the two. Where consecration data is absent, the record says so.

---

## 2. Repository Layout

```
orthodox-succession/
├── CLAUDE.md                  # session conventions (provided)
├── README.md                  # public-facing project description
├── LICENSE-DATA               # CC BY 4.0 for data
├── LICENSE-CODE               # MIT for code
├── data/
│   ├── jurisdictions/         # one file per jurisdiction
│   ├── sees/<jurisdiction>/   # one file per see
│   ├── people/<jurisdiction>/ # one file per person
│   ├── tenures/<jurisdiction>/
│   ├── consecrations/<jurisdiction>/
│   ├── events/
│   │   ├── councils/          # councils & synods (Event with participants)
│   │   └── context/           # curated world-history backdrop (~150–300 max, ever)
│   ├── participations/        # person↔council links
│   ├── works/                 # Work records (with nested editions)
│   ├── traditions/            # apostolic claims without surviving lineage
│   └── sources/               # bibliography: one file per source
├── schemas/                   # JSON Schema for every entity type
├── scripts/
│   ├── validate.py            # full validation suite (see §6)
│   ├── build_db.py            # YAML → SQLite
│   ├── export_graph.py        # SQLite → GraphML + JSON for the dashboard
│   └── import_wikidata.py     # seeding tool (see §7)
├── site/                      # prototype dashboard (Phase 0: crude but functional)
└── build/                     # generated artifacts (gitignored)
```

Principles: YAML files in `data/` are the **single source of truth**. SQLite is
disposable and rebuilt on every change. Everything generated lives in `build/`.

---

## 3. Global Conventions

### IDs
Stable, human-readable, never renamed once published:

```
person/<jurisdiction>/<name>-<start-year>     person/cyprus/epiphanios-of-salamis-0367
see/<jurisdiction>/<place>                    see/cyprus/salamis-constantia
tenure/<person-id-suffix>@<see-suffix>        tenure/cyprus/epiphanios-0367@salamis
consecration/<jurisdiction>/<person>-<year>   consecration/cyprus/epiphanios-0367
jurisdiction/<name>                           jurisdiction/church-of-cyprus
event/council/<place>-<year>                  event/council/ephesus-0431
event/context/<slug>                          event/context/fall-of-constantinople-1453
work/<slug>                                   work/ancoratus
source/<slug>                                 source/le-quien-oriens-christianus-v2
tradition/<slug>                              tradition/thomas-in-india
```

Years are zero-padded to 4 digits. Use `-bce` suffix in the rare BCE case. When the
start year is unknown, use the earliest attested year.

### Dates
Every date is an object, never a bare string:

```yaml
date:
  value: "0431-06-22"        # ISO-8601, as precise as known
  calendar: julian            # julian | gregorian | anno-mundi (store converted value)
  precision: day              # day | month | year | decade | century | circa | disputed
  note: ""                    # free text for disputes/conversions
```

### Names (Person)
```yaml
names:
  monastic: Bartholomew        # the name a bishop is known by
  family: Archontonis          # conventional disambiguator: Bartholomew (Archontonis)
  baptismal: Demetrios         # pre-monastic name, if known
  native: [{script: grc, value: "Βαρθολομαῖος"}]
  variants: ["Bartholomeos", "Vartholomaios"]   # transliterations found in sources
```

Transliteration standards (fixed now, applied always): Greek → ALA-LC romanization;
Church Slavonic / Russian → simplified BGN/PCGN; Georgian → national system; Arabic →
ALA-LC; Romanian native. Native script always stored alongside.

### Sourcing (applies to every entity)
Every substantive claim carries at least one citation:

```yaml
sources:
  - ref: source/le-quien-oriens-christianus-v2
    locator: "col. 1044"
    reliability: scholarly     # primary | official-list | scholarly | tradition
    note: ""
    archived_url: ""           # archive.org snapshot for any web source (mandatory)
```

Reliability grades: **primary** (contemporary document, e.g., council subscription
list), **official-list** (a patriarchate's published diadochal list),
**scholarly** (Le Quien, Fedalto, modern academic work), **tradition**
(hagiography, devotional lists — recorded honestly, graded honestly).

### Verification status
Every record carries: `status: unverified | verified | disputed`. Everything imported
programmatically (Wikidata etc.) enters as `unverified` and stays that way until a
human confirms it against a graded source.

---

## 4. Entity Schemas (nine)

Implement each as a JSON Schema in `schemas/` and enforce in `validate.py`.
Field lists below are the minimum; add `notes: ""` (free text) to every entity.

### 4.1 Person
`id, names{}, born{date?, place?}, died{date?, place?}, attestation
(attested | legendary | uncertain), identifiers{wikidata?, viaf?}, sources[], status`

### 4.2 See
`id, name, jurisdiction_history[{jurisdiction, from, to}], rank_history[{rank:
bishopric|archbishopric|metropolis|patriarchate, from, to}], founded{date?,
founded_from: see-id?}, suppressed{date?}, location{lat?, lon?, modern_place?},
apostolic_founder{person-id?, sources[]}, sources[], status`

### 4.3 Tenure
`id, person, see, from{date}, to{date?}, end_reason (died | translated | resigned |
deposed | schism | unknown), recognition[{by: jurisdiction-id | "all", status:
recognized | disputed | rival-claimant}], sources[], status`

Overlapping tenures on one see are **legal** when at least one carries a
non-universal recognition entry (rival claimants).

### 4.4 Consecration
`id, consecrated: person-id, date{}, place?, principal_consecrator: person-id?,
co_consecrators[person-id], sources[], status`

Principal vs. co-consecrator are distinct edge types in every export.

### 4.5 Jurisdiction
`id, name, type (autocephalous | autonomous | historical), autocephaly[{granted_by,
date, recognition[{by, status, since?}]}], dissolved{date?, successor?}, primatial_see:
see-id, sources[], status`

### 4.6 Source
`id, type (book | article | web | manuscript | database), title, author?, year?,
series?, url?, archived_url?, worldcat?, notes`

### 4.7 Work (+ nested Editions)
`id, title, author: person-id, subject_of[person-id]?  # for works ABOUT a bishop,
relation (by | about | involving), language, date{}, attribution (authentic |
disputed | spurious), cpg?, genre (homily | letter | treatise | canon | encyclical |
liturgical | hagiography | biography | acts | study), editions[{type: original |
translation, language, translator?, series?, year?, locator?  # e.g. "PG 48:623–692",
url?, rights: public-domain | in-copyright}], sources[], status`

Key rule: **one Work, many Editions** — never duplicate a work per translation.

### 4.8 Event
`id, type (council-ecumenical | council-local | synod | context), title, date{from,
to?}, place?, scope (global | jurisdiction:<id>)  # context events only,
outcomes[]?, affected[see-id | jurisdiction-id]?, recognition[{by, status}]?  # e.g.
Crete 2016, sources[], status`

Context events: curated, ~150–300 total ceiling, one-sentence description, one source
link (Wikipedia acceptable for this layer only). Rendered as background band, never
as graph nodes.

### 4.9 Participation
`id, person, event, role (presided | signed | attended | legate | condemned |
deposed-by | posthumously-condemned), sources[], status`

Council subscription lists are primary evidence: a `signed` participation with a
primary source simultaneously supports the person, the see, and the tenure date —
`validate.py` should surface these corroborations.

### 4.10 Tradition (auxiliary, for out-of-lineage apostolic claims)
`id, title, claim, region, persons[person-id], sources[], status` — e.g., Pantaenus'
mission to "India" (Eusebius HE 5.10), the Thomas tradition. Explicitly marked as
non-succession data.

---

## 5. Build Pipeline

```
data/*.yaml → validate.py → build_db.py → build/succession.sqlite
                                        → export_graph.py → build/graph.graphml
                                                          → build/site-data/*.json
                                                          → site/ (reads the JSON)
```

- Python 3.11+, `ruamel.yaml` or `pyyaml`, `jsonschema`, stdlib `sqlite3`.
- A single `make build` (or `./build.sh`) runs the whole chain.
- CI-friendly: validation must exit non-zero on any error so GitHub Actions can gate
  pull requests — this is the public review mechanism.

---

## 6. Validation Rules (minimum set for `validate.py`)

1. Every file parses; every record matches its JSON Schema; every ID is unique and
   matches its path.
2. Referential integrity: every `person`, `see`, `event`, `source` reference resolves.
3. Chronology: death ≥ birth; tenure within person's lifespan (± precision slack);
   tenure within the see's existence window; consecration before first tenure and
   within lifespan; participation date within person's lifespan.
4. Consecration sanity: no self-consecration; consecrators must be plausibly alive at
   the date; DAG check — no cycles in the consecration graph.
5. Tenure overlap on one see ⇒ at least one overlapping tenure must carry a
   `recognition` qualifier; otherwise error.
6. Sources: every record has ≥1 source ref; every web source has `archived_url`;
   every `verified` record has ≥1 source with reliability better than `tradition`
   (tradition-only records must remain `unverified` or be flagged).
7. Works: no two Works by the same author with near-identical titles (duplicate
   detector, warn-level); every edition with `rights: public-domain` should have a URL.
8. Context events: hard count ceiling (300) — error if exceeded.
9. Report corroborations (info-level): tenures supported by council signatures.

---

## 7. Wikidata Import Tool (`import_wikidata.py`)

- Input: a jurisdiction or a list of Wikidata QIDs.
- Uses SPARQL (endpoint: query.wikidata.org) to pull: bishops (P39 position held /
  P1435 etc.), dates, consecrator (P1598) where present, VIAF (P214), works (P800 /
  authored-by inverse).
- Emits draft YAML files with `status: unverified` and a source entry pointing at the
  Wikidata item (reliability: `scholarly` is NOT allowed for these — use a dedicated
  `database` source graded per claim after human review).
- Never overwrites an existing verified record. Idempotent re-runs.

---

## 8. Primary Reference Sources (seed the bibliography with these)

| Source | Use |
|---|---|
| Le Quien, *Oriens Christianus* (1740, 3 vols., public domain, archive.org) | Episcopal lists for every Eastern see |
| Fedalto, *Hierarchia Ecclesiastica Orientalis* | Modern scholarly successor to Le Quien |
| Official patriarchal diadochal lists (each church's site; archive every URL) | Official succession claims |
| Eusebius, *Ecclesiastical History* | Earliest see traditions (grade: tradition/scholarly per claim) |
| Mansi, *Sacrorum Conciliorum Collectio*; ACO; Translated Texts for Historians | Council acts & subscription lists |
| Stroev's lists; Russian synodal records | Russian consecration-level data |
| Migne, *Patrologia Graeca* (PG vol:col citation system) | Original texts of works |
| ANF/NPNF via CCEL / newadvent.org | Public-domain English translations |
| Clavis Patrum Graecorum (CPG numbers) | Work identification & attribution |
| Wikidata / VIAF | Seeding & identifiers only — never final citation |
| OrthodoxWiki / Wikipedia | Lead generation only — never final citation (exception: context-event layer) |

---

## 9. Milestones

### Milestone 0 — Scaffold (first session)
Repo initialized; layout above; CLAUDE.md in root; all nine JSON Schemas;
`validate.py`, `build_db.py`, `export_graph.py` skeletons passing on empty data;
licenses; README.

### Milestone 1 — Cyprus Pilot
The Church of Cyprus end-to-end (autocephalous since Ephesus 431 — which is itself
the first council record):

- `jurisdiction/church-of-cyprus`; principal sees (Salamis-Constantia/Nea Justiniana,
  later Nicosia line); the full archiepiscopal succession list from the official list
  + Le Quien + Fedalto, entered as Tenures with graded sources.
- Key persons fleshed out: Barnabas (apostolic founder — attestation per sources),
  Epiphanios of Salamis (incl. Works: *Panarion*, *Ancoratus*, with PG references and
  CCEL/archive.org edition links), and the modern archbishops with consecration data.
- `event/council/ephesus-0431` with the Cypriot autocephaly outcome; participations.
- A handful of context events scoped `jurisdiction:church-of-cyprus` (Arab raids,
  Latin rule 1191–1571, Ottoman period, 1974) + a starter `global` set.
- **Prototype page**: `site/` renders, from the exported JSON, at least (a) the Cyprus
  succession timeline with the context band and (b) one bishop profile page with
  citations and a works list. Crude is fine; the pipeline must flow end-to-end.

Acceptance: `make build` green; validation reports ≥1 council-signature corroboration;
prototype loads locally.

### Milestone 2 — Primatial Spines
Diadochal lists of all autocephalous churches (Constantinople, Alexandria, Antioch,
Jerusalem, Moscow, Serbia, Romania, Bulgaria, Georgia, Cyprus ✓, Greece, Poland,
Albania, Czech Lands & Slovakia; OCA and OCU with recognition disputes modeled).
~1,500–2,000 tenures. Wikidata seeding + human verification workflow proven.

### Milestone 3 — Branching & Councils
Major historical metropolises (Kyiv, Ohrid, Thessalonica, …), mother-church founding
links, the major councils (7 ecumenical + key local: 867/879, 1341–51, 1666–67, 1872,
2016) with participation lists from subscription records, full context-event layer.

### Milestone 4 — Open-ended fill-in
Suffragan sees, consecration-level depth (15th c. onward), bibliography expansion,
dashboard polish (D3.js/vis.js interactive graph; "primary writings survive" node
highlighting; recognition-dispute rendering).

---

## 10. Non-negotiables (summary for every session)

1. YAML in `data/` is the only source of truth; SQLite/exports are disposable.
2. Every claim cited; every citation graded; every web source archived.
3. Imported = `unverified` until a human verifies.
4. IDs never change once published.
5. See-succession and consecration-succession are never conflated.
6. Recognition disputes are recorded, not adjudicated.
7. One Work, many Editions.
8. Chalcedonian canonical scope only; traditions folder for everything else.
