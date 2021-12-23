import unittest
from datamodel import KaapanaDatamodel

class TestStringMethods(unittest.TestCase):

    def test_kaapana_datamodel(self):
        dm = KaapanaDatamodel()
        self.assertEqual(dm.get_data(), {"dummy": ["data"]})

if __name__ == '__main__':
    unittest.main()