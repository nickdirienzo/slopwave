"""Versioned interchange boundary; research helpers keep their original event tuples."""
from copy import deepcopy
import hashlib
from importlib.resources import files
import json
import math
from pathlib import Path
import re

PARTS = ('low', 'middle', 'high', 'kick', 'snare', 'hat')
ROLES = dict(low='bass', middle='accompaniment', high='melody', kick='kick', snare='snare', hat='hat')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def load(path):
    value = json.loads(Path(path).read_text())
    validate(value)
    return value


def save(path, value):
    validate(value)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def validate(value):
    from jsonschema import Draft202012Validator
    schema = json.loads(files('slopwave').joinpath('score.schema.json').read_text())
    Draft202012Validator(schema).validate(value)
    # JSON accepts NaN in some readers; forbid it at every depth.
    json.dumps(value, allow_nan=False)
    if abs(value['loop_seconds']-value['beats']*60/value['bpm']) > 1e-5:
        raise ValueError('loop_seconds must equal beats * 60 / bpm')
    for part, rows in value['parts'].items():
        previous = -1
        for at, duration, pitch, gain in rows:
            if at < previous or at >= value['beats'] or at+duration > value['beats']+2e-5:
                raise ValueError(f'{part}: unsorted event or event outside score extent')
            if isinstance(pitch, str):
                from .refinement import midi_pitch
                if not 0 <= midi_pitch(pitch) <= 127:
                    raise ValueError('Pitch outside MIDI 0..127')
            previous = at
    for part, voice in value.get('voices', {}).items():
        if part not in PARTS:
            raise ValueError('Unknown voice')
        for key, number in voice.items():
            if key == 'sound':
                if not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_]*', number):
                    raise ValueError('Sound identifiers must be plain identifiers')
            elif isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number):
                raise ValueError('Voice controls must be finite numbers')
    return value


def promote(data, *, title, source_id, source_kind, stage='detections', source_offset=0):
    """Explicit adapter for legacy research results; never guess input units."""
    result = deepcopy(data)
    result.update(schema_version=1, title=title, stage=stage,
                  roles=deepcopy(ROLES), timing=dict(unit='quarter_note_beats', source_offset_seconds=source_offset),
                  provenance=dict(source_id=source_id, source_kind=source_kind, steps=[]),
                  source=source_id, mode='full-song-stems',
                  status='Research result; listening review pending')
    result.setdefault('beat_offset_seconds', 0)
    result['loop_seconds'] = result['beats']*60/result['bpm']
    result['parts'] = {part: sorted(result.get('parts', {}).get(part, [])) for part in PARTS}
    validate(result)
    return result


def step(source, result, stage, operation, settings=None):
    result = deepcopy(result)
    for key in ('schema_version', 'roles', 'timing', 'provenance', 'title'):
        result[key] = deepcopy(source[key])
    result['stage'] = stage
    result['provenance']['steps'].append(dict(operation=operation, input_sha256=digest(source), settings=settings or {}))
    validate(result)
    return result


def apply_corrections(source, patch):
    """Whole-input and exact-event guards: stale edits fail rather than drifting."""
    validate(source)
    if source['stage'] not in ('detections', 'reviewed'):
        raise ValueError('Correct detections/reviewed scores before arrangement or mixing')
    if patch.get('source_audio_sha256') != source['source_audio_sha256'] or patch.get('input_sha256') != digest(source):
        raise ValueError('Correction source or score changed; re-review the patch')
    result = deepcopy(source)
    for edit in patch['edits']:
        if not edit.get('reason') or not edit.get('evidence'):
            raise ValueError('Corrections require a reason and evidence reference')
        rows = result['parts'][edit['part']]
        expected = edit['expected']
        if not expected:
            raise ValueError('Use an explicit insertion with reviewed span for missing notes')
        positions = [i for i in range(len(rows)-len(expected)+1) if rows[i:i+len(expected)] == expected]
        if len(positions) != 1:
            raise ValueError('Expected events changed or are ambiguous')
        i = positions[0]
        rows[i:i+len(expected)] = deepcopy(edit['replacement'])
        rows.sort()
    for addition in patch.get('additions', []):
        if not addition.get('reason') or not addition.get('evidence'):
            raise ValueError('Additions require evidence and reason')
        event = addition['event']; at, duration = event[:2]
        rows = result['parts'][addition['part']]
        if any(r[0] < at+duration and r[0]+r[1] > at for r in rows):
            raise ValueError('Addition overlaps existing events; use an explicit replacement')
        rows.append(deepcopy(event)); rows.sort()
    result['corrections'] = deepcopy(source.get('corrections', []))+[deepcopy(patch)]
    return step(source, result, 'reviewed', 'apply-corrections', {'patch_sha256': digest(patch)})
