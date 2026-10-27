from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from generate_concept_review import load_descriptions, render_markdown


class ReviewTests(unittest.TestCase):
    def taxonomy(self, directory, text='An official definition.'):
        (directory/'example-doc.xml').write_text('''<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase" xmlns:xlink="http://www.w3.org/1999/xlink"><link:labelLink>
<link:loc xlink:href="schema.xsd#us-gaap_Example" xlink:label="unrelated-locator"/>
<link:label xlink:label="unrelated-resource" xlink:role="http://www.xbrl.org/2003/role/documentation" xml:lang="en-US">'''+text+'''</link:label>
<link:labelArc xlink:from="unrelated-locator" xlink:to="unrelated-resource"/>
</link:labelLink></link:linkbase>''')

    def test_description_is_bound_by_locator_and_arc(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);self.taxonomy(path)
            definitions,files=load_descriptions(path)
            self.assertEqual(definitions['us-gaap:Example']['text'],'An official definition.')
            self.assertEqual(files,['example-doc.xml'])

    def test_conflicting_versions_are_not_silently_mixed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);self.taxonomy(path)
            other=path/'other';other.mkdir();self.taxonomy(other,'Different definition.')
            with self.assertRaisesRegex(ValueError,'Conflicting definitions'):load_descriptions(path)

    def sample(self):
        return {'profile_id':'test','research_scope':{'source_sics':['1234']},'concepts':[
            {'concept':'us-gaap:Mapped','label':'Mapped'},
            {'concept':'us-gaap:Unmapped','label':'Unmapped'},
            {'concept':'dei:Entity','label':'Entity'}]}

    def test_namespaces_and_mapping_status_are_separated(self):
        files,counts=render_markdown(self.sample(),{'us-gaap:Mapped':['IS / mapped'],'dei:Entity':['BS / entity']},{},[],1)
        self.assertEqual(counts,{'mapped':1,'unmapped':1,'other':1})
        self.assertIn('### us-gaap:Mapped',files['pages/mapped-001.md'])
        self.assertNotIn('### us-gaap:Unmapped',files['pages/mapped-001.md'])
        self.assertIn('### us-gaap:Unmapped',files['pages/unmapped-001.md'])
        self.assertIn('### dei:Entity',files['pages/other-dei-001.md'])
        self.assertIn('No description found',files['pages/other-dei-001.md'])

    def test_pagination_preserves_all_entries_and_indexes(self):
        inventory=self.sample();inventory['concepts'] += [{'concept':'us-gaap:Zebra','label':'Zebra'}]
        files,_=render_markdown(inventory,{}, {},[],1)
        self.assertEqual(len([p for p in files if p.startswith('pages/unmapped-')]),3)
        pages='\n'.join(text for p,text in files.items() if p.startswith('pages/'))
        for item in inventory['concepts']:self.assertEqual(pages.count('### '+item['concept']),1)
        self.assertIn('(pages/unmapped-003.md)',files['unmapped_concepts.md'])

    def test_source_text_is_escaped(self):
        inventory=self.sample();inventory['concepts'][0]['label']='<script>alert(1)</script>'
        files,_=render_markdown(inventory,{}, {'us-gaap:Mapped':{'text':'<img src=x onerror=alert(1)>'}},[],1)
        page=files['pages/unmapped-001.md']
        self.assertNotIn('<script>',page);self.assertNotIn('<img',page)
        self.assertIn('&lt;script&gt;',page)

    def test_duplicate_concepts_are_rejected(self):
        inventory=self.sample();inventory['concepts'].append(inventory['concepts'][0])
        with self.assertRaisesRegex(ValueError,'duplicate'):render_markdown(inventory,{}, {},[])


if __name__=='__main__':unittest.main()
