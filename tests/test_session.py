"""Consumer artifact integrity and conservative preference extraction."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from slopwave import session
from slopwave.cli import arrange, mix, export_module
from slopwave.score import load, save

ROOT = Path(__file__).resolve().parents[1]


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.work = Path(self.directory.name)
        self.root = self.work / 'consumer/session'
        session.write_json(self.work / 'brief.json', {'description':'Quiet lighthouse music'})
        session.initialize(self.root, self.work / 'brief.json')
        self.score = mix(arrange(load(ROOT / 'examples/lantern/score.json'), 'synth'))
        save(self.work / 'score.json', self.score)
        self.runtime = patch('slopwave.session.runtime_info', return_value={'test':True})
        self.runtime.start(); self.addCleanup(self.runtime.stop)
        self.render = patch('slopwave.session.run_logged', side_effect=self.fake_render)
        self.render.start(); self.addCleanup(self.render.stop)

    @staticmethod
    def fake_render(command, directory, log):
        Path(log).write_text('Test double, not playback evidence\n')
        if 'render' in command:
            Path(command[-1]).write_bytes(b'test audio')
            session.write_json(str(command[-1]) + '.json', {'test':True})
        if 'playback' in command:
            session.write_json(command[-1], {'test':True})

    def revision(self, parent=None, **kwargs):
        return session.render_revision(self.root, self.work / 'score.json', parent=parent,
                                       note='Test candidate', toolchain=ROOT, **kwargs)['id']

    def test_snapshots_survive_working_edits_and_detect_artifact_changes(self):
        first = self.revision()
        original = (self.root / 'revisions' / first / 'score.json').read_bytes()
        changed = deepcopy(self.score)
        changed['parts']['high'][0][3] /= 2
        save(self.work / 'score.json', changed)
        second = self.revision(first)
        self.assertEqual((self.root / 'revisions' / first / 'score.json').read_bytes(), original)
        self.assertEqual(session.revision_info(self.root, second)['parent'], first)
        (self.root / 'revisions' / first / 'song.wav').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'artifact changed'):
            session.record(self.root, first, kind='acceptance', quote='Good')

    def test_only_explicit_same_brief_nontechnical_comparisons_export(self):
        a, b = self.revision(), None
        b = self.revision(a)
        session.record(self.root, a, kind='feedback', quote='Too busy')
        session.record(self.root, b, kind='acceptance', quote='Ship it')
        for outcome in ('tie','undecided'):
            session.record(self.root, b, kind='comparison', against=a, outcome=outcome, quote='Not sure')
        session.record(self.root, b, kind='comparison', against=a, outcome='preferred',
                       dimension='technical', quote='It loads now')
        result = session.export_preferences(self.root, self.work / 'empty.json')
        self.assertEqual(result['pairs'], 0)
        session.record(self.root, b, kind='comparison', against=a, outcome='preferred',
                       quote='Much better, but the bass disappeared', interpretation='Bass still unresolved')
        session.write_json(self.work / 'new-brief.json', {'description':'Loud boss fight'})
        c = self.revision(b, brief=self.work / 'new-brief.json')
        session.record(self.root, c, kind='comparison', against=b, outcome='preferred', quote='Better for the boss')
        session.export_preferences(self.root, self.work / 'pairs.json')
        pairs = session.read_json(self.work / 'pairs.json')['pairs']
        self.assertEqual(len(pairs), 1)
        self.assertEqual((pairs[0]['preferred'], pairs[0]['rejected']), (b,a))
        self.assertIn('bass disappeared', pairs[0]['evidence']['quote'])
        with self.assertRaises(FileExistsError):
            session.export_preferences(self.root, self.work / 'pairs.json')

    def test_invalid_feedback_and_stale_manifest_are_rejected(self):
        a = self.revision()
        for kwargs in [dict(kind='comparison', against=a, outcome='preferred', quote='Yes'),
                       dict(kind='acceptance', quote=' '),
                       dict(kind='acceptance', against=a, quote='Yes')]:
            with self.assertRaises(ValueError):
                session.record(self.root, a, **kwargs)
        with self.assertRaisesRegex(ValueError, 'Invalid revision'):
            session.record(self.root, '../outside', kind='feedback', quote='No')
        session.record(self.root, a, kind='acceptance', quote='Good enough')
        manifest = self.root / 'revisions' / a / 'revision.json'
        value = session.read_json(manifest); value['note'] = 'rewritten'
        manifest.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, 'changed revision manifest'):
            session.inspect(self.root)

    def test_failed_render_is_not_a_revision_and_parent_is_required(self):
        with patch('slopwave.session.run_logged', side_effect=ValueError('browser failed')):
            with self.assertRaisesRegex(ValueError, 'browser failed'):
                self.revision()
        self.assertEqual(list((self.root / 'revisions').iterdir()), [])
        self.revision()
        with self.assertRaisesRegex(ValueError, 'explicit parent'):
            self.revision()

    def test_context_is_inherited_and_soundfont_module_has_explicit_preload(self):
        session.write_json(self.work / 'plan.json', {'motif':['d4','a4','g4']})
        a = self.revision(plan=self.work / 'plan.json')
        b = self.revision(a)
        self.assertEqual(session.read_json(self.root / 'revisions' / b / 'plan.json'),
                         session.read_json(self.work / 'plan.json'))
        sampled = mix(arrange(load(ROOT / 'examples/lantern/score.json'), 'piano-strings'))
        module = export_module(sampled)
        self.assertIn('export async function preload(S)', module)
        self.assertIn('await Promise.all(preload)', module)

    def test_setup_preserves_existing_consumer_configuration(self):
        script = ROOT / '.agents/skills/slopwave/scripts/setup.py'
        spec = importlib.util.spec_from_file_location('slopwave_setup', script)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        project = self.work / 'game'; home = project / '.slopwave'; home.mkdir(parents=True)
        value = {'toolchain':'chosen-engine', 'sessions':'custom-location'}
        session.write_json(home / 'config.json', value)
        with patch.object(module, 'run', side_effect=AssertionError('Unexpected install')):
            self.assertEqual(module.setup(project, install=True), value)
