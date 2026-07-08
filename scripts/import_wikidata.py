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
import time
import urllib.error
import unicodedata
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA_DIR  # noqa: E402

import yaml  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):  # Windows cp1252 consoles
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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


def http_json(url: str, attempts: int = 6):
    """GET JSON with polite pacing and 429/5xx backoff."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    delay = 5.0
    for attempt in range(attempts):
        time.sleep(1.0)  # politeness gap between all requests
        try:
            with urllib.request.urlopen(req, timeout=120,
                                        context=SSL_CTX) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503) and attempt < attempts - 1:
                retry_after = exc.headers.get("Retry-After")
                wait = float(retry_after) if (retry_after or "").isdigit() \
                    else delay
                print(f"  HTTP {exc.code}; retrying in {wait:.0f}s "
                      f"({attempt + 1}/{attempts - 1})", file=sys.stderr)
                time.sleep(wait)
                delay = min(delay * 2, 120)
                continue
            raise


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
            bad = (
                # Wikidata century/decade-precision timestamps parse as bare
                # years and can invert the lifespan
                (born_y is not None and died_y is not None
                 and died_y < born_y)
            ) or any(
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
# consecration import: P1598 edges between persons already in the database
# ---------------------------------------------------------------------------

CONSECRATOR_QUERY = """
SELECT ?item ?consecrator WHERE {
  VALUES ?item { %(values)s }
  ?item wdt:P1598 ?consecrator .
}
"""


def import_consecrations(min_year: int, dry_run: bool):
    """For every person in the database with a Wikidata QID, pull P1598
    (consecrator) and emit consecration drafts where BOTH parties already
    exist as person records.

    Honesty rules:
      * P1598 does not distinguish principal from co-consecrators, so every
        consecrator lands in co_consecrators and principal_consecrator is
        left absent, noted for verification.
      * The consecration date is NOT in Wikidata; it is approximated by the
        consecrated person's first tenure start with precision `circa` and a
        note saying exactly that. Persons without a dated tenure are
        skipped (the schema requires a date, and inventing one silently
        would violate the project's rules).
      * Consecrators who were dead (or unborn) at the approximated date are
        dropped; empty records are skipped.
      * Records that would create a cycle in the consecration graph are
        skipped and reported.
    """
    ensure_wikidata_source(dry_run)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from common import load_all, date_year  # local import to avoid cycles

    records, _ = load_all()
    persons = {r["data"]["id"]: r["data"] for r in records
               if r["kind"] == "person" and r["data"].get("id")}
    qid_to_pid = {}
    for pid, p in persons.items():
        qid = (p.get("identifiers") or {}).get("wikidata")
        if qid:
            qid_to_pid[qid] = pid

    # first dated tenure start per person
    first_start = {}
    for r in records:
        if r["kind"] != "tenure":
            continue
        d = r["data"]
        y = date_year(d.get("from"))
        pid = d.get("person")
        if pid and y is not None and (pid not in first_start
                                      or y < first_start[pid]):
            first_start[pid] = y

    # existing consecration edges (for cycle detection) and existing ids
    edges = {}
    existing = set()
    for r in records:
        if r["kind"] != "consecration":
            continue
        d = r["data"]
        existing.add(d.get("consecrated"))
        ks = ([d["principal_consecrator"]]
              if d.get("principal_consecrator") else []) \
            + (d.get("co_consecrators") or [])
        for k in ks:
            edges.setdefault(k, set()).add(d.get("consecrated"))

    def reaches(src, dst):  # is dst reachable from src?
        stack, seen = [src], set()
        while stack:
            n = stack.pop()
            if n == dst:
                return True
            if n in seen:
                continue
            seen.add(n)
            stack.extend(edges.get(n, ()))
        return False

    # query Wikidata in chunks
    qids = sorted(qid_to_pid)
    pairs = []
    for i in range(0, len(qids), 150):
        chunk = qids[i:i + 150]
        rows = sparql(CONSECRATOR_QUERY
                      % {"values": " ".join(f"wd:{q}" for q in chunk)})
        for row in rows:
            item = row["item"]["value"].rsplit("/", 1)[-1]
            kons = row["consecrator"]["value"].rsplit("/", 1)[-1]
            pairs.append((item, kons))
        print(f"  queried {min(i + 150, len(qids))}/{len(qids)} QIDs, "
              f"{len(pairs)} P1598 edge(s) so far")

    by_target = {}
    for item, kons in pairs:
        by_target.setdefault(item, set()).add(kons)

    written = skipped = 0
    for qid, kon_qids in sorted(by_target.items()):
        pid = qid_to_pid[qid]
        if pid in existing:
            skipped += 1
            continue
        year = first_start.get(pid)
        if year is None or year < min_year:
            skipped += 1
            continue
        consecrators = []
        for kq in sorted(kon_qids):
            kpid = qid_to_pid.get(kq)
            if not kpid or kpid == pid:
                continue
            kp = persons[kpid]
            died = date_year((kp.get("died") or {}).get("date"))
            born = date_year((kp.get("born") or {}).get("date"))
            if died is not None and died < year - 26:
                continue  # dead well before the approximated date
            if born is not None and born > year:
                continue
            consecrators.append(kpid)
        if not consecrators:
            skipped += 1
            continue
        if any(reaches(pid, k) for k in consecrators):
            print(f"  SKIP (would create cycle): {pid}")
            skipped += 1
            continue

        jur, suffix = pid.split("/")[1], pid.rsplit("/", 1)[-1]
        rec = {
            "id": f"consecration/{jur}/{suffix}",
            "consecrated": pid,
            "date": {
                "value": f"{year:04d}",
                "calendar": "julian" if year < 1583 else "gregorian",
                "precision": "circa",
                "note": ("consecration date not in Wikidata; approximated "
                         "by the first tenure start for chronology — "
                         "replace from synodal records during verification"),
            },
            "co_consecrators": consecrators,
            "sources": wikidata_citation(
                qid, "consecrator(s) from P1598"),
            "status": "unverified",
            "notes": ("Draft seeded from Wikidata P1598. P1598 does not "
                      "distinguish the principal consecrator from "
                      "co-consecrators, so all are recorded as "
                      "co_consecrators and principal_consecrator is left "
                      "absent — assign during verification."),
        }
        path = DATA_DIR / "consecrations" / jur / f"{suffix}.yaml"
        if write_yaml(path, rec, dry_run):
            written += 1
            for k in consecrators:
                edges.setdefault(k, set()).add(pid)

    print(f"import_wikidata: {written} consecration draft(s) written, "
          f"{skipped} candidate(s) skipped (existing record, no dated "
          f"tenure, before {min_year}, no surviving consecrator, or cycle)"
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
    ap.add_argument("--consecrations", action="store_true",
                    help="seed P1598 consecration edges between persons "
                         "already in the database")
    ap.add_argument("--min-year", type=int, default=1400,
                    help="with --consecrations: skip approximated dates "
                         "before this year (default 1400, per Milestone 4)")
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
    if args.consecrations:
        import_consecrations(args.min_year, args.dry_run)
        return 0
    if args.qids:
        import_people(sorted(set(args.qids)), args.jurisdiction, args.dry_run)
        return 0
    ap.error("nothing to do: pass --find, --office, --consecrations, or --qids")


if __name__ == "__main__":
    sys.exit(main())
