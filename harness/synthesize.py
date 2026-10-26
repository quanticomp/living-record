#!/usr/bin/env python3
"""Wonder synthesis tier for the harness (wired 2026-10-26, hold lifted).

project: living-record-hackathon

The synthesis slot sits AFTER the deterministic classes and retrieval:
computed / pointer / refusal answers never reach the model. A retrieval
result may be synthesized into prose by Wonder, grounded ONLY in the
retrieved chunks, with citations preserved from retrieval — the model
composes, it never sources.

Laws carried from the exam record (kill-tony-wonder-exam-2026-10-25):
- model muse-wonder-1.0 via https://api.meta.ai/v1 (OpenAI-compatible)
- reasoning_effort=low (probe law: 0/10 empty at low vs 10/10 default)
- thinking-aware output cap: max_tokens 2000 (800 starves the answer)
- cost at list rates: $4.00 in / $20.00 out per MTok (ESTIMATE class)
- instructions mirror production's citable-records wording (the fixture-v2
  lesson: excerpt-only scoping makes the model refuse the record blocks)

Modes: --dry-run constructs the exact request and prints it (key redacted,
no call, $0). Live mode requires META_API_KEY in env and HARNESS_SYNTHESIS=live.
Every live call appends its finance line (tokens + dollars) to
stage/finance-lines.jsonl — the Showcase Doctrine receipt.
"""
import json, os, sys, time, urllib.request

API = 'https://api.meta.ai/v1/chat/completions'
MODEL = 'muse-wonder-1.0'
RATE_IN, RATE_OUT = 4.00, 20.00  # $ per MTok, list

SYSTEM = (
    'You answer questions from a verified archive record. You are given record '
    'evidence: excerpts from the corpus, each labeled with its source unit. '
    'Answer using ONLY that evidence. Cite the source unit for each claim, in '
    'the form [unit: <id>]. If the evidence does not answer the question, say '
    'the record does not answer it — never use outside knowledge. Keep the '
    'answer tight: the fact, its citation, nothing decorative.'
)

def full_evidence(corpus_dir, citations, limit=5):
    """Synthesis evidence = FULL chunk text for the top citations.
    The offline retrieval display truncates chunks to 400 chars; that cut
    amputated the answer-bearing span in the B2 validation run (the title
    sat past char 400), and the model correctly refused evidence that did
    not contain the answer. Synthesis never truncates, and takes 5."""
    import sqlite3
    con = sqlite3.connect(os.path.join(corpus_dir, 'index.db'))
    out = []
    for c in citations[:limit]:
        row = con.execute('SELECT text FROM chunks WHERE unit_id=? AND chunk_no=?',
                          (c['unit'], c['chunk'])).fetchone()
        out.append({'unit': c['unit'], 'chunk': c['chunk'],
                    'text': row[0] if row else c['text']})
    return out

def build_request(question, chunks):
    ev = '\n\n'.join(f"[unit: {c['unit']}]\n{c['text']}" for c in chunks)
    return {
        'model': MODEL,
        'messages': [
            {'role': 'system', 'content': SYSTEM},
            {'role': 'user', 'content': f'Question: {question}\n\nRecord evidence:\n{ev}'},
        ],
        'reasoning_effort': 'low',
        'max_tokens': 2000,
    }

def call(req):
    key = os.environ.get('META_API_KEY')
    if not key:
        raise RuntimeError('META_API_KEY not in env')
    http = urllib.request.Request(
        API, data=json.dumps(req).encode(),
        headers={'Content-Type': 'application/json',
                 'Authorization': f'Bearer {key}'})
    t0 = time.time()
    with urllib.request.urlopen(http, timeout=120) as resp:
        body = json.loads(resp.read())
    dt = (time.time() - t0) * 1000
    usage = body.get('usage', {})
    cost = (usage.get('prompt_tokens', 0) * RATE_IN
            + usage.get('completion_tokens', 0) * RATE_OUT) / 1_000_000
    return {
        'answer': body['choices'][0]['message']['content'],
        'usage': usage, 'cost_usd': round(cost, 4), 'latency_ms': round(dt, 1),
    }

def finance_line(record, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'a') as f:
        f.write(json.dumps(record) + '\n')

if __name__ == '__main__':
    dry = '--dry-run' in sys.argv
    args = [a for a in sys.argv[1:] if a != '--dry-run']
    corpus_dir, question = args[0], args[1]
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        import subprocess
        out = subprocess.run([sys.executable, os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'query.py'),
            corpus_dir, question], capture_output=True, text=True).stdout
    base = json.loads(out)
    if base['class'] != 'retrieval':
        print(json.dumps({'class': base['class'], 'synthesis': 'not applicable — '
                          'deterministic classes never reach the model',
                          'answer': base['answer']}, indent=1))
        sys.exit(0)
    req = build_request(question, full_evidence(corpus_dir, base['citations']))
    if dry:
        redacted = json.loads(json.dumps(req))
        print(json.dumps({'dry_run': True, 'endpoint': API, 'request': redacted,
                          'evidence_units': [c['unit'] for c in base['citations']]},
                         indent=1))
        sys.exit(0)
    if os.environ.get('HARNESS_SYNTHESIS') != 'live':
        print(json.dumps({'error': 'live synthesis requires HARNESS_SYNTHESIS=live'}, indent=1))
        sys.exit(1)
    res = call(req)
    line = {'ts': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'feature': 'wonder-synthesis',
            'corpus': os.path.basename(os.path.abspath(corpus_dir)),
            'question': question, 'model': MODEL,
            'tokens_in': res['usage'].get('prompt_tokens'),
            'tokens_out': res['usage'].get('completion_tokens'),
            'cost_usd': res['cost_usd'], 'cost_basis': 'list rates $4/$20 per MTok (ESTIMATE class)',
            'latency_ms': res['latency_ms']}
    finance_line(line, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', 'stage', 'finance-lines.jsonl'))
    print(json.dumps({'class': 'synthesis', 'answer': res['answer'],
                      'citations': [c['unit'] for c in base['citations']],
                      'finance': line}, indent=1))
