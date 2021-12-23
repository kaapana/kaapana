from graphene.test import Client
from datamodel.database import schema_dicom
# https://docs.graphene-python.org/en/latest/testing/

def test_hey():
    client = Client(schema_dicom)
    executed = client.execute('''{ hey }''')
    assert executed == {
        'data': {
            'hey': 'hello!'
        }
    }

from snapshottest import TestCase

class APITestCase(TestCase):
    def test_api_me(self):
        """Testing the API for /me"""
        client = Client(schema_dicom)
        self.assertMatchSnapshot(client.execute('''{ hey }'''))