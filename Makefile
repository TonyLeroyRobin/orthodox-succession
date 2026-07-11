PY ?= python

.PHONY: build validate db export gaps clean

build: validate db export gaps

gaps:
	$(PY) scripts/gap_report.py

validate:
	$(PY) scripts/validate.py

db:
	$(PY) scripts/build_db.py

export:
	$(PY) scripts/export_graph.py

clean:
	rm -rf build
