"""Set up slopwave tools and local storage for a consumer project.

Standard-library bootstrap, usable after installing just this skill folder.
With --install, downloads the lightweight Python/Node runtime and Chromium.
Model extras are deliberately a separate, task-dependent installation.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


REPOSITORY = 'https://github.com/nickdirienzo/slopwave.git'


def executable(value):
    found = shutil.which(str(value))
    if not found:
        raise ValueError(f'Executable not found: {value}')
    return str(Path(found).absolute())  # Keep venv interpreter symlinks intact.


def run(argv, cwd, env=None):
    subprocess.run([str(v) for v in argv], cwd=cwd, env=env, check=True)


def setup(project, *, toolchain=None, install=False, python=sys.executable,
          node='node', npm='npm', ref='main'):
    project = Path(project).resolve(strict=True)
    home = project / '.slopwave'
    if not home.resolve().is_relative_to(project):
        raise ValueError('Consumer storage must remain inside the project')
    config = home / 'config.json'
    if config.exists():
        # Do not silently update an engine or replace a consumer's configuration.
        return json.loads(config.read_text())
    node = executable(node)
    version = subprocess.check_output([node, '--version'], text=True).strip().lstrip('v')
    if tuple(map(int, version.split('.')[:2])) < (22, 15):
        raise ValueError('Node 22.15 or newer is required')
    python = executable(python)
    home.mkdir(exist_ok=True)
    ignore = home / '.gitignore'
    if not ignore.exists():
        ignore.write_text('# Local music work, feedback, renders, and installed tools.\n*\n')
    engine = Path(toolchain).resolve() if toolchain else home / 'toolchain'
    if not engine.exists():
        if toolchain or not install:
            raise ValueError('Provide an existing --toolchain, or use --install to download one')
        run(['git', 'clone', '--', REPOSITORY, engine], project)
        run(['git', 'checkout', '--detach', ref], engine)
    if not (engine / 'src/slopwave/session.py').is_file():
        raise ValueError('Toolchain lacks consumer sessions; use a revision with the slopwave skill')
    if install:
        npm = executable(npm)
        # npm's node shebang must resolve to the selected executable, not a shim.
        env = dict(os.environ, PATH=str(Path(node).parent) + os.pathsep + os.environ.get('PATH', ''))
        runtime_python = engine / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        if not runtime_python.exists():
            run([python, '-m', 'venv', engine / '.venv'], engine)
        run([runtime_python, '-m', 'pip', 'install', '-e', '.'], engine)
        run([npm, 'ci'], engine, env)
        run([node, engine / 'node_modules/playwright/cli.js', 'install', 'chromium'], engine, env)
    else:
        runtime_python = Path(python)
    # Verify Python resolves this engine, not an unrelated installed slopwave.
    probe = subprocess.check_output([str(runtime_python), '-c',
        'import pathlib, slopwave.session; print(pathlib.Path(slopwave.session.__file__).resolve())'], text=True).strip()
    if Path(probe) != (engine / 'src/slopwave/session.py').resolve():
        raise ValueError('Python imports a different slopwave checkout; install this engine or select its Python')
    run([node, '-e', "import('playwright').then(()=>import('./tools/runtime.mjs'))"], engine)
    head = subprocess.run(['git', '-C', str(engine), 'rev-parse', 'HEAD'], text=True, capture_output=True)
    (home / 'sessions').mkdir(exist_ok=True)
    (home / 'preferences').mkdir(exist_ok=True)
    value = dict(schema_version=1, toolchain=str(engine), python=str(runtime_python), node=node,
                 installed_commit=head.stdout.strip() if head.returncode == 0 else None,
                 sessions='sessions', preferences='preferences')
    with config.open('x') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--toolchain', type=Path)
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--node', default='node'); parser.add_argument('--npm', default='npm')
    parser.add_argument('--ref', default='main', help='Initial checkout ref; existing installations are never updated')
    args = parser.parse_args()
    try:
        value = setup(**vars(args))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.error(str(error))
    print(json.dumps(value, indent=2))


if __name__ == '__main__':
    main()
