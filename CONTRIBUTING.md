# Contributing

*Drafted with the maintainer, 2026-07-15 (ROADMAP_ADDENDUM §B2).*

Corrections and additions are welcome — as **pull requests with graded
sources**. There is no other contribution channel (no accounts, no comment
system; standing boundary, ROADMAP_ADDENDUM §D).

## The workflow

1. Edit the YAML under `data/` — it is the single source of truth. Never
   touch `build/` (generated, disposable).
2. Run `python scripts/validate.py` (or `make build`). **Validation must
   exit 0; failures block merges.**
3. One commit per source consulted or per coherent record batch; the commit
   message names the source (e.g. `cyprus: tenures 1600–1800 per Fedalto v2`).
4. Open a PR. Expect review to be about sourcing, not opinion.

## Sourcing requirements

- Every substantive claim carries a citation graded
  `primary | official-list | scholarly | tradition`. The `database` grade is
  reserved for programmatic imports and never counts toward verification.
- **Grade honestly.** A synaxarion is `tradition` even when you believe it;
  honest grading is the neutrality policy applied to evidence
  ([docs/NEUTRALITY.md](docs/NEUTRALITY.md)).
- Every web source carries an `archived_url` (archive.org snapshot — exact
  timestamps preferred; request a Save Page Now capture for unarchived
  pages).
- Transcriptions from scans (Le Quien, Mansi, Fedalto) record the
  page/column locator.

## Disputes

**Disputes are resolved by sourcing, not argument.** If reputable lists
disagree, the record carries both witnesses — `status: disputed`,
per-recognizer `recognition` entries, and a note saying "recorded, not
adjudicated." A PR that picks a winner between churches will be asked to
model both positions instead. See [docs/NEUTRALITY.md](docs/NEUTRALITY.md)
and [docs/NAMING.md](docs/NAMING.md).

## Statuses and verification (maintainer decision, 2026-07-15)

- Every new or imported record enters `status: unverified`.
- **Only the maintainer promotes a record to `verified`**, through the
  verification queue, after reviewing it against a graded non-tradition
  source. Contributors never set `verified` themselves — instead, attach
  your evidence (source, locator, pinned snapshot) in the PR so the record
  is ready for review. Bulk verification does not happen, by anyone.
- `disputed` is not a downgrade; it is the correct status for a record whose
  sources genuinely disagree.

## Hard rules (will fail review)

- **IDs are permanent** (from v0.1.0). Never rename a published ID; new IDs
  follow the documented format with years zero-padded to 4 digits.
- **Scope:** canonical Chalcedonian jurisdictions only; no vagante bodies;
  nothing below the episcopate; apostolic claims without surviving lineage go
  to `data/traditions/`.
- **Two succession models, never conflated**; absent consecration data is
  stated, not inferred.
- **One Work, many Editions** — never a second Work for a translation.
- **No AI-generated biographical prose** anywhere in data or site
  (ROADMAP_ADDENDUM §D). Records contain sourced facts, dates, and notes.
- Context events: hard ceiling 300, one sentence, one link, scoped.

## Conventions quick reference

Dates are objects (`{value, calendar, precision, note}`); watch
Julian/Gregorian. Names follow [docs/NAMING.md](docs/NAMING.md) — no
honorific prefixes, variants for everything. The full working conventions
live in [CLAUDE.md](CLAUDE.md) and the authoritative spec in
[KICKOFF.md](KICKOFF.md).

## Licensing

By contributing you agree your contributions are released under the
project licenses: data under CC BY 4.0, code under MIT. No CLA beyond this.
