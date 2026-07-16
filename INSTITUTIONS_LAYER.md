# INSTITUTIONS_LAYER.md — Monasteries, Schools & Academies (Post-Freeze Module)

**Instruction to Claude Code:** `KICKOFF.md`, `CLAUDE.md`, and all prior specs
bind. **GATE: do not begin this module until Q-final is signed off, and (recommended)
after CORRESPONDENCE_CITATION_GRAPH.md, since this module involves a genuine new
collection effort while that one is mostly derivation. Maintainer initiates.**
Plan Mode discipline throughout. IDs permanent. $0 and static.

Concept: bishops are drawn from the monastic clergy and formed in monasteries
and schools — institutions are the seedbeds of the episcopate this database
documents. This layer records WHERE the people in the succession graphs were
made: the geography of formation.

## COMPLETION VERIFICATION PROTOCOL
Identical to prior specs: line-by-line evidence-mapped checklist (done/partial/
not-done, no bare "done"), full validation + build with summary, local render
inspection with stated observations, coverage statement for data milestones,
honest gaps, report-and-STOP for maintainer sign-off per milestone.

## I1 — Schema: the Institution entity

`institution/<slug>`:
- `type: monastery | school | academy`
- name, name variants/native script (existing conventions), location (lat/lon,
  modern place)
- `jurisdiction_history: [{jurisdiction, from, to}]` — institutions change
  jurisdictions too (Athos under Constantinople; Sinai's peculiar status)
- lifecycle: `founded{date, note}`, and events for suppression/closure/
  refoundation as dated entries (`history: [{event: founded|suppressed|
  destroyed|refounded|closed|reopened, date, note, sources}]`) — the
  Bolshevik arc (suppressed 1918–1930s, refounded post-1991) and Halki
  (closed 1971, unreopened) are modeled here, not in prose
- `current_status: active | ruined | archaeological-site | museum | converted
  | destroyed` (Deir 'Ain 'Abata, the Monastery of St Lot in Jordan:
  archaeological-site — excavated from 1988, Byzantine monastery at Lot's
  cave, abandoned c. 8th–9th century)
- `official_site: {url, archived_url}` — the maintainer's requested link to
  the living institution, archived like every web source
- sources[], status, notes — all existing conventions apply.

Typika and monastic rules are Works (the Rule of Pachomius is the existing
precedent) — link via a `typikon: work-id` field where one exists.

## I2 — Admission gate (three tiers)

- **Tier 1 — by-name curated list** (~40–60; the plan MUST enumerate for
  approval before creation; floor list): Mar Saba; St Catherine's, Sinai; the
  Studion; the twenty ruling monasteries of Athos; Kyiv Caves Lavra;
  Trinity–St Sergius Lavra; Optina; Valaam; Solovetsky; St John the
  Theologian, Patmos; the Meteora houses; Sumela; Deir 'Ain 'Abata. Schools/
  academies: the Catechetical School of Alexandria (Pantaenus — where this
  project's very first question pointed); the School of Antioch (as an
  institution-of-formation record, honestly noted as a scholarly construct as
  much as a campus); Halki; the Moscow, Kyiv-Mohyla (Peter Mohyla — already
  in the library), and St Petersburg academies; St Vladimir's Seminary.
- **Tier 2 — connection rule:** any institution connected to an in-scope
  person or event may be added when encountered (the admission-rule pattern,
  fourth use).
- **Tier 3 — everything else: backlog, forever.** A complete catalog of all
  monasteries is explicitly NOT the goal (the Synaxarion trap); for the
  Russian pre-1917 sweep, Zverinsky's pre-revolutionary catalog of Russian
  monasteries (public domain) is the checklist SOURCE for Tier 1/2 records —
  cited, never mass-imported.

## I3 — Person↔Institution associations

`association/<slug>`: `{person, institution, role: tonsured-at | brotherhood |
hegumen | elder-of | student | teacher, dates?, sources[], status}`.
- **In-scope persons ONLY** (validator, error level). Recording that Theodore
  the Studite was hegumen of the Studion is succession-relevant; abbot lists
  and faculty rosters are NOT — no person may be created merely to populate
  an institution.
- These associations complement (never duplicate) the existing tonsured/
  teacher relationship records: the relationship is person→person; the
  association is person→place. Where both are known, both exist.

## I4 — Special cases (handle honestly)

1. **Sinai completes a jurisdiction:** the autonomous Church of Sinai —
   effectively one monastery with an archbishop, the smallest self-governing
   body in Orthodoxy — is added as `jurisdiction type: autonomous` with its
   archiepiscopal succession per the standard reconciliation method, linked
   to the St Catherine's institution record.
2. **Oriental-held ancient houses** (e.g., St Anthony's by the Red Sea, the
   Scetis monasteries): model the pre-Chalcedonian foundation as shared
   heritage via jurisdiction_history, with an explicit note where the
   lineage passes outside Chalcedonian scope — the pre-schism honesty
   pattern, third use. No pretense, no exclusion.
3. Institutions do NOT get succession lists of their own heads (see I3); a
   `notable_heads` prose note (sourced) is permitted on the record.

## I5 — Site & map

1. Institution pages (per entity, standard citations/status rendering) + an
   institutions index filterable by type/jurisdiction/status.
2. **Map layer:** distinct marker shape for institutions (one visual channel,
   one meaning — shape distinguishes institution vs see; fill color remains
   verification status); time slider uses lifecycle events, so Russian
   monasteries visibly go dark after 1917 and rekindle after 1991; toggle to
   show/hide the institution layer.
3. Person pages: "Formation" line rendering associations (tonsured at …,
   hegumen of …).

## I6 — Boundaries (explicit rejects)

- No relics or pilgrimage data.
- No complete global monastery catalog, ever (tier gate is permanent).
- No general coverage of monks/faculty (admission rule holds).
- No tracking of institution websites beyond the archived official link.

Ordering: I1 → I2 (Tier 1 in approved batches) → I3/I4 opportunistically with
the batches → I5. Tier 2 remains open-ended thereafter.
