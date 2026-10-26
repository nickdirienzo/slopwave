"""Real synth rendering from a consumer cwd, including module equivalence."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile

from slopwave.cli import arrange, mix
from slopwave.score import digest, promote, save

engine = Path(__file__).resolve().parents[1]
node = os.environ.get('SLOPWAVE_TEST_NODE', 'node')
with tempfile.TemporaryDirectory(prefix='slopwave-consumer-') as work:
    project = Path(work)
    # Install only the skill folder in the consumer, with no sibling repo docs.
    skill = project / '.agents/skills/slopwave'
    shutil.copytree(engine / '.agents/skills/slopwave', skill)
    def command(*args):
        result = subprocess.run([str(v) for v in args], cwd=project, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        return result.stdout
    command(sys.executable, skill / 'scripts/setup.py', '--project', project,
            '--toolchain', engine, '--python', sys.executable, '--node', node)
    home = project / '.slopwave'
    brief = home / 'brief.json'; brief.write_text(json.dumps({'description':'A short original synth pulse'}))
    plan = home / 'plan.json'; plan.write_text(json.dumps({'motif':['c4','e4'], 'form':'one bar test'}))
    parts = dict(low=[[0,2,'c3',.4]],middle=[],high=[[0,.5,'c4',.4],[2,.5,'e4',.4]],
                 kick=[[0,.12,36,.4]],snare=[[1,.12,36,.4]],hat=[[2.5,.12,36,.3]])
    score = promote(dict(bpm=120,beats=4,source_audio_sha256=digest(parts),parts=parts),
                    title='Consumer test',source_id='original:consumer-test',source_kind='authored',stage='reviewed')
    save(home / 'mixed.json', mix(arrange(score, 'synth')))
    def cli(*args):
        return json.loads(command(sys.executable, '-m', 'slopwave', *args))
    session = home / 'sessions/test'
    cli('session','init',session,'--brief',brief)
    revision = cli('session','render',session,'--score',home/'mixed.json','--plan',plan,
                   '--note','Original smoke fixture','--toolchain',engine,'--node',node)
    report = json.loads((session/'revisions'/revision['id']/'playback.json').read_text())
    assert report['expected_attacks'] == 6 and not report['missing'] and not report['late']
    candidate = json.loads((home / 'mixed.json').read_text())
    candidate['parts']['high'][1][2] = 'g4'
    save(home / 'mixed.json', candidate)
    second = cli('session','render',session,'--score',home/'mixed.json','--parent',revision['id'],
                 '--note','Alternate ending','--toolchain',engine,'--node',node)
    quote = home / 'feedback.txt'; quote.write_text('Synthetic test feedback: second is preferred.')
    cli('session','record',session,'--revision',second['id'],'--against',revision['id'],
        '--kind','comparison','--outcome','preferred','--quote-file',quote)
    export = cli('session','export',session,'-o',home/'preferences/test.json')
    assert export['pairs'] == 1
    assert len(cli('session','inspect',session)['revisions']) == 2
    print(json.dumps({'consumer_smoke':True,'events_per_revision':6,'revisions':2,
                      'preference_pairs':1,'module_equivalent':True,'external_requests':report['external_requests']}))
