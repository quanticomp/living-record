#!/usr/bin/env python3
"""Living Record ingest harness — core (v0, built 2026-10-25, $0/offline).

project: living-record-hackathon

Sources:
  manifest     — filesystem adapter over a corpus manifest (Data's Build Record
                 manifest v1 shape): members are artifacts on disk; cited
                 evidence from other projects rides as POINTERS, never members.
  captions-dir — a directory of transcript files (<id>.txt), the cached-pull
                 input shape for the video path (rehearsal discipline: the
                 harness consumes cached captions; live pulls are a separate,
                 rate-limited step exercised in rehearsals, not here).

Stages write an atomic state.json in the console contract's shape (absent
fields stay absent — the console renders "—", never an interpolated 0).
Index: SQLite FTS5 over chunk TEXT only (metadata in a side table — the
F23 lesson: FTS indexes text, never metadata).

Usage:
  python3 ingest.py build --source manifest --manifest <path> --out <dir>
  python3 ingest.py build --source captions-dir --dir <path> --out <dir>
"""
import argparse, json, os, re, sqlite3, sys, time

CHUNK_CHARS = 1200
OVERLAP = 150

def now():
    return time.strftime('%Y-%m-%dT%H:%M:%S%z')

def write_state(out, state):
    state['updated_at'] = now()
    tmp = os.path.join(out, 'state.json.tmp')
    with open(tmp, 'w') as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, os.path.join(out, 'state.json'))

