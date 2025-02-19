from unittest import IsolatedAsyncioTestCase

from app.database.database_manager import DatabaseManager
from app.models.requests.application_and_version_model import ApplicationAndVersionNameModel
from app.queries.versions.create_version import CreateVersion
from app.queries.versions.retrieve_version_history import RetrieveVersionHistory


class TestRetrieveVersionHistory(IsolatedAsyncioTestCase):
    def setUp(self):
        DatabaseManager.create_table()

    def tearDown(self):
        DatabaseManager.drop_table()

    async def test_retrieve_version_history(self):
        data_1 = ApplicationAndVersionNameModel(product_name="test", version='1.1.1')
        data_2 = ApplicationAndVersionNameModel(product_name="test", version='1.2.1')
        data_3 = ApplicationAndVersionNameModel(product_name="test", version='2.1.1')

        _ = await CreateVersion().execute(data=data_1)
        _ = await CreateVersion().execute(data=data_2)
        _ = await CreateVersion().execute(data=data_3)

        result = await RetrieveVersionHistory().execute(data=data_1)
        expected_result = [
            {"major": 1, "minor": 1, "patch": 1, "product_name": "test", "id": 1},
            {"major": 1, "minor": 2, "patch": 1, "product_name": "test", "id": 2},
            {"major": 2, "minor": 1, "patch": 1, "product_name": "test", "id": 3},
        ]

        self.assertListEqual(result, expected_result)
