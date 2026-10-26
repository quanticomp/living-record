#!/usr/bin/env python3
"""Evidence-sufficiency checks (added 2026-10-26 after the B2 finding).

The class fixtures prove an answer ROUTES correctly; they cannot see a
recall failure where the routed evidence lacks the answer-bearing span
(B2: the model correctly refused evidence whose 400-char truncation had
amputated the title). These checks assert the synthesis evidence itself
contains the fact the question asks for. $0, offline.
"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from synthesize import full_evidence

CASES = [
    ('corpora/build-record', 'what is the locked title of the companion',
     'Anatomy of a System'),
    ('corpora/build-record', 'why was sam 3.1 descoped to a stretch layer',
     'stretch'),
    ('corpora/e1-stripe', 'what does the record say about how developers use checkout',
     'checkout'),
    ('corpora/e1-gct', 'how is gemini used according to the record', 'Gemini'),
]
base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
fails = 0
for cdir, q, expect in CASES:
    out = subprocess.run([sys.executable, os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'query.py'),
        os.path.join(base_dir, cdir), q], capture_output=True, text=True).stdout
    base = json.loads(out)
    ev = full_evidence(os.path.join(base_dir, cdir), base.get('citations', []))
    joined = '\n'.join(c['text'] for c in ev)
    ok = expect.lower() in joined.lower()
    print(('PASS' if ok else 'FAIL'), cdir, '|', q[:50], '| evidence contains', repr(expect))
    fails += 0 if ok else 1
print('EVIDENCE CHECKS:', 'ALL PASS' if not fails else f'{fails} FAILED')
sys.exit(1 if fails else 0)
