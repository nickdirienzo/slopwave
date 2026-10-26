"""Phrase decoding for a separated vocal: acoustic evidence plus continuity.

This produces a musical hypothesis, not a verified score. No lyrics or fixed key
are supplied, and rests cannot be filled solely from a repeated phrase.
"""
import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.signal import find_peaks


def harmonic_features(audio, sr, hop=256, pitches=None, n_fft=4096):
    import librosa
    spectrum = abs(librosa.stft(audio, n_fft=n_fft, hop_length=hop))
    frequencies = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    background = uniform_filter1d(spectrum, size=41, axis=0)
    background += np.max(spectrum, axis=0)[None, :]*.015 + 1e-8
    contrast = np.minimum(spectrum/background, 6)/6
    pitches = np.arange(48, 85) if pitches is None else np.asarray(pitches)
    salience, odd = [], []
    for pitch in pitches:
        partials = []
        hz = librosa.midi_to_hz(pitch)
        for harmonic in range(1, 7):
            band = ((frequencies > hz*harmonic*2**(-.45/12)) &
                    (frequencies < hz*harmonic*2**(.45/12)))
            if not np.any(band):
                band[np.argmin(abs(frequencies-hz*harmonic))] = True
            partials.append(np.max(contrast[band], axis=0))
        partials = np.asarray(partials)
        salience.append(np.average(partials, axis=0, weights=1/np.sqrt(np.arange(1, 7))))
        odd.append(np.mean(partials[[0, 2, 4]], axis=0))
    rms = librosa.feature.rms(y=audio, frame_length=1024, hop_length=hop)[0]
    return dict(times=librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop),
                pitches=pitches, salience=np.asarray(salience), odd=np.asarray(odd), rms=rms)


def sequence_path(emissions, pitches, switch_cost=4.):
    """Viterbi path; last emission state is rest, transitions penalize flicker."""
    count, frames = emissions.shape
    distance = abs(pitches[:, None]-pitches[None, :])
    transition = np.full((count, count), 1.2)
    transition[:-1, :-1] = switch_cost + .07*np.minimum(distance, 12)
    transition[:-1, :-1] += 8*(distance >= 10)
    np.fill_diagonal(transition, 0)
    back = np.zeros((frames, count), dtype=np.int16)
    score = emissions[:, 0].copy()
    for frame in range(1, frames):
        candidates = score[:, None]-transition
        winners = np.argmax(candidates, axis=0)
        back[frame] = winners
        score = candidates[winners, np.arange(count)] + emissions[:, frame]
    path = np.empty(frames, dtype=np.int16)
    path[-1] = np.argmax(score)
    for frame in range(frames-1, 0, -1):
        path[frame-1] = back[frame, path[frame]]
    return path


def join_short_fragments(path, emissions, activity, dt):
    """Assign tiny pitch fragments to supported neighbors instead of deleting them."""
    path = path.copy()
    rest = emissions.shape[0]-1
    edits = []
    for _ in range(2):
        boundaries = np.flatnonzero(np.r_[True, np.diff(path) != 0, True])
        for start, end in zip(boundaries[:-1], boundaries[1:]):
            if start == 0 or end == len(path) or (end-start)*dt >= .065:
                continue
            before, after, current = int(path[start-1]), int(path[end]), int(path[start])
            if current == rest:
                if before != after or before == rest or np.mean(activity[start:end]) < .2:
                    continue
                replacement = before
            else:
                neighbors = [state for state in (before, after) if state != rest]
                if not neighbors:
                    continue
                replacement = max(neighbors, key=lambda state: np.sum(emissions[state, start:end]))
            path[start:end] = replacement
            edits.append(dict(start_frame=int(start), end_frame=int(end), before=current, after=replacement))
    return path, edits


def repetition_support(features, activity):
    """Borrow weak pitch-class support only across acoustically similar windows."""
    times, pitches, salience = (features[key] for key in ('times', 'pitches', 'salience'))
    step = 8
    chroma = np.asarray([np.max(salience[pitches % 12 == pc], axis=0) for pc in range(12)])
    chroma -= np.mean(chroma, axis=0)
    chroma /= np.linalg.norm(chroma, axis=0)+1e-8
    coarse = chroma[:, ::step] * activity[::step][None, :]
    dt = times[1]-times[0]
    maximum = min(len(coarse[0])-1, int(140/(dt*step)))
    correlation = np.array([np.mean(np.sum(coarse[:, lag:]*coarse[:, :-lag], axis=0))
                            for lag in range(1, maximum+1)])
    peaks, _ = find_peaks(correlation, distance=max(1, round(3/(dt*step))))
    peaks = [i for i in peaks if (i+1)*dt*step >= 15]
    best = sorted(peaks, key=lambda i: correlation[i], reverse=True)[:4]
    support = np.zeros_like(chroma)
    weight = np.zeros(len(times))
    evidence = []
    for i in best:
        lag = (i+1)*step
        similarity = np.sum(chroma[:, lag:]*chroma[:, :-lag], axis=0)
        similarity = uniform_filter1d(similarity, size=max(1, round(2.4/dt)), mode='constant')
        reliable = (similarity > .72) & (activity[lag:] > .5) & (activity[:-lag] > .5)
        confidence = np.where(reliable, (similarity-.72)/.28, 0)
        support[:, lag:] += chroma[:, :-lag]*confidence
        support[:, :-lag] += chroma[:, lag:]*confidence
        weight[lag:] += confidence
        weight[:-lag] += confidence
        evidence.append(dict(lag_seconds=float(lag*dt), global_similarity=float(correlation[i]),
                             supported_seconds=float(np.sum(reliable)*dt)))
    support /= np.maximum(1, weight)[None, :]
    return support[pitches % 12], evidence


