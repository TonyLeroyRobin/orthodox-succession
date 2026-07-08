# Human verification workflow

Everything imported programmatically (Wikidata, scraped lists, OCR) enters
the database as `status: unverified` and **stays that way until a human
confirms it against a graded source**. Nothing is ever auto-promoted. This
document is the procedure for that confirmation.

## The loop

1. **Pick work from the queue.**

   ```sh
   python scripts/verification_queue.py                      # counts per church
   python scripts/verification_queue.py --jurisdiction serbia --all
   python scripts/verification_queue.py --kind tenure --all  # tenures only
   ```

   The queue shows each record's best citation grade and its gaps
   (`no end date`, `no tenure record`, `seed gaps`, `recognition-flagged`).

2. **Open the source of record.** Verify against, in descending preference:
   primary documents (council acts, synodal records) → the church's official
   diadochal list → Le Quien / Fedalto / modern scholarship → tradition
   (recorded and graded honestly). Wikidata/VIAF are identifiers only and can
   never support promotion.

3. **Correct the record.** Fix names (apply the transliteration standards),
   dates (value + calendar + precision — watch Julian/Gregorian), tenure
   spans, end_reason. When sources disagree, keep the better-graded reading
   in the fields and record the disagreement in `notes` or, if genuinely
   unresolvable, set `status: disputed`.

4. **Cite what you consulted.** Add a `sources` entry with `ref`, a real
   `locator` (page, column, PG vol:col, or URL fragment), the honest
   `reliability` grade, and — for any web source — an `archived_url` pinned
   to an exact archive.org snapshot (replace any year-wildcard
   `web.archive.org/web/2025/...` redirect left by seeding or scaffolding).

5. **Promote.** Set `status: verified` only when at least one citation is
   graded better than `tradition`/`database`. Validation enforces this.

6. **Rename draft IDs if needed — before publication only.** Seeded IDs use
   provisional year suffixes (earliest seeded term, or birth year when no
   term start existed). While the dataset is unpublished these may be
   corrected to the first-tenure year. **Once an ID has been published it is
   permanent** — after publication, corrections go in `names.variants` and
   `notes`, never the ID.

7. **Validate and commit.**

   ```sh
   make build     # or .\build.ps1 — validation must be green
   git commit     # one commit per source consulted or coherent batch,
                  # message names the source, e.g.:
                  # "serbia: tenures 1920-2010 per official SPC list, verified"
   ```

## Known seed gaps (as of the Milestone 2 import)

- Most Wikidata P39 statements carry **no start-date qualifier**, so many
  primates exist as person drafts without tenure records. Fill tenures from
  the official diadochal lists and Fedalto — that is the core Milestone 2
  verification workload.
- The **Czech Lands & Slovakia** primatial line has no usable Wikidata
  office item and was not seeded at all; enter it manually from the church's
  official history.
- Seeded dates are **year precision, calendar guessed** (Julian before 1583)
  — both must be checked.
- Records flagged `recognition-flagged` carry a `disputed` recognition entry
  because their seeded terms overlap another tenure on the same see: decide
  whether it is a rival claim (keep, refine the entry per-recognizer), a
  restoration (split terms correctly), or bad data (fix the dates, drop the
  flag).
- Persons whose Wikidata lifespan contradicted their term dates had
  birth/death **dropped**, noted in the record — restore from a real source.
