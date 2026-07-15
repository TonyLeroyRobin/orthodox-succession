# CHANGELOG

One line per merged change batch (ROADMAP_ADDENDUM §B1). Data releases
increment the minor version; corrections increment the patch. Kept from
v0.1.0 onward — new batches are added under **Unreleased** and folded into a
version heading at tag time.

## [Unreleased]

- kyiv: the historical metropolitanate populated, Michael I 988 to Gedeon Chetvertynsky 1685/1690 — 60 tenures with rule-6 qualifiers on five rival pairs; post-Brest suppression referenced
- cyprus: the archiepiscopal line closed, Gelasios I 325 to Leontios 1947 — 61 tenures across Salamis-Constantia and Nicosia; Bulla Cypria context event; the audit's documented gap eliminated
- ohrid: the Archbishopric of Ohrid line closed, John I of Debar 1018 to Arsenius II 1767 — 84 tenures, 80 persons, abolition context event; Mark Xylokaravis linked cross-jurisdiction
- works: Milestone D backfill — 19 works for the §4 starter set (PG/PL/CPG locators, CCEL links, Mark of Ephesus per maintainer decision), Basil the Great and Mark of Ephesus person records, Patrologia Latina source, veneration blocks on the six authors lacking them
- dashboard: ROADMAP §C phase — map of sees over time (C1, bundled Natural Earth), commemorated-today calendar with Julian/Gregorian toggle (C2), schema.org JSON-LD on person pages (C3), corroboration badges (C4, maintainer-approved), GitHub Pages deployment workflow
- docs: Zenodo DOI badge and citation backfilled after the v0.1.0 release (concept DOI 10.5281/zenodo.21382721)

## [0.1.0] — 2026-07-15 (first public release; ID permanence locks here)

- governance: NEUTRALITY.md, NAMING.md, CONTRIBUTING.md drafted with the maintainer (B2) — disputes UI badge-now-toggle-later, ecclesiastical see names, church's-own-numbering ordinals, maintainer-only verification
- release-prep: CHANGELOG seeded, README citation section, B2 placeholders (B1 package)

- verification: session wrap-up — 1,179 archive snapshots pinned, source conflicts re-sourced, status audit clean (zero auto-promotions)
- verification: cross-jurisdiction person dedup — five clusters merged (Pigas, Loukaris, Metaxakis ×3, Kosmas II/III, Joanikije III), plus the Georgian Okropir II seed
- ocu: Milestone C gap closure — Kyiv reconciled, symmetric per-recognizer rival-claim modeling
- oca: Milestone C gap closure — the American line, Joasaph 1799 to Tikhon, per the fetchable official past-primates list
- czech-slovakia: Milestone C gap closure — the alternating Prague/Prešov primacy, fully manual entry
- albania: Milestone C gap closure — Tirana spine, Vissarion 1929 to Joan; abolition-of-religion context event
- poland: Milestone C gap closure — Warsaw spine, Jerzy 1922 to Sawa
- greece: Milestone C gap closure — the Athens spine, Neophytos V 1833 to Ieronymos II
- cyprus: Milestone C audit (audit-only per spec) — pilot data passes; veneration blocks for Barnabas and Epiphanios
- georgia: Milestone C gap closure — the single spine, John I 326 to Shio III (153 chronology rows)
- bulgaria: Milestone C gap closure — three eras (Preslav, Tarnovo, Sofia) as historical jurisdictions
- romania: Milestone C gap closure — the single spine, Iachint 1359 to Daniel
- serbia: Milestone C gap closure — the single spine, Sava 1219 to Porfirije
- moscow: Milestone C gap closure — the patriarchal succession, 1589 to present; Synodal period as context event
- jerusalem: Milestone C gap closure — complete succession, 33 AD to present
- antioch: Milestone C gap closure — complete succession, 37 AD to present
- fix: recognition qualifier on Mark of Alexandria (list-inherent overlap with Anianos)
- alexandria: Milestone C gap closure — complete succession, 40 AD to present
- constantinople: Milestone C gap closure — complete succession, 38 AD to present
- fix: gap_report sort crash on identical tenure spans
- rome: veneration blocks for the papal saints and the apostle-founders
- rome: reconciliation vs the official vatican.va list + 17 antipopes as rival claimants
- seed: papal spine from Wikidata through Leo IX — 150 persons, 152 tenures
- rome: jurisdiction, see, bibliography, Peter and Paul (Milestone B structural layer)
- schema: none-in-scope successor sentinel, plural apostolic_founders, seeder year cap
- i18n: all site UI strings extracted to site/locales/en.json
- tooling: gap_report.py + verification queue --see/--batch filters
- hygiene: display-name pass over all person records — 134 changed, 19 flagged
- schema: veneration block (Person) + Relationship entity, validated end-to-end
- governance: BACKLOG.md, ADMIN_DASHBOARD.md placeholder, ID-permanence clarification
- jerusalem + alexandria + antioch: verification pass vs official diadochal lists — 30 tenures verified
- constantinople: verification pass vs the official EP diadochal list — 52 tenures verified
- cyprus: verification pass vs official site + public references — 3 factual errors fixed, dates day-precise
- site: Milestone 4 dashboard polish — D3 interactive consecration graph
- cyprus + bibliography: suffragan sees, reference works, four primary works
- seed: consecration-level depth from Wikidata P1598 (15th c. onward)
- context: full backdrop layer — 33 new events, 330 to 1991
- metropolises: Kyiv, Ohrid, Thessalonica with mother-church founding links
- councils: seven ecumenical + key local councils with participations, per Tanner/Mansi/NPNF II-14
- workflow: verification queue tool + docs; dashboard title generalized
- seed: remaining primatial spines from Wikidata — Russia, Serbia, Romania, Bulgaria, Georgia, Greece, Poland, Albania, OCA, OCU
- seed: ancient patriarchates from Wikidata — Constantinople, Alexandria, Antioch, Jerusalem
- jurisdictions: Milestone 2 structural layer — 14 churches, primatial sees, official-site sources
- site: Milestone 1 prototype dashboard — Cyprus timeline + bishop profiles
- cyprus: Milestone 1 pilot data — jurisdiction, sees, persons, tenures, consecrations, Ephesus 431, works, context layer
- scaffold: Milestone 0 — layout, 10 JSON Schemas, validate/build/export pipeline
