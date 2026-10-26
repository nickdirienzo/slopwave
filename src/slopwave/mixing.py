"""Repeatable synth mix policies applied to a preserved, unmixed arrangement."""
from copy import deepcopy
import numpy as np


def refine_mix(source, profile):
    if profile != 'stem-rock-v1':
        raise ValueError(f'Unknown mix profile: {profile}')
    if 'mix_review' in source:
        raise ValueError('Apply the mix to unmixed analysis, not already mixed gains')
    data = deepcopy(source)
    data['mix'] = dict(low=.24, middle=.08, high=.30, drums=.14)
    data['voices'] = {
        'low': dict(sound='sine', lpf=700, attack=.005, release=.035, pan=.5),
        'middle': dict(sound='sawtooth', hpf=180, lpf=1700, attack=.012, release=.025, pan=.32),
        'high': dict(sound='triangle', lpf=3800, attack=.006, release=.035, pan=.56),
    }
    data['drum_mix'] = dict(snare=.35, hat=.12)
    # Compress only loud notes; never raise quiet stem leakage to a gain floor.
    for row in data['parts']['high']:
        row[3] = round(min(row[3], .55) + max(0, row[3]-.55)/2.5, 4)
    # Evaluate every boundary, including synth tails. A conservative amplitude
    # budget prevents a larger chord from multiplying the backing loudness.
    backing = data['parts']['middle']
    lead = data['parts']['high']
    tail = .025*data['bpm']/60
    lead_tail = .035*data['bpm']/60
    times = np.unique([x for rows, release in ((backing, tail), (lead, lead_tail))
                       for at, length, _, _ in rows for x in (at, at+length+release)])
    amplitude = np.zeros(len(times))
    vocal = np.zeros(len(times))
    for rows, release, envelope in ((backing, tail, amplitude), (lead, lead_tail, vocal)):
        for at, length, _, level in rows:
            envelope[(times >= at) & (times < at+length+release)] += level
    factors = []
    for row in backing:
        at, length, _, level = row
        window = (times >= at) & (times < at+length+tail)
        density = float(np.max(amplitude[window]))
        # Hold one gain for the note: no pumping or added note retriggers.
        vocal_level = float(np.max(vocal[window]))
        factor = min(1., 1.8/max(density, 1e-8)) * (1-.3*min(1., vocal_level/.73))
        row[3] = round(level*factor, 4)
        factors.append(factor)
    data['mix_review'] = {
        'profile': profile, 'notes_and_timing_preserved': True,
        'backing_amplitude_budget': 1.8, 'backing_max_vocal_duck': .3,
        'vocal_compression_threshold': .55, 'vocal_compression_ratio': 2.5,
        'backing_gain_factor_range': [min(factors, default=1), max(factors, default=1)],
        'policy': 'Distinct synths; reduce dense backing chords and backing under vocals; compress loud vocal gains without raising quiet leakage.',
        'listening_review': 'pending',
    }
    return data
