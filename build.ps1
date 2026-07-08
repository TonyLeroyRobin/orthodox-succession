# Full build chain: validate -> SQLite -> GraphML + site JSON.
python scripts/validate.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/build_db.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/export_graph.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "build: OK"
