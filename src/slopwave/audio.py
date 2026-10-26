"""Optional local audio adapters. Models and heavy imports load only on demand."""
from pathlib import Path
import hashlib
import json
from importlib.metadata import version

from .score import promote, save, digest


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def transcribe(path, output, bpm, role='melody'):
    import math
    import numpy as np
    import soundfile as sf
    import librosa
    import basic_pitch
    from basic_pitch.inference import Model, predict
    from .strudel import note_name
    if not math.isfinite(bpm) or bpm <= 0:
        raise ValueError('BPM must be positive and finite')
    path = Path(path)
    audio, sr = sf.read(path, always_2d=True, dtype='float32')
    mono = librosa.resample(audio.mean(axis=1),orig_sr=sr,target_sr=22050)
    model_path = Path(basic_pitch.__file__).parent/'saved_models/icassp_2022/nmp.onnx'
    model = Model(model_path)
    # No temporary WAV timestamps enter the model-input identity.
    settings = dict(onset_threshold=.4,frame_threshold=.25,minimum_note_length=60,
                    minimum_frequency=35,maximum_frequency=2100)
    # Basic Pitch 0.4 accepts a path, not a NumPy waveform. Use float PCM so
    # the model sees the same mono samples recorded in our provenance and RMS.
    import tempfile
    with tempfile.TemporaryDirectory(prefix='slopwave-pitch-') as work:
        model_input=Path(work)/'input.wav'
        sf.write(model_input,mono,22050,subtype='FLOAT')
        _, _, raw = predict(model_input,model,**settings)
    seconds = len(mono)/22050
    if not seconds: raise ValueError('Empty audio')
    part = {'bass':'low','accompaniment':'middle','melody':'high'}[role]
    events=[]; evidence=[]
    for start,end,pitch,confidence,_ in sorted(raw):
        if start >= seconds or end <= start: continue
        end=min(float(end),seconds); start=float(start)
        segment=mono[int(start*22050):max(int(start*22050)+1,int(end*22050))]
        rms=float(np.sqrt(np.mean(segment**2)))
        # Amplitude follows audio, not model confidence; do not promote leakage.
        level=min(1.,rms*4)
        events.append([start*bpm/60,(end-start)*bpm/60,note_name(int(pitch)),level])
        evidence.append(dict(start_seconds=start,end_seconds=end,midi=int(pitch),confidence=float(confidence),rms=rms))
    score=promote(dict(bpm=bpm,beats=seconds*bpm/60,parts={part:events},source_audio_sha256=file_hash(path)),
                  title=path.stem,source_id=path.name,source_kind='audio')
    score['model_evidence']=dict(model='basic-pitch',version=version('basic-pitch'),model_sha256=file_hash(model_path),
      pcm_sha256=hashlib.sha256(mono.astype('<f4').tobytes()).hexdigest(),sample_rate=22050,settings=settings,notes=evidence)
    save(output,score)


def separate(path, output):
    import numpy as np
    import soundfile as sf
    import torch
    from demucs.apply import apply_model
    from demucs.pretrained import get_model
    path=Path(path); output=Path(output)
    y,sr=sf.read(path,always_2d=True,dtype='float32')
    if sr!=44100 or y.shape[1] not in (1,2):
        raise ValueError('Separation expects mono/stereo 44100 Hz WAV')
    if y.shape[1]==1: y=np.repeat(y,2,axis=1)
    torch.set_num_threads(4)
    model=get_model('htdemucs').cpu().eval()
    signal=torch.from_numpy(y.T.copy()); ref=signal.mean(0); mean,std=ref.mean(),ref.std()
    if std<1e-8: raise ValueError('Source is silent')
    with torch.no_grad():
        stems=apply_model(model,((signal-mean)/std)[None],shifts=0,overlap=.25,progress=True,device='cpu')[0]*std+mean
    output.mkdir(parents=True,exist_ok=True)
    manifest=dict(source_audio_sha256=file_hash(path),model='htdemucs',demucs_version=version('demucs'),
                  sample_rate=sr,shifts=0,overlap=.25,stems={})
    # Bind output stems and exact loaded parameters, not just their filenames.
    h=hashlib.sha256()
    for key,tensor in sorted(model.state_dict().items()):
        h.update(key.encode()); h.update(tensor.detach().cpu().numpy().tobytes())
    manifest['model_state_sha256']=h.hexdigest()
    for name,signal in zip(model.sources,stems):
        target=output/(name+'.wav'); sf.write(target,signal.T.numpy(),sr,subtype='FLOAT')
        manifest['stems'][name]=dict(path=target.name,sha256=file_hash(target))
    (output/'separation.json').write_text(json.dumps(manifest,indent=2)+'\n')


def evidence(score, stems, output):
    import numpy as np
    import soundfile as sf
    import librosa
    from .vocal_phrases import harmonic_features
    stems=Path(stems); output=Path(output); output.mkdir(parents=True,exist_ok=True)
    separation=json.loads((stems/'separation.json').read_text())
    if separation['source_audio_sha256']!=score['source_audio_sha256']:
        raise ValueError('Stems and score belong to different recordings')
    if score['timing']['source_offset_seconds'] != 0:
        raise ValueError('Evidence command currently requires uncropped aligned stems')
    manifest=dict(source_audio_sha256=score['source_audio_sha256'],input_sha256=digest(score),
                  sample_rate=22050,hop=256,fft=4096,parts={})
    for part,name in (('low','bass'),('middle','other'),('high','vocals')):
        name=score.get('stem_roles',{}).get(part,name)
        if name not in separation['stems']: raise ValueError(f'Unknown evidence stem for {part}: {name}')
        stem=stems/separation['stems'][name]['path']
        if file_hash(stem)!=separation['stems'][name]['sha256']: raise ValueError('Stem contents changed')
        y,sr=sf.read(stem,always_2d=True,dtype='float32')
        if abs(len(y)/sr-score['loop_seconds'])>1/22050: raise ValueError('Stem and score lengths differ')
        y=librosa.resample(y.mean(axis=1),orig_sr=sr,target_sr=22050)
        q=harmonic_features(y,22050,pitches=np.arange(24,97))
        target=output/(part+'.npz'); np.savez_compressed(target,**q)
        manifest['parts'][part]=dict(path=target.name,sha256=file_hash(target),stem=name,stem_sha256=file_hash(stem),
           pcm_sha256=hashlib.sha256(y.astype('<f4').tobytes()).hexdigest())
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


