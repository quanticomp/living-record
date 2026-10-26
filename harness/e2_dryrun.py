#!/usr/bin/env python3
"""E2 stub dry-run — scorer + halt-rule validation (built 2026-10-26, $0).

Go-sequence (Data, Oct 26 09:35): before any metered E2 run, the pack is
served against STUB answers on this stage, including ONE INJECTED EMPTY
proving (a) the scorer counts empties and (b) the halt rule fires
(halt: empty rate >20% at any checkpoint).

Checkpoint definition (stage machinery, declared for Data's attestation):
checkpoints are consecutive blocks of 4 rows in pack order — the run's
natural batching. One empty inside a block = 25% > 20% -> HALT, and the
run stops: later rows are UNSCORED, never silently skipped.

Stub answers are constructed correct per each row's pinned expectation
(Addendum 2 family figures govern the C rows), so pass A validates that
every expectation is gradeable and the scorer grades correctly; pass B
injects the empty. The live battery replaces stubs with Wonder answers.
"""
import json, os, re, sys

PACK = os.path.expanduser(
    '~/workspace/goals/youtube-channel-wiki-archive/files/'
    'hackathon-w2-fixture-pack-gct-2026-10-26.md')
FAMILY = {'gemini': (119, 7), 'agent': (253, 8), 'flutter': (50, 1),
          'security': (58, 2), 'prompt': (45, 7), 'astrocade': (7, 1)}
CHECKPOINT = 4
HALT_RATE = 0.20

def parse_pack():
    rows = []
    for line in open(PACK):
        m = re.match(r'\| (E2-G\d+) \| (\w) \| (.*?) \| (.*?) \|', line)
        if m:
            rows.append({'id': m.group(1), 'cls': m.group(2),
                         'question': m.group(3), 'expected': m.group(4)})
    return rows

def stub_for(row):
    q, exp = row['question'], row['expected']
    if row['cls'] == 'C':
        term = re.search(r"'(\w+)'", q).group(1)
        n, v = FAMILY[term]
        return {'class': 'computed',
                'answer': f"{n} mentions across {v} of 9 videos", 'citations': ['corpus']}
    if row['cls'] == 'T':
        ts = re.search(r'@ (\d\d:\d\d:\d\d\.\d+)', exp).group(1)
        vid = re.search(r'video (\S+)\?', q).group(1)
        return {'class': 'retrieval', 'answer': f"{vid} @ {ts}",
                'citations': [{'unit': f'video:{vid}'}]}
    if row['cls'] == 'R':
        return {'class': 'refusal_no_evidence',
                'answer': 'Not in the record: term absent.', 'citations': []}
    if row['cls'] == 'M':
        vid = exp.split(' — ')[0]
        return {'class': 'computed', 'answer': vid, 'citations': []}
    raise ValueError(row)

def grade(row, ans):
    if ans is None or not str(ans.get('answer', '')).strip():
        return 'EMPTY'
    if row['cls'] == 'C':
        term = re.search(r"'(\w+)'", row['question']).group(1)
        n, v = FAMILY[term]
        ok = f'{n} mentions' in ans['answer'] and f'{v} of 9' in ans['answer']
    elif row['cls'] == 'T':
        ts = re.search(r'@ (\d\d:\d\d:\d\d\.\d+)', row['expected']).group(1)
        ok = ts in ans['answer']
    elif row['cls'] == 'R':
        ok = ans['class'].startswith('refusal')
    else:  # M — right video, and NO transcript citation claimed
        vid = row['expected'].split(' — ')[0]
        ok = vid in ans['answer'] and not ans.get('citations')
    return 'PASS' if ok else 'FAIL'

def run(rows, stubs, label):
    grades, empties, halted_at = {}, 0, None
    for i, row in enumerate(rows):
        g = grade(row, stubs[i])
        grades[row['id']] = g
        if g == 'EMPTY':
            empties += 1
        if (i + 1) % CHECKPOINT == 0 or i == len(rows) - 1:
            block = rows[max(0, i - CHECKPOINT + 1):i + 1]
            b_empty = sum(1 for r in block if grades.get(r['id']) == 'EMPTY')
            if b_empty / len(block) > HALT_RATE:
                halted_at = {'checkpoint_row': row['id'], 'block_empty': b_empty,
                             'block_size': len(block)}
                break
    scored = len(grades)
    print(f'{label}: scored {scored}/{len(rows)} rows | empties {empties} | '
          f'PASS {sum(1 for g in grades.values() if g == "PASS")} | '
          f'FAIL {sum(1 for g in grades.values() if g == "FAIL")} | '
          f'HALT {"FIRED at " + halted_at["checkpoint_row"] + f" (block {halted_at['block_empty']}/{halted_at['block_size']} empty)" if halted_at else "not fired"}')
    return grades, halted_at

def main():
    rows = parse_pack()
    assert len(rows) == 24, len(rows)
    stubs = [stub_for(r) for r in rows]
    gA, hA = run(rows, stubs, 'PASS A (clean stubs)')
    stubs_b = list(stubs)
    stubs_b[1] = {'class': 'synthesis', 'answer': '', 'citations': []}  # injected empty at row 2
    gB, hB = run(rows, stubs_b, 'PASS B (injected empty @ E2-G02)')
    ok = (len(gA) == 24 and not hA and all(g == 'PASS' for g in gA.values())
          and hB is not None and gB.get('E2-G02') == 'EMPTY' and len(gB) == 4)
    print('DRY-RUN:', 'GREEN — scorer grades all 24 expectations; the injected empty is counted and the halt fires, stopping the run'
          if ok else 'DEFECT — see lines above')
    sys.exit(0 if ok else 1)

if __name__ == '__main__':
    main()
