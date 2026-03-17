import pytest
from unittest.mock import patch, MagicMock
from notifier.slack import SlackNotifier


WEBHOOK = 'https://hooks.slack.com/test'

SAMPLE_FINDINGS = [
    {
        'resource_id': 'i-123abc',
        'resource_type': 'EC2',
        'monthly_cost_inr': 2000.0,
        'monthly_cost_usd': 24.0,
    },
    {
        'resource_id': 'vol-456def',
        'resource_type': 'EBS',
        'monthly_cost_inr': 800.0,
        'monthly_cost_usd': 9.0,
    },
]

SAMPLE_SUMMARY = {
    'total_waste_inr': 2800.0,
    'total_findings': 2,
    'regions_scanned': ['ap-south-1'],
}


def test_init_raises_without_webhook(monkeypatch):
    monkeypatch.delenv('SLACK_WEBHOOK_URL', raising=False)
    with pytest.raises(ValueError):
        SlackNotifier(webhook_url=None)


def test_init_uses_env_variable(monkeypatch):
    monkeypatch.setenv('SLACK_WEBHOOK_URL', WEBHOOK)
    notifier = SlackNotifier()
    assert notifier.webhook_url == WEBHOOK


def test_send_message_posts_to_webhook():
    with patch('httpx.Client') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        notifier = SlackNotifier(webhook_url=WEBHOOK)
        notifier.send_message('hello')

        mock_client.post.assert_called_once_with(WEBHOOK, json={'text': 'hello'})


def test_send_digest_empty_findings():
    with patch('httpx.Client') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        notifier = SlackNotifier(webhook_url=WEBHOOK)
        notifier.send_digest([], {'total_waste_inr': 0, 'total_findings': 0, 'regions_scanned': []})

        mock_client.post.assert_called_once()


def test_send_digest_with_findings():
    with patch('httpx.Client') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        notifier = SlackNotifier(webhook_url=WEBHOOK)
        notifier.send_digest(SAMPLE_FINDINGS, SAMPLE_SUMMARY)

        mock_client.post.assert_called_once()
        payload = mock_client.post.call_args[1]['json']
        assert 'blocks' in payload


def test_send_digest_threshold_alert_block_added():
    findings = SAMPLE_FINDINGS.copy()
    summary = {**SAMPLE_SUMMARY, 'total_waste_inr': 60000.0}

    with patch('httpx.Client') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        notifier = SlackNotifier(webhook_url=WEBHOOK)
        notifier.send_digest(findings, summary)

        payload = mock_client.post.call_args[1]['json']
        texts = [b.get('text', {}).get('text', '') for b in payload['blocks'] if b.get('type') == 'section']
        assert any('ALERT' in t for t in texts)


def test_threshold_alert_not_sent_below_threshold():
    with patch.object(SlackNotifier, 'send_message') as mock_send:
        notifier = SlackNotifier(webhook_url=WEBHOOK)
        notifier.send_threshold_alert([], {'total_waste_inr': 10000.0, 'total_findings': 1})
        mock_send.assert_not_called()


def test_threshold_alert_sent_above_threshold():
    with patch.object(SlackNotifier, 'send_message') as mock_send:
        notifier = SlackNotifier(webhook_url=WEBHOOK)
        notifier.send_threshold_alert([], {'total_waste_inr': 60000.0, 'total_findings': 5})
        mock_send.assert_called_once()
