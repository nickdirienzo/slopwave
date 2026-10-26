# Workflows

Use explicit file paths. The public commands do not consult a private track
catalog, fetch YouTube recordings, or run a hosted LLM. Work in an ignored directory
such as `build/`; keep raw inputs and every derived stage separately.

## Review an authored or transcribed score

```sh
slopwave review examples/lantern/score.json -o build/review.json
slopwave validate examples/lantern/score.json
slopwave correct examples/lantern/score.json --patch build/patch.json -o build/reviewed.json
slopwave arrange build/reviewed.json --profile synth -o build/arranged.json
slopwave mix build/arranged.json -o build/mixed.json
slopwave export build/mixed.json -o build/song.strudel.js
```

`build/patch.json` is a decision you author after inspecting the review. It is not
created automatically by these commands. See the [patch format](score-format.md).
Without audio, `review` supplies structural phrase candidates, not source-backed
pitch verdicts. Whole-score review is the default; `--start` and `--end` select a
passage in score-relative seconds for the structural reviewer.

## Optional local audio inference

Use Python 3.10 or 3.11 for the optional model environment. Basic Pitch 0.4.0's
platform-dependent dependencies are not compatible with every newer Python release.
The lightweight score/arrangement/render quickstart supports 3.10–3.12.

```sh
python -m pip install -e '.[transcription,stems]'
slopwave separate input.wav -o build/stems
slopwave transcribe-stems build/stems --bpm 112 -o build/detections.json
slopwave decode build/detections.json --stems build/stems -o build/decoded.json
slopwave evidence build/decoded.json --stems build/stems -o build/evidence
slopwave review build/decoded.json --features build/evidence/manifest.json -o build/acoustic-review.json
```

The BPM above is an example. Measure the input's pulse; do not copy a fixture's
tempo to another recording. BPM supplies coordinates, without snapping original
attacks. Separation expects mono/stereo 44100 Hz WAV. Demucs may download weights
on first use and use substantial CPU/memory. Outputs include a source hash, loaded
model state hash, settings, and individual stem hashes.

For a single instrument or vocal file, use:

```sh
slopwave transcribe melody.wav --bpm 112 --role melody -o build/detections.json
```

The decoder requires a separated-stem transcription and matching stems. It keeps
its result at `detections` because a sequence inference is not a review decision.
Raw model confidence remains evidence; event gain follows measured amplitude.
Evidence archives are generated explicitly and hash-bound to the score; changing
the score requires generating a matching manifest. The current evidence commands
require uncropped stems aligned to source time zero. Acoustic review covers pitched
voices; it does not establish every missing note or correct drum hit.

Inspect evidence, save a patch, apply it to the decoded score, then arrange/mix/export.
Empty `edits` may record a review with no supported corrections; include the review
reference and unresolved findings. Do not use an empty patch as a claim of accuracy.

## Arrangement research

CLI profiles are `synth`, `piano-strings`, `bluegrass`, and `kazoo`. The last three
use external instrument resources; they are not covered by the local synth-only
browser runner. Paste their generated program into a compatible Strudel editor
with the requisite samples and verify sample starts before claiming playback.
The simple bluegrass profile is an early experiment, not the later evidence-driven
performance profile and not a general style-transfer model.
It requires an explicit `beat_times_seconds` sequence (at least eight increasing
pulse times), measured from a recording or supplied by the author of a score.

The Python modules retain the deeper experimental pieces:

- `refinement`: pulse/envelope/harmonic measurements and legacy guarded corrections.
- `vocal_phrases`: harmonic features, sequence decoding and acoustic repetition support.
- `audit_song.audit`: whole-score acoustic anomaly candidates, with optional decoder/F0 evidence.
- `bluegrass`: successive arrangement approaches, including source-supported
  continuity and exact-event performance decisions. Later versions require explicit
  harmony, riff, and performance-review inputs; absent evidence is not synthesized.
- `harmony.infer` / `riff.infer`: legacy feature-manifest APIs for arrangement cues.
  Their manifest uses `parts.low/middle.features`, `features_sha256`, `stem`, and
  `stem_sha256`, relative to the manifest directory. Harmony also needs source pulse
  anchors; riff needs the harmony review file. These are research APIs, not the
  public audit manifest; inspect their input contracts before use.
- `signal_analysis`: original loop detection, pulse estimation and drum-onset heuristics.

These modules preserve useful algorithms without shipping their old song-specific
threshold overrides, correction data, or cached model results. They require suitable
inputs and listening evaluation; retaining an algorithm does not validate it for
new genres or recordings.
