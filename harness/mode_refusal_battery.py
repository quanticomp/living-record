#!/usr/bin/env python3
"""Fallback-mode refusal battery (demo-integrity check, Studio ask Oct 25 19:34).
Every fallback mode must REFUSE what the main tier refuses. Runs the refusal
fixture set against each mode's corpus and prints one verdict line per mode."""
import json, subprocess, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
NONCE = "describe the zorblaxian treaty negotiations in detail"
# Expectations pin manifest v2 state for the build-record-derived modes:
# message counts answer as the WINDOWED computed count (the refusal class
# applies only under v1's defined_not_enumerated state — fixtures_v1.json).
# A manifest version bump that changes this expectation SHOULD fail here
# first: drift is the alarm working (as F1 demonstrated at the v2 rebuild).
CASES = [
    ('main', 'corpora/build-record', [(NONCE, 'refusal_no_evidence'),
        ("how many messages are in the corpus", 'computed'),
        ("what did the wonder probe measure", 'pointer')]),
    ('second-slice', 'corpora/mode-slice', [(NONCE, 'refusal_no_evidence')]),
    ('pre-ingested-twin', 'corpora/mode-twin', [(NONCE, 'refusal_no_evidence'),
        ("how many messages are in the corpus", 'computed'),
        ("what did the wonder probe measure", 'pointer')]),
    ('local-mirror', 'corpora/mode-mirror', [(NONCE, 'refusal_no_evidence'),
        ("how many messages are in the corpus", 'computed')]),
]
base = os.path.join(HERE, '..')
allok = True
for mode, rel, cases in CASES:
    cdir = os.path.join(base, rel)
    results = []
    for q, expect in cases:
        out = subprocess.run([sys.executable, os.path.join(HERE, 'query.py'), cdir, q],
                             capture_output=True, text=True).stdout
        got = json.loads(out)['class']
        ok = got == expect
        allok = allok and ok
        results.append(f"{expect}={'HOLD' if ok else 'FAIL(got '+got+')'}")
    print(f"MODE {mode}: refusal holds in this mode = {'YES' if all(r.endswith('HOLD') or 'YES' in r for r in results) and all('FAIL' not in r for r in results) else 'NO'} [{'; '.join(results)}]")
print('BATTERY:', 'ALL MODES HOLD' if allok else 'FAILURES PRESENT')
sys.exit(0 if allok else 1)
