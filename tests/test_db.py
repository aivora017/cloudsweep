import pytest
from unittest.mock import patch, MagicMock
from scanner.db import ScannerDB


DB_URL = 'postgresql://test:test@localhost/test'

SAMPLE_FINDINGS = [
    {
        'resource_id': 'i-123abc',
        'resource_type': 'EC2',
        'region': 'ap-south-1',
        'reason': 'CPU avg 1.0% over 7 days',
        'monthly_cost_usd': 10.0,
        'monthly_cost_inr': 900.0,
        'tags': {},
        'detected_at': '2026-03-17T00:00:00+00:00',
    }
]


def make_db():
    with patch('scanner.db.pool.SimpleConnectionPool') as mock_pool_class:
        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool
        db = ScannerDB(database_url=DB_URL)
        db.connection_pool = mock_pool
        return db


def test_init_raises_without_database_url(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with pytest.raises(ValueError):
        ScannerDB(database_url=None)


def test_insert_findings_returns_scan_run_id():
    db = make_db()

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = [42]
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    db.connection_pool.getconn.return_value = mock_conn

    scan_run_id = db.insert_findings(['ap-south-1'], SAMPLE_FINDINGS)

    assert scan_run_id == 42
    assert mock_cursor.execute.call_count == 2


def test_insert_findings_empty_list():
    db = make_db()

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = [1]
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    db.connection_pool.getconn.return_value = mock_conn

    scan_run_id = db.insert_findings(['ap-south-1'], [])
    assert scan_run_id == 1


def test_resolve_finding_returns_rowcount():
    db = make_db()

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    db.connection_pool.getconn.return_value = mock_conn

    result = db.resolve_finding('i-123abc')
    assert result == 1


def test_get_waste_trend_returns_list():
    db = make_db()

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.description = [('scan_date',), ('resource_type',), ('finding_count',), ('total_waste_inr',), ('total_waste_usd',)]
    mock_cursor.fetchall.return_value = []
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    db.connection_pool.getconn.return_value = mock_conn

    result = db.get_waste_trend()
    assert isinstance(result, list)


def test_close_calls_closeall():
    db = make_db()
    db.close()
    db.connection_pool.closeall.assert_called_once()
