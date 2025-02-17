from unittest import TestCase

from app.models.requests.request_model import RequestModel


class TestRequestModel(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_cotr(self):
        instance = RequestModel()
        self.assertIsInstance(instance, RequestModel)