def acoustic_audit(score, manifest_path):
    import numpy as np
    from .audit_song import audit
    path=Path(manifest_path); manifest=json.loads(path.read_text())
    if manifest['source_audio_sha256']!=score['source_audio_sha256'] or manifest['input_sha256']!=digest(score):
        raise ValueError('Evidence manifest does not match this score')
    features={}
    for part,entry in manifest['parts'].items():
        p=path.parent/entry['path']
        if file_hash(p)!=entry['sha256']: raise ValueError('Feature archive changed')
        features[part]=dict(np.load(p,allow_pickle=False))
    report=audit(score,features)
    report['feature_manifest']=manifest
    return report


def transcribe_stems(stems, output, bpm):
    """Keep roles explicit; preserve full source timing and per-stem evidence."""
    import tempfile
    import numpy as np
    import soundfile as sf
    import librosa
    from .score import load, PARTS
    from .signal_analysis import percussion
    stems=Path(stems); manifest=json.loads((stems/'separation.json').read_text())
    parts={p:[] for p in PARTS}; evidence_by_part={}; durations=[]
    with tempfile.TemporaryDirectory(prefix='slopwave-') as work:
        for name,role,part in [('bass','bass','low'),('other','accompaniment','middle'),('vocals','melody','high')]:
            entry=manifest['stems'][name]; path=stems/entry['path']
            if file_hash(path)!=entry['sha256']: raise ValueError('Stem changed since separation')
            target=Path(work)/(part+'.json'); transcribe(path,target,bpm,role); score=load(target)
            parts[part]=score['parts'][part]; durations.append(score['loop_seconds']); evidence_by_part[part]=score['model_evidence']
        entry=manifest['stems']['drums']; path=stems/entry['path']
        if file_hash(path)!=entry['sha256']: raise ValueError('Drum stem changed')
        y,sr=sf.read(path,always_2d=True,dtype='float32')
        durations.append(len(y)/sr)
        if max(durations)-min(durations)>1/22050: raise ValueError('Stems are not aligned to equal lengths')
        mono=librosa.resample(y.mean(axis=1),orig_sr=sr,target_sr=22050)
        parts.update(percussion(mono,bpm)); beats=durations[0]*bpm/60
        for part,rows in parts.items():
            parts[part]=[[at,min(length,beats-at),pitch,level] for at,length,pitch,level in rows if 0<=at<beats and length>0]
        score=promote(dict(bpm=bpm,beats=beats,parts=parts,source_audio_sha256=manifest['source_audio_sha256']),
                      title='Stem transcription',source_id='local:separated-recording',source_kind='audio')
        score['separation']=manifest; score['stem_model_evidence']=evidence_by_part
        save(output,score)


def decode(score, stems, output):
    """Save a vocal sequence hypothesis; this does not accept it as reviewed."""
    import numpy as np
    import librosa
    import soundfile as sf
    from .vocal_phrases import harmonic_features, decode_vocal
    from .strudel import note_name
    from .score import step
    if score['stage']!='detections': raise ValueError('Decode raw detections before applying saved corrections')
    if score['timing']['source_offset_seconds']!=0: raise ValueError('Decoder currently requires uncropped aligned stems')
    stems=Path(stems); separation=json.loads((stems/'separation.json').read_text())
    if separation['source_audio_sha256']!=score['source_audio_sha256']: raise ValueError('Stem/source mismatch')
    entry=separation['stems']['vocals']; path=stems/entry['path']
    if file_hash(path)!=entry['sha256']: raise ValueError('Vocal stem changed')
    y,sr=sf.read(path,always_2d=True,dtype='float32')
    if abs(len(y)/sr-score['loop_seconds'])>1/22050: raise ValueError('Vocal stem and score lengths differ')
    mono=librosa.resample(y.mean(axis=1),orig_sr=sr,target_sr=22050)
    features=harmonic_features(mono,22050)
    f0,_,prob=librosa.pyin(mono,sr=22050,fmin=65,fmax=1000,frame_length=2048,hop_length=256)
    times=librosa.frames_to_time(np.arange(len(f0)),sr=22050,hop_length=256)
    raw=score['stem_model_evidence']['high']['notes']
    raw_notes=[[n['start_seconds'],n['end_seconds'],n['midi'],n['confidence']] for n in raw]
    reference=max(1e-8,float(np.percentile(features['rms'],90)))
    notes,evidence=decode_vocal(features,raw_notes,times,f0,prob,reference)
    from copy import deepcopy
    result=deepcopy(score)
    result['parts']['high']=[[start*score['bpm']/60,min((end-start)*score['bpm']/60,score['beats']-start*score['bpm']/60),note_name(pitch),level]
                            for start,end,pitch,level in notes if start*score['bpm']/60<score['beats']]
    result['vocal_phrase_evidence']=evidence
    settings=dict(sample_rate=22050,hop=256,fft=4096,f0_range=[65,1000],reference_rms=reference,
                  vocal_stem_sha256=entry['sha256'],librosa=version('librosa'))
    save(output,step(score,result,'detections','decode-vocal',settings))
