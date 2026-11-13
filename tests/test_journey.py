import concurrent.futures
import copy
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from spend_outcomes import mcp
from spend_outcomes.__main__ import share
from spend_outcomes.core import digest, encoded
from spend_outcomes.device import render_device
from test_public_v1 import write_session


def apply(name, args):
    plan = mcp.execute(name, args)
    return mcp.execute(name, {**args, 'apply': True, 'expected_plan_sha256': plan['plan_sha256']})


class Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.ids = [], []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.ids.extend(value for key, value in attrs if key == 'id')


class Journey(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='cherry journey ')
        self.root = Path(self.temporary.name)
        self.demo = apply('cherry_meter_demo', {'root': str(self.root / 'demo')})
        self.config = Path(self.demo['config'])
        self.receipt = Path(self.demo['receipt'])
        self.state = self.receipt.parent.parent

    def tearDown(self):
        self.temporary.cleanup()

    def args(self, **updates):
        return {'config': str(self.config), 'receipt': str(self.receipt), 'id': 'test-choice',
                'actor': 'Synthetic test operator', 'decision': 'investigate',
                'feedback': 'Synthetic coverage requires a controlled check',
                'next_action': 'Inspect the named synthetic gap',
                'review_trigger': 'After the next synthetic report', **updates}

    def test_checkpoint_refresh_preserves_snapshot_and_returns_progress(self):
        old_json, old_html = self.receipt.read_bytes(), Path(self.demo['html']).read_bytes()
        args = {'config': str(self.config), 'project': 'demo', 'id': 'review', 'status': 'in-progress',
                'actor': 'Synthetic test operator', 'note': 'Synthetic traversal only'}
        plan = mcp.execute('cherry_meter_checkpoint', args)
        mcp.execute('cherry_meter_checkpoint', {**args, 'apply': True, 'expected_plan_sha256': plan['plan_sha256']})
        with self.assertRaises(mcp.Held):
            mcp.execute('cherry_meter_checkpoint', {**args, 'apply': True, 'expected_plan_sha256': plan['plan_sha256']})
        refreshed = apply('cherry_meter_report', {'config': str(self.config)})
        self.assertNotEqual(refreshed['receipt'], str(self.receipt))
        self.assertEqual(refreshed['projects'][0]['operator_outcome']['checkpoints'][0]['status'], 'in-progress')
        self.assertEqual(self.receipt.read_bytes(), old_json)
        self.assertEqual(Path(self.demo['html']).read_bytes(), old_html)
        text = Path(refreshed['html']).read_text(encoding='utf-8')
        for command in ('report', 'checkpoint', 'doctor', 'decision', 'decisions'):
            self.assertIn('/cherry-meter:' + command, text)
        self.assertIn('in-progress', text)
        self.assertIn(refreshed['report_sha256'], text)
        self.assertIn(str(self.config), text)
        self.assertIn('runs nothing and saves nothing', text)

    def test_real_renderer_fixture_states_preserve_identity_and_escape(self):
        base = json.loads(self.receipt.read_bytes())
        for status, value in [('complete', 0), ('partial', 300), ('unavailable', None)]:
            report = copy.deepcopy(base)
            report['coverage']['status'] = status
            report['consumption']['tokens'] = value
            report['sources'][0]['coverage'].update(unassigned_sessions=2, ambiguous_sessions=1)
            hostile = '<script>alert("unsafe")</script>' + 'LongLabel' * 100
            report['device']['label'] = hostile
            report['projects'][0]['selection']['label'] = hostile
            report['projects'][0]['operator_outcome']['statement'] = hostile
            report['consumption']['provider_models'][0]['model'] = hostile
            report['sources'][0]['coverage']['issues'] = [hostile]
            before = encoded(report)
            text = render_device(report, config_path=self.config, receipt_path=self.receipt)
            self.assertEqual(encoded(report), before)
            self.assertEqual(digest(report), __import__('hashlib').sha256(before).hexdigest())
            self.assertNotIn('<script>', text)
            self.assertIn('&lt;script&gt;', text)
            self.assertIn('2 unassigned sessions', text)
            self.assertIn('1 ambiguous sessions', text)
            self.assertIn('Unknown' if value is None else '<p class="number">' + str(value), text)
            headings = ['<h2 id="coverage-heading">', '<h2 id="projects-heading">', '<h2 id="providers-heading">', '<h2 id="next-heading">']
            self.assertEqual(sorted(text.index(h) for h in headings), [text.index(h) for h in headings])
            markup = Markup(); markup.feed(text)
            self.assertEqual(len(markup.ids), len(set(markup.ids)))
            self.assertIn('main', markup.tags)
            self.assertIn('summary', markup.tags)
            self.assertNotIn('script', markup.tags)
            self.assertNotIn('button', markup.tags)
            self.assertNotIn('form', markup.tags)
        self.assertIn('Synthetic demonstration only', render_device(base))

    def test_decision_preview_is_effect_free_and_saved_record_uses_legacy_owner(self):
        args = self.args()
        preview = mcp.execute('cherry_meter_decision', args)
        self.assertFalse((self.state / 'decisions').exists())
        self.assertFalse(preview['plan']['usage_sources_read'])
        self.assertEqual(preview['plan']['record']['receipt'], self.receipt.stem)
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with patch('spend_outcomes.mcp.observer', side_effect=AssertionError('usage forbidden')), \
             patch('subprocess.run', side_effect=AssertionError('execution forbidden')), \
             patch('socket.socket', side_effect=AssertionError('network forbidden')):
            saved = mcp.execute('cherry_meter_decision', {**args, 'apply': True, 'expected_plan_sha256': preview['plan_sha256']})
            history = mcp.execute('cherry_meter_decisions', {'config': str(self.config)})
        self.assertEqual(Path(saved['record']), self.state / 'decisions/test-choice.json')
        self.assertEqual(saved['decision']['contract'], 'pv-decision-v1')
        self.assertEqual(share(saved['decision']), saved['decision'])
        self.assertEqual(history['decisions'], [saved['decision']])
        self.assertEqual(saved['execution_effects'], [])
        self.assertEqual({p: p.read_bytes() for p in before}, before)
        for path in self.root.rglob('*'):
            if path.is_file() and path not in before:
                self.assertTrue(path.parent == self.state / 'decisions' or path == self.state / '.decisions.lock')

    def test_exact_retry_and_conflicting_reuse(self):
        args = self.args()
        preview = mcp.execute('cherry_meter_decision', args)
        applied = {**args, 'apply': True, 'expected_plan_sha256': preview['plan_sha256']}
        first = mcp.execute('cherry_meter_decision', applied)
        raw = Path(first['record']).read_bytes()
        second = mcp.execute('cherry_meter_decision', applied)
        self.assertTrue(second['reused'])
        self.assertEqual(first['decision'], second['decision'])
        self.assertEqual(Path(first['record']).read_bytes(), raw)
        with self.assertRaises(mcp.Held):
            apply('cherry_meter_decision', self.args(feedback='A conflicting new reason'))
        self.assertEqual(Path(first['record']).read_bytes(), raw)

    def test_concurrent_identical_decisions_keep_first_timestamp(self):
        args = self.args()
        preview = mcp.execute('cherry_meter_decision', args)
        applied = {**args, 'apply': True, 'expected_plan_sha256': preview['plan_sha256']}
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: mcp.execute('cherry_meter_decision', applied), range(12)))
        self.assertEqual(len({r['decision']['created_at'] for r in results}), 1)
        self.assertEqual(sum(not r['reused'] for r in results), 1)

    def test_later_snapshot_decision_supersedes_without_overwriting(self):
        first = apply('cherry_meter_decision', self.args())
        raw = Path(first['record']).read_bytes()
        report = apply('cherry_meter_report', {'config': str(self.config)})
        second = apply('cherry_meter_decision', self.args(id='later-choice', receipt=report['receipt'], supersedes='test-choice', decision='hold'))
        self.assertNotEqual(first['report_sha256'], second['report_sha256'])
        self.assertEqual(second['decision']['supersedes'], 'test-choice')
        self.assertEqual(Path(first['record']).read_bytes(), raw)
        self.assertEqual(len(mcp.execute('cherry_meter_decisions', {'config': str(self.config)})['decisions']), 2)

    def test_self_missing_and_incompatible_supersession_are_held(self):
        with self.assertRaises(mcp.Held):
            mcp.execute('cherry_meter_decision', self.args(supersedes='test-choice'))
        with self.assertRaises(mcp.Held):
            apply('cherry_meter_decision', self.args(supersedes='absent'))
        first = apply('cherry_meter_decision', self.args(id='first'))
        value = first['decision']; value['source_versions']['device_sha256'] = '0' * 64
        Path(first['record']).write_bytes(encoded(value))
        with self.assertRaises(mcp.Held):
            apply('cherry_meter_decision', self.args(id='second', supersedes='first'))
        self.assertFalse((self.state / 'decisions/second.json').exists())
        value['source_versions'] = {'device_sha256': digest(json.loads(self.receipt.read_bytes())['device'])}
        Path(first['record']).write_bytes(encoded(value))
        with self.assertRaises(mcp.Held):
            apply('cherry_meter_decision', self.args(id='legacy-link', supersedes='first'))
        self.assertFalse((self.state / 'decisions/legacy-link.json').exists())

    def test_stale_config_cancellation_and_blank_human_fields(self):
        args = self.args()
        preview = mcp.execute('cherry_meter_decision', args)
        original = self.config.read_bytes()
        value = json.loads(self.config.read_bytes()); value['device']['scope'] = 'Changed test scope'
        self.config.write_bytes(encoded(value))
        with self.assertRaises(mcp.Held):
            mcp.execute('cherry_meter_decision', {**args, 'apply': True, 'expected_plan_sha256': preview['plan_sha256']})
        cancel = threading.Event(); cancel.set()
        with self.assertRaises(mcp.Cancelled):
            mcp.execute('cherry_meter_decision', args, cancel)
        self.assertFalse((self.state / 'decisions').exists())
        self.config.write_bytes(original)
        for key in ('actor', 'feedback', 'next_action', 'review_trigger'):
            with self.assertRaises(mcp.Held):
                mcp.execute('cherry_meter_decision', self.args(**{key: ' '}))

    def test_snapshot_tamper_wrong_location_device_and_contract(self):
        original = self.receipt.read_bytes()
        self.receipt.write_bytes(original + b' ')
        with self.assertRaises(mcp.Held):
            mcp.execute('cherry_meter_decision', self.args())
        self.receipt.write_bytes(original)
        copied = self.root / self.receipt.name; copied.write_bytes(original)
        with self.assertRaises(mcp.Held):
            mcp.execute('cherry_meter_decision', self.args(receipt=str(copied)))
        for mutate in (lambda v: v.update(contract='pv-receipt-v1'), lambda v: v['device'].update(label='Another device')):
            value = json.loads(original); mutate(value)
            path = self.receipt.parent / (digest(value) + '.json'); path.write_bytes(encoded(value))
            with self.assertRaises(mcp.Held):
                mcp.execute('cherry_meter_decision', self.args(receipt=str(path)))
        for identity in ('../outside', 'bad/id', 'bad\\id'):
            with self.assertRaises(mcp.Held):
                mcp.execute('cherry_meter_decision', self.args(id=identity))
        self.assertFalse((self.state / 'decisions').exists())

    def test_read_history_is_bounded_and_no_write_on_empty_or_missing_id(self):
        result = mcp.execute('cherry_meter_decisions', {'config': str(self.config)})
        self.assertEqual(result['decisions'], [])
        self.assertFalse((self.state / 'decisions').exists())
        with self.assertRaises(mcp.Held):
            mcp.execute('cherry_meter_decisions', {'config': str(self.config), 'id': 'missing'})
        folder = self.state / 'decisions'; folder.mkdir()
        for i in range(129):
            (folder / (str(i) + '.json')).write_bytes(b'{}')
        with self.assertRaisesRegex(mcp.Held, '128'):
            mcp.execute('cherry_meter_decisions', {'config': str(self.config)})
        with self.assertRaises(mcp.Held):
            mcp.execute('cherry_meter_decisions', {'config': str(self.config), 'id': '0'})
        (folder / 'large.json').write_bytes(b'x' * (mcp.MAX_DECISION + 1))
        with self.assertRaisesRegex(mcp.Held, '64 KiB'):
            mcp.execute('cherry_meter_decisions', {'config': str(self.config), 'id': 'large'})

    def test_observed_zero_is_not_all_sources_unavailable(self):
        config = json.loads(self.config.read_bytes())
        config['sources'] = [config['sources'][0]]
        source = config['sources'][0]
        source['tracking_start'] = '2026-11-01T00:00:00+00:00'
        logs = Path(source['roots'][0])
        for path in logs.glob('*.jsonl'):
            path.unlink()
        path = logs / 'zero.jsonl'
        write_session(path, config['projects']['demo']['workspace'])
        rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
        for row in rows:
            payload = row.get('payload', {})
            for value in payload.get('info', {}).values():
                for key in value:
                    value[key] = 0
            for key in payload.get('usage', {}):
                payload['usage'][key] = 0
        path.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
        self.config.write_bytes(encoded(config))
        result = apply('cherry_meter_report', {'config': str(self.config), 'through': '2026-11-10'})
        self.assertEqual(result['consumption']['tokens'], 0)
        self.assertEqual(result['coverage']['status'], 'complete')
        self.assertIn('<p class="number">0</p>', Path(result['html']).read_text(encoding='utf-8'))
        config['sources'][0]['roots'] = [str(self.root / 'absent-source')]
        self.config.write_bytes(encoded(config))
        missing = apply('cherry_meter_report', {'config': str(self.config), 'through': '2026-11-10'})
        self.assertIsNone(missing['consumption']['tokens'])
        self.assertIn('<p class="number">Unknown</p>', Path(missing['html']).read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
