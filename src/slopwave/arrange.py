"""Build a separate, repeatable instrumental arrangement from reviewed notes."""
import argparse
from collections import defaultdict
from copy import deepcopy
import hashlib
import json

from .refinement import midi_pitch
from .strudel import ROOT, note_name, strudel_source
from .bluegrass import bluegrass, bluegrass_riff, bluegrass_drive, bluegrass_continuity, bluegrass_performance
from .kazoo import kazoo_rock


def piano_strings(source):
    """Keep the lead; simplify accompaniment and compose quiet string dyads.

    This is orchestration, not a new transcription or a source-pitch correction.
    All timing stays in the original beat coordinate system.
    """
    result = {k: deepcopy(source[k]) for k in
              ('source', 'source_audio_sha256', 'loop_seconds', 'beats', 'bpm', 'beat_offset_seconds')}
    result.update(mode='full-song-arrangement', status='Instrumental arrangement; listening review pending')
    result['parts'] = dict(low=[], middle=[], high=deepcopy(source['parts']['high']),
                           kick=[], snare=[], hat=[])
    bass = []
    for at, duration, name, gain in source['parts']['low']:
        if gain < .03 or duration < .3:
            continue
        pitch = midi_pitch(name)
        while pitch < 36:
            pitch += 12
        while pitch > 55:
            pitch -= 12
        row = [at, duration, note_name(pitch), round(min(.8, gain), 4)]
        # Reduce repeated bass attacks in this arrangement only.
        if (bass and bass[-1][2] == row[2]
                and 0 <= at-bass[-1][0]-bass[-1][1] <= .25):
            bass[-1][1] = round(at+duration-bass[-1][0], 5)
            bass[-1][3] = max(bass[-1][3], row[3])
        else:
            bass.append(row)
    result['parts']['low'] = bass

    def support(rows, start, end):
        scores = defaultdict(float)
        for at, length, pitch, gain in rows:
            overlap = max(0, min(at+length, end)-max(at, start))
            if gain >= .03 and overlap:
                scores[midi_pitch(pitch) % 12] += overlap*gain
        return scores

    # Local two-beat harmonic windows; retain silence where there is no support.
    # Root/fifth voicing avoids inventing major/minor thirds from noisy backing.
    windows = []
    for start in range(0, int(source['beats'])+1, 2):
        end = min(start+2, source['beats'])
        roots = support(bass, start, end)
        backing = support(source['parts']['middle'], start, end)
        scores = roots if sum(roots.values()) >= .2 else backing
        if not scores or sum(scores.values()) < .15:
            continue
        root = max(scores, key=lambda pitch: (scores[pitch], -pitch))
        windows.append(dict(start=start, end=end, root=root,
                            support='bass' if scores is roots else 'backing'))
        # Supply a piano slopwavef where there is no bass or vocal activity (intro/outro).
        if not roots and not support(source['parts']['high'], start, end):
            result['parts']['low'].append([start, round(end-start, 5), note_name(60+root), .38])

    phrases = []
    for window in windows:
        if (phrases and phrases[-1]['root'] == window['root']
                and phrases[-1]['end'] == window['start']
                and window['end']-phrases[-1]['start'] <= 8):
            phrases[-1]['end'] = window['end']
        else:
            phrases.append(dict(window))
    for phrase in phrases:
        start, end, root = phrase['start'], phrase['end'], phrase['root']
        pitch = 48+root
        if pitch < 52:
            pitch += 12
        vocal = bool(support(source['parts']['high'], start, end))
        level = .46 if vocal else .60
        for note in (pitch, pitch+7):
            result['parts']['middle'].append([start, round(end-start, 5), note_name(note), level])
    for rows in result['parts'].values():
        rows.sort()
    result['mix'] = dict(low=.40, middle=.22, high=.78, drums=0)
    result['voices'] = {
        'low': dict(sound='gm_piano', n=1, lpf=4200, attack=.002, decay=.8,
                    sustain=.35, release=.18, pan=.40, room=.20),
        'middle': dict(sound='gm_string_ensemble_1', n=2, lpf=3300, attack=.16,
                       release=.28, pan=.62, room=.30),
        'high': dict(sound='gm_piano', n=1, lpf=6500, attack=.002, decay=1.2,
                     sustain=.45, release=.20, pan=.52, room=.24),
    }
    result['soundfonts'] = {
        'gm_piano': dict(preset='0000_FluidR3_GM_sf2_file', n=1),
        'gm_string_ensemble_1': dict(preset='0480_FluidR3_GM_sf2_file', n=2),
    }
    result['arrangement'] = dict(profile='piano-strings-v1',
        melody_policy='Reviewed vocal events preserved exactly, including pitch, timing and relative gain.',
        accompaniment_policy='Piano bass folded into MIDI 36–55; short/quiet bass events omitted and adjacent repeats joined. Piano fills instrumental windows without bass. Strings play inferred root/fifth dyads from local bass/backing support, up to eight beats per hold.',
        percussion_policy='Omitted for a piano-and-strings instrumental cover.',
        harmonic_windows=windows, listening_review='pending',
        limitation='A new instrumental interpretation, not a recovery of original piano/string parts. Source transcription uncertainties remain.')
    return result


def apply_articulation_review(data, review):
    """Apply source-bound piano ties without rewriting the reviewed source score."""
    if (review['source_audio_sha256'] != data['source_audio_sha256']
            or review['input_analysis_sha256'] != data['arrangement']['input_analysis_sha256']
            or review['profile'] != data['arrangement']['profile']):
        raise ValueError('Articulation review does not match the arrangement source/profile')
    result = deepcopy(data)
    rows = result['parts']['high']
    for edit in review['edits']:
        expected, replacement = edit['expected'], edit['replacement']
        matches = [i for i in range(len(rows)-len(expected)+1)
                   if rows[i:i+len(expected)] == expected]
        if len(expected) < 2 or len(matches) != 1:
            raise ValueError('Reviewed piano phrase changed or was already tied')
        first, last = expected[0], expected[-1]
        if (replacement[0] != first[0] or replacement[2] != first[2] or last[2] != first[2]
                or abs(replacement[0]+replacement[1]-last[0]-last[1]) > 2e-5
                or not 0 <= replacement[3] <= 1):
            raise ValueError('Piano tie must preserve its endpoints and outer pitch')
        for a, b in zip(expected, expected[1:]):
            if not -2e-5 <= (b[0]-a[0]-a[1])*60/data['bpm'] <= .03:
                raise ValueError('Piano tie must not bridge a separate phrase/rest')
        for row in expected:
            if row[2] != first[2] and not (
                    edit.get('kind') == 'piano_neighbor_smoothing'
                    and abs(midi_pitch(row[2])-midi_pitch(first[2])) == 1
                    and row[1]*60/data['bpm'] <= .15):
                raise ValueError('Only explicitly reviewed brief neighboring pitches can be smoothed')
        rows[matches[0]:matches[0]+len(expected)] = [deepcopy(replacement)]
    result['arrangement']['melody_policy'] = (
        'Reviewed melody retained except explicit piano articulation edits: scoped same-pitch ties '
        'and a brief neighboring-pitch smoothing; source transcription unchanged.')
    result['arrangement']['articulation_review'] = deepcopy(review)
    return result
