"""Synthetic regressions for the musical failure modes found during review."""
import copy
import unittest

import numpy as np

from slopwave.refinement import BeatGrid, PitchEvidence, dominant_line, measure_grid, midi_pitch, vocal_octaves, apply_reviewed_additions
from slopwave.review import review


class RefinementTests(unittest.TestCase):
    def test_reviewed_additions_reject_wrong_source_and_duplicate_attacks(self):
        source = {'source_audio_sha256': 'example', 'beats': 4,
                  'parts': {'high': [[0, 1, 'c4', .4]]}}
        review = {'source_audio_sha256': 'example',
                  'additions': [{'part': 'high', 'event': [1, .5, 'd4', .3]}]}
        result = apply_reviewed_additions(source, review)
        self.assertEqual(len(source['parts']['high']), 1)
        self.assertEqual(len(result['parts']['high']), 2)
        with self.assertRaises(ValueError):
            apply_reviewed_additions(result, review)
        review['source_audio_sha256'] = 'different'
        with self.assertRaises(ValueError):
            apply_reviewed_additions(source, review)

    def test_vocal_octave_requires_periodicity_and_neighbor_support(self):
        times = np.arange(0, 1, .01)
        fundamental = np.full(len(times), 440*2**((68-69)/12))
        notes = [[0., .3, 80, .5], [.3, .6, 68, .5]]
        result, evidence = vocal_octaves(notes, times, fundamental, np.ones(len(times))*.8)
        self.assertEqual(result[0][2], 68)
        self.assertEqual(len(evidence), 1)
        unchanged, evidence = vocal_octaves(notes, times, fundamental, np.zeros(len(times)))
        self.assertEqual(unchanged, notes)
        self.assertEqual(evidence, [])
        isolated, evidence = vocal_octaves(notes[:1], times, fundamental, np.ones(len(times)))
        self.assertEqual(isolated, notes[:1])

    def test_dominant_voice_keeps_real_repeated_attacks_and_crosses_registers(self):
        notes = [[0., .2, 69, .8], [.2, .4, 69, .8], [.4, .6, 64, .7],
                 [0., .4, 81, .3]]
        self.assertEqual(dominant_line(notes), notes[:3])
        self.assertEqual(dominant_line([]), [])

    def test_grid_uses_measured_phase_and_preserves_offbeat(self):
        attacks = .087 + np.arange(40)*.25 + np.sin(np.arange(40))*.002
        fit = measure_grid(attacks, 120, 2)
        self.assertLess(fit['p90_error_ms'], 3)
        grid = BeatGrid(120, fit['phase_seconds'])
        self.assertAlmostEqual(grid.snap_beat(.212)*.5, .212, places=3)
        self.assertFalse(fit['automatic_quantization_authorized'])

    def test_swing_is_not_silently_flattened_to_straight_eighths(self):
        attacks = np.array([beat*.5+offset for beat in range(20) for offset in (0, 1/3)])
        straight = measure_grid(attacks, 120, 2)
        triplet = measure_grid(attacks, 120, 3)
        self.assertGreater(straight['p90_error_ms'], 30)
        self.assertLess(triplet['p90_error_ms'], .001)
        with self.assertRaises(ValueError):
            measure_grid([0, 1], 120)

    def test_pitch_names_and_invalid_values(self):
        self.assertEqual(midi_pitch('e4'), 64)
        self.assertEqual(midi_pitch('cs5'), 73)
        self.assertEqual(midi_pitch('c-1'), 0)
        for value in ('h5', 'c12', 69.5, -1):
            with self.assertRaises(ValueError):
                midi_pitch(value)
        with self.assertRaises(ValueError):
            BeatGrid(0, 0)

    def test_harmonic_flag_does_not_blanket_remove_high_notes(self):
        sr = 22050
        t = np.arange(sr)/sr
        g4 = 440*2**((67-69)/12)
        mixed = np.sin(2*np.pi*g4*t) + .2*np.sin(2*np.pi*4*g4*t)
        measured = PitchEvidence(mixed, sr, offset_seconds=65)
        candidates = measured.octave_candidates(91, 65.3)
        self.assertIn(67, [row['candidate_midi'] for row in candidates])
        high_only = PitchEvidence(np.sin(2*np.pi*4*g4*t), sr)
        self.assertEqual(high_only.octave_candidates(91, .3), [])
        quiet = PitchEvidence(np.zeros(sr), sr)
        self.assertEqual(quiet.octave_candidates(91, .3), [])
        self.assertIsNone(quiet.boundary(91, .1, .3))

    def test_envelope_distinguishes_evidence_without_merging_notes(self):
        sr = 22050
        t = np.arange(sr)/sr
        carrier = np.sin(2*np.pi*440*t)
        held = PitchEvidence(carrier, sr)
        repeated = PitchEvidence(carrier*(1-.99*np.exp(-((t-.5)/.045)**2)), sr)
        flat = held.boundary(69, .2, .5)
        dip = repeated.boundary(69, .2, .5)
        self.assertGreater(flat['dip_ratio'], .95)
        self.assertLess(dip['dip_ratio'], flat['dip_ratio']*.6)

    def test_register_crossing_and_weak_missing_note_are_review_candidates(self):
        data = {'bpm': 120, 'parts': {'low': [],
            'middle': [[2.4, .3, 'e4', .65]],
            'high': [[2, .3, 'gs4', .6], [2.8, .3, 'a4', .6]]}}
        original = copy.deepcopy(data)
        notes = [[1.3, 1.35, 74, .21]]
        report = review(data, 1, 2, stem_notes=notes)
        kinds = [row['kind'] for row in report['findings']]
        self.assertIn('possible_lead_register_crossing', kinds)
        self.assertIn('unrepresented_stem_candidate', kinds)
        self.assertEqual(data, original)
        data['mode'] = 'full-song-stems'
        report = review(data, 1, 2)
        self.assertNotIn('possible_lead_register_crossing', [row['kind'] for row in report['findings']])
        report = review(data, 1, 2, parts=('high',))
        self.assertTrue(all(row['part'] == 'high' for row in report['events']))


if __name__ == '__main__':
    unittest.main()
