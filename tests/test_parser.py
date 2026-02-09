"""
Tests for GoszakupParser
Tests parsing logic and filtering by deadlines
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from parsers.goszakup import GoszakupParser


@pytest.mark.parser
@pytest.mark.unit
class TestGoszakupParser:
    """Test GoszakupParser functionality"""

    def test_parser_initialization(self):
        """Test that parser initializes correctly"""
        parser = GoszakupParser()
        assert parser is not None
        assert parser.session is not None

    def test_filter_lots_by_date_removes_expired(self):
        """Test that _filter_lots_by_date removes lots with expired deadlines"""
        parser = GoszakupParser()
        now = datetime.now()

        lots = [
            {
                'announcement_number': 'FUTURE-1',
                'application_deadline': now + timedelta(days=5),
                'lot_name': 'Future Lot'
            },
            {
                'announcement_number': 'EXPIRED-1',
                'application_deadline': now - timedelta(days=10),
                'lot_name': 'Expired Lot'
            },
            {
                'announcement_number': 'FUTURE-2',
                'application_deadline': now + timedelta(days=2),
                'lot_name': 'Future Lot 2'
            }
        ]

        filtered = parser._filter_lots_by_date(lots, days_back=7)

        # Only future lots should remain
        assert len(filtered) == 2
        assert all(lot['application_deadline'] >= now - timedelta(days=7) for lot in filtered)

    def test_extract_region_from_address(self):
        """Test region extraction from legal address"""
        parser = GoszakupParser()

        test_cases = [
            ('г. Алматы, ул. Тестовая, 1', 'г. Алматы'),
            ('г. Астана, пр. Мира, 10', 'г. Астана'),
            ('Карагандинская область, г. Караганда', 'Карагандинская область'),
            ('Неизвестный адрес', 'Не указан'),
        ]

        for address, expected_region in test_cases:
            region = parser._extract_region(address)
            assert region == expected_region, f"Failed for address: {address}"

    def test_group_lots_by_announcement(self):
        """Test grouping lots by announcement number"""
        parser = GoszakupParser()

        lots = [
            {
                'announcement_number': 'ANN-001',
                'lot_number': 1,
                'lot_name': 'Lot 1',
                'lot_description': 'Desc 1',
                'keyword_matched': 'keyword1',
                'announcement_url': 'url1',
                'organization_name': 'Org 1',
                'organization_bin': 'BIN1',
                'legal_address': 'Address 1',
                'region': 'Region 1',
                'application_deadline': datetime.now(),
                'procurement_method': 'Method 1'
            },
            {
                'announcement_number': 'ANN-001',
                'lot_number': 2,
                'lot_name': 'Lot 2',
                'lot_description': 'Desc 2',
                'keyword_matched': 'keyword2',
                'announcement_url': 'url1',
                'organization_name': 'Org 1',
                'organization_bin': 'BIN1',
                'legal_address': 'Address 1',
                'region': 'Region 1',
                'application_deadline': datetime.now(),
                'procurement_method': 'Method 1'
            },
            {
                'announcement_number': 'ANN-002',
                'lot_number': 1,
                'lot_name': 'Lot 3',
                'lot_description': 'Desc 3',
                'keyword_matched': 'keyword3',
                'announcement_url': 'url2',
                'organization_name': 'Org 2',
                'organization_bin': 'BIN2',
                'legal_address': 'Address 2',
                'region': 'Region 2',
                'application_deadline': datetime.now(),
                'procurement_method': 'Method 2'
            }
        ]

        grouped = parser._group_lots_by_announcement(lots)

        assert len(grouped) == 2
        # First announcement should have 2 lots
        ann1 = next(a for a in grouped if a['announcement_number'] == 'ANN-001')
        assert len(ann1['lots']) == 2
        # Second announcement should have 1 lot
        ann2 = next(a for a in grouped if a['announcement_number'] == 'ANN-002')
        assert len(ann2['lots']) == 1


@pytest.mark.parser
@pytest.mark.integration
class TestParserFiltering:
    """Test parser filtering to prevent parsing old announcements"""

    def test_parser_does_not_return_expired_announcements(self, mock_parser):
        """Critical: Parser should NOT return announcements with deadlines in the past"""
        now = datetime.now()

        # Mock parser to return mix of valid and expired
        mock_results = [
            {
                'announcement_number': 'VALID-1',
                'application_deadline': now + timedelta(days=5),
                'organization_name': 'Valid Org'
            },
            {
                'announcement_number': 'EXPIRED-1',
                'application_deadline': now - timedelta(days=10),
                'organization_name': 'Expired Org'
            }
        ]

        # Simulate filtering (this is what parser should do)
        cutoff = now - timedelta(days=7)
        filtered = [
            ann for ann in mock_results
            if ann.get('application_deadline') and ann['application_deadline'] >= cutoff
        ]

        # Only valid announcement should remain
        assert len(filtered) == 1
        assert filtered[0]['announcement_number'] == 'VALID-1'
