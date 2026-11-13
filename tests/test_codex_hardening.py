"""Synthetic-only coverage and accounting regression fixtures."""
import datetime as dt
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from spend_outcomes.codex import observe_codex, observe_codex_views, parse_codex_file, _inside


class CodexHardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.logs=self.root/'logs';self.logs.mkdir()
        self.workspace=self.root/'project';self.workspace.mkdir()
        self.projects={'p':{'permitted':True,'workspace':str(self.workspace)}}

    def rows(self, tokens=10, model='gpt-exact'):
        return [
            {'timestamp':'2026-11-10T10:00:00Z','type':'session_meta','payload':{'id':'s','cwd':str(self.workspace)}},
            {'timestamp':'2026-11-10T10:00:00Z','type':'turn_context','payload':{'model':model}},
            self.counter('2026-11-10T10:01:00Z', tokens, tokens),
        ]

    def counter(self, timestamp, total, last=None):
        info={'total_token_usage':{'input_tokens':total,'output_tokens':0}}
        if last is not None:info['last_token_usage']={'input_tokens':last,'output_tokens':0}
        return {'timestamp':timestamp,'type':'event_msg','payload':{'type':'token_count','info':info}}

    def write(self,name,rows):
        path=self.logs/name
        path.write_text(''.join(json.dumps(row)+'\n' for row in rows),encoding='utf-8')
        return path

    def observe(self,**kwargs):
        return observe_codex([self.logs],self.projects,'p',7,'2026-11-10',**kwargs)

    def test_identical_copies_nonadditive_and_identity_qualified(self):
        self.write('one.jsonl',self.rows());self.write('two.jsonl',self.rows())
        report=self.observe();period=report['projects'][0]['period']
        self.assertEqual(period['tokens'],10)
        self.assertEqual(period['provider_models'][0]['client'],'codex')
        self.assertEqual(period['provider_models'][0]['service_route'],'unknown')
        self.assertEqual(period['provider_models'][0]['model'],'gpt-exact')

    def test_counter_conflicting_copy_excluded_and_third_copy_cannot_restore(self):
        self.write('a.jsonl',self.rows());self.write('b.jsonl',self.rows(11));self.write('c.jsonl',self.rows())
        report=self.observe()
        self.assertEqual(report['projects'][0]['period']['tokens'],0)
        self.assertEqual(report['status'],'partial')
        self.assertGreater(report['conflicts']['total'],0)
        self.assertIn('conflicting_event_observation',report['coverage']['issues'])

    def test_model_conflict_is_not_another_billing_category(self):
        self.write('a.jsonl',self.rows());self.write('b.jsonl',self.rows(model='different'))
        self.assertEqual(self.observe()['projects'][0]['period']['tokens'],0)

    def test_in_file_conflict_cannot_be_restored_from_clean_copy(self):
        rows=self.rows()+[self.counter('2026-11-10T10:01:00Z',11,11)]
        self.write('a.jsonl',rows);self.write('b.jsonl',self.rows())
        self.assertEqual(self.observe()['projects'][0]['period']['tokens'],0)

    def test_compaction_conflict_and_repeat(self):
        rows=self.rows()
        response={'timestamp':'2026-11-10T10:02:00Z','type':'token_usage_record',
                  'payload':{'thread_id':'s','response_id':'r','usage':{'input_tokens':5,'output_tokens':1}}}
        marker={'type':'compacted','payload':{'compaction_response_id':'r'}}
        rows += [response,marker,marker]
        self.write('a.jsonl',rows)
        self.assertEqual(self.observe()['projects'][0]['period']['tokens'],16)
        changed=json.loads(json.dumps(rows));changed[-3]['payload']['usage']['input_tokens']=6
        self.write('b.jsonl',changed)
        self.assertEqual(self.observe()['projects'][0]['period']['tokens'],10)

    def test_partial_line_and_malformed_reported_at_source(self):
        path=self.write('a.jsonl',self.rows())
        with path.open('ab') as f:f.write(b'{bad\n{unfinished')
        report=self.observe()
        self.assertEqual(report['projects'][0]['period']['tokens'],10)
        self.assertEqual(report['sources'][0]['status'],'partial')
        self.assertIn('partial_trailing_line',report['sources'][0]['issues'])
        self.assertIn('malformed_jsonl',report['sources'][0]['issues'])

    def test_read_and_file_count_limits_are_partial(self):
        self.write('a.jsonl',self.rows());self.write('b.jsonl',self.rows())
        self.assertIn('source_file_limit_exceeded',self.observe(max_files=1)['coverage']['issues'])
        self.assertIn('source_line_limit_exceeded',self.observe(max_line_bytes=10)['coverage']['issues'])
        self.assertIn('source_size_limit_exceeded',self.observe(max_file_bytes=10)['coverage']['issues'])

    def test_deadline_stops_before_reading(self):
        path=self.write('a.jsonl',self.rows())
        record=parse_codex_file(path,deadline=time.monotonic()-1)
        self.assertEqual(record['events'],[])
        self.assertIn('scan_deadline_exceeded',record['issues'])

    def test_tracking_start_excludes_interval_straddling_cutover(self):
        self.write('a.jsonl',self.rows()+[self.counter('2026-11-10T10:02:00Z',15),
                                                   self.counter('2026-11-10T10:03:00Z',17)])
        report=self.observe(tracking_start='2026-11-10T10:01:30Z')
        self.assertEqual(report['projects'][0]['period']['tokens'],2)
        self.assertIn('inferred_counter_interval_crosses_report_start',report['coverage']['issues'])
        self.assertEqual(report['status'],'partial')
        self.assertIn('tracking_started_within_report_window',report['coverage']['issues'])

    def test_prospective_first_cumulative_is_not_backfill(self):
        rows=self.rows()[:2]+[self.counter('2026-11-10T10:01:00Z',500)]
        self.write('a.jsonl',rows)
        report=self.observe(tracking_start='2026-11-10T09:00:00Z')
        self.assertEqual(report['projects'][0]['period']['tokens'],0)
        self.assertIn('prospective_counter_baseline_unavailable',report['coverage']['issues'])

    def test_counter_reset_and_replay(self):
        self.write('a.jsonl',self.rows()+[
            self.counter('2026-11-10T10:02:00Z',3,3),
            self.counter('2026-11-10T10:00:30Z',8,8),
            self.counter('2026-11-10T10:03:00Z',8,5)])
        self.assertEqual(self.observe()['projects'][0]['period']['tokens'],18)

    def test_subsets_not_added_and_privacy(self):
        rows=self.rows();info=rows[-1]['payload']['info']
        for counter in info.values():counter.update(cached_input_tokens=3,reasoning_output_tokens=0)
        rows.append({'type':'response_item','payload':{'text':'PRIVATE SENTINEL'}})
        self.write('a.jsonl',rows)
        report=self.observe()
        self.assertEqual(report['projects'][0]['period']['tokens'],10)
        self.assertNotIn('PRIVATE SENTINEL',json.dumps(report))

    def test_native_path_boundary(self):
        self.assertTrue(_inside(self.workspace/'nested',self.workspace))
        self.assertFalse(_inside(self.root/'project-other',self.workspace))
        if os.name=='nt':
            self.assertTrue(_inside(str(self.workspace).upper(),str(self.workspace).lower()))
            self.assertFalse(_inside('Z:\\other','C:\\root'))

    def test_device_scope_counts_unmapped_without_project_attribution(self):
        self.write('a.jsonl',self.rows())
        other=self.rows(7);other[0]['payload']['id']='other';other[0]['payload']['cwd']=str(self.root/'unmapped')
        self.write('b.jsonl',other)
        report=observe_codex([self.logs],self.projects,None,7,'2026-11-10')
        row=report['projects'][0]
        self.assertEqual(row['project_id'],'device')
        self.assertEqual(row['period']['tokens'],17)
        self.assertEqual(row['attribution'],'explicit-source-roots-device')
        self.assertEqual(report['coverage']['unassigned_sessions'],1)
        self.assertEqual(self.observe()['projects'][0]['period']['tokens'],10)

    def test_device_scope_works_without_project_bindings(self):
        self.write('a.jsonl',self.rows())
        report=observe_codex([self.logs],{},None,7,'2026-11-10')
        self.assertEqual(report['projects'][0]['period']['tokens'],10)

    def test_views_read_once_and_share_same_sanitized_snapshot(self):
        path=self.write('a.jsonl',self.rows())
        projects={**self.projects,'second':{'permitted':True,'workspace':str(self.root/'second')},
                  'forbidden':{'permitted':False,'workspace':str(self.root/'private')}}
        def changing_source(path, **kwargs):
            record=parse_codex_file(path, **kwargs)
            self.write('a.jsonl',self.rows(999))
            return record
        with patch('spend_outcomes.codex.parse_codex_file',side_effect=changing_source) as parser:
            views=observe_codex_views([self.logs],projects,7,'2026-11-10')
        self.assertEqual(parser.call_count,1)
        self.assertEqual(views['device']['projects'][0]['period']['tokens'],10)
        self.assertEqual(views['projects']['p']['projects'][0]['period']['tokens'],10)
        self.assertEqual(views['projects']['second']['projects'][0]['period']['tokens'],0)
        self.assertNotIn('forbidden',views['projects'])
        self.assertEqual(views['device']['generation'],views['projects']['p']['generation'])
        views['device']['sources'][0]['status']='mutated'
        self.assertEqual(views['projects']['p']['sources'][0]['status'],'current')

    def test_review_cutover_and_report_window_boundaries(self):
        rows=self.rows()[:2]+[self.counter('2026-11-10T09:00:00Z',100),
                             self.counter('2026-11-10T11:00:00Z',200)]
        self.write('a.jsonl',rows)
        report=self.observe(tracking_start='2026-11-10T10:00:00Z')
        self.assertEqual(report['projects'][0]['period']['tokens'],0)
        self.assertIn('inferred_counter_interval_crosses_report_start',report['coverage']['issues'])
        rows=self.rows()[:2]+[self.counter('2026-11-09T23:00:00Z',100),
                             self.counter('2026-11-10T01:00:00Z',200),
                             self.counter('2026-11-10T02:00:00Z',220)]
        self.write('a.jsonl',rows)
        report=observe_codex([self.logs],self.projects,'p',1,'2026-11-10')
        self.assertEqual(report['projects'][0]['period']['tokens'],20)
        self.assertIn('inferred_counter_interval_crosses_report_start',report['coverage']['issues'])

    def test_conflicted_baseline_recovery_is_order_invariant(self):
        for variants in ((100,300),(300,100)):
            rows=self.rows()[:2]+[self.counter('2026-11-10T09:00:00Z',50)]
            rows += [self.counter('2026-11-10T10:00:00Z',n) for n in variants]
            rows += [self.counter('2026-11-10T11:00:00Z',400),
                     self.counter('2026-11-10T12:00:00Z',450)]
            path=self.write('a.jsonl',rows)
            parsed=parse_codex_file(path)
            self.assertEqual([event['tokens'] for event in parsed['events']],[50,50])
            report=self.observe()
            self.assertEqual(report['projects'][0]['period']['tokens'],100)
            self.assertIn('conflicted_counter_baseline_excluded',report['coverage']['issues'])

    def test_late_conflict_and_cross_copy_dependencies_are_excluded(self):
        rows=self.rows()[:2]+[self.counter('2026-11-10T09:00:00Z',50),
                             self.counter('2026-11-10T11:00:00Z',400),
                             self.counter('2026-11-10T10:00:00Z',100),
                             self.counter('2026-11-10T10:00:00Z',300)]
        self.write('a.jsonl',rows)
        self.assertEqual(self.observe()['projects'][0]['period']['tokens'],50)
        a=self.rows()[:2]+[self.counter('2026-11-10T09:00:00Z',50),
                           self.counter('2026-11-10T10:00:00Z',100),
                           self.counter('2026-11-10T11:00:00Z',400)]
        b=self.rows()[:2]+[self.counter('2026-11-10T09:00:00Z',50),
                           self.counter('2026-11-10T10:00:00Z',300)]
        self.write('a.jsonl',a);self.write('b.jsonl',b)
        self.assertEqual(self.observe()['projects'][0]['period']['tokens'],50)

    def test_invalid_bounds_and_tracking(self):
        for kwargs in ({'max_seconds':0},{'max_seconds':float('nan')},{'max_files':True},
                       {'max_line_bytes':0},{'tracking_start':'2026-11-10'}):
            with self.assertRaises(ValueError):self.observe(**kwargs)


if __name__=='__main__':unittest.main()
