import unittest
from citation_core import inspect

class CitationTests(unittest.TestCase):
    def test_links_and_duplicate_doi(self):
        result = inspect([{'id':'p1','text':'Growth increased (Smith, 2020).'}, {'id':'p2','text':'References'}, {'id':'p3','text':'Smith, J. (2020). Study. https://doi.org/10.1234/test'}, {'id':'p4','text':'Smith, J. (2020). Study. https://doi.org/10.1234/test'}])
        self.assertEqual(result['citations'][0]['link_status'], 'ambiguous')
        self.assertEqual(len([i for i in result['issues'] if i['kind']=='duplicate_doi']),2)

    def test_fragment_and_format(self):
        result=inspect([{'id':'p1','text':'Smith (2020) reported growth.'}], completeness='fragment')
        self.assertEqual(result['citations'][0]['link_status'],'unresolved')
        self.assertEqual(result['completeness'],'fragment')
        result=inspect([{'id':'p1','text':'References'}, {'id':'p2','text':'Smith, J. 2020. Study. doi:10.1234/test'}],style='apa-7')
        self.assertEqual(len(result['references'][0]['format_issues']),2)

    def test_offsets_locate_original(self):
        text='Evidence (Smith, 2020; Jones, 2021).'
        result=inspect([{'id':'p1','text':text}])
        self.assertEqual(len(result['citations']),2)
        for citation in result['citations']:
            self.assertEqual(text[citation['start']:citation['end']],citation['text'])
