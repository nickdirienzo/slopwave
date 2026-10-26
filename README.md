# slopwave

I asked Codex if it could turn the Ribbit King soundtrack into
[Strudel](https://strudel.cc/). It got surprisingly close.

After a few hours of listening, we fixed timing, octave errors, and held notes
that had become a bunch of beeps. Eventually we tried restyling those
transcriptions with piano and strings, banjo, and a kazoo.

`slopwave` is the code that came out of that. It's a research prototype meant to be
driven by a coding agent. Still figuring out how far this can go.

## Try the Ribbit King example

[Title Screen: Strudel source](examples/ribbit-king/title-screen.strudel.js) ·
[Original track](https://www.youtube.com/watch?v=oRnpBqkoI6U&t=215s)

Copy the whole source file into [strudel.cc](https://strudel.cc/) and press Play.
It loops about 100 seconds of the title music using synth voices. This version
includes the timing, phrasing, and octave fixes from those listening sessions.

## Work with an agent

Open the repo in your coding agent, give it a recording, and ask it to make a
Strudel arrangement. Listen to what comes back. Tell it where the notes are
wrong, where something should be held, or where the mix is fighting itself.

[AGENTS.md](AGENTS.md) gives the agent context.
[Setup and commands](docs/workflows.md#setup-and-original-example) cover the tools
it uses. The [Lantern example](examples/lantern/lantern.strudel.js) is a small
original tune for checking setup and rendering.

## What's happening

```text
audio → detections → reviewed score → arrangement → mix → Strudel/audio
```

Models separate stems and suggest notes. Algorithms help reconstruct phrases,
arrange parts, and mix levels. The coding agent looks at the evidence and makes
edits. Those decisions get saved so the next rebuild keeps the fixes.

There's a [musical IR](docs/score-format.md) in here now. We also ended up with a
[song-review skill](.agents/skills/song-review/SKILL.md), because reviewing a whole
song for weird notes turned out to be useful. More detail in the
[agent workflow](docs/agent-workflow.md) and [research notes](docs/findings.md).

The [checks](docs/validation.md) can tell us whether notes actually played.
They can't tell us whether the banjo arrangement sounds terrible. Listening is
still a pretty significant part of this for now.

## Related work

[Strudel](https://strudel.cc/) provides the pattern language and audio runtime.
[Basic Pitch](https://github.com/spotify/basic-pitch) provides note inference.
[MIDI-grep](https://github.com/dygy/MIDI-grep) also explores audio-to-Strudel, and
[Decomposer](https://arxiv.org/abs/2607.01849) explores readable Strudel from MIDI.

## License

[AGPL-3.0-or-later](LICENSE) for the code. [CC0](examples/lantern/LICENSE) for
Lantern. The original Ribbit King music isn't covered by either license.
[Licensing notes](docs/licensing.md) have the dependency and instrument details.
