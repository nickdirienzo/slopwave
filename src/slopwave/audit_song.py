"""Read-only whole-song anomaly review for explicitly separated stem voices.

Candidates are not verdicts. Polyphonic backing can contain real octave doubles;
source-supported high notes are not automatically errors.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from .refinement import midi_pitch
from .strudel import ROOT


def audit(data, features, decoder_notes=(), f0=None):
    period = 60/data['bpm']
    findings, summaries = [], {}
    for part in ('low', 'middle', 'high'):
        q = features[part]
        reference = max(1e-8, float(np.percentile(q['rms'], 75)))
        rows = data['parts'][part]
        pitches = [midi_pitch(row[2]) for row in rows]
        summaries[part] = dict(events=len(rows), minimum_midi=min(pitches, default=None), maximum_midi=max(pitches, default=None),
                               reference_rms=reference, source_seconds=[0, data['loop_seconds']])
        for index, row in enumerate(rows):
            at, duration, name, gain = row
            start, end, pitch = at*period, (at+duration)*period, pitches[index]
            window = (q['times'] >= start) & (q['times'] < end)
            if not np.any(window):
                continue
            average = np.mean(q['salience'][:, window], axis=1)
            score = {int(n): float(s) for n, s in zip(q['pitches'], average)}
            rms = float(np.sqrt(np.mean(q['rms'][window]**2))/reference)
            neighbors = [rows[i] for i in (index-1, index+1) if 0 <= i < len(rows)
                         and abs(rows[i][0]*period-start) < max(2, duration*period+.3)]
            neighbor_pitches = [midi_pitch(r[2]) for r in neighbors]
            lower = [n for n in (pitch-12, pitch-24) if n in score]
            candidates = [dict(midi=n, support=score[n], ratio_to_current=score[n]/max(score.get(pitch, 0), 1e-8))
                          for n in lower]
            categories = []
            if part == 'low' and rms < .02 and gain > .05:
                categories.append('quiet_stem_promoted_to_loud_note')
            if any(item['ratio_to_current'] >= 1.25 for item in candidates) and rms >= .02:
                categories.append('stronger_lower_octave')
            if part != 'middle' and gain > .05 and neighbor_pitches and pitch-min(neighbor_pitches) >= 10:
                categories.append('upward_register_outlier')
            if part != 'middle' and gain > .05 and 0 < index < len(rows)-1:
                previous, following = rows[index-1], rows[index+1]
                if (min(pitches[index-1], pitches[index+1])-pitch >= 10
                        and (at-previous[0]-previous[1])*period < .4
                        and (following[0]-at-duration)*period < .4):
                    categories.append('isolated_downward_register_outlier')
            if part == 'high' and pitch >= 75:
                categories.append('upper_vocal_register_review')
            if part == 'middle' and pitch >= 83:
                categories.append('high_backing_pitch_review')
            if part == 'high' and duration*period >= 1.5:
                categories.append('long_vocal_hold_review')
            if not categories:
                continue
            evidence = dict(harmonic_support=score.get(pitch), lower_octaves=candidates,
                            source_rms_relative_to_reference=rms, adjacent_pitches=neighbor_pitches)
            if part == 'high':
                original = next((n for n in decoder_notes if abs(n['start_seconds']-start) < .001), None)
                if original:
                    evidence['raw_note_model_coverage'] = original['raw_model_support_fraction']
                if f0 is not None:
                    fw = (f0['times'] >= start) & (f0['times'] < end)
                    valid = fw & np.isfinite(f0['f0'])
                    evidence['voiced_fraction'] = float(np.sum(valid)/max(1, np.sum(fw)))
                    evidence['mean_voicing_probability'] = float(np.mean(f0['probability'][valid])) if np.any(valid) else 0
            findings.append(dict(id=f'{part}:{index}', part=part, event=row,
                source_seconds=[start, end], kinds=categories, evidence=evidence,
                disposition='candidate; source and phrase review required'))
    drums = {}
    for part in ('kick', 'snare', 'hat'):
        rows = data['parts'][part]
        drums[part] = dict(events=len(rows),
            invalid_events=sum(not (0 <= at < at+length <= data['beats'] and 0 <= gain <= 1)
                               for at, length, _, gain in rows))
    return dict(source_audio_sha256=data['source_audio_sha256'], coverage=summaries,
        percussion_structural_checks=drums, findings=findings,
        policy='Read-only candidates; no pitch ceiling or automatic octave folding.',
        limits='Numerical source review, not a full listening transcription. Percussion checks are structural; backing polyphony makes octave attribution ambiguous.')
