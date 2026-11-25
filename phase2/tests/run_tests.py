#!/usr/bin/env python3
"""Execute local regressions and write genuine logs plus machine-readable results."""
import argparse
import contextlib
import datetime
import json
import platform
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from phase2.network import Tee
from phase2.tests import test_phase2
import test_local


class Results(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cases = []
        self.started = {}

    def startTest(self, test):
        self.started[test.id()] = time.monotonic()
        super().startTest(test)

    def addSuccess(self, test):
        self.record(test, "PASS")
        super().addSuccess(test)

    def addFailure(self, test, error):
        self.record(test, "FAIL")
        super().addFailure(test, error)

    def addError(self, test, error):
        self.record(test, "ERROR")
        super().addError(test, error)

    def addSkip(self, test, reason):
        self.record(test, "SKIP", reason)
        super().addSkip(test, reason)

    def record(self, test, status, reason=None):
        self.cases.append({"test": test.id(), "status": status, "seconds": round(time.monotonic()-self.started[test.id()], 3), "reason": reason})


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ttl-only", action="store_true")
    a = p.parse_args()
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    if a.ttl_only:
        suite.addTest(test_phase2.DNSIntegrationTests("test_real_ttl_expiry_record_change_and_cache_flush"))
    else:
        suite.addTests(loader.loadTestsFromModule(test_local))
        suite.addTests(loader.loadTestsFromModule(test_phase2))
    evidence = ROOT / "evidence/phase2"
    evidence.mkdir(parents=True, exist_ok=True)
    prefix = "ttl-lab" if a.ttl_only else "local-tests"
    with (evidence / f"{prefix}.txt").open("w") as file:
        tee = Tee(sys.stdout, file)
        with contextlib.redirect_stdout(tee), contextlib.redirect_stderr(tee):
            print("Observed:", datetime.datetime.now().astimezone().isoformat())
            print("Host:", platform.platform(), "Python:", platform.python_version())
            print("Scope: local loopback processes, ephemeral test ports. No LAN, Keychain, system DNS or PF changes.")
            result = unittest.TextTestRunner(stream=tee, verbosity=2, resultclass=Results).run(suite)
    summary = {"observed_at": datetime.datetime.now().astimezone().isoformat(), "scope": "local loopback only",
               "run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
               "successful": result.wasSuccessful(), "cases": result.cases}
    (evidence / f"{prefix}.json").write_text(json.dumps(summary, indent=2) + "\n")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
