from unittest.mock import patch, MagicMock
from scanner.pricing import (
    get_ebs_cost,
    get_rds_cost,
    get_snapshot_cost,
    convert_usd_to_inr,
    EIP_MONTHLY_COST,
    EBS_PRICING,
)


def test_ebs_gp2_cost():
    assert get_ebs_cost(100, 'gp2') == 100 * 0.10


def test_ebs_gp3_cost():
    assert get_ebs_cost(100, 'gp3') == 100 * 0.08


def test_ebs_io1_cost():
    assert get_ebs_cost(100, 'io1') == 100 * 0.125


def test_ebs_unknown_type_falls_back_to_gp3():
    assert get_ebs_cost(100, 'unknown') == 100 * EBS_PRICING['gp3']


def test_rds_known_instance():
    assert get_rds_cost('db.t3.micro') == 30.0


def test_rds_t4g_micro():
    assert get_rds_cost('db.t4g.micro') == 25.0


def test_rds_unknown_instance_returns_default():
    assert get_rds_cost('db.unknown.type') == 100.0


def test_rds_custom_default():
    assert get_rds_cost('db.unknown.type', default=50.0) == 50.0


def test_snapshot_cost():
    assert get_snapshot_cost(200) == 200 * 0.05


def test_snapshot_zero_size():
    assert get_snapshot_cost(0) == 0.0


def test_eip_monthly_cost():
    assert EIP_MONTHLY_COST == 0.005 * 730


def test_convert_usd_to_inr_with_explicit_rate():
    assert convert_usd_to_inr(100, rate=85.0) == 8500.0


def test_convert_usd_to_inr_zero():
    assert convert_usd_to_inr(0, rate=85.0) == 0.0


def test_convert_usd_to_inr_fetches_rate():
    with patch('scanner.pricing.get_usd_to_inr_rate', return_value=90.0):
        assert convert_usd_to_inr(10) == 900.0


def test_get_usd_to_inr_rate_falls_back_on_error():
    from scanner.pricing import get_usd_to_inr_rate, DEFAULT_USD_TO_INR
    get_usd_to_inr_rate.cache_clear()
    with patch('httpx.Client') as mock_client_class:
        mock_client_class.return_value.__enter__.side_effect = Exception("network error")
        rate = get_usd_to_inr_rate()
        assert rate == DEFAULT_USD_TO_INR
    get_usd_to_inr_rate.cache_clear()


def test_get_usd_to_inr_rate_returns_api_value():
    from scanner.pricing import get_usd_to_inr_rate
    get_usd_to_inr_rate.cache_clear()
    mock_response = MagicMock()
    mock_response.json.return_value = {'rates': {'INR': 84.5}}
    with patch('httpx.Client') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        rate = get_usd_to_inr_rate()
        assert rate == 84.5
    get_usd_to_inr_rate.cache_clear()
