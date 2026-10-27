import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from generate_statement_reviews import find_facts_by_sic, add_statement_info, group_facts_by_statement, collect_mapped, write_review_files


class StatementReviewTests(unittest.TestCase):
    def test_counts_deduplicate_tickers_and_skip_missing_files_in_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            companies = {'a':{'cik_str':1,'sic':1234},'b':{'cik_str':1,'sic':1234},
                         'c':{'cik_str':2,'sic':1234},'d':{'cik_str':3,'sic':1234},
                         'e':{'cik_str':4,'sic':9999}}
            info = path/'companies.json'; info.write_text(json.dumps(companies))
            (path/'CIK0000000001.json').write_text(json.dumps({'facts':{'us-gaap':{'Rare':{'label':'Rare concept','units':{'USD':[{'val':1},{'val':2}]}}}}}))
            (path/'CIK0000000002.json').write_text(json.dumps({'facts':{'dei':{'Other':{'label':'Other'}}}}))
            with contextlib.redirect_stdout(io.StringIO()):
                facts, loaded, selected = find_facts_by_sic(['1234'], path, info)
            self.assertEqual(loaded, {'1','2'}); self.assertEqual(selected,3)
            rare = next(f for f in facts if f['fact']=='us-gaap:Rare')
            self.assertEqual((rare['company_count'], rare['appearance_percentage']), (1,50.0))

    def test_statement_evidence_uses_loaded_companies_and_has_no_majority_threshold(self):
        facts = [{'fact':'us-gaap:Revenue','company_count':1,'appearance_percentage':0.01}]
        rows = pd.DataFrame([{'sic':'1234','cik':'1','concept':'us-gaap:Revenue','stmt':s} for s in ['IS','CF']]+
                            [{'sic':'1234','cik':'9','concept':'us-gaap:Revenue','stmt':'BS'}])
        enriched = add_statement_info(facts, ['1234'], rows, {'1'})
        groups = group_facts_by_statement(enriched)
        self.assertEqual(len(groups['IS']),1);self.assertEqual(len(groups['CF']),1)
        self.assertEqual(groups['BS'],[])
        self.assertEqual(enriched[0]['company_count'],1)
        self.assertEqual(enriched[0]['appearance_percentage'],0.01)

    def test_other_statement_types_and_no_evidence_remain_unclassified(self):
        facts = [{'fact':'us-gaap:A','stmt':['EQ']},{'fact':'dei:B','stmt':[]}]
        groups = group_facts_by_statement(facts)
        self.assertEqual(groups['unclassified'],facts)

    def test_json_formats_preserve_records_and_filter_each_statement(self):
        a = {'fact':'us-gaap:A','label':'A','description':None,'company_count':1,'appearance_percentage':0.25}
        b = {'fact':'us-gaap:B','label':'B','description':'Definition','company_count':2,'appearance_percentage':0.5}
        facts = [b,a]
        grouped = {'BS':facts,'IS':[a],'CF':[],'unclassified':[]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            write_review_files(path,facts,grouped,{'loaded_companies':400},{'BS':{'us-gaap:A'},'IS':set(),'CF':set()})
            self.assertEqual(json.loads((path/'facts_by_sic.json').read_text()),facts)
            self.assertEqual(json.loads((path/'facts_by_statement.json').read_text()),grouped)
            self.assertEqual(json.loads((path/'unmapped_facts_by_sic.json').read_text()),[b])
            missing=json.loads((path/'unmapped_facts_by_statement.json').read_text())
            self.assertEqual(missing['BS'],[b])
            self.assertEqual(missing['IS'],[a])
            self.assertIsNone(missing['IS'][0]['description'])
            self.assertEqual(missing['IS'][0]['company_count'],1)
            self.assertEqual(missing['IS'][0]['appearance_percentage'],0.25)
        self.assertEqual(collect_mapped([{'concepts':[{'name':'us-gaap:A'}],'children':[]}]),{'us-gaap:A'})


if __name__=='__main__':unittest.main()
