# Neutrality

*Drafted with the maintainer, 2026-07-15 (ROADMAP_ADDENDUM §B2). Binding on
every record and on the dashboard.*

## The principle

**This database records recognition claims as made by each church, with
sources; it adjudicates nothing.** (Golden rule 6.) Where churches disagree —
about an autocephaly, a claimant to a see, a glorification, a historical act —
the dataset carries each position, attributed to the church that holds it,
with a citation. The database has no position of its own.

## What this means in the data

- **Per-recognizer `recognition` entries**, never a single verdict. A tenure
  or jurisdiction that is recognized by some churches and not others lists
  each recognizer's status (`recognized | disputed | rival-claimant |
  not-recognized`), with `since` dates and notes where known.
- **`status: disputed`** marks records whose substance the sources themselves
  contest. Both (or all) witnesses are cited in the record.
- **Symmetry.** Rival claims are modeled from both sides with the same care.
- **Silence is never used to adjudicate.** Where naming a successor or
  picking a list would take a side, the field is left empty and the note says
  why.

## Worked examples (all live in the dataset)

- **The Kyiv see (OCU / UOC-MP):** two overlapping tenures — Epiphanius
  (recognized by the Ecumenical Patriarchate, Alexandria, Greece, Cyprus; not
  recognized by Moscow) and Onufriy (recognized by Moscow; not recognized by
  the EP since 2019) — each carrying the mirror-image recognition entries.
- **The 1686 Kyiv letter:** `jurisdiction/metropolitanate-of-kyiv` leaves its
  `dissolved.successor` empty, because naming either Moscow or the OCU would
  adjudicate the 2018 dispute; the note records both successor claims.
- **The OCA autocephaly:** recognized by five churches, not recognized by the
  EP — six recognition entries on the jurisdiction record; the Metropolia-era
  estrangement is carried on the affected tenures with
  reconciled-by-the-1970-tomos notes.
- **The Roman antipopes** and the **vicar-administrators on the OCA list**:
  overlapping tenures with `rival-claimant` or `disputed` qualifiers whose
  notes say exactly what kind of overlap the source records.
- **Diverging successions** (the Georgian Germene ↔ Nikoloz VI span, the
  Bulgarian ordinal quirks, the Romanian Grigorie III interposition): both
  witnesses recorded, keep-both wherever the lists genuinely disagree.
- **Condemnations and veneration:** conciliar condemnations live in
  Participation records (`condemned`, `posthumously-condemned`);
  veneration is per-recognizer (`universal` vs `jurisdiction:<id>`).

## Wording policy

- Attribute every claim to its maker: *"Moscow declared…"*, *"per the
  official EP list…"*, *"the standard chronology gives…"* — never the bare
  assertion where the fact is contested.
- Descriptive verbs, no evaluative adjectives. A deposition is *recorded*
  (`end_reason: deposed`, with who deposed and by what act), not endorsed or
  deplored. Politically sensitive events get the same treatment as ancient
  ones.
- The phrase **"recorded, not adjudicated"** in a note is the standing marker
  that a divergence was seen and deliberately left open.

## Dashboard rendering (maintainer decision, 2026-07-15)

Disputed records display a neutral **"recognition varies" badge**; expanding
it lists each recognizer's position with its sources, in a fixed neutral
order (no default viewpoint). A per-recognizer *"view as reckoned by X"*
toggle is deferred to the dashboard phase as an enhancement (see BACKLOG).

## What neutrality is not

Neutrality applies to *recognition and interpretation*, not to attested
fact. The database does not both-sides a documented date, and it does not
inflate weak evidence: tradition-grade claims are labeled `tradition` and can
never silently masquerade as scholarship. Honest grading **is** the
neutrality policy applied to evidence.
