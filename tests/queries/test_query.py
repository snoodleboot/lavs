from unittest import TestCase

from app.models.requests.request_model import RequestModel
from app.queries.query import Query


class TestQuery(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_execute(self):
        query = Query()
        with self.assertRaises(NotImplementedError):
            query.execute(data=RequestModel(application_name="test"))
