# Consumer setup

Run `scripts/setup.py` relative to this installed skill's directory. It is a
standard-library bootstrap. Select Python 3.10–3.12 and Node 22.15+ (24 works).
With `--install`, it downloads slopwave, core Python dependencies, the pinned npm
dependencies, and Chromium. No transcription models are installed by default.

```sh
python3 /path/to/installed/slopwave/scripts/setup.py \
  --project /path/to/game --install
```

An initial download checks out `main` detached and records its commit. `--ref`
selects another published commit/tag. Existing configurations are returned
unchanged; setup does not automatically update tools or replace project choices.

For development, reuse a local checkout:

```sh
python3 /path/to/installed/slopwave/scripts/setup.py \
  --project /path/to/game --toolchain /path/to/slopwave --install
```

Or omit `--install` and supply `--python /path/to/slopwave/.venv/bin/python` to
reuse an already installed runtime. `--node` and `--npm` accept executable paths.
The script verifies that Python imports the selected checkout. It writes
`.slopwave/config.json` and a local `.gitignore` so renders, preferences, and
machine-specific installation paths stay untracked. No consumer instructions or
music files are overwritten. On Linux, missing Chromium system libraries may
need Playwright's documented OS dependency setup.

When asked to integrate the skill with a consumer's generation workflow, add a
short pointer to its existing agent instructions: use slopwave for music, read
`.slopwave/config.json`, and retain listening feedback in the consumer's sessions.
Preserve the rest of that workflow. Do not install a competing game audio engine.

Verify setup with one small authored synth score through `session render`, from
the consumer directory. Then report the skill location, toolchain, and artifact
directory. Installation is not complete proof of browser playback until that
smoke test succeeds. A skill installed by itself must not depend on sibling
skill folders or on the installer's source repository still being present.
