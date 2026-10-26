import base64
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from slopwave.cli import arrange, mix, export
from slopwave.score import load
from slopwave.samples import snapshot_samples

ROOT = Path(__file__).resolve().parents[1]

class SoundDesignTests(unittest.TestCase):
    def test_unknown_or_nonliteral_controls_fail_export(self):
        score = mix(arrange(load(ROOT/'examples/lantern/score.json'), 'synth'))
        for key, value in [('distrosion', .5), ('lpf', 'alert(1)'), ('crush', float('inf'))]:
            bad = deepcopy(score); bad['voices']['low'][key] = value
            with self.assertRaises(ValueError): export(bad)

    def test_samples_are_frozen_and_hash_checked(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'hit.wav'; path.write_bytes(b'RIFFfixture')
            score = {'sample_buffers': {'hit': {'url':'hit.wav','seconds':.2,'license':'original'}}}
            frozen = snapshot_samples(score, temp)
            sample = frozen['sample_buffers']['hit']
            self.assertEqual(base64.b64decode(sample['url'].split(',')[1]), b'RIFFfixture')
            self.assertEqual(score['sample_buffers']['hit']['url'], 'hit.wav')
            path.unlink()
            self.assertEqual(snapshot_samples(frozen, temp), frozen)
            sample['sha256'] = '0'*64
            with self.assertRaisesRegex(ValueError, 'mismatch'): snapshot_samples(frozen, temp)

    def test_bad_sample_definitions_fail_before_render(self):
        for sample in [dict(url='file:///etc/passwd',seconds=1),
                       dict(url='data:text/html;base64,YQ==',seconds=1),
                       dict(url='missing.wav',seconds=0)]:
            with self.assertRaises(ValueError): snapshot_samples({'sample_buffers':{'hit':sample}}, ROOT)
