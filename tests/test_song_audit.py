import copy
import unittest
import numpy as np

from slopwave.audit_song import audit
from slopwave.refinement import apply_instrument_review


class SongAuditTests(unittest.TestCase):
    def test_audit_does_not_fold_a_supported_high_note_or_mutate_input(self):
        times = np.arange(0, 3, .01)
        pitches = np.arange(24, 91)
        salience = np.full((len(pitches), len(times)), .1)
        salience[pitches == 80] = .8
        features = {part: dict(times=times, pitches=pitches, salience=salience.copy(),
                               rms=np.ones(len(times))*.05) for part in ('low', 'middle', 'high')}
        features['low']['rms'][:100] = .00005
        source = dict(bpm=60, beats=3, loop_seconds=3, source_audio_sha256='source', parts=dict(
            low=[[0, .5, 'c2', .8]], middle=[[0, 1, 'gs5', .5]], high=[[1, 1, 'gs5', .5]],
            kick=[[0, .1, 36, .4]], snare=[], hat=[]))
        before = copy.deepcopy(source)
        report = audit(source, features)
        self.assertEqual(source, before)
        self.assertEqual(sum(v['events'] for v in report['coverage'].values()), 3)
        self.assertTrue(any('quiet_stem_promoted_to_loud_note' in r['kinds'] for r in report['findings']))
        high = next(r for r in report['findings'] if r['part'] == 'high')
        self.assertNotIn('stronger_lower_octave', high['kinds'])

        source['parts']['high'] = [[0, .5, 'c4', .5], [.5, .2, 'c3', .5], [.7, .5, 'd4', .5]]
        report = audit(source, features)
        dip = next(r for r in report['findings'] if r['part'] == 'high' and r['event'][2] == 'c3')
        self.assertIn('isolated_downward_register_outlier', dip['kinds'])
        source['parts']['high'][2][0] = 2
        report = audit(source, features)
        self.assertFalse(any(r['part'] == 'high' and r['event'][2] == 'c3'
                            and 'isolated_downward_register_outlier' in r['kinds']
                            for r in report['findings']))

    def test_reviewed_merge_retains_neighbor_and_rejects_reapplication(self):
        rows = [[0, .5, 'gs5', .5], [.5, .5, 'gs5', .7], [1, 1, 'c4', .6]]
        source = dict(source_audio_sha256='source', parts=dict(middle=rows, low=[]))
        review = dict(source_audio_sha256='source', edits=[dict(part='middle',
            expected=rows[:2], replacement=[[0, 1, 'gs5', .6]])])
        result = apply_instrument_review(source, review)
        self.assertEqual(result['parts']['middle'], [[0, 1, 'gs5', .6], rows[2]])
        self.assertEqual(source['parts']['middle'], rows)
        with self.assertRaises(ValueError):
            apply_instrument_review(result, review)
        review['edits'][0]['replacement'][0][1] = 2
        with self.assertRaises(ValueError):
            apply_instrument_review(source, review)
        review['source_audio_sha256'] = 'other'
        with self.assertRaises(ValueError):
            apply_instrument_review(source, review)
