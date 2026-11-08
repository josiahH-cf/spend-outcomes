import unittest
from spend_outcomes.core import inspect
from test_product import source, binding


class AttributionTests(unittest.TestCase):
    def test_session_observation_and_project_linkage_remain_nonadditive(self):
        s=source();s['sessions']=[{'vendor':'openai','session_id':'fixture-session',
            'status':'observed','attribution':'exact','linkage':'unattributed',
            'project_id':'ad-hoc','tokens':25}]
        r=inspect(s,binding(),[])
        self.assertEqual(r['native_sessions'],s['sessions'])
        self.assertEqual(r['consumption']['tokens'],120)
        self.assertEqual(r['native_sessions'][0]['linkage'],'unattributed')
        self.assertEqual(r['execution_effects'],[])
