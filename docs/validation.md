# Validation

Three different questions must stay separate:

1. **Structure:** Does the exported pattern preserve event counts, pitches, timbre
   assignments, gains, attack times, gates, and repetition? `npm run check` queries
   two complete repetitions through Strudel's pattern engine.
2. **Execution:** Does the browser schedule actual sources on time, and does an
   offline render contain finite, non-silent, unclipped audio of the right length?
   `npm run playback` and `npm run render` record revision-bound JSON reports.
3. **Music:** Is the transcription recognizable and the arrangement convincing?
   These tools do not answer this. Record human listening feedback and coverage.

```sh
python -m pip install -e '.[analysis]'
python -m unittest discover -s tests -p 'test_*.py'
npm run check -- build/mixed.json build/lantern.strudel.js
npm run playback -- build/mixed.json build/lantern.strudel.js build/playback.json
npm run render -- build/mixed.json build/lantern.strudel.js build/lantern.wav
```

The regression suite uses generated signals and explicit toy note sequences.
It retains tests for supported register crossings, octave candidates, holds versus
reattacks, stale corrections, mixing once, and arrangement-specific edits.
No commercial recordings are needed. CI runs the suite and the original example.

Consumer-session regressions cover immutable snapshots, stale artifact detection,
failed-render cleanup, explicit parent revisions, context inheritance, and
conservative preference export. `python tests/consumer_smoke.py` copies the skill
into a temporary consumer, configures an existing runtime, renders two original
synth revisions, and exports one synthetic preference pair. It checks actual
playback and equivalence between the REPL source and game pattern factory. CI
runs this after installing Node dependencies and Chromium. It does not test
musical taste or pretend its synthetic feedback came from a listening user.

Browser tooling serves only the preview, selected score/source, and the pinned
Strudel bundle on localhost. Tests reject external requests. `CHROMIUM_PATH` is
an optional override; normal installations use Playwright's managed Chromium.
Playback checks synthesized oscillators and combined white-noise percussion
starts. Added synth-noise layers are rejected because they cannot be distinguished
from percussion by this check. Sampled profiles must be
checked in a runtime with their instrument resources; the local runner rejects
them rather than claiming to validate unobserved sample playback.

Runtime pins: `@strudel/web` 1.3.0 and its core 1.2.6. The Node checker resolves
`@kabelsalat/web` 0.4.1 to its published ESM entry because its `main` points to a
UMD build. This narrow resolver hook needs Node 22.15+. Dependencies are not patched.

Reports contain source/score hashes and test scope. Offline renders do not test
real-time deadlines; live playback does. No agent listening comparison is claimed.
Raw render bytes may vary with browser/platform floating-point implementations;
score and source regeneration should be identical for identical saved inputs.
