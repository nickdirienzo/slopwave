# slopwave

A research workbench exploring how audio models, musical heuristics, and agent-assisted review can produce editable Strudel arrangements.

The code preserves experiments in phrase reconstruction, evidence-backed corrections,
instrument arrangements, mixing, and playback verification. Results are musical
hypotheses. This is not an automatic composer or a claim of accurate transcription.

## Work with a coding agent

Open this repository in your coding agent and ask it to carry out a musical task:

> Render the original Lantern example and give me a WAV and the Strudel source.

> Review this arrangement for octave errors and fragmented held notes. Preserve
> the current version, investigate source evidence, and save supported corrections.

The agent uses [AGENTS.md](AGENTS.md), the [task workflow](docs/agent-workflow.md),
and the optional song-review skill. The scripts below are its execution tools;
there is no separate hosted agent service. Human listening guides the iterations.

## Reproduce the original example

The eight-bar **Lantern** study was written for this repository. It uses synthesized
voices, has no source recording, and needs no model weights or instrument downloads.
[Score](examples/lantern/score.json) · [Strudel arrangement](examples/lantern/lantern.strudel.js)

Paste the entire Strudel file into [strudel.cc](https://strudel.cc/) and press Play,
or use the pinned local renderer below. Share files or rendered audio rather than
large URLs containing the entire program.

Python 3.10–3.12 and Node.js 22.15+ are required. From this directory:

```sh
python3 -m venv .venv
# Windows: .venv\Scripts\activate
. .venv/bin/activate
python -m pip install -e .
npm ci
npx playwright install chromium

slopwave validate examples/lantern/score.json
slopwave arrange examples/lantern/score.json --profile synth -o build/arranged.json
slopwave mix build/arranged.json -o build/mixed.json
slopwave export build/mixed.json -o build/lantern.strudel.js
npm run check -- build/mixed.json build/lantern.strudel.js
npm run render -- build/mixed.json build/lantern.strudel.js build/lantern.wav
```

Installation downloads dependencies and Chromium. Rendering this example afterward
uses local files only. On Linux, `npx playwright install --with-deps chromium` also
installs required system libraries. WAV output is a finite pass; the Strudel pattern
loops. `npm run serve` opens a local preview at the URL printed in the terminal.

## Pipeline

```text
local audio → model detections → reviewed score → arrangement → mix → Strudel/audio
                                      ↑
                              authored score
```

The [versioned score format](docs/score-format.md) retains source identity, explicit
voice roles, beat coordinates, and a history of operations. Corrections are saved
against both the source and the exact input score. Arrangement changes are separate
from repairs to a transcription. Mixing is an explicit, single stage.

- **Models:** optional Demucs stem separation and Basic Pitch note candidates.
- **Algorithms:** acoustic measurements, phrase decoding, arrangement rules, gain
  budgets, and event scheduling. Saved-input replay is testable; model inference
  and floating-point audio are not promised bit-identical across environments.
- **Agent judgment:** interpreting evidence and proposing scoped corrections. No
  hosted LLM or API key is required by the command-line tools.
- **Human listening:** recognizability, phrasing, timbre, and whether an arrangement
  is enjoyable. Passing a playback check cannot answer those questions.

See [workflows](docs/workflows.md), [transferable findings](docs/findings.md), and
[validation](docs/validation.md). The optional [song-review skill](.agents/skills/song-review/SKILL.md)
guides evidence-based investigation without requiring private tracks.

## Limits

The public fixture demonstrates reproduction and playback, not transcription
accuracy on a benchmark. Separated stems can leak harmonics and erase notes. Vocal
phrase decoding is an inference. Genre profiles are experiments, not arbitrary
style transfer. The current IR stores events; it does not discover a reusable
composition grammar. Instrument-sample profiles require external resources and
have weaker reproducibility guarantees than the synth-only example.

## Related work

[MIDI-grep](https://github.com/dygy/MIDI-grep) already combines audio/stem
transcription with Strudel output. [Basic Pitch](https://github.com/spotify/basic-pitch)
provides note inference. [Decomposer](https://arxiv.org/abs/2607.01849) investigates
recovering readable Strudel programs from MIDI. [Strudel](https://strudel.cc/)
provides the pattern language and sound runtime. This workbench concentrates on
reviewable evidence, corrections, arrangement experiments, and execution checks;
no novelty claim is made for the overall audio-to-code pipeline.

## License and release status

Local release candidate; nothing has been published. AGPL-3.0-or-later is the
proposed code license, included in [LICENSE](LICENSE), consistent with the Strudel
integration. [Licensing notes](docs/licensing.md) distinguish code, models,
instruments, recordings, and compositions. No commercial-song data or original
experiment history is included.
