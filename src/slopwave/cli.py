"""File-oriented entry points; no private track catalog or implicit downloads."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from .score import load, save, validate, digest, step, apply_corrections


def write_json(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False)+'\n')


def arrange(source, profile):
    if source['stage'] != 'reviewed':
        raise ValueError('Arrangement requires a reviewed score')
    if source['roles']['high'] != 'melody' or source['roles']['low'] != 'bass':
        raise ValueError('These experimental profiles require explicit melody/bass roles')
    if profile == 'synth':
        result = deepcopy(source)
        result['voices'] = dict(low=dict(sound='sine', attack=.005, release=.05, lpf=900),
                                middle=dict(sound='triangle', attack=.035, release=.10, lpf=2400),
                                high=dict(sound='triangle', attack=.006, release=.08, lpf=4500))
    elif profile == 'piano-strings':
        from .arrange import piano_strings
        result = piano_strings(source)
    elif profile == 'bluegrass':
        from .bluegrass import bluegrass
        result = bluegrass(source)
    elif profile == 'kazoo':
        from .kazoo import kazoo_rock
        # Legacy function guards already-mixed inputs, but only copies events and
        # assigns voices. The v1 pipeline supplies unmixed events and mixes later.
        adapter = deepcopy(source); adapter['mix_review'] = {'profile':'stem-rock-v1'}
        result = kazoo_rock(adapter); del result['mix_review']
    else:
        raise ValueError('Unknown arrangement profile')
    return step(source, result, 'arranged', 'arrange', {'profile':profile})


def mix(source, profile='stem-rock-v1'):
    if source['stage'] != 'arranged':
        raise ValueError('Mix exactly once, after arrangement')
    if profile == 'preserve':
        if not all(key in source.get('mix', {}) for key in ('low','middle','high','drums')):
            raise ValueError('Preserving a mix requires explicit arrangement bus levels')
        result=deepcopy(source)
        result['mix_review']=dict(profile='preserve',notes_and_timing_preserved=True,
            policy='Retain explicit reviewed note gains and bus levels without additional compression.')
        return step(source,result,'mixed','mix',{'profile':profile})
    if profile != 'stem-rock-v1': raise ValueError('Unknown mix profile')
    from .mixing import refine_mix
    result = refine_mix(source, 'stem-rock-v1')
    # Preserve the arrangement's timbre and intended part balance while applying
    # the event-level density budget and lead ducking once.
    for key in ('voices','mix','drum_mix'):
        if key in source: result[key] = deepcopy(source[key])
    return step(source, result, 'mixed', 'mix', {'profile':'stem-rock-v1'})


def export(source):
    if source['stage'] != 'mixed':
        raise ValueError('Export requires the mixed stage')
    from .strudel import strudel_source
    title = source['title'].replace('\n',' ').replace('\r',' ')
    source_id = source['provenance']['source_id'].replace('\n',' ').replace('\r',' ')
    text = strudel_source(dict(title=title, youtube=source_id, collection='slopwave'), source)
    at = text.index('const BPM = ')
    # Keep preload code, but replace misleading historical transcription headers.
    pre = text[:at]
    barrier = next((pre.index(marker) for marker in ('// Load the ', '// Preload acoustic ') if marker in pre), len(pre))
    header = f'// {title} — slopwave\n// Input score SHA-256: {digest(source)}\n// Research arrangement; listening evaluation is separate from execution checks.\n// Paste the entire file into https://strudel.cc to play.\n\n'
    return header+pre[barrier:]+text[at:]


def export_module(source):
    """The consumer awaits preload(S), then owns tempo and playback."""
    text = export(source)
    prelude = text[:text.index('const BPM = ')]
    preload = ('export async function preload(S) {\n'
               'const {getAudioContext, getFontBufferSource, registerSound} = S;\n'
               + prelude + '\n}\n')
    body = text[text.index('const BPM = '):].replace('setcpm(BPM / 4);\n', '', 1)
    body = body.replace('\nstack(\n', '\nreturn stack(\n', 1)
    return (f'// slopwave score SHA-256: {digest(source)}\n'
            f'export const bpm = {source["bpm"]!r};\n' + preload +
            f'export const beats = {source["beats"]!r};\n'
            'export const cps = bpm / 240;\n'
            'export function createPattern(S) {\n'
            'const {stack, cat, timecat, silence, note, gain} = S;\n' + body + ';\n}\n')


def main():
    parser = argparse.ArgumentParser(prog='slopwave', description='Research workbench for editable Strudel arrangements')
    subs = parser.add_subparsers(dest='command', required=True)
    from .session import add_parser, dispatch
    add_parser(subs)
    for name in ('validate','review','correct','arrange','mix','export'):
        sub = subs.add_parser(name); sub.add_argument('input', type=Path)
        if name != 'validate': sub.add_argument('-o','--output',type=Path,required=True)
        if name == 'correct': sub.add_argument('--patch',type=Path,required=True)
        if name == 'arrange': sub.add_argument('--profile',choices=['synth','piano-strings','bluegrass','kazoo'],default='synth')
        if name == 'mix': sub.add_argument('--profile',choices=['stem-rock-v1','preserve'],default='stem-rock-v1')
        if name == 'export': sub.add_argument('--format', choices=['repl','module'], default='repl')
        if name == 'review':
            sub.add_argument('--start',type=float,default=0); sub.add_argument('--end',type=float)
            sub.add_argument('--features',type=Path,help='Hash-bound evidence manifest for a whole-score acoustic audit')
    sub = subs.add_parser('transcribe'); sub.add_argument('input',type=Path)
    sub.add_argument('-o','--output',type=Path,required=True); sub.add_argument('--bpm',type=float,required=True)
    sub.add_argument('--role',choices=['melody','bass','accompaniment'],default='melody')
    sub = subs.add_parser('separate'); sub.add_argument('input',type=Path); sub.add_argument('-o','--output',type=Path,required=True)
    sub = subs.add_parser('evidence'); sub.add_argument('input',type=Path); sub.add_argument('--stems',type=Path,required=True); sub.add_argument('-o','--output',type=Path,required=True)
    sub = subs.add_parser('transcribe-stems'); sub.add_argument('input',type=Path); sub.add_argument('-o','--output',type=Path,required=True); sub.add_argument('--bpm',type=float,required=True)
    sub = subs.add_parser('decode'); sub.add_argument('input',type=Path); sub.add_argument('--stems',type=Path,required=True); sub.add_argument('-o','--output',type=Path,required=True)
    args = parser.parse_args()
    try:
        if args.command == 'session':
            print(json.dumps(dispatch(args), indent=2)); return
        if getattr(args, 'output', None) and args.output.resolve()==args.input.resolve():
            raise ValueError('Keep each pipeline stage in a separate file')
        if args.command in ('transcribe','separate','evidence','transcribe-stems','decode'):
            from . import audio
            if args.command=='transcribe': audio.transcribe(args.input,args.output,args.bpm,args.role)
            elif args.command=='separate': audio.separate(args.input,args.output)
            elif args.command=='evidence': audio.evidence(load(args.input),args.stems,args.output)
            elif args.command=='transcribe-stems': audio.transcribe_stems(args.input,args.output,args.bpm)
            else: audio.decode(load(args.input),args.stems,args.output)
            return
        data = load(args.input)
        if args.command=='validate':
            print(json.dumps(dict(valid=True,stage=data['stage'],events=sum(map(len,data['parts'].values())),sha256=digest(data))))
            return
        if args.output.resolve()==args.input.resolve():
            raise ValueError('Keep each pipeline stage in a separate file')
        if args.command=='review':
            if args.features:
                if args.start != 0 or args.end is not None:
                    raise ValueError('Acoustic feature review currently covers the whole score')
                from .audio import acoustic_audit
                report = acoustic_audit(data,args.features)
            else:
                from .review import review
                end = args.end if args.end is not None else data['loop_seconds']
                if not 0 <= args.start < end <= data['loop_seconds']:
                    raise ValueError('Review interval is outside the score')
                report = review(data,args.start,end)
            report.update(input_sha256=digest(data),source_audio_sha256=data['source_audio_sha256'],listening_comparison=False)
            write_json(args.output,report); return
        if args.command=='correct': result = apply_corrections(data,json.loads(args.patch.read_text()))
        elif args.command=='arrange': result=arrange(data,args.profile)
        elif args.command=='mix': result=mix(data,args.profile)
        else:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(export_module(data) if args.format == 'module' else export(data)); return
        save(args.output,result)
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))
    except ImportError as error:
        parser.error(f'{error}. Install the analysis, transcription or stems extra for this operation; see docs/workflows.md.')
