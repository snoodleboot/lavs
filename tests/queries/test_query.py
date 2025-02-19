from unittest import TestCase, IsolatedAsyncioTestCase

from app.models.requests.request_model import RequestModel
from app.queries.query import Query


class TestQuery(IsolatedAsyncioTestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    async def test_execute(self):
        query = Query()
        with self.assertRaises(NotImplementedError):
            await query.execute(data=RequestModel(product_name="test"))
