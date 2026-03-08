import pytest
import os
import boto3

@pytest.fixture
def aws_credentials(monkeypatch):
    """Mock AWS credentials for tests"""
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'ap-south-1')

@pytest.fixture
def session(aws_credentials):
    """Create a boto3 session with mock credentials"""
    return boto3.Session(region_name='ap-south-1')

