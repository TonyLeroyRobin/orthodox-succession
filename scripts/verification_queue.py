#!/usr/bin/env python3
"""Human-verification queue.

Lists every `unverified` (and optionally `disputed`) record, grouped by
jurisdiction, with what a reviewer most needs to know: the citations it has,
the reliability of the best one, and common gaps (tenure without end, person
without any tenure, seeded lifespan dropped, overlap flags).

Only a human review against a graded source may promote a record to
`verified` — this tool never modifies anything.

Usage:
  python scripts/verification_queue.py                 # summary counts
  python scripts/verification_queue.py --jurisdiction cyprus
  python scripts/verification_queue.py --kind tenure --limit 40
  python scripts/verification_queue.py --all           # every jurisdiction
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import REPO_ROOT, load_all  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RANK = {"primary": 4, "official-list": 3, "scholarly": 2, "tradition": 1,
        "database": 0}


def jurisdiction_of(record_id: str) -> str:
    parts = (record_id or "").split("/")
    kind = parts[0] if parts else ""
    if kind in {"person", "see", "tenure", "consecration"} and len(parts) > 2:
        return parts[1]
    if kind == "jurisdiction":
        return parts[1] if len(parts) > 1 else "?"
    return "(global)"


def best_reliability(record) -> str:
    cits = record.get("sources") or []
    if not cits:
        return "NONE"
    return max(cits, key=lambda c: RANK.get(c.get("reliability"), -1)) \
        .get("reliability", "NONE")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jurisdiction", help="filter by jurisdiction slug")
    ap.add_argument("--kind", help="filter by record kind (person, tenure, ...)")
    ap.add_argument("--see", help="filter to records referencing this see id "
                                  "(tenures at it, plus the see itself)")
    ap.add_argument("--batch", help="filter to records added in this git "
                                    "commit (import-batch review)")
    ap.add_argument("--include-disputed", action="store_true")
    ap.add_argument("--limit", type=int, default=25,
                    help="max records listed per group (default 25)")
    ap.add_argument("--all", action="store_true",
                    help="list records for every jurisdiction, not just counts")
    args = ap.parse_args()

    records, problems = load_all()
    for path, msg in problems:
        print(f"PARSE PROBLEM {path}: {msg}")

    statuses = {"unverified"} | ({"disputed"} if args.include_disputed else set())
    queue = [r for r in records if r["data"].get("status") in statuses]

    if args.see:
        queue = [r for r in queue
                 if r["data"].get("see") == args.see
                 or r["data"].get("id") == args.see]

    if args.batch:
        import subprocess
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "show", "--diff-filter=A",
             "--name-only", "--format=", args.batch],
            capture_output=True, text=True)
        if out.returncode != 0:
            print(f"--batch: git could not resolve {args.batch!r}:"
                  f" {out.stderr.strip()}")
            return 1
        added = {line.strip().replace("/", "\\") for line in
                 out.stdout.splitlines() if line.strip()}
        added |= {p.replace("\\", "/") for p in added}
        queue = [r for r in queue
                 if str(Path(r["path"]).relative_to(REPO_ROOT)) in added
                 or str(Path(r["path"]).relative_to(REPO_ROOT)).replace(
                     "\\", "/") in added]
    tenured_people = {r["data"].get("person")
                      for r in records if r["kind"] == "tenure"}

    groups = defaultdict(list)
    for r in queue:
        jur = jurisdiction_of(r["data"].get("id", ""))
        if args.jurisdiction and jur != args.jurisdiction:
            continue
        if args.kind and r["kind"] != args.kind:
            continue
        groups[jur].append(r)

    total = sum(len(v) for v in groups.values())
    verified_n = sum(1 for r in records if r["data"].get("status") == "verified")
    print(f"Verification queue: {total} record(s) awaiting review "
          f"({verified_n} verified across the dataset).\n")

    for jur in sorted(groups):
        rs = groups[jur]
        by_kind = defaultdict(int)
        for r in rs:
            by_kind[r["kind"]] += 1
        kinds = ", ".join(f"{k}: {n}" for k, n in sorted(by_kind.items()))
        print(f"── {jur}  ({len(rs)} — {kinds})")
        if not (args.all or args.jurisdiction or args.kind):
            continue
        for r in rs[: args.limit]:
            d = r["data"]
            flags = []
            if r["kind"] == "tenure" and not d.get("to"):
                flags.append("no end date")
            if r["kind"] == "person" and d["id"] not in tenured_people:
                flags.append("no tenure record")
            if d.get("recognition"):
                flags.append("recognition-flagged")
            notes = d.get("notes") or ""
            if "NOT imported" in notes or "no start-date qualifier" in notes:
                flags.append("seed gaps")
            rel = best_reliability(d)
            path = Path(r["path"]).relative_to(REPO_ROOT)
            print(f"   [{rel:>13}] {d.get('id')}"
                  + (f"  ({'; '.join(flags)})" if flags else ""))
        if len(rs) > args.limit:
            print(f"   ... and {len(rs) - args.limit} more "
                  f"(raise --limit to see them)")
        print()

    if total:
        print("Promotion rule: a record becomes `verified` only after a HUMAN "
              "confirms it against a source graded better than "
              "tradition/database, adding a citation with locator (and "
              "archived_url for web sources). See docs/VERIFICATION.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
