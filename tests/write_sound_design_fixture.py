"""Deterministic original synth/sample fixtures; no network or licensed assets."""
import base64
import io
import math
from pathlib import Path
import struct
import wave
from slopwave.score import promote, save, digest
from slopwave.cli import export, export_module

output = Path('build/sound-design'); output.mkdir(parents=True, exist_ok=True)
for name in ('effects', 'samples', 'long'):
    beats = 132 if name == 'long' else 4
    parts = {key: [] for key in ('low', 'middle', 'high', 'kick', 'snare', 'hat')}
    voices = {}
    if name == 'samples':
        data = io.BytesIO()
        with wave.open(data, 'wb') as wav:
            wav.setparams((1, 2, 44100, 0, 'NONE', 'not compressed'))
            wav.writeframes(b''.join(struct.pack('<h', int(8000 * math.sin(i*2*math.pi*180/44100) * (1-i/8820))) for i in range(8820)))
        parts['kick'] = [[at, .25, 36, .4] for at in (0, 1, 2, 3)]
        voices['kick'] = dict(sound='test_hit', distort=.3, distortvol=.5)
        samples = {'test_hit': dict(url='data:audio/wav;base64,'+base64.b64encode(data.getvalue()).decode(), seconds=.2)}
    else:
        parts['low'] = [[at, .5, 36, .35] for at in range(0, beats, 2)]
        parts['kick'] = [[at, .2, 36, .3] for at in range(beats)]
        parts['hat'] = [[at+.5, .1, 36, .25] for at in range(beats)]
        voices = dict(low=dict(sound='sawtooth',fm=.5,fmh=1.5,lpf=1500,lpenv=2,lpdecay=.12,distort=.6,distortvol=.25,release=.1),
                      kick=dict(sound='sine',freq=49,penv=12,pdecay=.04,decay=.1,sustain=0,distort=.5,distortvol=.2),
                      hat=dict(sound='white',hpf=6000,crush=10,decay=.03,sustain=0))
        samples = None
        if name == 'long':
            # Hold crosses the 16-cycle segment boundary.
            parts['low'].append([63.5, 3, 43, .2]); parts['low'].sort()
    data = dict(bpm=120,beats=beats,parts=parts,voices=voices,mix=dict(low=.3,middle=.2,high=.2,drums=.3),source_audio_sha256=digest(parts))
    if samples: data['sample_buffers'] = samples
    score = promote(data,title='Original sound-design test',source_id='original:sound-design-test',source_kind='authored',stage='mixed')
    save(output/(name+'.json'), score)
    (output/(name+'.strudel.js')).write_text(export(score))
    (output/(name+'.mjs')).write_text(export_module(score))
