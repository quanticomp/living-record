#!/usr/bin/env python3
"""Entities stage v0 + term cross-check (built 2026-10-26, $0/offline).

project: living-record-hackathon

Candidate extraction is DETERMINISTIC and labeled as what it is: capitalized
name phrases mined over normalized chunk text, with frequency + unit
evidence. Every candidate carries its derivation; the class is CANDIDATE —
resolution/verification is a Data spot-check away, never asserted here
(the derivability rule: a surface claims only the verification it has).

Usage:
  entities.py extract <corpus_dir>
  entities.py term <corpus_dir> <term> [<term> ...]   (whole-word counts)
"""
import json, os, re, sqlite3, sys
from collections import Counter, defaultdict

STOP = {'The', 'This', 'That', 'And', 'But', 'You', 'Your', 'We', 'It', 'In',
        'On', 'At', 'So', 'If', 'When', 'What', 'How', 'Why', 'Now', 'Then',
        'There', 'Here', 'Yeah', 'Uh', 'Um', 'Okay', 'Right', 'Like', 'Just',
        # discourse markers captions capitalize at cue starts (observed v0 run)
        'Thank', 'They', 'Yes', 'Mhm', 'Very', 'Well', 'Can', 'He', 'She',
        'Then', 'Also', 'Actually', 'Really', 'One', 'First', 'Get', 'Got'}
NAME = re.compile(r"\b([A-Z][a-z]+(?:\s+(?:[A-Z][a-z]+|of|the|de|van)){0,2})\b")

def load_chunks(corpus_dir):
    con = sqlite3.connect(os.path.join(corpus_dir, 'index.db'))
    return con.execute('SELECT unit_id, text FROM chunks').fetchall()

def extract(corpus_dir):
    mentions, units = Counter(), defaultdict(set)
    for unit_id, text in load_chunks(corpus_dir):
        for m in NAME.finditer(text):
            name = m.group(1).strip()
            if name.split()[0] in STOP or len(name) < 3:
                continue
            mentions[name] += 1
            units[name].add(unit_id)
    out = [{'name': n, 'mentions': c, 'units': sorted(units[n]),
            'class': 'CANDIDATE',
            'derivation': 'capitalized-phrase frequency over normalized text; unresolved — pending Data spot-check'}
           for n, c in mentions.most_common(60) if c >= 2]
    path = os.path.join(corpus_dir, 'entities.json')
    json.dump(out, open(path, 'w'), indent=1)
    print(f'entities: {len(out)} candidates (>=2 mentions) -> {path}')
    for e in out[:12]:
        print(f"  {e['name']}: {e['mentions']}x in {len(e['units'])} units")

def term(corpus_dir, terms):
    # Count over FULL unit text, never chunks: chunk overlap double-counts
    # boundary words (caught against Data's E2 exemplars, 2026-10-26).
    con = sqlite3.connect(os.path.join(corpus_dir, 'index.db'))
    try:
        rows = con.execute('SELECT unit_id, full_text FROM units').fetchall()
    except sqlite3.OperationalError:
        rows = [(u, t) for u, t in load_chunks(corpus_dir)]
    for t in terms:
        # Term definition (pinned after the checkout trace, 2026-10-26): the
        # term and its regular plural count as the term family — Data's E2
        # exemplars count 'checkouts' under checkout; an exact-form counter
        # silently misses every plural. The basis is stated wherever cited.
        pat = re.compile(r'\b' + re.escape(t) + r'(?:s|es)?\b', re.I)
        total, per_unit = 0, Counter()
        for unit_id, text in rows:
            n = len(pat.findall(text))
            if n:
                total += n
                per_unit[unit_id] += n
        print(f'TERM {t}: {total} mentions across {len(per_unit)} units')

if __name__ == '__main__':
    if sys.argv[1] == 'extract':
        extract(sys.argv[2])
    elif sys.argv[1] == 'term':
        term(sys.argv[2], sys.argv[3:])
