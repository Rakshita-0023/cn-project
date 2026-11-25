PYTHON ?= python3
CN = $(PYTHON) phase2/network.py
.PHONY: help setup render start stop status health diagnose test-local test-live demo-backend demo-dns firewall rollback restore cleanup bundle inventory ttl-lab
help:
	@echo 'Phase 2: setup render start stop status health inventory test-local test-live'
	@echo 'Demos: demo-backend demo-dns ttl-lab; firewall: firewall rollback'
	@echo 'Recovery: restore cleanup; package: bundle. Read phase2/README.md first.'
setup:
	$(CN) setup
render:
	$(CN) render
start:
	$(CN) start
stop:
	$(CN) stop
status:
	$(CN) status
health diagnose:
	$(CN) diagnose
inventory:
	$(CN) inventory
test-local:
	$(PYTHON) phase2/tests/run_tests.py
ttl-lab:
	$(PYTHON) phase2/tests/run_tests.py --ttl-only
test-live:
	$(CN) test all
demo-backend:
	$(CN) demo backend
demo-dns:
	$(CN) demo dns
firewall:
	$(CN) firewall apply
rollback:
	$(CN) firewall rollback
restore:
	$(CN) records --target primary --ttl 30
cleanup:
	$(CN) cleanup
bundle:
	$(CN) bundle

.PHONY: submission
submission:
	$(PYTHON) scripts/prepare_submission.py
