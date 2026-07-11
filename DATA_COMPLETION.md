# DATA_COMPLETION.md — Gap Closure, Pre-Schism Rome, Veneration, Works Backfill

**Instruction to Claude Code:** Read `KICKOFF.md` and `CLAUDE.md` first; all their
rules bind. This document corrects and completes the dataset produced so far. Work
in **Plan Mode discipline**: before each milestone, present a plan (files to be
created/changed, sources to be used, record counts expected) and WAIT for the
maintainer's approval before writing anything. Never bulk-verify; `verified` status
is set only through the human verification workflow.

---

## 0. Behavior contract for every session under this spec

1. Plan first, execute after approval. One milestone at a time.
2. Enumerations in this document are exhaustive instructions, not examples. Where
   the maintainer's intent seems to imply something not written here, ASK — do not
   silently extend, and do not silently omit.
3. Every record created here enters as `status: unverified` unless it carries a
   graded non-tradition source AND the maintainer verifies it via the admin queue.
4. Report at the end of each milestone: records created, records modified, known
   remaining gaps (explicitly listed), validation status.

---

## 1. Schema addition: Veneration (Person entity)

Add an optional `veneration` block to the Person schema, validate.py, admin forms,
and KICKOFF.md §4.1:

```yaml
veneration:
  status: saint | not-venerated | uncertain
  titles: []            # e.g. Equal-to-the-Apostles, Hieromartyr, Confessor,
                        # Wonderworker, the Great, the Theologian, the Dialogist
  recognition:          # per-recognizer, same pattern as jurisdictions
    - by: universal | jurisdiction:<id> | pre-schism-church
      glorified_date: {date?}        # formal glorification where known (rare pre-modern)
      note: ""
  feast_days:
    - {month_day: "MM-DD", calendar: julian|gregorian, note: ""}
  sources: []
```

Rules:
- Absence of the block means "not yet assessed" — distinct from
  `status: not-venerated`, which is an assessed claim requiring a source.
- Local-only veneration is expressed via `recognition` entries naming specific
  jurisdictions; universal veneration uses `by: universal`.
- Figures condemned by councils (e.g., Nestorius, Dioscorus post-451) simply carry
  `not-venerated` here; their condemnations already live in Participation records.
  Do NOT model Oriental Orthodox veneration of such figures — out of scope.
- Do not mass-assign sainthood from Wikidata. Populate opportunistically with
  sources (official calendars, synaxaria), starting with the persons touched in
  Milestones B–D below.

---

## 2. New jurisdiction: Pre-Schism Rome (SCOPE AMENDMENT — explicit)

KICKOFF.md scope is amended as follows and this list is EXHAUSTIVE: the historical
jurisdictions to be modeled as part of the undivided pre-1054 Church are:

1. **jurisdiction/pre-schism-rome** — the See of Rome from the apostolic era to
   1054. THIS MILESTONE.
2. Pre-schism Western missionary/regional traditions (British Isles, Gaul, etc.) —
   remain in `data/traditions/` only, NOT succession chains, unless the maintainer
   later explicitly promotes a specific see.

### Requirements for pre-schism-rome

- `type: historical`; end cap: 1054 (the mutual excommunications of July 1054),
  with a `note` stating the end cap is the conventional schism date, that estrangement
  was gradual, and that the post-1054 line continues outside this database's scope
  (`successor: none-in-scope`).
- `see/pre-schism-rome/rome` with apostolic founders Peter and Paul recorded per
  sources (attestation graded honestly; earliest lists are tradition/scholarly).
- **The complete succession of bishops of Rome from Linus (or Peter, per source
  handling below) through Leo IX (d. 1054)** — roughly 150 tenures. No
  cherry-picking; every occupant on the reference lists gets a Tenure.
- Antipopes/rival claimants (e.g., Hippolytus, Novatian, Ursinus, the Laurentian
  schism, Anastasius Bibliothecarius…) are modeled as overlapping tenures with
  `recognition: rival-claimant` — the existing pattern. Do not omit them; they are
  part of the historical record.
- Peter himself: model as Person with apostolic attestation; whether he appears as
  first Tenure or as `apostolic_founder` follows the sources — record both the
  traditional enumeration (Peter first) and the note that earliest lists (Irenaeus)
  begin the episcopal succession with Linus.
- Veneration blocks for the major venerated popes encountered (at minimum: Clement I,
  Leo I "the Great", Gregory I "the Dialogist", Martin I "the Confessor") with
  Orthodox calendar sources — these demonstrate §1 in real data.

### Sources (create Source records for each)

- *Liber Pontificalis* (ed. Duchesne; public domain scans) — primary/near-primary
  for early-medieval popes.
- J.N.D. Kelly, *Oxford Dictionary of Popes* — scholarly reference for dates and
  disputed successions.
- Jaffé, *Regesta Pontificum Romanorum* — scholarly, public domain.
- Eusebius, *Ecclesiastical History* + Irenaeus, *Adversus Haereses* III.3 — the
  earliest succession lists (grade: tradition/scholarly per claim).
- The Annuario Pontificio historical list — official-list grade (archive the URL).
- Wikidata may SEED the skeleton; every seeded record stays `unverified` and its
  dates must be reconciled against Kelly/Duchesne in the plan report.

---

## 3. Gap closure for the Eastern primatial spines (the main event)

### Method — "complete-list reconciliation", per see, in this order:
Constantinople, Alexandria, Antioch, Jerusalem, Moscow, Serbia, Romania, Bulgaria,
Georgia, Cyprus (audit only — pilot data exists), Greece, Poland, Albania,
Czech Lands & Slovakia, OCA, OCU.