def md_to_text(md):
    t = re.sub(r'```.*?```', ' ', md, flags=re.S)
    t = re.sub(r'`([^`]*)`', r'\1', t)
    t = re.sub(r'!\[[^\]]*\]\([^)]*\)', ' ', t)
    t = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', t)
    t = re.sub(r'^#{1,6}\s*', '', t, flags=re.M)
    t = re.sub(r'[*_]{1,3}([^*_]+)[*_]{1,3}', r'\1', t)
    t = re.sub(r'\|', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()

def chunk_text(text):
    chunks, i = [], 0
    while i < len(text):
        chunks.append(text[i:i + CHUNK_CHARS])
        if i + CHUNK_CHARS >= len(text):
            break
        i += CHUNK_CHARS - OVERLAP
    return [c for c in chunks if c.strip()]

EXCLUSION_CLASSES = [
    (re.compile(r'credential|vault|\.env|secret|\.key$|\.pem$|id_rsa|keys\.zip', re.I),
     'credentials/secrets — never members, never pointers, never chunked'),
    (re.compile(r'(^|/)MEMORY\.md$|(^|/)memory/', re.I),
     'mixed personal/work memory — excluded as content (design §Exclusion)'),
    (re.compile(r'health|diary|whatsapp', re.I),
     'personal thread class — excluded by the work-ledger precedent'),
]

def exclusion_check(path):
    for pat, reason in EXCLUSION_CLASSES:
        if pat.search(path):
            return reason
    return None

def write_exclusion_log(out, entries):
    with open(os.path.join(out, 'exclusion-log.jsonl'), 'w') as f:
        for e in entries:
            f.write(json.dumps(e) + '\n')

def build_index(out, docs):
    """docs: list of {unit_id, kind, title, text, meta{}}"""
    db = os.path.join(out, 'index.db')
    if os.path.exists(db):
        os.remove(db)
    con = sqlite3.connect(db)
    con.execute('CREATE TABLE units (unit_id TEXT PRIMARY KEY, kind TEXT, title TEXT, meta TEXT, full_text TEXT)')
    con.execute('CREATE VIRTUAL TABLE chunk_fts USING fts5(text)')
    con.execute('CREATE TABLE chunks (rowid INTEGER PRIMARY KEY, unit_id TEXT, chunk_no INT, text TEXT)')
    total_words = 0
    for d in docs:
        con.execute('INSERT INTO units VALUES (?,?,?,?,?)',
                    (d['unit_id'], d['kind'], d['title'], json.dumps(d.get('meta', {})),
                     d['text']))
        for n, c in enumerate(chunk_text(d['text'])):
            cur = con.execute('INSERT INTO chunks (unit_id, chunk_no, text) VALUES (?,?,?)',
                              (d['unit_id'], n, c))
            con.execute('INSERT INTO chunk_fts (rowid, text) VALUES (?,?)', (cur.lastrowid, c))
            total_words += len(c.split())
    con.commit(); con.close()
    return total_words

def _pointers(m):
    """Pointers are definitional (corpus definition, scope rule). v1/v2 carry
    the block in the manifest; v3 ships pointers_not_members: null. When a
    manifest omits the block, inherit the definitional set (harness/
    pointers.json, seeded from v2) and MARK the inheritance — the pointer
    behavior never silently lapses because a generator changed shape."""
    p = m.get('pointers_not_members')
    if p:
        return p
    seed = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pointers.json')
    inherited = json.load(open(seed)) if os.path.exists(seed) else []
    for e in inherited:
        e['provenance'] = (f"definitional inheritance — manifest {m.get('version')} "
                           f"carries no pointers block (flagged to Data)")
    return inherited

def source_manifest(manifest_path, home):
    m = json.load(open(manifest_path))
    docs, loaded, missing, excluded = [], 0, [], []
    for a in m['artifacts']:
        reason = exclusion_check(a['path'])
        if reason:
            excluded.append({'path': a['path'], 'excluded_class': reason,
                             'enforced_at': 'ingest'})
            continue
        p = os.path.join(home, a['path'])
        if not os.path.exists(p):
            missing.append(a['id']); continue
        raw = open(p, encoding='utf-8', errors='replace').read()
        docs.append({'unit_id': a['id'], 'kind': 'artifact',
                     'title': os.path.basename(a['path']),
                     'text': md_to_text(raw),
                     'meta': {'bytes': a.get('bytes'), 'path': a['path'],
                              # convergence fields (internal-instance design):
                              'source_class': 'contest-artifact',
                              'membership': 'member',
                              'source_asof': f"manifest {m.get('version')} fingerprint",
                              'enumeration_state': 'enumerated',
                              # Data's cadence law (Oct 26): living members are a
                              # DECLARED class in the manifest; membership is the
                              # frozen fact, bytes the declared variable.
                              'member_class': ('living' if a.get('living')
                                               else 'settled')}})
        loaded += 1
    # Enumeration state is DERIVED from the manifest, never hardcoded:
    # v1 defined the message corpus without enumerating it; v2 enumerated a
    # bounded window (total_submissions + window). The answer path keys off
    # this state, so a manifest version bump changes behavior by itself —
    # and the fixture suites pin expectations per version (drift = alarm).
    msg_block = m.get('counts', {}).get('messages')
    enumeration = {'artifacts': 'enumerated'}
    messages_summary = None
    if isinstance(msg_block, dict) and 'total_submissions' in msg_block:
        enumeration['messages'] = 'enumerated_window'
        pc = msg_block.get('project_class', {})
        def _val(x):
            return x.get('value') if isinstance(x, dict) else x
        sc = msg_block.get('settle_check')
        if isinstance(sc, dict) and sc.get('result') == 'FROZEN':
            settle_summary = {'status': 'FROZEN — settle check PASSED',
                              'pass1': sc.get('pass1'), 'pass2': sc.get('pass2'),
                              'rule': sc.get('rule')}
        elif isinstance(sc, dict):
            settle_summary = {'status': 'FREEZE CANDIDATE — settle-check pass 1 of 2',
                              'pass1': sc.get('pass1'), 'pass2_due': sc.get('pass2_due'),
                              'rule': sc.get('rule')}
        else:
            settle_summary = None
        messages_summary = {
            'total_submissions': msg_block['total_submissions'],
            'window': msg_block.get('window'),
            'universe': msg_block.get('universe'),
            'project_class_value': pc.get('value'),
            'project_class_stance': 'floor — pattern-classified, reported as a floor, never an exact census',
            'end_of_cycle_reports': _val(msg_block.get('end_of_cycle_reports')),
            'system_handoffs': _val(msg_block.get('system_handoffs')),
            'settle_check': settle_summary,
        }
    else:
        enumeration['messages'] = 'defined_not_enumerated'
    # Annex overlay: Data's annex recounts can supersede as-materialized
    # figures between manifest versions. The overlay rides INTO corpus.json
    # so the answer path presents both provenances, never a corrected number
    # as if it still stood. (stage/annex-overlay.json, maintained by hand
    # from Data's filed annexes; manifest v3 supersedes it when frozen.)
    # Overlay files are VERSION-SCOPED (annex-overlay.v2.json corrects the v2
    # base only); a manifest version with no overlay file carries none.
    overlay_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'stage',
                                f"annex-overlay.{m.get('version')}.json")
    annex = None
    if messages_summary and os.path.exists(overlay_path):
        try:
            annex = json.load(open(overlay_path))
            c = annex.get('corrections', {})
            if 'project_class' in c:
                messages_summary['project_class_annex_recount'] = c['project_class']
            if 'end_of_cycle_reports' in c:
                messages_summary['end_of_cycle_reports_annex_recount'] = c['end_of_cycle_reports']
        except Exception:
            annex = None
    # Count keys normalize across manifest versions (v1/v2: decisions_v1,
    # corrections_v1; v3: decisions, corrections) — the answer path keys off
    # the canonical names only.
    raw_counts = m.get('counts', {})
    def _cval(k):
        v = raw_counts.get(k)
        return v.get('value') if isinstance(v, dict) else None
    norm_counts = {'artifacts': _cval('artifacts'),
                   'decisions': _cval('decisions') if 'decisions' in raw_counts else _cval('decisions_v1'),
                   'corrections': _cval('corrections') if 'corrections' in raw_counts else _cval('corrections_v1')}
    corpus = {
        'corpus_id': m.get('corpus', 'build-record'),
        'manifest_version': m.get('version'),
        'fingerprint_local': m.get('fingerprint_local'),
        'counts': {k: v for k, v in norm_counts.items() if v is not None},
        'count_methods': {k: v.get('method') or v.get('note') for k, v in raw_counts.items()
                          if isinstance(v, dict)},
        'enumeration': enumeration,
        'messages_summary': messages_summary,
        'annex_overlay': annex,
        'excluded_entries': excluded,
        'currency': ({'kind': 'frozen',
                      'label': f"contest corpus as of the manifest {m.get('version')} freeze",
                      'as_of': (messages_summary or {}).get('settle_check', {}).get('pass2')
                               or m.get('version')}
                     if (messages_summary or {}).get('settle_check', {}).get('status', '')
                        .startswith('FROZEN')
                     else {'kind': 'manifest',
                           'label': f"contest corpus at manifest {m.get('version')}",
                           'as_of': m.get('version')}),
        'pointers_not_members': _pointers(m),
        'missing_members': missing,
    }
    return docs, corpus, loaded

