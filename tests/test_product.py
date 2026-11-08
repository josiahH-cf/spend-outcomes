import copy
import json
from pathlib import Path
import tempfile
import unittest
from spend_outcomes.core import inspect, save_record, read_export


def source():
    return {'contract':'telemetry-consumer-v1','producer':'agent-telemetry',
      'status':'stale','conflicts':[],'generation':{'finished_at':'2026-11-01T00:00:00Z','digest':'a'},
      'projects':[{'project_id':'p','project_code':'p','attribution':'correlated',
        'period':{'from_day':'2026-10-30','to_day':'2026-11-05','days':7,'tokens':120,
         'api_equivalent_cost_usd':2.0,'unpriced_tokens':20,'basis':'UTC events'}}],
      'capacity':[{'remaining_percent':0,'account':'subscription'}],
      'coverage':{'missing':[{'source':'work','status':'unavailable'}]},
      'accounting':{'shared':{'tokens':40},'totals':{'tokens':160}},
      'quality':{'outcomes_total':2,'outcomes':[]}}


def binding():
    return {'project_id':'canonical-p','telemetry_project_id':'p','association':'owner-attested','days':7}


class ProductTests(unittest.TestCase):
    def test_unknown_billed_cash_and_unpriced_not_zero(self):
        r=inspect(source(),binding(),[{'kind':'numeric','unit':'USD','meaning':'billed-cash','amount':3,'from':'2026-10-30','to':'2026-11-05'}])
        self.assertIsNone(r['comparisons'][0]['actual'])
        self.assertEqual(r['consumption']['unpriced_tokens'],20)
        self.assertEqual(r['consumption']['api_equivalent_cost_usd'],2)

    def test_same_basis_token_target_and_nonadditive_views(self):
        r=inspect(source(),binding(),[{'kind':'numeric','unit':'tokens','meaning':'observed','amount':100,'from':'2026-10-30','to':'2026-11-05'}])
        self.assertEqual(r['comparisons'][0]['excess'],20)
        self.assertEqual(r['consumption']['tokens'],120)
        self.assertEqual(r['other_views']['shared']['tokens'],40)
        self.assertTrue(r['advisory_only'])

    def test_weekly_estimate_partial_pricing_not_full_actual(self):
        t={'kind':'numeric','unit':'USD','meaning':'api-equivalent','amount':3,'from':'2026-10-30','to':'2026-11-05'}
        self.assertIsNone(inspect(source(),binding(),[t])['comparisons'][0]['actual'])
        s=source();s['projects'][0]['period']['unpriced_tokens']=0
        self.assertEqual(inspect(s,binding(),[t])['comparisons'][0]['remainder'],1)

    def test_share_never_infers_denominator(self):
        r=inspect(source(),binding(),[{'kind':'allocation','percent':5,'period':'weekly','unit':'tokens','account':'subscription'}])
        self.assertIsNone(r['comparisons'][0]['actual'])
        self.assertIsNone(r['comparisons'][0]['absolute_target'])
        self.assertTrue(r['advisory_only'])

    def test_missing_source_and_freshness_survive_regeneration(self):
        a=inspect(source(),binding(),[]); b=inspect(source(),binding(),[])
        self.assertEqual(a['source'],b['source'])
        self.assertEqual(a['source']['as_of'],'2026-11-01T00:00:00Z')
        self.assertEqual(a['recommendation']['action'],'investigate')
        self.assertIsNone(a['human_benefit'])

    def test_changed_period_and_no_numeric_targets(self):
        t={'kind':'numeric','unit':'tokens','meaning':'observed','amount':100,'from':'2026-10-29','to':'2026-11-04'}
        self.assertIsNone(inspect(source(),binding(),[t])['comparisons'][0]['actual'])
        self.assertEqual(inspect(source(),binding(),[{'kind':'qualitative','aim':'preserve quality'}])['comparisons'][0]['status'],'qualitative')

    def test_outcome_delivery_acceptance_benefit_stay_separate(self):
        e={'contract':'pv-outcomes-v1','source_id':'owner','version':'v1','project_id':'canonical-p','permitted':True,
           'outcomes':[{'id':'o','version':'r1','association':'exact','delivered':True,'acceptance':'accepted','benefit':None,'corrections':['rework']} ]}
        r=inspect(source(),binding(),[],outcomes=e)
        self.assertIsNone(r['outcomes'][0]['benefit'])
        self.assertEqual(r['outcomes'][0]['corrections'],['rework'])
        self.assertIsNone(r['human_benefit'])

    def test_disallowed_and_ambiguous_sources(self):
        s=source();s['contract']='raw-transcript'
        with self.assertRaises(ValueError):inspect(s,binding(),[])
        s=source();s['projects'].append(copy.deepcopy(s['projects'][0]))
        with self.assertRaises(ValueError):inspect(s,binding(),[])

    def test_idempotent_records_and_conflicting_import(self):
        with tempfile.TemporaryDirectory() as d:
            record={'contract':'pv-decision-v1','id':'decision-1','actor':'operator','receipt':'sha','decision':'keep','feedback':None,'provenance':'operator-reported'}
            a=save_record(Path(d),record);self.assertEqual(a,save_record(Path(d),record))
            self.assertEqual(read_export(a),record)
            record['decision']='change'
            with self.assertRaises(ValueError):save_record(Path(d),record)

    def test_mismatched_export_window_is_not_selected_period(self):
        b=binding();b['days']=30
        with self.assertRaises(ValueError):inspect(source(),b,[])

    def test_consumer_outcomes_retain_human_acceptance_basis(self):
        s=source();s['quality']['outcomes']=[{'outcome_id':'o','project_id':'canonical-p','delivered':True,'verdict':'accepted','acceptance_basis':'agent','last_at':'2026-11-05T01:00:00Z','repairs':1}]
        r=inspect(s,binding(),[])
        self.assertEqual(len(r['outcomes']),1)
        self.assertEqual(r['outcomes'][0]['acceptance_basis'],'agent')
        self.assertIsNone(r['outcomes'][0]['acceptance'])

    def test_prior_manual_comparison_requires_declared_conditions(self):
        b=binding();r=inspect(source(),b,[])
        self.assertEqual(inspect(source(),b,[],baseline=r)['prior_comparison']['status'],'unsupported')
        r['changed_conditions']=[]
        self.assertEqual(inspect(source(),b,[],baseline=r)['prior_comparison']['status'],'comparable')
        r['selection']['project_id']='other'
        self.assertEqual(inspect(source(),binding(),[],baseline=r)['prior_comparison']['status'],'unsupported')

    def test_high_and_exhausted_observations_have_no_execution_effect(self):
        s=source();s['status']='current'
        r=inspect(s,binding(),[{'kind':'numeric','unit':'tokens','meaning':'observed','amount':1,'from':'2026-10-30','to':'2026-11-05'}])
        self.assertEqual(r['recommendation']['action'],'change')
        self.assertEqual(r['execution_effects'],[])
        self.assertTrue(r['advisory_only'])
