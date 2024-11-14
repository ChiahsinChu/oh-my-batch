from unittest import TestCase
from oh_my_batch import util

class TestUtil(TestCase):

    def test_split_list(self):
        l = list(range(10))
        n = 3
        result = list(util.split_list(l, n))
        self.assertEqual(len(result), n)
        self.assertEqual(len(result[0]), 4)
        self.assertEqual(len(result[1]), 3)
        self.assertEqual(len(result[2]), 3)
        self.assertEqual(result[0], [0, 1, 2, 3])
        self.assertEqual(result[1], [4, 5, 6])
        self.assertEqual(result[2], [7, 8, 9])

        n = 20
        result = list(util.split_list(l, n))
        self.assertEqual(len(result), 10)
        self.assertEqual(result[0], [0])
        self.assertEqual(result[1], [1])
        self.assertEqual(result[9], [9])

