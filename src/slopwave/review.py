"""Create a read-only phrase review for any track; never rewrite its notes."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from .refinement import PitchEvidence, measure_grid, midi_pitch
from .strudel import ROOT


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def review(data, start, end, audio=None, stem_notes=None, parts=('low', 'middle', 'high')):
    period = 60/data['bpm']
    events = sorted([{'part': part, 'at': at*period, 'duration': duration*period,
                      'pitch': pitch, 'midi': midi_pitch(pitch), 'level': level}
        for part in parts
        for at, duration, pitch, level in data['parts'][part]], key=lambda row: row['at'])
    selected = [row for row in events if start <= row['at'] < end]
    findings = []
    if audio:
        for row in selected:
            if row['part'] == 'low':
                continue
            candidates = audio.octave_candidates(row['midi'], row['at'])
            if candidates:
                findings.append({'kind': 'possible_harmonic_detection', 'event': row,
                    'candidates': candidates,
                    'review': 'Check stem attacks and voice continuity; a lower accompaniment note can also explain this ratio.'})
    # Look at raw model fragments when supplied; otherwise inspect arranged repeats.
    boundaries = (sorted([{'at': row[0], 'duration': row[1]-row[0],
                          'midi': int(row[2]), 'level': row[3], 'part': 'stem'}
                         for row in stem_notes], key=lambda row: row['at'])
                  if stem_notes is not None else events)
    previous = {}
    for row in boundaries:
        key = (row['part'], row['midi'])
        prior = previous.get(key)
        if prior and start <= row['at'] < end and 0 < row['at']-prior['at'] < .6:
            gap = row['at']-prior['at']-prior['duration']
            if -.03 <= gap <= .06:
                findings.append({'kind': 'repeat_or_fragment', 'event': row,
                    'previous_start': prior['at'], 'gap_seconds': gap,
                    'envelope': audio.boundary(row['midi'], prior['at'], row['at']) if audio else None,
                    'review': 'Compare real attacks and holds; do not merge using a dip threshold alone.'})
        previous[key] = row
    lead = [row for row in events if row['part'] == 'high']
    for row in selected:
        if row['part'] != 'middle' or data.get('mode') in ('full-song-stems', 'full-song-arrangement'):
            continue
        before = [note for note in lead if note['at'] < row['at']]
        after = [note for note in lead if note['at'] > row['at']]
        if not before or not after:
            continue
        prev, nxt = before[-1], after[0]
        if (nxt['at']-prev['at'] <= .8 and row['at'] >= prev['at']+prev['duration']-.03
                and max(abs(row['midi']-prev['midi']), abs(row['midi']-nxt['midi'])) <= 12):
            findings.append({'kind': 'possible_lead_register_crossing', 'event': row,
                'review': 'This middle-register note sits inside a lead gap. Review its voice and mix level.'})
    if stem_notes is not None:
        for row in stem_notes:
            at, stop, pitch, amplitude = row[:4]
            if not start <= at < end:
                continue
            if not any(note['midi'] == pitch and abs(note['at']-at) <= .06 for note in events):
                findings.append({'kind': 'unrepresented_stem_candidate',
                    'at': at, 'duration': stop-at, 'midi': pitch, 'amplitude': amplitude,
                    'review': 'May be a missing short note, a held-note fragment, or an overtone; amplitude alone cannot decide.'})
    return {'range_seconds': [start, end], 'parts_reviewed': list(parts), 'events': selected, 'findings': findings,
            'policy': 'Review candidates only. No pitches, attacks, holds, voice assignments, or gains have been changed.'}
