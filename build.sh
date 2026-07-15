#!/usr/bin/env sh
# Full build chain: validate -> SQLite -> GraphML + site JSON.
set -e
python scripts/validate.py
python scripts/build_db.py
python scripts/export_graph.py
python scripts/gap_report.py
python scripts/build_site.py
echo "build: OK"
