# Sound design and portable samples

Voice settings are explicit numeric controls. Export rejects unknown controls and
non-finite/non-numeric values instead of silently dropping them. The supported
list lives in `src/slopwave/strudel.py:VOICE_CONTROLS`; it includes filter and pitch
envelopes, FM, distortion/output level, bit reduction, phaser, tremolo, delay and
reverb. Native Strudel processing order applies, regardless of property order.
Structural checks verify the emitted control values as well as notes and timing.

```json
{"sound":"sawtooth","fm":0.5,"fmh":1.5,"lpf":1500,"lpenv":2,
 "lpdecay":0.12,"distort":0.6,"distortvol":0.25,"release":0.1}
```

Synth sounds include sine, triangle, sawtooth, square, white, pink and brown noise.
Noise playback checks verify a combined buffer-start class; they do not identify
individual noise parts or colors. Custom sample starts retain their sound name.
Checks establish execution, not a verdict on the music or effects' perceptual quality.

For a custom unpitched one-shot, declare its resource and use its name as a voice:

```json
{
  "sample_buffers": {
    "metal_hit": {"url":"samples/metal.wav","seconds":0.3,"license":"original recording"}
  },
  "voices": {"snare":{"sound":"metal_hit","hpf":500,"distort":0.2}}
}
```

`session render` resolves file paths relative to the input score, downloads declared
HTTPS resources, or accepts base64 audio data URLs. It freezes each resource into
an embedded data URL with a SHA-256 and original location. An optional `sha256` on
the input definition pins the expected bytes. Each resource is limited to 16 MiB.
Keep ownership/license information with the definition. Browser decoding must
succeed before playback. Saved score, REPL source and module are self-contained;
no sample server is needed at playback time. These are unpitched one-shots: the
note field does not transpose them, and `seconds` caps the sample's played duration.
For standalone exports, embed resources first with `snapshot_samples(score, directory)`
or supply data URLs. A relative file path cannot be fetched by strudel.cc.

Modules export `async preload(S)` in addition to `createPattern(S)`, `bpm`, `beats`
and `cps`. After initializing Strudel, await `song.preload(S)` before creating or
playing the pattern. The application still owns transport and tempo. Soundfont
REPL/module exports retain explicit network preloading. General MIDI soundfont
presets are not bundled in the pinned local browser runtime; session renders
require explicit `sample_buffers` instead. The sample path does not add arbitrary
JavaScript instrument definitions or arbitrary effect graphs to the score format.

The player awaits audio initialization on both mouse and keyboard activation before offline rendering
changes contexts. This prevents a race that unloaded worklets and produced silent
WAVs for distortion/crush voices. Checks catch Strudel's logged per-note failures,
worklet warnings and processor errors, and distinguish silent output from clipping.

Long eligible arrangements render in bounded segments with gate/release pre-roll.
Samples, soundfonts and global/time-dependent effects use an uninterrupted render.
Noise generation is stochastic, so rendering is not guaranteed bit-identical.
WAVs remain finite passes; tail/seam musical quality needs listening review.
