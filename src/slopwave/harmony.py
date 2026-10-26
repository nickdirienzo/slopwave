"""Compile source-bound harmonic windows for an acoustic arrangement.

Requires the aligned, hashed feature manifest used by audit_song.py. No source
notes are changed; this evidence supplies the arrangement's new accompaniment.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

from .bluegrass import pulse_anchors
from .strudel import ROOT


def infer(source_path, manifest_path):
    source_path=Path(source_path); manifest_path=Path(manifest_path)
    source = json.loads(source_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    if source['source_audio_sha256'] != manifest['source_audio_sha256']:
        raise ValueError('Harmonic features/source mismatch')
    features = {}
    for part in ('low', 'middle'):
        entry = manifest['parts'][part]
        path = manifest_path.parent/entry['features']
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['features_sha256']:
            raise ValueError('Feature archive changed')
        features[part] = dict(np.load(path, allow_pickle=False))
    anchors, _, _ = pulse_anchors(source)
    windows, emissions = [], []
    for start, end in zip(anchors, anchors[1:]):
        for half in range(2):
            left = max(0, start+(end-start)*half/2)
            right = min(source['beats'], start+(end-start)*(half+1)/2)
            if left >= right:
                continue
            score = np.zeros(12)
            levels = {}
            for part in ('low', 'middle'):
                f = features[part]
                mask = (f['times'] >= left*60/source['bpm']) & (f['times'] < right*60/source['bpm'])
                mean = np.mean(f['salience'][:, mask], axis=1)
                ceiling = 55 if part == 'low' else 65
                chroma = np.array([np.max(mean[(f['pitches'] % 12 == pc) & (f['pitches'] <= ceiling)]) for pc in range(12)])
                # Remove the broad noise floor before weighing pitched support.
                chroma = np.maximum(0, chroma-np.median(chroma))
                rms = float(np.sqrt(np.mean(f['rms'][mask]**2))/max(1e-8, np.percentile(f['rms'], 75)))
                levels[part] = rms
                if rms < .08:
                    continue
                if part == 'low':
                    score += 2*min(1, rms)*chroma
                else:
                    score += min(1, rms)*(chroma+.45*np.roll(chroma, -7))
            windows.append(dict(start=left, end=right, relative_stem_rms=levels))
            emissions.append(score)
    emissions = np.asarray(emissions)
    # A soft, recording-learned root vocabulary reduces isolated noisy chromatic
    # guesses. It cannot force an unsupported root or fill acoustically quiet bars.
    reliable = np.max(emissions, axis=1) > .15
    histogram = np.bincount(np.argmax(emissions[reliable], axis=1), minlength=12)
    prior = .035*histogram/max(1, np.max(histogram))
    previous = None
    for window, score in zip(windows, emissions):
        adjusted = score+prior
        if previous is not None:
            adjusted[previous] += .018
        root = int(np.argmax(adjusted)) if np.max(score) >= .045 else None
        window.update(root=root, root_scores=score.tolist(), support_margin=float(np.sort(adjusted)[-1]-np.sort(adjusted)[-2]))
        previous = root
    review = dict(source_audio_sha256=source['source_audio_sha256'],
                  input_analysis_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
                  feature_manifest=manifest, windows=windows, learned_root_histogram=histogram.tolist(),
                  method='RMS-gated harmonic-series root/fifth evidence from bass/backing, weak learned vocabulary and continuity; no hard key.',
                  parameters=dict(minimum_relative_rms=.08, minimum_support=.045, prior_maximum=.035, continuity_bonus=.018),
                  listening_review='pending; roots are arrangement inferences, not verified source chords')
    return review
