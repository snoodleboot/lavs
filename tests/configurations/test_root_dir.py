import os.path
from unittest import TestCase

from app.configurations.root_dir import root_dir


class TestRoot(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_root(self):
        result = root_dir()
        # This will test Windows and Linux = a bit hacky - but the code is hacky right now so fine with it.
        try:
            self.assertEqual(
                result.replace(os.path.dirname(os.path.dirname(result)), ''),
                r'\lavs\app'
            )
        except:
            self.assertEqual(
                result.replace(os.path.dirname(os.path.dirname(result)), ''),
                r'/lavs/app'
            )