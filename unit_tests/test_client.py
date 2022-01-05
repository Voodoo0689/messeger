"""Unit-тесты клиента"""

import sys
import os
import unittest
sys.path.append(os.path.join(os.getcwd(), '..'))
from client import get_args


class TestClass(unittest.TestCase):

    def test_conf_args(self):
        test = get_args()
        self.assertEqual(test, ('127.0.0.1', 7777, 'default'))


if __name__ == '__main__':
    unittest.main()
