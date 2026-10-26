import unittest
import hashlib
import json
import numpy as np

from slopwave.vocal_phrases import decode_vocal, harmonic_features, join_short_fragments, sequence_path
from slopwave.refinement import apply_vocal_phrase_review, apply_vocal_corrections


class VocalPhraseTests(unittest.TestCase):
    def test_local_corrections_preserve_neighbors_and_reject_stale_input(self):
        review = dict(source_audio_sha256='source', after_notes=3,
                      events=[[0, .1, 'gs5', .4], [1, 3, 'gs5', .8], [4, 1, 'a4', .6]])
        edits = dict(source_audio_sha256='source', edits=[
            dict(expected=[0, .1, 'gs5', .4], replacement=None),
            dict(expected=[1, 3, 'gs5', .8], replacement=[1, 3, 'gs4', .8])])
        result = apply_vocal_corrections(review, edits)
        self.assertEqual(result['events'], [[1, 3, 'gs4', .8], [4, 1, 'a4', .6]])
        self.assertEqual(len(review['events']), 3)
        with self.assertRaises(ValueError):
            apply_vocal_corrections(result, edits)
        edits['source_audio_sha256'] = 'other'
        with self.assertRaises(ValueError):
            apply_vocal_corrections(review, edits)

    def test_phrase_replacement_rejects_stale_detections_and_preserves_other_parts(self):
        events = [[0, .5, 'c4', .4]]
        source = dict(source_audio_sha256='source', beats=4,
                      vocal_dynamics=dict(reference_rms=.05), parts=dict(high=events, low=[[0, 2, 'c2', .5]]))
        review = dict(source_audio_sha256='source', events=[[0, 1, 'c4', .5]],
                      input_vocal_events_sha256=hashlib.sha256(json.dumps(events, separators=(',', ':')).encode()).hexdigest())
        result = apply_vocal_phrase_review(source, review)
        self.assertEqual(source['parts']['high'], events)
        self.assertEqual(result['parts']['low'], source['parts']['low'])
        with self.assertRaises(ValueError):
            apply_vocal_phrase_review(result, review)

    def test_continuity_rejects_brief_octave_flip_but_keeps_real_leap_and_rest(self):
        pitches = np.array([60, 72])
        emissions = np.zeros((3, 160))
        emissions[0, :65] = 3
        emissions[1, 25:28] = 4
        emissions[2, 65:90] = 4
        emissions[1, 90:] = 4
        path = sequence_path(emissions, pitches)
        self.assertTrue(np.all(path[:65] == 0))
        self.assertTrue(np.all(path[65:90] == 2))
        self.assertTrue(np.all(path[90:] == 1))

    def test_short_fragment_is_joined_without_erasing_real_silence(self):
        path = np.array([0]*10+[1]*3+[0]*10+[2]*10+[0]*10)
        emissions = np.ones((3, len(path)))
        activity = np.ones(len(path))
        activity[23:33] = 0
        result, edits = join_short_fragments(path, emissions, activity, .01)
        self.assertTrue(np.all(result[:23] == 0))
        self.assertTrue(np.all(result[23:33] == 2))
        self.assertEqual(len(edits), 1)

    def test_model_predictions_cannot_sing_through_silence(self):
        sr = 22050
        features = harmonic_features(np.zeros(sr*2, dtype=np.float32), sr)
        times = features['times']
        notes, _ = decode_vocal(features, [[0, 2, 69, .99]], times,
                                np.full(len(times), 440.), np.ones(len(times)), .05)
        self.assertEqual(notes, [])

    def test_harmonic_evidence_can_recover_fundamental_under_loud_overtone(self):
        sr = 22050
        times = np.arange(sr*2)/sr
        hz = 220
        audio = (.2*np.sin(2*np.pi*hz*times)+.8*np.sin(2*np.pi*hz*2*times)
                 +.4*np.sin(2*np.pi*hz*3*times)+.3*np.sin(2*np.pi*hz*5*times)).astype(np.float32)*.1
        features = harmonic_features(audio, sr)
        t = features['times']
        notes, _ = decode_vocal(features, [[0, 2, 69, .8]], t,
                                np.full(len(t), 440.), np.ones(len(t)), .05)
        self.assertGreater(sum(end-start for start, end, pitch, _ in notes if pitch == 57), 1.7)

    def test_same_pitch_syllable_dip_keeps_two_attacks(self):
        sr = 22050
        t = np.arange(sr*2)/sr
        envelope = np.ones(len(t))*.08
        envelope[(t > .9) & (t < .97)] = .005
        audio = (envelope*(np.sin(2*np.pi*440*t)+.3*np.sin(2*np.pi*880*t))).astype(np.float32)
        features = harmonic_features(audio, sr)
        times = features['times']
        notes, _ = decode_vocal(features, [[0, 2, 69, .9]], times,
                                np.full(len(times), 440.), np.ones(len(times)), .05)
        melody = [row for row in notes if row[2] == 69]
        self.assertGreaterEqual(len(melody), 2)
        self.assertTrue(any(.85 < row[0] < 1.05 for row in melody))
