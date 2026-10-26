# Music sessions in another project

slopwave can be used as an agent skill backed by the existing Python/Node tools.
The consuming project owns its briefs, music, revisions, listening feedback, and
preference data. The skill and engine do not maintain a shared taste database.

Install the folder at `.agents/skills/slopwave` from this repository using your
agent's skill installer. Then follow its [setup instructions](../.agents/skills/slopwave/references/setup.md).
The bootstrap is included in the skill so a standalone folder install works.
It can download a toolchain or reuse a local checkout; no publishing step or
Python package index release is required. It records a specific Git commit at
initial download and does not auto-update on later sessions.

Default consumer layout:

```text
.slopwave/                    ignored local data
  config.json                toolchain, Python/Node paths, artifact locations
  toolchain/                 optional dedicated checkout and dependencies
  sessions/<song>/
    session.json
    brief.json
    revisions/r-.../         score, plan, brief, source/module, WAV, runtime, checks
    events/e-....json         attributed feedback, acceptance, comparisons
  preferences/               exported comparison indexes
```

This is local storage, not a backup service. Keep session artifacts when archiving
the project or exporting a dataset. Nothing is uploaded, trained on, committed,
or published by the recorder. The accepted game module can be copied to the
consumer's ordinary served source directory.

Read [session commands](../.agents/skills/slopwave/references/sessions.md) for
exact operations and label semantics. Read [composition](../.agents/skills/slopwave/references/composition.md)
for the description-to-score workflow and game adapter example.

## What is automatic

`session render` captures a revision and runs structure, actual rendering, and
live onset checks. It also verifies that the exported game factory produces the
same pattern as the REPL source. It publishes a revision only after these checks
pass; it never marks it musically accepted. Later revisions require an explicit
parent. Existing revisions and events are not edited by the commands.

The agent records relevant conversational feedback as part of the skill workflow.
There is no transcript hook or background listener. Quotes, revision references,
and interpretations remain distinct. Attribution comes from the recording agent;
the code cannot prove that a human said the words or listened to the result.

Export includes only decisive comparisons under an unchanged brief and excludes
technical-only comparisons. Acceptance, ties, silence, and agent evaluations do
not become winner/loser pairs. The export references saved artifacts and retains
their hashes; it isn't a self-contained audio bundle. Conflicting feedback and
duplicate observations still need curation before training. Keep related songs
and revisions in the same evaluation split.

## Current limits

Composition is performed by the coding agent using an explicit plan and score;
this revision adds no generation model, reward model, or claim of autonomous
musical quality. Existing transcription and arrangement tools remain available.

Session rendering and game-module export support synth voices. Sampled instruments
still require their resources and a compatible renderer. A WAV is one finite pass;
tail continuity, repeated-loop listening, and game-state transitions need separate
review. The module exports a pattern factory and tempo metadata without starting
a scheduler. It does not implement transport synchronization or quantized state
switching for a consumer. The file-based recorder assumes one writer per session.
