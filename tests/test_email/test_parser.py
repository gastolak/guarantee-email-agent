"""Tests for email parser."""

import pytest
import logging
from datetime import datetime
from guarantee_email_agent.email.parser import EmailParser
from guarantee_email_agent.email.models import EmailMessage
from guarantee_email_agent.utils.errors import EmailParseError


def test_parse_email_plain_text():
    """Test parsing plain text email with all fields."""
    parser = EmailParser()
    raw_email = {
        'subject': 'Warranty check',
        'body': 'Hi, I need warranty info for SN12345',
        'from': 'customer@example.com',
        'received': '2026-01-18T10:00:00',
        'thread_id': 'thread_123',
        'message_id': 'msg_456'
    }

    email = parser.parse_email(raw_email)

    assert email.subject == 'Warranty check'
    assert email.body == 'Hi, I need warranty info for SN12345'
    assert email.from_address == 'customer@example.com'
    assert isinstance(email.received_timestamp, datetime)
    assert email.thread_id == 'thread_123'
    assert email.message_id == 'msg_456'


def test_parse_email_text_body_field():
    """Test parsing email with text_body field (preferred over body)."""
    parser = EmailParser()
    raw_email = {
        'subject': 'Test',
        'text_body': 'This is the text body',
        'body': 'This is the html body',
        'from': 'test@example.com',
        'received': '2026-01-18T10:00:00'
    }

    email = parser.parse_email(raw_email)

    # Should prefer text_body over body
    assert email.body == 'This is the text body'


def test_parse_email_html_conversion():
    """Test HTML email converted to plain text."""
    parser = EmailParser()
    raw_email = {
        'subject': 'HTML email',
        'body': '<p>Hello <b>world</b></p>',
        'from': 'test@example.com',
        'received': '2026-01-18T10:00:00',
        'content_type': 'text/html'
    }

    email = parser.parse_email(raw_email)

    # HTML tags should be stripped
    assert '<p>' not in email.body
    assert '<b>' not in email.body
    assert 'Hello' in email.body
    assert 'world' in email.body


def test_parse_email_missing_optional_fields():
    """Test parsing email without optional fields."""
    parser = EmailParser()
    raw_email = {
        'subject': 'Test',
        'body': 'Test body',
        'from': 'test@example.com',
        'received': '2026-01-18T10:00:00'
    }

    email = parser.parse_email(raw_email)

    assert email.thread_id is None
    assert email.message_id is None


def test_parse_email_missing_required_field():
    """Test parsing email with missing required field raises error."""
    parser = EmailParser()
    raw_email = {
        'subject': 'Test',
        'body': 'Test body'
        # Missing 'from' field
    }

    with pytest.raises(EmailParseError) as exc_info:
        parser.parse_email(raw_email)

    assert 'from' in str(exc_info.value).lower()
    assert exc_info.value.code == 'email_missing_field'


def test_parse_email_no_subject_uses_default():
    """Test email without subject uses default."""
    parser = EmailParser()
    raw_email = {
        # No subject
        'body': 'Test body',
        'from': 'test@example.com',
        'received': '2026-01-18T10:00:00'
    }

    email = parser.parse_email(raw_email)

    assert email.subject == '(No Subject)'


def test_parse_email_datetime_parsing():
    """Test timestamp parsing from ISO string."""
    parser = EmailParser()
    raw_email = {
        'subject': 'Test',
        'body': 'Test body',
        'from': 'test@example.com',
        'received': '2026-01-18T15:30:45'
    }

    email = parser.parse_email(raw_email)

    assert email.received_timestamp.year == 2026
    assert email.received_timestamp.month == 1
    assert email.received_timestamp.day == 18
    assert email.received_timestamp.hour == 15
    assert email.received_timestamp.minute == 30


def test_parse_email_logs_at_info_level(caplog):
    """Test email parsing logs at INFO level WITHOUT body."""
    parser = EmailParser()
    raw_email = {
        'subject': 'Test Subject',
        'body': 'SENSITIVE CUSTOMER DATA',
        'from': 'test@example.com',
        'received': '2026-01-18T10:00:00',
        'message_id': 'msg_123'
    }

    with caplog.at_level(logging.INFO):
        email = parser.parse_email(raw_email)

    # Check INFO log contains metadata
    assert 'Email received' in caplog.text
    assert 'Test Subject' in caplog.text
    assert 'test@example.com' in caplog.text

    # Check INFO log does NOT contain body (NFR14)
    assert 'SENSITIVE CUSTOMER DATA' not in caplog.text


def test_parse_email_logs_body_at_debug_only(caplog):
    """Test email body only logged at DEBUG level (NFR14)."""
    parser = EmailParser()
    raw_email = {
        'subject': 'Test',
        'body': 'SENSITIVE CUSTOMER DATA',
        'from': 'test@example.com',
        'received': '2026-01-18T10:00:00'
    }

    # First test: INFO level should NOT show body
    with caplog.at_level(logging.INFO):
        caplog.clear()
        parser.parse_email(raw_email)
        assert 'SENSITIVE CUSTOMER DATA' not in caplog.text

    # Second test: DEBUG level SHOULD show body
    with caplog.at_level(logging.DEBUG):
        caplog.clear()
        parser.parse_email(raw_email)
        assert 'SENSITIVE CUSTOMER DATA' in caplog.text


def test_parse_email_encoding_handling():
    """Test email parsing handles special characters and encoding."""
    parser = EmailParser()
    raw_email = {
        'subject': 'Test with émojis 🎉',
        'body': 'Special chars: café, naïve, Zürich',
        'from': 'test@example.com',
        'received': '2026-01-18T10:00:00'
    }

    email = parser.parse_email(raw_email)

    assert 'émojis' in email.subject or 'emojis' in email.subject
    assert 'café' in email.body or 'cafe' in email.body


def test_parse_email_malformed_raises_error():
    """Test completely malformed email raises EmailParseError."""
    parser = EmailParser()
    raw_email = {
        # Completely broken structure
        'invalid': 'data'
    }

    with pytest.raises(EmailParseError) as exc_info:
        parser.parse_email(raw_email)

    assert exc_info.value.code in ['email_missing_field', 'email_parse_failed']
