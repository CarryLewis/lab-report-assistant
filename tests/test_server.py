import unittest

from server import _normalise_work, _plain_text


class ScholarlyMetadataTests(unittest.TestCase):
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
