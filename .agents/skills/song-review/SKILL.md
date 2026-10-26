---
name: song-review
description: Review Strudel transcriptions in slopwave for musical anomalies across a whole song or a reported passage. Use for octave errors, apparent missing notes, bad articulation, or uneven mixing; investigate source evidence, preserve scoped corrections, and verify regeneration and playback.
---

# Song review

Produce a timestamped review that distinguishes transcription errors, rendering
choices, playback failures, and unresolved musical interpretations. The scripts
collect evidence and reproduce saved edits; Codex interprets that evidence.

Read the project's [AGENTS.md](../../../AGENTS.md) for preservation and playback
invariants. Read [Harness operations](references/harness.md) for commands,
supported inputs, correction formats, and validation. Run commands from the
project root. Use the requested track and scope; a local complaint does not
automatically require a whole-song rewrite.

## Establish the review

Identify the requested experiment manifest, current score and Strudel file, raw
detections, prior corrections, and available source/stem evidence.
Preserve a before snapshot or hashes before editing. Carry forward existing
corrections and listening feedback; do not restart from an unreviewed model output.

Check what the part names mean. In explicitly separated arrangements `high` may
mean vocal even when its pitch is low; other arrangements use pitch-register
bins. Determine the time origin: arrangement rows use beats, while source reports
use seconds. Account for a cropped loop's source offset. Verify evidence belongs
to the same recording and settings before reusing it.

For a whole-song review, scan the entire available arrangement across every
voice. Start investigation at the user's timestamp, then prioritize repeated
failure patterns elsewhere. Record coverage and missing evidence. A structural
scan without source audio is useful, but cannot establish source pitch accuracy.

## Decide what a finding means

Use automated flags as investigation prompts. Examine the phrase around each
candidate, not just the suspicious row. Evaluate competing explanations:

| Symptom | Evidence to compare | Decision boundary |
| --- | --- | --- |
| Sudden high or low note | Fundamental and overtone support, neighboring register, simultaneous voices, acoustically matching repetitions | A large leap or stronger lower harmonic alone does not prove an octave error. Preserve supported leaps and octave doubles. |
| Missing or fragmented notes | Raw detections, voiced activity, source envelope attacks, actual oscillator starts | Distinguish transcription omission, masking, a held note split by the model, and scheduler loss. Restore a note only with local evidence. |
| Repeated beeps or sloppy holds | Pitch-band envelope at boundaries, syllable attacks, synth attack/release | Merge fragments only where continuity supports a hold; retain real repeated attacks. Duration alone does not justify truncation. |
| Loud or piercing passage | Source RMS, overlapping voices, rendered levels, confidence versus amplitude | A correct pitch can need a gain or timbre adjustment. Quiet stem leakage must not become loud merely because a model is confident. |
| Different repeated phrase | Acoustic alignment, pitch contour, local timing and voice identity | Repetitions supply supporting evidence, not a template that forces identical notes or rhythm. |

Check both upward and downward register anomalies, and inspect bass and backing
as well as the lead. Polyphonic backing is especially ambiguous. Fixed pitch
ceilings, a song-wide octave fold, or another track's key/grid/thresholds are not
substitutes for evidence. Treat weak fundamentals, low voicing confidence, and
separation leakage as uncertainty rather than independent proof of an error.

Classify findings as supported corrections, rendering adjustments, or open
candidates. Save the reason and contradictory evidence when relevant. If more
evidence would not resolve a candidate, leave it open with a timestamp; do not
keep editing merely to reduce the flag count. Ask for a listening timestamp only
when it would change a decision and the available evidence cannot supply it.

## Make corrections reproducible

A review-only request should produce findings without musical edits. When fixes
are requested or already authorized by the active task, apply supported changes
within that scope. Do not introduce a separate approval step for ordinary local
corrections already authorized.

Store changes against exact expected events and a source hash, with source-time
intervals and evidence. Use the existing correction formats and pipeline order
described in the operations reference. Retain raw detections and decoder evidence.
Do not hand-patch only the generated JavaScript, silently weaken stale-input
guards, or apply gain compression twice. If the current format cannot express a
justified change, explicitly extend and validate the pipeline rather than hiding
the edit in a generated artifact.

## Verify and report

Rebuild the affected track and compare reviewed and unreviewed events. Preserve
unrelated songs. Check that another rebuild reproduces the result when claiming
determinism. Test changed helper behavior where necessary and validate generated
event timing, including holds and the repeat boundary.

For playback/dropout complaints, verify actual browser starts in the affected
passage. Changes spanning the song or sustained scheduler concerns warrant a full
song run when the browser is available. Record the tested file hash and interval;
do not reuse a passing result from a different revision. Keep instrumentation
bounded and separate missing starts from late starts and clipping.

Persist the review in the experiment's report conventions with source and
output hashes, coverage, prioritized findings, before/after events or correction
references, evidence, disposition, open timestamps, and validation results.
Summarize what changed and what remains uncertain for the user. State whether
listening comparison actually occurred. Numerical evidence, fewer flags, and
successful playback do not establish musical correctness.
