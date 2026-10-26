"""Acoustic orchestration over a measured pulse, separate from transcription."""
from collections import defaultdict
from copy import deepcopy
import statistics

from .refinement import midi_pitch
from .strudel import note_name


def pulse_anchors(source):
    # Beat tracking may select a half-time or quarter-note pulse. Normalize the
    # accompaniment to a bass pulse near 80–120/min without rescaling the melody.
    measured = [t*source['bpm']/60 for t in source.get('beat_times_seconds', [])]
    if len(measured) < 8 or any(b <= a for a, b in zip(measured, measured[1:])):
        raise ValueError('Bluegrass arrangement needs an increasing measured beat sequence')
    stride = 2 if source['bpm'] > 140 else 1
    anchors = measured[::stride]
    period = statistics.median(b-a for a, b in zip(anchors, anchors[1:]))
    # Extend the measured grid into the pickup/tail; local pitch support still
    # decides whether to play. Keep local drift instead of copying another song's BPM.
    while anchors[0] > 0:
        anchors.insert(0, anchors[0]-period)
    while anchors[-1] < source['beats']:
        anchors.append(anchors[-1]+period)
    return anchors, period, stride


def bluegrass(source, harmonic_review=None):
    result = {k: deepcopy(source[k]) for k in
              ('source', 'source_audio_sha256', 'loop_seconds', 'beats', 'bpm', 'beat_offset_seconds')}
    result.update(mode='full-song-arrangement', status='Bluegrass interpretation; listening review pending')
    parts = dict(low=[], middle=[], high=deepcopy(source['parts']['high']), kick=[], snare=[], hat=[])
    result['parts'] = parts
    anchors, period, stride = pulse_anchors(source)
    reviewed = None
    if harmonic_review is not None:
        if harmonic_review['source_audio_sha256'] != source['source_audio_sha256']:
            raise ValueError('Harmonic evidence belongs to another recording')
        reviewed = {(round(w['start'], 5), round(w['end'], 5)): w for w in harmonic_review['windows']}

    def support(rows, start, end):
        scores = defaultdict(float)
        for at, length, name, gain in rows:
            overlap = max(0., min(at+length, end)-max(at, start))
            if gain >= .03 and overlap:
                scores[midi_pitch(name) % 12] += overlap*gain
        return scores

    def harmony(start, end):
        if reviewed is not None:
            window = reviewed[(round(start, 5), round(end, 5))]
            return (dict(root=window['root'], support='stem harmonic evidence')
                    if window['root'] is not None else None)
        bass = support(source['parts']['low'], start, end)
        backing = support(source['parts']['middle'], start, end)
        if sum(bass.values()) >= .08*(end-start):
            root = max(bass, key=lambda p: (bass[p], -p))
            origin = 'bass'
        elif sum(backing.values()) >= .12*(end-start):
            # Power-chord evidence: prefer a supported root with a fifth above.
            root = max(backing, key=lambda p: (backing[p]+.8*backing.get((p+7)%12, 0), -p))
            origin = 'backing'
        else:
            return None
        return dict(root=root, support=origin)

    def emit(part, at, length, pitch, gain):
        if 0 <= at < source['beats'] and length > 0:
            length = min(length, source['beats']-at)
            if length > .00002:
                parts[part].append([round(at, 5), round(length, 5), note_name(pitch), round(gain, 4)])

    def active_lead(start, end):
        return any(at < end and at+length > start and gain >= .04
                   for at, length, _, gain in source['parts']['high'])

    windows = []
    for pulse, (start, end) in enumerate(zip(anchors, anchors[1:])):
        width = end-start
        for half in range(2):
            left, right = start+half*width/2, start+(half+1)*width/2
            if right <= 0 or left >= source['beats']:
                continue
            chord = harmony(max(0, left), min(source['beats'], right))
            if chord is None:
                continue
            root = chord['root']
            windows.append(dict(start=max(0, left), end=min(source['beats'], right), **chord))
            if half == 0:
                # Alternating root/fifth, kept in an acoustic-bass register.
                pitch = 36+root+(7 if pulse % 2 else 0)
                while pitch > 50:
                    pitch -= 12
                emit('low', left, .66*width, pitch, .76 if pulse % 2 == 0 else .64)
            else:
                # Short "chuck" on the offbeat; open voicing avoids guessing
                # major/minor thirds from distorted power chords.
                base = 48+root
                for index, interval in enumerate((0, 7, 12)):
                    emit('middle', left+index*.006*source['bpm']/60,
                         .23*width, base+interval, (.43, .31, .27)[index])
            # Forward/reverse roll cells only in melody gaps, with a safety
            # margin at phrase entrances so ornament notes do not mask them.
            for step in range(2):
                at = left+step*width/4
                if active_lead(at-.10*width, at+.34*width):
                    continue
                degree = (0, 7, 12, 7, 0, 12, 7, 12)[(pulse*4+half*2+step) % 8]
                base = 55+(root-7) % 12
                emit('high', at, .21*width, base+degree,
                     .40 if half == 0 and step == 0 else .27)
    for rows in parts.values():
        rows.sort()
        for row in rows:
            row[1] = min(row[1], source['beats']-row[0])
    result['mix'] = dict(low=.48, middle=.31, high=.70, drums=0)
    result['voices'] = {
        'low': dict(sound='gm_acoustic_bass', n=1, lpf=2200, attack=.003,
                    release=.06, pan=.42, room=.08),
        'middle': dict(sound='gm_acoustic_guitar_steel', n=3, hpf=160, lpf=5000,
                       attack=.003, release=.045, pan=.68, room=.10),
        'high': dict(sound='gm_banjo', n=0, hpf=180, lpf=6500, attack=.002,
                     release=.055, pan=.46, room=.10),
    }
    result['soundfonts'] = {
        'gm_acoustic_bass': dict(preset='0320_FluidR3_GM_sf2_file', n=1),
        'gm_acoustic_guitar_steel': dict(preset='0250_FluidR3_GM_sf2_file', n=3),
        'gm_banjo': dict(preset='1050_FluidR3_GM_sf2_file', n=0),
    }
    result['arrangement'] = dict(profile='bluegrass-v1',
        melody_policy='Source vocal events retained at their original pitch, timing and level. Quieter banjo rolls composed only in gaps, with entrance clearance.',
        accompaniment_policy='Alternating acoustic root/fifth bass and offbeat steel-guitar root/fifth/octave chops. Harmonic windows follow source bass/backing; no hard key or guessed thirds.',
        percussion_policy='No drum kit; bass and guitar supply the pulse.',
        pulse=dict(measured_beat_stride=stride, median_beats=period, median_seconds=period*60/source['bpm'],
                   anchors_beats=anchors, source='Aligned drum-stem beat tracker; extrapolated only before/after measured anchors'),
        harmonic_windows=windows, composed_roll_notes=len(parts['high'])-len(source['parts']['high']), listening_review='pending',
        limitation='A bluegrass-style instrumental interpretation using GM samples, not a human performance or a verified score. Source transcription uncertainties remain.')
    if harmonic_review is not None:
        result['arrangement']['harmonic_evidence'] = deepcopy(harmonic_review)
    return result


