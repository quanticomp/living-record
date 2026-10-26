#!/usr/bin/env python3
"""VTT source support for the harness (built 2026-10-26, $0/offline).

Parses WebVTT caption files into per-video normalized text. Normalization
rides the shop's ONE stage (kill-tony/textnorm.py): entity unescape +
rolling-caption dedupe — the same functions the production corpora use,
never a local reimplementation.
"""
import os, re, sys

sys.path.insert(0, os.path.expanduser('~/workspace/youtube-wiki/kill-tony'))
from textnorm import unescape_entities, dedupe_rolling  # noqa: E402

CUE = re.compile(r'(\d+):(\d+):(\d+)\.\d+\s*-->')

def parse_vtt(path):
    cues, cur = [], None
    for line in open(path, encoding='utf-8', errors='replace'):
        line = line.rstrip('\n')
        m = CUE.match(line)
        if m:
            cur = {'start': int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)),
                   'text': []}
            cues.append(cur)
        elif cur is not None and line.strip() and not line.startswith(('WEBVTT', 'Kind:', 'Language:')):
            cur['text'].append(re.sub(r'<[^>]+>', '', line))
    return [{'start': c['start'], 'text': ' '.join(c['text']).strip()}
            for c in cues if c['text']]

def video_text(path):
    cues = parse_vtt(path)
    joined = ' '.join(c['text'] for c in cues)
    return dedupe_rolling(unescape_entities(joined))

def group_vtt_dir(dirpath):
    """video_id -> best file (en-orig preferred over en)."""
    groups = {}
    for fn in sorted(os.listdir(dirpath)):
        if not fn.endswith('.vtt'):
            continue
        vid = re.sub(r'\.(en-orig|en)\.vtt$', '', fn)
        rank = 0 if fn.endswith('.en-orig.vtt') else 1
        if vid not in groups or rank < groups[vid][0]:
            groups[vid] = (rank, os.path.join(dirpath, fn))
    return {vid: p for vid, (rank, p) in groups.items()}
