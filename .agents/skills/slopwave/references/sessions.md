# Sessions and revisions

Read `.slopwave/config.json` in the consumer. Use its `python` to run
`-m slopwave`; use its `toolchain` and `node` for rendering. Resolve `sessions`
and `preferences` relative to the directory containing config.json. All paths
below are illustrative consumer paths. Commands are agent tools, not a user UI.

```sh
/engine/.venv/bin/python -m slopwave session init \
  .slopwave/sessions/lighthouse --brief .slopwave/brief.json

# Author/review a score, then arrange and mix using the toolchain's workflows.
/engine/.venv/bin/python -m slopwave session render \
  .slopwave/sessions/lighthouse --score .slopwave/work/mixed.json \
  --plan .slopwave/work/plan.json --note 'Initial theme' \
  --toolchain /engine --node /path/to/node
```

The result returns an ID such as `r-0123456789ab`. A later render requires
`--parent` with the revision actually being edited. The parent brief and plan
are inherited unless `--brief` or `--plan` supplies a replacement. Pass the updated
plan when musical decisions change. Do not infer a parent from file timestamps.

Snapshot publication is atomic after structure, render, and live playback checks
succeed. Failure creates no completed revision. Edits happen in working files;
revision artifacts are read-only by convention and checked by hashes. The recorder
supports a single composing session writer; it is not a multiwriter database.
Runtime file hashes and the saved score/source document the render. Browser/noise
differences can prevent bit-identical audio on a different machine.

Write the user's actual words into a UTF-8 file, then record them. Quote-file
input avoids shell interpolation of conversation text.

```sh
/engine/.venv/bin/python -m slopwave session record \
  .slopwave/sessions/lighthouse --revision r-0123456789ab \
  --quote-file .slopwave/feedback.txt --kind feedback --scope 'bars 9–12'
```

For an unambiguous comparison, use `--kind comparison --against <earlier-id>
--outcome preferred`. `preferred` means the `--revision` wins; `rejected` means
`--against` wins. `tie` and `undecided` record those outcomes without creating
training pairs. `--dimension` can be `musicality`, `mix`, `fit`, `technical`, or
`unspecified`. `--interpretation` stores a separate agent interpretation, including
remaining complaints. `--message-ref` stores an available conversation reference.
Use `--kind acceptance` for approval without an explicit comparison.

```sh
/engine/.venv/bin/python -m slopwave session inspect .slopwave/sessions/lighthouse
/engine/.venv/bin/python -m slopwave session export .slopwave/sessions/lighthouse \
  -o .slopwave/preferences/lighthouse.json
```

Inspect verifies artifact hashes and feedback-to-revision references. Export is
an index referencing the saved session via a relative `artifact_root`, not a
self-contained audio bundle. Preserve/copy those artifacts with it when moving
the dataset. Outputs are created exclusively; use a new filename for a later
export. It includes only attributed decisive comparisons under the same brief,
excluding technical fixes. It does not infer transitive preferences or turn
acceptance into pairwise wins. Human attribution is an agent assertion backed by
the quote, not authenticated by the tool.

Keep contradictory judgments and their context available for dataset curation.
Do not train on the raw export without checking contradictions, repeated votes,
and attribution. Split evaluation by song/session, grouping related sessions when
they derive from the same composition, so neighboring edits cannot leak answers.
