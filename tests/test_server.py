import unittest

from server import _normalise_work, _plain_text, merge_works


class ScholarlyMetadataTests(unittest.TestCase):
    def test_merge_retains_provenance_and_fills_abstract(self):
        result = merge_works([[{'doi': '10.1/ABC', 'source': 'Crossref', 'abstract': None}], [{'doi': '10.1/abc', 'source': 'PubMed', 'abstract': 'Evidence', 'pmid': '123'}]])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['sources'], ['Crossref', 'PubMed'])
        self.assertEqual(result[0]['abstract'], 'Evidence')
        self.assertEqual(result[0]['pmid'], '123')

    def test_same_title_without_identifier_is_not_merged(self):
        self.assertEqual(len(merge_works([[{'title': 'Same title', 'source': 'Crossref'}], [{'title': 'Same title', 'source': 'PubMed'}]])), 2)

    def test_plain_text_removes_jats_markup(self):
        self.assertEqual(_plain_text("<jats:p>A &amp; B</jats:p>"), "A & B")

    def test_normalise_work_handles_crossref_arrays(self):
        work = _normalise_work({
            "title": ["A paper"],
            "author": [{"given": "Ada", "family": "Lovelace"}],
            "published-print": {"date-parts": [[1843, 1, 1]]},
            "container-title": ["Example Journal"],
            "DOI": "10.1234/example",
            "abstract": "<jats:p>Evidence text.</jats:p>",
        })
        self.assertEqual(work["title"], "A paper")
        self.assertEqual(work["authors"], ["Ada Lovelace"])
        self.assertEqual(work["year"], 1843)
        self.assertEqual(work["abstract"], "Evidence text.")

    def test_normalise_work_tolerates_missing_optional_fields(self):
        work = _normalise_work({})
        self.assertEqual(work["title"], "Untitled work")
        self.assertEqual(work["authors"], [])
        self.assertIsNone(work["year"])
        self.assertIsNone(work["doi"])


if __name__ == "__main__":
    unittest.main()
