PY ?= python

.PHONY: build validate db export clean

build: validate db export

validate:
	$(PY) scripts/validate.py

db:
	$(PY) scripts/build_db.py

export:
	$(PY) scripts/export_graph.py

clean:
	rm -rf build
