# slopwave review operations

Use explicit files from the requested experiment. The included cover example is
Strudel source; no private track catalog is bundled. Read [workflows](../../../../docs/workflows.md)
for executable commands and [score format](../../../../docs/score-format.md) for
units, stages, source identity and correction contracts.

`slopwave review score.json -o build/review.json` scans structural phrase candidates.
For source-backed whole-score candidates, generate the explicit evidence manifest
and pass `--features`; this currently requires uncropped aligned stems. Without
source audio, report reduced evidence rather than treating a structural flag as
proof of a pitch mistake. Acoustic flags do not identify all missing notes.

Store a v1 patch with source hash, canonical input score hash, exact expected
sequences, replacements, reasons and evidence references. Apply it with `slopwave
correct`, then arrange, mix once, and export into a new revision. Retain prior
approved outputs. The legacy research helper formats are different; do not feed a
legacy patch into the v1 CLI or silently weaken its guards.

Use `npm run check -- score.json song.strudel.js` for event preservation across two
repetitions. `npm run playback -- score.json song.strudel.js build/playback.json`
checks the complete synthesized arrangement's actual starts and scheduling deadlines.
`npm run render -- score.json song.strudel.js build/song.wav` records offline audio
properties. The local runners reject sample-dependent arrangements. Such work needs
a sample-aware browser check in a compatible Strudel environment; report that gap
if unavailable. A WAV render alone does not test real-time scheduling.

Reports should include source/input/output hashes, scope in score and source
seconds, coverage, evidence references, supported corrections, deliberate rendering
changes, unresolved candidates, validation results and whether human listening
comparison occurred. Keep them in the ignored experiment directory unless the
music and evidence are cleared for public redistribution.
