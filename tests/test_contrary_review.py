"""Regression for the installed 0.1.0 contrary-review loss; fixtures are synthetic."""
import copy
import unittest
from spend_outcomes.core import inspect, digest
from test_product import source, binding


def evidence():
    s=source();s['status']='current'
    s['quality']['outcomes']=[{'outcome_id':'result-1','project_id':'canonical-p',
        'last_at':'2026-11-05T16:00:00Z','delivered':True,'verdict':'needs-changes',
        'acceptance_basis':'human','repairs':2,'usage_attribution':'shared-session'}]
    e={'contract':'pv-outcomes-v1','permitted':True,'project_id':'canonical-p',
       'source_id':'authorized-result-owner','version':'export-1','denominator':1,
       'outcomes':[{'id':'result-1','version':'artifact-1','observed_at':'2026-11-05T15:00:00Z',
          'association':'exact','artifact':'artifact-ref','revision':'a'*40,
          'delivered':True,'installed':True,'acceptance':'accepted','benefit':None}]}
    return s,e


class ContraryReviewTests(unittest.TestCase):
    def test_distinct_sources_and_versions_survive_with_logical_count(self):
        s,e=evidence();r=inspect(s,binding(),[],outcomes=e)
        self.assertEqual(len(r['outcomes']),2)
        old,new=r['outcomes']
        self.assertEqual((old['source_id'],old['source_version'],old['version']),('authorized-result-owner','export-1','artifact-1'))
        self.assertEqual((new['source_id'],new['version'],new['acceptance']),('agent-telemetry:quality','2026-11-05T16:00:00Z','needs-changes'))
        self.assertEqual(new['rework'],2);self.assertIsNone(new['installed'])
        self.assertEqual(r['outcome_coverage']['returned'],1)
        self.assertEqual(r['outcome_coverage']['observations_returned'],2)
        self.assertEqual(r['outcome_coverage']['denominator'],1)
        self.assertEqual(r['outcome_conflicts'][0]['id'],'result-1')
        self.assertIn('acceptance',r['outcome_conflicts'][0]['fields'])
        self.assertEqual(r['consumption']['tokens'],120)

    def test_current_contrary_review_drives_specific_nonexecuting_decision(self):
        s,e=evidence()
        t={'kind':'numeric','amount':1,'unit':'tokens','meaning':'observed','from':'2026-10-30','to':'2026-11-05'}
        r=inspect(s,binding(),[t],outcomes=e)
        rec=r['recommendation'];self.assertEqual(rec['action'],'investigate')
        self.assertIn('result-1',rec['next']);self.assertIn('needs-changes',rec['next'])
        self.assertIn(digest(r['outcomes'][1]),rec['evidence'])
        self.assertIn('rework',rec['missing'])
        self.assertEqual(r['execution_effects'],[]);self.assertTrue(r['advisory_only'])

    def test_repeated_observations_collapse_but_source_versions_do_not(self):
        s,e=evidence();s['quality']['outcomes']*=2;e['outcomes']*=2
        r=inspect(s,binding(),[],outcomes=e)
        self.assertEqual(len(r['outcomes']),2)
        e['outcomes'][1]=copy.deepcopy(e['outcomes'][0]);e['outcomes'][1]['version']='artifact-2'
        r=inspect(s,binding(),[],outcomes=e)
        self.assertEqual(len(r['outcomes']),3)
        self.assertEqual(r['outcome_coverage']['returned'],1)

    def test_equal_version_labels_across_sources_never_hide_disagreement(self):
        s,e=evidence();e['outcomes'][0]['version']=s['quality']['outcomes'][0]['last_at']
        r=inspect(s,binding(),[],outcomes=e)
        self.assertEqual(len(r['outcomes']),2)
        self.assertTrue(r['outcome_conflicts'])

    def test_newer_accepted_review_keeps_historical_contrary_without_treating_it_current(self):
        s,e=evidence();e['outcomes'][0]['acceptance']='needs-changes'
        s['quality']['outcomes'][0].update(verdict='accepted',repairs=0)
        r=inspect(s,binding(),[],outcomes=e)
        self.assertEqual(len(r['outcomes']),2)
        self.assertTrue(r['outcome_conflicts'])
        self.assertEqual(r['recommendation']['action'],'hold')
        self.assertIsNone(r['human_benefit'])

    def test_unknown_review_clock_prevents_assuming_supersession(self):
        s,e=evidence();s['quality']['outcomes'][0]['last_at']=None
        r=inspect(s,binding(),[],outcomes=e)
        self.assertEqual(len(r['outcomes']),2)
        self.assertEqual(r['recommendation']['action'],'investigate')
        self.assertIn('unknown',r['recommendation']['missing'])

    def test_agent_verdict_is_not_human_acceptance_and_unknowns_support_hold(self):
        s,e=evidence();s['quality']['outcomes'][0].update(verdict='accepted',acceptance_basis='agent',repairs=0)
        r=inspect(s,binding(),[],outcomes=e)
        self.assertEqual(len(r['outcomes']),2)
        self.assertIsNone(r['outcomes'][1]['acceptance'])
        self.assertIn(digest(r['outcomes'][1]),r['recommendation']['evidence'])
        self.assertIn('human',r['recommendation']['missing'])

    def test_unrelated_project_review_is_excluded_and_input_not_mutated(self):
        s,e=evidence();s['quality']['outcomes'][0]['project_id']='other'
        before=copy.deepcopy((s,e));r=inspect(s,binding(),[],outcomes=e)
        self.assertEqual(len(r['outcomes']),1);self.assertEqual((s,e),before)
