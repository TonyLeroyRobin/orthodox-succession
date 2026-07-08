#!/usr/bin/env python3
"""Wikidata seeding tool (KICKOFF.md §7).

Pulls bishops, dates, consecrators (P1598), VIAF (P214), and works from the
Wikidata SPARQL endpoint and emits DRAFT YAML files:

  * every record enters with status: unverified — a human must verify each
    claim against a graded source before promotion; never auto-promote;
  * every citation points at source/wikidata with reliability: database
    (never scholarly);
  * an existing file is NEVER overwritten — re-runs are idempotent and only
    add records that do not exist yet.

Usage:
  python scripts/import_wikidata.py --qids Q44269 Q102851
  python scripts/import_wikidata.py --position Q611644 --jurisdiction cyprus
      (--position: a Wikidata QID for an episcopal office, used via P39)
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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA_DIR  # noqa: E402

import yaml  # noqa: E402

ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "orthodox-succession-db/0.1 (data seeding; see repository README)"
WIKIDATA_SOURCE_ID = "source/wikidata"

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

POSITION_QUERY = """
SELECT DISTINCT ?item WHERE {
  ?item p:P39 ?stmt .
  ?stmt ps:P39 wd:%(position)s .
}
"""


def sparql(query: str):
    url = ENDPOINT + "?" + urllib.parse.urlencode(
        {"query": query, "format": "json"}
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)["results"]["bindings"]


def slugify(label: str) -> str:
    s = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s or "unnamed"


def wd_date(value: str):
    """Wikidata timestamp -> date object dict (year precision is the safest
    default for seeded data; a human refines it during verification)."""
    m = re.match(r"^([+-]?\d{4,})-(\d{2})-(\d{2})", value)
    if not m:
        return None
    year = int(m.group(1))
    return {
        "value": f"{year:04d}-{m.group(2)}-{m.group(3)}",
        "calendar": "gregorian",
        "precision": "year",
        "note": "seeded from Wikidata; verify precision and calendar",
    }


def wikidata_citation(qid: str):
    return [{
        "ref": WIKIDATA_SOURCE_ID,
        "locator": qid,
        "reliability": "database",
        "note": "programmatic seed — verify against a graded source",
    }]


def ensure_wikidata_source(dry_run: bool):
    path = DATA_DIR / "sources" / "wikidata.yaml"
    if path.exists():
        return
    record = {
        "id": WIKIDATA_SOURCE_ID,
        "type": "database",
        "title": "Wikidata",
        "url": "https://www.wikidata.org/",
        "archived_url": "https://web.archive.org/web/2026/https://www.wikidata.org/",
        "status": "verified",
        "notes": "Seeding and identifiers only — never a final citation.",
    }
    write_yaml(path, record, dry_run)


def write_yaml(path: Path, record: dict, dry_run: bool) -> bool:
    """Write a draft record. Returns False (and leaves the file alone) if the
    file already exists — existing records, verified or not, are never
    overwritten."""
    if path.exists():
        print(f"skip (exists): {path}")
        return False
    if dry_run:
        print(f"would write: {path}")
        print(yaml.safe_dump(record, allow_unicode=True, sort_keys=False))
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(record, fh, allow_unicode=True, sort_keys=False)
    print(f"wrote draft: {path}")
    return True


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
        if "born" in row:
            entry["born"] = row["born"]["value"]
        if "died" in row:
            entry["died"] = row["died"]["value"]
        if "viaf" in row:
            entry["viaf"] = row["viaf"]["value"]
        if "consecrator" in row:
            entry["consecrators"].add(
                row["consecrator"]["value"].rsplit("/", 1)[-1])

    written = 0
    for qid, e in by_qid.items():
        label = e["label"]
        born = wd_date(e["born"]) if e["born"] else None
        year = None
        if born:
            year = int(born["value"][:4].lstrip("0") or 0)
        suffix = f"{year:04d}" if year else "0000"
        pid = f"person/{jurisdiction}/{slugify(label)}-{suffix}"
        record = {
            "id": pid,
            "names": {"monastic": label},
            "attestation": "attested",
            "identifiers": {k: v for k, v in
                            [("wikidata", qid), ("viaf", e["viaf"])] if v},
            "sources": wikidata_citation(qid),
            "status": "unverified",
            "notes": ("Draft seeded from Wikidata. Verify name forms, dates, "
                      "and see assignments against a graded source; the id "
                      "suffix year is provisional until first-tenure year is "
                      "known. Consecrator QID(s): "
                      + (", ".join(sorted(e["consecrators"])) or "none")),
        }
        if born:
            record["born"] = {"date": born}
        if e["died"]:
            died = wd_date(e["died"])
            if died:
                record["died"] = {"date": died}
        path = (DATA_DIR / "people" / jurisdiction /
                (pid.rsplit("/", 1)[-1] + ".yaml"))
        if write_yaml(path, record, dry_run):
            written += 1
    print(f"import_wikidata: {written} draft record(s) "
          f"({'dry run' if dry_run else 'written'}), all status: unverified")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--qids", nargs="+", help="Wikidata QIDs of persons")
    ap.add_argument("--position",
                    help="QID of an episcopal office; imports all P39 holders")
    ap.add_argument("--jurisdiction", default="unsorted",
                    help="jurisdiction slug for output paths/ids")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    qids = list(args.qids or [])
    if args.position:
        rows = sparql(POSITION_QUERY % {"position": args.position})
        qids += [r["item"]["value"].rsplit("/", 1)[-1] for r in rows]
    if not qids:
        ap.error("nothing to import: pass --qids and/or --position")

    import_people(sorted(set(qids)), args.jurisdiction, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
