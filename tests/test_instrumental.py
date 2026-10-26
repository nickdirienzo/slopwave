"""Regression coverage for explicit instrumental evidence and reviewed mix replay."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import sys
from types import ModuleType
import numpy as np
import soundfile as sf
from slopwave.audio import evidence
from slopwave.cli import arrange, mix
from slopwave.score import load, promote

class InstrumentalTests(unittest.TestCase):
    def test_explicit_instrumental_stem_and_hash_guard(self):
        with tempfile.TemporaryDirectory() as work:
            work=Path(work)
            stems={}
            t=np.arange(22050)/22050
            for name,hz in [('bass',110),('other',440),('vocals',880)]:
                p=work/(name+'.wav')
                sf.write(p,.1*np.sin(2*np.pi*hz*t),22050,subtype='FLOAT')
                stems[name]=dict(path=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
            manifest=dict(source_audio_sha256='a'*64,stems=stems)
            (work/'separation.json').write_text(json.dumps(manifest))
            score=promote(dict(bpm=60,beats=1,source_audio_sha256='a'*64,parts={}),
                          title='Synthetic',source_id='test',source_kind='audio')
            score['stem_roles']=dict(high='other')
            evidence(score,work,work/'features')
            result=json.loads((work/'features/manifest.json').read_text())
            self.assertEqual(result['parts']['high']['stem'],'other')
            self.assertEqual(result['parts']['high']['stem_sha256'],stems['other']['sha256'])
            with np.load(work/'features/high.npz') as high, np.load(work/'features/middle.npz') as middle:
                np.testing.assert_array_equal(high['salience'],middle['salience'])
            (work/'other.wav').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'Stem contents changed'):
                evidence(score,work,work/'stale')

    def test_preserved_mix_is_explicit_and_cannot_be_applied_twice(self):
        score=load(Path(__file__).resolve().parents[1]/'examples/lantern/score.json')
        arranged=arrange(score,'synth')
        with self.assertRaises(ValueError):
            mix(arranged,'preserve')
        arranged['mix']=dict(low=.2,middle=.1,high=.3,drums=.15)
        result=mix(arranged,'preserve')
        self.assertEqual(result['parts'],arranged['parts'])
        self.assertEqual(result['mix'],arranged['mix'])
        with self.assertRaises(ValueError):
            mix(result,'preserve')

    def test_pitch_adapter_supplies_a_real_normalized_audio_file(self):
        from slopwave.audio import transcribe
        with tempfile.TemporaryDirectory() as directory:
            work=Path(directory)
            model=work/'saved_models/icassp_2022/nmp.onnx'
            model.parent.mkdir(parents=True)
            model.write_bytes(b'mock model')
            package=ModuleType('basic_pitch'); package.__file__=str(work/'__init__.py')
            inference=ModuleType('basic_pitch.inference')
            inference.Model=lambda path: path
            def predict(path, model, **settings):
                self.assertIsInstance(path,Path)
                info=sf.info(path)
                self.assertEqual((info.samplerate,info.channels,info.subtype),(22050,1,'FLOAT'))
                return None,None,[(0.,.5,69,.8,None)]
            inference.predict=predict
            sf.write(work/'source.wav',np.ones((44100,2))*.1,44100,subtype='FLOAT')
            with mock.patch.dict(sys.modules,{'basic_pitch':package,'basic_pitch.inference':inference}), mock.patch('slopwave.audio.version',return_value='test'):
                transcribe(work/'source.wav',work/'result.json',120)
            result=load(work/'result.json')
            self.assertEqual(result['parts']['high'][0][:3],[0.,1.,'a4'])
            self.assertAlmostEqual(result['parts']['high'][0][3],.4,places=3)
