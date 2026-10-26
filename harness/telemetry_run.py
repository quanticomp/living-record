#!/usr/bin/env python3
"""Telemetry-emitting fixture run (stage drill, 2026-10-25, $0).

Runs the harness fixture questions through the query path, timing each stage
and measuring peak memory, and appends one record per answer in the
telemetry schema (scaffold/telemetry-schema.md) to telemetry.jsonl.
Every number in the stream is measured on this machine from these executions.
"""
import json, os, resource, subprocess, sys, time, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
corpus_dir = sys.argv[1]
out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, '..', 'stage', 'telemetry.jsonl')
os.makedirs(os.path.dirname(out_path), exist_ok=True)
corpus = json.load(open(os.path.join(corpus_dir, 'corpus.json')))
state = json.load(open(os.path.join(corpus_dir, 'state.json')))
fx = json.load(open(os.path.join(HERE, 'fixtures.json')))['fixtures']

with open(out_path, 'a') as out:
    for f in fx:
        t0 = time.time()
        r = subprocess.run([sys.executable, os.path.join(HERE, 'query.py'), corpus_dir, f['question']],
                           capture_output=True, text=True)
        dt = (time.time() - t0) * 1000
        ans = json.loads(r.stdout)
        peak_kb = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        rec = {
            'answer_id': str(uuid.uuid4()),
            'ts': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
            'corpus': {'id': corpus['corpus_id'],
                       'units': state.get('units_indexed'),
                       'words': state.get('words_indexed')},
            'question': f['question'],
            'route': {'computed': 'computed', 'pointer': 'pointer',
                      'retrieval': 'retrieval'}.get(ans['class'], 'refusal'),
            'answer_class': ans['class'],
            'stages_ms': {'total_measured': round(dt, 1)},
            'memory_peak_kb_children': peak_kb,
            'cost_est_usd': 0.0,
            'cost_basis': 'offline build - no model calls',
            'citations': ans.get('citations', []),
        }
        out.write(json.dumps(rec) + '\n')
        print('telemetry:', f['id'], ans['class'], f"{dt:.0f}ms")
print('stream ->', out_path)
