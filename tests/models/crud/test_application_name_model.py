from unittest import TestCase

from app.models.requests.application_name_model import ApplicationNameModel
from app.models.requests.request_model import RequestModel


class TestRequestModel(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_cotr(self):
        instance = ApplicationNameModel(product_name="test_app")
        self.assertIsInstance(instance, ApplicationNameModel)
