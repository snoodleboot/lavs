from unittest import IsolatedAsyncioTestCase

from app.database.database_manager import DatabaseManager
from app.queries.versions.create_version import create_version
from app.queries.versions.retrieve_version_history import retrieve_version_history


class TestRetrieveVersionHistory(IsolatedAsyncioTestCase):
    def setUp(self):
        DatabaseManager.create_table()

    def tearDown(self):
        DatabaseManager.drop_table()

    async def test_retrieve_version_history(self):
        product_name = "test"
        major = 1
        minor = 1
        patch = 1
        _ = await create_version(product_name, major, minor, patch)
        _ = await create_version(product_name, major, minor + 1, patch)
        _ = await create_version(product_name, major + 1, minor, patch)

        result = await retrieve_version_history(product_name=product_name)
        expected_result = [
            {"major": 1, "minor": 1, "patch": 1, "product_name": "test", "id": 1},
            {"major": 1, "minor": 2, "patch": 1, "product_name": "test", "id": 2},
            {"major": 2, "minor": 1, "patch": 1, "product_name": "test", "id": 3},
        ]

        self.assertListEqual(result, expected_result)
