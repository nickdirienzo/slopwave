# Transferable findings

The private experiments began with a game soundtrack and expanded into vocal
melodies and several instrumental arrangements. The public repository carries
algorithms, synthetic regressions, and the Title Screen Strudel example.
Source recordings and stems stay in the local experiments.

- **Execution can masquerade as rhythm failure.** Whole-song parallel scheduling
  dropped valid attacks. Schedule the current bar, retain gates across boundaries,
  and crop only trailing silence after indexing a partial final bar. Check actual
  Web Audio starts before changing tempo or adding notes.
- **Detections are candidates.** Separation leaks harmonics and can erase quiet
  notes. Fundamental energy, neighboring phrases, envelope attacks, and measured
  dynamics are complementary evidence. Confidence is not loudness.
- **Track voices across registers.** Melody does not become accompaniment merely
  because it crosses a register threshold. Never apply a blanket high-note cutoff.
- **Articulation is part of transcription.** A held note split into model fragments
  can sound like extra syllables. True repeated attacks can look similar. Compare
  the envelope and phrase context, then consider synth release as well as the gate.
- **Phrases improve coherence but can preserve mistakes.** Sequence decoding uses
  harmonic evidence, continuity, soft tonal vocabulary and repeated acoustic
  windows. It must retain supported rests/leaps, mark inference, and allow scoped
  exceptions. Lower flag counts do not measure musical quality.
- **Instrument changes can require compositional changes.** A voice that works on
  a synth may clash on a banjo because of ringing overlap or inappropriate voicing.
  Preserve the reviewed source and record arrangement-specific simplification.
- **Energy is not note count.** Dense accompaniment can mask a melody; sparse
  detections can miss sustained backing. Use source activity and musical role,
  rather than filling every rest or introducing a fixed genre template.
- **Mix once.** Budget simultaneous chord gain, reduce backing under the melody,
  and preserve quietness in near-silent stems. Repeated compression during rebuilds
  silently changes the arrangement.
- **A successful check has a limited meaning.** Syntax and event checks do not
  establish sound output. Actual starts do not establish good phrasing. Listening
  acceptance does not establish exact source accuracy.
- **Evidence and decisions have different lifetimes.** Keep raw detections, cached
  features, corrections, arrangements and output hashes distinct. Reject stale
  corrections. Record ambiguous findings instead of changing notes until every
  warning disappears.

Known engineering lessons include literal-string handling in Strudel's transpiler,
preloading each sampled pitch, checking buffer starts as well as oscillators, and
keeping metering bounded. A test that creates one meter per note can cause the
performance failure it is trying to diagnose. The local synth example avoids
remote sample behavior; it does not replace sampled-profile validation.