def decode_vocal(features, raw_notes, f0_times, f0, probability, reference_rms):
    times, pitches, salience, odd, rms = (features[key] for key in
        ('times', 'pitches', 'salience', 'odd', 'rms'))
    dt = float(times[1]-times[0])
    activity = np.clip((rms/reference_rms-.08)/.45, 0, 1)
    activity *= np.clip((np.max(salience, axis=0)-.18)/.15, 0, 1)
    activity = uniform_filter1d(activity, size=5)
    model = np.zeros_like(salience)
    for start, end, pitch, confidence in raw_notes:
        index = np.where(pitches == pitch)[0]
        if len(index):
            window = (times >= start) & (times < end)
            model[index[0], window] = np.maximum(model[index[0], window], confidence)
    model_pc = np.asarray([np.max(model[pitches % 12 == pitch % 12], axis=0) for pitch in pitches])
    # pYIN itself can follow an overtone. Most of its support is octave-neutral;
    # the harmonic series and sequence decide the register together.
    nearest = np.clip(np.searchsorted(f0_times, times), 0, len(f0_times)-1)
    midi = np.full(len(times), -100.)
    valid = np.isfinite(f0[nearest]) & (f0[nearest] > 0)
    midi[valid] = 69+12*np.log2(f0[nearest][valid]/440)
    distance = abs(pitches[:, None]-midi[None, :])
    pc_distance = np.minimum(distance % 12, 12-distance % 12)
    reliability = np.where(valid, np.clip(probability[nearest]*3, 0, 1), 0)
    fundamental = np.exp(-distance**2/(2*.55**2))*reliability
    pitch_class = np.exp(-pc_distance**2/(2*.55**2))*reliability
    repeats, repeat_evidence = repetition_support(features, activity)
    # Learn a weak tonal vocabulary from this recording. Ambiguous relative
    # scales are combined; chromatic evidence can always outweigh this prior.
    strong = (activity > .6) & (np.max(salience, axis=0) > .3)
    classes = pitches[np.argmax(salience, axis=0)] % 12
    histogram = np.bincount(classes[strong], minlength=12).astype(float)
    histogram /= max(1, np.sum(histogram))
    scales = [sorted((np.array([0, 2, 4, 5, 7, 9, 11])+root) % 12) for root in range(12)]
    masses = [float(np.sum(histogram[scale])) for scale in scales]
    vocabulary = sorted({int(pc) for scale, mass in zip(scales, masses)
                         if mass >= max(masses)-.02 for pc in scale}) if max(masses) > .9 else list(range(12))
    tonal_penalty = np.array([0 if pitch % 12 in vocabulary else .5 for pitch in pitches])
    score = (8*salience + .6*odd + .8*model_pc + .15*model
             + .4*pitch_class + .2*fundamental + .65*repeats - tonal_penalty[:, None])
    score *= activity[None, :]
    rest = .9+1.6*(1-activity)
    emissions = np.vstack([score, rest])
    path, joins = join_short_fragments(sequence_path(emissions, pitches), emissions, activity, dt)
    # Same-pitch retriggers need an actual envelope dip plus a fresh rise.
    # Neural-model boundaries alone do not create syllable attacks.
    smooth = uniform_filter1d(rms, size=3)
    troughs, _ = find_peaks(-smooth, distance=max(1, round(.10/dt)))
    attacks = set()
    for index in troughs:
        width = round(.09/dt)
        before = np.max(smooth[max(0, index-width):index+1])
        after = np.max(smooth[index:min(len(smooth), index+width+1)])
        if (min(before, after) > reference_rms*.18 and
                smooth[index] < .48*min(before, after)):
            attacks.add(int(index))
    boundaries = np.flatnonzero(np.r_[True, np.diff(path) != 0, True])
    notes, evidence = [], []
    for start, end in zip(boundaries[:-1], boundaries[1:]):
        state = int(path[start])
        if state == len(pitches):
            continue
        cuts = [start] + sorted(i for i in attacks if start+.10/dt < i < end-.10/dt) + [end]
        for left, right in zip(cuts[:-1], cuts[1:]):
            if (right-left)*dt < .065:
                continue
            level = min(.9, .68*np.sqrt(float(np.mean(rms[left:right]**2)))/reference_rms)
            notes.append([float(times[left]), float(min(times[-1], right*dt)), int(pitches[state]), level])
            evidence.append(dict(start_seconds=float(times[left]), end_seconds=float(right*dt),
                midi=int(pitches[state]), mean_harmonic_support=float(np.mean(salience[state, left:right])),
                mean_activity=float(np.mean(activity[left:right])),
                raw_model_support_fraction=float(np.mean(model_pc[state, left:right] > .1)),
                inferred_without_raw_model=bool(np.mean(model_pc[state, left:right] > .1) < .5)))
    return notes, dict(method='harmonic-series evidence + Viterbi continuity + acoustic repetition support + envelope articulation',
                       repeat_matches=repeat_evidence, notes=evidence, short_fragment_joins=joins,
                       tonal_prior=dict(pitch_classes=vocabulary, strongest_scale_mass=max(masses),
                                        outside_vocabulary_penalty=.5, hard_key_quantization=False),
                       parameters=dict(pitch_range_midi=[48, 84], minimum_note_seconds=.065,
                                       switch_cost=4., octave_jump_cost=8., repetition_similarity_minimum=.72))
