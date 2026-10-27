"""Inventories follow research SICs and retain rare concepts without duplication."""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from generate_concept_inventory import build_profile


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.repo=Path(self.tmp.name)
        (self.repo/'archetypes/test').mkdir(parents=True)
        (self.repo/'archetypes/test/profile.json').write_text(json.dumps({'research_scope':{'source_sics':['1111']}}))
        paths={s:f'archetypes/test/{s.lower()}.json' for s in ['IS','BS','CF']}
        (self.repo/'archetypes/sic_to_archetype.json').write_text(json.dumps({'archetypes':{'test':{'statements':paths}},'defaults':{'unlisted_sic':{'archetype':'test'}}}))
        for s,p in paths.items():
            (self.repo/p).write_text(json.dumps({'nodes':[{'node_id':'revenue','label':'Revenue','concepts':[{'name':'us-gaap:Revenues','status':'proposed'}]}] if s=='IS' else []}))
        self.db=sqlite3.connect(':memory:');self.addCleanup(self.db.close);self.db.row_factory=sqlite3.Row
        self.db.executescript('''
        CREATE TABLE filings(filing_id INTEGER PRIMARY KEY,company_id INTEGER,accession TEXT,form TEXT,filed_date TEXT);
        CREATE TABLE raw_facts(fact_id INTEGER PRIMARY KEY,filing_id INTEGER,concept_id INTEGER,value TEXT,unit TEXT,start_date TEXT,end_date TEXT);
        INSERT INTO filings VALUES(1,1,'a','10-K','2025-02-01'),(2,1,'b','10-K','2026-02-01'),(3,2,'c','10-K','2025-02-01'),(4,3,'d','10-K','2025-02-01');
        INSERT INTO raw_facts VALUES(1,1,1,'1','USD','2024-01-01','2024-12-31'),(2,2,1,'2','USD','2025-01-01','2025-12-31'),(3,1,2,'7','shares',NULL,'2024-12-31'),(4,3,1,'3','USD','2024-01-01','2024-12-31'),(5,4,3,'99','USD',NULL,'2024-12-31');
        ''')
        self.companies=[dict(company_id=i,cik=str(i).zfill(10),ticker=f'T{i}',name=f'Company {i}',sic=sic) for i,sic in [(1,'1111'),(2,'1111'),(3,'9999'),(4,'1111')]]
        self.concepts={i:dict(taxonomy=tax,tag=tag,label=tag) for i,tax,tag in [(1,'us-gaap','Revenues'),(2,'dei','RareShares'),(3,'us-gaap','FallbackOnly')]}

    def test_source_sics_exclude_runtime_fallback_companies(self):
        all_items,unmapped=build_profile(self.db,self.repo,'test',self.companies,self.concepts,'test')
        self.assertEqual(all_items['population']['companies_in_source_db'],3)
        self.assertEqual(all_items['population']['companies_with_facts'],2)
        self.assertNotIn('us-gaap:FallbackOnly',[i['concept'] for i in all_items['concepts']])

    def test_company_counts_not_filing_counts_and_examples_keep_latest_row(self):
        all_items,_=build_profile(self.db,self.repo,'test',self.companies,self.concepts,'test')
        revenue=next(i for i in all_items['concepts'] if i['concept']=='us-gaap:Revenues')
        self.assertEqual(revenue['company_count'],2)
        self.assertEqual(revenue['observation_count'],3)
        self.assertEqual(revenue['examples'][0]['value'],'2')
        self.assertEqual(revenue['examples'][0]['accession'],'b')
        self.assertEqual(revenue['company_counts_by_sic'],{'1111':2})

    def test_rare_concepts_taxonomies_and_units_are_not_filtered(self):
        _,unmapped=build_profile(self.db,self.repo,'test',self.companies,self.concepts,'test')
        self.assertEqual([i['concept'] for i in unmapped['concepts']],['dei:RareShares'])
        item=unmapped['concepts'][0]
        self.assertEqual(item['examples'][0]['unit'],'shares')
        self.assertEqual(item['company_count'],1)
        self.assertEqual(item['mappings'],[])
        self.assertIsNone(unmapped['filters']['minimum_appearance'])


if __name__=='__main__':unittest.main()
