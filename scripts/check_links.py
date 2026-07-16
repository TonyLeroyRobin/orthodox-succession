#!/usr/bin/env python3
"""Link-rot checker (P4, promoted from BACKLOG).

Validates every LIVE url in the dataset — Source records' `url` and Works'
edition `url`s — and reports dead links, suggesting the stored archived_url
as the replacement. REPORTS ONLY; never auto-replaces. Network-bound and
slow by design (polite rate limiting), so it is a separate make target
(`make check-links`), not part of the default build chain.
"""

from __future__ import annotations

import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load_all  # noqa: E402

UA = {"User-Agent": "orthodox-succession-db link checker "
                    "(https://github.com/TonyLeroyRobin/orthodox-succession)"}
DELAY = 1.0
TIMEOUT = 20


def check(url):
    """Return (ok, detail). HEAD first, GET on 405/403-ish fallback."""
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, headers=UA, method=method)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return True, f"{r.status}"
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code in (403, 405, 501):
                continue
            return (e.code < 400), f"HTTP {e.code}"
        except Exception as e:  # noqa: BLE001
            if method == "HEAD":
                continue
            return False, type(e).__name__
    return False, "unreachable"


def main():
    records, _ = load_all()
    targets = []  # (record_id, where, url, archived_url)
    for r in records:
        d = r["data"]
        if r["kind"] == "source" and d.get("url"):
            targets.append((d.get("id"), "source.url", d["url"],
                            d.get("archived_url")))
        elif r["kind"] == "work":
            for i, ed in enumerate(d.get("editions") or []):
                if ed.get("url"):
                    targets.append((d.get("id"), f"edition #{i + 1}",
                                    ed["url"], ed.get("archived_url")))

    seen = {}
    dead = 0
    print(f"check_links: {len(targets)} live URL reference(s), "
          f"{len(set(t[2] for t in targets))} distinct")
    for rid, where, url, arch in targets:
        if url not in seen:
            seen[url] = check(url)
            time.sleep(DELAY)
        ok, detail = seen[url]
        if not ok:
            dead += 1
            print(f"DEAD   {rid} ({where}): {url} [{detail}]")
            print(f"       suggested replacement: "
                  f"{arch or '(no archived_url stored!)'}")
    print(f"check_links: {dead} dead reference(s) "
          f"across {sum(1 for v in seen.values() if not v[0])} distinct URL(s)")

    # Q3.4: persist the report so the build/site can surface it
    import datetime
    import json
    report = {
        "checked_at": datetime.datetime.now(datetime.timezone.utc)
                      .strftime("%Y-%m-%d %H:%M UTC"),
        "targets": len(targets),
        "distinct": len(seen),
        "dead": [
            {"id": rid, "where": where, "url": url,
             "suggested": arch or None,
             "detail": seen[url][1]}
            for rid, where, url, arch in targets if not seen[url][0]
        ],
    }
    out = Path(__file__).resolve().parent.parent / "build" / "link-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"check_links: report -> {out}")
    return 0  # report only — never gates


if __name__ == "__main__":
    sys.exit(main())
