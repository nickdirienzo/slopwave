"""Original repeat, pulse, and percussion heuristics; analysis extra required."""
import numpy as np
import librosa
from scipy.fft import next_fast_len, rfft, irfft
from scipy.signal import correlate, find_peaks
SR=22050
HOP=512

def find_loop(audio):
    spectrum = np.abs(librosa.stft(audio, hop_length=HOP))
    mel = librosa.feature.melspectrogram(S=spectrum ** 2, sr=SR, n_mels=48)
    features = np.log1p(mel)
    features -= features.mean(axis=1, keepdims=True)
    n = features.shape[1]
    fft_size = next_fast_len(2 * n - 1)
    spectrum_fft = rfft(features, n=fft_size, axis=1)
    correlation = irfft(np.sum(abs(spectrum_fft) ** 2, axis=0), n=fft_size)[:n]
    energy = np.r_[0, np.cumsum(np.sum(features ** 2, axis=0))]
    lags = np.arange(n)
    denominator = np.sqrt(energy[n-lags] * (energy[n] - energy[lags]))
    similarity = correlation / np.maximum(denominator, 1e-10)
    low = int(10 * SR / HOP)
    high = min(n // 2, int(155 * SR / HOP))
    peaks, _ = find_peaks(similarity[low:high], distance=int(SR/HOP))
    peaks += low
    if not len(peaks):
        raise ValueError('No repeat found; inspect the source instead of guessing a loop.')
    best = max(peaks, key=lambda p: similarity[p])
    near_best = [p for p in peaks if similarity[p] >= max(.85, similarity[best] - .015)]
    if near_best:
        best = min(near_best)
    rough = best * HOP / SR
    # Refine the feature-level lag with waveform alignment, within 60 ms.
    reference = audio[SR:21*SR]
    center = round(rough*SR)
    radius = round(.06*SR)
    target = audio[SR+center-radius:21*SR+center+radius]
    alignment = correlate(target, reference, mode='valid', method='fft')
    offset = int(np.argmax(alignment)) - radius
    seconds = (center + offset) / SR
    confidence = float(similarity[best])
    if confidence < .65:
        raise ValueError(f'Low loop confidence ({confidence:.3f}); manual loop selection required.')
    return seconds, confidence


def beat_grid(audio, loop_seconds):
    envelope = librosa.onset.onset_strength(y=audio, sr=SR, hop_length=HOP)
    _, frames = librosa.beat.beat_track(onset_envelope=envelope, sr=SR, hop_length=HOP)
    times = librosa.frames_to_time(frames, sr=SR, hop_length=HOP)
    if len(times) < 8:
        raise ValueError('Insufficient beats to estimate tempo.')
    period, offset = np.polyfit(np.arange(len(times)), times, 1)
    count = loop_seconds / period
    # Lock near-integer loop lengths to the repeat, avoiding accumulated drift.
    if abs(count-round(count)) < .3:
        count = round(count)
        period = loop_seconds / count
    return float(60 / period), float(count), float(offset)


def percussion(audio, bpm):
    magnitude = np.abs(librosa.stft(audio, hop_length=256))
    _, percussive = librosa.decompose.hpss(magnitude)
    frequencies = librosa.fft_frequencies(sr=SR)
    result = {}
    # These are spectral-band onset guesses, not instrument recognition.
    bands = [('kick', 40, 180, .19, .35, .65), ('snare', 250, 2400, .23, .4, .8),
             ('hat', 6500, 10500, .075, .22, .4)]
    for name, low, high, distance, prominence, height in bands:
        band = percussive[(frequencies >= low) & (frequencies < high)]
        flux = np.mean(np.maximum(0, np.diff(np.log1p(band*10), axis=1)), axis=0)
        flux = np.r_[0, flux]
        scale = np.percentile(flux, 98)
        if scale <= 1e-8:
            result[name] = []
            continue
        flux /= scale
        peaks, _ = find_peaks(flux, distance=max(1, int(distance*SR/256)),
                             prominence=prominence, height=height)
        result[name] = [[round(float(p*256/SR*bpm/60), 5), .12, 36,
                         round(float(np.clip(flux[p], .25, 1)), 3)] for p in peaks]
    return result
