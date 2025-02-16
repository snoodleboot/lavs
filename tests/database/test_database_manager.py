from unittest import TestCase

from app.database.database_manager import DatabaseManager


class TestDatabaseManager(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_build(self):
        DatabaseManager().create_table()
        pass

    def test_delete(self):
        DatabaseManager().create_table()
        DatabaseManager().drop_table()