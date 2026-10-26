# Score format v1

The machine-readable contract is [`score.schema.json`](../src/slopwave/score.schema.json).
`slopwave validate` adds finite-number, ordering, pitch-range, and extent checks.
Unknown schema versions are rejected. Extra research metadata is allowed; the
six part keys are fixed for compatibility with the existing algorithms.

| Field | Meaning |
| --- | --- |
| `schema_version` | Integer `1` |
| `stage` | `detections`, `reviewed`, `arranged`, or `mixed` |
| `parts` | Lists of `[start, duration, pitch, level]`, ordered by start |
| `roles` | Explicit meaning of each part; `high` is not necessarily high in pitch |
| `bpm` | Positive quarter-note beats per minute, defining a coordinate system |
| `beats` | Exact score/repeat extent, including a possible partial final bar |
| `loop_seconds` | Exactly `beats * 60 / bpm` within numerical tolerance |
| `timing.unit` | `quarter_note_beats`; never infer units from magnitudes |
| `timing.source_offset_seconds` | Source timestamp corresponding to score beat zero |
| `source_audio_sha256` | Audio-file SHA-256; for authored fixtures, explicitly documented content hash |
| `provenance` | Source identifier/kind and ordered operation records with input hashes/settings |

A source timestamp is `source_offset_seconds + start * 60 / bpm`. Audio evidence
arrays use seconds. `beat_offset_seconds` is a legacy pulse-estimation annotation,
not an extra offset to add to every event. Measured attack times can retain swing
or drift even though BPM is constant. Tempo maps are not represented in v1.

Pitch is a MIDI integer 0–127 or a lowercase name such as `fs4`. Pitched algorithms
currently expect named pitches; use names for melody, accompaniment and bass.
The percussion helpers retain numeric MIDI placeholders. Level is relative linear
amplitude, 0–1, not MIDI velocity, dB, or model confidence. `voices` assigns timbre
and envelopes; `mix` contains part gains. Duration is a note gate; instrument
release can extend the audible tail. Events must start and end inside the score.

The public profiles currently interpret `low=bass`, `middle=accompaniment`, and
`high=melody`. These are explicit adapter slots rather than pitch classifications.
More flexible voice graphs and phrase/section structure are future schema work.

## Stages and corrections

The CLI requires reviewed inputs for arrangement, arranged inputs for mixing,
and mixed inputs for export. It rejects a second mix pass. Stage labels record
workflow disposition, not proof of musical correctness. Agent/human review remains
responsible for interpreting evidence. An authored score may begin at `reviewed`.

A correction patch contains:

```json
{
  "source_audio_sha256": "<recording hash>",
  "input_sha256": "<canonical score hash from slopwave validate>",
  "edits": [{
    "part": "high",
    "expected": [[1, 0.5, "c5", 0.4]],
    "replacement": [[1, 0.5, "c4", 0.4]],
    "reason": "Lower fundamental supported in this phrase",
    "evidence": "review.json#finding-3"
  }]
}
```

`expected` must match one contiguous sequence exactly. Empty replacement deletes
that sequence. Whole-input and source hashes reject stale decisions. Optional
`additions` carry `part`, `event`, `reason`, and `evidence`; additions cannot overlap
existing notes in that part. Use an explicit replacement to review overlaps.
A patch with no edits can record acceptance without changing notes; include the
review report/reference in the patch rather than silently labelling a model output
as verified. Evidence references document judgment; the program does not prove the
truth of prose or follow arbitrary URLs.

Canonical hashes use UTF-8 JSON with sorted keys, compact separators, and no NaN.
Every derived stage retains the preceding input hash. Raw inputs are separate
files and never overwritten by the normal CLI. Legacy correction/decoder formats
remain in the Python research modules, with their original regression tests; they
are not interchangeable with the v1 patch format.
