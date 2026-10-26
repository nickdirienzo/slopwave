# Licensing inventory

The workbench uses **AGPL-3.0-or-later** for its code, documentation,
and optional review skill. The exact license is included at the repository root.
Strudel's integrated runtime uses that license; its maintainers document source
availability and compatible licensing requirements for integrations:
https://strudel.cc/technical-manual/project-start/

This is a release inventory and recommendation, not a determination that every
possible input or output is cleared. Dependencies retain their own notices.
Installing dependencies does not put their source or model files into this Git repo.

| Component | Upstream terms / obligations | Included here |
| --- | --- | --- |
| Strudel core/mini/web and superdough | AGPL-3.0-or-later; retain notices and provide corresponding source for distributed integrations | Exact npm pins/lock; installed code ignored |
| Playwright | Apache-2.0; preserve license/NOTICE when redistributing | Dev dependency, no browser binary committed |
| NumPy / SciPy | BSD licenses; retain notices | Dependency pins |
| jsonschema | MIT; retain notice | Dependency pin |
| librosa | ISC; retain notice | Optional analysis dependency |
| SoundFile | BSD-3-Clause wrapper; bundled libsndfile has separate LGPL terms | Optional dependency; no bundled wheel in repo |
| ONNX Runtime | MIT | Optional inference dependency |
| Basic Pitch 0.4.0 | Apache-2.0 repository; retain Spotify NOTICE and third-party notices on redistribution | Optional package; no checkpoint/audio dataset committed |
| Demucs 4.0.1 | MIT repository | Optional package; no weights committed |
| PyTorch / torchaudio | BSD-style project licenses plus third-party notices | Optional separation dependencies |
| VCSL percussion | CC0-1.0 | URLs in optional kazoo profile; no audio committed |
| FluidR3-named soundfont presets | Exact loaded sample distribution requires attribution/license verification before bundling or shipping sampled examples | Identifiers in research profiles only; no soundfont files committed |
| Ribbit King Title Screen | Underlying music is outside the repository code license | Strudel cover source; no recording or render |
| Lantern score and composition | CC0-1.0 dedication, to extent rights exist; newly authored with agent assistance | Explicit notes and generated synth-only example |

Primary sources:
- [Strudel repository](https://codeberg.org/uzu/strudel)
- [Basic Pitch license](https://github.com/spotify/basic-pitch/blob/main/LICENSE) and
  [NOTICE](https://github.com/spotify/basic-pitch/blob/main/NOTICE)
- [Demucs license statement](https://github.com/facebookresearch/demucs#license)
- [VCSL license](https://github.com/sgossner/VCSL/blob/master/LICENSE)
- [SoundFile license](https://github.com/bastibe/python-soundfile/blob/master/LICENSE)
- [libsndfile licensing](https://libsndfile.github.io/libsndfile/)

Model checkpoints must be assessed at their upstream release, independently of
training dataset or song rights. The adapters record model/state hashes when run.
No claim is made that a model license clears its training material or downstream
music. Before redistributing checkpoints, archive the applicable release terms;
this candidate delegates optional downloads to the upstream packages.

The soundfont distinction is deliberate: a loader's code license is not necessarily
its samples' license. For example, the MIDI.js soundfont project's README identifies
its Fluid distribution as CC-BY-3.0 despite the repository's MIT code license:
https://github.com/gleitz/midi-js-soundfonts#soundfonts-available
That is not proof of the terms of every similarly named WebAudioFont preset.
The verified quickstart uses oscillators and avoids this unresolved asset chain.

The workbench license does not license imported compositions, recordings, recovered
MIDI, correction files containing protected music, or cover renders. Composition
and recording are separate works:
https://www.copyright.gov/circs/circ56a.pdf
Linking to an original recording does not itself grant redistribution rights.
The Ribbit King Title Screen example is an unofficial synth cover, included as
Strudel source. Its underlying music is not licensed under the workbench's AGPL
or Lantern's CC0 dedication. The example links to the original track; the repo
does not include its source recording, stems, or rendered audio.
