#!/usr/bin/env python3
"""SQLite -> GraphML + JSON exporter for the dashboard.

Outputs (all disposable, all under build/):

  build/graph.graphml       persons + sees as nodes; tenure edges
                            (person->see) and consecration edges
                            (consecrator->consecrated, principal vs
                            co-consecrator kept distinct) — never conflated.
  build/site-data/*.json    one JSON array per entity kind, read by site/.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BUILD_DIR  # noqa: E402

DB_PATH = BUILD_DIR / "succession.sqlite"
SITE_DATA = BUILD_DIR / "site-data"
GRAPHML_NS = "http://graphml.graphdrawing.org/xmlns"

KIND_TO_FILE = {
    "person": "people.json",
    "see": "sees.json",
    "jurisdiction": "jurisdictions.json",
    "tenure": "tenures.json",
    "consecration": "consecrations.json",
    "event": "events.json",
    "participation": "participations.json",
    "work": "works.json",
    "source": "sources.json",
    "tradition": "traditions.json",
}


def export_site_data(con):
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    counts = {}
    for kind, filename in KIND_TO_FILE.items():
        rows = con.execute(
            "SELECT json FROM records WHERE kind = ? ORDER BY id", (kind,)
        ).fetchall()
        items = [json.loads(r[0]) for r in rows]
        with open(SITE_DATA / filename, "w", encoding="utf-8") as fh:
            json.dump(items, fh, ensure_ascii=False, indent=1)
        counts[kind] = len(items)
    with open(SITE_DATA / "index.json", "w", encoding="utf-8") as fh:
        json.dump({"counts": counts}, fh, indent=1)
    return counts


def export_graphml(con):
    ET.register_namespace("", GRAPHML_NS)
    root = ET.Element(f"{{{GRAPHML_NS}}}graphml")

    keys = [
        ("d_label", "node", "label", "string"),
        ("d_kind", "node", "kind", "string"),
        ("d_status", "node", "status", "string"),
        ("d_etype", "edge", "edge_type", "string"),
        ("d_from", "edge", "from", "string"),
        ("d_to", "edge", "to", "string"),
        ("d_estatus", "edge", "status", "string"),
    ]
    for kid, target, name, ktype in keys:
        ET.SubElement(root, f"{{{GRAPHML_NS}}}key",
                      id=kid, attrib={"for": target,
                                      "attr.name": name, "attr.type": ktype})

    graph = ET.SubElement(root, f"{{{GRAPHML_NS}}}graph",
                          id="succession", edgedefault="directed")

    def data_el(parent, key, value):
        if value is None:
            return
        el = ET.SubElement(parent, f"{{{GRAPHML_NS}}}data", key=key)
        el.text = str(value)

    def node(nid, label, kind, status):
        n = ET.SubElement(graph, f"{{{GRAPHML_NS}}}node", id=nid)
        data_el(n, "d_label", label)
        data_el(n, "d_kind", kind)
        data_el(n, "d_status", status)

    for pid, name, status in con.execute("SELECT id, name, status FROM persons"):
        node(pid, name, "person", status)
    for sid, name, status in con.execute("SELECT id, name, status FROM sees"):
        node(sid, name, "see", status)

    known = {r[0] for r in con.execute("SELECT id FROM persons")} | \
            {r[0] for r in con.execute("SELECT id FROM sees")}

    edge_count = 0

    def edge(src, dst, etype, extra=None, status=None):
        nonlocal edge_count
        if src not in known or dst not in known:
            return
        e = ET.SubElement(graph, f"{{{GRAPHML_NS}}}edge",
                          id=f"e{edge_count}", source=src, target=dst)
        edge_count += 1
        data_el(e, "d_etype", etype)
        data_el(e, "d_estatus", status)
        for k, v in (extra or {}).items():
            data_el(e, k, v)

    # See-succession model: person -> see occupancy
    for person, see, fv, tv, status in con.execute(
        "SELECT person, see, from_value, to_value, status FROM tenures"
    ):
        edge(person, see, "tenure", {"d_from": fv, "d_to": tv}, status)

    # Consecration-succession model: consecrator -> consecrated,
    # principal vs co-consecrator preserved as distinct edge types.
    for consecrator, consecrated, role, status in con.execute(
        """SELECT e.consecrator, e.consecrated, e.role, c.status
           FROM consecration_edges e
           JOIN consecrations c ON c.id = e.consecration_id"""
    ):
        edge(consecrator, consecrated, role, None, status)

    BUILD_DIR.mkdir(exist_ok=True)
    tree = ET.ElementTree(root)
    ET.indent(tree)
    tree.write(BUILD_DIR / "graph.graphml", encoding="utf-8", xml_declaration=True)
    return edge_count


def main():
    if not DB_PATH.exists():
        print(f"export_graph: {DB_PATH} not found — run build_db.py first",
              file=sys.stderr)
        return 1
    con = sqlite3.connect(DB_PATH)
    counts = export_site_data(con)
    edges = export_graphml(con)
    con.close()
    total = sum(counts.values())
    print(f"export_graph: {total} record(s) -> {SITE_DATA}, "
          f"{edges} edge(s) -> {BUILD_DIR / 'graph.graphml'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
