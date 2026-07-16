# SEEDS_BACKLOG_UPDATE.md — Dispositions from the Post-Review Planning Round

**Instruction to Claude Code:** Two tasks only. (1) Append the entries in §A to
`BACKLOG.md` verbatim (these are captured ideas — do NOT build any of them
now). (2) Add the single small milestone in §B to the current queue, scheduled
just before Q-final. Plan Mode discipline and the Completion Verification
Protocol apply to §B.

---

## §A — Append to BACKLOG.md (capture only; post-freeze candidates)

| Idea | Notes for future spec | Phase candidate |
|---|---|---|
| Correspondence & citation graph ("succession of ideas") | FULL SPEC EXISTS: `CORRESPONDENCE_CITATION_GRAPH.md` (post-freeze gated). Derive edges, don't duplicate: `addressee` on letter-works; `cites`/`responds_to` on Works (locator+source required per edge); 3-tier epistemology (documented correspondence / documented citation / influence stays scholarly-gated); curated seed list (Jerome↔Augustine, Basil↔Athanasius, Cappadocians, Cyril↔Nestorius, Leo↔Flavian, Chrysostom↔Olympias); model lost halves (Olympias's replies: survival lost); works timeline view; third graph page, never blended with consecration graph. | First post-freeze module (recommended) |
| Institutions layer: monasteries + schools/academies | FULL SPEC EXISTS: `INSTITUTIONS_LAYER.md` (post-freeze gated). One entity, `type: monastery|school|academy`; lifecycle incl. suppression/refoundation (Bolshevik arc; Halki 1971) + `current_status: active|ruined|archaeological-site|museum|converted|destroyed` (Deir 'Ain 'Abata / Monastery of Lot = archaeological-site); 3-tier gate, Tier 1 by-name (~40–60 great houses); person↔institution associations (tonsured-at/hegumen/elder-of) for in-scope persons ONLY — no abbot lists; Zverinsky as Russian checklist; Sinai = autonomous jurisdiction completion; Oriental-held ancient houses via pre-schism honesty pattern; distinct map marker. Rejects: relics/pilgrimage data, complete global catalog, general monk coverage. | Second post-freeze module (recommended) |
| Communion graph (diptychs, breaks, restorations) | Breaks/restorations as dated Events; derived jurisdiction-pair communion timeline ("who was in communion with whom in year X"). HARD GATE: does not go public before NEUTRALITY.md is published. | Post-freeze, governance-gated |
| Famous manuscripts | Tier-gated (~10–15 world witnesses: Sinaiticus, Alexandrinus…); `manuscript` records linkable from Works, or minimal `notable_witnesses` field; ties: Sinaiticus↔St Catherine's, Alexandrinus↔Cyril Lucaris. | Post-freeze, low priority |
| Icons — TYPE catalog (maintainer priority; long horizon) | KEY REFRAME: catalog unit is the icon TYPE (prototype), not physical objects — "every icon ever" is unbounded; "every named type + notable instances" is finishable. One-Type-many-Instances = the one-Work-many-Editions pattern. Types carry iconographic definition, origin, FEAST DAYS (→ calendar synergy: e.g. Vladimir icon, multiple feasts); instances carry famous bearers (Sinai Pantocrator, Vladimirskaya/Tretyakov). Catalog-entry + links; image hosting a rights question to revisit (Princeton Sinai archive permits scholarly use; Wikimedia Commons PD holdings; Index of Medieval Art subscription-only). Prior-art check 2026-07: no open structured type catalog exists — same gap succession had. Possibly a sister site sharing architecture. | Post-freeze, after institutions layer; maintainer flagged as long-term priority |
| Titular usage of suppressed sees | Small `titular_usage` note on See (e.g., Constantinople's titular metropolitans of Ephesus/Chalcedon/Nicaea) — add opportunistically whenever suppressed sees are touched. | Opportunistic, any time |

## §B — Pulled forward: Tomos & autocephaly instruments (run before Q-final)

Create Work records (genre: `tomos` — add to the genre enum — or `synodal-act`)
for the primary legal instruments of autocephaly/patriarchal status, each with
relation `involving` its jurisdiction, dates, archived links to the document
text where published, and sources; link each from its Jurisdiction record and
from the councils already cataloged where applicable (e.g., Constantinople
1590/1593 ↔ the Moscow instruments).

Starter set (propose additions in the plan; this is a floor): Moscow 1589/1590/
1593 acts; Greece 1850 Tomos; Serbia 1879; Romania 1885; the 1945 Bulgarian
resolution; Georgia's 1990 recognition by Constantinople; Poland 1924; Albania
1937; Czech Lands & Slovakia 1998; OCA 1970 (Moscow-issued; recognition
disputes recorded as usual); OCU 2019 Tomos (per-recognizer handling as
usual).

Rationale for pulling forward: these documents convert the database's most
politically contested claims from sourced assertions into document-backed
records — direct armor for the governance documents published at Q-final.
Verification protocol applies; every record unverified until maintainer
review.
