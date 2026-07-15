#!/usr/bin/env python3
"""Occupancy gap report (DATA_COMPLETION §5 + ROADMAP_ADDENDUM A2).

For every see with tenure records: the occupancy timeline with gaps larger
than GAP_YEARS flagged (including the tail gap up to the present for
non-suppressed sees), tenure counts by verification status, sees whose
apostolic_founder is absent or unsourced, and sees missing location data.

Info-level only — always exits 0; wired into the build chain after export.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import REPO_ROOT, date_year, load_all  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GAP_YEARS = 2
PRESENT = 2026  # tail-gap horizon; update opportunistically


def main():
    records, _ = load_all()
    sees = {r["data"]["id"]: r["data"] for r in records
            if r["kind"] == "see" and r["data"].get("id")}
    tenures_by_see = defaultdict(list)
    for r in records:
        if r["kind"] != "tenure":
            continue
        d = r["data"]
        fy = date_year(d.get("from"))
        if d.get("see") and fy is not None:
            ty = date_year(d.get("to"))
            tenures_by_see[d["see"]].append((fy, ty, d))

    total_gaps = 0
    print("Gap report (info): occupancy gaps > "
          f"{GAP_YEARS} years, per see\n")

    for see_id in sorted(tenures_by_see):
        spans = sorted(tenures_by_see[see_id],
                       key=lambda s: (s[0], s[1] if s[1] is not None
                                      else s[0]))
        statuses = defaultdict(int)
        for _, _, d in spans:
            statuses[d.get("status", "?")] += 1
        counts = ", ".join(f"{n} {s}" for s, n in sorted(statuses.items()))
        print(f"== {see_id} — {len(spans)} tenure(s) ({counts})")

        gaps = []
        cursor_end = None
        for fy, ty, d in spans:
            if cursor_end is not None and fy - cursor_end > GAP_YEARS:
                gaps.append((cursor_end, fy))
            end = ty if ty is not None else fy
            cursor_end = max(cursor_end or end, end)
        # tail gap: only when the last known occupancy ended in the past
        # and the see is not suppressed
        see = sees.get(see_id, {})
        suppressed = bool((see.get("suppressed") or {}).get("date"))
        open_ended = any(ty is None and fy > 1900 for fy, ty, _ in spans)
        if (cursor_end is not None and not suppressed and not open_ended
                and PRESENT - cursor_end > GAP_YEARS):
            gaps.append((cursor_end, PRESENT))

        if gaps:
            total_gaps += len(gaps)
            line = "   " + "   ".join(
                f"GAP {a:04d}–{b:04d} ({b - a}y)" +
                ("  [to present]" if b == PRESENT else "")
                for a, b in gaps)
            print(line)
        print()

    no_location = [sid for sid, s in sorted(sees.items())
                   if not (s.get("location") or {}).get("lat")]
    af_unsourced = []
    for sid, s in sorted(sees.items()):
        af = s.get("apostolic_founder")
        afs = s.get("apostolic_founders") or []
        if afs:
            if any(not e.get("sources") for e in afs):
                af_unsourced.append(sid)
        elif not af or not af.get("sources"):
            af_unsourced.append(sid + ("" if af else "  (no founder at all)"))

    print(f"-- summary: {len(tenures_by_see)} see(s) with tenures, "
          f"{total_gaps} flagged gap(s)")
    print(f"-- sees missing location ({len(no_location)}): "
          + (", ".join(no_location) or "none"))
    print(f"-- sees without sourced apostolic_founder ({len(af_unsourced)}):")
    for s in af_unsourced:
        print(f"     {s}")

    # ---- council leads not yet cataloged (R5 standing rule) ----------------
    leads_doc = REPO_ROOT / "docs" / "COUNCIL_LEADS.md"
    open_leads = []
    if leads_doc.exists():
        for line in leads_doc.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\|([^|]+)\|([^|]+)\|[^|]+\|([^|]*)\|\s*$", line)
            if not m:
                continue
            lead, guess, closed = (g.strip() for g in m.groups())
            if lead in ("Lead", "---") or lead.startswith("-"):
                continue
            if not closed:
                open_leads.append(f"{lead} ({guess})")
    print(f"-- council leads not yet cataloged ({len(open_leads)}) "
          f"[docs/COUNCIL_LEADS.md]:")
    for lead in open_leads:
        print(f"     {lead}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