def bluegrass_riff(source, harmonic_review, riff_review):
    """Keep vocal phrases foregrounded; use source attack cues in long gaps."""
    if riff_review['source_audio_sha256'] != source['source_audio_sha256']:
        raise ValueError('Riff evidence belongs to another recording')
    result = bluegrass(source, harmonic_review)
    beat_seconds = 60/source['bpm']
    # Treat short gaps between syllables as part of a vocal phrase. Fill only
    # genuine instrumental sections; never pepper every tiny rest with picking.
    phrases = []
    for at, length, _, gain in source['parts']['high']:
        if gain < .04:
            continue
        if phrases and (at-phrases[-1][1])*beat_seconds < 1.5:
            phrases[-1][1] = max(phrases[-1][1], at+length)
        else:
            phrases.append([at, at+length])
    def instrumental(at, length=0):
        return not any(at < end+.12/beat_seconds and at+length > start-.12/beat_seconds
                       for start, end in phrases)
    riff = [deepcopy(row) for row in riff_review['events'] if instrumental(row[0], row[1])]
    result['parts']['high'] = sorted(deepcopy(source['parts']['high'])+riff)
    # Guitar supports vocal sections; leave instrumental statements uncluttered.
    result['parts']['middle'] = [row for i, row in enumerate(result['parts']['middle'])
                               if not instrumental(row[0], row[1]) and i % 3 != 2]
    result['parts']['low'] = [row for row in result['parts']['low'] if not instrumental(row[0], row[1])]
    previous = None
    for at, length, name, _ in riff:
        pitch = midi_pitch(name) % 12
        # Bass anchors root changes and spaced repeats in the source riff.
        if previous is None or pitch != previous[1] or (at-previous[0])*beat_seconds >= .5:
            result['parts']['low'].append([at, min(length, .22/beat_seconds), note_name(36+pitch), .55])
            previous = (at, pitch)
    result['parts']['low'].sort()
    result['mix'].update(low=.36, middle=.22)
    result['arrangement'].update(profile='bluegrass-riff-v2',
        melody_policy='Source vocal melody preserved exactly. Source attack/root cues supply a compact banjo riff only in long instrumental gaps; no invented rolls.',
        accompaniment_policy='Quiet offbeat guitar dyads and alternating bass under vocals. Instrumental riff gets sparse synchronized root bass and no guitar chops.',
        composed_roll_notes=0, instrumental_riff_notes=len(riff), vocal_phrase_spans=phrases,
        riff_evidence=deepcopy(riff_review),
        listening_review='Previous roll arrangement rejected by user as incomprehensible; sparse riff version awaiting comparison.')
    return result


