"""Reusable measurements for transcription review, never automatic musical edits.

Beat grids, envelope dips and harmonic ratios are evidence, not musical truth.
Use separated stems where possible and retain a human review step.
"""
from dataclasses import dataclass
import math
import re
from copy import deepcopy
import hashlib
import json

import numpy as np


def apply_instrument_review(source, review):
    """Apply exact, reviewed bass/backing edits before mixing, including merges."""
    if source['source_audio_sha256'] != review['source_audio_sha256'] or 'mix_review' in source:
        raise ValueError('Instrument review needs its matching unmixed source')
    data = deepcopy(source)
    for edit in review['edits']:
        part = edit['part']
        if part not in ('low', 'middle') or not edit['expected']:
            raise ValueError('Instrument review must target explicit bass/backing events')
        rows = data['parts'][part]
        indices = []
        for expected in edit['expected']:
            matches = [i for i, row in enumerate(rows) if row == expected]
            if len(matches) != 1 or matches[0] in indices:
                raise ValueError('Reviewed instrument event changed or was selected twice')
            indices.append(matches[0])
        first = min(row[0] for row in edit['expected'])
        last = max(row[0]+row[1] for row in edit['expected'])
        for at, duration, pitch, level in edit['replacement']:
            midi_pitch(pitch)
            if not (first-2e-5 <= at < at+duration <= last+2e-5 and 0 <= level <= 1):
                raise ValueError('Instrument correction exceeds its reviewed span')
        data['parts'][part] = sorted([row for i, row in enumerate(rows) if i not in indices]
                                     + deepcopy(edit['replacement']))
    data['instrument_review'] = deepcopy(review)
    return data


def apply_vocal_corrections(review, corrections):
    """Reapply scoped listening corrections only to their exact decoder events."""
    if review['source_audio_sha256'] != corrections['source_audio_sha256']:
        raise ValueError('Vocal corrections belong to a different recording')
    if corrections.get('additions'):
        digest = hashlib.sha256(json.dumps(review['events'], separators=(',', ':')).encode()).hexdigest()
        if corrections.get('input_decoder_events_sha256') != digest:
            raise ValueError('Vocal addition decoder inputs changed; re-review before applying')
    result = deepcopy(review)
    for edit in corrections['edits']:
        expected, replacement = edit['expected'], edit['replacement']
        matches = [i for i, row in enumerate(result['events']) if row == expected]
        if len(matches) != 1:
            raise ValueError('Reviewed vocal event changed; re-review before applying correction')
        if replacement is None:
            result['events'].pop(matches[0])
        else:
            if replacement[:2] != expected[:2] or replacement[3] != expected[3]:
                raise ValueError('This correction supports pitch changes or deletion only')
            midi_pitch(replacement[2])
            result['events'][matches[0]] = list(replacement)
    for addition in corrections.get('additions', []):
        event = addition['event']
        at, length, pitch, level = event
        midi_pitch(pitch)
        if not (at >= 0 and length > 0 and 0 <= level <= 1):
            raise ValueError('Invalid reviewed vocal addition')
        if any(row[0] < at+length-2e-5 and row[0]+row[1] > at+2e-5
               for row in result['events']):
            raise ValueError('Reviewed vocal addition overlaps an existing phrase')
        result['events'].append(deepcopy(event))
        result['events'].sort()
    result['decoder_notes'] = review['after_notes']
    result['after_notes'] = len(result['events'])
    result['evidence_stage'] = 'Unmodified decoder output; scoped corrections are recorded separately.'
    result['reviewed_corrections'] = deepcopy(corrections)
    return result


def apply_vocal_phrase_review(source, review):
    if source['source_audio_sha256'] != review['source_audio_sha256']:
        raise ValueError('Phrase review belongs to a different recording')
    digest = hashlib.sha256(json.dumps(source['parts']['high'], separators=(',', ':')).encode()).hexdigest()
    if digest != review['input_vocal_events_sha256']:
        raise ValueError('Vocal detections changed; rebuild the phrase review')
    events = review['events']
    end = 0
    for at, length, pitch, level in events:
        midi_pitch(pitch)
        if not (at >= end-2e-5 and 0 <= at < at+length <= source['beats'] and 0 <= level <= 1):
            raise ValueError('Invalid or overlapping phrase events')
        end = at+length
    data = deepcopy(source)
    data['parts']['high'] = deepcopy(events)
    data['vocal_phrase_review'] = {key: value for key, value in review.items() if key != 'events'}
    data['vocal_dynamics'] = dict(reference_rms=source['vocal_dynamics']['reference_rms'],
        method='Phrase source RMS scaled by 0.68/reference, capped at 0.9 before mix compression; no confidence gain or minimum-volume floor.')
    data['voice_selection'] = 'Bass dominant confidence line; backing polyphony; vocal acoustic phrase decoder. No grid snapping.'
    return data


