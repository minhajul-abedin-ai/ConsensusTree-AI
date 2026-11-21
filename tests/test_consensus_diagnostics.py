import unittest
from consensustree.consensus_diagnostics import summarize_votes


class VoteDiagnosticsTests(unittest.TestCase):
    def test_unanimous(self):
        self.assertEqual(summarize_votes(['yes', 'yes'])['winner'], 'yes')

    def test_tie_has_no_winner(self):
        result = summarize_votes(['yes', 'no'])
        self.assertTrue(result['tie'])
        self.assertIsNone(result['winner'])

    def test_abstention_is_not_vote(self):
        result = summarize_votes(['yes', None, 'yes'])
        self.assertEqual(result['abstained'], 1)
        self.assertAlmostEqual(result['winner_share_of_all'], 2 / 3)

    def test_all_abstain(self):
        result = summarize_votes([None, None])
        self.assertIsNone(result['winner'])
        self.assertFalse(result['unanimous_among_responses'])

    def test_reject_empty(self):
        with self.assertRaises(ValueError):
            summarize_votes([])

    def test_reject_blank_and_wrong_type(self):
        for bad in ('', ' ', 1, False):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                summarize_votes([bad])

    def test_generator_and_stable_counts(self):
        result = summarize_votes(x for x in ['b', 'a', 'b'])
        self.assertEqual(list(result['counts']), ['a', 'b'])