def source_vtt_dir(dirpath):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from vtt import group_vtt_dir, video_text
    docs, mtimes = [], []
    for vid, path in sorted(group_vtt_dir(dirpath).items()):
        mt = time.strftime('%Y-%m-%dT%H:%M:%S%z', time.localtime(os.path.getmtime(path)))
        mtimes.append(mt)
        docs.append({'unit_id': 'video:' + vid, 'kind': 'transcript',
                     'title': vid, 'text': video_text(path),
                     'meta': {'source_file': os.path.basename(path),
                              'source_class': 'transcript', 'membership': 'member',
                              'source_asof': mt, 'enumeration_state': 'enumerated'}})
    corpus = {'corpus_id': 'e1-' + os.path.basename(os.path.abspath(dirpath)),
              'enumeration': {'transcripts': 'enumerated'},
              'pointers_not_members': [], 'excluded_entries': [],
              'currency': {'kind': 'files', 'label': 'source files at ingest',
                           'as_of': max(mtimes) if mtimes else None}}
    return docs, corpus, len(docs)

def source_captions_dir(dirpath):
    docs = []
    for fn in sorted(os.listdir(dirpath)):
        if fn.endswith('.txt'):
            raw = open(os.path.join(dirpath, fn), encoding='utf-8', errors='replace').read()
            docs.append({'unit_id': 'video:' + fn[:-4], 'kind': 'transcript',
                         'title': fn[:-4], 'text': re.sub(r'\s+', ' ', raw).strip(),
                         'meta': {}})
    corpus = {'corpus_id': os.path.basename(os.path.abspath(dirpath)),
              'enumeration': {'transcripts': 'enumerated'},
              'pointers_not_members': [], 'excluded_entries': [],
              'currency': {'kind': 'files', 'label': 'source files at ingest',
                           'as_of': None}}
    return docs, corpus, len(docs)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['build'])
    ap.add_argument('--source', required=True, choices=['manifest', 'captions-dir', 'vtt-dir'])
    ap.add_argument('--manifest'); ap.add_argument('--dir')
    ap.add_argument('--out', required=True)
    ap.add_argument('--home', default=os.path.expanduser('~/workspace'))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    state = {'stage': 'enumerate', 'stage_started_at': now()}
    write_state(a.out, state)
    if a.source == 'manifest':
        docs, corpus, loaded = source_manifest(a.manifest, a.home)
    elif a.source == 'vtt-dir':
        docs, corpus, loaded = source_vtt_dir(a.dir)
    else:
        docs, corpus, loaded = source_captions_dir(a.dir)
    excluded_entries = corpus.pop('excluded_entries', [])
    write_exclusion_log(a.out, excluded_entries)
    corpus['excluded_count'] = len(excluded_entries)
    state.update({'stage': 'index', 'items_found': loaded,
                  'items_with_content': loaded,
                  'exclusions_logged': len(excluded_entries)})
    write_state(a.out, state)
    words = build_index(a.out, docs)
    # Surface self-identification (demo-composition discipline, Oct 26):
    # every corpus the demo serves names its provenance class — in-window
    # work is the demo's substance; pre-existing production work is cited
    # proof/context only, and enters as pointers, never as a demo corpus.
    provenance = ('project record — built in-window' if a.source == 'manifest'
                  else 'public corpus ingested in-window (demo substance)')
    corpus['provenance_class'] = provenance
    state.update({'stage': 'ask-ready', 'words_indexed': words,
                  'units_indexed': len(docs), 'provenance_class': provenance})
    write_state(a.out, state)
    with open(os.path.join(a.out, 'corpus.json'), 'w') as f:
        json.dump(corpus, f, indent=1)
    print(f"BUILT {corpus['corpus_id']}: {len(docs)} units, {words} words indexed -> {a.out}")

if __name__ == '__main__':
    main()
