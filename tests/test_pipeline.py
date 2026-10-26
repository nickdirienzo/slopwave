"""Public pipeline boundaries, using only the original study."""
from copy import deepcopy
from pathlib import Path
import unittest

from slopwave.cli import arrange, mix, export
from slopwave.score import load, validate, digest, apply_corrections


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.score = load(Path(__file__).resolve().parents[1]/'examples/lantern/score.json')

    def test_replay_and_input_preservation(self):
        before = deepcopy(self.score)
        first = mix(arrange(self.score, 'synth'))
        second = mix(arrange(self.score, 'synth'))
        self.assertEqual(first, second)
        self.assertEqual(export(first), export(second))
        self.assertEqual(self.score, before)
        self.assertEqual(first['provenance']['steps'][0]['input_sha256'], digest(before))

    def test_stage_order_and_double_mix(self):
        with self.assertRaises(ValueError):
            mix(self.score)
        with self.assertRaises(ValueError):
            export(self.score)
        mixed = mix(arrange(self.score, 'synth'))
        with self.assertRaises(ValueError):
            mix(mixed)
        with self.assertRaises(ValueError):
            arrange(mixed, 'synth')

    def test_all_profiles_export(self):
        for profile in ('synth', 'piano-strings', 'bluegrass', 'kazoo'):
            with self.subTest(profile=profile):
                source = deepcopy(self.score)
                if profile == 'bluegrass':
                    # Explicit authored pulse; recordings need their measured grid.
                    source['beat_times_seconds'] = [i*60/source['bpm'] for i in range(33)]
                score = mix(arrange(source, profile))
                validate(score)
                self.assertIn('const BPM = ', export(score))

    def test_correction_guards_and_replay(self):
        expected = deepcopy(self.score['parts']['high'][:1])
        replacement = deepcopy(expected)
        replacement[0][3] *= .8
        patch = dict(source_audio_sha256=self.score['source_audio_sha256'],
                     input_sha256=digest(self.score), edits=[dict(part='high',
                     expected=expected, replacement=replacement, reason='test dynamics',
                     evidence='authored fixture')])
        corrected = apply_corrections(self.score, patch)
        self.assertEqual(corrected['parts']['high'][0], replacement[0])
        self.assertEqual(self.score['parts']['high'][0], expected[0])
        with self.assertRaises(ValueError):
            apply_corrections(corrected, patch)
        patch['edits'][0]['expected'][0][2] = 'c0'
        with self.assertRaises(ValueError):
            apply_corrections(self.score, patch)

    def test_extent_and_nonfinite_values(self):
        bad = deepcopy(self.score)
        bad['parts']['high'][0][1] = bad['beats']+1
        with self.assertRaises(ValueError):
            validate(bad)
        bad = deepcopy(self.score)
        bad['extra_measurement'] = float('nan')
        with self.assertRaises(ValueError):
            validate(bad)


if __name__ == '__main__':
    unittest.main()