def bluegrass_drive(source, harmonic_review, riff_review):
    """Restore source rhythmic accents underneath the unchanged sparse lead."""
    result = bluegrass_riff(source, harmonic_review, riff_review)
    seconds_per_beat = 60/source['bpm']
    phrases = result['arrangement']['vocal_phrase_spans']
    guitar, accents = [], []
    previous_root = None
    for cue in riff_review['cues']:
        at = cue['seconds']/seconds_per_beat
        root = cue['root']
        # Let strong attacks and chord changes drive the rhythm. Weaker repeated
        # detections need not become constant strumming or new lead ornamentation.
        changed = root != previous_root
        previous_root = root
        if cue['onset_strength'] < .9 and not changed:
            continue
        vocal = any(start <= at <= end for start, end in phrases)
        energy = min(1.2, max(.65, cue['relative_stem_rms']['middle']**.5))
        strength = min(1.5, cue['onset_strength'])/1.5
        level = (.36+.20*strength)*energy*(.72 if vocal else 1)
        base = 48+root
        for offset, interval, relative in ((0, 0, 1), (.005, 7, .72)):
            onset = at+offset/seconds_per_beat
            if onset >= source['beats']:
                continue
            guitar.append([round(onset, 5), min(round(.12/seconds_per_beat, 5), source['beats']-round(onset, 5)),
                           note_name(base+interval), round(level*relative, 4)])
        accents.append(dict(at=at, root=root, source_strength=cue['onset_strength'],
                            source_energy=energy, under_vocal=vocal))
    result['parts']['middle'] = sorted(guitar)
    for row in result['parts']['low']:
        coincident_kick = any(abs(row[0]-kick[0])*seconds_per_beat <= .09
                              for kick in source['parts'].get('kick', []))
        row[3] = round(min(.9, row[3]*(1.20 if coincident_kick else 1.05)), 4)
    result['mix'].update(low=.42, middle=.32)
    result['voices']['middle'].update(decay=.14, sustain=.08, release=.035)
    result['arrangement'].update(profile='bluegrass-drive-v3',
        accompaniment_policy='Short steel-guitar root/fifth strums follow strong source attacks and chord changes, with source-energy dynamics and reduced levels under vocals. Bass accents coincident source kicks. Sparse banjo riff and melody unchanged.',
        rhythmic_accents=accents,
        listening_review='Sparse riff version lacked original energy according to user; source-accent accompaniment awaiting comparison.')
    return result


def bluegrass_continuity(source, harmonic_review, riff_review):
    """Keep a source-supported rhythm bed when selected riff attacks are sparse."""
    result = bluegrass_drive(source, harmonic_review, riff_review)
    seconds_per_beat = 60/source['bpm']
    windows = harmonic_review['windows']
    original_guitar = deepcopy(result['parts']['middle'])
    original_bass = deepcopy(result['parts']['low'])
    added = dict(low=[], middle=[])
    anchors, _, _ = pulse_anchors(source)
    for window in windows:
        at, end, root = window['start'], window['end'], window['root']
        if root is None:
            continue
        levels = window['relative_stem_rms']
        vocal = any(a < end and a+n > at and g >= .04 for a, n, _, g in source['parts']['high'])
        if (levels['middle'] >= .12 and not any(
                abs(row[0]-at)*seconds_per_beat <= .14 for row in original_guitar)):
            # Sustain the accompaniment between source accents; do not add new
            # melody notes or infer harmony through acoustically quiet windows.
            length = min(end-at, .29/seconds_per_beat)
            level = (.24 if vocal else .32)*min(1.1, levels['middle']**.5)
            for pitch, relative in ((48+root, 1), (55+root, .7)):
                added['middle'].append([round(at, 5), round(length, 5), note_name(pitch), round(level*relative, 4)])
        on_pulse = any(abs(at-anchor) < 1e-6 for anchor in anchors)
        if (on_pulse and levels['low'] >= .12 and not any(
                abs(row[0]-at)*seconds_per_beat <= .22 for row in original_bass)):
            length = min(.40/seconds_per_beat, source['beats']-at)
            added['low'].append([round(at, 5), round(length, 5), note_name(36+root), .52])
    for part, rows in added.items():
        result['parts'][part] = sorted(result['parts'][part]+rows)
        for row in result['parts'][part]:
            row[1] = min(row[1], source['beats']-row[0])
    # Pitched rests are not full-band silence: preserve original drum-only fills
    # with quiet synthesized percussion, without extending chords through them.
    breaks = []
    for window in windows:
        if window['root'] is not None:
            continue
        start, end = window['start'], window['end']
        if any(a < end and a+n > start and g >= .04 for a, n, _, g in source['parts']['high']):
            continue
        breaks.append([start, end])
    for part in ('kick', 'snare', 'hat'):
        result['parts'][part] = [deepcopy(row) for row in source['parts'].get(part, [])
                               if any(a <= row[0] < b for a, b in breaks)]
    result['mix']['drums'] = .14
    result['drum_mix'] = dict(snare=.45, hat=.20)
    result['voices']['middle'].update(decay=.18, sustain=.18, release=.07)
    result['arrangement'].update(profile='bluegrass-continuity-v4',
        accompaniment_policy='Source-accent guitar and bass retained. Quiet guitar dyads and bass pulses bridge sparse detections only in windows with measured stem activity and known harmony.',
        percussion_policy='Quiet synthesized source drum events retained in unpitched breaks; no chords invented across drum-only passages.',
        continuity_additions=added, percussion_break_windows=breaks,
        listening_review='User heard excessive dead silence; source-supported continuity revision awaiting comparison.')
    return result


