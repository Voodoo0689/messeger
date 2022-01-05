"""Unit-тесты сервера"""

import sys
import os
import unittest

sys.path.append(os.path.join(os.getcwd(), '..'))
from server import get_args


class TestServer(unittest.TestCase):

    def test_get_args(self):
        test = get_args()
        self.assertEqual(test, ('', 7777))


if __name__ == '__main__':
    unittest.main()
