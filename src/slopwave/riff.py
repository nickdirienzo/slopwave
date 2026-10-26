"""Save source attack/root cues for sparse instrumental banjo phrases."""
import argparse
import hashlib
import json
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

from .strudel import ROOT, note_name


def infer(source_path, manifest_path, harmonic_path):
    source_path=Path(source_path); manifest_path=Path(manifest_path)
    harmonic_path=Path(harmonic_path)
    source = json.loads(source_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    if manifest['source_audio_sha256'] != source['source_audio_sha256']:
        raise ValueError('Riff evidence/source mismatch')
    features = {}
    for part in ('low', 'middle'):
        entry = manifest['parts'][part]
        for name, key in [('features', 'features_sha256'), ('stem', 'stem_sha256')]:
            if hashlib.sha256((manifest_path.parent/entry[name]).read_bytes()).hexdigest() != entry[key]:
                raise ValueError('Riff evidence archive or stem changed')
        features[part] = dict(np.load(manifest_path.parent/entry['features'], allow_pickle=False))
    audio, sr = sf.read(manifest_path.parent/manifest['parts']['middle']['stem'])
    envelope = librosa.onset.onset_strength(y=audio, sr=sr, hop_length=128)
    normalized = np.minimum(envelope/max(1e-8, np.percentile(envelope, 95)), 1.5)
    frames = librosa.onset.onset_detect(onset_envelope=normalized, sr=sr, hop_length=128,
        normalize=False, units='frames', delta=.06, wait=16, pre_max=7, post_max=7, pre_avg=25, post_avg=8)
    times = librosa.frames_to_time(frames, sr=sr, hop_length=128)
    cues, rejected = [], []
    harmony = json.loads(harmonic_path.read_text())
    if harmony['input_analysis_sha256'] != hashlib.sha256(source_path.read_bytes()).hexdigest():
        raise ValueError('Recompile harmony for this source first')
    histogram = np.asarray(harmony['learned_root_histogram'])
    prior = .035*histogram/max(1, np.max(histogram))
    for at, frame in zip(times, frames):
        if normalized[frame] < .70 or (cues and at-cues[-1]['seconds'] < .14):
            continue
        score = np.zeros(12)
        levels = {}
        for part, f in features.items():
            # Distorted pick transients can resemble unrelated pitches. Infer
            # the chord from the following body while retaining the attack time.
            window = (f['times'] >= at+.08) & (f['times'] < at+.28)
            if not np.any(window):
                continue
            means = np.mean(f['salience'][:, window], axis=1)
            ceiling = 55 if part == 'low' else 65
            chroma = np.array([np.max(means[(f['pitches'] % 12 == pc) & (f['pitches'] <= ceiling)]) for pc in range(12)])
            chroma = np.maximum(0, chroma-np.median(chroma))
            rms = float(np.sqrt(np.mean(f['rms'][window]**2))/max(1e-8, np.percentile(f['rms'], 75)))
            levels[part] = rms
            if rms >= .08:
                score += (2*chroma if part == 'low' else chroma+.45*np.roll(chroma, -7))*min(1, rms)
        if np.max(score) < .045:
            continue
        root = int(np.argmax(score+prior))
        nearby = {w['root'] for w in harmony['windows']
                  if w['start']*60/source['bpm'] < at+.28
                  and w['end']*60/source['bpm'] > at+.08}
        if root not in nearby:
            rejected.append(dict(seconds=float(at), root=root, reason='Attack-body root disagrees with overlapping longer harmonic windows; omit ambiguous fill rather than invent a chord change.'))
            continue
        cues.append(dict(seconds=float(at), root=root, onset_strength=float(normalized[frame]),
                         root_scores=score.tolist(), relative_stem_rms=levels))
    events = []
    for i, cue in enumerate(cues):
        start = cue['seconds']
        end = min(start+.25, (cues[i+1]['seconds']-.025) if i+1 < len(cues) else source['loop_seconds'])
        pitch = 54+(cue['root']-6) % 12
        events.append([round(start*source['bpm']/60, 5), round((end-start)*source['bpm']/60, 5),
                       note_name(pitch), round(.44+.10*min(1, cue['onset_strength']), 4)])
    review = dict(source_audio_sha256=source['source_audio_sha256'],
        input_analysis_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
        harmonic_review_sha256=hashlib.sha256(harmonic_path.read_bytes()).hexdigest(),
        feature_manifest=manifest, events=events, cues=cues, omitted_ambiguous_cues=rejected,
        method='Detected strong backing attacks, with local bass/backing harmonic root evidence; compact single-note banjo register. No arpeggio template.',
        parameters=dict(onset_hop=128, onset_delta=.06, minimum_normalized_strength=.70,
                        minimum_spacing_seconds=.14, pitch_window_after_attack_seconds=[.08,.28],
                        maximum_gate_seconds=.25, midi_range=[54,65]),
        limitation='Rhythmic root reduction of backing, not a transcription of the original guitar solo. Listening verification pending.')
    return review
