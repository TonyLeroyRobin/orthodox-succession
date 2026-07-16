"""Shared loading utilities for the Orthodox Apostolic Succession Database.

YAML files in data/ are the single source of truth. This module walks the data
tree, loads every record, and derives the ID each file is *expected* to carry
from its path, so validate.py can enforce id-matches-path.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
SCHEMA_DIR = REPO_ROOT / "schemas"
BUILD_DIR = REPO_ROOT / "build"

# kind -> (data subdirectory, schema file, nesting)
# nesting: "jurisdiction" = one subdirectory level (per jurisdiction), "flat" = none,
# "two" = fixed two-level path segment (events).
KINDS = {
    "jurisdiction": ("jurisdictions", "jurisdiction.json", "flat"),
    "see": ("sees", "see.json", "jurisdiction"),
    "person": ("people", "person.json", "jurisdiction"),
    "tenure": ("tenures", "tenure.json", "jurisdiction"),
    "consecration": ("consecrations", "consecration.json", "jurisdiction"),
    "event": ("events", "event.json", "two"),
    "participation": ("participations", "participation.json", "flat"),
    "work": ("works", "work.json", "flat"),
    "tradition": ("traditions", "tradition.json", "flat"),
    "source": ("sources", "source.json", "flat"),
    "relationship": ("relationships", "relationship.json", "flat"),
    "controversy": ("controversies", "controversy.json", "flat"),
}


def _normalize(node):
    """PyYAML parses unquoted ISO dates into date objects; convert back to
    ISO strings so schema validation and downstream code see strings."""
    if isinstance(node, dict):
        return {k: _normalize(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_normalize(v) for v in node]
    if isinstance(node, (datetime.datetime, datetime.date)):
        return node.isoformat()
    return node


def expected_id(kind: str, path: Path) -> str:
    """Derive the ID a record file must carry from its location."""
    subdir, _, nesting = KINDS[kind]
    rel = path.relative_to(DATA_DIR / subdir).with_suffix("")
    parts = rel.parts
    if nesting == "flat":
        return f"{kind}/{parts[-1]}"
    if nesting == "jurisdiction":
        return f"{kind}/{'/'.join(parts)}"
    if nesting == "two":
        # data/events/councils/<slug> -> event/council/<slug>
        # data/events/context/<slug>  -> event/context/<slug>
        segment = {"councils": "council", "context": "context"}.get(parts[0], parts[0])
        return f"{kind}/{segment}/{'/'.join(parts[1:])}"
    raise ValueError(nesting)


def load_all():
    """Load every YAML record under data/.

    Returns (records, problems) where records is a list of dicts:
    {kind, path, expected_id, data} and problems is a list of
    (path, message) for files that failed to parse or are misplaced.
    """
    records, problems = [], []
    for kind, (subdir, _, _) in KINDS.items():
        base = DATA_DIR / subdir
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.yaml")) + sorted(base.rglob("*.yml")):
            try:
                with open(path, encoding="utf-8") as fh:
                    data = _normalize(yaml.safe_load(fh))
            except yaml.YAMLError as exc:
                problems.append((path, f"YAML parse error: {exc}"))
                continue
            if not isinstance(data, dict):
                problems.append((path, "record is not a mapping"))
                continue
            records.append(
                {
                    "kind": kind,
                    "path": path,
                    "expected_id": expected_id(kind, path),
                    "data": data,
                }
            )
    return records, problems


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

# Chronology-check slack, in years, per stated precision.
PRECISION_SLACK_YEARS = {
    "day": 0,
    "month": 0,
    "year": 1,
    "decade": 10,
    "century": 100,
    "circa": 25,
    "disputed": None,  # skip chronology checks entirely
}


def parse_date_value(value: str):
    """'0431-06-22' -> (431, 6, 22); missing parts default to mid-range so
    comparisons are fair for partial dates. Returns None if unparseable."""
    if not isinstance(value, str):
        return None
    neg = value.startswith("-")
    body = value[1:] if neg else value
    parts = body.split("-")
    try:
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 6
        day = int(parts[2]) if len(parts) > 2 else 15
    except (ValueError, IndexError):
        return None
    if neg:
        year = -year
    return (year, month, day)


def date_ordinal(date_obj) -> float | None:
    """Approximate a date object as a fractional year for comparisons.
    Returns None if the date is missing, unparseable, or precision=disputed."""
    if not isinstance(date_obj, dict):
        return None
    if PRECISION_SLACK_YEARS.get(date_obj.get("precision"), 0) is None:
        return None
    parsed = parse_date_value(date_obj.get("value"))
    if parsed is None:
        return None
    y, m, d = parsed
    return y + (m - 1) / 12 + (d - 1) / 365


def date_slack(date_obj) -> float:
    """Slack in years implied by a date's precision (0 if absent)."""
    if not isinstance(date_obj, dict):
        return 0.0
    slack = PRECISION_SLACK_YEARS.get(date_obj.get("precision"), 0)
    return float(slack or 0)


def date_year(date_obj):
    """Bare year of a date object, or None."""
    if not isinstance(date_obj, dict):
        return None
    parsed = parse_date_value(date_obj.get("value"))
    return parsed[0] if parsed else None
