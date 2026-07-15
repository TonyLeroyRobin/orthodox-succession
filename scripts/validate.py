#!/usr/bin/env python3
"""Full validation suite for the Orthodox Apostolic Succession Database.

Implements the minimum rule set of KICKOFF.md §6:

 1. Every file parses; every record matches its JSON Schema; every ID is
    unique and matches its path.
 2. Referential integrity: every person/see/event/source/jurisdiction
    reference resolves.
 3. Chronology: death >= birth; tenure within lifespan (+/- precision slack);
    tenure within the see's existence window; consecration before first
    tenure and within lifespan; participation within lifespan.
 4. Consecration sanity: no self-consecration; consecrators plausibly alive;
    no cycles in the consecration graph (DAG check).
 5. Overlapping tenures on one see require a recognition qualifier on at
    least one. (Tenures with an unknown end are treated as point intervals,
    not open-ended, to avoid false positives on ancient data.)
 6. Sources: every record has >= 1 source ref; every web source has an
    archived_url; every `verified` record has >= 1 source with reliability
    better than `tradition` (or `database`).
 7. Works: near-duplicate detector per author (warn); public-domain editions
    should carry a URL (warn).
 8. Context events: hard ceiling 300.
 9. Corroborations (info): tenures supported by council signatures.

Exit status is non-zero on any error, so CI can gate pull requests.
"""

from __future__ import annotations

import datetime
import difflib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    DATA_DIR,
    KINDS,
    REPO_ROOT,
    SCHEMA_DIR,
    date_ordinal,
    date_slack,
    date_year,
    load_all,
)

from jsonschema import Draft202012Validator  # noqa: E402
from referencing import Registry, Resource  # noqa: E402

CONTEXT_EVENT_CEILING = 300
GOOD_RELIABILITY = {"primary", "official-list", "scholarly"}
EPS = 0.01  # comparison epsilon in fractional years


class Reporter:
    def __init__(self):
        self.errors, self.warnings, self.infos = [], [], []

    def _rel(self, path):
        try:
            return str(Path(path).relative_to(REPO_ROOT))
        except (ValueError, TypeError):
            return str(path)

    def error(self, path, msg):
        self.errors.append(f"ERROR  {self._rel(path)}: {msg}")

    def warn(self, path, msg):
        self.warnings.append(f"WARN   {self._rel(path)}: {msg}")

    def info(self, path, msg):
        self.infos.append(f"INFO   {self._rel(path)}: {msg}")

    def dump(self):
        for line in self.errors + self.warnings + self.infos:
            print(line)
        print(
            f"\nValidation: {len(self.errors)} error(s), "
            f"{len(self.warnings)} warning(s), {len(self.infos)} info."
        )
        return 1 if self.errors else 0


def build_validators():
    """Load every schema in schemas/ into a referencing Registry and return
    {kind: Draft202012Validator}."""
    resources = []
    schemas = {}
    for schema_path in SCHEMA_DIR.glob("*.json"):
        with open(schema_path, encoding="utf-8") as fh:
            contents = json.load(fh)
        resources.append((contents["$id"], Resource.from_contents(contents)))
        schemas[schema_path.name] = contents
    registry = Registry().with_resources(resources)
    validators = {}
    for kind, (_, schema_file, _) in KINDS.items():
        validators[kind] = Draft202012Validator(schemas[schema_file], registry=registry)
    return validators


# ---------------------------------------------------------------------------
# Reference extraction (rule 2)
# ---------------------------------------------------------------------------