def bluegrass_performance(source, harmonic_review, riff_review, performance):
    """Apply explicit banjo interpretation decisions without changing source IR."""
    if performance['source_audio_sha256'] != source['source_audio_sha256']:
        raise ValueError('Banjo performance belongs to another recording')
    interpreted = deepcopy(source)
    harmony, riff = deepcopy(harmonic_review), deepcopy(riff_review)
    # Match against the original list before deleting any entries. Applying a
    # reviewed reduction twice, or against a changed score, must fail loudly.
    for edit in performance['lead_edits']:
        if source['parts']['high'][edit['index']] != edit['expected']:
            raise ValueError('Reviewed banjo melody event changed')
        replacement = edit['replacement']
        if replacement is not None and (replacement[:2] != edit['expected'][:2]
                                         or replacement[3] != edit['expected'][3]):
            raise ValueError('Banjo pitch interpretation must preserve timing and gain')
    for edit in sorted(performance['lead_edits'], key=lambda e: e['index'], reverse=True):
        interpreted['parts']['high'][edit['index']:edit['index']+1] = (
            [deepcopy(edit['replacement'])] if edit['replacement'] is not None else [])
    for edit in performance['harmony_edits']:
        window = harmony['windows'][edit['index']]
        if {k: window[k] for k in ('start', 'end', 'root')} != edit['expected']:
            raise ValueError('Reviewed harmony window changed')
        window['inferred_root_before_review'] = window['root']
        window['root'] = edit['replacement_root']
    for edit in performance['riff_edits']:
        index = edit['index']
        if (riff['events'][index] != edit['expected_event']
                or riff['cues'][index]['root'] != edit['expected_root']):
            raise ValueError('Reviewed riff cue changed')
        riff['events'][index] = deepcopy(edit['replacement_event'])
        riff['cues'][index]['inferred_root_before_review'] = riff['cues'][index]['root']
        riff['cues'][index]['root'] = edit['replacement_root']
    result = bluegrass_continuity(interpreted, harmony, riff)
    result['voices']['high']['release'] = .025
    # Preserve the drum-only breaks without importing an electronic drum kit
    # into the acoustic arrangement. These are percussion registers, not chords.
    for part, pitch in (('kick', 'c4'), ('snare', 'g4'), ('hat', 'c5')):
        for row in result['parts'][part]:
            row[2] = pitch
        result['voices'][part] = dict(sound='gm_woodblock', n=3, lpf=4000,
                                    attack=.001, decay=.07, sustain=0, release=.015)
    result['soundfonts']['gm_woodblock'] = dict(n=3, preset='1150_FluidR3_GM_sf2_file')
    result['mix']['drums'] = .09
    result['drum_mix'] = dict(snare=.65, hat=.28)
    result['arrangement'].update(profile='bluegrass-performance-v5',
        percussion_policy='Source break onsets voiced as quiet sampled woodblock taps; no synthetic kick, snare or hats. Percussion registers do not imply harmonic roots.',
        melody_policy='Explicit, source-bound banjo pitch reductions and omission of brief low/unvoiced entries. Original synth score unchanged. Reviewed riff and backing use the same harmonic interpretation.',
        performance_review=deepcopy(performance),
        source_vocal_events=len(source['parts']['high']),
        interpreted_vocal_events=len(interpreted['parts']['high']),
        listening_review='User reported discordance in the banjo itself plus missing backing energy; revised performance and continuity awaiting comparison.')
    return result
