# Compose from a description

Save the consumer's game description, music brief, phase, and constraints in a
JSON object. Keep actual musical scale distinct from gameplay number scale (the
game generator has both). Treat the requested style and context as constraints;
avoid imposing another game's tempo, instrumentation, or taste.

Before expanding notes, save a small `plan.json`: motif and its rhythm, harmony,
phrase/section lengths, groove, roles/registers, instrument articulation, intended
development, and how the last phrase returns to the first. The exact plan shape
is freeform for this prototype. Preserve explicit decisions, not private reasoning.

Use the toolchain's `docs/score-format.md` and `examples/lantern/write_score.py` as
format examples, not a musical template. An authored score can enter at `reviewed`;
this stage permits arrangement and does not mean a human has heard it. Set
`source_kind='authored'` and document the content-hash basis instead of inventing
an audio-source hash. Save the authoring code/inputs alongside the working score.

Develop a recognizable motif across phrases. Parts should share harmonic intent
and leave each other space. Style choices include rhythm, voicings, articulation,
and accompaniment, not just an instrument name. A repeated phrase with an altered
ending can be more useful than independently generated notes in every bar.

Start with one composed loop. Add controlled variation or game-state arrangements
only as needed. Save any random seed and expanded notes; a seed cannot reproduce
an unsaved LLM composition. Keep a shared phase/tempo when designing compatible
layers; don't substitute random note deletion for musical development.

Review both the score and rendered audio when an audio-capable reviewer is
available. Numerical checks cannot establish enjoyment or style fit. Inspect the
return boundary, long releases, competing parts, repeated attacks versus holds,
and changes of energy. Hear several repetitions in the actual runtime before
claiming the loop is comfortable for extended play. Solving a clipping warning
doesn't establish a good mix, and all-in-scale notes don't establish good music.

## Game delivery

`session render` includes `song.mjs`, a synth-only module exporting `bpm`, `beats`,
`cps`, and `createPattern(S)`. It does not start playback or change global tempo.
With dailyincrementalgame's existing `createMusic` adapter:

```js
import { createPattern, cps } from './song.mjs';
const music = await createMusic(A, {
  song: () => ['main', createPattern(music.strudel), cps],
});
music.update();
```

The callback is invoked after `createMusic` returns in the current game adapter.
Check the actual consumer API before copying this snippet. Copy the accepted
module into the game's served assets; keep research artifacts in its session.
Runtime state switching, reverb continuity, and multi-loop listening need their
own integration checks. The current game adapter switches immediately; this
revision does not implement bar-boundary state transitions.
