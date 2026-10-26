import copy
import hashlib
import json
import unittest

from slopwave.kazoo import kazoo_rock
from slopwave.strudel import strudel_source
from slopwave.refinement import apply_vocal_corrections


class KazooTests(unittest.TestCase):
    def test_cover_preserves_events_holds_rests_and_once_mixed_gains(self):
        source = dict(mode='full-song-stems', bpm=120, beats=12.25,
                      mix_review=dict(profile='stem-rock-v1'), parts=dict(
                          low=[[0, 2, 'c2', .5]], middle=[[0, 2, 'c4', .3]],
                          high=[[2, 4, 'g4', .5], [9, .3, 'c5', .4]],
                          kick=[[0, .1, 36, .8]], snare=[[1, .1, 36, .5]], hat=[]))
        original = copy.deepcopy(source)
        result = kazoo_rock(source)
        self.assertEqual(source, original)
        self.assertEqual(result['parts'], source['parts'])
        self.assertEqual(result['mix_review'], source['mix_review'])
        rendered = strudel_source(dict(title='Fixture', youtube='fixture'), result)
        self.assertIn('await Promise.all(samplePreload);', rendered)
        self.assertLess(rendered.index('await Promise.all(samplePreload);'), rendered.index('setcpm('))
        self.assertNotIn('.penv(', rendered)
        self.assertIn('.bpf(1150).bpq(0.65)', rendered)
        result['parts']['high'][0][2] = 'c3'
        self.assertEqual(source, original)

    def test_requires_mixed_source(self):
        with self.assertRaisesRegex(ValueError, 'once-mixed'):
            kazoo_rock(dict(parts={}))

    def test_reviewed_quiet_phrase_additions_reject_stale_or_overlapping_inputs(self):
        review = dict(source_audio_sha256='audio', events=[[0, 1, 'g4', .3]], after_notes=1)
        digest = hashlib.sha256(json.dumps(review['events'], separators=(',', ':')).encode()).hexdigest()
        corrections = dict(source_audio_sha256='audio', input_decoder_events_sha256=digest,
                           edits=[], additions=[dict(event=[2, 1, 'fs4', .1])])
        result = apply_vocal_corrections(review, corrections)
        self.assertEqual(len(result['events']), 2)
        self.assertEqual(len(review['events']), 1)
        with self.assertRaisesRegex(ValueError, 'decoder inputs changed'):
            apply_vocal_corrections(result, corrections)
        corrections['additions'][0]['event'][0] = .5
        with self.assertRaisesRegex(ValueError, 'overlaps'):
            apply_vocal_corrections(review, corrections)


if __name__ == '__main__':
    unittest.main()
