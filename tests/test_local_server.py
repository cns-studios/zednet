import unittest
from unittest.mock import MagicMock
from pathlib import Path

from server.local_server import initialize_server
from core.app_controller import AppController
from core.storage import SiteStorage


class TestLocalServer(unittest.TestCase):
    def test_initialize_server(self):
        # Create mock objects
        mock_audit_logger = MagicMock()
        mock_content_dir = MagicMock(spec=Path)
        mock_controller = MagicMock(spec=AppController)
        mock_controller.storage = MagicMock(spec=SiteStorage)
        mock_controller.directory_info_hash = "test_hash"

        # Call the function to be tested
        initialize_server(mock_audit_logger, mock_content_dir, mock_controller)

        # Assert that the global variables in local_server are set correctly
        from server import local_server
        self.assertEqual(local_server.audit_logger, mock_audit_logger)
        self.assertEqual(local_server.content_dir, mock_content_dir)
        self.assertEqual(local_server.storage, mock_controller.storage)
        self.assertEqual(local_server.directory_info_hash, "test_hash")
        self.assertEqual(local_server.app_controller, mock_controller)


if __name__ == '__main__':
    unittest.main()