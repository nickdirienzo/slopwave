# slopwave

A research workbench exploring how audio models, musical heuristics, and agent-assisted review can produce editable Strudel arrangements.

Built to be used by a coding agent, with a human listening and steering the
experiments. So far that means transcribing audio, fixing strange notes and
phrasing, trying different instruments, and checking whether the result plays
correctly. It's a research project / proof of concept.

## Try it

Open this repository in your coding agent and ask:

> Render the Lantern example and give me a WAV and the Strudel source.

Or, with your own local audio and arrangement:

> Review this arrangement for octave errors and fragmented held notes.
> Investigate the source, preserve the current version, and save supported fixes.

[AGENTS.md](AGENTS.md) gives the agent its working instructions.
[Setup and commands](docs/workflows.md#setup-and-original-example) cover the tools
it uses, including optional transcription dependencies.

To hear an example immediately, paste the entire
[Lantern arrangement](examples/lantern/lantern.strudel.js) into
[strudel.cc](https://strudel.cc/) and press Play. It's an original eight-bar study
using synth voices; no model or instrument downloads are needed.

## How it works

```text
audio → detections → reviewed score → arrangement → mix → Strudel/audio
```

Models separate stems and suggest notes. Algorithms reconstruct phrases, arrange
parts, mix levels, and schedule playback. The agent investigates questionable
results and saves corrections against the input score. You listen and decide
whether it sounds any good. An authored score can enter the pipeline directly.

Notes and decisions live in an editable [score format](docs/score-format.md).
The [agent workflow](docs/agent-workflow.md) and optional
[song-review skill](.agents/skills/song-review/SKILL.md) describe the review process.
[Research notes](docs/findings.md) capture what the experiments taught us.

Transcription and genre profiles are still rough. Models miss notes and mistake
harmonics for melody; an instrument swap can make a recognizable part sound awful.
[Validation](docs/validation.md) checks structure and playback. Musical quality
still needs listening.

## Related work

[Strudel](https://strudel.cc/) provides the pattern language and audio runtime.
[Basic Pitch](https://github.com/spotify/basic-pitch) provides note inference.
[MIDI-grep](https://github.com/dygy/MIDI-grep) also explores audio-to-Strudel, and
[Decomposer](https://arxiv.org/abs/2607.01849) explores readable Strudel from MIDI.

## License

[AGPL-3.0-or-later](LICENSE) is the proposed code license; the original Lantern
example is [CC0](examples/lantern/LICENSE). See [licensing notes](docs/licensing.md)
for models, instrument samples, and music rights.
