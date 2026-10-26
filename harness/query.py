#!/usr/bin/env python3
"""Living Record query path — offline classes (v0, built 2026-10-25, $0).

project: living-record-hackathon

Answer classes, in routing order:
  1. ENUMERATION-STATE REFUSAL — a question about a class the corpus
     definition marks defined_not_enumerated (messages) gets the designed
     refusal. Implemented as a state check in the answer path, NOT a prompt
     hope: this build has no model in the loop at all.
  2. POINTER — a question about cited evidence owned by another project
     (the Wonder exam set, the production corpora) returns the pointer:
     named, owned, cited — never answered from member content and never
     counted as a member.
  3. COMPUTED — counts the manifest itself carries (artifacts, decisions,
     corrections) answered from corpus.json with the counting method.
  4. RETRIEVAL — FTS over member chunks; the answer is the cited evidence
     itself, labeled as retrieval. (The Wonder synthesis tier plugs in here
     when the contest build activates it; this offline build does not fake
     a synthesis it doesn't have.)

Usage: python3 query.py <corpus_dir> "<question>"
"""
import json, os, re, sqlite3, sys

MSG_COUNT = re.compile(r'(how many|number of|count of|total)\b[^?]*\bmessages?\b', re.I)
COUNT_Q = re.compile(r'how many (artifacts|decisions|corrections)\b', re.I)
POINTER_TOPICS = [
    (re.compile(r'wonder|exam|probe|fixture|pilot sample', re.I),
     re.compile(r'wonder|exam', re.I)),
    (re.compile(r'kill tony|episodes?\b.*\bwords?\b|words?\b.*\bepisodes?\b', re.I),
     re.compile(r'kill tony|production corpora', re.I)),
]

DISPLAY = {
    'computed': ('COMPUTED', 'no model in this path — arithmetic over the record'),
    'pointer': ('POINTER', 'cited evidence owned by another project — not a member'),
    'retrieval': ('EVIDENCE', 'record excerpts, composed by no model'),
    'refusal_enumeration_state': ('REFUSED', 'not counted yet — the record states its own limit'),
    'refusal_no_evidence': ('REFUSED', 'the record does not answer this — a first-class state, not an error'),
}

def with_display(obj):
    """The anti-RAG visibility contract (Oct 26): every answer carries its
    class badge + whether a model was in the path + its evidence affordance,
    so the live surface SHOWS the separation instead of merely having it."""
    badge, note = DISPLAY.get(obj.get('class'), (obj.get('class', '').upper(), ''))
    obj['display'] = {'badge': badge, 'note': note,
                      'model_in_path': obj.get('class') == 'synthesis',
                      'evidence_reachable': bool(obj.get('citations')) or
                      obj.get('class', '').startswith('refusal')}
    return obj

_CURRENCY = None

def emit(obj):
    # Freshness law (internal-instance design): EVERY answer carries its
    # source currency — frozen sources state their freeze; the as-of is the
    # source's own signal, carried from the corpus record at answer time.
    if _CURRENCY:
        obj['currency'] = _CURRENCY
    print(json.dumps(with_display(obj), indent=1))

def fts_terms(q):
    words = re.findall(r"[a-z0-9']+", q.lower())
    stop = {'what', 'when', 'who', 'how', 'many', 'the', 'was', 'were', 'did', 'does', 'is', 'are', 'in', 'of', 'on', 'a', 'an', 'to',
            # framing vocabulary — how a question is phrased, never its topic.
            # The vocabulary gate judges TOPIC terms only; a framing word's
            # absence ("according to the record") must not refuse a question
            # whose topics are all present (caught live, 2026-10-26: S3).
            'according', 'record', 'archive', 'corpus', 'say', 'says', 'said',
            'describe', 'mention', 'mentions', 'mentioned', 'talk', 'talks',
            'discuss', 'discusses', 'explain', 'show', 'shows', 'give', 'list',
            'tell', 'tells', 'about', 'say', 'using', 'use', 'used'}
    return [w for w in words if w not in stop and len(w) > 2]