def iter_refs(kind, data):
    """Yield (description, referenced_id) pairs for every cross-record
    reference a record makes. Skips absent fields."""

    def dates_ok(x):  # helper no-op to keep structure obvious
        return x

    def citations(cits, where):
        for c in cits or []:
            if isinstance(c, dict) and c.get("ref"):
                yield (f"{where} source ref", c["ref"])

    yield from citations(data.get("sources"), "record")

    for entry in data.get("recognition") or []:
        by = entry.get("by")
        if by and by != "all":
            yield ("recognition.by", by)

    if kind == "tenure":
        yield ("person", data.get("person"))
        yield ("see", data.get("see"))
    elif kind == "consecration":
        yield ("consecrated", data.get("consecrated"))
        if data.get("principal_consecrator"):
            yield ("principal_consecrator", data["principal_consecrator"])
        for p in data.get("co_consecrators") or []:
            yield ("co_consecrator", p)
    elif kind == "see":
        for h in data.get("jurisdiction_history") or []:
            yield ("jurisdiction_history.jurisdiction", h.get("jurisdiction"))
        if (data.get("founded") or {}).get("founded_from"):
            yield ("founded.founded_from", data["founded"]["founded_from"])
        af = data.get("apostolic_founder") or {}
        if af.get("person"):
            yield ("apostolic_founder.person", af["person"])
        yield from citations(af.get("sources"), "apostolic_founder")
        for af2 in data.get("apostolic_founders") or []:
            if af2.get("person"):
                yield ("apostolic_founders.person", af2["person"])
            yield from citations(af2.get("sources"), "apostolic_founders")
    elif kind == "jurisdiction":
        if data.get("primatial_see"):
            yield ("primatial_see", data["primatial_see"])
        succ = (data.get("dissolved") or {}).get("successor")
        if succ and succ != "none-in-scope":
            yield ("dissolved.successor", succ)
        for a in data.get("autocephaly") or []:
            gb = a.get("granted_by", "")
            # granted_by may be free text; check only when it looks like an id
            if re.match(r"^(jurisdiction|event)/", gb):
                yield ("autocephaly.granted_by", gb)
            for entry in a.get("recognition") or []:
                by = entry.get("by")
                if by and by != "all":
                    yield ("autocephaly.recognition.by", by)
    elif kind == "work":
        if data.get("author"):
            yield ("author", data["author"])
        for p in data.get("subject_of") or []:
            yield ("subject_of", p)
    elif kind == "participation":
        yield ("person", data.get("person"))
        yield ("event", data.get("event"))
    elif kind == "tradition":
        for p in data.get("persons") or []:
            yield ("persons", p)
    elif kind == "relationship":
        yield ("from", data.get("from"))
        yield ("to", data.get("to"))
    elif kind == "event":
        for a in data.get("affected") or []:
            yield ("affected", a)


# ---------------------------------------------------------------------------
# Chronology helpers (rule 3)
# ---------------------------------------------------------------------------

def before(a, b, extra_slack=0.0):
    """True unless a is definitely AFTER b (allowing both dates' precision
    slack). Missing/disputed dates always pass."""
    oa, ob = date_ordinal(a), date_ordinal(b)
    if oa is None or ob is None:
        return True
    return oa <= ob + date_slack(a) + date_slack(b) + extra_slack + EPS


def lifespan(person):
    born = (person.get("born") or {}).get("date")
    died = (person.get("died") or {}).get("date")
    return born, died


