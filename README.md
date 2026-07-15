# Orthodox Apostolic Succession Database

A structured, sourced, machine-readable database of **Eastern Orthodox apostolic
succession** — strictly Chalcedonian in scope — covering the canonical
autocephalous churches and their historical antecedents, tracing episcopal
succession back toward the Apostles.

Two deliverables:

1. **The dataset** — version-controlled YAML in `data/`, citation-backed,
   publicly reviewable via pull requests gated by automated validation.
2. **The dashboard** — an interactive public explorer (succession timelines,
   consecration graphs, bishop profiles, readable-works links, click-through
   citations) generated from the dataset and hostable as a static site.

## The two succession models

Both are modeled, as **separate** relationship types, and the UI distinguishes
them:

- **Succession of sees** — ordered occupancy of a throne (Tenure records).
  This is what ancient records preserve; it extends to the apostolic era.
- **Succession of consecrations** — who laid hands on whom (Consecration
  records), a directed acyclic graph with *principal* and *co-consecrator*
  edge types. Reliably documentable mostly from the 15th–17th centuries onward.

The two are never silently blended. Where consecration data is absent, the
record says so.

## Scope

- Canonical Chalcedonian Eastern Orthodox jurisdictions only.
- Genuinely contested canonical cases (OCA, OCU) are in scope, handled via
  per-recognizer recognition status — the data records disputes, it does not
  adjudicate them.
- Apostolic claims without a surviving Chalcedonian lineage (e.g. the Thomas
  tradition in India) live in `data/traditions/` as sourced tradition entries,
  never as succession chains.
- Oriental Orthodox, Church of the East, and Eastern Catholic churches are out
  of scope.

## Repository layout

```
data/               YAML — the single source of truth
  jurisdictions/    one file per jurisdiction
  sees/<jur>/       one file per see
  people/<jur>/     one file per person
  tenures/<jur>/    occupancy of sees
  consecrations/<jur>/
  events/councils/  councils & synods
  events/context/   curated world-history backdrop (hard ceiling: 300)
  participations/   person ↔ council links
  works/            works by/about bishops (one Work, many Editions)
  traditions/       apostolic claims without surviving lineage
  relationships/    person↔person links (tonsured, spiritual-father, teacher)
  sources/          bibliography, one file per source
schemas/            JSON Schema for every entity type
scripts/            validate / build / export / import tooling
site/               prototype dashboard (static, reads build/site-data/)
build/              generated artifacts — disposable, gitignored
```

## Build pipeline

```
data/*.yaml → validate.py → build_db.py → build/succession.sqlite
                                        → export_graph.py → build/graph.graphml
                                                          → build/site-data/*.json
```

Requirements: Python 3.11+, `pyyaml`, `jsonschema`.

```sh
pip install pyyaml jsonschema
make build          # or: ./build.sh   or (Windows): .\build.ps1
```

To view the prototype dashboard locally (the site fetches JSON, so it needs an
HTTP server):

```sh
python -m http.server 8000
# then open http://localhost:8000/site/
```

## Data conventions (summary)

- **IDs are permanent** and human-readable, e.g.
  `person/cyprus/epiphanios-of-salamis-0367`, `see/cyprus/salamis-constantia`,
  `event/council/ephesus-0431`. Years zero-padded to 4 digits.
  Participation IDs use `participation/<event-suffix>--<person-suffix>`.
- **Dates are objects** — `{value, calendar, precision, note}` — never bare
  strings. Calendar is `julian | gregorian | anno-mundi` (Anno Mundi stored
  converted, original in `note`).
- **Every substantive claim carries a citation** graded
  `primary | official-list | scholarly | tradition`; every web source carries
  an `archived_url` (archive.org snapshot).
- **Every record carries** `status: unverified | verified | disputed`.
  Programmatic imports (Wikidata etc.) enter as `unverified` and stay that way
  until a human confirms them against a graded source.
- **Recognition disputes are recorded, not adjudicated**, via per-recognizer
  `recognition` entries.

See [`CLAUDE.md`](CLAUDE.md) for the full working conventions and
[`KICKOFF.md`](KICKOFF.md) for the authoritative project specification.
Governance: [`docs/NEUTRALITY.md`](docs/NEUTRALITY.md),
[`docs/NAMING.md`](docs/NAMING.md), [`CONTRIBUTING.md`](CONTRIBUTING.md)
(placeholders pending maintainer drafting). Change history:
[`CHANGELOG.md`](CHANGELOG.md).

## Releases & how to cite

<!-- DOI badge — replace the placeholder once Zenodo mints the concept DOI
     after the first GitHub release:
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
-->

Releases follow semver: **data additions increment the minor version,
corrections the patch** (ROADMAP_ADDENDUM §B1). Each GitHub release ships the
repository plus the built artifacts (`build/succession.sqlite`,
`build/graph.graphml`, `build/site-data/*.json`) and is archived on Zenodo
with a DOI. **IDs are permanent from v0.1.0 onward.**

To cite the dataset (fill in the DOI after the first release):

> Robinson, L. (2026). *Orthodox Apostolic Succession Database* (v0.1.0)
> [Data set]. Zenodo. https://doi.org/10.5281/zenodo.XXXXXXX

## Contributing

All changes go through pull requests. `python scripts/validate.py` must pass
(exit 0) — validation failures block merges. One commit per source consulted
or per coherent record batch; commit messages name the source. See
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licenses

- **Data** (`data/`): [CC BY 4.0](LICENSE-DATA)
- **Code** (`scripts/`, `site/`, `schemas/`): [MIT](LICENSE-CODE)
