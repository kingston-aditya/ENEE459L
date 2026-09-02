# ENEE459L Lab 01. `make help` lists what is here.
#
# There is no build step — this is Python against sysfs. The targets exist so
# that the commands in the lab guide are one word long and identical on a
# laptop and on the board.

PYTHON  ?= python3
DEVICE  ?= unknown
OUT     ?= system_report.json

.PHONY: help fixtures test report check clean

help:
	@echo "  make fixtures   build the fake machines the tests run against"
	@echo "  make test       run the public test suite"
	@echo "  make report     run the probes on THIS machine, write $(OUT)"
	@echo "                  (pass the unit's label: make report DEVICE=jetson-07)"
	@echo "  make check      validate an existing $(OUT) against the schema"
	@echo "  make clean      remove generated fixtures and reports"

fixtures:
	$(PYTHON) tests/make_fixtures.py

test: fixtures
	$(PYTHON) -m pytest tests/test_public.py -v

# Not .PHONY-guarded against a missing DEVICE on purpose: a report with
# device_id "unknown" is still a valid report, and refusing to write one would
# lose a student's measurement over a naming convention. It is caught at
# submission instead, where it can be fixed without re-running anything.
report:
	$(PYTHON) system_report.py --device-id $(DEVICE) -o $(OUT)

check:
	@$(PYTHON) -c "import json, sys; from enee459l import schema; \
	  p = schema.validate(json.load(open('$(OUT)'))); \
	  print('\n'.join('  - ' + x for x in p) if p else '$(OUT) is valid'); \
	  sys.exit(1 if p else 0)"

clean:
	rm -rf tests/fixtures $(OUT) .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +
