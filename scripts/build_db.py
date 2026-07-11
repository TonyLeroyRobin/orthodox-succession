#!/usr/bin/env python3
"""YAML -> SQLite compiler.

build/succession.sqlite is a disposable, regenerated artifact. The YAML in
data/ is the single source of truth — never edit the database by hand.

Every record is stored whole (as JSON) in `records`; frequently-queried
fields are additionally broken out into typed tables, including the two
succession models kept strictly apart:

  tenures             see-succession (occupancy of thrones)
  consecration_edges  consecration-succession (principal | co-consecrator)
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BUILD_DIR, date_year, load_all  # noqa: E402

DB_PATH = BUILD_DIR / "succession.sqlite"

SCHEMA = """
CREATE TABLE records (
    id     TEXT PRIMARY KEY,
    kind   TEXT NOT NULL,
    status TEXT,
    json   TEXT NOT NULL
);
CREATE TABLE persons (
    id TEXT PRIMARY KEY, name TEXT, attestation TEXT,
    born_year INTEGER, died_year INTEGER, wikidata TEXT, status TEXT
);
CREATE TABLE sees (
    id TEXT PRIMARY KEY, name TEXT, modern_place TEXT,
    lat REAL, lon REAL, founded_year INTEGER, suppressed_year INTEGER, status TEXT
);
CREATE TABLE jurisdictions (
    id TEXT PRIMARY KEY, name TEXT, type TEXT, primatial_see TEXT, status TEXT
);
CREATE TABLE tenures (
    id TEXT PRIMARY KEY, person TEXT, see TEXT,
    from_value TEXT, from_year INTEGER, to_value TEXT, to_year INTEGER,
    end_reason TEXT, disputed_recognition INTEGER, status TEXT
);
CREATE TABLE consecrations (
    id TEXT PRIMARY KEY, consecrated TEXT, date_value TEXT, year INTEGER,
    place TEXT, status TEXT
);
CREATE TABLE consecration_edges (
    consecration_id TEXT, consecrator TEXT, consecrated TEXT,
    role TEXT CHECK (role IN ('principal', 'co-consecrator'))
);
CREATE TABLE events (
    id TEXT PRIMARY KEY, type TEXT, title TEXT,
    from_value TEXT, from_year INTEGER, to_value TEXT, to_year INTEGER,
    place TEXT, scope TEXT, status TEXT
);
CREATE TABLE participations (
    id TEXT PRIMARY KEY, person TEXT, event TEXT, role TEXT, status TEXT
);
CREATE TABLE works (
    id TEXT PRIMARY KEY, title TEXT, author TEXT, author_display TEXT,
    relation TEXT, attribution TEXT, genre TEXT, cpg TEXT, status TEXT
);
CREATE TABLE editions (
    work_id TEXT, idx INTEGER, type TEXT, language TEXT, translator TEXT,
    series TEXT, year INTEGER, locator TEXT, url TEXT, rights TEXT
);
CREATE TABLE sources (
    id TEXT PRIMARY KEY, type TEXT, title TEXT, author TEXT, year INTEGER,
    url TEXT, archived_url TEXT, status TEXT
);
CREATE TABLE traditions (
    id TEXT PRIMARY KEY, title TEXT, region TEXT, status TEXT
);
CREATE TABLE relationships (
    id TEXT PRIMARY KEY, from_person TEXT, to_person TEXT, type TEXT,
    date_value TEXT, status TEXT
);
CREATE TABLE citations (
    record_id TEXT, ref TEXT, reliability TEXT, locator TEXT, archived_url TEXT
);
CREATE INDEX idx_tenures_see ON tenures (see, from_year);
CREATE INDEX idx_tenures_person ON tenures (person);
CREATE INDEX idx_edges_consecrated ON consecration_edges (consecrated);
CREATE INDEX idx_citations_record ON citations (record_id);
"""


def main():
    records, problems = load_all()
    if problems:
        for path, msg in problems:
            print(f"ERROR {path}: {msg}", file=sys.stderr)
        return 1

    BUILD_DIR.mkdir(exist_ok=True)
    DB_PATH.unlink(missing_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)

    for rec in records:
        d, kind = rec["data"], rec["kind"]
        rid, status = d.get("id"), d.get("status")
        con.execute(
            "INSERT INTO records VALUES (?,?,?,?)",
            (rid, kind, status, json.dumps(d, ensure_ascii=False)),
        )
        for c in d.get("sources") or []:
            con.execute(
                "INSERT INTO citations VALUES (?,?,?,?,?)",
                (rid, c.get("ref"), c.get("reliability"), c.get("locator"),
                 c.get("archived_url")),
            )

        if kind == "person":
            con.execute(
                "INSERT INTO persons VALUES (?,?,?,?,?,?,?)",
                (rid,
                 (d.get("names") or {}).get("monastic"),
                 d.get("attestation"),
                 date_year((d.get("born") or {}).get("date")),
                 date_year((d.get("died") or {}).get("date")),
                 (d.get("identifiers") or {}).get("wikidata"),
                 status),
            )
        elif kind == "see":
            loc = d.get("location") or {}
            con.execute(
                "INSERT INTO sees VALUES (?,?,?,?,?,?,?,?)",
                (rid, d.get("name"), loc.get("modern_place"),
                 loc.get("lat"), loc.get("lon"),
                 date_year((d.get("founded") or {}).get("date")),
                 date_year((d.get("suppressed") or {}).get("date")),
                 status),
            )
        elif kind == "jurisdiction":
            con.execute(
                "INSERT INTO jurisdictions VALUES (?,?,?,?,?)",
                (rid, d.get("name"), d.get("type"), d.get("primatial_see"), status),
            )
        elif kind == "tenure":
            disputed = int(any(
                e.get("status") in ("disputed", "rival-claimant", "not-recognized")
                for e in d.get("recognition") or []
            ))
            con.execute(
                "INSERT INTO tenures VALUES (?,?,?,?,?,?,?,?,?,?)",
                (rid, d.get("person"), d.get("see"),
                 (d.get("from") or {}).get("value"), date_year(d.get("from")),
                 (d.get("to") or {}).get("value"), date_year(d.get("to")),
                 d.get("end_reason"), disputed, status),
            )
        elif kind == "consecration":
            con.execute(
                "INSERT INTO consecrations VALUES (?,?,?,?,?,?)",
                (rid, d.get("consecrated"), (d.get("date") or {}).get("value"),
                 date_year(d.get("date")), d.get("place"), status),
            )
            if d.get("principal_consecrator"):
                con.execute(
                    "INSERT INTO consecration_edges VALUES (?,?,?,'principal')",
                    (rid, d["principal_consecrator"], d.get("consecrated")),
                )
            for co in d.get("co_consecrators") or []:
                con.execute(
                    "INSERT INTO consecration_edges VALUES (?,?,?,'co-consecrator')",
                    (rid, co, d.get("consecrated")),
                )
        elif kind == "event":
            dr = d.get("date") or {}
            con.execute(
                "INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?)",
                (rid, d.get("type"), d.get("title"),
                 (dr.get("from") or {}).get("value"), date_year(dr.get("from")),
                 (dr.get("to") or {}).get("value"), date_year(dr.get("to")),
                 d.get("place"), d.get("scope"), status),
            )
        elif kind == "participation":
            con.execute(
                "INSERT INTO participations VALUES (?,?,?,?,?)",
                (rid, d.get("person"), d.get("event"), d.get("role"), status),
            )
        elif kind == "work":
            con.execute(
                "INSERT INTO works VALUES (?,?,?,?,?,?,?,?,?)",
                (rid, d.get("title"), d.get("author"), d.get("author_display"),
                 d.get("relation"), d.get("attribution"), d.get("genre"),
                 d.get("cpg"), status),
            )
            for idx, ed in enumerate(d.get("editions") or []):
                con.execute(
                    "INSERT INTO editions VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (rid, idx, ed.get("type"), ed.get("language"),
                     ed.get("translator"), ed.get("series"), ed.get("year"),
                     ed.get("locator"), ed.get("url"), ed.get("rights")),
                )
        elif kind == "source":
            con.execute(
                "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?)",
                (rid, d.get("type"), d.get("title"), d.get("author"),
                 d.get("year"), d.get("url"), d.get("archived_url"), status),
            )
        elif kind == "tradition":
            con.execute(
                "INSERT INTO traditions VALUES (?,?,?,?)",
                (rid, d.get("title"), d.get("region"), status),
            )
        elif kind == "relationship":
            con.execute(
                "INSERT INTO relationships VALUES (?,?,?,?,?,?)",
                (rid, d.get("from"), d.get("to"), d.get("type"),
                 (d.get("date") or {}).get("value"), status),
            )

    con.commit()
    n = con.execute("SELECT COUNT(*) FROM records").fetchone()[0]
    con.close()
    print(f"build_db: wrote {n} record(s) to {DB_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