def apply_reviewed_additions(source, review):
    """Apply explicit source-bound additions; reject overlaps or double application."""
    if source['source_audio_sha256'] != review['source_audio_sha256']:
        raise ValueError('Note review belongs to a different source recording')
    data = deepcopy(source)
    for item in review['additions']:
        part, event = item['part'], item['event']
        at, length, pitch, level = event
        midi_pitch(pitch)
        if not (0 <= at < at+length <= data['beats'] and 0 <= level <= 1):
            raise ValueError('Invalid reviewed event')
        if any(row[0] < at+length-2e-5 and row[0]+row[1] > at+2e-5
               for row in data['parts'][part]):
            raise ValueError('Reviewed addition overlaps an existing voice event')
        data['parts'][part].append(list(event))
        data['parts'][part].sort()
    data['note_review'] = review
    return data


def midi_pitch(name):
    if isinstance(name, (int, float)):
        pitch = int(name)
        if pitch != name or not 0 <= pitch <= 127:
            raise ValueError('MIDI pitch must be an integer from 0 to 127')
        return pitch
    match = re.fullmatch(r'([a-g])(s?)(-?\d+)', name)
    if not match:
        raise ValueError(f'Unsupported pitch: {name}')
    letter, sharp, octave = match.groups()
    pitch = (int(octave)+1)*12 + {'c': 0, 'd': 2, 'e': 4, 'f': 5,
        'g': 7, 'a': 9, 'b': 11}[letter] + bool(sharp)
    return midi_pitch(pitch)


@dataclass(frozen=True)
class BeatGrid:
    bpm: float
    phase_seconds: float
    subdivisions: int = 4

    def __post_init__(self):
        if not math.isfinite(self.bpm) or self.bpm <= 0:
            raise ValueError('BPM must be finite and positive')
        if not math.isfinite(self.phase_seconds):
            raise ValueError('Grid phase must be finite')
        if not isinstance(self.subdivisions, int) or self.subdivisions < 1:
            raise ValueError('Subdivisions must be a positive integer')

    def snap_beat(self, seconds):
        if not math.isfinite(seconds):
            raise ValueError('Attack time must be finite')
        period = 60/self.bpm
        phase = self.phase_seconds/period
        return round(phase + round((seconds/period-phase)*self.subdivisions)
                     / self.subdivisions, 5)


def measure_grid(attacks, bpm, subdivisions=2):
    """Measure phase and fit at a supplied tempo; do not infer a snap policy.

    A fine subdivision can fit swung or syncopated material misleadingly well.
    Inspect multiple subdivisions and the actual phrase before quantizing.
    """
    BeatGrid(bpm, 0, subdivisions)
    attacks = np.asarray(attacks, dtype=float)
    if attacks.ndim != 1 or len(attacks) < 8 or not np.all(np.isfinite(attacks)):
        raise ValueError('At least eight finite, one-dimensional attack times are required')
    spacing = 60/bpm/subdivisions
    vector = np.mean(np.exp(2j*np.pi*attacks/spacing))
    phase = float(np.angle(vector)/(2*np.pi)*spacing)
    residual = attacks-(phase+np.rint((attacks-phase)/spacing)*spacing)
    return {'bpm': float(bpm), 'subdivisions': subdivisions,
            'phase_seconds': phase, 'attack_count': len(attacks),
            'phase_concentration': float(abs(vector)),
            'median_error_ms': float(np.median(abs(residual))*1000),
            'p90_error_ms': float(np.percentile(abs(residual), 90)*1000),
            'automatic_quantization_authorized': False}


