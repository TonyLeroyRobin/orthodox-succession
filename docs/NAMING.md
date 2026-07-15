# Naming

*Drafted with the maintainer, 2026-07-15 (ROADMAP_ADDENDUM §B2). Binding on
every record and on the dashboard.*

## The principle

**Historical names in historical contexts, modern official names for modern
entities, all variants stored and searchable.** Nobody should fail to find a
record because they know a person or place under a different form.

## Persons

- **Display name = monastic name** (the name the bishop is known by), with
  the conventional family/origin disambiguator in `names.family` (e.g.
  *Bartholomew (Archontonis)*, *Evdemoz I (Diasamidze)*).
- **No honorific or office prefix** in any name field — "Patriarch",
  "Metropolitan", "Kryepiskop" etc. are expressed by the Tenure, never the
  name (DATA_COMPLETION §3 hygiene rule, applied dataset-wide).
- **Native scripts** in `names.native` (script-tagged); **every
  transliteration or historical form encountered in a source** goes into
  `names.variants`.
- **One person, one record**, even across jurisdictions: Meletios Metaxakis
  is a single record with three primatial thrones; Niphon II carries both
  Constantinople and Ungro-Wallachia; Tikhon of Moscow carries his American
  archdiocese. Cross-jurisdiction duplicates are merged, not annotated apart.

## Sees and toponyms (maintainer decision, 2026-07-15)

**Sees display their ecclesiastical names at all periods.** The see of
Constantinople is *Constantinople* in 2026 as in 381; the metropolitan see of
Kyiv is *Kyiv* (modern official romanization) across its history, with *Kiev*
and other romanizations as searchable variants. The modern civil place —
whatever its current official name — lives in `location.modern_place`
(e.g. "ruins of Salamis, near Famagusta"; "Istanbul, Türkiye" when that
field is populated for Constantinople). Civil renamings are variants, not
display names. Politically contested toponyms follow the same rule: the
ecclesiastical name displays, every claimant spelling is searchable, and the
notes attribute usage rather than adjudicate it.

## Ordinals (maintainer decision, 2026-07-15)

Where churches number the same office-holders differently, **the
jurisdiction's own official numbering leads the display name**; competing
scholarly or encyclopedic ordinals live in `names.variants` with a note
naming the scheme. This is the record-not-adjudicate rule applied to
numbering: a church's self-description governs its own diptych.

Known open case: the **Georgian catholicoi** currently display the standard
chronology's ordinals because the official diptych was unreachable during
Milestone C — the divergences are recorded on the affected records
(their Nikoloz IX = our Nikoloz VII, etc.), and the display ordinals are
flagged for re-check against the official reckoning during verification
(see BACKLOG).

## Transliteration conventions

| Language | System |
|---|---|
| Greek | ALA-LC |
| Russian / Church Slavonic / Bulgarian | simplified BGN/PCGN |
| Serbian | native Latin (Gaj) with diacritics |
| Georgian | Georgian national system |
| Arabic | ALA-LC |
| Romanian, Polish, Czech, Slovak, Albanian | native Latin orthography with diacritics |

Source-specific spellings (Fedalto's Latin, Wikidata's language-tagged
labels, older English forms) are kept as variants, never discarded.

## Searchability

Every value in `names.variants` and `names.native` is a search key in the
dashboard and the exports. When in doubt, add the variant.
