---
name: slopwave
description: Compose, transcribe, arrange, and revise editable Strudel music with slopwave, including looping game music and consumer-owned listening feedback. Use when a user requests slopwave or wants this music workflow installed in a project.
---

# slopwave

Use the consumer project's brief and listening feedback to produce editable music.
The agent supplies musical judgment; slopwave supplies score, arrangement, render,
and review tools. A render passing checks is not a musical-quality verdict.

## Set up or resume

Read the consumer's agent instructions and `.slopwave/config.json`, if present.
For first setup, use [setup](references/setup.md). Installing this skill folder
alone does not install the Python/Node toolchain. Keep the engine separate from
the consumer's music. Store briefs, plans, revisions, renders, and preferences in
the consumer's `.slopwave/` directory by default; honor an existing chosen location.
Do not write a consumer's experiments into the slopwave checkout.

Read [sessions](references/sessions.md) for commands and feedback semantics. On
resume, inspect the saved session before editing; do not assume the newest render
was accepted. Retain branches and previously accepted revisions.

## Make music

For a description, read [composition](references/composition.md). Author a plan
and explicit score, then use the existing arrangement/mix/export pipeline. No
text-to-music model or automatic quality critic is built in. Make sensible musical
choices within the brief without requiring the user to choose theory parameters.

For a cover or transcription, read `docs/workflows.md` in the configured toolchain.
For source-backed anomaly review, read that checkout's
`.agents/skills/song-review/SKILL.md` and follow its evidence and correction rules.
Those files belong to the toolchain, not this installed skill's parent folders.

Use `session render` for each listening candidate. It preserves a mixed score,
plan/brief, generated source, game module, WAV, runtime hashes, and checks as one
revision. Synth voices and declared custom one-shot sample_buffers are supported, with
embedded resource snapshots and actual sample-start checks. Read the toolchain
`docs/sound-design.md` for controls, resources and module preloading. Network GM
soundfont profiles still require their external runtime; do not claim local
checks verified them. WAV previews are finite passes, not verified seamless audio assets.

## Learn from the session

Record relevant user feedback against the exact revision they heard. Keep the
verbatim quote separate from your interpretation and include a message reference
when one is available. Do not invent one or collect unrelated conversation.

- “Too busy” is feedback, not proof that a subsequent edit improved anything.
- “Much better” can establish a comparison when the two versions are unambiguous.
- “Ship it” records acceptance; it does not establish all-pairs preference.
- Agent critiques, test results, silence, and inferred listening are not human labels.
- A changed brief is a new revision context; record it before rendering.

Use ordinary conversation; do not add a rating questionnaire after every edit.
Leave unclear comparisons unlabelled. Technical fixes can be recorded as technical
comparisons but are excluded from the default musical-preference export. Save
remaining complaints even when the user prefers the new version.

Feedback capture is agent-driven, not a background transcript listener. The tools
validate references and files; they cannot authenticate a quoted human judgment.
Use confirmed, relevant preferences from this consumer to guide later work. Export
a dataset when requested; do not train models, upload feedback, or publish artifacts
as an implicit consequence of installing the skill.
