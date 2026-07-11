# ADMIN_DASHBOARD.md — placeholder

**Status: NOT YET BUILT. Full specification pending from the maintainer** —
this file is a stub created during DATA_COMPLETION Milestone A so that
requirements discovered before the spec lands are not lost. Replace this
stub with the real specification; keep the requirements below.

## Requirements captured so far

1. **Veneration forms** (DATA_COMPLETION §1): the person editor must cover
   the `veneration` block — status, titles, per-recognizer recognition with
   optional glorification dates, feast days (Julian/Gregorian), and its own
   sources (≥1 required whenever the block is present).
2. **Relationship forms** (ROADMAP_ADDENDUM §A1): create/edit `relationship/`
   records with the reference picker for `from`/`to` persons; the form must
   not offer `type: consecrated` (reserved — Consecration records are the
   single source of truth; validate.py rejects it).
3. **Home page** (DATA_COMPLETION §5): surface `scripts/gap_report.py`
   output.
4. **Verification queue** (DATA_COMPLETION §5): filters by see and by import
   batch — already available in the CLI (`scripts/verification_queue.py
   --see … --batch …`); the dashboard should expose the same.

## Boundaries already decided (ROADMAP_ADDENDUM §D)

Local, single-user, no hosting/auth/multi-user; no paid services.
