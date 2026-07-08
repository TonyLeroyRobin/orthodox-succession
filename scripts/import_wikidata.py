#!/usr/bin/env python3
"""Wikidata seeding tool (KICKOFF.md §7).

Pulls bishops, dates, consecrators (P1598), VIAF (P214), and office terms
(P39 with start/end qualifiers) from Wikidata and emits DRAFT YAML files:

  * every record enters with status: unverified — a human must verify each
    claim against a graded source before promotion; never auto-promote;
  * every citation points at source/wikidata with reliability: database
    (never scholarly);
  * an existing file is NEVER overwritten — re-runs are idempotent and only
    add records that do not exist yet;
  * drafts are made internally consistent (inconsistent lifespans are
    dropped, with a note) so that seeding never breaks `validate.py`;
  * overlapping seeded tenures on one see are flagged with a `disputed`
    recognition entry noting the collision for human resolution.

Usage:
  # find an office/person QID
  python scripts/import_wikidata.py --find "Ecumenical Patriarch of Constantinople"

  # seed every holder of an office as person + tenure drafts
  python scripts/import_wikidata.py --office Q1811429 \
      --jurisdiction constantinople --see see/constantinople/constantinople

  # seed specific persons only (no tenures)
  python scripts/import_wikidata.py --qids Q44269 Q102851 --jurisdiction cyprus

  add --dry-run to print what would be written without touching data/

This is a seeding tool only. Wikidata is never a final citation.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA_DIR  # noqa: E402

import yaml  # noqa: E402

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
API_ENDPOINT = "https://www.wikidata.org/w/api.php"
USER_AGENT = "orthodox-succession-db/0.1 (data seeding; see repository README)"
WIKIDATA_SOURCE_ID = "source/wikidata"

try:  # some Windows Python installs carry a stale CA bundle; prefer certifi
    import ssl
    import certifi

    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:  # pragma: no cover
    SSL_CTX = None


def http_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120, context=SSL_CTX) as resp:
        return json.load(resp)


def sparql(query: str):
    url = SPARQL_ENDPOINT + "?" + urllib.parse.urlencode(
        {"query": query, "format": "json"}
    )
    return http_json(url)["results"]["bindings"]


def find_entities(term: str):
    url = API_ENDPOINT + "?" + urllib.parse.urlencode({
        "action": "wbsearchentities", "search": term, "language": "en",
        "format": "json", "limit": 10,
    })
    for hit in http_json(url).get("search", []):
        print(f"{hit['id']:>12}  {hit.get('label', '')}"
              f"  —  {hit.get('description', '')}")


OFFICE_QUERY = """
SELECT ?item ?itemLabel ?start ?end ?born ?died ?viaf WHERE {
  ?item p:P39 ?stmt .
  ?stmt ps:P39 wd:%(office)s .
  FILTER NOT EXISTS { ?stmt wikibase:rank wikibase:DeprecatedRank }
  OPTIONAL { ?stmt pq:P580 ?start }
  OPTIONAL { ?stmt pq:P582 ?end }
  OPTIONAL { ?item wdt:P569 ?born }
  OPTIONAL { ?item wdt:P570 ?died }
  OPTIONAL { ?item wdt:P214 ?viaf }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""

PERSON_QUERY = """
SELECT ?item ?itemLabel ?born ?died ?viaf ?consecrator WHERE {
  VALUES ?item { %(values)s }
  OPTIONAL { ?item wdt:P569 ?born }
  OPTIONAL { ?item wdt:P570 ?died }
  OPTIONAL { ?item wdt:P214 ?viaf }
  OPTIONAL { ?item wdt:P1598 ?consecrator }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def slugify(label: str) -> str:
    s = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s or "unnamed"


def ts_year(value: str | None):
    """Wikidata timestamp -> integer year, or None (BCE and junk skipped)."""
    if not value:
        return None
    m = re.match(r"^\+?(\d{4,})-", value)
    return int(m.group(1)) if m else None


def wd_date_obj(value: str, day_precision: bool = False):
    """Wikidata timestamp -> date object dict. Calendar is a heuristic
    (julian before 1583) and every seeded date says so in its note."""
    year = ts_year(value)
    if year is None:
        return None
    m = re.match(r"^\+?(\d{4,})-(\d{2})-(\d{2})", value)
    month, day = (m.group(2), m.group(3)) if m else ("01", "01")
    return {
        "value": f"{year:04d}" if not day_precision else f"{year:04d}-{month}-{day}",
        "calendar": "julian" if year < 1583 else "gregorian",
        "precision": "year",
        "note": "seeded from Wikidata; verify date, precision, and calendar",
    }


def wikidata_citation(qid: str, extra_note: str = ""):
    note = "programmatic seed — verify against a graded source"
    if extra_note:
        note += "; " + extra_note
    return [{
        "ref": WIKIDATA_SOURCE_ID,
        "locator": qid,
        "reliability": "database",
        "note": note,
    }]


def write_yaml(path: Path, record: dict, dry_run: bool) -> bool:
    """Write a draft record. Returns False (and leaves the file alone) if the
    file already exists — existing records, verified or not, are never
    overwritten."""
    if path.exists():
        print(f"skip (exists): {path}")
        return False
    if dry_run:
        print(f"would write: {path}")
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(record, fh, allow_unicode=True, sort_keys=False)
    return True


def ensure_wikidata_source(dry_run: bool):
    path = DATA_DIR / "sources" / "wikidata.yaml"
    if path.exists():
        return
    write_yaml(path, {
        "id": WIKIDATA_SOURCE_ID,
        "type": "database",
        "title": "Wikidata",
        "url": "https://www.wikidata.org/",
        "archived_url": "https://web.archive.org/web/2026/https://www.wikidata.org/",
        "status": "verified",
        "notes": "Seeding and identifiers only — never a final citation.",
    }, dry_run)


# ---------------------------------------------------------------------------
# office import: persons + tenures
# ---------------------------------------------------------------------------

def import_office(office: str, jurisdiction: str, see_id: str, dry_run: bool):
    ensure_wikidata_source(dry_run)
    rows = sparql(OFFICE_QUERY % {"office": office})
    see_slug = see_id.rsplit("/", 1)[-1]

    # fold rows: one entry per person; one term per distinct (start, end)
    people = {}
    for row in rows:
        qid = row["item"]["value"].rsplit("/", 1)[-1]
        e = people.setdefault(qid, {
            "label": None, "born": None, "died": None, "viaf": None,
            "terms": set(),
        })
        e["label"] = row.get("itemLabel", {}).get("value") or qid
        if "born" in row and e["born"] is None:
            e["born"] = row["born"]["value"]
        if "died" in row and e["died"] is None:
            e["died"] = row["died"]["value"]
        if "viaf" in row and e["viaf"] is None:
            e["viaf"] = row["viaf"]["value"]
        e["terms"].add((
            row.get("start", {}).get("value"),
            row.get("end", {}).get("value"),
        ))

    persons_written = tenures_written = skipped_terms = 0
    tenure_drafts = []  # (from_year, to_year_or_None, record, path)

    for qid, e in sorted(people.items(), key=lambda kv: kv[1]["label"]):
        label = e["label"]
        terms = sorted(
            {(ts_year(s), ts_year(en), s, en) for s, en in e["terms"]},
            key=lambda t: (t[0] is None, t[0] or 0),
        )
        start_years = [t[0] for t in terms if t[0] is not None]
        born_y, died_y = ts_year(e["born"]), ts_year(e["died"])

        # id suffix: earliest term start year, else birth year, else 0000
        suffix_year = start_years[0] if start_years else (born_y or 0)
        person_suffix = f"{slugify(label)}-{suffix_year:04d}"
        pid = f"person/{jurisdiction}/{person_suffix}"

        # internal-consistency guard: drop lifespans that contradict terms so
        # seeding can never make validate.py fail; a human sorts it out later
        lifespan_note = ""
        if born_y is not None or died_y is not None:
            bad = any(
                (born_y is not None and sy is not None and sy < born_y)
                or (died_y is not None and sy is not None and sy > died_y + 2)
                or (died_y is not None and ey is not None and ey > died_y + 2)
                for sy, ey, _, _ in terms
            )
            if bad:
                lifespan_note = (
                    " Wikidata birth/death dates conflicted with the term "
                    "dates and were NOT imported — resolve during verification."
                )
                born_y = died_y = None

        notes = (
            "Draft seeded from Wikidata (office holders import). Verify name "
            "forms, dates, calendar, and see assignment against a graded "
            "source; the id year is the earliest seeded term start."
            + lifespan_note
        )
        no_start = [t for t in terms if t[0] is None]
        if no_start:
            notes += (f" {len(no_start)} term(s) had no start-date qualifier "
                      "and produced no tenure record.")

        record = {
            "id": pid,
            "names": {"monastic": label},
            "attestation": "attested",
            "sources": wikidata_citation(qid),
            "status": "unverified",
            "notes": notes,
        }
        identifiers = {k: v for k, v in
                       [("wikidata", qid), ("viaf", e["viaf"])] if v}
        if identifiers:
            record["identifiers"] = identifiers
        if born_y is not None and e["born"]:
            record["born"] = {"date": wd_date_obj(e["born"])}
        if died_y is not None and e["died"]:
            record["died"] = {"date": wd_date_obj(e["died"])}

        ppath = DATA_DIR / "people" / jurisdiction / f"{person_suffix}.yaml"
        if write_yaml(ppath, record, dry_run):
            persons_written += 1

        # tenures, one per term with a start date
        term_no = 0
        for sy, ey, s_raw, e_raw in terms:
            if sy is None:
                skipped_terms += 1
                continue
            term_no += 1
            at = see_slug if term_no == 1 else f"{see_slug}-{term_no}"
            tid = f"tenure/{jurisdiction}/{person_suffix}@{at}"
            t_rec = {
                "id": tid,
                "person": pid,
                "see": see_id,
                "from": wd_date_obj(s_raw),
                "end_reason": "unknown",
                "sources": wikidata_citation(
                    qid, "term dates from P39 start/end qualifiers"),
                "status": "unverified",
                "notes": ("Draft tenure seeded from Wikidata P39. end_reason "
                          "is unknown until verified against a diadochal "
                          "list or scholarly source."),
            }
            if ey is not None and e_raw:
                t_rec["to"] = wd_date_obj(e_raw)
            tpath = (DATA_DIR / "tenures" / jurisdiction /
                     f"{person_suffix}@{at}.yaml")
            tenure_drafts.append((sy, ey, t_rec, tpath))

    # overlap flagging (mirrors validate.py rule 5 semantics: missing end =
    # point interval, mid-year ordinals, strict overlap)
    def ordinal(y):
        return y + 0.45
    for i in range(len(tenure_drafts)):
        for j in range(len(tenure_drafts)):
            if i == j:
                continue
            a0 = ordinal(tenure_drafts[i][0])
            a1 = ordinal(tenure_drafts[i][1] if tenure_drafts[i][1] is not None
                         else tenure_drafts[i][0])
            b0 = ordinal(tenure_drafts[j][0])
            b1 = ordinal(tenure_drafts[j][1] if tenure_drafts[j][1] is not None
                         else tenure_drafts[j][0])
            if a0 < b1 - 0.01 and b0 < a1 - 0.01 and j > i:
                rec_j = tenure_drafts[j][2]
                rec_j.setdefault("recognition", [{
                    "by": "all",
                    "status": "disputed",
                    "note": (f"seeded term dates overlap "
                             f"{tenure_drafts[i][2]['id']} — rival claim, "
                             "restoration, or bad data; resolve during "
                             "human verification"),
                }])

    for _, _, t_rec, tpath in tenure_drafts:
        if write_yaml(tpath, t_rec, dry_run):
            tenures_written += 1

    print(f"import_wikidata: office {office} -> {persons_written} person "
          f"draft(s), {tenures_written} tenure draft(s) "
          f"({skipped_terms} term(s) without start skipped), all unverified"
          f"{' [dry run]' if dry_run else ''}")


# ---------------------------------------------------------------------------
# plain person import (original mode)
# ---------------------------------------------------------------------------

def import_people(qids, jurisdiction: str, dry_run: bool):
    ensure_wikidata_source(dry_run)
    values = " ".join(f"wd:{q}" for q in qids)
    rows = sparql(PERSON_QUERY % {"values": values})

    by_qid = {}
    for row in rows:
        qid = row["item"]["value"].rsplit("/", 1)[-1]
        entry = by_qid.setdefault(qid, {"label": None, "born": None,
                                        "died": None, "viaf": None,
                                        "consecrators": set()})
        entry["label"] = row.get("itemLabel", {}).get("value") or qid
        for k in ("born", "died", "viaf"):
            if k in row and entry[k] is None:
                entry[k] = row[k]["value"]
        if "consecrator" in row:
            entry["consecrators"].add(
                row["consecrator"]["value"].rsplit("/", 1)[-1])

    written = 0
    for qid, e in by_qid.items():
        label = e["label"]
        born_y = ts_year(e["born"])
        suffix = f"{born_y:04d}" if born_y else "0000"
        person_suffix = f"{slugify(label)}-{suffix}"
        record = {
            "id": f"person/{jurisdiction}/{person_suffix}",
            "names": {"monastic": label},
            "attestation": "attested",
            "sources": wikidata_citation(qid),
            "status": "unverified",
            "notes": ("Draft seeded from Wikidata. Verify name forms, dates, "
                      "and see assignments against a graded source; the id "
                      "suffix year is provisional (birth year) until the "
                      "first-tenure year is known. Consecrator QID(s): "
                      + (", ".join(sorted(e["consecrators"])) or "none")),
        }
        identifiers = {k: v for k, v in
                       [("wikidata", qid), ("viaf", e["viaf"])] if v}
        if identifiers:
            record["identifiers"] = identifiers
        if e["born"]:
            record["born"] = {"date": wd_date_obj(e["born"])}
        if e["died"]:
            record["died"] = {"date": wd_date_obj(e["died"])}
        path = DATA_DIR / "people" / jurisdiction / f"{person_suffix}.yaml"
        if write_yaml(path, record, dry_run):
            written += 1
    print(f"import_wikidata: {written} draft person record(s) "
          f"({'dry run' if dry_run else 'written'}), all status: unverified")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--find", help="search Wikidata entities by label")
    ap.add_argument("--office", help="QID of an office; seeds holders + tenures")
    ap.add_argument("--see", help="see id for tenures (required with --office)")
    ap.add_argument("--qids", nargs="+", help="Wikidata QIDs of persons")
    ap.add_argument("--jurisdiction", default="unsorted",
                    help="jurisdiction slug for output paths/ids")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.find:
        find_entities(args.find)
        return 0
    if args.office:
        if not args.see or args.jurisdiction == "unsorted":
            ap.error("--office requires --see and --jurisdiction")
        import_office(args.office, args.jurisdiction, args.see, args.dry_run)
        return 0
    if args.qids:
        import_people(sorted(set(args.qids)), args.jurisdiction, args.dry_run)
        return 0
    ap.error("nothing to do: pass --find, --office, or --qids")


if __name__ == "__main__":
    sys.exit(main())
