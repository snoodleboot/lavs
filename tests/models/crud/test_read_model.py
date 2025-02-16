from unittest import TestCase

from app.models.crud.read_model import ReadModel


class TestReadModel(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_cotr(self):
        instance = ReadModel()
        self.assertIsInstance(instance, ReadModel)
