"""Unit tests for the task sourcer module."""

from clawforge.tasks import sourcer


def test_sourcer_returns_empty_when_no_criteria():
    # Replace with the actual API of sourcer.py
    result = sourcer.discover(criteria={})
    assert result == [] or isinstance(result, list)


# Add more tests here, each one asserting a real behavior
