from unittest import IsolatedAsyncioTestCase

from app.database.database_manager import DatabaseManager
from app.queries.versions.create_version import create_version


class TestReadLatestVersion(IsolatedAsyncioTestCase):
    def setUp(self):
        DatabaseManager.create_table()

    def tearDown(self):
        DatabaseManager.drop_table()

    async def test_read_latest_version(self):
        product_name = "test"
        major = 1
        minor = 1
        patch = 1
        expected_result = {
            "major": 1,
            "minor": 1,
            "patch": 1,
            "product_name": "test",
            "id": 1,
        }
        result = await create_version(product_name, major, minor, patch)
        self.assertDictEqual(result, expected_result)
