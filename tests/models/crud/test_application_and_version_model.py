from unittest import TestCase

from app.models.requests.application_and_version_model import (
    ApplicationAndVersionNameModel,
)
from app.models.requests.application_name_model import ApplicationNameModel
from app.models.requests.request_model import RequestModel


class TestRequestModel(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_cotr(self):
        instance = ApplicationAndVersionNameModel(
            application_name="test_app", version="1.2.3"
        )
        self.assertIsInstance(instance, ApplicationAndVersionNameModel)
        with self.assertRaises(ValueError):
            instance = ApplicationAndVersionNameModel(
                application_name="test_app", version="1.2.g"
            )
        self.assertIsInstance(instance, ApplicationAndVersionNameModel)