class PitchEvidence:
    """Pitch-band envelopes from one audio excerpt, with absolute source times."""
    def __init__(self, audio, sample_rate, offset_seconds=0, n_fft=4096, hop=64):
        import librosa
        audio = np.asarray(audio, dtype=float)
        if audio.ndim != 1 or len(audio) < n_fft or not np.all(np.isfinite(audio)):
            raise ValueError('Provide a finite mono excerpt at least n_fft samples long')
        if sample_rate <= 0 or hop <= 0 or not math.isfinite(offset_seconds):
            raise ValueError('Invalid sample rate, hop, or time offset')
        self.spectrum = abs(librosa.stft(audio, n_fft=n_fft, hop_length=hop))
        self.times = np.arange(self.spectrum.shape[1])*hop/sample_rate + offset_seconds
        self.frequencies = np.fft.rfftfreq(n_fft, 1/sample_rate)
        self.sample_rate = sample_rate
        self.n_fft = n_fft
        self.hop = hop
        self.cache = {}

    def envelope(self, pitch):
        pitch = midi_pitch(pitch)
        if pitch not in self.cache:
            hz = 440*2**((pitch-69)/12)
            band = (self.frequencies > hz*.98) & (self.frequencies < hz*1.02)
            # Low notes may fall between FFT bins. Do not invent evidence.
            self.cache[pitch] = (np.sqrt(np.mean(self.spectrum[band]**2, axis=0))
                                 if np.any(band) else None)
        return self.cache[pitch]

    def peak(self, pitch, start, end):
        envelope = self.envelope(pitch)
        window = (self.times >= start) & (self.times < end)
        if envelope is None or not np.any(window):
            return None
        return float(np.max(envelope[window]))

    def octave_candidates(self, pitch, at, ratio_threshold=3):
        """Flag stronger lower octaves; a simultaneous bass note can also cause this."""
        pitch = midi_pitch(pitch)
        detected = self.peak(pitch, at+.02, at+.17)
        if detected is None or detected < 1e-8:
            return []
        candidates = []
        for semitones in (12, 24):
            lower = pitch-semitones
            if lower < 0:
                continue
            peak = self.peak(lower, at+.02, at+.17)
            if peak is not None and peak/detected >= ratio_threshold:
                candidates.append({'candidate_midi': lower, 'lower_band_peak': peak,
                                   'detected_band_peak': detected, 'ratio': peak/detected})
        return candidates

    def boundary(self, pitch, previous_start, boundary):
        """Return a dip ratio, without declaring a repeat or merging notes.

        Earlier experiments showed that one global dip threshold misclassifies
        real repeated attacks. Review onset timing and neighboring notes too.
        """
        envelope = self.envelope(pitch)
        if envelope is None:
            return None
        windows = [(max(previous_start, boundary-.16), boundary-.035),
                   (boundary+.035, boundary+.14), (boundary-.045, boundary+.035)]
        values = [envelope[(self.times >= start) & (self.times < end)]
                  for start, end in windows]
        if any(len(value) == 0 for value in values):
            return None
        before, after, trough = float(max(values[0])), float(max(values[1])), float(min(values[2]))
        if min(before, after) < 1e-8:
            return None
        return {'before_peak': before, 'after_peak': after, 'trough': trough,
                'dip_ratio': trough/min(before, after)}


def dominant_line(notes):
    """Choose the strongest overlapping detection; keep distinct model attacks.

    This is a draft voice-selection policy, not proof of the intended melody.
    Sustained-note fragment decisions are left to phrase review.
    """
    changes = {}
    for index, (start, end, pitch, level) in enumerate(notes):
        changes.setdefault(start, []).append((True, index))
        changes.setdefault(end, []).append((False, index))
    times = sorted(changes)
    active = set()
    segments = []
    for i, at in enumerate(times[:-1]):
        for add, index in changes[at]:
            if add:
                active.add(index)
            else:
                active.discard(index)
        if not active:
            continue
        winner = max(active, key=lambda index: (notes[index][3], -index))
        end = times[i+1]
        if segments and segments[-1][0] == winner and abs(segments[-1][2]-at) < 1e-8:
            segments[-1][2] = end
        else:
            segments.append([winner, at, end])
    return [[start, end, notes[index][2], notes[index][3]]
            for index, start, end in segments if end-start >= .045]


def vocal_octaves(notes, times, f0, probability):
    """Correct octave-only disagreements supported by stable periodicity and context.

    Designed for a separated monophonic vocal line. Does not apply to chords.
    Ambiguous/unvoiced spans retain their original model pitch for listening review.
    """
    corrected = [list(row) for row in notes]
    evidence = []
    for i, (start, end, pitch, level) in enumerate(notes):
        window = (times >= start) & (times < end)
        valid = window & np.isfinite(f0) & (f0 > 0)
        if not np.any(window) or np.sum(valid)/np.sum(window) < .7:
            continue
        semitones = 69+12*np.log2(f0[valid]/440)
        median = float(np.median(semitones))
        candidate = round(median)
        spread = float(np.median(abs(semitones-median)))
        confidence = float(np.mean(probability[valid]))
        neighbor = any(j != i and abs(row[0]-start) <= .8 and abs(row[2]-candidate) <= 2
                       for j, row in enumerate(notes))
        if (pitch-candidate in (12, 24) and abs(median-candidate) < .45
                and spread < .35 and confidence >= .08 and neighbor):
            corrected[i][2] = candidate
            evidence.append({'start_seconds': start, 'before_midi': pitch, 'after_midi': candidate,
                'median_f0_midi': median, 'median_absolute_deviation': spread,
                'mean_voicing_probability': confidence,
                'voiced_fraction': float(np.sum(valid)/np.sum(window))})
    return corrected, evidence
