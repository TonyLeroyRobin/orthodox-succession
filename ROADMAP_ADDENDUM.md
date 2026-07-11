# ROADMAP_ADDENDUM.md — Agreed Extensions, Triggers, and Boundaries

**Instruction to Claude Code:** This document extends `KICKOFF.md` and
`DATA_COMPLETION.md`; their rules bind. Same behavior contract: Plan Mode, plan →
approval → execute, nothing auto-verified. Items are grouped by WHEN they activate.
Do not build "later" items early.

---

## A. NOW — fold into the current DATA_COMPLETION milestones

### A1. Generic Relationship entity (schema only; populate opportunistically)
New entity `relationship/` alongside the existing nine:

```yaml
id: relationship/<slug>
from: person-id
to: person-id
type: tonsured | spiritual-father | teacher | consecrated   # extensible enum
      # NOTE: 'consecrated' relationships remain in Consecration records —
      # this enum value is RESERVED for exports only; validate.py must reject
      # relationship records of type 'consecrated' to prevent forked truth.
date: {}?
sources: []
status: unverified | verified | disputed
notes: ""
```

- JSON Schema, validate.py (referential + chronology + the 'consecrated' rejection
  rule), admin form with the reference picker, included in graph exports as
  distinct edge types.
- Populate ONLY when encountered during verification work — no dedicated
  collection pass yet. (Future analytics: lineage-convergence studies — the
  Orthodox "Rebiba question" — and teacher–student network. Backlog, not now.)

### A2. Location discipline
- During all reconciliation/verification work (DATA_COMPLETION §3), fill
  `see.location` (lat/lon + modern_place) whenever a see is touched.
- Add to gap_report.py: count of sees missing location.

### A3. Internationalization groundwork (strings only, no translations yet)
- All user-facing strings in `site/` (and future dashboard work) live in a single
  locale file (e.g., `site/locales/en.json`); code references keys, never
  hard-coded English. Data values (names, titles) are NOT translated — they
  already carry native scripts and variants in the data model.
- Zero translation work now. This is purely to avoid a rewrite later.

### A4. BACKLOG.md
- Create `BACKLOG.md` in the repo root: a one-line-per-idea capture file with
  columns: idea, date, phase-candidate. Seed it with the "later/horizon" items
  below plus: corroboration tier (two independent sources → badge),
  link-rot checker (periodic archived_url validation), Wikidata give-back,
  multilingual UI translations, lineage-convergence analytics.
- Rule for all future sessions: new ideas encountered mid-task go into BACKLOG.md,
  not into the current milestone.

## B. TRIGGER: when DATA_COMPLETION Milestone C (Eastern gap closure) is complete

### B1. Versioned releases + Zenodo DOI
- Tag `v0.1.0` (semver; data releases increment minor, corrections patch).
- Release artifact: the repo + built SQLite + JSON exports, via GitHub Releases.
- Connect the GitHub repo to Zenodo (free, zenodo.org) so each release is
  archived and receives a DOI; add DOI badge + "How to cite" section to README.
- Add `CHANGELOG.md` (kept from now on, one line per merged change batch).

### B2. Governance & neutrality documents (DRAFTED WITH THE MAINTAINER IN CHAT,
not generated unilaterally — create placeholders only):
- `docs/NEUTRALITY.md` — the database records recognition claims as made by each
  church, with sources; it adjudicates nothing. (Placeholder + TODO.)
- `docs/NAMING.md` — historical names in historical contexts, modern official
  names for modern entities, all variants stored and searchable. (Placeholder.)
- `CONTRIBUTING.md` — corrections come as pull requests with graded sources;
  disputes are resolved by sourcing, not argument; validation gates merges.
  (Placeholder.)

## C. TRIGGER: dashboard phase (public site build-out)

- **C1. Map view:** sees as points from `location`, time slider (33 AD → today),
  color by succession/verification state; jurisdictional coverage visible over
  time. D3 or MapLibre (free/open source only; no paid map APIs).
- **C2. Liturgical calendar front page:** "Commemorated today" generated from
  `veneration.feast_days` — person, feast, tenure summary, links to succession
  and works. Support Julian/Gregorian display toggle (data already carries
  calendar per feast entry).
- **C3. schema.org structured-data markup** on person/see pages (Person,
  historical role, sameAs → Wikidata/VIAF).
- **C4. Corroboration badges** (promote from backlog if maintainer approves):
  records with ≥2 independent non-tradition sources get a distinct visual tier.

## D. Standing boundaries (rejected — do not build, do not propose)

- No user accounts, comments, or submissions outside GitHub PRs.
- No real-time features.
- No expansion below the episcopate (no priests/deacons).
- No AI-generated biographical prose anywhere in data or site. Profile pages show
  sourced facts and link to sources/works only.
- No paid services of any kind. The entire stack remains $0 (optional custom
  domain is a maintainer decision, not a default).

## E. Cost ledger (for the record)
GitHub (public repo, Pages hosting, Actions CI): free. Zenodo DOIs: free
(CERN/EU-funded). archive.org snapshots: free. Full software stack (Python,
FastAPI, React, SQLite, D3/MapLibre): open source. Total required budget: $0.