def main():
    rep = Reporter()
    records, problems = load_all()
    for path, msg in problems:
        rep.error(path, msg)

    validators = build_validators()

    # ---- rule 1: schema, id uniqueness, id-matches-path -------------------
    by_id = {}
    for rec in records:
        data, path, kind = rec["data"], rec["path"], rec["kind"]
        for err in validators[kind].iter_errors(data):
            loc = "/".join(str(p) for p in err.absolute_path) or "(root)"
            rep.error(path, f"schema: {loc}: {err.message}")
        rid = data.get("id")
        if rid:
            if rid != rec["expected_id"]:
                rep.error(path, f"id {rid!r} does not match path (expected {rec['expected_id']!r})")
            if rid in by_id:
                rep.error(path, f"duplicate id {rid!r} (also in {by_id[rid]['path']})")
            else:
                by_id[rid] = rec

    # ---- rule 8: context event ceiling ------------------------------------
    context_events = [
        r for r in records
        if r["kind"] == "event" and r["data"].get("type") == "context"
    ]
    if len(context_events) > CONTEXT_EVENT_CEILING:
        rep.error(DATA_DIR / "events" / "context",
                  f"{len(context_events)} context events exceed the hard ceiling "
                  f"of {CONTEXT_EVENT_CEILING}")

    # ---- rule 2: referential integrity -------------------------------------
    for rec in records:
        for desc, ref in iter_refs(rec["kind"], rec["data"]):
            if ref and ref not in by_id:
                rep.error(rec["path"], f"unresolved reference ({desc}): {ref!r}")

    persons = {r["data"]["id"]: r for r in records
               if r["kind"] == "person" and r["data"].get("id")}
    sees = {r["data"]["id"]: r for r in records
            if r["kind"] == "see" and r["data"].get("id")}
    events = {r["data"]["id"]: r for r in records
              if r["kind"] == "event" and r["data"].get("id")}
    tenures = [r for r in records if r["kind"] == "tenure"]
    consecrations = [r for r in records if r["kind"] == "consecration"]
    participations = [r for r in records if r["kind"] == "participation"]
    sources_by_id = {r["data"]["id"]: r for r in records
                     if r["kind"] == "source" and r["data"].get("id")}

    # first-tenure start per person, for consecration ordering
    first_tenure_start = {}
    for t in tenures:
        d = t["data"]
        start = date_ordinal(d.get("from"))
        pid = d.get("person")
        if pid and start is not None:
            cur = first_tenure_start.get(pid)
            if cur is None or start < cur[0]:
                first_tenure_start[pid] = (start, d.get("from"))

    # ---- rule 3: chronology -------------------------------------------------
    for pid, rec in persons.items():
        born, died = lifespan(rec["data"])
        if not before(born, died):
            rep.error(rec["path"], "death precedes birth")

    for t in tenures:
        d, path = t["data"], t["path"]
        if not before(d.get("from"), d.get("to")):
            rep.error(path, "tenure ends before it begins")
        p = persons.get(d.get("person"))
        if p:
            born, died = lifespan(p["data"])
            if not before(born, d.get("from")):
                rep.error(path, "tenure begins before the person's birth")
            if not before(d.get("from"), died):
                rep.error(path, "tenure begins after the person's death")
            if not before(d.get("to"), died, extra_slack=1.0):
                rep.error(path, "tenure ends after the person's death")
        s = sees.get(d.get("see"))
        if s:
            founded = (s["data"].get("founded") or {}).get("date")
            suppressed = (s["data"].get("suppressed") or {}).get("date")
            if not before(founded, d.get("from")):
                rep.error(path, "tenure begins before the see was founded")
            if suppressed and not before(d.get("to") or d.get("from"), suppressed):
                rep.error(path, "tenure extends past the see's suppression")

    for c in consecrations:
        d, path = c["data"], c["path"]
        p = persons.get(d.get("consecrated"))
        if p:
            born, died = lifespan(p["data"])
            if not before(born, d.get("date")):
                rep.error(path, "consecration precedes the person's birth")
            if not before(d.get("date"), died):
                rep.error(path, "consecration follows the person's death")
        ft = first_tenure_start.get(d.get("consecrated"))
        if ft and not before(d.get("date"), ft[1]):
            rep.error(path, "consecration follows the person's first tenure")

    for pt in participations:
        d, path = pt["data"], pt["path"]
        ev = events.get(d.get("event"))
        p = persons.get(d.get("person"))
        if ev and p:
            edate = (ev["data"].get("date") or {}).get("from")
            born, died = lifespan(p["data"])
            role = d.get("role")
            if role != "posthumously-condemned":
                if not before(born, edate):
                    rep.error(path, "participation precedes the person's birth")
                if not before(edate, died):
                    rep.error(path, "participation follows the person's death")

    # ---- rule 4: consecration sanity ---------------------------------------
    edges = defaultdict(set)  # consecrator -> {consecrated}
    for c in consecrations:
        d, path = c["data"], c["path"]
        target = d.get("consecrated")
        consecrators = []
        if d.get("principal_consecrator"):
            consecrators.append(d["principal_consecrator"])
        consecrators.extend(d.get("co_consecrators") or [])
        for k in consecrators:
            if k == target:
                rep.error(path, "self-consecration")
                continue
            edges[k].add(target)
            kp = persons.get(k)
            if kp:
                born, died = lifespan(kp["data"])
                if not before(born, d.get("date")):
                    rep.error(path, f"consecrator {k} not yet born at the consecration date")
                if not before(d.get("date"), died):
                    rep.error(path, f"consecrator {k} already dead at the consecration date")

    # DAG check: iterative three-color DFS over the consecration graph
    color = {}  # 0 unseen implicit, 1 in-stack, 2 done
    for start in list(edges):
        if color.get(start):
            continue
        stack = [(start, iter(edges.get(start, ())))]
        color[start] = 1
        while stack:
            node, it = stack[-1]
            advanced = False
            for nxt in it:
                if color.get(nxt) == 1:
                    rep.error(DATA_DIR / "consecrations",
                              f"cycle in the consecration graph involving {nxt}")
                elif not color.get(nxt):
                    color[nxt] = 1
                    stack.append((nxt, iter(edges.get(nxt, ()))))
                    advanced = True
                    break
            if not advanced:
                color[node] = 2
                stack.pop()

    # ---- veneration (DATA_COMPLETION §1) and relationships (ADDENDUM A1) ---
    for pid, rec in persons.items():
        ven = rec["data"].get("veneration")
        if not ven:
            continue  # absent block = "not yet assessed" — fine
        if not ven.get("sources"):
            rep.error(rec["path"],
                      "veneration block present but has no sources — presence "
                      "is an assessed claim (absence means not-yet-assessed)")
        for c in ven.get("sources") or []:
            if c.get("ref") and c["ref"] not in by_id:
                rep.error(rec["path"],
                          f"unresolved veneration source ref: {c['ref']!r}")
        for entry in ven.get("recognition") or []:
            by = entry.get("by", "")
            if by.startswith("jurisdiction:"):
                jid = by.split(":", 1)[1]
                if jid not in by_id:
                    rep.error(rec["path"],
                              f"unresolved veneration recognizer: {jid!r}")
        for fd in ven.get("feast_days") or []:
            md = fd.get("month_day", "")
            try:
                datetime.date(2000, int(md[:2]), int(md[3:5]))  # 2000 is leap
            except (ValueError, IndexError):
                rep.error(rec["path"], f"invalid feast month_day {md!r}")

    for rel in (r for r in records if r["kind"] == "relationship"):
        d, path = rel["data"], rel["path"]
        if d.get("type") == "consecrated":
            rep.error(path,
                      "relationship type 'consecrated' is reserved for "
                      "exports — consecration lineage lives in Consecration "
                      "records only (no forked truth)")
        if d.get("from") and d.get("from") == d.get("to"):
            rep.error(path, "relationship from == to")
        rdate = d.get("date")
        if rdate:
            for role in ("from", "to"):
                p = persons.get(d.get(role))
                if p:
                    born, died = lifespan(p["data"])
                    if not before(born, rdate):
                        rep.error(path, f"relationship date precedes the "
                                        f"birth of the '{role}' person")
                    if not before(rdate, died):
                        rep.error(path, f"relationship date follows the "
                                        f"death of the '{role}' person")

    # ---- P1 admission rule: non-bishop persons must connect to the corpus --
    # (PERSONS_LIBRARY_CONTROVERSIES §P1.2, error level.) A person whose
    # explicit role is not bishop must be reachable via a Work
    # (author/subject_of), a Participation, a Relationship (either
    # direction), or citation as apostolic founder on a See / person
    # reference in a Tradition. Absent role means bishop (pre-P1 default).
    # NOTE: Jurisdiction records have no structured founder/evangelizer
    # person field today; that leg of the rule activates if one is added.
    connected = set()
    for rec in records:
        d, k = rec["data"], rec["kind"]
        if k == "work":
            if d.get("author"):
                connected.add(d["author"])
            for p in d.get("subject_of") or []:
                connected.add(p)
        elif k == "participation":
            if d.get("person"):
                connected.add(d["person"])
        elif k == "relationship":
            for f in ("from", "to"):
                if d.get(f):
                    connected.add(d[f])
        elif k == "see":
            af = d.get("apostolic_founder") or {}
            if af.get("person"):
                connected.add(af["person"])
            for af2 in d.get("apostolic_founders") or []:
                if af2.get("person"):
                    connected.add(af2["person"])
        elif k == "tradition":
            for p in d.get("persons") or []:
                connected.add(p)
    for pid, rec in persons.items():
        role = rec["data"].get("role", "bishop")
        if role != "bishop" and pid not in connected:
            rep.error(
                rec["path"],
                f"non-bishop person (role: {role}) has no corpus connection — "
                "the admission rule requires a Work (author or subject_of), a "
                "Participation, a Relationship, or citation as apostolic "
                "founder on a See / person reference in a Tradition "
                "(PERSONS_LIBRARY_CONTROVERSIES §P1)",
            )

    # ---- rule 5: overlapping tenures need a recognition qualifier ----------
    by_see = defaultdict(list)
    for t in tenures:
        if t["data"].get("see"):
            by_see[t["data"]["see"]].append(t)
    for see_id, ts in by_see.items():
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                a, b = ts[i]["data"], ts[j]["data"]
                a0, a1 = date_ordinal(a.get("from")), date_ordinal(a.get("to") or a.get("from"))
                b0, b1 = date_ordinal(b.get("from")), date_ordinal(b.get("to") or b.get("from"))
                if None in (a0, a1, b0, b1):
                    continue
                if a0 < b1 - EPS and b0 < a1 - EPS:  # strict interval overlap
                    if not (a.get("recognition") or b.get("recognition")):
                        rep.error(
                            ts[j]["path"],
                            f"tenure overlaps {a.get('id')} on {see_id} and neither "
                            f"carries a recognition qualifier",
                        )

    # ---- rule 6: sources -----------------------------------------------------
    for rec in records:
        d, path, kind = rec["data"], rec["path"], rec["kind"]
        if kind == "source":
            if d.get("type") == "web" and not d.get("archived_url"):
                rep.error(path, "web source without archived_url (archive.org snapshot is mandatory)")
            continue
        cits = d.get("sources") or []
        if not cits:
            rep.error(path, "record has no sources")
            continue
        for c in cits:
            src = sources_by_id.get(c.get("ref"))
            if src and src["data"].get("type") == "web":
                if not (c.get("archived_url") or src["data"].get("archived_url")):
                    rep.error(path, f"citation of web source {c.get('ref')} has no archived_url")
        if d.get("status") == "verified":
            if not any(c.get("reliability") in GOOD_RELIABILITY for c in cits):
                rep.error(
                    path,
                    "verified record has no source better than tradition/database — "
                    "it must remain unverified or be flagged disputed",
                )

    # ---- rule 7: work hygiene (warn) ----------------------------------------
    works = [r for r in records if r["kind"] == "work"]
    def norm_title(t):
        return re.sub(r"[^a-z0-9 ]", "", (t or "").lower()).strip()
    by_author = defaultdict(list)
    for w in works:
        by_author[w["data"].get("author") or w["data"].get("author_display")].append(w)
    for author, ws in by_author.items():
        for i in range(len(ws)):
            for j in range(i + 1, len(ws)):
                t1, t2 = norm_title(ws[i]["data"].get("title")), norm_title(ws[j]["data"].get("title"))
                if t1 and t2 and difflib.SequenceMatcher(None, t1, t2).ratio() > 0.85:
                    rep.warn(ws[j]["path"],
                             f"possible duplicate of {ws[i]['data'].get('id')} "
                             f"(same author, near-identical title) — one Work, many Editions")
    for w in works:
        for idx, ed in enumerate(w["data"].get("editions") or []):
            if ed.get("rights") == "public-domain" and not ed.get("url"):
                rep.warn(w["path"], f"edition #{idx + 1} is public-domain but has no URL")

    # ---- rule 9: corroborations (info) ---------------------------------------
    corroborations = 0
    for pt in participations:
        d = pt["data"]
        if d.get("role") not in {"signed", "presided"}:
            continue
        if not any(c.get("reliability") == "primary" for c in d.get("sources") or []):
            continue
        ev = events.get(d.get("event"))
        if not ev:
            continue
        edate = (ev["data"].get("date") or {}).get("from")
        for t in tenures:
            td = t["data"]
            if td.get("person") != d.get("person"):
                continue
            starts_before = before(td.get("from"), edate)
            ends_after = td.get("to") is None or before(edate, td.get("to"))
            if starts_before and ends_after:
                corroborations += 1
                rep.info(
                    t["path"],
                    f"tenure {td.get('id')} corroborated by council signature "
                    f"{d.get('id')} ({ev['data'].get('title')})",
                )
    if participations:
        rep.info(DATA_DIR, f"{corroborations} council-signature corroboration(s) found")

    return rep.dump()


if __name__ == "__main__":
    sys.exit(main())
