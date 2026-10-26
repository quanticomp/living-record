#!/usr/bin/env python3
"""Run the harness fixture suite against a built corpus. $0, offline."""
import json, subprocess, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
corpus_dir = sys.argv[1]
fx_file = sys.argv[2] if len(sys.argv) > 2 else 'fixtures.json'
fx = json.load(open(os.path.join(HERE, fx_file)))['fixtures']
passed = failed = 0
for f in fx:
    out = subprocess.run([sys.executable, os.path.join(HERE, 'query.py'), corpus_dir, f['question']],
                         capture_output=True, text=True).stdout
    try:
        r = json.loads(out)
    except Exception:
        r = {'class': 'PARSE_ERROR', 'answer': out[:100]}
    ok = r.get('class') == f['expect_class'] and all(
        s.lower() in (r.get('answer', '') + json.dumps(r.get('citations', []))).lower()
        for s in f['expect_contains'])
    print(('PASS' if ok else 'FAIL'), f['id'], '->', r.get('class'))
    if not ok:
        failed += 1
        print('   answer:', (r.get('answer') or '')[:160])
    else:
        passed += 1
print(f'FIXTURES: {passed} passed, {failed} failed')
sys.exit(1 if failed else 0)
