"""Guard against masking fixes erasing notes or proslopwaveng stem leakage."""
import copy
import unittest

from slopwave.mixing import refine_mix


class MixingTests(unittest.TestCase):
    def test_dense_chords_and_lead_keep_attacks_with_bounded_gain(self):
        source = {'bpm': 120, 'parts': {
            'low': [[0, 1, 'c2', .8]],
            'middle': [[0, 1, pitch, 1.] for pitch in ('c4', 'e4', 'g4', 'c5', 'e5', 'g5', 'c6')],
            'high': [[0, .5, 'c5', .02], [.5, .5, 'd5', 1.]],
            'kick': [[0, .1, 36, .8]],
        }}
        before = copy.deepcopy(source)
        result = refine_mix(source, 'stem-rock-v1')
        self.assertEqual(source, before)
        for part, rows in source['parts'].items():
            self.assertEqual([r[:3] for r in result['parts'][part]], [r[:3] for r in rows])
        self.assertLessEqual(sum(r[3] for r in result['parts']['middle']), 1.8)
        self.assertEqual(result['parts']['high'][0][3], .02)
        self.assertLess(result['parts']['high'][1][3], 1.)
        with self.assertRaises(ValueError):
            refine_mix(result, 'stem-rock-v1')

    def test_backing_ducks_only_when_vocals_overlap_and_quiet_notes_stay_quiet(self):
        source = {'bpm': 120, 'parts': {'low': [],
            'middle': [[0, 1, 'c4', .1], [2, 1, 'c4', .1]],
            'high': [[0, 1, 'g4', 1.]]}}
        result = refine_mix(source, 'stem-rock-v1')
        self.assertLess(result['parts']['middle'][0][3], .1)
        self.assertEqual(result['parts']['middle'][1][3], .1)
