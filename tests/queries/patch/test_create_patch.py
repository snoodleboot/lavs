from unittest import IsolatedAsyncioTestCase

from app.database.database_manager import DatabaseManager
from app.queries.patch_version.create_patch import create_patch
from app.queries.versions.create_version import create_version
from app.queries.versions.retrieve_latest_version import retrieve_latest_version


class TestCreateVersion(IsolatedAsyncioTestCase):
    def setUp(self):
        DatabaseManager.create_table()

    def tearDown(self):
        DatabaseManager.drop_table()

    async def test_create_version(self):
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
        await create_version(product_name, major, minor, patch)
        result = await retrieve_latest_version(product_name=product_name)
        self.assertDictEqual(result, expected_result)

        await create_patch(product_name=product_name)
        result = await retrieve_latest_version(product_name=product_name)
        expected_result = {
            "major": 1,
            "minor": 1,
            "patch": 2,
            "product_name": "test",
            "id": 2,
        }
        self.assertDictEqual(result, expected_result)
