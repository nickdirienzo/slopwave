# Working through a coding agent

slopwave is a repository of tools, research methods, and durable musical decisions
for a coding agent. The agent reads code and evidence, invokes local models and
scripts, investigates anomalies, edits explicit correction files, and regenerates
reviewable outputs. The human supplies intent and listening feedback.

The tools do not make semantic musical decisions automatically. There is no agent
service to deploy and no dependency on one vendor's agent API. `AGENTS.md` provides
the local context; the optional song-review skill supplies a focused review method.

## Example requests

- “Render the original Lantern example and give me a WAV and the Strudel source.”
- “Transcribe this local recording into an instrumental Strudel draft. Preserve
  its timing, retain the raw detections, and flag uncertain phrases.”
- “The melody around 0:18 sounds like repeated beeps. Compare the source envelope
  and the actual playback; fix supported articulation errors.”
- “Try a piano-and-strings arrangement of this reviewed score. Preserve the source
  score and record arrangement-specific decisions separately.”
- “Review this whole arrangement for octave errors, missing notes and uneven mix.
  Leave ambiguous findings open and give me timestamps to listen to.”

## Task protocol

1. Identify the input recording or authored score, requested output, existing
   approved versions, listening feedback, and available evidence. Keep source
   offsets and event units explicit. Verify source hashes before reusing evidence.
2. Create an ignored experiment directory with a small manifest linking source,
   raw detections, features, corrections, reviewed score, arrangement, mix, Strudel,
   audio and validation reports. Reuse exact matching artifacts; do not rerun heavy
   inference solely because a prior process timed out or a result is unfamiliar.
3. Choose tools for the task. For authored input, skip transcription. For audio,
   consider separated stems, pitch candidates, phrase decoding and acoustic review.
   The [operations reference](workflows.md) documents commands and limitations.
4. Interpret findings in phrase context. Separate source transcription corrections,
   deliberate arrangement changes, timbre/mix choices, and execution failures.
   Save supported decisions against exact inputs. Keep uncertainty with evidence.
5. Regenerate from the retained score and decisions. Check unchanged parts and
   approved versions, then run relevant regressions and structural checks. Use
   real browser playback when onset/dropout behavior is implicated. Sampled voices
   need a suitable sample-aware runtime; do not substitute synth-only success.
6. Deliver playable source/audio, a concise account of changes, tested scope and
   unresolved listening timestamps. Do not make the user read internal diagnostics
   to understand the result. Incorporate feedback into another scoped revision.

Record enough to replay decisions without the conversation. The initial agent
reasoning is not deterministic, but applying a saved patch and exporting the same
score should be. A patch's evidence string is a reference for review, not a machine
verification that a note is correct.

## Bootstrapping

Use the setup in [workflows](workflows.md#setup-and-original-example) to install lightweight tools. Add `analysis`,
`transcription`, or `stems` extras only when required. On a tool-restricted host,
explain the specific blocked operation; keep doing independent local work.
Do not depend on developer-machine paths, cached recordings, or a live public REPL
for the original synth fixture. A useful first task is reproducing that fixture
from a fresh checkout before working on an external recording.
