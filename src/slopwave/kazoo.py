"""Kazoo-like synthesis over source-timed rock accompaniment."""
from copy import deepcopy


def kazoo_rock(source):
    if source.get('mix_review', {}).get('profile') != 'stem-rock-v1':
        raise ValueError('Kazoo profile expects the once-mixed stem-rock source')
    result = deepcopy(source)
    result.update(mode='full-song-arrangement', status='Kazoo-like synth cover; listening review pending')
    result['mix'] = dict(low=.25, middle=.10, high=.44, drums=.27)
    result['voices'] = {
        'low': dict(sound='sine', lpf=800, attack=.005, release=.04, pan=.5),
        'middle': dict(sound='triangle', hpf=150, lpf=1900, attack=.008, release=.05, pan=.30),
        'high': dict(sound='sawtooth', hpf=170, lpf=3200, bpf=1150, bpq=.65,
                     vib=5.2, vibmod=.10, attack=.015, decay=.08,
                     sustain=.82, release=.045, pan=.56),
        'kick': dict(sound='cover_kick', lpf=1800, pan=.5),
        'snare': dict(sound='cover_snare', hpf=120, lpf=6500, pan=.48),
        'hat': dict(sound='cover_hat', hpf=4000, lpf=10000, pan=.62),
    }
    base = 'https://cdn.jsdelivr.net/gh/sgossner/VCSL@master/'
    result['sample_buffers'] = {
        'cover_kick': dict(url=base+'Membranophones/Struck%20Membranophones/Bass%20Drum%201/BDrumNew_hit_v5_rr1_Sum.wav', seconds=.34),
        'cover_snare': dict(url=base+'Membranophones/Struck%20Membranophones/Snare%20Drum%2C%20Modern%201/Snare2_HitSN_v5_rr1_Mid.wav', seconds=.28),
        'cover_hat': dict(url=base+'Idiophones/Struck%20Idiophones/Hi-Hat%20Cymbal/HiHat_HitC_v3_rr1_Mid.wav', seconds=.10),
    }
    result['drum_mix'] = dict(snare=.85, hat=.32)
    result['arrangement'] = dict(profile='kazoo-rock-v1',
        melody_policy='All source pitches, attacks, holds, rests and relative gains preserved; no second mix compression pass.',
        timbre_policy='Synthesized kazoo approximation: nasal filtered saw and restrained vibrato. Not a recorded kazoo. Added noise omitted because current Strudel noise crossfade cleanup throws on note endings.',
        backing_policy='Retain source-timed bass and polyphonic backing, including instrumental passages; melody remains foreground.',
        percussion_policy='Source drum onsets with preloaded VCSL acoustic bass drum, snare and hi-hat one-shots; short natural tails independent of event gates.',
        sample_license='VCSL CC0: https://github.com/sgossner/VCSL',
        listening_review='Pending user comparison.')
    return result
