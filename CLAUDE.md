# CLAUDE.md — Orthodox Apostolic Succession Database

This repository is a structured, sourced database of Eastern Orthodox apostolic
succession (strictly Chalcedonian), built from YAML data files and compiled to SQLite
and JSON for a public dashboard. The authoritative specification is `KICKOFF.md`.
Read it before making structural changes. These rules bind every session.

## Golden rules

1. **YAML in `data/` is the single source of truth.** SQLite and everything in
   `build/` are disposable, regenerated artifacts. Never hand-edit generated files.
2. **Every substantive claim carries a citation** with a reliability grade
   (`primary | official-list | scholarly | tradition`). Every web source gets an
   `archived_url` (archive.org snapshot). No citation → the record is `unverified`.
3. **Imported data is `unverified`** (Wikidata, scraped lists, OCR). Only a human
   review against a graded source promotes it to `verified`. Never auto-promote.
4. **IDs are permanent.** Never rename a published ID. Format examples:
   `person/cyprus/epiphanios-of-salamis-0367`, `see/cyprus/salamis-constantia`,
   `event/council/ephesus-0431`. Years zero-padded to 4 digits.
   *Clarification (maintainer, 2026-07-10): the dataset is unpublished; ID
   corrections are permitted through the Milestone C reconciliation
   (DATA_COMPLETION §3). The permanence rule locks in at the first public
   release (v0.1.0).*
5. **Two succession models, never conflated:** see-succession (Tenure order) vs.
   consecration-succession (Consecration DAG, principal vs. co-consecrator edges).
   Absent consecration data is stated, not inferred.
6. **Recognition disputes are recorded, not adjudicated** (OCA, OCU, rival
   claimants, Crete 2016). Use per-recognizer `recognition` entries.
7. **One Work, many Editions.** Never create a second Work record for a translation
   or reprint — add an edition under the existing Work.
8. **Scope:** canonical Chalcedonian jurisdictions only. Apostolic claims without
   surviving lineage go in `data/traditions/`. No vagante bodies. Oriental Orthodox,
   Church of the East, and Eastern Catholic are out of scope.
9. **Context events are a thin layer:** hard ceiling 300, one sentence, one link,
   `scope: global` or `scope: jurisdiction:<id>`. They render as a timeline
   background band, never as graph nodes.
10. **Run `python scripts/validate.py` (or `make build`) after every data change**
    and before every commit. Validation failures block commits.

## Conventions quick reference

- **Dates** are objects: `{value, calendar: julian|gregorian|anno-mundi,
  precision: day|month|year|decade|century|circa|disputed, note}`. Watch
  Julian/Gregorian; store Anno Mundi dates converted, with the original in `note`.
- **Names**: monastic + family (disambiguator) + baptismal + native script +
  variants. Transliteration: Greek ALA-LC; Russian/Slavonic simplified BGN/PCGN;
  Georgian national; Arabic ALA-LC.
- **Attribution** on Works: `authentic | disputed | spurious`; store CPG numbers for
  patristic works; PG references as `locator: "PG <vol>:<cols>"`.
- **Participation roles**: presided | signed | attended | legate | condemned |
  deposed-by | posthumously-condemned. Council subscription lists are primary
  evidence — they corroborate person + see + tenure at once.
- Overlapping tenures on one see require a `recognition` qualifier on at least one.
- **Person roles (P1):** `role` absent = bishop (pre-P1 records); explicit on all
  new records. Non-bishop persons are admitted ONLY via a corpus connection — a
  Work (author/subject_of), a Participation, a Relationship, or an
  apostolic-founder/tradition citation (validate.py enforces, error level). No
  general clergy coverage.

## Source hierarchy

Verify against (descending preference): primary documents (council acts, synodal
records) → official diadochal lists → Le Quien / Fedalto / modern scholarship →
tradition (recorded, graded honestly). Wikidata/VIAF are for seeding and
identifiers. OrthodoxWiki/Wikipedia are lead generators only — except the
context-event layer, where Wikipedia links are acceptable.

## Workflow habits

- One commit per source consulted or per coherent record batch; commit messages name
  the source (e.g., `cyprus: tenures 1600–1800 per Fedalto v2, verified`).
- When uncertain about a historical claim, create the record as `unverified` or
  `disputed` with a `note` — never guess silently.
- When transcribing scans (Le Quien, Mansi), always record the page/column locator.
- Prefer editing existing records over creating near-duplicates; run the Work
  duplicate detector when adding bibliography.
