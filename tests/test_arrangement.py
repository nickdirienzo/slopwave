import copy
import unittest

from slopwave.arrange import piano_strings, apply_articulation_review
from slopwave.refinement import midi_pitch
from slopwave.strudel import strudel_source
from slopwave.bluegrass import bluegrass, bluegrass_riff, bluegrass_drive, bluegrass_continuity, bluegrass_performance, pulse_anchors


class ArrangementTests(unittest.TestCase):
    def continuity_fixture(self):
        source = dict(source='fixture', source_audio_sha256='fixture', loop_seconds=8,
                      beats=8, bpm=60, beat_offset_seconds=0, beat_times_seconds=list(range(8)),
                      parts=dict(low=[[0, 4, 'gs2', .7]], middle=[[0, 4, 'ds4', .4]],
                                 high=[[2, .3, 'e4', .6], [3.2, .1, 'd3', .3]],
                                 kick=[[4.5, .1, 36, .8]], snare=[], hat=[[6.5, .1, 36, .5]]))
        windows = [dict(start=i/2, end=(i+1)/2, root=8 if i<8 else None,
                        relative_stem_rms=dict(low=1 if i<8 else 0, middle=1 if i<8 else 0)) for i in range(16)]
        harmony = dict(source_audio_sha256='fixture', windows=windows)
        riff = dict(source_audio_sha256='fixture', events=[[0, .2, 'e4', .5]], cues=[
            dict(seconds=0, root=4, onset_strength=1.2, relative_stem_rms=dict(middle=1))])
        return source, harmony, riff

    def test_continuity_keeps_backing_and_drum_break_but_preserves_true_silence(self):
        source, harmony, riff = self.continuity_fixture()
        source['parts']['hat'] = []
        result = bluegrass_continuity(source, harmony, riff)
        self.assertTrue(any(.4 <= r[0] <= 1.8 for r in result['parts']['middle']))
        self.assertEqual(result['parts']['kick'], source['parts']['kick'])
        self.assertFalse(any(r[0] >= 5 for rows in result['parts'].values() for r in rows))
        self.assertTrue(all(r in result['parts']['high'] for r in source['parts']['high']))

    def test_banjo_review_is_scoped_preserves_source_and_rejects_stale_inputs(self):
        source, harmony, riff = self.continuity_fixture()
        before = copy.deepcopy((source, harmony, riff))
        review = dict(source_audio_sha256='fixture', lead_edits=[
            dict(index=0, expected=copy.deepcopy(source['parts']['high'][0]), replacement=[2, .3, 'ds4', .6]),
            dict(index=1, expected=copy.deepcopy(source['parts']['high'][1]), replacement=None)], harmony_edits=[],
            riff_edits=[dict(index=0, expected_event=[0, .2, 'e4', .5], expected_root=4,
                            replacement_event=[0, .2, 'gs3', .5], replacement_root=8)])
        result = bluegrass_performance(source, harmony, riff, review)
        self.assertEqual((source, harmony, riff), before)
        self.assertIn([2, .3, 'ds4', .6], result['parts']['high'])
        self.assertIn([0, .2, 'gs3', .5], result['parts']['high'])
        self.assertNotIn(source['parts']['high'][1], result['parts']['high'])
        source['parts']['high'][0][2] = 'f4'
        with self.assertRaisesRegex(ValueError, 'event changed'):
            bluegrass_performance(source, harmony, riff, review)

    def test_acoustic_breaks_keep_timing_and_preload_sample_without_synth_effects(self):
        source, harmony, riff = self.continuity_fixture()
        before = copy.deepcopy(source)
        review = dict(source_audio_sha256='fixture', lead_edits=[], harmony_edits=[], riff_edits=[])
        result = bluegrass_performance(source, harmony, riff, review)
        self.assertEqual(source, before)
        for part in ('kick', 'snare', 'hat'):
            self.assertEqual([r[:2]+r[3:] for r in result['parts'][part]],
                             [r[:2]+r[3:] for r in source['parts'][part]])
        rendered = strudel_source(dict(title='Fixture', youtube='fixture'), result)
        self.assertIn('...'+str([60, 72])+'.map(note => getFontBufferSource("1150_FluidR3_GM_sf2_file"', rendered)
        for part in ('kick', 'snare', 'hat'):
            self.assertIn('phrase('+part+').s("gm_woodblock").n(3)', rendered)
        self.assertNotIn('.penv(', rendered)
        self.assertNotIn('.freq(65)', rendered)
        self.assertNotIn('.s("white")', rendered)

    def test_drive_uses_source_accents_without_changing_banjo_line(self):
        source = dict(source='fixture', source_audio_sha256='fixture', loop_seconds=8,
                      beats=8, bpm=60, beat_offset_seconds=0, beat_times_seconds=list(range(8)),
                      parts=dict(low=[[0, 8, 'g2', .7]], middle=[[0, 8, 'd4', .4]],
                                 high=[[3, 1, 'g4', .6]], kick=[[.5, .1, 36, .8]]))
        riff = dict(source_audio_sha256='fixture', events=[[.5, .2, 'g3', .5]], cues=[
            dict(seconds=.5, root=7, onset_strength=1.2, relative_stem_rms=dict(middle=1)),
            dict(seconds=.7, root=7, onset_strength=.7, relative_stem_rms=dict(middle=1)),
            dict(seconds=3.2, root=7, onset_strength=1.2, relative_stem_rms=dict(middle=1)),
            dict(seconds=4.5, root=0, onset_strength=.7, relative_stem_rms=dict(middle=.5))])
        before = copy.deepcopy(source)
        sparse = bluegrass_riff(source, None, riff)
        driven = bluegrass_drive(source, None, riff)
        self.assertEqual(source, before)
        self.assertEqual(driven['parts']['high'], sparse['parts']['high'])
        self.assertEqual([r[:3] for r in driven['parts']['low']], [r[:3] for r in sparse['parts']['low']])
        guitar = driven['parts']['middle']
        self.assertEqual([r[0] for r in guitar], [.5, .505, 3.2, 3.205, 4.5, 4.505])
        self.assertLess(guitar[2][3], guitar[0][3])
        self.assertLess(guitar[4][3], guitar[0][3])
        self.assertEqual(driven['parts']['kick'], [])

    def test_riff_version_preserves_phrases_without_filling_syllable_gaps(self):
        source = dict(source='fixture', source_audio_sha256='fixture', loop_seconds=8,
                      beats=8, bpm=60, beat_offset_seconds=0, beat_times_seconds=list(range(8)),
                      parts=dict(low=[[0, 8, 'g2', .7]], middle=[[0, 8, 'd4', .4]],
                                 high=[[2, .3, 'g4', .6], [3, .4, 'a4', .6]]))
        riff = dict(source_audio_sha256='fixture', events=[
            [0, .2, 'g3', .5], [2.6, .2, 'g3', .5], [5, .2, 'g3', .5]])
        before = copy.deepcopy(source)
        result = bluegrass_riff(source, None, riff)
        self.assertEqual(source, before)
        self.assertEqual(result['parts']['high'], sorted(source['parts']['high']+[riff['events'][0], riff['events'][2]]))
        self.assertEqual(result['arrangement']['composed_roll_notes'], 0)
        self.assertEqual(result['arrangement']['instrumental_riff_notes'], 2)
        self.assertTrue(all(1.88 < r[0] < 3.52 for r in result['parts']['middle']))
        riff['source_audio_sha256'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'another recording'):
            bluegrass_riff(source, None, riff)

    def test_bluegrass_preserves_melody_and_rests_with_roll_clearance(self):
        source = dict(source='fixture', source_audio_sha256='fixture', loop_seconds=8.3,
                      beats=8.3, bpm=60, beat_offset_seconds=.1,
                      beat_times_seconds=[.1+i for i in range(8)], parts=dict(
                          low=[[0, 4, 'g2', .7]], middle=[[0, 4, 'd4', .4]],
                          high=[[1.13, 1.81, 'g4', .7]], kick=[], snare=[], hat=[]))
        before = copy.deepcopy(source)
        result = bluegrass(source)
        self.assertEqual(source, before)
        self.assertEqual(result, bluegrass(source))
        lead = source['parts']['high'][0]
        self.assertIn(lead, result['parts']['high'])
        rolls = [r for r in result['parts']['high'] if r != lead]
        self.assertTrue(rolls)
        self.assertTrue(all(r[0]+r[1] < lead[0] or r[0] > lead[0]+lead[1] for r in rolls))
        for rows in result['parts'].values():
            for at, length, _, gain in rows:
                self.assertTrue(0 <= at < at+length <= 8.3)
                self.assertLess(at, 4)
                self.assertTrue(0 <= gain <= 1)
        self.assertEqual(result['parts']['kick'], [])
        rendered = strudel_source(dict(title='Fixture', youtube='fixture'), result)
        self.assertIn('1050_FluidR3_GM_sf2_file', rendered)
        self.assertIn('// mini-off', rendered)

    def test_bluegrass_rejects_unmeasured_pulse(self):
        source = dict(source='fixture', source_audio_sha256='fixture', loop_seconds=8,
                      beats=8, bpm=60, beat_offset_seconds=0, beat_times_seconds=[],
                      parts=dict(high=[]))
        with self.assertRaisesRegex(ValueError, 'measured beat'):
            bluegrass(source)

    def test_bluegrass_source_bound_harmony_retains_acoustic_silence(self):
        source = dict(source='fixture', source_audio_sha256='fixture', loop_seconds=8,
                      beats=8, bpm=60, beat_offset_seconds=0,
                      beat_times_seconds=list(range(8)), parts=dict(
                          low=[[0, 8, 'c2', .8]], middle=[], high=[[1, .5, 'c4', .6]]))
        anchors, _, _ = pulse_anchors(source)
        windows = [dict(start=a+(b-a)*half/2, end=a+(b-a)*(half+1)/2, root=None)
                   for a, b in zip(anchors, anchors[1:]) for half in range(2)]
        evidence = dict(source_audio_sha256='fixture', windows=windows)
        result = bluegrass(source, evidence)
        self.assertEqual(result['parts']['high'], source['parts']['high'])
        self.assertEqual(result['parts']['low'], [])
        self.assertEqual(result['parts']['middle'], [])
        evidence['source_audio_sha256'] = 'other'
        with self.assertRaisesRegex(ValueError, 'another recording'):
            bluegrass(source, evidence)

    def test_scoped_tie_preserves_neighbors_and_rejects_stale_or_rest_spanning_edits(self):
        rows = [[0, 1, 'gs4', .5], [1, .1, 'a4', .4], [1.1, .9, 'gs4', .6],
                [3, 1, 'b4', .5]]
        data = dict(source_audio_sha256='audio', bpm=60, parts=dict(high=rows),
                    arrangement=dict(input_analysis_sha256='score', profile='piano-strings-v1'))
        review = dict(source_audio_sha256='audio', input_analysis_sha256='score',
                      profile='piano-strings-v1', edits=[dict(kind='piano_neighbor_smoothing',
                      expected=copy.deepcopy(rows[:3]), replacement=[0, 2, 'gs4', .54])])
        result = apply_articulation_review(data, review)
        self.assertEqual(result['parts']['high'], [[0, 2, 'gs4', .54], rows[3]])
        self.assertEqual(len(data['parts']['high']), 4)
        with self.assertRaises(ValueError):
            apply_articulation_review(result, review)
        wrong = copy.deepcopy(review)
        wrong['input_analysis_sha256'] = 'other'
        with self.assertRaises(ValueError):
            apply_articulation_review(data, wrong)
        spaced = copy.deepcopy(data)
        spaced['parts']['high'][1][0] += .1
        spaced_review = copy.deepcopy(review)
        spaced_review['edits'][0]['expected'] = spaced['parts']['high'][:3]
        with self.assertRaises(ValueError):
            apply_articulation_review(spaced, spaced_review)

    def test_melody_and_input_preserved_with_sparse_separate_accompaniment(self):
        source = dict(source='fixture', source_audio_sha256='fixture', loop_seconds=8,
                      beats=8, bpm=60, beat_offset_seconds=0, parts=dict(
                          low=[[0, 1, 'cs1', .8], [1, 1, 'cs1', .7], [4, 1, 'f3', .001]],
                          middle=[[0, 4, 'cs4', .5]], high=[[2, 1, 'gs4', .6]],
                          kick=[[0, .1, 36, .5]], snare=[], hat=[]))
        before = copy.deepcopy(source)
        result = piano_strings(source)
        self.assertEqual(source, before)
        self.assertEqual(result['parts']['high'], source['parts']['high'])
        self.assertEqual(result['parts']['low'], [[0, 2, 'cs2', .8]])
        self.assertEqual(result['parts']['kick'], [])
        self.assertEqual(len(result['parts']['middle']), 2)
        pitches = [midi_pitch(r[2]) for r in result['parts']['middle']]
        self.assertEqual(pitches[1]-pitches[0], 7)
        for rows in result['parts'].values():
            for at, length, _, gain in rows:
                self.assertTrue(0 <= at < at+length <= source['beats'])
                self.assertTrue(0 <= gain <= 1)
        self.assertEqual(result, piano_strings(source))

    def test_preloading_rejects_mismatched_soundfont_variant(self):
        source = dict(source='fixture', source_audio_sha256='fixture', loop_seconds=8,
                      beats=8, bpm=60, beat_offset_seconds=0,
                      parts=dict(low=[], middle=[], high=[[0, 1, 'c4', .5]]))
        result = piano_strings(source)
        result['voices']['high']['n'] = 0
        with self.assertRaisesRegex(ValueError, 'preload preset'):
            strudel_source(dict(title='Fixture', youtube='fixture'), result)


if __name__ == '__main__':
    unittest.main()