For each see:

1. Obtain the COMPLETE official diadochal list (patriarchate website — archive it)
   and the corresponding sections of Le Quien/Fedalto where available.
2. Build a reconciliation table: official list ⟷ existing records ⟷ Wikidata.
3. Create a Tenure (and Person where missing) for EVERY occupant on the official
   list that has no record — sourced to the official list at minimum. Expected
   scale: Constantinople alone ~270 tenures; total across sees ~1,500–2,000.
4. Where lists disagree (numbering, dates, disputed patriarchs, iconoclast-era
   rivals, Meletian-era Antioch), create the records with `status: disputed` or
   recognition qualifiers and a `note` describing the disagreement — never pick a
   winner silently.
5. Milestone report MUST include a per-see coverage statement: "official list has N
   occupants; database now has N tenures; K disputed; 0 silently missing."

### Known specific gaps visible today (fix in this pass; list not exhaustive —
the method above finds the rest):
- Alexandria: everything between Dioscorus (451) and the 9th c.; post-1398 to
  present.
- Antioch: the entire spans 330–360, 559–695, 702–1090, 1100–1673, 1720–1766,
  1791–1906, 1928–1979.
- Jerusalem: gaps around 333–422, 458–630, 638–706, 735–820, 838–950, 962–1020,
  post-1020 to present.
- Moscow: patriarchs before 1642 (Job, Ignatius [disputed], Hermogenes, Philaret,
  Joasaph I, Joseph — then the list continues), 1658–1721 (incl. the patriarchal
  vacancy/Synodal question — model the 1721–1917 Synodal period as a gap in
  patriarchal tenures WITH an explanatory context event, not as missing data),
  1700–1917 handled accordingly, Tikhon 1917 onward to Kirill.
- Constantinople and all remaining sees: run the same reconciliation.

### Data hygiene (same pass)
- **Name normalization:** imported Wikidata labels in French or other languages
  ("Cyrille III d'Antioche", "Daniel Ier d'Antioche") are re-rendered per the
  transliteration conventions; original label moves to `variants`. Spelling
  corrections (Eustatius → Eustathius) likewise.
- **Display-name consistency:** person display names carry no honorific prefix
  ("Patriarch X of Y" → "X of Y"); office is expressed by the Tenure, not the name.
  Apply across all existing records.

---

## 4. Works backfill — starter set (exhaustive for THIS milestone; more later)

Create Work + Edition records, following one-Work-many-Editions, with PG locators
and public-domain links where they exist. Note: CPG numbering ends around the 8th
century — do not invent CPG numbers for later authors.

- **Photios I of Constantinople**: *Mystagogy of the Holy Spirit* (PG 102);
  *Bibliotheca / Myriobiblon* (PG 103–104); *Amphilochia* (PG 101); *Homilies*
  (Eng. tr. Mango, 1958 — in-copyright; link WorldCat).
- **John Chrysostom**: *On the Priesthood* (PG 48; NPNF I.9); *Homilies on Matthew*
  (PG 57–58; NPNF I.10); *Divine Liturgy* attributed — attribution: disputed, note.
- **Athanasius of Alexandria**: *On the Incarnation* (PG 25; public-domain tr.);
  *Life of Antony* (PG 26; NPNF II.4).
- **Basil the Great**: *On the Holy Spirit* (PG 32; NPNF II.8); *Hexaemeron* (PG 29).
- **Gregory the Theologian**: *Five Theological Orations* (PG 36; NPNF II.7).
- **Cyril of Alexandria**: *On the Unity of Christ* (PG 75); *Twelve Anathemas*
  (within the Ephesus acts — relation: involving).
- **Gregory Palamas**: *Triads* (in-copyright critical eds.; link publisher);
  *Homilies*.
- **Leo I of Rome**: *Tome of Leo* (PG/PL cross-ref; NPNF II.12 — relation: by;
  also involving re: Chalcedon); *Sermons* (NPNF II.12).
- **Gregory I of Rome**: *Dialogues*; *Pastoral Rule* (NPNF II.12–13).
- **Mark of Ephesus**: works on the Florence controversy — model with `disputed`
  editions data if sourcing is thin; ASK before guessing.
- Cross-link works to Participation where a work IS conciliar material (Tome of
  Leo ↔ Chalcedon; Twelve Anathemas ↔ Ephesus).

Also add veneration blocks (per §1) for every person in this list, sourced to
Orthodox calendars.

## 5. Tooling additions

- `scripts/gap_report.py`: for each see, print occupancy timeline with gaps > 2
  years flagged, counts by status, and sees with zero apostolic_founder sourcing.
  Wire it into the admin dashboard home page and `make build` (info-level).
- Verification queue: add filter by import batch AND by see, so reconciliation
  batches can be reviewed see-by-see.

## 6. Milestones & order

- **A — Schema + hygiene:** §1 veneration schema, §3 name normalization &
  display-name pass, `gap_report.py`. (Small, fast, unblocks everything.)
- **B — Pre-Schism Rome:** §2 complete.
- **C — Eastern gap closure:** §3, one see per approved plan, starting
  Constantinople.
- **D — Works & veneration backfill:** §4.

Acceptance for each: validation green; gap report attached; per-see coverage
statement; nothing auto-verified; maintainer sign-off recorded in the commit
message (`per DATA_COMPLETION.md milestone X, approved`).
