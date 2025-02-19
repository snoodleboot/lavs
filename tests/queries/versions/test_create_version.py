from unittest import IsolatedAsyncioTestCase

from app.database.database_manager import DatabaseManager
from app.models.requests.application_and_version_model import ApplicationAndVersionNameModel
from app.queries.versions.create_version import CreateVersion
from app.queries.versions.retrieve_latest_version import RetrieveLatestVersion


class TestCreateVersion(IsolatedAsyncioTestCase):
    def setUp(self):
        DatabaseManager.create_table()

    def tearDown(self):
        DatabaseManager.drop_table()

    async def test_create_version(self):
        data = ApplicationAndVersionNameModel(
            product_name = "test",
            version='1.1.1'
        )
        expected_result = {
            "major": 1,
            "minor": 1,
            "patch": 1,
            "product_name": "test",
            "id": 1,
        }
        await CreateVersion().execute(data=data)
        result = await RetrieveLatestVersion().execute(data=data)
        self.assertDictEqual(result, expected_result)
