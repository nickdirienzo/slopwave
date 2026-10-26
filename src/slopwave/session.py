"""Consumer-owned revision snapshots and attributed listening feedback.

This records evidence; it cannot establish that a quote came from a human or that
the human listened. The recording agent is responsible for that attribution.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from uuid import uuid4

from .score import digest, load


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    with Path(path).open('x') as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + '\n')


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def brief_value(path):
    value = read_json(path)
    if not isinstance(value, dict) or not value:
        raise ValueError('Brief must be a nonempty JSON object')
    digest(value)  # Reject nonfinite JSON before writing anything.
    return value


def initialize(root, brief):
    root = Path(root).resolve()
    value = brief_value(brief)
    root.mkdir(parents=True, exist_ok=False)
    (root / 'revisions').mkdir()
    (root / 'events').mkdir()
    write_json(root / 'brief.json', value)
    manifest = dict(schema_version=1, id='s-' + uuid4().hex, created_at=now(),
                    brief_sha256=file_hash(root / 'brief.json'))
    write_json(root / 'session.json', manifest)
    return manifest


def session_info(root):
    root = Path(root).resolve()
    value = read_json(root / 'session.json')
    if value.get('schema_version') != 1:
        raise ValueError('Unsupported session version')
    if file_hash(root / 'brief.json') != value['brief_sha256']:
        raise ValueError('Session brief changed; pass a new brief to a new revision')
    return value


def revision_info(root, revision):
    session = session_info(root)
    if not re.fullmatch(r'r-[0-9a-f]{12}', revision):
        raise ValueError('Invalid revision ID')
    directory = Path(root) / 'revisions' / revision
    value = read_json(directory / 'revision.json')
    if value.get('id') != revision or value.get('session') != session['id']:
        raise ValueError('Revision belongs to a different session')
    for name, sha in value['artifacts'].items():
        if Path(name).name != name or (directory / name).is_symlink():
            raise ValueError('Invalid artifact path')
        if file_hash(directory / name) != sha:
            raise ValueError(f'Revision artifact changed: {revision}/{name}')
    return value


def run_logged(command, directory, log):
    result = subprocess.run([str(x) for x in command], cwd=directory,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    Path(log).write_text(result.stdout)
    if result.returncode:
        raise ValueError(f'Command failed ({result.returncode}): {command[0]}\n{result.stdout[-4000:]}')


def runtime_info(toolchain, node):
    toolchain = Path(toolchain).resolve()
    git = subprocess.run(['git', '-C', str(toolchain), 'rev-parse', 'HEAD'],
                         capture_output=True, text=True)
    paths = [*toolchain.glob('src/slopwave/*.py'), *toolchain.glob('src/slopwave/*.json'),
             *toolchain.glob('tools/*'), toolchain / 'package-lock.json', toolchain / 'pyproject.toml']
    return dict(python=sys.version, node=subprocess.check_output([node, '--version'], text=True).strip(),
                git_commit=git.stdout.strip() if git.returncode == 0 else None,
                files={str(p.relative_to(toolchain)): file_hash(p) for p in sorted(paths) if p.is_file()})


def render_revision(root, score_path, *, parent=None, brief=None, plan=None,
                    note, toolchain=None, node='node'):
    from .cli import export, export_module
    root = Path(root).resolve()
    session = session_info(root)
    if parent:
        revision_info(root, parent)
    elif any((root / 'revisions').glob('r-*')):
        raise ValueError('Later revisions require an explicit parent')
    score = load(score_path)
    from .samples import snapshot_samples
    score = snapshot_samples(score, Path(score_path).resolve().parent)
    if not note.strip():
        raise ValueError('Describe the revision')
    source = export(score)  # Also enforces the mixed stage.
    inherited = root / 'revisions' / parent if parent else root
    context = brief_value(brief or inherited / 'brief.json')
    if plan:
        composition = brief_value(plan)
    elif parent and (inherited / 'plan.json').exists():
        composition = read_json(inherited / 'plan.json')
    else:
        composition = None
    toolchain = Path(toolchain or Path(__file__).resolve().parents[2]).resolve()
    if not (toolchain / 'tools/audio.mjs').is_file():
        raise ValueError('Pass --toolchain pointing to the installed slopwave checkout')
    runtime = runtime_info(toolchain, node)
    revision = 'r-' + uuid4().hex[:12]
    destination = root / 'revisions' / revision
    # Publish a revision only when the snapshot, render, and playback checks finish.
    with tempfile.TemporaryDirectory(prefix='.pending-', dir=root / 'revisions') as temporary:
        work = Path(temporary)
        write_json(work / 'score.json', score)
        write_json(work / 'brief.json', context)
        if composition is not None:
            write_json(work / 'plan.json', composition)
        (work / 'song.strudel.js').write_text(source)
        (work / 'song.mjs').write_text(export_module(score))
        write_json(work / 'runtime.json', runtime)
        args = [work / 'score.json', work / 'song.strudel.js']
        run_logged([node, toolchain / 'tools/check.mjs', *args, work / 'song.mjs'], work, work / 'structure.log')
        run_logged([node, toolchain / 'tools/audio.mjs', 'render', *args, work / 'song.wav'],
                   work, work / 'render.log')
        run_logged([node, toolchain / 'tools/audio.mjs', 'playback', *args, work / 'playback.json'],
                   work, work / 'playback.log')
        value = dict(schema_version=1, id=revision, session=session['id'], parent=parent,
                     created_at=now(), note=note, brief_digest=digest(context),
                     listening_review='pending', artifacts={p.name: file_hash(p) for p in sorted(work.iterdir())})
        write_json(work / 'revision.json', value)
        os.rename(work, destination)
    return value


def record(root, revision, *, kind, quote, against=None, outcome=None,
           dimension='unspecified', scope=None, interpretation=None, message_ref=None):
    root = Path(root).resolve()
    target = revision_info(root, revision)
    if not quote.strip():
        raise ValueError('Record the actual human feedback; an empty quote is not evidence')
    if kind not in ('feedback', 'acceptance', 'comparison'):
        raise ValueError('Unknown feedback kind')
    if kind == 'comparison':
        if not against or against == revision or outcome not in ('preferred', 'rejected', 'tie', 'undecided'):
            raise ValueError('Comparison requires two distinct revisions and an explicit outcome')
        revision_info(root, against)
    elif against is not None or outcome is not None:
        raise ValueError('Only comparisons have an opponent or outcome')
    if dimension not in ('musicality', 'mix', 'fit', 'technical', 'unspecified'):
        raise ValueError('Unknown comparison dimension')
    value = dict(schema_version=1, id='e-' + uuid4().hex, session=target['session'],
                 created_at=now(), kind=kind, revision=revision, against=against, outcome=outcome,
                 quote=quote, attributed_to='human', recorded_by='agent', dimension=dimension,
                 scope=scope, interpretation=interpretation, message_ref=message_ref)
    value['revision_manifest_sha256'] = file_hash(root / 'revisions' / revision / 'revision.json')
    if against:
        value['against_manifest_sha256'] = file_hash(root / 'revisions' / against / 'revision.json')
    write_json(root / 'events' / (value['id'] + '.json'), value)
    return value


def inspect(root):
    root = Path(root).resolve()
    session = session_info(root)
    revisions = [revision_info(root, p.name) for p in sorted((root / 'revisions').glob('r-*'))]
    events = []
    for path in (root / 'events').glob('e-*.json'):
        event = read_json(path)
        if event.get('schema_version') != 1 or event.get('session') != session['id']:
            raise ValueError('Invalid feedback event')
        for key, hash_key in [('revision', 'revision_manifest_sha256'), ('against', 'against_manifest_sha256')]:
            if event.get(key):
                revision_info(root, event[key])
                if file_hash(root / 'revisions' / event[key] / 'revision.json') != event[hash_key]:
                    raise ValueError('Feedback references a changed revision manifest')
        events.append(event)
    return dict(session=session, revisions=sorted(revisions, key=lambda v: v['created_at']),
                events=sorted(events, key=lambda v: v['created_at']))


def export_preferences(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    data = inspect(root)
    revisions = {v['id']: v for v in data['revisions']}
    pairs = []
    for event in data['events']:
        if event['kind'] != 'comparison' or event['outcome'] not in ('preferred', 'rejected'):
            continue
        if event['dimension'] == 'technical':
            continue
        a, b = event['revision'], event['against']
        if revisions[a]['brief_digest'] != revisions[b]['brief_digest']:
            continue
        winner, loser = (a, b) if event['outcome'] == 'preferred' else (b, a)
        pairs.append(dict(preferred=winner, rejected=loser, evidence=event,
                          brief=read_json(root / 'revisions' / winner / 'brief.json'),
                          revisions={r: revisions[r] for r in (winner, loser)}))
    if output.is_relative_to(root):
        raise ValueError('Export outside the session to preserve its artifacts')
    output.parent.mkdir(parents=True, exist_ok=True)
    value = dict(schema_version=1, session=data['session']['id'],
                 artifact_root=os.path.relpath(root, output.parent), pairs=pairs,
                 policy='Explicit attributed comparisons, unchanged brief, nontechnical; no transitive preferences.')
    write_json(output, value)
    return dict(pairs=len(pairs), output=str(output))


def add_parser(subs):
    parser = subs.add_parser('session', help='Consumer-owned music revisions and feedback')
    commands = parser.add_subparsers(dest='session_command', required=True)
    init = commands.add_parser('init'); init.add_argument('directory', type=Path)
    init.add_argument('--brief', type=Path, required=True)
    render = commands.add_parser('render'); render.add_argument('directory', type=Path)
    render.add_argument('--score', type=Path, required=True)
    render.add_argument('--parent'); render.add_argument('--brief', type=Path)
    render.add_argument('--plan', type=Path); render.add_argument('--note', required=True)
    render.add_argument('--toolchain', type=Path); render.add_argument('--node', default='node')
    feedback = commands.add_parser('record'); feedback.add_argument('directory', type=Path)
    feedback.add_argument('--revision', required=True)
    feedback.add_argument('--kind', choices=['feedback','acceptance','comparison'], default='feedback')
    feedback.add_argument('--quote-file', type=Path, required=True)
    feedback.add_argument('--against'); feedback.add_argument('--outcome', choices=['preferred','rejected','tie','undecided'])
    feedback.add_argument('--dimension', choices=['musicality','mix','fit','technical','unspecified'], default='unspecified')
    feedback.add_argument('--scope'); feedback.add_argument('--interpretation'); feedback.add_argument('--message-ref')
    view = commands.add_parser('inspect'); view.add_argument('directory', type=Path)
    export = commands.add_parser('export'); export.add_argument('directory', type=Path)
    export.add_argument('-o', '--output', type=Path, required=True)


def dispatch(args):
    if args.session_command == 'init':
        return initialize(args.directory, args.brief)
    if args.session_command == 'render':
        return render_revision(args.directory, args.score, parent=args.parent, brief=args.brief,
                               plan=args.plan, note=args.note, toolchain=args.toolchain, node=args.node)
    if args.session_command == 'record':
        return record(args.directory, args.revision, kind=args.kind, quote=args.quote_file.read_text(),
                      against=args.against, outcome=args.outcome, dimension=args.dimension,
                      scope=args.scope, interpretation=args.interpretation, message_ref=args.message_ref)
    if args.session_command == 'inspect':
        return inspect(args.directory)
    return export_preferences(args.directory, args.output)
