# slopwave

A research workbench exploring how audio models, musical heuristics, and
agent-assisted review can produce editable Strudel arrangements.

The intended operator is a coding agent working with a human who listens. Treat
Python and Node entry points as tools for carrying out a musical request, not a
workflow the user must manually orchestrate. There is no built-in autonomous agent,
agent SDK, or hosted LLM dependency: the user's coding agent supplies the judgment.

Read [agent workflow](docs/agent-workflow.md) when starting a transcription or
arrangement task. For a whole-song or passage anomaly review, use the optional
[song-review skill](.agents/skills/song-review/SKILL.md). Detailed executable
operations live in [workflows](docs/workflows.md), not in this entrypoint.

## Preserve the research

- Keep source audio, raw detections, evidence, reviewed scores, arrangements, and
  mixes separate. Save input/output hashes and the decisions that connect them.
- Never overwrite an approved arrangement to try another instrument or repair a
  different version. Work in a new experiment directory and compare affected parts.
- Corrections must match the source and exact expected events. A stale guard is a
  reason to investigate, not bypass validation. Rebuild from saved decisions.
- Diagnose missing playback before changing tempo or notes. Structural checks do
  not establish sound output; actual starts do not establish musical quality.
- Pitch and envelope models provide evidence. Preserve supported leaps, real rests,
  swing, and voice identity across registers. Avoid blanket ceilings or hard keys.
- Distinguish a repeated attack from a fragmented hold using source context. Review
  gate duration together with the chosen instrument's attack and release.
- Model confidence is not volume. Do not turn separation leakage into a loud note.
  Mix once, budget concurrent backing, and preserve unmixed gains.
- A genre change is an arrangement decision, not necessarily a transcription fix.
  Record which pitches, rhythms and voicings changed and why.
- Browser diagnostics must remain bounded. Preserve per-bar scheduling, indexed
  partial-bar handling, and bar-crossing holds. Sample playback needs buffer-start
  verification; oscillator tests cannot establish it.
- Report musical uncertainty and human listening feedback separately from model,
  numerical, structural, and browser evidence. Never claim listening occurred when
  only plots or execution metrics were inspected.

## Local artifacts and release boundary

Keep experiments under ignored `build/` or `.cache/`. Use explicit paths and read
existing manifests before invoking tools. No private track catalog is bundled.
The only public musical fixture is the original Lantern study. Do not add source
recordings, recovered commercial scores/MIDI, or cover audio to the public example
collection without established redistribution rights. A source URL is provenance,
not permission. This does not prevent authorized local research.

Follow the user's requested scope. A local correction does not automatically mean
retranscribe the full song. When fixes are authorized, finish the evidence-based
edit and validation without adding a separate routine approval step. If evidence
is missing, state what can be assessed and collect it when within scope. Ask the
user only when a missing preference or fact materially prevents progress.