def main():
    corpus_dir, question = sys.argv[1], sys.argv[2]
    corpus = json.load(open(os.path.join(corpus_dir, 'corpus.json')))
    global _CURRENCY
    _CURRENCY = corpus.get('currency')
    enum = corpus.get('enumeration', {})

    # 1. enumeration-state handling (state derived from the manifest):
    # defined_not_enumerated -> the designed refusal. enumerated_window ->
    # the windowed count WITH its window and coverage stated; the
    # project-class figure rides as a labeled FLOOR, never a census.
    if MSG_COUNT.search(question):
        if enum.get('messages') == 'defined_not_enumerated':
            emit({
                'class': 'refusal_enumeration_state',
                'answer': ('Not counted yet. The message corpus is defined in the corpus '
                           'definition but has not been enumerated in any manifest version, '
                           'so this record does not state a message count.'),
                'citations': []})
            return
        if enum.get('messages') == 'enumerated_window' and corpus.get('messages_summary'):
            ms = corpus['messages_summary']
            if re.search(r'project|about the (project|contest|build)', question, re.I):
                ans = (f"{ms['project_class_value']} project-class submissions in the "
                       f"enumerated window ({ms['window']}) — a FLOOR, not an exact "
                       f"census: pattern-classified, and project vocabulary evolves "
                       f"faster than pattern sets.")
                if ms.get('project_class_annex_recount'):
                    ans += (f" Annex recount for the same window: "
                            f"{ms['project_class_annex_recount']} (the record store "
                            f"backfills late; the frozen figure lands in the next "
                            f"manifest under the settle-check law).")
            else:
                ans = (f"{ms['total_submissions']} submissions in the enumerated window "
                       f"({ms['window']}). Universe: {ms['universe']}")
            if ms.get('settle_check'):
                sc = ms['settle_check']
                if sc.get('pass2'):
                    ans += (f" Status: {sc['status']} (pass 1: {sc['pass1']}; "
                            f"pass 2: {sc['pass2']}).")
                else:
                    ans += (f" Status: {sc['status']} (pass 1: {sc['pass1']}; pass 2 due "
                            f"{sc.get('pass2_due')} — {sc['rule']}).")
            emit({'class': 'computed', 'answer': ans,
                              'citations': ['corpus-manifest']})
            return

    # 2. pointers, never members — matched by CONTENT, never by list position
    for qpat, ppat in POINTER_TOPICS:
        if qpat.search(question):
            p = next((e for e in corpus.get('pointers_not_members', [])
                      if ppat.search(e.get('what', ''))), None)
            if p:
                emit({
                    'class': 'pointer',
                    'answer': (f"That belongs to another project's record — {p['what']} "
                               f"(owner: {p['owner_project']}; role here: {p['role_here']}). "
                               f"It is cited by this corpus, not a member of it."),
                    'citations': []})
                return

    # 3. computed counts from the manifest, with method
    mcount = COUNT_Q.search(question)
    if mcount:
        kind = mcount.group(1).lower()
        key = kind  # adapter normalizes count keys across manifest versions
        counts = corpus.get('counts', {})
        if key in counts:
            emit({
                'class': 'computed',
                'answer': (f"{counts[key]} {kind} (manifest {corpus.get('manifest_version')}). "
                           f"Counting method: {corpus.get('count_methods', {}).get(key, 'stated in the corpus definition')}"),
                'citations': ['corpus-manifest']})
            return

    # 4. retrieval over member chunks, cited — GATED (vocabulary proof):
    # a distinctive term with ZERO presence in the corpus vocabulary means the
    # corpus provably cannot answer about it -> refusal naming the term.
    # Otherwise AND first; OR only when the top chunk co-presents >=2 terms.
    terms = fts_terms(question)
    con = sqlite3.connect(os.path.join(corpus_dir, 'index.db'))
    hits = []
    if terms:
        def present(t):
            try:
                return con.execute('SELECT 1 FROM chunk_fts WHERE chunk_fts MATCH ? LIMIT 1',
                                   (f'"{t}"',)).fetchone() is not None
            except sqlite3.OperationalError:
                return False
        absent = [t for t in terms if not present(t)]
        if absent:
            emit({
                'class': 'refusal_no_evidence',
                'answer': (f"Not in the record: this corpus contains no mention of "
                           f"'{absent[0]}', so it cannot answer that question."),
                'citations': []})
            return
        def search(match_expr):
            try:
                return con.execute(
                    'SELECT c.unit_id, c.chunk_no, c.text FROM chunk_fts f '
                    'JOIN chunks c ON c.rowid = f.rowid WHERE chunk_fts MATCH ? '
                    'ORDER BY rank LIMIT 3', (match_expr,)).fetchall()
            except sqlite3.OperationalError:
                return []
        rows = search(' AND '.join(f'"{t}"' for t in terms))
        if not rows:
            rows = [r for r in search(' OR '.join(f'"{t}"' for t in terms))
                    if sum(1 for t in terms if t in r[2].lower()) >= 2]
        # per-citation byte currency (Data's surface rule): a living member
        # renders as current bytes under its frozen membership; a settled
        # member renders under the freeze.
        def byte_currency(u):
            row = con.execute('SELECT meta FROM units WHERE unit_id=?', (u,)).fetchone()
            meta = json.loads(row[0]) if row else {}
            if meta.get('member_class') == 'living':
                return ('living document — current bytes under '
                        f"{meta.get('source_asof', 'manifest')} membership")
            return 'settled bytes — as frozen in the manifest'
        hits = [{'unit': u, 'chunk': n, 'text': t[:400],
                 'byte_currency': byte_currency(u)} for u, n, t in rows]
    if hits:
        emit({
            'class': 'retrieval',
            'answer': ('Retrieval (offline build — synthesis tier not active). '
                       'Best-matching record evidence:'),
            'citations': hits})
    else:
        emit({
            'class': 'refusal_no_evidence',
            'answer': 'Not in the record: no member of this corpus matches that question.',
            'citations': []})

if __name__ == '__main__':
    main()
