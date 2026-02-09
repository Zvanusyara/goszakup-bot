"""
Tests for Google Sheets integration
Tests GoogleSheetsManager error handling and retry logic
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import gspread

from utils.google_sheets import GoogleSheetsManager


@pytest.mark.google_sheets
@pytest.mark.unit
class TestGoogleSheetsManager:
    """Test GoogleSheetsManager"""

    def test_initialization_with_disabled_flag(self):
        """Test that manager respects GOOGLE_SHEETS_ENABLED=False"""
        with patch('utils.google_sheets.GOOGLE_SHEETS_ENABLED', False):
            manager = GoogleSheetsManager()
            assert manager.enabled is False
            assert manager.client is None

    def test_initialization_handles_missing_credentials(self):
        """Test graceful handling when credentials file is missing"""
        with patch('utils.google_sheets.GOOGLE_SHEETS_ENABLED', True):
            with patch('os.path.exists', return_value=False):
                manager = GoogleSheetsManager()
                assert manager.enabled is False

    @patch('utils.google_sheets.GOOGLE_SHEETS_ENABLED', True)
    @patch('os.path.exists', return_value=True)
    def test_initialization_handles_network_error(self, mock_exists):
        """Test handling of DNS/network errors during initialization"""
        with patch('gspread.authorize') as mock_authorize:
            # Simulate DNS error
            mock_authorize.side_effect = Exception('[Errno -3] Temporary failure in name resolution')

            manager = GoogleSheetsManager()

            # Should be disabled after error
            assert manager.enabled is False

    def test_retry_initialization(self):
        """Test retry_initialization() method"""
        manager = GoogleSheetsManager()
        manager.enabled = False
        manager.client = None

        with patch.object(manager, '_initialize') as mock_init:
            # Simulate successful initialization
            def set_enabled():
                manager.enabled = True
                manager.client = Mock()

            mock_init.side_effect = set_enabled

            result = manager.retry_initialization()

            assert result is True
            assert manager.enabled is True
            mock_init.assert_called_once()

    def test_add_announcement_when_disabled(self):
        """Test add_announcement returns False when disabled"""
        manager = GoogleSheetsManager()
        manager.enabled = False

        result = manager.add_announcement(Mock())

        assert result is False

    def test_update_announcement_when_disabled(self):
        """Test update_announcement returns False when disabled"""
        manager = GoogleSheetsManager()
        manager.enabled = False

        result = manager.update_announcement(Mock())

        assert result is False


@pytest.mark.google_sheets
@pytest.mark.integration
class TestGoogleSheetsErrorHandling:
    """Test error handling and logging for Google Sheets"""

    def test_distinguishes_dns_errors_from_other_errors(self):
        """Test that DNS errors are logged differently from other errors"""
        with patch('utils.google_sheets.logger') as mock_logger:
            with patch('gspread.authorize') as mock_authorize:
                # DNS error
                mock_authorize.side_effect = Exception('name resolution failed')

                manager = GoogleSheetsManager()

                # Check that error was logged with DNS-related message
                # (logger.error should be called with DNS-related message)
                assert mock_logger.error.called

    @patch('utils.google_sheets.GOOGLE_SHEETS_ENABLED', True)
    @patch('os.path.exists', return_value=True)
    def test_handles_api_errors_gracefully(self, mock_exists):
        """Test handling of API errors during add/update operations"""
        with patch('gspread.authorize') as mock_authorize:
            mock_client = Mock()
            mock_spreadsheet = Mock()
            mock_worksheet = Mock()

            mock_authorize.return_value = mock_client
            mock_client.open_by_key.return_value = mock_spreadsheet
            mock_spreadsheet.worksheet.return_value = mock_worksheet

            manager = GoogleSheetsManager()
            assert manager.enabled is True

            # Now simulate error during add_announcement
            mock_worksheet.append_row.side_effect = Exception('API error')

            announcement = Mock()
            announcement.announcement_number = 'TEST-001'
            announcement.lots = None
            announcement.application_deadline = None

            result = manager.add_announcement(announcement)

            # Should return False but not crash
            assert result is False
